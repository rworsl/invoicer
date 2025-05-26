@echo off
echo =================================================
echo    Invoice Generator - Windows Setup
echo =================================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found! Please install Python 3.11+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✓ Python found

REM Check if Git is installed
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Git not found. Install from: https://git-scm.com/
)

REM Create project directory
if not exist "invoice-generator" (
    mkdir invoice-generator
)

cd invoice-generator

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Create requirements.txt if it doesn't exist
if not exist requirements.txt (
    echo Creating requirements.txt...
    (
        echo Flask==2.3.3
        echo Flask-SQLAlchemy==3.0.5
        echo Flask-Login==0.6.3
        echo Flask-WTF==1.1.1
        echo Flask-Limiter==3.5.0
        echo WTForms==3.0.1
        echo Werkzeug==2.3.7
        echo bcrypt==4.0.1
        echo cryptography==41.0.7
        echo reportlab==4.0.4
        echo python-dotenv==1.0.0
        echo email-validator==2.0.0
        echo gunicorn==21.2.0
    ) > requirements.txt
)

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file...
    (
        echo # Flask Configuration
        echo FLASK_ENV=development
        echo SECRET_KEY=dev-secret-key-change-in-production
        echo DATABASE_URL=sqlite:///invoices.db
        echo.
        echo # Security Settings
        echo WTF_CSRF_TIME_LIMIT=3600
        echo SESSION_COOKIE_SECURE=False
        echo SESSION_COOKIE_HTTPONLY=True
        echo SESSION_COOKIE_SAMESITE=Lax
        echo.
        echo # Development Settings
        echo DEBUG=True
        echo TESTING=False
    ) > .env
)

REM Create necessary directories
if not exist logs mkdir logs
if not exist uploads mkdir uploads
if not exist static\css mkdir static\css
if not exist static\js mkdir static\js
if not exist templates mkdir templates

echo.
echo =================================================
echo    Setup completed successfully!
echo =================================================
echo.
echo Next steps:
echo 1. Copy all the application files to this directory
echo 2. Run: start-windows.bat
echo 3. Open browser to: http://localhost:5000
echo.
echo Virtual environment is activated
echo To deactivate later, run: deactivate
echo.
pause

REM ============================================
REM start-windows.bat - Windows Start Script
REM ============================================
@echo off
echo =================================================
echo    Starting Invoice Generator
echo =================================================

