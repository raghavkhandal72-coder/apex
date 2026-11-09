@echo off
:: Apex Sovereign - Enable Windows Virtual Memory (Pagefile)
echo ======================================================================
echo    APEX SOVEREIGN - WINDOWS VIRTUAL MEMORY (PAGEFILE) ENABLER
echo ======================================================================

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Administrator privileges required.
    echo Please right-click this script and select 'Run as Administrator'.
    pause
    exit /b 1
)

echo [*] Enabling Windows Automatic Managed Pagefile via WMIC and Registry...
wmic computersystem where name="%computername%" set AutomaticManagedPagefile=True
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v PagingFiles /t REG_MULTI_SZ /d "C:\pagefile.sys 0 0" /f

echo.
echo ======================================================================
echo [SUCCESS] Windows Automatic Virtual Memory (Pagefile) is now ENABLED!
echo Available Virtual Memory has been expanded across disk space.
echo ======================================================================
echo.
pause
