"""
HOD Routes
Handles HOD operations: final approval, department statistics, override approvals
"""

from flask import Blueprint, request, jsonify, session
from backend.config import get_db_connection
from backend.utils.helpers import (
    role_required, format_datetime, format_date, format_time,
    log_action, get_client_ip, generate_unique_qr_token, generate_qr_code,
    send_sms_notification, get_ist_now
)
from backend.utils.pdf_generator import generate_hod_monthly_report
from datetime import datetime, timedelta
from flask import Response

import re
hod_bp = Blueprint('hod', __name__, url_prefix='/api/hod')

@hod_bp.route('/pending-approvals', methods=['GET'])
@role_required('hod')
def get_pending_approvals():
    """Get all outpasses pending HOD approval for the department"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get HOD's department
        cursor.execute("SELECT dept_id FROM users WHERE user_id = %s", (session['user_id'],))
        hod_dept = cursor.fetchone()
        
        if not hod_dept:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Department not found'}), 404
        
        # Get pending requests for HOD's department
        query = """
            SELECT 
                o.*,
                s.full_name as student_name,
                s.registration_no,
                s.email as student_email,
                s.phone as student_phone,
                s.parent_name,
                s.parent_mobile,
                s.profile_image,
                a.full_name as advisor_name,
                d.dept_name
            FROM outpasses o
            JOIN users s ON o.student_id = s.user_id
            LEFT JOIN users a ON o.advisor_id = a.user_id
            LEFT JOIN departments d ON s.dept_id = d.dept_id
            WHERE o.hod_id = %s 
            AND o.hod_status = 'pending'
            AND o.advisor_status = 'approved'
            ORDER BY o.created_at ASC
        """
        
        cursor.execute(query, (session['user_id'],))
        requests = cursor.fetchall()
        
        # Format datetime fields
        for req in requests:
            req['out_date'] = format_date(req['out_date'])
            req['out_time'] = format_time(req['out_time'])
            req['expected_return_time'] = format_time(req['expected_return_time'])
            req['created_at'] = format_datetime(req['created_at'])
            req['advisor_action_time'] = format_datetime(req['advisor_action_time'])
            # Normalize profile image to clean relative path
            if req.get('profile_image'):
                img = req['profile_image'].replace('uploads/', '', 1).lstrip('/')
                req['profile_image'] = img
            else:
                req['profile_image'] = None
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'requests': requests
        }), 200
        
    except Exception as e:
        print(f"Get pending approvals error: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch pending approvals'}), 500

@hod_bp.route('/approve-final/<int:outpass_id>', methods=['POST'])
@role_required('hod')
def approve_final(outpass_id):
    """
    Give final approval to outpass and generate QR code
    Request body: {remarks}
    """
    try:
        data = request.get_json()
        remarks = data.get('remarks', 'Approved by HOD')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Fetch student and parent details for notification
        cursor.execute("""
            SELECT o.*, s.full_name as student_name, s.parent_mobile, d.dept_name
            FROM outpasses o
            JOIN users s ON o.student_id = s.user_id
            LEFT JOIN departments d ON s.dept_id = d.dept_id
            WHERE o.outpass_id = %s AND o.hod_id = %s
        """, (outpass_id, session['user_id']))
        outpass = cursor.fetchone()
        
        if not outpass:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Outpass not found or unauthorized'}), 404
        
        if outpass['hod_status'] != 'pending':
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Request already processed'}), 400
        
        if outpass['advisor_status'] != 'approved':
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Advisor has not approved this request'}), 400
        
        # Generate QR code token
        qr_token = generate_unique_qr_token(outpass_id)
        qr_expires = get_ist_now() + timedelta(hours=1)  # QR valid for 1 hour
        
        # Update outpass - HOD approval and generate QR
        cursor.execute("""
            UPDATE outpasses 
            SET hod_status = 'approved',
                hod_remarks = %s,
                hod_action_time = NOW(),
                final_status = 'approved',
                qr_code = %s,
                qr_generated_at = NOW(),
                qr_expires_at = %s
            WHERE outpass_id = %s
        """, (remarks, qr_token, qr_expires, outpass_id))
        
        conn.commit()
        
        # Log action
        log_action(conn, outpass_id, session['user_id'], 'hod_approved', 
                  remarks, get_client_ip())
        
        # Send notification to parent
        if outpass['parent_mobile']:
            message = (
                f"Dear Parent, your ward {outpass['student_name']}'s outpass "
                f"({outpass['dept_name']}) has been approved. "
                f"Departure: {outpass['out_date']} {format_time(outpass['out_time'])}."
            )
            send_sms_notification(outpass['parent_mobile'], message)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Outpass approved. QR code generated.',
            'qr_code': qr_token
        }), 200
        
    except Exception as e:
        print(f"Approve final error: {e}")
        return jsonify({'success': False, 'message': 'Failed to approve outpass'}), 500

@hod_bp.route('/reject-final/<int:outpass_id>', methods=['POST'])
@role_required('hod')
def reject_final(outpass_id):
    """
    Reject outpass at HOD level
    Request body: {remarks}
    """
    try:
        data = request.get_json()
        remarks = data.get('remarks', 'Rejected by HOD')
        
        if not remarks or remarks.strip() == '':
            return jsonify({'success': False, 'message': 'Remarks required for rejection'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Verify this HOD owns this request
        cursor.execute("""
            SELECT * FROM outpasses 
            WHERE outpass_id = %s AND hod_id = %s
        """, (outpass_id, session['user_id']))
        
        outpass = cursor.fetchone()
        
        if not outpass:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Outpass not found or unauthorized'}), 404
        
        if outpass['hod_status'] != 'pending':
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Request already processed'}), 400
        
        # Update outpass - HOD rejection
        cursor.execute("""
            UPDATE outpasses 
            SET hod_status = 'rejected',
                hod_remarks = %s,
                hod_action_time = NOW(),
                final_status = 'rejected'
            WHERE outpass_id = %s
        """, (remarks, outpass_id))
        
        conn.commit()
        
        # Log action
        log_action(conn, outpass_id, session['user_id'], 'hod_rejected', 
                  remarks, get_client_ip())
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Outpass rejected'
        }), 200
        
    except Exception as e:
        print(f"Reject final error: {e}")
        return jsonify({'success': False, 'message': 'Failed to reject outpass'}), 500

@hod_bp.route('/department-statistics', methods=['GET'])
@role_required('hod')
def get_department_statistics():
    """Get comprehensive statistics for the department"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get HOD's department
        cursor.execute("SELECT dept_id FROM users WHERE user_id = %s", (session['user_id'],))
        hod_dept = cursor.fetchone()
        
        if not hod_dept:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Department not found'}), 404
        
        dept_id = hod_dept['dept_id']
        
        # Total students in department
        cursor.execute("""
            SELECT COUNT(*) as total_students
            FROM users
            WHERE dept_id = %s AND role = 'student' AND is_active = TRUE
        """, (dept_id,))
        students = cursor.fetchone()
        
        # Outpass statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_outpasses,
                SUM(CASE WHEN o.final_status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN o.final_status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN o.final_status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN o.final_status = 'used' THEN 1 ELSE 0 END) as used
            FROM outpasses o
            JOIN users s ON o.student_id = s.user_id
            WHERE s.dept_id = %s
        """, (dept_id,))
        outpass_stats = cursor.fetchone()
        
        # Pending HOD approvals
        cursor.execute("""
            SELECT COUNT(*) as pending_hod
            FROM outpasses o
            JOIN users s ON o.student_id = s.user_id
            WHERE s.dept_id = %s AND o.hod_status = 'pending' AND o.advisor_status = 'approved'
        """, (dept_id,))
        pending_hod = cursor.fetchone()
        
        # Monthly trend (last 6 months)
        cursor.execute("""
            SELECT 
                DATE_FORMAT(o.created_at, '%%Y-%%m') as month,
                COUNT(*) as count
            FROM outpasses o
            JOIN users s ON o.student_id = s.user_id
            WHERE s.dept_id = %s
            AND o.created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(o.created_at, '%%Y-%%m')
            ORDER BY month DESC
        """, (dept_id,))
        monthly_trend = cursor.fetchall()
        
        # Top reasons for outpasses
        cursor.execute("""
            SELECT 
                reason,
                COUNT(*) as count
            FROM outpasses o
            JOIN users s ON o.student_id = s.user_id
            WHERE s.dept_id = %s
            GROUP BY reason
            ORDER BY count DESC
            LIMIT 5
        """, (dept_id,))
        top_reasons = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_students': students['total_students'],
                'pending_hod_approval': pending_hod['pending_hod'],
                'outpasses': outpass_stats,
                'monthly_trend': monthly_trend,
                'top_reasons': top_reasons
            }
        }), 200
        
    except Exception as e:
        print(f"Get department statistics error: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch statistics'}), 500

@hod_bp.route('/override-approval/<int:outpass_id>', methods=['POST'])
@role_required('hod')
def override_approval(outpass_id):
    """
    Emergency override - approve outpass even if advisor hasn't approved
    Request body: {remarks}
    """
    try:
        data = request.get_json()
        remarks = data.get('remarks', 'Emergency override by HOD')
        
        if not remarks or remarks.strip() == '':
            return jsonify({'success': False, 'message': 'Remarks required for override'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Verify outpass belongs to HOD's department and fetch details
        cursor.execute("""
            SELECT o.*, s.dept_id, s.full_name as student_name, s.parent_mobile, d.dept_name
            FROM outpasses o
            JOIN users s ON o.student_id = s.user_id
            JOIN users h ON h.user_id = %s
            LEFT JOIN departments d ON s.dept_id = d.dept_id
            WHERE o.outpass_id = %s AND s.dept_id = h.dept_id
        """, (session['user_id'], outpass_id))
        
        outpass = cursor.fetchone()
        
        if not outpass:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Outpass not found or unauthorized'}), 404
        
        # Generate QR code
        qr_token = generate_unique_qr_token(outpass_id)
        qr_expires = get_ist_now() + timedelta(hours=1)  # QR valid for 1 hour
        
        # Override approval
        cursor.execute("""
            UPDATE outpasses 
            SET advisor_status = 'approved',
                advisor_remarks = %s,
                hod_status = 'approved',
                hod_remarks = %s,
                hod_action_time = NOW(),
                final_status = 'approved',
                qr_code = %s,
                qr_generated_at = NOW(),
                qr_expires_at = %s
            WHERE outpass_id = %s
        """, ('Override approval by HOD', remarks, qr_token, qr_expires, outpass_id))
        
        conn.commit()
        
        # Log action
        log_action(conn, outpass_id, session['user_id'], 'hod_approved', 
                  f'OVERRIDE: {remarks}', get_client_ip())
        
        # Send notification to parent
        if outpass['parent_mobile']:
            message = (
                f"Emergency Update: Your ward {outpass['student_name']}'s outpass "
                f"({outpass['dept_name']}) has been approved by HOD (Emergency Override). "
                f"Departure: {outpass['out_date']} {format_time(outpass['out_time'])}."
            )
            send_sms_notification(outpass['parent_mobile'], message)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Emergency override approved. QR code generated.'
        }), 200
        
    except Exception as e:
        print(f"Override approval error: {e}")
        return jsonify({'success': False, 'message': 'Failed to override approval'}), 500

@hod_bp.route('/all-outpasses', methods=['GET'])
@role_required('hod')
def get_all_department_outpasses():
    """Get all outpasses for the department with filters"""
    try:
        status_filter = request.args.get('status')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get HOD's department
        cursor.execute("SELECT dept_id FROM users WHERE user_id = %s", (session['user_id'],))
        hod_dept = cursor.fetchone()
        
        if not hod_dept:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Department not found'}), 404
        
        # Build query
        query = """
            SELECT 
                o.*,
                s.full_name as student_name,
                s.registration_no,
                s.parent_mobile,
                a.full_name as advisor_name
            FROM outpasses o
            JOIN users s ON o.student_id = s.user_id
            LEFT JOIN users a ON o.advisor_id = a.user_id
            WHERE s.dept_id = %s
        """
        params = [hod_dept['dept_id']]
        
        if status_filter:
            query += " AND o.final_status = %s"
            params.append(status_filter)
        
        if from_date:
            query += " AND o.out_date >= %s"
            params.append(from_date)
        
        if to_date:
            query += " AND o.out_date <= %s"
            params.append(to_date)
        
        query += " ORDER BY o.created_at DESC LIMIT 100"
        
        cursor.execute(query, params)
        outpasses = cursor.fetchall()
        
        # Format dates
        for op in outpasses:
            op['out_date'] = format_date(op['out_date'])
            op['out_time'] = format_time(op['out_time'])
            op['expected_return_time'] = format_time(op['expected_return_time'])
            op['created_at'] = format_datetime(op['created_at'])
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'outpasses': outpasses
        }), 200
        
    except Exception as e:
        print(f"Get all outpasses error: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch outpasses'}), 500

@hod_bp.route('/download-history', methods=['GET'])
@role_required('hod')
def download_history():
    """Download monthly outpass history report for HOD"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get HOD's department
        cursor.execute("SELECT u.dept_id, d.dept_name FROM users u JOIN departments d ON u.dept_id = d.dept_id WHERE u.user_id = %s", (session['user_id'],))
        hod_info = cursor.fetchone()
        
        if not hod_info:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Department not found'}), 404
            
        dept_id = hod_info['dept_id']
        dept_name = hod_info['dept_name']
        
        # Get department name and records for current month
        # Improved query to join with users and get academic_year
        current_year = get_ist_now().year
        current_month = get_ist_now().month
        cursor.execute("""
            SELECT o.*, u.full_name as student_name, u.registration_no, u.academic_year, d.dept_name, a.full_name as advisor_name
            FROM outpasses o
            JOIN users u ON o.student_id = u.user_id
            JOIN departments d ON u.dept_id = d.dept_id
            LEFT JOIN users a ON o.advisor_id = a.user_id
            WHERE u.dept_id = %s 
            AND o.final_status IN ('approved', 'used')
            AND (
                (o.advisor_action_time IS NOT NULL AND MONTH(o.advisor_action_time) = %s AND YEAR(o.advisor_action_time) = %s)
                OR (o.hod_action_time IS NOT NULL AND MONTH(o.hod_action_time) = %s AND YEAR(o.hod_action_time) = %s)
            )
            ORDER BY u.academic_year ASC, o.out_date DESC
        """, (dept_id, current_month, current_year, current_month, current_year))
        records = cursor.fetchall()
        
        # Group by year logic
        # Assuming format like ABCD2023001 or 2023CSE001
        # We'll try to extract the 4-digit year from the registration number
        import re
        # current_year and current_month are already defined above
        # Academic year transition (assuming July start) - not strictly needed for grouping by academic_year column
        
        records_by_year = {} # Initialize as empty dict to allow dynamic keys
        
        for rec in records:
            rec['out_date'] = format_date(rec['out_date'])
            # Use academic_year if available, otherwise fallback to registration_no inference
            year_level = rec.get('academic_year')
            
            if not year_level:
                # Fallback to existing logic if academic_year is missing
                reg_no = rec.get('registration_no') or ''
                match = re.search(r'(\d{4})', reg_no)
                if match:
                    batch_year = int(match.group(1))
                    academic_start_year = current_year if current_month >= 7 else current_year - 1
                    calc_year = academic_start_year - batch_year + 1
                    year_level = min(max(calc_year, 1), 3) # Cap between 1 and 3
                else:
                    year_level = 0 # Unknown
            
            year_label = f"Year {year_level}" if year_level > 0 else "Unknown Year"
            
            if year_label not in records_by_year:
                records_by_year[year_label] = []
            records_by_year[year_label].append(rec)
     
        cursor.close()
        conn.close()
        
        now = get_ist_now()
        month_name = now.strftime('%B')
        year = now.strftime('%Y')
        
        pdf_bytes = generate_hod_monthly_report(dept_name, month_name, year, records_by_year)
        
        return Response(
            bytes(pdf_bytes),
            mimetype="application/pdf",
            headers={"Content-disposition": f"attachment; filename=Dept_Outpass_History_{month_name}_{year}.pdf"}
        )
        
    except Exception as e:
        print(f"Download history HOD error: {e}")
        return jsonify({'success': False, 'message': 'Failed to generate PDF history'}), 500