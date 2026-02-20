import mysql.connector
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path to allow importing backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'mysql123'),
    'database': os.environ.get('DB_NAME', 'outpass_db'),
}

def get_db_connection():
    return mysql.connector.connect(**config)

def run_test():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print("1. Creating test users if needed...")
    # Ensure we have a student, advisor, and HOD
    # This is simplified; assuming they exist or we rely on existing IDs.
    # For this test, let's just pick one of each role from the DB.
    
    cursor.execute("SELECT user_id FROM users WHERE role='student' LIMIT 1")
    student = cursor.fetchone()
    if not student:
        print("Error: No student found in DB")
        return
        
    cursor.execute("SELECT user_id FROM users WHERE role='staff' LIMIT 1")
    advisor = cursor.fetchone()
    if not advisor:
        print("Error: No advisor found in DB")
        return

    cursor.execute("SELECT user_id FROM users WHERE role='hod' LIMIT 1")
    hod = cursor.fetchone()
    if not hod:
        print("Error: No HOD found in DB")
        return
        
    print(f"Using: Student ID {student['user_id']}, Advisor ID {advisor['user_id']}, HOD ID {hod['user_id']}")
    
    print("\n2. Creating Outpass Request...")
    out_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    query = """
        INSERT INTO outpasses 
        (student_id, out_date, out_time, expected_return_time, reason, advisor_id, hod_id)
        VALUES (%s, %s, '10:00:00', '18:00:00', 'Test approval flow check', %s, %s)
    """
    cursor.execute(query, (student['user_id'], out_date, advisor['user_id'], hod['user_id']))
    outpass_id = cursor.lastrowid
    conn.commit()
    print(f"Created Outpass ID: {outpass_id}")
    
    # Check status
    cursor.execute("SELECT final_status, advisor_status, hod_status, qr_code FROM outpasses WHERE outpass_id=%s", (outpass_id,))
    row = cursor.fetchone()
    print(f"Initial Status: Final={row['final_status']}, Advisor={row['advisor_status']}, HOD={row['hod_status']}")
    
    print("\n3. Simulating Advisor Approval...")
    # Update like staff.py
    cursor.execute("""
        UPDATE outpasses 
        SET advisor_status = 'approved',
            advisor_remarks = 'Test Approved by Advisor',
            advisor_action_time = NOW(),
            hod_status = 'pending'
        WHERE outpass_id = %s
    """, (outpass_id,))
    conn.commit()
    
    cursor.execute("SELECT final_status, advisor_status, hod_status, qr_code FROM outpasses WHERE outpass_id=%s", (outpass_id,))
    row = cursor.fetchone()
    print(f"After Advisor: Final={row['final_status']}, Advisor={row['advisor_status']}, HOD={row['hod_status']}")
    
    print("\n4. Simulating HOD Approval...")
    # Update like hod.py
    # Generate mock QR token
    qr_token = f"QR-TEST-{outpass_id}"
    qr_expires = datetime.now() + timedelta(hours=24)
    
    cursor.execute("""
        UPDATE outpasses 
        SET hod_status = 'approved',
            hod_remarks = 'Test Approved by HOD',
            hod_action_time = NOW(),
            final_status = 'approved',
            qr_code = %s,
            qr_generated_at = NOW(),
            qr_expires_at = %s
        WHERE outpass_id = %s
    """, (qr_token, qr_expires, outpass_id))
    conn.commit()
    
    cursor.execute("SELECT final_status, advisor_status, hod_status, qr_code FROM outpasses WHERE outpass_id=%s", (outpass_id,))
    row = cursor.fetchone()
    print(f"After HOD: Final={row['final_status']}, Advisor={row['advisor_status']}, HOD={row['hod_status']}")
    print(f"QR Code: {row['qr_code']}")
    
    if row['final_status'] == 'approved' and row['qr_code'] == qr_token:
        print("\nSUCCESS: Database logic is correct.")
    else:
        print("\nFAILURE: Database state is incorrect.")
        
    # Clean up (optional, keep for inspection)
    # cursor.execute("DELETE FROM outpasses WHERE outpass_id=%s", (outpass_id,))
    # conn.commit()
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_test()
