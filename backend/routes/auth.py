"""
Authentication Routes
Handles login, logout, session management, and user registration
"""

from flask import Blueprint, request, jsonify, session
from backend.config import get_db_connection
from backend.utils.helpers import hash_password, verify_password, get_client_ip
from werkzeug.utils import secure_filename
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login endpoint
    Request body: {username, password}
    Response: {success, user_data, message}
    """
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'}), 400
        
        # Get database connection
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Find user by username or email
        query = """
            SELECT u.*, d.dept_name, d.dept_code
            FROM users u
            LEFT JOIN departments d ON u.dept_id = d.dept_id
            WHERE (u.username = %s OR u.email = %s) AND u.is_active = TRUE
        """
        cursor.execute(query, (username, username))
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Verify password
        if not verify_password(password, user['password_hash']):
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Create session
        session.permanent = False
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['full_name'] = user['full_name']
        session['dept_id'] = user['dept_id']
        session['email'] = user['email']
        
        # Get advisor name for students
        advisor_name = None
        if user['role'] == 'student' and user['advisor_id']:
            cursor.execute("SELECT full_name FROM users WHERE user_id = %s", (user['advisor_id'],))
            advisor = cursor.fetchone()
            if advisor:
                advisor_name = advisor['full_name']
        
        cursor.close()
        conn.close()
        
        # Prepare response data (exclude password hash)
        user_data = {
            'user_id': user['user_id'],
            'username': user['username'],
            'email': user['email'],
            'full_name': user['full_name'],
            'role': user['role'],
            'dept_name': user.get('dept_name'),
            'dept_code': user.get('dept_code'),
            'registration_no': user.get('registration_no'),
            'phone': user.get('phone'),
            'parent_name': user.get('parent_name'),
            'parent_mobile': user.get('parent_mobile'),
            'profile_image': user.get('profile_image'),
            'advisor_name': advisor_name
        }
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': user_data
        }), 200
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Server error during login'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    try:
        session.clear()
        return jsonify({'success': True, 'message': 'Logged out successfully'}), 200
    except Exception as e:
        print(f"Logout error: {e}")
        return jsonify({'success': False, 'message': 'Error during logout'}), 500

@auth_bp.route('/departments', methods=['GET'])
def get_departments():
    """Fetch all departments for the registration dropdown"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT dept_id, dept_name, dept_code FROM departments ORDER BY dept_name")
        departments = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'departments': departments
        }), 200
    except Exception as e:
        print(f"Error fetching departments: {e}")
        return jsonify({'success': False, 'message': 'Failed to load departments'}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Student self-registration endpoint
    Handles multipart/form-data for profile photo upload
    """
    try:
        # Get data from multipart/form-data
        data = request.form.to_dict()
        profile_file = request.files.get('profile_image')
        
        # Validate required fields based on role
        role = data.get('role', 'student')
        required_fields = ['username', 'password', 'full_name', 'phone']
        
        # Email and Dept are required for all but Security/Admin
        if role != 'security' and role != 'admin':
            required_fields.extend(['email', 'dept_id'])
            
        # Admin still needs email
        if role == 'admin':
            required_fields.append('email')
            
        if role == 'student':
            required_fields.extend(['registration_no', 'parent_name', 'parent_mobile'])
            
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required for {role}'}), 400

        # Phone validation (restore variable for DB)
        phone = data.get('phone', '').strip()
        if not phone.isdigit() or len(phone) != 10:
            return jsonify({'success': False, 'message': 'Student phone number must be exactly 10 digits'}), 400

        # Parent Mobile validation (if student)
        parent_mobile = data.get('parent_mobile', '').strip() or None
        if role == 'student' and parent_mobile:
            if not parent_mobile.isdigit() or len(parent_mobile) != 10:
                return jsonify({'success': False, 'message': 'Parent mobile number must be exactly 10 digits'}), 400

        # Handle Security-specific defaults (Email is NOT NULL in DB)
        email = data.get('email', '').strip()
        if role == 'security' and not email:
            email = f"security_{data['username']}@portal.local"
            
        # Validate email format (except for our generated placeholder if needed)
        if '@' not in email or '.' not in email:
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400
            
        # Format Full Name (Title Case)
        full_name = data.get('full_name', '').strip().title()
        
        # Hash password
        password_hash = hash_password(data['password'])
        
        # Handle profile image upload
        profile_image_path = None
        if profile_file and profile_file.filename:
            from backend.config import app, allowed_file
            if allowed_file(profile_file.filename):
                # Use registration_no if present, otherwise username
                identifier = data.get('registration_no') or data['username']
                filename = secure_filename(f"{role}_{identifier}_{profile_file.filename}")
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], 'profiles', filename)
                profile_file.save(upload_path)
                profile_image_path = f"uploads/profiles/{filename}"
        
        # Get database connection
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        try:
            # Insert new user
            query = """
                INSERT INTO users (username, email, password_hash, full_name, role, 
                                 registration_no, phone, dept_id, parent_name, parent_mobile, profile_image)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            # Sanitize optional fields: convert empty strings to None (stored as NULL in DB)
            reg_no = data.get('registration_no', '').strip() or None
            p_name = data.get('parent_name', '').strip() or None

            cursor.execute(query, (
                data['username'],
                email,
                password_hash,
                full_name,
                role,
                reg_no,
                phone,
                data.get('dept_id') or None,
                p_name,
                parent_mobile,
                profile_image_path
            ))
            
            conn.commit()
            user_id = cursor.lastrowid
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Registration successful! Please login.',
                'user_id': user_id
            }), 201
            
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            
            # Check for duplicate entry
            if 'Duplicate entry' in str(e):
                return jsonify({'success': False, 'message': 'Username, email, or registration number already exists'}), 400
            
            raise e
            
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'success': False, 'message': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """
    Change user password
    Request body: {current_password, new_password}
    """
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Not logged in'}), 401
        
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'success': False, 'message': 'Both passwords required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'New password must be at least 6 characters'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Verify current password
        cursor.execute("SELECT password_hash FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()
        
        if not user or not verify_password(current_password, user['password_hash']):
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401
        
        # Update password
        new_hash = hash_password(new_password)
        cursor.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", 
                      (new_hash, session['user_id']))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        print(f"Change password error: {e}")
        return jsonify({'success': False, 'message': 'Failed to change password'}), 500