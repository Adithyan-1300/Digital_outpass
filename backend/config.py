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
        return mysql.connector.connect(
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME"),
            port=int(os.environ.get("DB_PORT")),
            ssl_disabled=False
        )
    except Exception as e:
        print("Actual Error:", e)
        return None


# ================= INIT DB FUNCTION =================

def init_db():
    """Initializes schema and sample data."""
    conn = get_db_connection()
    if not conn:
        print("[ERROR] Cannot initialize DB: Ensure MySQL is running and credentials are correct")
        return False

    schema_path = os.path.join(BASE_DIR, 'database', 'schema.sql')
    sample_path = os.path.join(BASE_DIR, 'database', 'sample_data.sql')

    try:
        cursor = conn.cursor()
        
        # Execute Schema
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                for statement in f.read().split(';'):
                    if statement.strip():
                        cursor.execute(statement)
            print("[OK] Database schema initialized")
        
        # Execute Sample Data
        if os.path.exists(sample_path):
            with open(sample_path, 'r', encoding='utf-8') as f:
                for statement in f.read().split(';'):
                    if statement.strip():
                        try:
                            cursor.execute(statement)
                        except mysql.connector.Error:
                            pass # Skip duplicates
            print("[OK] Sample data loaded")

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Error during DB init: {e}")
        return False

# File Handling
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'pdf'}