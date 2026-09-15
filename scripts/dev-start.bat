@echo off
REM Development startup script for Windows

echo 🚀 Starting Cyber Threat Visualizer Development Environment

REM Check for Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker is required but not installed. Aborting.
    exit /b 1
)

docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker Compose is required but not installed. Aborting.
    exit /b 1
)

REM Start Redis
echo 📦 Starting Redis...
docker-compose up -d redis

REM Wait for Redis
echo ⏳ Waiting for Redis...
:wait_redis
docker-compose exec redis redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 1 >nul
    goto wait_redis
)
echo ✅ Redis ready

REM Build and start backend
echo 🔧 Building backend...
docker-compose build backend

echo 🚀 Starting backend...
docker-compose up -d backend

REM Build and start frontend
echo 🎨 Building frontend...
docker-compose build frontend

echo 🚀 Starting frontend...
docker-compose up -d frontend

echo.
echo ✅ All services started!
echo.
echo 📊 Dashboard: http://localhost:3000
echo 🔌 API:       http://localhost:8000
echo 📝 API Docs:  http://localhost:8000/docs
echo.
echo 📋 View logs: docker-compose logs -f
echo 🛑 Stop:      docker-compose down

pause