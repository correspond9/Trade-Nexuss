@echo off
REM Quick Setup Script for Windows VPS Deployment

echo 🚀 Broking Terminal V2 - Quick Windows VPS Setup
echo ================================================

REM Check if Docker is installed
docker --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Docker not found. Please install Docker Desktop first.
    echo Download from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Check if Git is installed
git --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Git not found. Please install Git first.
    echo Download from: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM Get repository URL
set /p REPO_URL="Enter your Git repository URL: "

if "%REPO_URL%"=="" (
    echo ❌ Repository URL is required.
    pause
    exit /b 1
)

REM Clone repository
echo 📥 Cloning repository...
git clone "%REPO_URL%" broking-terminal
cd broking-terminal\data_server_backend

REM Setup environment file
if not exist .env (
    echo 📝 Setting up environment file...
    copy .env.production .env
    
    echo.
    echo ⚠️  Please edit .env file with your configuration:
    echo    - POSTGRES_PASSWORD (database password)
    echo    - DHAN_CLIENT_ID, DHAN_API_KEY, DHAN_API_SECRET
    echo    - SECRET_KEY (generate with: openssl rand -hex 32)
    echo    - VITE_API_URL (your domain or IP)
    echo.
    pause
    
    REM Check if .env has been modified
    findstr /C:"your_.*_here" .env >nul
    if %ERRORLEVEL% equ 0 (
        echo ⚠️  Some values still contain placeholders. Please update .env file.
        set /p continue_anyway="Continue anyway? (y/N): "
        if /i not "%continue_anyway%"=="y" exit /b 1
    )
) else (
    echo ℹ️ .env file already exists. Skipping environment setup.
)

REM Setup SSL
echo.
set /p has_domain="Do you have a domain name? (y/N): "

if /i "%has_domain%"=="y" (
    set /p DOMAIN_NAME="Enter your domain name: "
    
    if not "%DOMAIN_NAME%"=="" (
        echo 🔒 Setting up SSL for %DOMAIN_NAME%...
        
        REM Create SSL directory
        if not exist ssl mkdir ssl
        
        REM Generate self-signed certificate (for Windows, user needs to manually setup Let's Encrypt)
        echo 📝 Generating self-signed certificate...
        echo You should replace this with a proper certificate from Let's Encrypt or your CA.
        
        REM Create a simple self-signed certificate using PowerShell
        powershell -Command "cert = New-SelfSignedCertificate -DnsName '%DOMAIN_NAME%' -CertStoreLocation 'cert:\LocalMachine\My'; Export-Certificate -Cert $cert -FilePath 'ssl\cert.cer'; Export-PfxCertificate -Cert $cert -FilePath 'ssl\cert.pfx' -Password (ConvertTo-SecureString -String '' -Force -AsPlainText)" 2>nul
        
        if not exist ssl\cert.pem (
            REM Fallback: create placeholder files
            echo Creating placeholder SSL files...
            echo # Placeholder SSL certificate > ssl\cert.pem
            echo # Placeholder SSL key > ssl\key.pem
        )
        
        REM Update VITE_API_URL in .env
        powershell -Command "(Get-Content .env) -replace 'https://your-domain.com/api', 'https://%DOMAIN_NAME%/api' | Set-Content .env"
        echo ✅ SSL setup completed for %DOMAIN_NAME%
    )
) else (
    echo 🔒 Generating self-signed certificate...
    if not exist ssl mkdir ssl
    echo # Self-signed certificate placeholder > ssl\cert.pem
    echo # Self-signed key placeholder > ssl\key.pem
    echo ✅ Self-signed certificate generated
)

REM Create necessary directories
echo 📁 Creating directories...
if not exist logs mkdir logs
if not exist backups mkdir backups

REM Deploy application
echo 🚀 Deploying application...
call scripts\deploy.bat

REM Final instructions
echo.
echo ✅ Setup completed!
echo.
echo Next steps:
echo 1. Wait for containers to start (30-60 seconds)
echo 2. Check status: docker-compose -f docker-compose.prod.yml ps
echo 3. View logs: docker-compose -f docker-compose.prod.yml logs -f
echo 4. Test API: curl -k https://localhost/health
echo.
echo Useful commands:
echo - Backup: scripts\backup.bat
echo - Restart: docker-compose -f docker-compose.prod.yml restart
echo - Stop: docker-compose -f docker-compose.prod.yml down
echo - Update: git pull && scripts\deploy.bat
echo.
echo Documentation: VPS_DEPLOYMENT_GUIDE.md
pause
