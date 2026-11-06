# Apex Installer for Windows PowerShell
# Usage: irm https://raw.githubusercontent.com/YOUR_USER/apex/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

$Repo = "YOUR_USER/apex"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\apex"
$PyzTarget = Join-Path $InstallDir "apex.pyz"
$CmdTarget = Join-Path $InstallDir "apex.cmd"

Write-Host "=== Installing Apex (Zero-Dependency Program Repair) ===" -ForegroundColor Cyan

# Check Python 3.10+
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Error "Python 3 is required but was not found on PATH. Please install Python 3.10+."
    exit 1
}

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$LatestUrl = "https://github.com/$Repo/releases/latest/download/apex.pyz"
Write-Host "Downloading apex.pyz to $PyzTarget..." -ForegroundColor Gray

try {
    Invoke-WebRequest -Uri $LatestUrl -OutFile $PyzTarget -UseBasicParsing
} catch {
    Write-Warning "Could not fetch release binary from GitHub. If building from source, run: python scripts/build_pyz.py"
    exit 1
}

# Create wrapper apex.cmd
$cmdContent = @"
@echo off
python "%~dp0apex.pyz" %*
"@
Set-Content -Path $CmdTarget -Value $cmdContent -Encoding ASCII

# Add to User PATH if missing
$UserPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
if ($UserPath -notlike "*$InstallDir*") {
    Write-Host "Adding $InstallDir to User PATH..." -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$InstallDir", [EnvironmentVariableTarget]::User)
    $env:Path = "$env:Path;$InstallDir"
}

Write-Host "Apex successfully installed to $InstallDir!" -ForegroundColor Green
Write-Host "Run 'apex --version' to get started." -ForegroundColor Green
