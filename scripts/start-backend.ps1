<# 
.SYNOPSIS
    Starts the Backend API (FastAPI) with ML model
.DESCRIPTION
    Terminal 2: Starts the FastAPI backend with ML anomaly detection
.REQUIRES
    - Redis must be running first (run start-redis.ps1 first)
    - Python virtual environment set up
#>

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   TERMINAL 2: BACKEND API (FastAPI + ML)" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

Write-Host "[INFO] Checking Redis connection..." -ForegroundColor Yellow
try {
    $result = redis-cli ping 2>$null
    if ($result -match "PONG") {
        Write-Host "[OK] Redis connection verified" -ForegroundColor Green
    } else {
        Write-Error "Redis not responding. Start Redis first!"
        exit 1
    }
} catch {
    Write-Error "Cannot connect to Redis. Is Redis running?"
    exit 1
}

Write-Host ""
Write-Host "[INFO] Setting up Python environment..." -ForegroundColor Yellow
Set-Location "C:\Users\shari\cyber-threat-visualizer\backend"

if (-not (Test-Path ".venv")) {
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Yellow
. .venv\Scripts\Activate.ps1

Write-Host "[INFO] Installing Python dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt 2>$null
Write-Host "[OK] Python dependencies ready" -ForegroundColor Green

# Train ML model if needed
if (-not (Test-Path "C:\Users\shari\cyber-threat-visualizer\backend\ml\models\anomaly_detector.pkl")) {
    Write-Host "[INFO] Training ML model (first run)..." -ForegroundColor Yellow
    $env:PYTHONPATH = "C:\Users\shari\cyber-threat-visualizer"
    python -c "
import sys
sys.path.insert(0, r'C:\Users\shari\cyber-threat-visualizer')
from ml.model import AnomalyDetector, ModelConfig, generate_synthetic_data
from pathlib import Path
detector = AnomalyDetector(ModelConfig())
X, y = generate_synthetic_data(5000, 0.05)
detector.fit(X)
Path('ml/models').mkdir(parents=True, exist_ok=True)
detector.save('ml/models/anomaly_detector.pkl')
print('Model trained and saved')
"
    Write-Host "[OK] ML model trained" -ForegroundColor Green
} else {
    Write-Host "[OK] ML model already trained" -ForegroundColor Green
}

Write-Host ""
Write-Host "[INFO] Starting Backend API on http://localhost:8000..." -ForegroundColor Yellow
Write-Host "API Docs will be at: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

# Start the backend API
python -m backend.api.main