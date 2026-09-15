<# 
.SYNOPSIS
    Complete setup and run guide for Cyber Threat Visualizer
.DESCRIPTION
    Step-by-step guide to start all services (Redis, Kafka, Zookeeper, Backend, Frontend) in separate terminals
#>

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   CYBER THREAT VISUALIZER - COMPLETE SETUP GUIDE" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

Write-Host "PREREQUISITES:" -ForegroundColor Yellow
Write-Host "1. Docker Desktop installed and running" -ForegroundColor White
Write-Host "2. Npcap installed with 'WinPcap API-compatible Mode' checked" -ForegroundColor White
Write-Host "3. Python 3.11+ installed" -ForegroundColor White
Write-Host "4. Node.js 20+ installed" -ForegroundColor White
Write-Host "5. PowerShell running as Administrator" -ForegroundColor White
Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "STEP 1: START INFRASTRUCTURE (Redis, Kafka, Zookeeper)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Write-Host "`nOpening Terminal 1: Docker Compose (Redis, Kafka, Zookeeper)..." -ForegroundColor Yellow
Write-Host "Run this in Terminal 1 (PowerShell as Administrator):" -ForegroundColor Yellow
Write-Host ""
Write-Host "  cd C:\Users\shari\cyber-threat-visualizer" -ForegroundColor White
Write-Host "  docker-compose up -d redis zookeeper kafka" -ForegroundColor White
Write-Host ""
Write-Host "Wait for all containers to show 'healthy' or 'running' status" -ForegroundColor Yellow
Write-Host "Run: docker ps  (should show 3 containers: redis, zookeeper, kafka)" -ForegroundColor White
Write-Host "Verify: redis-cli ping  (should return PONG)" -ForegroundColor White

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "STEP 2: START BACKEND API (Terminal 2)" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host "Run this in Terminal 2 (PowerShell as Administrator):" -ForegroundColor Yellow
Write-Host ""
Write-Host "  cd C:\Users\shari\cyber-threat-visualizer\backend" -ForegroundColor White
Write-Host "  . .venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  python -m backend.api.main" -ForegroundColor White
Write-Host ""
Write-Host "Wait for: 'Application startup complete' and 'Uvicorn running on http://127.0.0.1:8000'" -ForegroundColor Yellow
Write-Host "Verify: http://localhost:8000/docs  (should show Swagger UI)" -ForegroundColor White

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "STEP 3: START PACKET SNIFFER (Terminal 3)" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host "Run this in Terminal 3 (PowerShell as Administrator):" -ForegroundColor Yellow
Write-Host ""
Write-Host "  cd C:\Users\shari\cyber-threat-visualizer" -ForegroundColor White
Write-Host "  . .venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  python -m backend.sniffer.packet_sniffer --fallback" -ForegroundColor White
Write-Host ""
Write-Host "Wait for: 'Starting libpcap fallback on <interface>'" -ForegroundColor Yellow
Write-Host "Should see: '[INTERCEPT] 192.168.x.x:port -> 192.168.x.x:port [TCP] Flags:SYN Len:XX'" -ForegroundColor White

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "STEP 4: START FRONTEND (Terminal 4)" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host "Run this in Terminal 4:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  cd C:\Users\shari\cyber-threat-visualizer\frontend" -ForegroundColor White
Write-Host "  npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "Wait for: 'Local: http://localhost:3000'" -ForegroundColor Yellow

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "VERIFICATION CHECKLIST" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host "□ Docker: docker ps  (shows redis, zookeeper, kafka running)" -ForegroundColor White
Write-Host "□ Redis: redis-cli ping  ->  PONG" -ForegroundColor White
Write-Host "□ Backend: http://localhost:8000/docs  (shows Swagger UI)" -ForegroundColor White
Write-Host "□ Backend Health: http://localhost:8000/health  -> {'status':'healthy'}" -ForegroundColor White
Write-Host "□ Frontend: http://localhost:3000  (shows 3D globe)" -ForegroundColor White
Write-Host "□ WebSocket: ws://localhost:8000/ws/live (connects in browser)" -ForegroundColor White
Write-Host "□ Packet Sniffer: Shows [INTERCEPT] logs in terminal" -ForegroundColor White

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "ATTACK DEMO (Run AFTER all services are up)" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host "Run in a new terminal (PowerShell as Admin):" -ForegroundColor Yellow
Write-Host "  cd C:\Users\shari\cyber-threat-visualizer\backend" -ForegroundColor White
Write-Host "  . .venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  python scripts\simulate_ddos.py --target 192.168.1.100 --rate 5000 --duration 30" -ForegroundColor White
Write-Host ""
Write-Host "Watch: Globe turns RED, Terminal shows [INTERCEPT], Threat Matrix shows DDoS" -ForegroundColor Red

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "QUICK START COMMANDS (Copy-paste each in separate terminal)" -ForegroundColor Cyan
Write-Host "============================================================"

Write-Host "`n--- TERMINAL 1 (Infrastructure) ---" -ForegroundColor Yellow
Write-Host "cd C:\Users\shari\cyber-threat-visualizer" -ForegroundColor White
Write-Host "docker-compose up -d redis zookeeper kafka" -ForegroundColor White

