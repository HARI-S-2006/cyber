@echo off
echo ==========================================
echo  PREREQUISITES VERIFICATION
echo ==========================================
echo.

echo [1] Checking Docker...
docker --version
if %errorlevel% neq 0 echo [FAIL] Docker not found

echo.
echo [2] Checking Docker Compose...
docker compose version
if %errorlevel% neq 0 echo [FAIL] Docker Compose not found

echo.
echo [3] Checking Npcap...
if exist "C:\Program Files\Npcap\npcap.dll" (
    echo [OK] Npcap found
) else (
    echo [FAIL] Npcap not found - REINSTALL WITH WINPCAP MODE!
)

echo.
echo [4] Checking Git...
git --version
if %errorlevel% neq 0 echo [WARN] Git not found (optional)

echo.
echo [5] Checking Docker Daemon...
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Docker daemon running
) else (
    echo [FAIL] Docker daemon not running - START DOCKER DESKTOP!
)

echo.
echo ==========================================
echo  VERIFICATION COMPLETE
echo ==========================================
pause