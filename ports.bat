@echo off
title Port 5000 Conflict Fixer
echo ====================================================
echo    Port 5000 Conflict Fixer
echo ====================================================
echo.

echo 🔍 Checking what's using port 5000...
echo.

REM Check if port 5000 is in use
netstat -an | find ":5000" | find "LISTENING" >nul
if %errorlevel% equ 0 (
    echo ⚠️  Port 5000 is currently in use!
    echo.
    echo 📋 Processes using port 5000:
    netstat -ano | find ":5000"
    echo.
    
    echo 🔧 Attempting to free port 5000...
    for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000" ^| find "LISTENING"') do (
        echo Killing process ID: %%a
        taskkill /f /pid %%a 2>nul
        if !errorlevel! equ 0 (
            echo ✅ Process %%a terminated successfully
        ) else (
            echo ❌ Failed to terminate process %%a
        )
    )
    
    echo.
    echo 🔍 Checking port 5000 again...
    timeout /t 2 /nobreak >nul
    netstat -an | find ":5000" | find "LISTENING" >nul
    if %errorlevel% equ 0 (
        echo ❌ Port 5000 still in use. Manual intervention required.
        echo.
        echo 💡 Solutions:
        echo 1. Restart your computer
        echo 2. Use a different port (edit app.py, change port=5000 to port=5001)
        echo 3. Find and close the application using port 5000
        echo.
    ) else (
        echo ✅ Port 5000 is now free!
        echo.
        echo 🚀 You can now start the Invoice Generator:
        echo start-invoice-generator.bat
        echo.
    )
) else (
    echo ✅ Port 5000 is available!
    echo.
    echo The port conflict is not the issue.
    echo Other possible causes:
    echo 1. Import error in app.py
    echo 2. Database initialization error
    echo 3. Missing template files
    echo.
    echo 🔍 Run debug-startup.bat for detailed diagnosis
)

echo.
echo 📱 Alternative ports you can use:
echo - Port 5001: http://localhost:5001
echo - Port 8000: http://localhost:8000
echo - Port 3000: http://localhost:3000
echo.
echo To use a different port, edit app.py and change:
echo   app.run(port=5000)  →  app.run(port=5001)
echo.
pause