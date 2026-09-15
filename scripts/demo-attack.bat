@echo off
REM ============================================================
REM Cyber Threat Visualizer - Attack Demo (Windows)
REM Run from: cmd.exe as Administrator
REM From: C:\Users\shari\cyber-threat-visualizer\backend
REM ============================================================

echo ============================================================
echo   CYBER THREAT VISUALIZER - ATTACK DEMO
echo ============================================================
echo.

REM Check if backend is running
curl -s http://localhost:8000/api/v1/stats >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Backend not running. Start services first:
    echo   scripts\start-all.bat
    pause
    exit /b 1
)

echo [OK] Backend is running
echo.
echo Opening Command Center: http://localhost:3000
echo Starting attack simulation in 3 seconds...
timeout /t 3 /nobreak >nul

REM Run DDoS simulation
echo [ATTACK] Starting SYN Flood DDoS simulation...
cd /d C:\Users\shari\cyber-threat-visualizer\backend
call .venv\Scripts\activate.bat
python scripts\simulate_ddos.py --target 192.168.1.100 --rate 5000 --duration 30

echo.
echo [DEMO COMPLETE]
echo Check the Command Center at http://localhost:3000
echo   - Globe should show RED arcs
echo   - Terminal log should show [INTERCEPT] entries
echo   - Threat Matrix should show DDoS/SYN_FLOOD
echo   - Red Alert should have flashed
echo.
echo Other simulations available:
echo   python scripts\simulate_portscan.py --target 192.168.1.100 --type syn
echo   python scripts\simulate_bruteforce.py --target 192.168.1.100 --service ssh
echo.
pause