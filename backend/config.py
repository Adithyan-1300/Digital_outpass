"""
Smart Outpass Management System - Backend Configuration
Cleaned & Error-Free Version
"""

import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
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

# DATABASE CONFIGURATION
# Update 'password' to your actual MySQL root password 
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD'), 
    'database': os.environ.get('DB_NAME', 'outpass_db'),
}

# Ensure the database exists; create if missing
def ensure_database():
    """Create the database if it does not exist."""
    try:
        # Connect without specifying a database
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        conn.commit()
        cursor.close()
        conn.close()
        print(f"[OK] Ensured database '{DB_CONFIG['database']}' exists")
    except Exception as e:
        print(f"[ERROR] Could not ensure database exists: {e}")

# Connection Pool Initialization
connection_pool = None
try:
    ensure_database()
    connection_pool = pooling.MySQLConnectionPool(pool_name="outpass_pool", pool_size=5, **DB_CONFIG)
    print("[OK] Database connection pool created successfully")
except Exception as err:
    print(f"[WARNING] Database not ready: {err}")

def get_db_connection():
    """Returns a database connection from the pool or a direct connection."""
    try:
        if connection_pool:
            try:
                return connection_pool.get_connection()
            except Exception as pool_err:
                print(f"⚠️  Pool error: {pool_err}. Falling back to direct connection.")
        
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as err:
        print(f"[ERROR] Database connection error: {err}")
        return None

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