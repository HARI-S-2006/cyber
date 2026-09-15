<# 
.SYNOPSIS
    Runs attack simulations for the Cyber Threat Visualizer
.DESCRIPTION
    Runs various attack simulations (DDoS, Port Scan, Brute Force) to demonstrate the threat detection
.REQUIRES
    - Backend API running on port 8000
    - Frontend running on port 3000
    - Run as Administrator for packet capture
#>

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   CYBER THREAT VISUALIZER - ATTACK DEMO" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

# Check if backend is running
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/stats" -ErrorAction Stop
    Write-Host "[OK] Backend is running" -ForegroundColor Green
} catch {
    Write-Error "Backend not running. Start services first with: .\scripts\start-all.ps1"
    exit 1
}

Write-Host ""
Write-Host "Opening Command Center: http://localhost:3000" -ForegroundColor Cyan
Write-Host "Starting attack simulation in 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Run DDoS simulation
Write-Host ""
Write-Host "[ATTACK] Starting SYN Flood DDoS simulation..." -ForegroundColor Red
Set-Location "C:\Users\shari\cyber-threat-visualizer\backend"
. .venv\Scripts\Activate.ps1
python scripts\simulate_ddos.py --target 192.168.1.100 --rate 5000 --duration 30

Write-Host ""
Write-Host "[DEMO COMPLETE]" -ForegroundColor Green
Write-Host "Check the Command Center at http://localhost:3000" -ForegroundColor Cyan
Write-Host "  - Globe should show RED arcs" -ForegroundColor Red
Write-Host "  - Terminal log should show [INTERCEPT] entries" -ForegroundColor Yellow
Write-Host "  - Threat Matrix should show DDoS/SYN_FLOOD" -ForegroundColor Red
Write-Host "  - Red Alert should have flashed" -ForegroundColor Red
Write-Host ""
Write-Host "Other simulations available:" -ForegroundColor Cyan
Write-Host "  Port Scan:    python scripts\simulate_portscan.py --target 192.168.1.100 --type syn" -ForegroundColor Cyan
Write-Host "  Brute Force:  python scripts\simulate_bruteforce.py --target 192.168.1.100 --service ssh" -ForegroundColor Cyan
Write-Host ""
pause