"""
Student Routes
Handles student-specific operations: apply for outpass, view status, history, etc.
"""

from flask import Blueprint, request, jsonify, session
from backend.config import get_db_connection
from backend.utils.helpers import (
    login_required, role_required, format_datetime, format_date, format_time,
    validate_outpass_timing, log_action, get_client_ip
)
from datetime import datetime

student_bp = Blueprint('student', __name__, url_prefix='/api/student')

@student_bp.route('/apply-outpass', methods=['POST'])
@role_required('student')
def apply_outpass():
    """
    Apply for new outpass
    Request body: {out_date, out_time, expected_return_time, reason, destination}
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['out_date', 'out_time', 'expected_return_time', 'reason']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Validate timing
        is_valid, error_msg = validate_outpass_timing(
            data['out_date'], 
            data['out_time'], 
            data['expected_return_time']
        )
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get student's advisor and department
        cursor.execute("""
            SELECT u.advisor_id, u.dept_id, d.dept_name
            FROM users u
            LEFT JOIN departments d ON u.dept_id = d.dept_id
            WHERE u.user_id = %s
        """, (session['user_id'],))
        
        student_info = cursor.fetchone()
        
        if not student_info:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Student record not found'}), 404
            
        advisor_id = student_info['advisor_id']
        
        # Fallback: If no advisor is assigned, find any active staff in the same department
        if not advisor_id:
            cursor.execute("""
                SELECT user_id FROM users 
                WHERE role = 'staff' AND dept_id = %s AND is_active = TRUE 
                LIMIT 1
            """, (student_info['dept_id'],))
            fallback_staff = cursor.fetchone()
            if fallback_staff:
                advisor_id = fallback_staff['user_id']
            else:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'No staff/advisor available in your department. Contact admin.'}), 400
        
        # Get HOD for department
        cursor.execute("""
            SELECT user_id FROM users 
            WHERE role = 'hod' AND dept_id = %s AND is_active = TRUE
            LIMIT 1
        """, (student_info['dept_id'],))
        
        hod = cursor.fetchone()
        hod_id = hod['user_id'] if hod else None
        
        # Insert outpass request
        query = """
            INSERT INTO outpasses 
            (student_id, out_date, out_time, expected_return_time, reason, 
             destination, advisor_id, hod_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            session['user_id'],
            data['out_date'],
            data['out_time'],
            data['expected_return_time'],
            data['reason'],
            data.get('destination', ''),
            advisor_id,
            hod_id
        ))
        
        outpass_id = cursor.lastrowid
        conn.commit()
        
        # Log the action
        log_action(conn, outpass_id, session['user_id'], 'created', 
                  'Outpass request created', get_client_ip())
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Outpass request submitted successfully',
            'outpass_id': outpass_id
        }), 201
        
    except Exception as e:
        print(f"Apply outpass error: {e}")
        return jsonify({'success': False, 'message': 'Failed to submit outpass request'}), 500

