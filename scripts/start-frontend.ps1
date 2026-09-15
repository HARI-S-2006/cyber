<# 
.SYNOPSIS
    Starts the Frontend (React + Vite + Three.js)
.DESCRIPTION
    Terminal 4: Frontend development server with Vite
.REQUIRES
    - Node.js 20+ installed
    - Dependencies installed (npm install)
#>

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   TERMINAL 4: FRONTEND (React + Vite + Three.js)" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

Set-Location "C:\Users\shari\cyber-threat-visualizer\frontend"

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "[INFO] Installing Node.js dependencies..." -ForegroundColor Yellow
    npm install 2>$null
    Write-Host "[OK] Node.js dependencies ready" -ForegroundColor Green
} else {
    Write-Host "[OK] Node.js dependencies ready" -ForegroundColor Green
}

Write-Host ""
Write-Host "[INFO] Starting Frontend dev server on http://localhost:3000..." -ForegroundColor Yellow
Write-Host "The dashboard will be available at: http://localhost:3000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

npm run dev