@echo off
REM Cyber Threat Visualizer - Windows Startup Script (cmd.exe version)
REM Run this from cmd.exe (Command Prompt) as Administrator, NOT PowerShell

echo.
echo ============================================================
echo   CYBER THREAT VISUALIZER - STARTUP SCRIPT (cmd.exe)
echo ============================================================
echo.

REM Check if running as Admin
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running as Administrator
) else (
    echo [WARN] Not running as Administrator
    echo [WARN] Packet capture may not work without Admin privileges
    echo.
)

REM Check if Redis is running
echo.
echo [INFO] Checking Redis...
redis-cli ping >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] Redis is running
) else (
    echo [WARN] Redis not detected. Starting Redis...
    start /b redis-server
    timeout /t 3 /nobreak >nul
    redis-cli ping >nul 2>&1
    if %errorlevel% == 0 (
        echo [OK] Redis started
    ) else (
        echo [ERROR] Failed to start Redis. Please start Redis manually.
        echo [INFO] You can install Redis via: winget install Redis.Redis
        pause
        exit /b 1
    )
)

echo.
echo [INFO] Installing Python dependencies...
cd /d C:\Users\shari\cyber-threat-visualizer\backend
pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)

echo.
echo [INFO] Installing Node.js dependencies...
cd /d C:\Users\shari\cyber-threat-visualizer\frontend
npm install --silent
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Node.js dependencies
    pause
    exit /b 1
)

cd /d C:\Users\shari\cyber-threat-visualizer

echo.
echo ============================================================
echo [SUCCESS] All dependencies installed!
echo ============================================================
echo.
echo Starting services in separate windows...
echo.

REM Start Redis (if not already running)
echo [1] Starting Redis...
start "Redis" cmd /k redis-server

REM Start Backend API
echo [2] Starting Backend API on http://localhost:8000...
start "Backend API - Port 8000" cmd /k "cd /d C:\Users\shari\cyber-threat-visualizer\backend && python -m api.main"

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start Packet Sniffer
echo [3] Starting Packet Sniffer...
start "Packet Sniffer" cmd /k "cd /d C:\Users\shari\cyber-threat-visualizer\backend && python -m sniffer.packet_sniffer --fallback"

REM Wait for sniffer to start
timeout /t 2 /nobreak >nul

REM Start Frontend
echo [4] Starting Frontend on http://localhost:3000...
start "Frontend - Port 3000" cmd /k "cd /d C:\Users\shari\cyber-threat-visualizer\frontend && npm run dev"

echo.
echo ============================================================
echo [SUCCESS] All services started in separate windows!
echo ============================================================
echo.
echo Access the Command Center at: http://localhost:3000
echo API Documentation at: http://localhost:8000/docs
echo.
echo Press Ctrl+C in each window to stop services.
echo.
pause