<# 
.SYNOPSIS
    Stops all Cyber Threat Visualizer services
.DESCRIPTION
    Stops all running services: Backend, Packet Sniffer, Frontend, Docker containers
    Only stops processes related to this project.
#>

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   CYBER THREAT VISUALIZER - STOP ALL SERVICES" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

$ProjectRoot = "C:\Users\shari\cyber-threat-visualizer"

Write-Host "[INFO] Stopping project services..." -ForegroundColor Yellow

# Stop Python processes related to this project
Write-Host "[INFO] Stopping Python processes..." -ForegroundColor Yellow
$pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*$ProjectRoot*" -or $_.CommandLine -like "*cyber-threat*" -or $_.CommandLine -like "*backend*"
}
if ($pythonProcesses) {
    $pythonProcesses | ForEach-Object { 
        Write-Host "  Stopping PID $($_.Id) ($($_.ProcessName))..." -ForegroundColor Yellow
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[OK] Stopped project Python processes" -ForegroundColor Green
} else {
    Write-Host "[INFO] No project Python processes running" -ForegroundColor Yellow
}

# Stop Node processes related to this project
Write-Host "[INFO] Stopping Node.js processes..." -ForegroundColor Yellow
$nodeProcesses = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*$ProjectRoot*" -or $_.CommandLine -like "*cyber-threat*" -or $_.CommandLine -like "*frontend*" -or $_.CommandLine -like "*vite*"
}
if ($nodeProcesses) {
    $nodeProcesses | ForEach-Object { 
        Write-Host "  Stopping PID $($_.Id) ($($_.ProcessName))..." -ForegroundColor Yellow
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[OK] Stopped project Node.js processes" -ForegroundColor Green
} else {
    Write-Host "[INFO] No project Node.js processes running" -ForegroundColor Yellow
}

# Stop Docker containers
Write-Host "[INFO] Stopping Docker containers..." -ForegroundColor Yellow
$containers = @("cyber-threat-redis", "cyber-threat-zookeeper", "cyber-threat-kafka", "cyber-threat-redis-commander")
foreach ($container in $containers) {
    $exists = docker ps -a --filter "name=$container" --format "{{.Names}}" 2>$null
    if ($exists) {
        Write-Host "  Stopping $container..." -ForegroundColor Yellow
        docker stop $container 2>$null
        docker rm $container 2>$null
    }
}
Write-Host "[OK] Docker containers stopped and removed" -ForegroundColor Green

# Remove project Docker volumes
Write-Host "[INFO] Removing Docker volumes..." -ForegroundColor Yellow
$volumes = docker volume ls --filter "name=cyber-threat-visualizer" --format "{{.Name}}" 2>$null
if ($volumes) {
    $volumes | ForEach-Object { docker volume rm $_ 2>$null }
    Write-Host "[OK] Docker volumes removed" -ForegroundColor Green
} else {
    Write-Host "[INFO] No project Docker volumes found" -ForegroundColor Yellow
}

# Remove project Docker network
Write-Host "[INFO] Removing Docker network..." -ForegroundColor Yellow
$network = docker network ls --filter "name=cyber-threat-visualizer" --format "{{.Name}}" 2>$null
if ($network) {
    docker network rm $network 2>$null
    Write-Host "[OK] Docker network removed" -ForegroundColor Green
} else {
    Write-Host "[INFO] No project Docker network found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "All project services stopped." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
pause