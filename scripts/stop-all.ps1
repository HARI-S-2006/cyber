<# 
.SYNOPSIS
    Stops all Cyber Threat Visualizer services
.DESCRIPTION
    Stops all running services: Backend, Packet Sniffer, Frontend, Docker containers
#>

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   CYBER THREAT VISUALIZER - STOP ALL SERVICES" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

Write-Host "[INFO] Stopping services..." -ForegroundColor Yellow

# Kill Python processes
Write-Host "[INFO] Stopping Python processes..." -ForegroundColor Yellow
$pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    $pythonProcesses | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Write-Host "[OK] Stopped Python processes" -ForegroundColor Green
} else {
    Write-Host "[INFO] No Python processes running" -ForegroundColor Yellow
}

# Kill Node processes
$nodeProcesses = Get-Process -Name "node" -ErrorAction SilentlyContinue
if ($nodeProcesses) {
    $nodeProcesses | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Write-Host "[OK] Stopped Node.js processes" -ForegroundColor Green
} else {
    Write-Host "[INFO] No Node.js processes running" -ForegroundColor Yellow
}

# Stop Docker containers
Write-Host "[INFO] Stopping Docker containers..." -ForegroundColor Yellow
docker stop redis zookeeper kafka 2>$null
docker rm redis zookeeper kafka 2>$null
Write-Host "[OK] Docker containers stopped and removed" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "All services stopped." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
pause