<# 
.SYNOPSIS
    Starts the Frontend (React + Vite + Three.js)
.DESCRIPTION
    Window 4: Frontend development server with Vite
.REQUIRES
    - Node.js 20+ installed
    - Dependencies installed (npm install)
#>

# Resolve project root dynamically
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   WINDOW 4: FRONTEND (React + Vite + Three.js)" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

Write-Host "[INFO] Project Root: $ProjectRoot" -ForegroundColor Yellow
Write-Host ""

cd "C:\Users\shari\cyber-threat-visualizer\frontend"

# Check Node.js
Write-Host "[INFO] Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "[OK] Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Error "Node.js not found. Install from https://nodejs.org"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check npm
try {
    $npmVersion = npm --version
    Write-Host "[OK] npm: $npmVersion" -ForegroundColor Green
} catch {
    Write-Error "npm not found"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if node_modules exists
Write-Host ""
Write-Host "[INFO] Checking Node.js dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "node_modules")) {
    Write-Host "[INFO] Installing Node.js dependencies..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Error "npm install failed"
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "[OK] Node.js dependencies installed" -ForegroundColor Green
} else {
    Write-Host "[OK] Node.js dependencies ready" -ForegroundColor Green
}

Write-Host ""
Write-Host "[INFO] Starting Frontend dev server on http://localhost:3000..." -ForegroundColor Yellow
Write-Host "The dashboard will be available at: http://localhost:3000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

npm run dev