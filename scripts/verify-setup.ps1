<# 
.SYNOPSIS
    Verifies all Cyber Threat Visualizer prerequisites and setup
.DESCRIPTION
    Checks all prerequisites, dependencies, and services are properly configured
#>

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   CYBER THREAT VISUALIZER - SETUP VERIFICATION" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

$global:errors = 0
$global:warnings = 0

function Check-Command($name, $command, $required = $true) {
    try {
        $result = & $command 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] $name: $($result.Trim())" -ForegroundColor Green
            return $true
        } else {
            throw "Command failed"
        }
    } catch {
        if ($required) {
            Write-Host ("[FAIL] {0}: NOT FOUND (required)" -f $name) -ForegroundColor Red
            $global:errors++
        } else {
            Write-Host "[WARN] {0}: NOT FOUND (optional)" -f $name -ForegroundColor Yellow
            $global:warnings++
        }
        return $false
    }
}

function Check-PythonPackage($package) {
    try {
        $version = python -c "import $package; print($package.__version__)" 2>&1
        Write-Host ("[OK] Python package {0}: {1}" -f $package, $version) -ForegroundColor Green
        return $true
    } catch {
        Write-Host ("[FAIL] Python package {0}: NOT INSTALLED" -f $package) -ForegroundColor Red
        $global:errors++
        return $false
    }
}

function Check-NpmPackage($package) {
    try {
        npm list $package --depth=0 2>&1 | Out-Null
        Write-Host "[OK] npm package $package" -ForegroundColor Green
        return $true
    } catch {
        Write-Host ("[FAIL] npm package {0}: NOT INSTALLED" -f $package) -ForegroundColor Red
        $global:errors++
        return $false
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   CYBER THREAT VISUALIZER - SETUP VERIFICATION" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

$global:errors = 0
$global:warnings = 0

# Check core tools
Write-Host "`n=== Core Tools ===" -ForegroundColor Yellow
Check-Command "Python" { python --version }
Check-Command "Node.js" { node --version }
Check-Command "npm" { npm --version }
Check-Command "Redis CLI" { redis-cli --version } $false

# Check Python packages
Write-Host "`n=== Python Packages ===" -ForegroundColor Yellow
$pyPackages = @("fastapi", "uvicorn", "redis", "pydantic", "scapy", "numpy", "pandas", "sklearn", "joblib", "lightgbm")
foreach ($pkg in $pyPackages) {
    try {
        $version = python -c "import $pkg; print($pkg.__version__)" 2>&1
        Write-Host ("[OK] Python package {0}: {1}" -f $pkg, $version) -ForegroundColor Green
    } catch {
        Write-Host ("[FAIL] Python package {0}: NOT INSTALLED" -f $pkg) -ForegroundColor Red
        $global:errors++
    }
}

# Check npm packages
Write-Host "`n=== Frontend Packages ===" -ForegroundColor Yellow
Set-Location "C:\Users\shari\cyber-threat-visualizer\frontend"
$npmPackages = @("react", "three", "@react-three/fiber", "@react-three/drei", "zustand", "socket.io-client", "d3-geo", "topojson-client")
foreach ($pkg in $npmPackages) {
    try {
        npm list $pkg --depth=0 2>&1 | Out-Null
        Write-Host "[OK] npm package $pkg" -ForegroundColor Green
    } catch {
        Write-Host ("[FAIL] npm package {0}: NOT INSTALLED" -f $pkg) -ForegroundColor Red
        $global:errors++
    }
}

# Check network interfaces
Write-Host "`n=== Network Interfaces ===" -ForegroundColor Yellow
try {
    $interfaces = python -c "
import sys
sys.path.insert(0, r'C:\Users\shari\cyber-threat-visualizer\backend')
from capture.capture_manager import list_interfaces
for i in list_interfaces():
    print(i)
" 2>&1
    if ($interfaces) {
        $interfaces.Split("`n") | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
    } else {
        Write-Host "  (none found - install Npcap)" -ForegroundColor Yellow
        $warnings++
    }
} catch {
    Write-Host "  Error listing interfaces" -ForegroundColor Red
    $errors++
}

# Check Npcap
Write-Host "`n=== Npcap Status ===" -ForegroundColor Yellow
if (Test-Path "C:\Program Files\Npcap") {
    Write-Host "[OK] Npcap installed" -ForegroundColor Green
} elseif (Test-Path "C:\Program Files (x86)\Npcap") {
    Write-Host "[OK] Npcap installed (x86)" -ForegroundColor Green
} else {
    Write-Host "[WARN] Npcap NOT installed - packet capture will not work" -ForegroundColor Yellow
    Write-Host "   Download from: https://npcap.com/#download" -ForegroundColor Gray
    Write-Host "   ✅ Check 'Install Npcap in WinPcap API-compatible Mode'" -ForegroundColor Gray
    $warnings++
}

# Check project structure
Write-Host "`n=== Project Structure ===" -ForegroundColor Yellow
$requiredFiles = @(
    "backend/api/main.py",
    "backend/sniffer/packet_sniffer.py",
    "backend/ml/model.py",
    "backend/streaming/stream_manager.py",
    "backend/utils/redis_client.py",
    "backend/utils/kafka_client.py",
    "frontend/package.json",
    "frontend/src/main.tsx",
    "frontend/src/App.tsx",
    "frontend/src/hooks/useStore.ts",
    "frontend/src/components/globe/GlobeScene.tsx",
    "docker-compose.yml",
    "README.md"
)

foreach ($file in $requiredFiles) {
    $path = "C:\Users\shari\cyber-threat-visualizer\$file"
    if (Test-Path $path) {
        Write-Host "[OK] $file" -ForegroundColor Green
    } else {
        Write-Host ("[FAIL] {0} (MISSING)" -f $file) -ForegroundColor Red
        $global:errors++
    }
}

# Summary
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "   VERIFICATION SUMMARY" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if ($global:errors -eq 0 -and $global:warnings -eq 0) {
    Write-Host "ALL CHECKS PASSED! Ready to run." -ForegroundColor Green
    Write-Host "`nRun: .\scripts\start-all.ps1" -ForegroundColor Cyan
} elseif ($global:errors -eq 0) {
    Write-Host "Core setup OK with $global:warnings warning(s)" -ForegroundColor Yellow
    Write-Host "`nRun: .\scripts\start-all.ps1" -ForegroundColor Cyan
} else {
    Write-Host ("{0} error(s), {1} warning(s) - Fix before running" -f $global:errors, $global:warnings) -ForegroundColor Red
    exit 1
}