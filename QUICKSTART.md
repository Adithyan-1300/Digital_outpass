# Quick Start Guide - Smart Outpass Management System

## 5-Minute Setup

### Step 1: Install MySQL (if not installed)
```bash
# Check if MySQL is installed
mysql --version

# If not installed, install MySQL
# Windows: Download from https://dev.mysql.com/downloads/installer/
# Mac: brew install mysql
# Linux: sudo apt-get install mysql-server
```

### Step 2: Create Database
```bash
# Login to MySQL
mysql -u root -p

# Create database
CREATE DATABASE outpass_db;
EXIT;
```

### Step 3: Install Python Dependencies
```bash
cd smart_outpass_system
pip install -r requirements.txt
```

### Step 4: Configure Database
Edit `backend/config.py`:
```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',          # Your MySQL username
    'password': '',          # Your MySQL password (leave empty if no password)
    'database': 'outpass_db',
}
```

### Step 5: Run Application
```bash
python app.py

# When prompted, type: yes
# This will create tables and add sample data
```

### Step 6: Access System
Open browser: **http://localhost:5000**

---

## Default Login Credentials

| Role | Username | Password | Description |
|------|----------|----------|-------------|
| Admin | admin | password123 | Full system access |
| HOD | hod_cse | password123 | Department head |
| Staff | staff_cse1 | password123 | Faculty advisor |
| Security | security1 | password123 | Gate security |
| Student | student1 | password123 | Regular student |

---

## Common Issues

### Issue: "Can't connect to MySQL server"
**Solution**:
```bash
# Check MySQL is running
# Windows: Services → MySQL → Start
# Mac: brew services start mysql
# Linux: sudo systemctl start mysql
```

### Issue: "Access denied for user"
**Solution**: Update password in `backend/config.py`

### Issue: "Port 5000 already in use"
**Solution**: Change port in `app.py`:
```python
app.run(host='0.0.0.0', port=5001, debug=True)
```

---

## Testing the System

### Test Workflow:
1. **Login as Student** (student1 / password123)
2. **Apply Outpass** → Fill form and submit
3. **Login as Staff** (staff_cse1 / password123)
4. **Approve Request** → Go to Pending Requests
5. **Login as HOD** (hod_cse / password123)
6. **Final Approval** → QR code generated
7. **Login as Student** → View QR Code
8. **Login as Security** (security1 / password123)
9. **Scan QR Code** → Enter QR code string to verify

---

## Project Structure

```
smart_outpass_system/
├── app.py                 # Run this to start
├── requirements.txt       # Python packages
├── README.md             # Full documentation
├── backend/              # Python Flask code
│   ├── config.py        # Database settings
│   ├── routes/          # API endpoints
│   └── utils/           # Helper functions
├── database/            # SQL files
│   ├── schema.sql      # Table structure
│   └── sample_data.sql # Test data
├── frontend/           # HTML/CSS/JS
│   ├── index.html     # Main page
│   ├── css/           # Styles
│   └── js/            # JavaScript
└── docs/              # Documentation
```

---

## Next Steps

After testing with sample data:

1. **Change Passwords**: Update all default passwords
2. **Add Real Users**: Use Admin panel to add users
3. **Configure Email**: Set up email notifications (optional)
4. **Backup Database**: Regular backups recommended
5. **Deploy**: Follow production deployment guide in README.md

---

## Support

- **Full Documentation**: `docs/DOCUMENTATION.md`
- **Setup Guide**: `README.md`
- **API Reference**: `docs/DOCUMENTATION.md`

## System Features Checklist

✅ Student registration and login
✅ Apply for outpass with validation
✅ Two-level approval (Advisor → HOD)
✅ QR code generation after approval
✅ QR code scanning and verification
✅ Exit/Entry logging
✅ Role-based dashboards
✅ Activity tracking
✅ Department statistics
✅ System reports
✅ User management

---

**System is ready to use! Start with the test credentials above.**