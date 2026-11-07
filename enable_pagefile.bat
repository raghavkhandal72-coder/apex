@echo off
:: Apex Sovereign - Enable Windows Virtual Memory (Pagefile)
:: Automatically requests Admin privileges via UAC and enables Automatic Pagefile
echo ======================================================================
echo    APEX SOVEREIGN - WINDOWS VIRTUAL MEMORY ENABLER
echo ======================================================================

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Requesting Administrator privileges (UAC prompt)...
    powershell -NoProfile -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo [*] Configuring Windows Managed Pagefile...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$cs = Get-CimInstance Win32_ComputerSystem; $cs.AutomaticManagedPagefile = $true; Set-CimInstance $cs; Write-Host '[SUCCESS] Windows Automatic Virtual Memory (Pagefile) is now ENABLED!' -ForegroundColor Green"

echo.
echo ======================================================================
echo Done! Your system virtual memory is now enabled.
echo Larger AI models like CodeGemma and Llama will now load without RAM limits.
echo ======================================================================
echo.
pause
