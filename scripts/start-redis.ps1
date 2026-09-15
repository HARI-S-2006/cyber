<# 
.SYNOPSIS
    Starts Redis and verifies it's working properly
.DESCRIPTION
    Terminal 1: Starts Redis via Docker and verifies it's healthy before proceeding
.REQUIRES
    - Docker Desktop running
#>

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   TERMINAL 1: REDIS STARTUP & VERIFICATION" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

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

Write-Host "[INFO] Starting Redis container..." -ForegroundColor Yellow
docker run -d --name redis -p 6379:6379 --restart unless-stopped redis:7-alpine 2>$null

Write-Host "[INFO] Waiting for Redis to be healthy..." -ForegroundColor Yellow
$redisOk = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $result = redis-cli ping 2>$null
        if ($result -match "PONG") {
            Write-Host "[OK] Redis is ready and responding to PING" -ForegroundColor Green
            $redisOk = $true
            break
        }
    } catch { }
    Start-Sleep -Seconds 1
    Write-Host "  Waiting... ($i/30)" -ForegroundColor Gray
}

if (-not $redisOk) {
    Write-Error "Redis failed to start after 30 seconds"
    Write-Host "Check logs: docker logs redis" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[SUCCESS] Redis is running and healthy!" -ForegroundColor Green
Write-Host ""
Write-Host "Redis is running on localhost:6379" -ForegroundColor Cyan
Write-Host "You can now start the backend in another terminal." -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Enter to keep this window open (Redis runs in background)..." -ForegroundColor Yellow
Read-Host "Press Enter to continue..."