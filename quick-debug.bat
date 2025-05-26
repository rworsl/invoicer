
REM quick-debug.bat - Simple Windows debug script
@echo off
title Invoice Generator - Quick Debug
color 0E

echo.
echo ====================================================
echo    Invoice Generator - Quick Debug
echo ====================================================
echo.

REM Check if app.py exists
if not exist app.py (
    echo ❌ ERROR: app.py not found!
    echo.
    echo Current directory: %CD%
    echo.
    dir *.py
    echo.
    pause
    exit /b 1
)

echo ✅ Found app.py in %CD%

REM Check Python
echo.
echo 🐍 Testing Python...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python not found!
    pause
    exit /b 1
)
echo ✅ Python is working

REM Test Flask import
echo.
echo 🔍 Testing Flask...
python -c "import flask; print('Flask version:', flask.__version__)"
if %errorlevel% neq 0 (
    echo ❌ Flask not installed
    echo Installing Flask...
    pip install flask
)

REM Test other imports one by one
echo.
echo 🔍 Testing dependencies...
python -c "import flask_sqlalchemy; print('✅ SQLAlchemy OK')" || echo "❌ flask_sqlalchemy missing"
python -c "import flask_login; print('✅ Login OK')" || echo "❌ flask_login missing"
python -c "import flask_wtf; print('✅ WTF OK')" || echo "❌ flask_wtf missing"
python -c "import werkzeug; print('✅ Werkzeug OK')" || echo "❌ werkzeug missing"
python -c "import dotenv; print('✅ Dotenv OK')" || echo "❌ python-dotenv missing"

REM Install missing dependencies
echo.
echo 📦 Installing any missing dependencies...
pip install flask flask-sqlalchemy flask-login flask-wtf werkzeug python-dotenv bcrypt

REM Check port 5000
echo.
echo 🔍 Checking port 5000...
netstat -an | find "5000" | find "LISTENING" >nul
if %errorlevel% equ 0 (
    echo ⚠️  Port 5000 is already in use!
    echo You may need to stop other applications using port 5000
    echo.
) else (
    echo ✅ Port 5000 is available
)

REM Create minimal .env
echo.
echo 📝 Creating .env file...
(
    echo FLASK_ENV=development
    echo SECRET_KEY=test-secret-key
    echo DATABASE_URL=sqlite:///test.db
    echo DEBUG=True
) > .env
echo ✅ .env created

REM Try to import the app
echo.
echo 🧪 Testing app import...
python -c "from app import app; print('✅ App import successful')"
if %errorlevel% neq 0 (
    echo ❌ App import failed
    echo There might be an error in app.py
    pause
    exit /b 1
)

echo.
echo ====================================================
echo 🚀 Starting Application...
echo ====================================================
echo.
echo 🌐 Open browser to: http://localhost:5000
echo 🔑 Login: admin@invoicegen.com / SecureAdmin123!
echo.
echo ⚠️  Keep this window open!
echo 🛑 Press Ctrl+C to stop
echo.

REM Start the app
python app.py

echo.
echo ====================================================
echo Application stopped - Exit code: %errorlevel%
echo ====================================================
pause

REM ==========================================
REM Create test files
REM ==========================================

REM Create a super simple Flask test
echo.
echo Creating simple test files...

REM minimal-test.py
(
    echo from flask import Flask
    echo app = Flask^(__name__^)
    echo @app.route^('/'^)
    echo def home^(^):
    echo     return "^<h1^>Flask is working!^</h1^>^<p^>^<a href='/test'^>Test page^</a^>^</p^>"
    echo @app.route^('/test'^)
    echo def test^(^):
    echo     return "^<h1^>Test page works!^</h1^>^<p^>^<a href='/'^>Home^</a^>^</p^>"
    echo if __name__ == '__main__':
    echo     print^('Simple Flask test starting...'^)
    echo     print^('Open: http://localhost:5000'^)
    echo     app.run^(debug=True, port=5000^)
) > minimal-test.py

echo ✅ Created minimal-test.py

REM test-minimal.bat
(
    echo @echo off
    echo echo Testing minimal Flask app...
    echo echo Open browser to: http://localhost:5000
    echo echo Press Ctrl+C to stop
    echo python minimal-test.py
    echo pause
) > test-minimal.bat

echo ✅ Created test-minimal.bat

REM install-all.bat
(
    echo @echo off
    echo echo Installing all dependencies...
    echo pip install --upgrade pip
    echo pip install flask
    echo pip install flask-sqlalchemy
    echo pip install flask-login
    echo pip install flask-wtf
    echo pip install werkzeug
    echo pip install python-dotenv
    echo pip install bcrypt
    echo pip install reportlab
    echo echo ✅ All dependencies installed!
    echo pause
) > install-all.bat

echo ✅ Created install-all.bat

REM check-python.bat
(
    echo @echo off
    echo echo Python Information:
    echo python --version
    echo python -c "import sys; print^('Python path:', sys.executable^)"
    echo python -c "import sys; print^('Python version:', sys.version^)"
    echo echo.
    echo echo Testing basic imports:
    echo python -c "print^('Testing imports...'^); import os, sys, json; print^('✅ Basic imports work'^)"
    echo echo.
    echo echo Flask test:
    echo python -c "import flask; print^('✅ Flask works, version:', flask.__version__^)"
    echo echo.
    echo pause
) > check-python.bat

echo ✅ Created check-python.bat

echo.
echo ====================================================
echo    Debug Tools Created!
echo ====================================================
echo.
echo 📁 Available tools:
echo   🔍 quick-debug.bat      ^(run this first^)
echo   📦 install-all.bat      ^(install all dependencies^)
echo   🧪 test-minimal.bat     ^(test basic Flask^)
echo   🐍 check-python.bat     ^(check Python setup^)
echo   📄 minimal-test.py      ^(simple Flask app^)
echo.
echo 🚀 What to do now:
echo.
echo   1. If imports failed: install-all.bat
echo   2. If Python issues: check-python.bat  
echo   3. Test basic Flask: test-minimal.bat
echo   4. Try main app: quick-debug.bat
echo.
echo Let's start with the minimal test:
echo.
pause

echo Running minimal Flask test...
test-minimal.bat