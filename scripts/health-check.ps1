<# 
.SYNOPSIS
    Health check for all Cyber Threat Visualizer services
.DESCRIPTION
    Verifies Docker, Redis, Zookeeper, Kafka, Backend, WebSocket, Sniffer, Frontend, and ML model
#>

# Resolve project root dynamically
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   CYBER THREAT VISUALIZER - HEALTH CHECK" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

$results = @()

function Add-Result {
    param($Service, $Status, $Detail)
    $global:results += [PSCustomObject]@{
        Service = $Service
        Status  = $Status
        Detail  = $Detail
    }
}

# 1. Docker
Write-Host "[1/10] Checking Docker..." -ForegroundColor Yellow -NoNewline
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        docker info >$null 2>&1
        if ($LASTEXITCODE -eq 0) {
            Add-Result "Docker" "OK" "Docker daemon running"
            Write-Host " [OK]" -ForegroundColor Green
        } else {
            Add-Result "Docker" "FAIL" "Docker daemon not running"
            Write-Host " [FAIL] Daemon not running" -ForegroundColor Red
        }
    } else {
        Add-Result "Docker" "FAIL" "Docker not installed"
        Write-Host " [FAIL] Not installed" -ForegroundColor Red
    }
} catch {
    Add-Result "Docker" "FAIL" "Error: $_"
    Write-Host " [FAIL] $_" -ForegroundColor Red
}

# 2. Redis
Write-Host "[2/10] Checking Redis..." -ForegroundColor Yellow -NoNewline
try {
    $result = & "C:\Users\shari\cyber-threat-visualizer\backend\.venv\Scripts\python.exe" -c "import redis; r = redis.Redis(host='localhost', port=6379, socket_timeout=2, protocol=2); print(r.ping())"
    if ($result -match "True") {
        Add-Result "Redis" "OK" "PONG received"
        Write-Host " [OK]" -ForegroundColor Green
    } else {
        Add-Result "Redis" "FAIL" "Unexpected response: $result"
        Write-Host " [FAIL] $result" -ForegroundColor Red
    }
} catch {
    Add-Result "Redis" "FAIL" "Connection failed: $_"
    Write-Host " [FAIL] $_" -ForegroundColor Red
}

# 3. Zookeeper
Write-Host "[3/10] Checking Zookeeper..." -ForegroundColor Yellow -NoNewline
try {
    $container = docker ps --filter "name=cyber-threat-zookeeper" --format "{{.Status}}"
    if ($container -like "*Up*" -and $container -like "*healthy*") {
        Add-Result "Zookeeper" "OK" "Container healthy"
        Write-Host " [OK]" -ForegroundColor Green
    } elseif ($container -like "*Up*") {
        Add-Result "Zookeeper" "WARN" "Container running but not healthy"
        Write-Host " [WARN] Running but not healthy" -ForegroundColor Yellow
    } else {
        Add-Result "Zookeeper" "FAIL" "Container not running"
        Write-Host " [FAIL] Not running" -ForegroundColor Red
    }
} catch {
    Add-Result "Zookeeper" "FAIL" "Error: $_"
    Write-Host " [FAIL] $_" -ForegroundColor Red
}

# 4. Kafka
Write-Host "[4/10] Checking Kafka..." -ForegroundColor Yellow -NoNewline
try {
    $container = docker ps --filter "name=cyber-threat-kafka" --format "{{.Status}}"
    if ($container -like "*Up*" -and $container -like "*healthy*") {
        # Test broker readiness
        $test = docker exec cyber-threat-kafka kafka-broker-api-versions --bootstrap-server localhost:9092 2>&1
        if ($LASTEXITCODE -eq 0) {
            Add-Result "Kafka" "OK" "Broker ready"
            Write-Host " [OK]" -ForegroundColor Green
        } else {
            Add-Result "Kafka" "WARN" "Container healthy but broker not ready"
            Write-Host " [WARN] Broker not ready" -ForegroundColor Yellow
        }
    } elseif ($container -like "*Up*") {
        Add-Result "Kafka" "WARN" "Container running but not healthy"
        Write-Host " [WARN] Running but not healthy" -ForegroundColor Yellow
    } else {
        Add-Result "Kafka" "FAIL" "Container not running"
        Write-Host " [FAIL] Not running" -ForegroundColor Red
    }
} catch {
    Add-Result "Kafka" "FAIL" "Error: $_"
    Write-Host " [FAIL] $_" -ForegroundColor Red
}

# 5. Backend API
Write-Host "[5/10] Checking Backend API..." -ForegroundColor Yellow -NoNewline
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -ErrorAction Stop -TimeoutSec 5
    if ($response.status -eq "healthy") {
        Add-Result "Backend API" "OK" "Health endpoint OK"
        Write-Host " [OK]" -ForegroundColor Green
    } else {
        Add-Result "Backend API" "WARN" "Unexpected response"
        Write-Host " [WARN] Unexpected response" -ForegroundColor Yellow
    }
} catch {
    Add-Result "Backend API" "FAIL" "Health endpoint unreachable: $_"
    Write-Host " [FAIL] $_" -ForegroundColor Red
}

