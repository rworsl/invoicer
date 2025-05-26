@echo off
title Invoice Generator - Debug Mode
color 0E

echo.
echo ====================================================
echo    Invoice Generator - Debug Mode
echo ====================================================
echo.

REM Check if app.py exists
if not exist app.py (
    echo ❌ ERROR: app.py not found!
    echo.
    echo Current directory: %CD%
    echo Files in directory:
    dir /b *.py
    echo.
    echo Please make sure app.py is in this directory.
    pause
    exit /b 1
)

echo ✅ Found app.py

REM Show Python version and location
echo 🐍 Python Information:
python --version
python -c "import sys; print('Python path:', sys.executable)"
echo.

REM Test basic imports first
echo 🔍 Testing basic Python imports...
python -c "
try:
    print('✅ Basic Python working')
    import sys
    print('✅ sys module working')
    import os
    print('✅ os module working')
    print('Python version:', sys.version_info[:2])
except Exception as e:
    print('❌ Basic import failed:', str(e))
    exit(1)
"

if %errorlevel% neq 0 (
    echo ❌ Basic Python imports failed!
    pause
    exit /b 1
)

echo.
echo 🔍 Testing Flask imports...
python -c "
try:
    import flask
    print('✅ Flask imported successfully')
    print('Flask version:', flask.__version__)
except Exception as e:
    print('❌ Flask import failed:', str(e))
    print('Installing Flask...')
    import subprocess
    subprocess.run(['pip', 'install', 'flask'])
"

echo.
echo 🔍 Testing app.py imports...
python -c "
try:
    print('Testing app.py imports...')
    
    # Test each import individually
    import flask
    print('✅ flask')
    
    from flask import Flask, render_template, redirect, url_for, flash, request, send_file, jsonify, session
    print('✅ flask components')
    
    from flask_sqlalchemy import SQLAlchemy
    print('✅ flask_sqlalchemy')
    
    from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
    print('✅ flask_login')
    
    from flask_wtf.csrf import CSRFProtect
    print('✅ flask_wtf')
    
    from werkzeug.security import generate_password_hash, check_password_hash
    print('✅ werkzeug')
    
    from datetime import datetime, timedelta
    print('✅ datetime')
    
    import os, secrets, re, io, logging, uuid
    print('✅ standard libraries')
    
    from dotenv import load_dotenv
    print('✅ dotenv')
    
    print('✅ All critical imports successful!')
    
except Exception as e:
    print('❌ Import error:', str(e))
    print('Error type:', type(e).__name__)
    import traceback
    traceback.print_exc()
"

if %errorlevel% neq 0 (
    echo.
    echo ❌ Import test failed! Installing missing dependencies...
    echo.
    pip install flask flask-sqlalchemy flask-login flask-wtf werkzeug python-dotenv
    echo.
    echo Dependencies installed. Testing again...
    python -c "from app import app; print('✅ App imports working')"
    if %errorlevel% neq 0 (
        echo ❌ Still having import issues
        pause
        exit /b 1
    )
)

echo.
echo 🔍 Testing app creation...
python -c "
try:
    print('Creating Flask app...')
    from app import app
    print('✅ Flask app created successfully')
    print('App name:', app.name)
    print('Debug mode:', app.debug)
except Exception as e:
    print('❌ App creation failed:', str(e))
    import traceback
    traceback.print_exc()
    exit(1)
"

if %errorlevel% neq 0 (
    echo ❌ App creation failed!
    pause
    exit /b 1
)

echo.
echo ====================================================
echo 🚀 Starting Flask Application...
echo ====================================================
echo.
echo 🌐 Application should be available at: http://localhost:5000
echo 🔑 Login: admin@invoicegen.com / SecureAdmin123!
echo.
echo ⚠️  IMPORTANT: Keep this window open!
echo    The app will close if you close this window.
echo.
echo 🛑 To stop: Press Ctrl+C in this window
echo.

REM Run with verbose output
python -u app.py

REM If we get here, app has stopped
echo.
echo ====================================================
echo    Application Stopped
echo ====================================================
echo.
echo The application has exited.
echo Exit code: %errorlevel%
echo.
echo Common reasons:
echo 1. Port 5000 already in use
echo 2. Import error
echo 3. Database error
echo 4. Configuration error
echo.
echo Check the output above for error messages.
echo.
pause

REM ==========================================
REM simple-test.py - Ultra simple test app
REM ==========================================

echo Creating simple test app...
(
    echo # simple-test.py - Ultra simple Flask app for testing
    echo from flask import Flask
    echo.
    echo app = Flask^(__name__^)
    echo.
    echo @app.route^('/'^)
    echo def hello^(^):
    echo     return '''
    echo     ^<h1^>Flask is Working!^</h1^>
    echo     ^<p^>If you can see this, Flask is working correctly.^</p^>
    echo     ^<p^>^<a href="/test"^>Test Page^</a^>^</p^>
    echo     '''
    echo.
    echo @app.route^('/test'^)
    echo def test^(^):
    echo     return '''
    echo     ^<h1^>Test Page^</h1^>
    echo     ^<p^>This is a test page.^</p^>
    echo     ^<p^>^<a href="/"^>Back to Home^</a^>^</p^>
    echo     '''
    echo.
    echo if __name__ == '__main__':
    echo     print^('Starting simple Flask app...'^)
    echo     print^('Open your browser to: http://localhost:5000'^)
    echo     print^('Press Ctrl+C to stop'^)
    echo     app.run^(debug=True, host='127.0.0.1', port=5000^)
) > simple-test.py

echo ✅ Simple test app created: simple-test.py

REM ==========================================
REM test-simple.bat - Test the simple app
REM ==========================================

