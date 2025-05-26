@echo off
title Installing Invoice Generator Dependencies
echo ====================================================
echo    Installing Invoice Generator Dependencies
echo ====================================================
echo.

echo 📦 Installing core dependencies...
pip install Flask==2.3.3
pip install Flask-SQLAlchemy==3.0.5
pip install Flask-Login==0.6.3
pip install Flask-WTF==1.1.1
pip install Werkzeug==2.3.7
pip install python-dotenv==1.0.0
pip install bcrypt==4.0.1

echo 📦 Installing optional dependencies...
pip install reportlab==4.0.4
pip install Flask-Limiter==3.5.0
pip install email-validator==2.0.0

echo ✅ Installation completed!
echo.
echo You can now run: start-invoice-generator.bat
pause
