@echo off
echo Fixing Flask-Limiter issue...

REM Kill any processes using port 5000
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000" ^| find "LISTENING"') do taskkill /f /pid %%a 2>nul

REM Install missing dependencies
pip install --quiet flask-limiter redis

REM Set environment variable to disable warnings
set FLASK_LIMITER_STORAGE_URI=memory://

REM Start with suppressed warnings
python -W ignore::UserWarning app.py

pause