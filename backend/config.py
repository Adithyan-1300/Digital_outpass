"""
Smart Outpass Management System - Backend Configuration
Cleaned & Error-Free Version
"""

import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
import mysql.connector
from datetime import timedelta

# Load environment variables
load_dotenv()

# Base directory setup
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'frontend'), static_url_path='')
CORS(app)

# Security Config
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-123')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# ================= DATABASE CONNECTION =================

def get_db_connection():
    try:
        # Get connection parameters with safe defaults
        db_host = os.environ.get("DB_HOST", "localhost")
        db_user = os.environ.get("DB_USER", "root")
        db_password = os.environ.get("DB_PASSWORD", "")
        db_name = os.environ.get("DB_NAME", "outpass_db")
        db_port = os.environ.get("DB_PORT", "3306")
        
        # Ensure port is an integer
        try:
            db_port = int(db_port)
        except (ValueError, TypeError):
            db_port = 3306

        return mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            port=db_port,
            ssl_disabled=False,
            autocommit=True,
            connection_timeout=10
        )
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return None


# ================= INIT DB FUNCTION =================

def init_db():
    """Initializes schema and sample data safely."""
    conn = get_db_connection()
    if not conn:
        print("[ERROR] Cannot initialize DB: Connection failed")
        return False

    schema_path = os.path.join(BASE_DIR, 'database', 'schema.sql')
    sample_path = os.path.join(BASE_DIR, 'database', 'sample_data.sql')

    try:
        cursor = conn.cursor()
        
        # Execute Schema
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Split by semicolon but ignore empty statements
                statements = [s.strip() for s in content.split(';') if s.strip()]
                for statement in statements:
                    try:
                        cursor.execute(statement)
                    except mysql.connector.Error as err:
                        if err.errno in [1060, 1061]: # Duplicate column/key
                            pass # Silently ignore duplicates
                        else:
                            print(f"[WARN] Schema statement failed: {err.msg}")
            print("[OK] Database schema verified/initialized")
        
        # Execute Sample Data Only if no users exist (to prevent duplicates on every restart)
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
        except:
            user_count = 0
        
        if user_count == 0 and os.path.exists(sample_path):
            with open(sample_path, 'r', encoding='utf-8') as f:
                content = f.read()
                statements = [s.strip() for s in content.split(';') if s.strip()]
                for statement in statements:
                    try:
                        cursor.execute(statement)
                    except mysql.connector.Error as err:
                        print(f"[WARN] Sample data statement failed: {err.msg}")
            print("[OK] Sample data loaded (first time setup)")
        else:
            print("[INFO] Skipping sample data (database already contains data)")

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Error during DB init: {e}")
        if conn:
            conn.close()
        return False

# File Handling
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'pdf'}