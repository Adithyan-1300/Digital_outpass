"""
Security Routes
Handles security operations: QR code scanning, entry/exit logging
"""

from flask import Blueprint, request, jsonify, session
from backend.config import get_db_connection
from backend.utils.helpers import (
    role_required, format_datetime, format_date, format_time,
    log_action, get_client_ip, is_qr_valid
)
from datetime import datetime

security_bp = Blueprint('security', __name__, url_prefix='/api/security')

@security_bp.route('/scan-qr', methods=['POST'])
@role_required('security')
def scan_qr():
    """
    Scan and verify QR code for exit
    Request body: {qr_code}
    """
    try:
        data = request.get_json()
        qr_code = data.get('qr_code', '').strip()
        
        if not qr_code:
            return jsonify({'success': False, 'message': 'QR code required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Find outpass by QR code
        cursor.execute("""
            SELECT 
                o.*,
                s.full_name as student_name,
                s.registration_no,
                s.phone as student_phone,
                s.profile_image,
                d.dept_name,
                d.dept_code
            FROM outpasses o
            JOIN users s ON o.student_id = s.user_id
            LEFT JOIN departments d ON s.dept_id = d.dept_id
            WHERE o.qr_code = %s
        """, (qr_code,))
        
        outpass = cursor.fetchone()
        
        if not outpass:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Invalid QR code',
                'valid': False
            }), 404
        
        # Validate QR code
        is_valid, error_message = is_qr_valid(
            outpass['qr_code'],
            outpass['qr_expires_at'],
            outpass['is_qr_used']
        )
        
        if not is_valid:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': error_message,
                'valid': False
            }), 400
        
        # Check if outpass is approved
        if outpass['final_status'] != 'approved':
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': f'Outpass status: {outpass["final_status"]}',
                'valid': False
            }), 400
        
        # Check if outpass date is valid (today or future)
        outpass_date = outpass['out_date']
        if isinstance(outpass_date, str):
            outpass_date = datetime.strptime(outpass_date, '%Y-%m-%d').date()
        
        if outpass_date > datetime.now().date():
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Outpass is for a future date',
                'valid': False,
                'outpass_date': format_date(outpass_date)
            }), 400
        
        # Record exit
        cursor.execute("""
            UPDATE outpasses 
            SET actual_exit_time = NOW(),
                exit_security_id = %s,
                is_qr_used = TRUE,
                final_status = 'used'
            WHERE outpass_id = %s
        """, (session['user_id'], outpass['outpass_id']))
        
        conn.commit()
        
        # Log action
        log_action(conn, outpass['outpass_id'], session['user_id'], 'exit_scanned',
                  f'Student exited via QR scan', get_client_ip())
        
        cursor.close()
        conn.close()
        
        # Return success with student details
        return jsonify({
            'success': True,
            'valid': True,
            'message': 'Exit recorded successfully',
            'student': {
                'name': outpass['student_name'],
                'registration_no': outpass['registration_no'],
                'department': outpass['dept_name'],
                'phone': outpass['student_phone'],
                'profile_image': outpass['profile_image'].replace('uploads/', '', 1) if outpass.get('profile_image') else None
            },
            'outpass': {
                'outpass_id': outpass['outpass_id'],
                'out_date': format_date(outpass['out_date']),
                'out_time': format_time(outpass['out_time']),
                'expected_return_time': format_time(outpass['expected_return_time']),
                'destination': outpass['destination'],
                'reason': outpass['reason']
            }
        }), 200
        
    except Exception as e:
        print(f"Scan QR error: {e}")
        return jsonify({'success': False, 'message': 'Failed to process QR code'}), 500

@security_bp.route('/verify-qr', methods=['POST'])
@role_required('security')
def verify_qr():
    """
    Verify QR code without marking as used (for preview)
    Request body: {qr_code}
    """
    try:
        data = request.get_json()
        qr_code = data.get('qr_code', '').strip()
        
        if not qr_code:
            return jsonify({'success': False, 'message': 'QR code required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Find outpass by QR code
        cursor.execute("""
            SELECT 
                o.*,
                s.full_name as student_name,
                s.registration_no,
                s.phone as student_phone,
                s.profile_image,
                d.dept_name
            FROM outpasses o
            JOIN users s ON o.student_id = s.user_id
            LEFT JOIN departments d ON s.dept_id = d.dept_id
            WHERE o.qr_code = %s
        """, (qr_code,))
        
        outpass = cursor.fetchone()
        
        if not outpass:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Invalid QR code',
                'valid': False
            }), 404
        
        # Validate QR code
        is_valid, error_message = is_qr_valid(
            outpass['qr_code'],
            outpass['qr_expires_at'],
            outpass['is_qr_used']
        )
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'valid': is_valid,
            'message': error_message if not is_valid else 'QR code is valid',
            'student': {
                'name': outpass['student_name'],
                'registration_no': outpass['registration_no'],
                'department': outpass['dept_name'],
                'profile_image': outpass['profile_image'].replace('uploads/', '', 1) if outpass.get('profile_image') else None
            } if is_valid else None,
            'outpass': {
                'outpass_id': outpass['outpass_id'],
                'out_date': format_date(outpass['out_date']),
                'out_time': format_time(outpass['out_time']),
                'status': outpass['final_status']
            } if is_valid else None
        }), 200
        
    except Exception as e:
        print(f"Verify QR error: {e}")
        return jsonify({'success': False, 'message': 'Failed to verify QR code'}), 500