Write-Host "`n--- TERMINAL 2 (Backend API) ---" -ForegroundColor Yellow
Write-Host "cd C:\Users\shari\cyber-threat-visualizer\backend" -ForegroundColor White
Write-Host ". .venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "python -m backend.api.main" -ForegroundColor White

Write-Host "`n--- TERMINAL 3 (Packet Sniffer) ---" -ForegroundColor Yellow
Write-Host "cd C:\Users\shari\cyber-threat-visualizer" -ForegroundColor White
Write-Host ". .venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "python -m backend.sniffer.packet_sniffer --fallback" -ForegroundColor White

Write-Host "`n--- TERMINAL 4 (Frontend) ---" -ForegroundColor Yellow
Write-Host "cd C:\Users\shari\cyber-threat-visualizer\frontend" -ForegroundColor White
Write-Host "npm run dev" -ForegroundColor White

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "VERIFICATION COMMANDS" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host "docker ps                          # Should show 3 containers" -ForegroundColor White
Write-Host "redis-cli ping                     # Should return PONG" -ForegroundColor White
Write-Host "curl http://localhost:8000/health  # Should return {'status':'healthy'}" -ForegroundColor White
Write-Host "open http://localhost:3000         # Opens 3D Globe dashboard" -ForegroundColor White
Write-Host "open http://localhost:8000/docs    # Shows FastAPI Swagger UI" -ForegroundColor White

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "TROUBLESHOOTING" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host "Redis connection failed?  -> docker restart redis" -ForegroundColor White
Write-Host "Kafka not ready?           -> Wait 30s, check: docker logs kafka" -ForegroundColor White
Write-Host "Backend 500 error?         -> Check backend logs, ensure Redis running" -ForegroundColor White
Write-Host "Frontend blank?            -> cd frontend && npm install && npm run dev" -ForegroundColor White
Write-Host "ModuleNotFoundError: backend -> Run from project root with PYTHONPATH" -ForegroundColor White
Write-Host "No packets captured?       -> Run as Admin, Npcap WinPcap mode ON" -ForegroundColor White
Write-Host "Frontend blank page?       -> cd frontend && rm -rf node_modules && npm install" -ForegroundColor White

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "ATTACK DEMO (Run AFTER all services are up)" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host "cd C:\Users\shari\cyber-threat-visualizer\backend" -ForegroundColor White
Write-Host ". .venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "python scripts\simulate_ddos.py --target 192.168.1.100 --rate 5000 --duration 30" -ForegroundColor White
Write-Host ""
Write-Host "Watch: Globe turns RED, Terminal shows [INTERCEPT], Threat Matrix shows DDoS" -ForegroundColor Red

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "ALL COMMANDS SAVED IN FILE: STARTUP_GUIDE.md" -ForegroundColor Cyan
Write-Host "============================================================"