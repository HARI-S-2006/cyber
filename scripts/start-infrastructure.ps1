<# 
.SYNOPSIS
    Docker Infrastructure Monitor - Window 1
.DESCRIPTION
    Starts and monitors Redis, Zookeeper, and Kafka containers.
    This is a persistent monitoring terminal that shows live infrastructure status.
.REQUIRES
    - Docker Desktop running
    - Run from project root directory
#>

# Resolve project root dynamically
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  CYBER THREAT VISUALIZER" -ForegroundColor Cyan
Write-Host "  DOCKER INFRASTRUCTURE MONITOR" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

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
    Read-Host "Press Enter to exit"
    exit 1
}

docker info >$null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker daemon not running. Start Docker Desktop first."
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Docker daemon running" -ForegroundColor Green
Write-Host ""

# Start infrastructure services
Write-Host "[INFO] Starting infrastructure services (Redis, Zookeeper, Kafka)..." -ForegroundColor Yellow
docker compose up -d redis zookeeper kafka

Write-Host ""
Write-Host "[INFO] Waiting for services to become healthy..." -ForegroundColor Yellow
Write-Host ""

# Function to display infrastructure status
function Show-InfrastructureStatus {
    Clear-Host
    Write-Host "===========================================================" -ForegroundColor Cyan
    Write-Host "  CYBER THREAT VISUALIZER" -ForegroundColor Cyan
    Write-Host "  DOCKER INFRASTRUCTURE MONITOR" -ForegroundColor Cyan
    Write-Host "===========================================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Get container status using docker ps
    $containers = docker ps --filter "name=cyber-threat-" --format "{{.Names}}|{{.Status}}|{{.Ports}}"
    
    if ($containers) {
        foreach ($line in $containers) {
            $parts = $line -split '\|'
            if ($parts.Count -ge 3) {
                $name = $parts[0]
                $status = $parts[1]
                $ports = $parts[2]
                
                # Determine port and health
                $port = switch -Wildcard ($name) {
                    "*redis*" { "6379" }
                    "*zookeeper*" { "2181" }
                    "*kafka*" { "9092" }
                    default { "N/A" }
                }
                
                $health = if ($status -like "*healthy*") { "healthy" } elseif ($status -like "*unhealthy*") { "unhealthy" } elseif ($status -like "*starting*") { "starting" } else { "unknown" }
                
                $statusColor = if ($status -like "*Up*" -and $health -eq "healthy") { "Green" }
                elseif ($status -like "*Up*") { "Yellow" }
                else { "Red" }
                
                $healthDisplay = switch ($health) {
                    "healthy" { "[HEALTHY]" }
                    "unhealthy" { "[UNHEALTHY]" }
                    "starting" { "[STARTING...]" }
                    default { "[$health]" }
                }
                
                Write-Host "$name".PadRight(30) " $port".PadRight(8) $healthDisplay -ForegroundColor $statusColor
            }
        }
    }
    
    Write-Host ""
    Write-Host "Docker Compose Project:" -ForegroundColor Cyan
    Write-Host "  cyber-threat-visualizer" -ForegroundColor White
    Write-Host ""
    Write-Host "LIVE LOGS" -ForegroundColor Cyan
    Write-Host "---------------------------------------------------------" -ForegroundColor Cyan
}

# Wait for all services to be healthy
$maxWait = 120
$elapsed = 0
$allHealthy = $false

while ($elapsed -lt $maxWait -and -not $allHealthy) {
    Show-InfrastructureStatus
    
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
    
    if ($runningCount -lt 3) {
        $allHealthy = $false
    }
    
    if (-not $allHealthy) {
        Write-Host "Waiting for health checks... ($elapsed/${maxWait}s) - $runningCount/3 containers running" -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        $elapsed += 5
    }
}

Show-InfrastructureStatus

if ($allHealthy) {
    Write-Host ""
    Write-Host "[SUCCESS] All infrastructure services are HEALTHY!" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host ""
    Write-Warning "Timeout waiting for all services to become healthy."
    Write-Host "Check logs below for details." -ForegroundColor Yellow
    Write-Host ""
}

# Show live logs
Write-Host "Streaming live logs (Ctrl+C to stop monitoring)..." -ForegroundColor Yellow
Write-Host ""

try {
    docker compose logs -f --tail 20 redis zookeeper kafka
} catch {
    Write-Error "Failed to stream logs: $_"
}

Write-Host ""
Write-Host "Infrastructure monitor stopped." -ForegroundColor Yellow
Read-Host "Press Enter to close this window"