# 6. Backend Stats
Write-Host "[6/10] Checking Backend Stats..." -ForegroundColor Yellow -NoNewline
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/stats" -ErrorAction Stop -TimeoutSec 5
    Add-Result "Backend Stats" "OK" "Stats: $($response.active_flows) flows, $($response.threats_detected) threats"
    Write-Host " [OK]" -ForegroundColor Green
} catch {
    Add-Result "Backend Stats" "FAIL" "Stats endpoint unreachable: $_"
    Write-Host " [FAIL] $_" -ForegroundColor Red
}

# 7. WebSocket - write test to file to avoid escaping issues
Write-Host "[7/10] Checking WebSocket..." -ForegroundColor Yellow -NoNewline
$wsTestScript = "$env:TEMP\ws_test_$([guid]::NewGuid()).py"
@"
import asyncio
import websockets
async def test_ws():
    try:
        async with websockets.connect('ws://localhost:8000/ws/live', open_timeout=5) as ws:
            await ws.send('{"type": "ping"}')
            resp = await asyncio.wait_for(ws.recv(), timeout=3)
            print('WS_OK')
    except Exception as e:
        print(f'WS_FAIL: {e}')
asyncio.run(test_ws())
"@ | Set-Content -Path $wsTestScript -Encoding UTF8
try {
    $wsTest = & "C:\Users\shari\cyber-threat-visualizer\backend\.venv\Scripts\python.exe" $wsTestScript 2>&1
    Remove-Item $wsTestScript -ErrorAction SilentlyContinue
    if ($wsTest -match "WS_OK") {
        Add-Result "WebSocket" "OK" "Connection and ping/pong successful"
        Write-Host " [OK]" -ForegroundColor Green
    } else {
        Add-Result "WebSocket" "FAIL" "$wsTest"
        Write-Host " [FAIL] $wsTest" -ForegroundColor Red
    }
} catch {
    Remove-Item $wsTestScript -ErrorAction SilentlyContinue
    Add-Result "WebSocket" "FAIL" "Test failed: $_"
    Write-Host " [FAIL] $_" -ForegroundColor Red
}

# 8. ML Model
Write-Host "[8/10] Checking ML Model..." -ForegroundColor Yellow -NoNewline
try {
    $modelPath = "C:\Users\shari\cyber-threat-visualizer\backend\ml\models\anomaly_detector.pkl"
    if (Test-Path $modelPath) {
        $test = & "C:\Users\shari\cyber-threat-visualizer\backend\.venv\Scripts\python.exe" -c "
import sys
sys.path.insert(0, r'C:\Users\shari\cyber-threat-visualizer')
from backend.ml.model import AnomalyDetector
detector = AnomalyDetector.load('backend/ml/models/anomaly_detector.pkl')
print(f'MODEL_OK: fitted={detector.is_fitted}, threshold={detector.threshold}')
"
        if ($test -match "MODEL_OK") {
            Add-Result "ML Model" "OK" "$test"
            Write-Host " [OK]" -ForegroundColor Green
        } else {
            Add-Result "ML Model" "FAIL" "Model load failed: $test"
            Write-Host " [FAIL] $test" -ForegroundColor Red
        }
    } else {
        Add-Result "ML Model" "FAIL" "Model file not found"
        Write-Host " [FAIL] Model file not found" -ForegroundColor Red
    }
} catch {
    Add-Result "ML Model" "FAIL" "Error: $_"
    Write-Host " [FAIL] $_" -ForegroundColor Red
}

# 9. Packet Sniffer (check if process exists)
Write-Host "[9/10] Checking Packet Sniffer..." -ForegroundColor Yellow -NoNewline
try {
    $snifferProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*packet_sniffer*" }
    if ($snifferProcess) {
        Add-Result "Packet Sniffer" "OK" "Process running (PID: $($snifferProcess.Id))"
        Write-Host " [OK]" -ForegroundColor Green
    } else {
        Add-Result "Packet Sniffer" "WARN" "No sniffer process found"
        Write-Host " [WARN] Not running" -ForegroundColor Yellow
    }
} catch {
    Add-Result "Packet Sniffer" "FAIL" "Error: $_"
    Write-Host " [FAIL] $_" -ForegroundColor Red
}

# 10. Frontend
Write-Host "[10/10] Checking Frontend..." -ForegroundColor Yellow -NoNewline
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -ErrorAction Stop -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Add-Result "Frontend" "OK" "HTTP 200 on port 3000"
        Write-Host " [OK]" -ForegroundColor Green
    } else {
        Add-Result "Frontend" "WARN" "HTTP $($response.StatusCode)"
        Write-Host " [WARN] HTTP $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Add-Result "Frontend" "FAIL" "Frontend unreachable: $_"
    Write-Host " [FAIL] $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   SUMMARY" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$okCount = ($results | Where-Object { $_.Status -eq "OK" }).Count
$warnCount = ($results | Where-Object { $_.Status -eq "WARN" }).Count
$failCount = ($results | Where-Object { $_.Status -eq "FAIL" }).Count

$results | Format-Table -AutoSize

Write-Host ""
Write-Host "Total: $($results.Count) | OK: $okCount | WARN: $warnCount | FAIL: $failCount" -ForegroundColor Cyan

if ($failCount -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] All critical services healthy!" -ForegroundColor Green
    exit 0
} else {
    Write-Host ""
    Write-Host "[FAILURE] $failCount critical service(s) failing" -ForegroundColor Red
    exit 1
}