@student_bp.route('/my-outpasses', methods=['GET'])
@role_required('student')
def get_my_outpasses():
    """Get all outpasses for logged-in student"""
    try:
        status_filter = request.args.get('status')  # Optional filter by status
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Build query
        query = """
            SELECT 
                o.*,
                a.full_name as advisor_name,
                h.full_name as hod_name,
                d.dept_name
            FROM outpasses o
            LEFT JOIN users a ON o.advisor_id = a.user_id
            LEFT JOIN users h ON o.hod_id = h.user_id
            LEFT JOIN users s ON o.student_id = s.user_id
            LEFT JOIN departments d ON s.dept_id = d.dept_id
            WHERE o.student_id = %s
        """
        
        params = [session['user_id']]
        
        if status_filter:
            query += " AND o.final_status = %s"
            params.append(status_filter)
        
        query += " ORDER BY o.created_at DESC"
        
        cursor.execute(query, params)
        outpasses = cursor.fetchall()
        
        # Format datetime fields
        for outpass in outpasses:
            outpass['out_date'] = format_date(outpass['out_date'])
            outpass['out_time'] = format_time(outpass['out_time'])
            outpass['expected_return_time'] = format_time(outpass['expected_return_time'])
            outpass['created_at'] = format_datetime(outpass['created_at'])
            outpass['updated_at'] = format_datetime(outpass['updated_at'])
            outpass['advisor_action_time'] = format_datetime(outpass['advisor_action_time'])
            outpass['hod_action_time'] = format_datetime(outpass['hod_action_time'])
            outpass['qr_generated_at'] = format_datetime(outpass['qr_generated_at'])
            outpass['qr_expires_at'] = format_datetime(outpass['qr_expires_at'])
            outpass['actual_exit_time'] = format_datetime(outpass['actual_exit_time'])
            outpass['actual_entry_time'] = format_datetime(outpass['actual_entry_time'])
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'outpasses': outpasses
        }), 200
        
    except Exception as e:
        print(f"Get outpasses error: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch outpasses'}), 500

@student_bp.route('/outpass/<int:outpass_id>', methods=['GET'])
@role_required('student')
def get_outpass_details(outpass_id):
    """Get detailed information about a specific outpass"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get outpass details
        query = """
            SELECT 
                o.*,
                s.full_name as student_name,
                s.registration_no,
                s.phone as student_phone,
                a.full_name as advisor_name,
                a.email as advisor_email,
                h.full_name as hod_name,
                h.email as hod_email,
                d.dept_name,
                d.dept_code
            FROM outpasses o
            JOIN users s ON o.student_id = s.user_id
            LEFT JOIN users a ON o.advisor_id = a.user_id
            LEFT JOIN users h ON o.hod_id = h.user_id
            LEFT JOIN departments d ON s.dept_id = d.dept_id
            WHERE o.outpass_id = %s AND o.student_id = %s
        """
        
        cursor.execute(query, (outpass_id, session['user_id']))
        outpass = cursor.fetchone()
        
        if not outpass:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Outpass not found'}), 404
        
        # Format datetime fields
        outpass['out_date'] = format_date(outpass['out_date'])
        outpass['out_time'] = format_time(outpass['out_time'])
        outpass['expected_return_time'] = format_time(outpass['expected_return_time'])
        outpass['created_at'] = format_datetime(outpass['created_at'])
        outpass['updated_at'] = format_datetime(outpass['updated_at'])
        outpass['advisor_action_time'] = format_datetime(outpass['advisor_action_time'])
        outpass['hod_action_time'] = format_datetime(outpass['hod_action_time'])
        outpass['qr_generated_at'] = format_datetime(outpass['qr_generated_at'])
        outpass['qr_expires_at'] = format_datetime(outpass['qr_expires_at'])
        outpass['actual_exit_time'] = format_datetime(outpass['actual_exit_time'])
        outpass['actual_entry_time'] = format_datetime(outpass['actual_entry_time'])
        
        # Get activity log
        cursor.execute("""
            SELECT 
                l.*,
                u.full_name as action_by_name,
                u.role as action_by_role
            FROM outpass_logs l
            JOIN users u ON l.action_by = u.user_id
            WHERE l.outpass_id = %s
            ORDER BY l.created_at DESC
        """, (outpass_id,))
        
        logs = cursor.fetchall()
        for log in logs:
            log['created_at'] = format_datetime(log['created_at'])
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'outpass': outpass,
            'logs': logs
        }), 200
        
    except Exception as e:
        print(f"Get outpass details error: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch outpass details'}), 500

@student_bp.route('/cancel-outpass/<int:outpass_id>', methods=['POST'])
@role_required('student')
def cancel_outpass(outpass_id):
    """Cancel a pending outpass request"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Check if outpass exists and is cancelable
        cursor.execute("""
            SELECT * FROM outpasses 
            WHERE outpass_id = %s AND student_id = %s
        """, (outpass_id, session['user_id']))
        
        outpass = cursor.fetchone()
        
        if not outpass:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Outpass not found'}), 404
        
        if outpass['final_status'] not in ['pending']:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Cannot cancel this outpass'}), 400
        
        # Update status to rejected
        cursor.execute("""
            UPDATE outpasses 
            SET final_status = 'rejected',
                advisor_status = 'rejected',
                advisor_remarks = 'Cancelled by student'
            WHERE outpass_id = %s
        """, (outpass_id,))
        
        conn.commit()
        
        # Log action
        log_action(conn, outpass_id, session['user_id'], 'rejected', 
                  'Cancelled by student', get_client_ip())
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Outpass cancelled successfully'
        }), 200
        
    except Exception as e:
        print(f"Cancel outpass error: {e}")
        return jsonify({'success': False, 'message': 'Failed to cancel outpass'}), 500

@student_bp.route('/dashboard-stats', methods=['GET'])
@role_required('student')
def get_dashboard_stats():
    """Get dashboard statistics for student"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get counts by status
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN final_status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN final_status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN final_status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN final_status = 'used' THEN 1 ELSE 0 END) as used
            FROM outpasses
            WHERE student_id = %s
        """, (session['user_id'],))
        
        stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        print(f"Get stats error: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch statistics'}), 500

@student_bp.route('/delete-outpass/<int:outpass_id>', methods=['DELETE'])
@role_required('student')
def delete_outpass(outpass_id):
    """Delete an outpass record (for history cleanup)"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Check if outpass exists and belongs to this student
        cursor.execute("""
            SELECT * FROM outpasses 
            WHERE outpass_id = %s AND student_id = %s
        """, (outpass_id, session['user_id']))
        
        outpass = cursor.fetchone()
        
        if not outpass:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Outpass not found'}), 404
        
        # Allow deletion of any outpass by students for cleanup
        
        # Delete associated logs first (foreign key constraint)
        cursor.execute("DELETE FROM outpass_logs WHERE outpass_id = %s", (outpass_id,))
        
        # Delete the outpass
        cursor.execute("DELETE FROM outpasses WHERE outpass_id = %s", (outpass_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Outpass deleted successfully'
        }), 200
        
    except Exception as e:
        print(f"Delete outpass error: {e}")
        return jsonify({'success': False, 'message': 'Failed to delete outpass'}), 500