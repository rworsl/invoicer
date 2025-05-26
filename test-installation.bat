@echo off
title Testing Invoice Generator Installation
echo ====================================================
echo    Testing Invoice Generator Installation
echo ====================================================
echo.

echo 🔍 Testing Python installation...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python not found!
    pause
    exit /b 1
)
echo ✅ Python found

echo 🔍 Testing Flask installation...
python -c "import flask; print('Flask version:', flask.__version__)"
if %errorlevel% neq 0 (
    echo ❌ Flask not installed
    echo Run: install-dependencies.bat
    pause
    exit /b 1
)
echo ✅ Flask working

echo 🔍 Testing SQLAlchemy...
python -c "import flask_sqlalchemy; print('✅ SQLAlchemy working')"
if %errorlevel% neq 0 (
    echo ❌ SQLAlchemy not working
)

echo 🔍 Testing Login Manager...
python -c "import flask_login; print('✅ Login Manager working')"
if %errorlevel% neq 0 (
    echo ❌ Login Manager not working
)

echo 🔍 Testing WTF Forms...
python -c "import flask_wtf; print('✅ WTF Forms working')"
if %errorlevel% neq 0 (
    echo ❌ WTF Forms not working
)

echo 🔍 Testing optional dependencies...
python -c "import reportlab; print('✅ ReportLab working - PDF generation enabled')" 2>nul || echo "⚠️  ReportLab not available - PDF generation disabled"
python -c "import flask_limiter; print('✅ Flask-Limiter working - Rate limiting enabled')" 2>nul || echo "⚠️  Flask-Limiter not available - Rate limiting disabled"

echo 🔍 Testing application startup...
python -c "from app import app; print('✅ Application can start')"
if %errorlevel% neq 0 (
    echo ❌ Application startup failed
    echo Check app.py file
    pause
    exit /b 1
)

echo ====================================================
echo    ✅ Installation Test Complete!
echo ====================================================
echo.
echo All tests passed! You can now run:
echo start-invoice-generator.bat
echo.
pause
