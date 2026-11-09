# Apex Sovereign Windows Installer
$ErrorActionPreference = "Stop"

$Repo = "raghavkhandal72-coder/apex"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\apex"
$PyzTarget = Join-Path $InstallDir "apex.pyz"
$CmdTarget = Join-Path $InstallDir "apex.cmd"
$Ps1Target = Join-Path $InstallDir "apex.ps1"

Write-Host ""
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "  APEX SOVEREIGN: AUTONOMOUS SELF-HEALING CODE ENGINE" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Locate Python 3
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Error "Python 3 is required. Please install Python 3.10+ from python.org or Microsoft Store."
    exit 1
}

$pyPath = $pythonCmd.Source
Write-Host "Detected Python: $pyPath" -ForegroundColor Green

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# 2. Deploy apex.pyz
$LocalPyz = ""
if (-not [string]::IsNullOrEmpty($PSScriptRoot)) {
    $LocalPyz = Join-Path $PSScriptRoot "dist\apex.pyz"
}

if ($LocalPyz -and (Test-Path $LocalPyz)) {
    Write-Host "Copying local build to $PyzTarget..." -ForegroundColor Gray
    Copy-Item -Path $LocalPyz -Destination $PyzTarget -Force
} else {
    $LatestUrl = "https://github.com/$Repo/releases/download/v0.9.0/apex.pyz"
    Write-Host "Downloading latest release from $LatestUrl..." -ForegroundColor Gray
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $LatestUrl -OutFile $PyzTarget -UseBasicParsing
    } catch {
        Write-Warning "Could not download release binary. Falling back to repository build..."
        exit 1
    }
}

# 3. Create Windows wrapper scripts: apex.cmd and apex.ps1
$cmdLines = @(
    "@echo off",
    "set PYTHONIOENCODING=utf-8",
    ('python "' + $PyzTarget + '" %*')
)
Set-Content -Path $CmdTarget -Value ($cmdLines -join "`r`n") -Encoding ASCII

$ps1Lines = @(
    '$env:PYTHONIOENCODING = "utf-8"',
    ('& python "' + $PyzTarget + '" @args')
)
Set-Content -Path $Ps1Target -Value ($ps1Lines -join "`r`n") -Encoding UTF8

# 4. Add to User PATH if missing
$UserPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
if ($UserPath -notlike "*$InstallDir*") {
    Write-Host "Adding $InstallDir to User PATH..." -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$InstallDir", [EnvironmentVariableTarget]::User)
    $env:Path = "$InstallDir;$env:Path"
}

Write-Host ""
Write-Host "===============================================================================" -ForegroundColor Green
Write-Host "APEX SUCCESSFULLY INSTALLED TO: $InstallDir" -ForegroundColor Green
Write-Host "===============================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Commands available anywhere in terminal:" -ForegroundColor White
Write-Host "  apex               - Interactive Autonomous Coding Console" -ForegroundColor Cyan
Write-Host "  apex demo-live     - 5-Stage Live CEGIS Repair Walkthrough" -ForegroundColor Cyan
Write-Host "  apex studio        - Apple Pro Studio Web Dashboard (http://127.0.0.1:8765)" -ForegroundColor Cyan
Write-Host "  apex hook install  - Self-Healing Git Pre-Commit Hook" -ForegroundColor Cyan
Write-Host ""
Write-Host "Type 'apex' to launch your interactive autonomous coding agent!" -ForegroundColor Yellow
Write-Host ""