@security_bp.route('/record-entry', methods=['POST'])
@role_required('security')
def record_entry():
    """
    Record student entry (return) - manual or QR scan
    Request body: {outpass_id} or {qr_code}
    """
    try:
        data = request.get_json()
        outpass_id = data.get('outpass_id')
        qr_code = data.get('qr_code')
        
        if not outpass_id and not qr_code:
            return jsonify({'success': False, 'message': 'Outpass ID or QR code required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Find outpass
        if qr_code:
            cursor.execute("SELECT * FROM outpasses WHERE qr_code = %s", (qr_code,))
        else:
            cursor.execute("SELECT * FROM outpasses WHERE outpass_id = %s", (outpass_id,))
        
        outpass = cursor.fetchone()
        
        if not outpass:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Outpass not found'}), 404
        
        # Check if already exited
        if not outpass['actual_exit_time']:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Student has not exited yet'}), 400
        
        # Check if already returned
        if outpass['actual_entry_time']:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Entry already recorded'}), 400
        
        # Record entry
        cursor.execute("""
            UPDATE outpasses 
            SET actual_entry_time = NOW(),
                entry_security_id = %s
            WHERE outpass_id = %s
        """, (session['user_id'], outpass['outpass_id']))
        
        conn.commit()
        
        # Log action
        log_action(conn, outpass['outpass_id'], session['user_id'], 'entry_scanned',
                  'Student returned', get_client_ip())
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Entry recorded successfully'
        }), 200
        
    except Exception as e:
        print(f"Record entry error: {e}")
        return jsonify({'success': False, 'message': 'Failed to record entry'}), 500

@security_bp.route('/recent-activity', methods=['GET'])
@role_required('security')
def get_recent_activity():
    """Get recent exit/entry activity"""
    try:
        limit = request.args.get('limit', 20, type=int)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get recent exits and entries
        cursor.execute("""
            SELECT 
                o.outpass_id,
                o.actual_exit_time,
                o.actual_entry_time,
                s.full_name as student_name,
                s.registration_no,
                d.dept_name,
                o.reason,
                o.destination
            FROM outpasses o
            JOIN users s ON o.student_id = s.user_id
            LEFT JOIN departments d ON s.dept_id = d.dept_id
            WHERE o.actual_exit_time IS NOT NULL
            ORDER BY COALESCE(o.actual_entry_time, o.actual_exit_time) DESC
            LIMIT %s
        """, (limit,))
        
        activities = cursor.fetchall()
        
        # Format datetime
        for activity in activities:
            activity['actual_exit_time'] = format_datetime(activity['actual_exit_time'])
            activity['actual_entry_time'] = format_datetime(activity['actual_entry_time'])
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'activities': activities
        }), 200
        
    except Exception as e:
        print(f"Get recent activity error: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch activity'}), 500

@security_bp.route('/students-out', methods=['GET'])
@role_required('security')
def get_students_currently_out():
    """Get list of students currently outside (exited but not returned)"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                o.outpass_id,
                o.out_date,
                o.out_time,
                o.expected_return_time,
                o.actual_exit_time,
                s.full_name as student_name,
                s.registration_no,
                s.phone as student_phone,
                d.dept_name,
                o.destination
            FROM outpasses o
            JOIN users s ON o.student_id = s.user_id
            LEFT JOIN departments d ON s.dept_id = d.dept_id
            WHERE o.actual_exit_time IS NOT NULL 
            AND o.actual_entry_time IS NULL
            ORDER BY o.actual_exit_time DESC
        """)
        
        students = cursor.fetchall()
        
        # Format datetime
        for student in students:
            student['out_date'] = format_date(student['out_date'])
            student['out_time'] = format_time(student['out_time'])
            student['expected_return_time'] = format_time(student['expected_return_time'])
            student['actual_exit_time'] = format_datetime(student['actual_exit_time'])
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'students_out': students,
            'count': len(students)
        }), 200
        
    except Exception as e:
        print(f"Get students out error: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch students'}), 500

@security_bp.route('/dashboard-stats', methods=['GET'])
@role_required('security')
def get_security_stats():
    """Get dashboard statistics for security"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Students currently out
        cursor.execute("""
            SELECT COUNT(*) as students_out
            FROM outpasses
            WHERE actual_exit_time IS NOT NULL AND actual_entry_time IS NULL
        """)
        currently_out = cursor.fetchone()
        
        # Total exits today
        cursor.execute("""
            SELECT COUNT(*) as exits_today
            FROM outpasses
            WHERE DATE(actual_exit_time) = CURDATE()
        """)
        exits_today = cursor.fetchone()
        
        # Total entries today
        cursor.execute("""
            SELECT COUNT(*) as entries_today
            FROM outpasses
            WHERE DATE(actual_entry_time) = CURDATE()
        """)
        entries_today = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'students_currently_out': currently_out['students_out'],
                'exits_today': exits_today['exits_today'],
                'entries_today': entries_today['entries_today']
            }
        }), 200
        
    except Exception as e:
        print(f"Get stats error: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch statistics'}), 500