REM Check if virtual environment exists
if not exist venv\Scripts\activate.bat (
    echo ERROR: Virtual environment not found!
    echo Please run setup-windows.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if app.py exists
if not exist app.py (
    echo ERROR: app.py not found!
    echo Please copy the application files to this directory
    pause
    exit /b 1
)

REM Start the application
echo Starting Flask application...
echo.
echo Application will be available at:
echo http://localhost:5000
echo.
echo Admin Login:
echo Email: admin@invoicegen.com
echo Password: SecureAdmin123!
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py

pause

REM ============================================
REM install-docker-windows.ps1 - Docker Setup for Windows
REM ============================================

# PowerShell script to install Docker Desktop on Windows
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "    Docker Desktop Installation for Windows" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Docker is already installed
try {
    $dockerVersion = docker --version
    Write-Host "✓ Docker is already installed: $dockerVersion" -ForegroundColor Green
    
    # Check if Docker is running
    try {
        docker ps | Out-Null
        Write-Host "✓ Docker is running" -ForegroundColor Green
    } catch {
        Write-Host "⚠ Docker is installed but not running" -ForegroundColor Yellow
        Write-Host "Please start Docker Desktop" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Docker not found. Installing Docker Desktop..." -ForegroundColor Yellow
    
    # Download Docker Desktop
    $dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
    $dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"
    
    Write-Host "Downloading Docker Desktop..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller -UseBasicParsing
        Write-Host "✓ Download completed" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Failed to download Docker Desktop" -ForegroundColor Red
        Write-Host "Please download manually from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    # Install Docker Desktop
    Write-Host "Installing Docker Desktop..." -ForegroundColor Yellow
    Write-Host "This may take several minutes..." -ForegroundColor Yellow
    
    try {
        Start-Process -FilePath $dockerInstaller -ArgumentList "install", "--quiet" -Wait -NoNewWindow
        Write-Host "✓ Docker Desktop installed successfully" -ForegroundColor Green
        
        # Clean up installer
        Remove-Item $dockerInstaller -Force
        
        Write-Host "" -ForegroundColor Yellow
        Write-Host "IMPORTANT:" -ForegroundColor Red
        Write-Host "1. You may need to restart your computer" -ForegroundColor Yellow
        Write-Host "2. Start Docker Desktop from the Start menu" -ForegroundColor Yellow
        Write-Host "3. Wait for Docker to start completely" -ForegroundColor Yellow
        Write-Host "4. Then run: docker-test-windows.bat" -ForegroundColor Yellow
        
    } catch {
        Write-Host "ERROR: Failed to install Docker Desktop" -ForegroundColor Red
        Write-Host "Please install manually from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    }
}

# Enable WSL 2 if needed
Write-Host "" -ForegroundColor Yellow
Write-Host "Checking WSL 2..." -ForegroundColor Yellow
try {
    $wslVersion = wsl --status
    Write-Host "✓ WSL is available" -ForegroundColor Green
} catch {
    Write-Host "⚠ WSL 2 may need to be enabled" -ForegroundColor Yellow
    Write-Host "Docker Desktop will guide you through this setup" -ForegroundColor Yellow
}

Write-Host "" -ForegroundColor Cyan
Write-Host "Setup completed!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Restart your computer if prompted" -ForegroundColor White
Write-Host "2. Start Docker Desktop" -ForegroundColor White
Write-Host "3. Run: docker-test-windows.bat" -ForegroundColor White

Read-Host "Press Enter to continue"

REM ============================================
REM docker-test-windows.bat - Test Docker Setup
REM ============================================
@echo off
echo =================================================
echo    Testing Docker Setup
echo =================================================

REM Check if Docker is available
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker not found!
    echo Please install Docker Desktop first
    echo Run: install-docker-windows.ps1
    pause
    exit /b 1
)

echo ✓ Docker found

REM Check if Docker is running
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and wait for it to start completely
    echo Look for the Docker whale icon in the system tray
    pause
    exit /b 1
)

echo ✓ Docker is running

REM Test Docker functionality
echo Testing Docker functionality...
docker run --rm hello-world >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker test failed!
    echo Please check Docker Desktop settings
    pause
    exit /b 1
)

echo ✓ Docker test passed

REM Check Docker Compose
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker Compose not found!
    echo Please update Docker Desktop
    pause
    exit /b 1
)

echo ✓ Docker Compose found

echo.
echo =================================================
echo    Docker setup is working correctly!
echo =================================================
echo.
echo You can now deploy the application using:
echo deploy-windows.bat
echo.
pause

REM ============================================
REM deploy-windows.bat - Deploy on Windows
REM ============================================
@echo off
echo =================================================
echo    Deploying Invoice Generator with Docker
echo =================================================

REM Check if Docker is running
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop first
    pause
    exit /b 1
)

REM Check if required files exist
if not exist docker-compose.yml (
    echo ERROR: docker-compose.yml not found!
    echo Please copy all application files to this directory
    pause
    exit /b 1
)

if not exist Dockerfile (
    echo ERROR: Dockerfile not found!
    echo Please copy all application files to this directory
    pause
    exit /b 1
)

REM Create necessary directories
if not exist logs mkdir logs
if not exist uploads mkdir uploads
if not exist backups mkdir backups
if not exist data mkdir data
if not exist ssl mkdir ssl

REM Generate SSL certificates if they don't exist
if not exist ssl\cert.pem (
    echo Generating SSL certificates...
    docker run --rm -v %cd%\ssl:/ssl alpine/openssl req -x509 -newkey rsa:4096 -nodes -out /ssl/cert.pem -keyout /ssl/key.pem -days 365 -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=localhost"
    if %errorlevel% neq 0 (
        echo WARNING: Could not generate SSL certificates
        echo You may need to generate them manually
    ) else (
        echo ✓ SSL certificates generated
    )
)

REM Generate secure secret key
echo Generating secure configuration...
for /f "delims=" %%i in ('docker run --rm python:3.11-alpine python -c "import secrets; print(secrets.token_urlsafe(32))"') do set SECRET_KEY=%%i

