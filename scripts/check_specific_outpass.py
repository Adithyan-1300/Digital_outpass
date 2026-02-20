import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'mysql123'),
    'database': os.environ.get('DB_NAME', 'outpass_db'),
}

conn = mysql.connector.connect(**config)
cursor = conn.cursor(dictionary=True)

# Check the "relative function" outpass
cursor.execute("""
    SELECT outpass_id, reason, advisor_status, hod_status, final_status, qr_code,
           advisor_action_time, hod_action_time
    FROM outpasses
    WHERE reason LIKE '%relative%'
    ORDER BY created_at DESC
    LIMIT 1
""")

result = cursor.fetchone()
if result:
    print("Found 'relative function' outpass:")
    print(f"ID: {result['outpass_id']}")
    print(f"Reason: {result['reason']}")
    print(f"Advisor Status: {result['advisor_status']}")
    print(f"HOD Status: {result['hod_status']}")
    print(f"Final Status: {result['final_status']}")
    print(f"QR Code: {result['qr_code']}")
    print(f"Advisor Action Time: {result['advisor_action_time']}")
    print(f"HOD Action Time: {result['hod_action_time']}")
else:
    print("No outpass found with 'relative' in reason")

conn.close()
