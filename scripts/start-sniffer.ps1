<# 
.SYNOPSIS
    Starts the Packet Sniffer with fallback mode
.DESCRIPTION
    Terminal 3: Packet capture with Scapy (fallback mode for Windows)
.REQUIRES
    - Run as Administrator (for packet capture)
    - Npcap installed with WinPcap API-compatible mode
    - Python virtual environment activated
    - Redis running
#>

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   TERMINAL 3: PACKET SNIFFER (Scapy + Fallback)" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

# Check for Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Not running as Administrator - packet capture will fail"
    Write-Warning "Please re-run PowerShell as Administrator"
    Read-Host "Press Enter to continue anyway, or Ctrl+C to exit"
}

Write-Host "[INFO] Checking prerequisites..." -ForegroundColor Yellow

# Check for Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "Not running as Administrator - packet capture will fail"
    Write-Warning "Please re-run PowerShell as Administrator"
}

# Check Npcap
if (-not (Test-Path "C:\Program Files\Npcap") -and -not (Test-Path "C:\Program Files (x86)\Npcap")) {
    Write-Warning "Npcap not found. Install from https://npcap.com/"
    Write-Warning "IMPORTANT: Check 'Install Npcap in WinPcap API-compatible Mode' during install"
    Read-Host "Press Enter to continue anyway, or Ctrl+C to exit"
}

Set-Location "C:\Users\shari\cyber-threat-visualizer\backend"
. .venv\Scripts\Activate.ps1

# Verify Redis
try {
    $result = redis-cli ping 2>$null
    if ($LASTEXITCODE -eq 0) {
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
Write-Host "[INFO] Starting Packet Sniffer (Fallback Mode)..." -ForegroundColor Yellow
Write-Host "This will capture live network traffic and send to backend" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start the sniffer
python -m backend.sniffer.packet_sniffer --fallback