@echo off
REM Deployment script for Broking Terminal V2 Backend (Windows)

echo 🚀 Starting deployment of Broking Terminal V2 Backend...

REM Check if environment file exists
if not exist .env (
    echo ❌ Error: .env file not found. Please create it from .env.example
    exit /b 1
)

REM Pull latest changes
echo 📥 Pulling latest changes...
git pull origin main

REM Build and run with Docker Compose
echo 🐳 Building Docker containers...
docker-compose -f docker-compose.prod.yml build

REM Stop existing containers
echo 🛑 Stopping existing containers...
docker-compose -f docker-compose.prod.yml down

REM Start new containers
echo ▶️ Starting new containers...
docker-compose -f docker-compose.prod.yml up -d

REM Wait for health check
echo 🏥 Waiting for health check...
timeout /t 30

REM Check health
curl -f http://localhost:8000/health
if %ERRORLEVEL% EQU 0 (
    echo ✅ Deployment successful!
    echo 🌐 API is available at: http://localhost:8000
    echo 📚 Documentation at: http://localhost:8000/docs
) else (
    echo ❌ Health check failed. Check logs:
    docker-compose -f docker-compose.prod.yml logs backend
    exit /b 1
)

echo 🎉 Deployment completed successfully!
