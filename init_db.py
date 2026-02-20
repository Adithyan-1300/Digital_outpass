"""Script to initialize database schema and sample data without interactive prompt"""

from backend.config import init_db

if __name__ == '__main__':
    success = init_db()
    if success:
        print('[OK] Database initialized successfully')
    else:
        print('[ERROR] Database initialization failed')
