<# 
.SYNOPSIS
    Starts the Packet Sniffer with fallback mode
.DESCRIPTION
    Window 3: Packet capture with Scapy (fallback mode for Windows)
.REQUIRES
    - Run as Administrator (for packet capture)
    - Npcap installed with WinPcap API-compatible mode
    - Python virtual environment activated
    - Redis running
#>

# Resolve project root dynamically
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   WINDOW 3: PACKET SNIFFER (Scapy + Fallback)" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

Write-Host "[INFO] Project Root: $ProjectRoot" -ForegroundColor Yellow
Write-Host ""

# Check for Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "Not running as Administrator - packet capture will fail"
    Write-Warning "Please re-run PowerShell as Administrator"
    Read-Host "Press Enter to continue anyway, or Ctrl+C to exit"
} else {
    Write-Host "[OK] Running as Administrator" -ForegroundColor Green
}

Write-Host ""
Write-Host "[INFO] Checking prerequisites..." -ForegroundColor Yellow

# Check Npcap
$npcapPaths = @("C:\Program Files\Npcap", "C:\Program Files (x86)\Npcap")
$npcapFound = $false
foreach ($path in $npcapPaths) {
    if (Test-Path $path) {
        Write-Host "[OK] Npcap found at $path" -ForegroundColor Green
        $npcapFound = $true
        break
    }
}
if (-not $npcapFound) {
    Write-Warning "Npcap not found. Install from https://npcap.com/"
    Write-Warning "IMPORTANT: Check 'Install Npcap in WinPcap API-compatible Mode' during install"
    Read-Host "Press Enter to continue anyway, or Ctrl+C to exit"
}

# Verify Python environment
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

# Verify Redis
Write-Host ""
Write-Host "[INFO] Checking Redis connection..." -ForegroundColor Yellow
$redisOk = $false
for ($i = 1; $i -le 10; $i++) {
    try {
        $result = & $pythonPath -c "import redis; r = redis.Redis(host='localhost', port=6379, protocol=2); print(r.ping())"
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
Write-Host "[INFO] Starting Packet Sniffer (Fallback Mode)..." -ForegroundColor Yellow
Write-Host "This will capture live network traffic and send to backend" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Set PYTHONPATH and start the sniffer
$env:PYTHONPATH = $ProjectRoot
cd "C:\Users\shari\cyber-threat-visualizer"

& $pythonPath -m backend.sniffer.packet_sniffer --fallback