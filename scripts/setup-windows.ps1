<# 
.SYNOPSIS
    Sets up the Cyber Threat Visualizer development environment on Windows
.DESCRIPTION
    Installs Python dependencies, Node.js dependencies, and configures the project
    to run natively on Windows using libpcap fallback (no eBPF on Windows)
#>

param(
    [switch]$SkipPython,
    [switch]$SkipNode,
    [switch]$InstallRedis
)

Write-Host "🚀 Cyber Threat Visualizer - Windows Setup" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Check prerequisites
Write-Host "`n📋 Checking prerequisites..." -ForegroundColor Yellow

$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Python not found. Install from https://python.org (3.11+ recommended)"
    exit 1
}
Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green

$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Node.js not found. Install from https://nodejs.org (20+ recommended)"
    exit 1
}
Write-Host "✅ Node.js: $nodeVersion" -ForegroundColor Green

$npmVersion = npm --version 2>&1
Write-Host "✅ npm: $npmVersion" -ForegroundColor Green

# Check for Npcap (Windows packet capture)
Write-Host "`n🔍 Checking for Npcap (required for packet capture)..." -ForegroundColor Yellow
$npcapPath = "C:\Program Files\Npcap"
if (Test-Path $npcapPath) {
    Write-Host "✅ Npcap found at $npcapPath" -ForegroundColor Green
} else {
    Write-Warning "⚠️ Npcap not found. Packet capture will not work."
    Write-Host "   Install from: https://npcap.com/#download" -ForegroundColor Gray
    Write-Host "   ✅ Check 'Install Npcap in WinPcap API-compatible Mode' during install" -ForegroundColor Gray
}

# Setup Python backend
if (-not $SkipPython) {
    Write-Host "`n🐍 Setting up Python backend..." -ForegroundColor Yellow
    
    Set-Location "C:\Users\shari\cyber-threat-visualizer\backend"
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Install requirements (skip bcc on Windows)
    Write-Host "Installing Python packages..." -ForegroundColor Gray
    $requirements = Get-Content requirements.txt | Where-Object { $_ -notmatch 'bcc' }
    $requirements | ForEach-Object {
        Write-Host "  Installing $_..." -ForegroundColor Gray
        python -m pip install $_ 2>&1 | Out-Null
    }
    
    # Install Windows-compatible alternatives
    python -m pip install scapy pyshark 2>&1 | Out-Null
    
    Write-Host "✅ Python dependencies installed" -ForegroundColor Green
}

# Setup Node.js frontend
if (-not $SkipNode) {
    Write-Host "`n📦 Setting up Node.js frontend..." -ForegroundColor Yellow
    
    Set-Location "C:\Users\shari\cyber-threat-visualizer\frontend"
    
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing npm packages (this may take a minute)..." -ForegroundColor Gray
        npm install 2>&1 | Out-Null
    } else {
        Write-Host "node_modules exists, skipping..." -ForegroundColor Gray
    }
    
    Write-Host "✅ Frontend dependencies installed" -ForegroundColor Green
}

# Setup Redis (optional - can use Docker or native)
if ($InstallRedis) {
    Write-Host "`n🔴 Setting up Redis..." -ForegroundColor Yellow
    
    # Check if Redis is already running
    $redisCheck = redis-cli ping 2>&1
    if ($redisCheck -eq "PONG") {
        Write-Host "✅ Redis already running" -ForegroundColor Green
    } else {
        Write-Host "Redis not running. Options:" -ForegroundColor Gray
        Write-Host "  1. Install Redis via Chocolatey: choco install redis-64" -ForegroundColor Gray
        Write-Host "  2. Use Memurai (Redis-compatible): https://www.memurai.com/" -ForegroundColor Gray
        Write-Host "  3. Run in WSL2: wsl sudo service redis-server start" -ForegroundColor Gray
    }
}

# Generate .env file
Write-Host "`n⚙️ Creating environment configuration..." -ForegroundColor Yellow
$envContent = @"
# Cyber Threat Visualizer - Windows Development Config
REDIS_URL=redis://localhost:6379
INTERFACE=any
FALLBACK_MODE=true
API_HOST=0.0.0.0
API_PORT=8000
VITE_WS_URL=ws://localhost:8000
"@
Set-Content -Path "C:\Users\shari\cyber-threat-visualizer\.env" -Value $envContent
Write-Host "✅ Created .env file" -ForegroundColor Green

# Create startup scripts
Write-Host "`n📝 Creating startup scripts..." -ForegroundColor Yellow

# Backend startup
$backendScript = @"
@echo off
title Cyber Threat Visualizer - Backend
cd /d C:\Users\shari\cyber-threat-visualizer\backend
echo Starting backend on http://localhost:8000
echo Press Ctrl+C to stop
python main.py --fallback -i any -r redis://localhost:6379 --api-port 8000
pause
"@
Set-Content -Path "C:\Users\shari\cyber-threat-visualizer\scripts\start-backend.bat" -Value $backendScript

# Frontend startup
$frontendScript = @"
@echo off
title Cyber Threat Visualizer - Frontend
cd /d C:\Users\shari\cyber-threat-visualizer\frontend
echo Starting frontend on http://localhost:3000
echo Press Ctrl+C to stop
npm run dev
pause
"@
Set-Content -Path "C:\Users\shari\cyber-threat-visualizer\scripts\start-frontend.bat" -Value $frontendScript

# Combined startup
$combinedScript = @"
@echo off
title Cyber Threat Visualizer - Full Stack
echo Starting Cyber Threat Visualizer...
echo.
echo This will open 3 command windows:
echo   1. Redis (if not running)
echo   2. Backend API (port 8000)
echo   3. Frontend Dev Server (port 3000)
echo.

REM Check Redis
redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    echo Redis not detected. Starting in new window...
    start "Redis" cmd /k "redis-server"
    timeout /t 3 >nul
) else (
    echo Redis is running.
)

echo Starting Backend...
start "Backend API" cmd /k "C:\Users\shari\cyber-threat-visualizer\scripts\start-backend.bat"

timeout /t 5 >nul

echo Starting Frontend...
start "Frontend" cmd /k "C:\Users\shari\cyber-threat-visualizer\scripts\start-frontend.bat"

echo.
echo ✅ All services starting!
echo 📊 Dashboard: http://localhost:3000
echo 🔌 API:       http://localhost:8000
echo 📝 API Docs:  http://localhost:8000/docs
echo.
pause
"@
Set-Content -Path "C:\Users\shari\cyber-threat-visualizer\scripts\start-all.bat" -Value $combinedScript

Write-Host "✅ Startup scripts created" -ForegroundColor Green

Write-Host "`n🎉 Setup Complete!" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To run the project:" -ForegroundColor Yellow
Write-Host "  1. Double-click: scripts\start-all.bat" -ForegroundColor White
Write-Host "  OR run manually:" -ForegroundColor White
Write-Host "     Terminal 1: redis-server" -ForegroundColor Gray
Write-Host "     Terminal 2: scripts\start-backend.bat" -ForegroundColor Gray
Write-Host "     Terminal 3: scripts\start-frontend.bat" -ForegroundColor Gray
Write-Host ""
Write-Host "Then open: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: On Windows, packet capture uses libpcap fallback (Npcap required)" -ForegroundColor Yellow
Write-Host "      For eBPF/kernel-level capture, use WSL2 or Linux" -ForegroundColor Yellow