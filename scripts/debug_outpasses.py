import mysql.connector
import os
import sys
import json
from dotenv import load_dotenv
from datetime import date, timedelta, datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'mysql123'),
    'database': os.environ.get('DB_NAME', 'outpass_db'),
}

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return str(obj)
    raise TypeError ("Type %s not serializable" % type(obj))

def inspect_db():
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT outpass_id, student_id, advisor_status, hod_status, final_status, qr_code
        FROM outpasses
        ORDER BY outpass_id DESC
        LIMIT 5
    """)
    outpasses = cursor.fetchall()
    
    print(json.dumps(outpasses, default=json_serial, indent=2))
        
    conn.close()

if __name__ == "__main__":
    inspect_db()
