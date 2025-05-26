@echo off
echo Installing all dependencies...
pip install --upgrade pip
pip install flask
pip install flask-sqlalchemy
pip install flask-login
pip install flask-wtf
pip install werkzeug
pip install python-dotenv
pip install bcrypt
pip install reportlab
echo ✅ All dependencies installed!
pause
