import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables if .env exists
load_dotenv()

config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'mysql123'),
    'database': os.environ.get('DB_NAME', 'outpass_db'),
}

print(f"Attempting to connect with:")
print(f"Host: {config['host']}")
print(f"User: {config['user']}")
print(f"Password: {config['password']}")
print(f"Database: {config['database']}")

try:
    conn = mysql.connector.connect(**config)
    print("\nSUCCESS: Connection established!")
    conn.close()
except mysql.connector.Error as err:
    print(f"\nERROR: {err}")
    print("\nTroubleshooting tips:")
    if err.errno == 2003:
        print("- MySQL server might not be running.")
        print("- Hostname might be incorrect.")
    elif err.errno == 1045:
        print("- Password or Username is incorrect.")
    elif err.errno == 1049:
        print("- Database 'outpass_db' does not exist.")
except Exception as e:
    print(f"\nUNEXPECTED ERROR: {e}")
