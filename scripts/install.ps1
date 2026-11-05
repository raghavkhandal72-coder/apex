# Apex-Sovereign: Universal Windows PowerShell Installer
# Zero external dependencies | 100% Pure Python Standard Library
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "   ▄██████▄      APEX-SOVEREIGN WINDOWS INSTALLER" -ForegroundColor Yellow
Write-Host " ▟███▀▀██▀▀███▙    Autonomous Multi-LLM Software Engineering & Attestation Council" -ForegroundColor Yellow
Write-Host " ▐███ █▗▖█ ▐███▌   100% Pure Python | Zero Dependencies" -ForegroundColor Yellow
Write-Host "  ████▄▄▄▄████" -ForegroundColor Yellow
Write-Host "  ▜██████████▛" -ForegroundColor Yellow
Write-Host "    ▀██  ██▀" -ForegroundColor Yellow
Write-Host ""

# Check for python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Error "Python 3.10+ is required on PATH to run Apex-Sovereign."
    exit 1
}

$installDir = Join-Path $HOME ".apex\bin"
if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoDir = Split-Path -Parent $scriptDir
$pyzSource = Join-Path $repoDir "dist\apex.pyz"

if (-not (Test-Path $pyzSource)) {
    Write-Host "Compiling fresh apex.pyz binary..." -ForegroundColor Cyan
    & python (Join-Path $repoDir "scripts\build_pyz.py")
}

$pyzTarget = Join-Path $installDir "apex.pyz"
Copy-Item -Force $pyzSource $pyzTarget

# Create apex.cmd shim
$cmdShim = Join-Path $installDir "apex.cmd"
"@echo off`npython `"%~dp0apex.pyz`" %*" | Out-File -Encoding ascii -FilePath $cmdShim

# Ensure installDir is in User PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$installDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$installDir;$userPath", "User")
    Write-Host "Added $installDir to User PATH." -ForegroundColor Green
}

Write-Host ""
Write-Host "[OK] Successfully installed Apex-Sovereign to $installDir\apex.cmd" -ForegroundColor Green
Write-Host "Open a new terminal and run: apex console" -ForegroundColor Cyan
Write-Host ""
