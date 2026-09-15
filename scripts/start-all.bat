@echo off
REM ============================================================
REM Cyber Threat Visualizer - Windows Startup Script (cmd.exe)
REM Run from: cmd.exe as Administrator
REM From: C:\Users\shari\cyber-threat-visualizer
REM ============================================================

echo ============================================================
echo   CYBER THREAT VISUALIZER - WINDOWS STARTUP
echo ============================================================
echo.

REM Check Administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running as Administrator
) else (
    echo [WARN] Not running as Administrator
    echo [WARN] Packet capture may not work without Admin privileges
    echo.
)

REM Check Docker
echo [INFO] Checking Docker...
docker --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Docker not found. Install Docker Desktop.
    pause
    exit /b 1
)
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker daemon not running. Start Docker Desktop.
    pause
    exit /b 1
)
echo [OK] Docker is running

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.11+
    pause
    exit /b 1
)
echo [OK] Python found

REM Check Node
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Install Node.js 20+
    pause
    exit /b 1
)
echo [OK] Node.js found

echo.
echo [INFO] Starting infrastructure services (Redis, Kafka, Zookeeper)...
docker-compose up -d redis zookeeper kafka

echo [INFO] Waiting for services to be healthy...
timeout /t 15 /nobreak >nul

REM Verify services
echo [INFO] Verifying services...
redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Redis is ready
) else (
    echo [WARN] Redis not ready yet
)

REM Check Kafka
docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Kafka is ready
) else (
    echo [WARN] Kafka not ready yet, may need more time
)

echo.
echo [INFO] Setting up Python environment...
cd /d C:\Users\shari\cyber-threat-visualizer\backend
if not exist .venv (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
echo [OK] Python dependencies ready

echo.
echo [INFO] Installing Node.js dependencies...
cd /d C:\Users\shari\cyber-threat-visualizer\frontend
if not exist node_modules (
    npm install --silent 2>nul
)
echo [OK] Node.js dependencies ready

echo.
echo [INFO] Building frontend...
npm run build
echo [OK] Frontend built

echo.
echo [INFO] Checking ML model...
if not exist C:\Users\shari\cyber-threat-visualizer\backend\ml\models\anomaly_detector.pkl (
    echo [INFO] Training ML model...
    cd /d C:\Users\shari\cyber-threat-visualizer\backend
    call .venv\Scripts\activate.bat
    python -c "
from ml.model import AnomalyDetector, ModelConfig, generate_synthetic_data
from pathlib import Path
detector = AnomalyDetector(ModelConfig())
X, y = generate_synthetic_data(5000, 0.05)
detector.fit(X)
Path('ml/models').mkdir(parents=True, exist_ok=True)
detector.save('ml/models/anomaly_detector.pkl')
print('Model trained and saved')
"
)
echo [OK] ML model ready

echo.
echo [INFO] Starting services...
echo.

REM ============================================================
REM START ALL 3 APPLICATION SERVICES IN SEPARATE WINDOWS
REM ============================================================

REM 1. Backend API
echo [1/3] Starting Backend API on http://localhost:8000...
start "Backend API - Port 8000" cmd /k "cd /d C:\Users\shari\cyber-threat-visualizer\backend && call .venv\Scripts\activate.bat && python -m backend.api.main"

REM Wait for backend to start
echo [INFO] Waiting for Backend API to start...
timeout /t 8 /nobreak >nul

REM Verify backend is responding
curl -s http://localhost:8000/api/v1/stats >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Backend API running on http://localhost:8000
) else (
    echo [WARN] Backend may still be starting... check the window
)

echo.

REM 2. Packet Sniffer
echo [2/3] Starting Packet Sniffer...
start "Packet Sniffer" cmd /k "cd /d C:\Users\shari\cyber-threat-visualizer && set PYTHONPATH=C:\Users\shari\cyber-threat-visualizer && call C:\Users\shari\cyber-threat-visualizer\backend\.venv\Scripts\activate.bat && python -m backend.sniffer.packet_sniffer --fallback"

timeout /t 3 /nobreak >nul
echo [OK] Packet Sniffer window opened

echo.

REM 3. Frontend Dev Server
echo [3/3] Starting Frontend Dev Server on http://localhost:3000...
start "Frontend - Port 3000" cmd /k "cd /d C:\Users\shari\cyber-threat-visualizer\frontend && npm run dev"

timeout /t 3 /nobreak >nul
echo [OK] Frontend Dev Server window opened

echo.
echo ============================================================
echo [SUCCESS] All services starting in separate windows!
echo ============================================================
echo.
echo Access Points:
echo   Command Center (3D Globe):  http://localhost:3000
echo   API Documentation (Swagger): http://localhost:8000/docs
echo   API Stats:                   http://localhost:8000/api/v1/stats
echo   WebSocket:                   ws://localhost:8000/ws/live
echo   Kafka UI:                    http://localhost:9101
echo.
echo Running Windows (4 windows should be open):
echo   1. Backend API        (Port 8000)
echo   2. Packet Sniffer     (Captures traffic)
echo   3. Frontend Dev       (Port 3000)
echo   4. Docker Infrastructure (Redis, Kafka, Zookeeper)
echo.
echo To test with live attack (in NEW Admin terminal):
echo   cd C:\Users\shari\cyber-threat-visualizer\backend
echo   python scripts\simulate_ddos.py --target 192.168.1.100 --rate 5000 --duration 30
echo.
echo To stop everything:
echo   scripts\stop-all.bat
echo   OR: docker-compose down
echo.
pause