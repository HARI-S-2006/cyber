<# 
.SYNOPSIS
    Starts all Cyber Threat Visualizer services in the correct order
.DESCRIPTION
    Opens 4 separate PowerShell windows in sequence:
    1. Docker Infrastructure Monitor (Redis, Zookeeper, Kafka)
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

# Resolve project root dynamically
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Write-Host "[INFO] Project Root: $ProjectRoot" -ForegroundColor Yellow
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
Write-Host ""

# Check Python
Write-Host "[INFO] Checking Python..." -ForegroundColor Yellow
$pythonPath = "$ProjectRoot\backend\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonPath)) {
    Write-Host "[INFO] Python virtual environment not found. Will be created by backend script." -ForegroundColor Yellow
} else {
    $pyVersion = & $pythonPath --version
    Write-Host "[OK] Python: $pyVersion" -ForegroundColor Green
}

# Check Node.js
Write-Host "[INFO] Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "[OK] Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Error "Node.js not found. Install from https://nodejs.org"
    exit 1
}
Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   LAUNCHING 4 SERVICE WINDOWS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Clean up any existing project Docker resources first
Write-Host "[INFO] Cleaning up any existing project Docker resources..." -ForegroundColor Yellow
docker compose down -v 2>$null
Write-Host "[OK] Cleaned up" -ForegroundColor Green
Write-Host ""

# WINDOW 1: Docker Infrastructure Monitor
Write-Host "[1/4] Launching Docker Infrastructure Monitor..." -ForegroundColor Yellow
$infraScript = "$ProjectRoot\scripts\start-infrastructure.ps1"
if (-not (Test-Path $infraScript)) {
    Write-Error "Infrastructure script not found: $infraScript"
    exit 1
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$infraScript'" -WindowStyle Normal

Write-Host "[INFO] Waiting for infrastructure to become healthy..." -ForegroundColor Yellow

# Wait for infrastructure to be healthy (Redis, Zookeeper, Kafka)
$maxWait = 180
$elapsed = 0
$infraReady = $false

while ($elapsed -lt $maxWait -and -not $infraReady) {
    $containers = docker ps --filter "name=cyber-threat-" --format "{{.Status}}"
    $allHealthy = $true
    $runningCount = 0
    
    if ($containers) {
        foreach ($status in $containers) {
            $runningCount++
            if ($status -notlike "*healthy*") {
                $allHealthy = $false
                break
            }
        }
    }
    
    if ($allHealthy -and $runningCount -ge 3) {
        $infraReady = $true
    }
    
    if (-not $infraReady) {
        Write-Host "  Waiting for infrastructure health checks... ($elapsed/${maxWait}s) - $runningCount/3 containers running" -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        $elapsed += 5
    }
}

if ($infraReady) {
    Write-Host "[OK] Infrastructure is healthy!" -ForegroundColor Green
} else {
    Write-Warning "Infrastructure health check timeout. Continuing anyway..."
}
Write-Host ""

# WINDOW 2: Backend API
Write-Host "[2/4] Launching Backend API..." -ForegroundColor Yellow
$backendScript = "$ProjectRoot\scripts\start-backend.ps1"
if (-not (Test-Path $backendScript)) {
    Write-Error "Backend script not found: $backendScript"
    exit 1
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$backendScript'" -WindowStyle Normal

# Wait for backend to start
Write-Host "[INFO] Waiting for Backend API to start..." -ForegroundColor Yellow
$backendReady = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -ErrorAction Stop -TimeoutSec 2
        if ($response.status -eq "healthy") {
            $backendReady = $true
            break
        }
    } catch { }
    Start-Sleep -Seconds 1
}

if ($backendReady) {
    Write-Host "[OK] Backend API running on http://localhost:8000" -ForegroundColor Green
} else {
    Write-Warning "Backend API may still be starting..."
}
Write-Host ""

# WINDOW 3: Packet Sniffer
Write-Host "[3/4] Launching Packet Sniffer..." -ForegroundColor Yellow
$snifferScript = "$ProjectRoot\scripts\start-sniffer.ps1"
if (-not (Test-Path $snifferScript)) {
    Write-Error "Sniffer script not found: $snifferScript"
    exit 1
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$snifferScript'" -WindowStyle Normal -Verb RunAs

Write-Host "[INFO] Packet Sniffer window launched" -ForegroundColor Green
Write-Host ""

# WINDOW 4: Frontend
Write-Host "[4/4] Launching Frontend..." -ForegroundColor Yellow
$frontendScript = "$ProjectRoot\scripts\start-frontend.ps1"
if (-not (Test-Path $frontendScript)) {
    Write-Error "Frontend script not found: $frontendScript"
    exit 1
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$frontendScript'" -WindowStyle Normal

Write-Host "[INFO] Frontend window launched" -ForegroundColor Green
Write-Host ""

# Wait for frontend to start
Write-Host "[INFO] Waiting for Frontend to start..." -ForegroundColor Yellow
$frontendReady = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -ErrorAction Stop -TimeoutSec 2 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            $frontendReady = $true
            break
        }
    } catch { }
    Start-Sleep -Seconds 1
}

if ($frontendReady) {
    Write-Host "[OK] Frontend running on http://localhost:3000" -ForegroundColor Green
} else {
    Write-Warning "Frontend may still be starting..."
}
Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] All 4 service windows launched!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "  Command Center:  http://localhost:3000" -ForegroundColor Cyan
Write-Host "  API Docs:        http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Health Check:    http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "  Live Stats:      http://localhost:8000/api/v1/stats" -ForegroundColor Cyan
Write-Host "  WebSocket:       ws://localhost:8000/ws/live" -ForegroundColor Cyan
Write-Host ""
Write-Host "Window Order:" -ForegroundColor Cyan
Write-Host "  1. Docker Infrastructure Monitor" -ForegroundColor White
Write-Host "  2. Backend API" -ForegroundColor White
Write-Host "  3. Packet Sniffer" -ForegroundColor White
Write-Host "  4. Frontend" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C in each service window to stop services." -ForegroundColor Yellow
Write-Host "Use .\scripts\stop-all.ps1 to stop all services cleanly." -ForegroundColor Yellow
Write-Host ""
Write-Host "This launcher window can be closed. Services run in their own windows." -ForegroundColor Yellow