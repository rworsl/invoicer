REM start-invoice-generator.bat - Start the Invoice Generator on Windows
@echo off
title Invoice Generator - Windows
color 0A

echo.
echo ====================================================
echo    Invoice Generator - Windows Edition
echo ====================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python not found!
    echo.
    echo Please install Python 3.8+ from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo ✅ Python found

REM Check if app.py exists
if not exist app.py (
    echo ❌ ERROR: app.py not found!
    echo.
    echo Please make sure you have the fixed app.py file in this directory.
    echo You can copy it from the provided code.
    echo.
    pause
    exit /b 1
)

echo ✅ Application file found

REM Check if virtual environment exists, if not create it
if not exist venv (
    echo 📦 Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ❌ Failed to create virtual environment
        echo Continuing without virtual environment...
    ) else (
        echo ✅ Virtual environment created
    )
)

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo 🔄 Activating virtual environment...
    call venv\Scripts\activate.bat
    echo ✅ Virtual environment activated
)

REM Install required packages if needed
echo 📦 Checking dependencies...
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📥 Installing Flask...
    pip install Flask
)

python -c "import flask_sqlalchemy" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📥 Installing Flask-SQLAlchemy...
    pip install Flask-SQLAlchemy
)

python -c "import flask_login" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📥 Installing Flask-Login...
    pip install Flask-Login
)

python -c "import flask_wtf" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📥 Installing Flask-WTF...
    pip install Flask-WTF
)

python -c "import werkzeug" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📥 Installing Werkzeug...
    pip install Werkzeug
)

python -c "import dotenv" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📥 Installing python-dotenv...
    pip install python-dotenv
)

python -c "import bcrypt" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📥 Installing bcrypt...
    pip install bcrypt
)

echo ✅ Core dependencies checked

REM Try to install optional dependencies
echo 📦 Installing optional dependencies...
pip install reportlab >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ ReportLab installed - PDF generation enabled
) else (
    echo ⚠️  ReportLab not installed - PDF generation disabled
)

pip install flask-limiter >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Flask-Limiter installed - Rate limiting enabled
) else (
    echo ⚠️  Flask-Limiter not installed - Rate limiting disabled
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env configuration...
    (
        echo # Invoice Generator - Windows Configuration
        echo FLASK_ENV=development
        echo SECRET_KEY=dev-secret-key-for-windows-testing-change-in-production
        echo DATABASE_URL=sqlite:///invoices.db
        echo.
        echo # Security Settings ^(Development^)
        echo WTF_CSRF_TIME_LIMIT=3600
        echo SESSION_COOKIE_SECURE=False
        echo SESSION_COOKIE_HTTPONLY=True
        echo SESSION_COOKIE_SAMESITE=Lax
        echo.
        echo # Development Settings
        echo DEBUG=True
        echo TESTING=False
    ) > .env
    echo ✅ Configuration file created
)

REM Create necessary directories
if not exist logs mkdir logs >nul 2>&1
if not exist uploads mkdir uploads >nul 2>&1
if not exist static mkdir static >nul 2>&1

echo ✅ Directories ready

echo.
echo 🚀 Starting Invoice Generator...
echo.
echo 🌐 The application will be available at:
echo    http://localhost:5000
echo.
echo 🔑 Default login credentials:
echo    Admin: admin@invoicegen.com / SecureAdmin123!
echo    Test:  test@example.com / test123
echo.
echo 💡 Features:
echo    ✅ User registration and login
echo    ✅ Invoice creation and management  
echo    ✅ Multi-currency support
echo    ✅ Dashboard and tracking
echo    📄 PDF export ^(if ReportLab is installed^)
echo.
echo 🛑 To stop the server: Press Ctrl+C
echo.
echo ====================================================
echo.

REM Start the application
python app.py

REM If we get here, the app has stopped
echo.
echo ====================================================
echo    Application Stopped
echo ====================================================
echo.
pause

REM ==========================================
REM install-dependencies.bat - Install all dependencies
REM ==========================================

echo Creating dependency installer...
(
    echo @echo off
    echo title Installing Invoice Generator Dependencies
    echo echo ====================================================
    echo echo    Installing Invoice Generator Dependencies
    echo echo ====================================================
    echo echo.
    echo.
    echo echo 📦 Installing core dependencies...
    echo pip install Flask==2.3.3
    echo pip install Flask-SQLAlchemy==3.0.5
    echo pip install Flask-Login==0.6.3
    echo pip install Flask-WTF==1.1.1
    echo pip install Werkzeug==2.3.7
    echo pip install python-dotenv==1.0.0
    echo pip install bcrypt==4.0.1
    echo.
    echo echo 📦 Installing optional dependencies...
    echo pip install reportlab==4.0.4
    echo pip install Flask-Limiter==3.5.0
    echo pip install email-validator==2.0.0
    echo.
    echo echo ✅ Installation completed!
    echo echo.
    echo echo You can now run: start-invoice-generator.bat
    echo pause
) > install-dependencies.bat

echo ✅ Dependency installer created

REM ==========================================
REM test-installation.bat - Test if everything works
REM ==========================================