echo Creating simple app tester...
(
    echo @echo off
    echo title Testing Simple Flask App
    echo echo ====================================================
    echo echo    Testing Simple Flask App
    echo echo ====================================================
    echo echo.
    echo echo This will test if Flask works at all.
    echo echo.
    echo echo 🚀 Starting simple test app...
    echo echo 🌐 Open browser to: http://localhost:5000
    echo echo 🛑 Press Ctrl+C to stop
    echo echo.
    echo python simple-test.py
    echo echo.
    echo echo Simple app stopped.
    echo pause
) > test-simple.bat

echo ✅ Simple app tester created: test-simple.bat

REM ==========================================
REM fix-common-issues.bat - Fix common problems
REM ==========================================

echo Creating issue fixer...
(
    echo @echo off
    echo title Fixing Common Issues
    echo echo ====================================================
    echo echo    Fixing Common Issues
    echo echo ====================================================
    echo echo.
    echo.
    echo echo 🔧 Checking for port conflicts...
    echo netstat -an ^| find "5000" ^| find "LISTENING"
    echo if %%errorlevel%% equ 0 ^(
    echo     echo ⚠️  Port 5000 is in use!
    echo     echo Try killing processes using port 5000:
    echo     echo netstat -ano ^| find "5000"
    echo     echo.
    echo ^) else ^(
    echo     echo ✅ Port 5000 is available
    echo ^)
    echo.
    echo echo 🔧 Updating pip...
    echo python -m pip install --upgrade pip
    echo.
    echo echo 🔧 Reinstalling Flask...
    echo pip uninstall flask -y
    echo pip install flask
    echo.
    echo echo 🔧 Installing missing dependencies...
    echo pip install flask-sqlalchemy flask-login flask-wtf werkzeug python-dotenv bcrypt
    echo.
    echo echo 🔧 Creating fresh .env file...
    echo ^(
    echo     echo FLASK_ENV=development
    echo     echo SECRET_KEY=test-secret-key
    echo     echo DATABASE_URL=sqlite:///test.db
    echo     echo DEBUG=True
    echo ^) ^> .env
    echo.
    echo echo ✅ Common issues fixed!
    echo echo.
    echo echo Try running: debug-start.bat
    echo pause
) > fix-common-issues.bat

echo ✅ Issue fixer created: fix-common-issues.bat

REM ==========================================
REM keep-alive.py - App that won't close
REM ==========================================

echo Creating keep-alive version...
(
    echo # keep-alive.py - Version that keeps running
    echo import signal
    echo import sys
    echo from flask import Flask
    echo.
    echo app = Flask^(__name__^)
    echo.
    echo @app.route^('/'^)
    echo def home^(^):
    echo     return '''
    echo     ^<h1^>Invoice Generator - Keep Alive Version^</h1^>
    echo     ^<p^>This version will keep running until you press Ctrl+C^</p^>
    echo     ^<p^>^<a href="/login"^>Login^</a^> ^| ^<a href="/register"^>Register^</a^>^</p^>
    echo     '''
    echo.
    echo @app.route^('/login'^)
    echo def login^(^):
    echo     return '''
    echo     ^<h1^>Login Page^</h1^>
    echo     ^<p^>This would be the login page^</p^>
    echo     ^<p^>^<a href="/"^>Back to Home^</a^>^</p^>
    echo     '''
    echo.
    echo @app.route^('/register'^)
    echo def register^(^):
    echo     return '''
    echo     ^<h1^>Register Page^</h1^>
    echo     ^<p^>This would be the registration page^</p^>
    echo     ^<p^>^<a href="/"^>Back to Home^</a^>^</p^>
    echo     '''
    echo.
    echo def signal_handler^(sig, frame^):
    echo     print^('\nShutting down gracefully...'^)
    echo     sys.exit^(0^)
    echo.
    echo if __name__ == '__main__':
    echo     signal.signal^(signal.SIGINT, signal_handler^)
    echo     print^('=='*25^)
    echo     print^('   Keep-Alive Flask App'^)
    echo     print^('=='*25^)
    echo     print^('🌐 Open browser to: http://localhost:5000'^)
    echo     print^('🛑 Press Ctrl+C to stop gracefully'^)
    echo     print^('=='*25^)
    echo     try:
    echo         app.run^(debug=True, host='127.0.0.1', port=5000, use_reloader=False^)
    echo     except KeyboardInterrupt:
    echo         print^('\nApplication stopped by user'^)
    echo     except Exception as e:
    echo         print^(f'\nApplication error: {e}'^)
    echo         input^('Press Enter to continue...'^)
) > keep-alive.py

echo ✅ Keep-alive version created: keep-alive.py

echo.
echo ====================================================
echo    Debug Package Created!
echo ====================================================
echo.
echo 📁 Files created:
echo   🔍 debug-start.bat        ^(detailed debugging^)
echo   🧪 simple-test.py         ^(ultra simple Flask test^)
echo   🧪 test-simple.bat        ^(run simple test^)
echo   🔧 fix-common-issues.bat  ^(fix common problems^)
echo   💪 keep-alive.py          ^(version that stays running^)
echo.
echo 🚀 Troubleshooting steps:
echo.
echo   1. FIRST: debug-start.bat
echo      ^(this will show you exactly what's failing^)
echo.
echo   2. IF Flask fails: test-simple.bat
echo      ^(test if Flask works at all^)
echo.
echo   3. IF imports fail: fix-common-issues.bat
echo      ^(reinstall everything^)
echo.
echo   4. IF app keeps closing: python keep-alive.py
echo      ^(version that won't auto-close^)
echo.
echo Start with: debug-start.bat
echo This will show you exactly what's going wrong!
echo.
pause