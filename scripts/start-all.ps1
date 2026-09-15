<# 
.SYNOPSIS
    Starts all Cyber Threat Visualizer services in the correct order
.DESCRIPTION
    Opens 4 separate PowerShell windows in sequence:
    1. Redis (Docker)
    2. Backend API (FastAPI + ML)
    3. Packet Sniffer (Scapy fallback)
    4. Frontend (React + Vite + Three.js)
.REQUIRES
    - Run as Administrator (for packet capture)
    - Docker Desktop running
    - Npcap installed with WinPcap API-compatible mode
#>

# Check for Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Not running as Administrator - packet capture will fail"
    Write-Warning "Please re-run PowerShell as Administrator"
    Read-Host "Press Enter to continue anyway, or Ctrl+C to exit"
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   CYBER THREAT VISUALIZER - WINDOWS STARTUP (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

# Check Docker
Write-Host "[INFO] Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Docker not found" }
    Write-Host "[OK] Docker: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Error "Docker not found. Install Docker Desktop from https://docker.com"
    exit 1
}

docker info >$null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker daemon not running. Start Docker Desktop first."
    exit 1
}
Write-Host "[OK] Docker daemon running" -ForegroundColor Green

# Start infrastructure services
Write-Host ""
Write-Host "[INFO] Starting infrastructure services (Redis, Kafka, Zookeeper)..." -ForegroundColor Yellow
docker-compose up -d redis zookeeper kafka

Write-Host "[INFO] Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Verify Redis
Write-Host "[INFO] Verifying Redis..." -ForegroundColor Yellow
$redisOk = $false
for ($i = 1; $i -le 10; $i++) {
    if (redis-cli ping 2>$null | Select-String -Pattern "PONG") {
        Write-Host "[OK] Redis is ready" -ForegroundColor Green
        $redisOk = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $redisOk) { Write-Error "Redis failed to start"; exit 1 }

# Verify Kafka
$kafkaOk = $false
for ($i = 1; $i -le 15; $i++) {
    if (docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 2>$null) {
        Write-Host "[OK] Kafka is ready" -ForegroundColor Green
        $kafkaOk = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $kafkaOk) { Write-Warning "Kafka not ready yet, continuing anyway..." }

# Setup Python environment
Write-Host ""
Write-Host "[INFO] Setting up Python environment..." -ForegroundColor Yellow
Set-Location "C:\Users\shari\cyber-threat-visualizer\backend"
if (-not (Test-Path ".venv")) {
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}
& .venv\Scripts\Activate.ps1
pip install -q -r requirements.txt 2>$null
Write-Host "[OK] Python dependencies ready" -ForegroundColor Green

# Install Node dependencies
Write-Host ""
Write-Host "[INFO] Installing Node.js dependencies..." -ForegroundColor Yellow
Set-Location "C:\Users\shari\cyber-threat-visualizer\frontend"
if (-not (Test-Path "node_modules")) {
    npm install --silent 2>$null
}
Write-Host "[OK] Node.js dependencies ready" -ForegroundColor Green

Write-Host ""
Write-Host "[INFO] Building frontend..." -ForegroundColor Yellow
npm run build 2>$null
Write-Host "[OK] Frontend built" -ForegroundColor Green

# Train ML model if needed
if (-not (Test-Path "C:\Users\shari\cyber-threat-visualizer\backend\ml\models\anomaly_detector.pkl")) {
    Write-Host "[INFO] Training ML model..." -ForegroundColor Yellow
    Set-Location "C:\Users\shari\cyber-threat-visualizer\backend"
    $env:PYTHONPATH = "C:\Users\shari\cyber-threat-visualizer"
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
    Write-Host "[OK] ML model trained" -ForegroundColor Green
}

Write-Host ""
Write-Host "[INFO] Starting application services..." -ForegroundColor Yellow

# 1. Backend API
Write-Host "[1/3] Starting Backend API on http://localhost:8000..." -ForegroundColor Yellow
$backendCmd = "cd C:\Users\shari\cyber-threat-visualizer\backend; . .venv\Scripts\Activate.ps1; python -m backend.api.main"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -Verb RunAs

# Wait for backend to start
Start-Sleep -Seconds 5
$backendOk = $false
for ($i = 1; $i -le 10; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/stats" -ErrorAction Stop
        if ($LASTEXITCODE -eq 0) { $backendOk = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
}
if ($backendOk) { Write-Host "[OK] Backend API running on http://localhost:8000" -ForegroundColor Green }
else { Write-Warning "Backend may still be starting..." }

# 2. Packet Sniffer
Start-Sleep -Seconds 2
Write-Host "[2/3] Starting Packet Sniffer..." -ForegroundColor Yellow
$snifferCmd = "cd C:\Users\shari\cyber-threat-visualizer; . .venv\Scripts\Activate.ps1; python -m backend.sniffer.packet_sniffer --fallback"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $snifferCmd -Verb RunAs

# 3. Frontend
Start-Sleep -Seconds 2
Write-Host "[3/3] Starting Frontend on http://localhost:3000..." -ForegroundColor Yellow
$frontendCmd = "cd C:\Users\shari\cyber-threat-visualizer\frontend; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -Verb RunAs

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] All services starting in separate PowerShell windows!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "  Command Center:  http://localhost:3000" -ForegroundColor Cyan
Write-Host "  API Docs:        http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Live Stats:      http://localhost:8000/api/v1/stats" -ForegroundColor Cyan
Write-Host "  WebSocket:       ws://localhost:8000/ws/live" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C in each window to stop services." -ForegroundColor Yellow
Write-Host ""
Write-Host "Services are running in separate windows. Close this window when done." -ForegroundColor Yellow
Write-Host "Check the other PowerShell windows for service logs."