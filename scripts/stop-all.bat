@echo off
REM ============================================================
REM Cyber Threat Visualizer - Stop All Services (Windows)
REM ============================================================

echo ============================================================
echo   CYBER THREAT VISUALIZER - STOP ALL SERVICES
echo ============================================================
echo.

echo [INFO] Stopping services...

REM Kill Python processes
taskkill /F /IM python.exe /T 2>nul
echo [OK] Stopped Python processes

REM Kill Node processes
taskkill /F /IM node.exe /T 2>nul
echo [OK] Stopped Node.js processes

REM Stop Redis Docker container
docker stop redis 2>nul
docker rm redis 2>nul
echo [OK] Stopped Redis container

echo.
echo ============================================================
echo All services stopped.
echo ============================================================
pause