echo Creating installation tester...
(
    echo @echo off
    echo title Testing Invoice Generator Installation
    echo echo ====================================================
    echo echo    Testing Invoice Generator Installation
    echo echo ====================================================
    echo echo.
    echo.
    echo echo 🔍 Testing Python installation...
    echo python --version
    echo if %%errorlevel%% neq 0 ^(
    echo     echo ❌ Python not found!
    echo     pause
    echo     exit /b 1
    echo ^)
    echo echo ✅ Python found
    echo.
    echo echo 🔍 Testing Flask installation...
    echo python -c "import flask; print('Flask version:', flask.__version__)"
    echo if %%errorlevel%% neq 0 ^(
    echo     echo ❌ Flask not installed
    echo     echo Run: install-dependencies.bat
    echo     pause
    echo     exit /b 1
    echo ^)
    echo echo ✅ Flask working
    echo.
    echo echo 🔍 Testing SQLAlchemy...
    echo python -c "import flask_sqlalchemy; print('✅ SQLAlchemy working')"
    echo if %%errorlevel%% neq 0 ^(
    echo     echo ❌ SQLAlchemy not working
    echo ^)
    echo.
    echo echo 🔍 Testing Login Manager...
    echo python -c "import flask_login; print('✅ Login Manager working')"
    echo if %%errorlevel%% neq 0 ^(
    echo     echo ❌ Login Manager not working
    echo ^)
    echo.
    echo echo 🔍 Testing WTF Forms...
    echo python -c "import flask_wtf; print('✅ WTF Forms working')"
    echo if %%errorlevel%% neq 0 ^(
    echo     echo ❌ WTF Forms not working
    echo ^)
    echo.
    echo echo 🔍 Testing optional dependencies...
    echo python -c "import reportlab; print('✅ ReportLab working - PDF generation enabled')" 2^>nul ^|^| echo "⚠️  ReportLab not available - PDF generation disabled"
    echo python -c "import flask_limiter; print('✅ Flask-Limiter working - Rate limiting enabled')" 2^>nul ^|^| echo "⚠️  Flask-Limiter not available - Rate limiting disabled"
    echo.
    echo echo 🔍 Testing application startup...
    echo python -c "from app import app; print('✅ Application can start')"
    echo if %%errorlevel%% neq 0 ^(
    echo     echo ❌ Application startup failed
    echo     echo Check app.py file
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo echo ====================================================
    echo echo    ✅ Installation Test Complete!
    echo echo ====================================================
    echo echo.
    echo echo All tests passed! You can now run:
    echo echo start-invoice-generator.bat
    echo echo.
    echo pause
) > test-installation.bat

echo ✅ Installation tester created

REM ==========================================
REM README-WINDOWS.txt - Instructions
REM ==========================================

echo Creating Windows instructions...
(
    echo Invoice Generator - Windows Setup Instructions
    echo ==============================================
    echo.
    echo QUICK START:
    echo 1. Make sure you have Python 3.8+ installed
    echo 2. Copy the fixed app.py file to this directory
    echo 3. Run: start-invoice-generator.bat
    echo 4. Open browser to: http://localhost:5000
    echo.
    echo MANUAL SETUP:
    echo 1. Install dependencies: install-dependencies.bat
    echo 2. Test installation: test-installation.bat  
    echo 3. Start application: start-invoice-generator.bat
    echo.
    echo LOGIN CREDENTIALS:
    echo - Admin: admin@invoicegen.com / SecureAdmin123!
    echo - Test:  test@example.com / test123
    echo.
    echo FEATURES:
    echo ✅ User registration and login
    echo ✅ Invoice creation and management
    echo ✅ Multi-currency support ^(25+ currencies^)
    echo ✅ Dashboard and invoice tracking
    echo ✅ PDF export ^(if ReportLab is installed^)
    echo ✅ Security features ^(CSRF, rate limiting^)
    echo.
    echo TROUBLESHOOTING:
    echo.
    echo Q: "Python not found" error?
    echo A: Install Python from https://python.org/downloads/
    echo    Make sure to check "Add Python to PATH"
    echo.
    echo Q: "Module not found" errors?
    echo A: Run install-dependencies.bat
    echo.
    echo Q: "Permission denied" errors?
    echo A: Run Command Prompt as Administrator
    echo.
    echo Q: Port 5000 already in use?
    echo A: Stop other applications using port 5000
    echo    Or change port in app.py ^(last line^)
    echo.
    echo Q: Database errors?
    echo A: Delete invoices.db file and restart
    echo.
    echo NEXT STEPS:
    echo - Test all features on Windows
    echo - Create some sample invoices
    echo - Try PDF export ^(install ReportLab if needed^)
    echo - When ready, deploy to VPS using the VPS guides
    echo.
    echo FILES IN THIS PACKAGE:
    echo - app.py ^(main application^)
    echo - start-invoice-generator.bat ^(startup script^)
    echo - install-dependencies.bat ^(dependency installer^)
    echo - test-installation.bat ^(installation tester^)
    echo - README-WINDOWS.txt ^(this file^)
    echo.
    echo SUPPORT:
    echo If you encounter issues, check the error messages
    echo and refer to the troubleshooting section above.
    echo.
    echo Happy invoicing! 🧾
) > README-WINDOWS.txt

echo ✅ Windows instructions created

echo.
echo ====================================================
echo    Windows Setup Package Created!
echo ====================================================
echo.
echo 📁 Files created:
echo   ✅ start-invoice-generator.bat  ^(main startup script^)
echo   ✅ install-dependencies.bat     ^(dependency installer^)
echo   ✅ test-installation.bat        ^(installation tester^)
echo   ✅ README-WINDOWS.txt           ^(instructions^)
echo.
echo 🚀 Quick Start:
echo   1. Make sure you have the fixed app.py file
echo   2. Run: start-invoice-generator.bat
echo   3. Open: http://localhost:5000
echo.
echo 🔧 If you have issues:
echo   1. Run: install-dependencies.bat
echo   2. Run: test-installation.bat
echo   3. Check: README-WINDOWS.txt
echo.
pause