REM Update .env file for production
if exist .env (
    echo Updating .env for Docker deployment...
    (
        echo # Docker Production Configuration
        echo FLASK_ENV=production
        echo SECRET_KEY=%SECRET_KEY%
        echo DATABASE_URL=postgresql://invoice_user:secure_password@db:5432/invoice_db
        echo.
        echo # Security Settings
        echo WTF_CSRF_TIME_LIMIT=3600
        echo SESSION_COOKIE_SECURE=True
        echo SESSION_COOKIE_HTTPONLY=True
        echo SESSION_COOKIE_SAMESITE=Lax
        echo.
        echo # Production Settings
        echo DEBUG=False
        echo TESTING=False
    ) > .env.docker
) else (
    echo Creating .env.docker file...
    (
        echo # Docker Production Configuration
        echo FLASK_ENV=production
        echo SECRET_KEY=%SECRET_KEY%
        echo DATABASE_URL=postgresql://invoice_user:secure_password@db:5432/invoice_db
        echo.
        echo # Security Settings
        echo WTF_CSRF_TIME_LIMIT=3600
        echo SESSION_COOKIE_SECURE=True
        echo SESSION_COOKIE_HTTPONLY=True
        echo SESSION_COOKIE_SAMESITE=Lax
        echo.
        echo # Production Settings
        echo DEBUG=False
        echo TESTING=False
    ) > .env.docker
)

REM Build and start services
echo Building Docker images...
docker-compose build

if %errorlevel% neq 0 (
    echo ERROR: Docker build failed!
    echo Please check the error messages above
    pause
    exit /b 1
)

echo ✓ Docker images built successfully

echo Starting services...
docker-compose up -d

if %errorlevel% neq 0 (
    echo ERROR: Failed to start services!
    echo Please check the error messages above
    pause
    exit /b 1
)

REM Wait for services to start
echo Waiting for services to start...
timeout /t 30 /nobreak >nul

REM Check service health
echo Checking service health...
docker-compose ps

echo.
echo =================================================
echo    Deployment Completed!
echo =================================================
echo.
echo 📱 Application: https://localhost
echo 🔒 Admin Login: admin@invoicegen.com / SecureAdmin123!
echo 📊 Monitoring: http://localhost:9090 (if enabled)
echo.
echo 🔧 Management Commands:
echo   View logs: docker-compose logs -f
echo   Stop: docker-compose down
echo   Restart: docker-compose restart
echo.
echo 🛡️  Security Notes:
echo   ✓ SSL certificates generated
echo   ✓ Secure secret key generated
echo   ✓ Production configuration applied
echo   ⚠ Change default admin password after first login
echo.
echo Open your browser to: https://localhost
echo (You may see a security warning for self-signed certificates)
echo.
pause

REM ============================================
REM test-application.bat - Test the Application
REM ============================================
@echo off
echo =================================================
echo    Testing Invoice Generator Application
echo =================================================

REM Test if application is responding
echo Testing application connectivity...

REM Use curl if available, otherwise use PowerShell
curl --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Using curl for testing...
    curl -k -s -o nul -w "HTTP Status: %%{http_code}\n" https://localhost/
    if %errorlevel% equ 0 (
        echo ✓ Application is responding
    ) else (
        echo ✗ Application is not responding
    )
) else (
    echo Using PowerShell for testing...
    powershell -Command "try { $response = Invoke-WebRequest -Uri 'https://localhost' -SkipCertificateCheck -UseBasicParsing; Write-Host '✓ Application is responding - Status:' $response.StatusCode } catch { Write-Host '✗ Application is not responding -' $_.Exception.Message }"
)

REM Check Docker services
echo.
echo Checking Docker services...
docker-compose ps

REM Show recent logs
echo.
echo Recent application logs:
docker-compose logs --tail=20 web

echo.
echo =================================================
echo    Test Results
echo =================================================
echo.
echo If you see "✓ Application is responding", the app is working!
echo.
echo Access your application at:
echo https://localhost
echo.
echo Default admin credentials:
echo Email: admin@invoicegen.com
echo Password: SecureAdmin123!
echo.
echo If there are issues, check:
echo 1. Docker Desktop is running
echo 2. All containers are healthy: docker-compose ps
echo 3. Check logs: docker-compose logs
echo.
pause