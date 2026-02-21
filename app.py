"""
Smart Outpass Management System
Main Flask Application Entry Point
"""

from backend.config import app, init_db
from backend.routes.auth import auth_bp
from backend.routes.student import student_bp
from backend.routes.staff import staff_bp
from backend.routes.hod import hod_bp
from backend.routes.security import security_bp
from backend.routes.admin import admin_bp
from flask import send_from_directory
import os

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(hod_bp)
app.register_blueprint(security_bp)
app.register_blueprint(admin_bp)

# Serve frontend files
@app.route('/')
def index():
    """Serve the main frontend page"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return {'error': 'Resource not found'}, 404

@app.errorhandler(500)
def internal_error(error):
    return {'error': 'Internal server error'}, 500

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return {'status': 'ok', 'message': 'Smart Outpass System API is running'}, 200

if __name__ == '__main__':
    # Initialize database on first run
    print("=" * 60)
    print("Smart Outpass Management System")
    print("=" * 60)
    
    # Check if database should be initialized
    # initialize = input("Initialize database with schema and sample data? (yes/no): ").lower()
    initialize = 'yes'
    if initialize == 'yes':
        print("\nInitializing database...")
        if init_db():
            print("[OK] Database initialized successfully!")
        else:
            print("[ERROR] Database initialization failed. Check MySQL connection.")
            print("\nPlease ensure:")
            print("1. MySQL server is running")
            print("2. Database 'outpass_db' exists (or will be created)")
            print("3. Correct credentials in backend/config.py")
    
    print("\n" + "=" * 60)
    print("Starting Flask application...")
    print("=" * 60)
    print("\nDefault credentials:")
    print("Admin    - Username: admin       Password: password123")
    print("HOD CSE  - Username: hod_cse     Password: password123")
    print("Staff    - Username: staff_cse1  Password: password123")
    print("Security - Username: security1   Password: password123")
    print("Student  - Username: student1    Password: password123")
    print("\n" + "=" * 60)
    print("\n>>> APPLICATION RUNNING AT:")
    print("   http://localhost:5000")
    print("   http://127.0.0.1:5000")
    print("\n" + "=" * 60 + "\n")
    
    # Run application
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT",10000)),
        debug=False
    )
