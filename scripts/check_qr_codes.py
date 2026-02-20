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

# Get an approved outpass with QR code
cursor.execute("""
    SELECT outpass_id, qr_code, final_status, advisor_status, hod_status
    FROM outpasses
    WHERE final_status = 'approved'
    AND qr_code IS NOT NULL
    ORDER BY qr_generated_at DESC
    LIMIT 1
""")

result = cursor.fetchone()
if result:
    print(f"Found approved outpass:")
    print(f"ID: {result['outpass_id']}")
    print(f"QR Code: {result['qr_code']}")
    print(f"Advisor Status: {result['advisor_status']}")
    print(f"HOD Status: {result['hod_status']}")
    print(f"Final Status: {result['final_status']}")
    print(f"\nCopy this QR code to test manual entry:")
    print(f"{result['qr_code']}")
else:
    print("No approved outpass with QR code found.")
    print("\nTip: You need to:")
    print("1. Have an outpass approved by both Advisor and HOD")
    print("2. Clear browser cache if HOD approval isn't working")

conn.close()
