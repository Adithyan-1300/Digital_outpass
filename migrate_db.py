import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from backend.config import get_db_connection

def migrate():
    conn = get_db_connection()
    if not conn:
        print("No DB connection")
        return
    cursor = conn.cursor()
    try:
        # Check if column exists
        cursor.execute("SHOW COLUMNS FROM outpasses LIKE 'return_date'")
        result = cursor.fetchone()
        if result:
            print("Column return_date already exists.")
        else:
            cursor.execute("ALTER TABLE outpasses ADD COLUMN return_date DATE AFTER out_date")
            conn.commit()
            print("Successfully added return_date to outpasses table.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    migrate()
