@echo off
title Cyber Threat Visualizer - Backend API + Capture
cd /d C:\Users\shari\cyber-threat-visualizer\backend

echo Starting Cyber Threat Visualizer Backend...
echo API will be on http://localhost:8000
echo Packet capture will start on default interface
echo Press Ctrl+C to stop
echo.

REM Run API server and capture together
python -m uvicorn streaming.stream_manager:app --host 0.0.0.0 --port 8000 --log-level info &
python main.py --fallback -r redis://localhost:6379 --api-port 8000 --capture-only

pause