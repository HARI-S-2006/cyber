<# 
.SYNOPSIS
    Starts the Backend API (FastAPI) with ML model
.DESCRIPTION
    Window 2: Starts the FastAPI backend with ML anomaly detection
.REQUIRES
    - Redis must be running first (Infrastructure Monitor window)
    - Python virtual environment set up
#>

# Resolve project root dynamically
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   WINDOW 2: BACKEND API (FastAPI + ML)" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

Write-Host "[INFO] Project Root: $ProjectRoot" -ForegroundColor Yellow
Write-Host ""

Write-Host "[INFO] Checking Redis connection..." -ForegroundColor Yellow
$redisOk = $false
for ($i = 1; $i -le 10; $i++) {
    try {
        $result = & "C:\Users\shari\cyber-threat-visualizer\backend\.venv\Scripts\python.exe" -c "import redis; r = redis.Redis(host='localhost', port=6379, protocol=2); print(r.ping())"
        if ($result -match "True") {
            Write-Host "[OK] Redis connection verified" -ForegroundColor Green
            $redisOk = $true
            break
        }
    } catch { }
    Start-Sleep -Seconds 1
}
if (-not $redisOk) {
    Write-Error "Redis not responding. Start Infrastructure Monitor first!"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[INFO] Verifying Python environment..." -ForegroundColor Yellow
$venvPath = "C:\Users\shari\cyber-threat-visualizer\backend\.venv"
$pythonPath = "$venvPath\Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    Write-Error "Python virtual environment not found at $venvPath"
    Read-Host "Press Enter to exit"
    exit 1
}

$pyVersion = & $pythonPath --version
Write-Host "[OK] Python: $pyVersion" -ForegroundColor Green

Write-Host ""
Write-Host "[INFO] Verifying ML model..." -ForegroundColor Yellow
$modelPath = "C:\Users\shari\cyber-threat-visualizer\backend\ml\models\anomaly_detector.pkl"
if (Test-Path $modelPath) {
    Write-Host "[OK] ML model found at $modelPath" -ForegroundColor Green
} else {
    Write-Host "[INFO] Training ML model..." -ForegroundColor Yellow
    & $pythonPath -c "
import sys
sys.path.insert(0, r'C:\Users\shari\cyber-threat-visualizer')
from backend.ml.model import AnomalyDetector, ModelConfig, generate_synthetic_data
from pathlib import Path
detector = AnomalyDetector(ModelConfig())
X, y = generate_synthetic_data(5000, 0.05)
detector.fit(X)
Path('backend/ml/models').mkdir(parents=True, exist_ok=True)
detector.save('backend/ml/models/anomaly_detector.pkl')
print('Model trained and saved')
"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] ML model trained" -ForegroundColor Green
    } else {
        Write-Error "Failed to train ML model"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host ""
Write-Host "[INFO] Starting Backend API on http://localhost:8000..." -ForegroundColor Yellow
Write-Host "API Docs will be at: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health endpoint: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "Stats endpoint: http://localhost:8000/api/v1/stats" -ForegroundColor Cyan
Write-Host "WebSocket: ws://localhost:8000/ws/live" -ForegroundColor Cyan
Write-Host ""

# Set PYTHONPATH and start the backend
$env:PYTHONPATH = $ProjectRoot
cd "C:\Users\shari\cyber-threat-visualizer"

& $pythonPath -m backend.api.main