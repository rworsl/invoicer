Invoice Generator - Windows Setup Instructions
==============================================

QUICK START:
1. Make sure you have Python 3.8+ installed
2. Copy the fixed app.py file to this directory
3. Run: start-invoice-generator.bat
4. Open browser to: http://localhost:5000

MANUAL SETUP:
1. Install dependencies: install-dependencies.bat
2. Test installation: test-installation.bat  
3. Start application: start-invoice-generator.bat

LOGIN CREDENTIALS:
- Admin: admin@invoicegen.com / SecureAdmin123!
- Test:  test@example.com / test123

FEATURES:
✅ User registration and login
✅ Invoice creation and management
✅ Multi-currency support (25+ currencies)
✅ Dashboard and invoice tracking
✅ PDF export (if ReportLab is installed)
✅ Security features (CSRF, rate limiting)

TROUBLESHOOTING:

Q: "Python not found" error?
A: Install Python from https://python.org/downloads/
   Make sure to check "Add Python to PATH"

Q: "Module not found" errors?
A: Run install-dependencies.bat

Q: "Permission denied" errors?
A: Run Command Prompt as Administrator

Q: Port 5000 already in use?
A: Stop other applications using port 5000
   Or change port in app.py (last line)

Q: Database errors?
A: Delete invoices.db file and restart

NEXT STEPS:
- Test all features on Windows
- Create some sample invoices
- Try PDF export (install ReportLab if needed)
- When ready, deploy to VPS using the VPS guides

FILES IN THIS PACKAGE:
- app.py (main application)
- start-invoice-generator.bat (startup script)
- install-dependencies.bat (dependency installer)
- test-installation.bat (installation tester)
- README-WINDOWS.txt (this file)

SUPPORT:
If you encounter issues, check the error messages
and refer to the troubleshooting section above.

Happy invoicing! 🧾
