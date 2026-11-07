# Apex Installer for Windows PowerShell
# Usage:
#   Remote: irm https://raw.githubusercontent.com/raghavkhandal72-coder/apex/main/install.ps1 | iex
#   Local:  .\install.ps1 [-WithOllama]

param(
    [switch]$WithOllama
)

$ErrorActionPreference = "Stop"

$Repo = "raghavkhandal72-coder/apex"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\apex"
$PyzTarget = Join-Path $InstallDir "apex.pyz"
$CmdTarget = Join-Path $InstallDir "apex.cmd"
$Ps1Target = Join-Path $InstallDir "apex.ps1"

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🏛️ APEX PRO: THE SOVEREIGN AUTONOMOUS AI CODE SUPREME COURT                  ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python 3.10+
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Error "Python 3 is required but was not found on PATH. Please install Python 3.10+."
    exit 1
}

$pyVer = & $pythonCmd.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "✓ Detected Python $pyVer ($($pythonCmd.Source))" -ForegroundColor Green

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# 2. Deploy apex.pyz (Local build if available, else download latest release)
$LocalPyz = Join-Path $PSScriptRoot "dist\apex.pyz"
if (Test-Path $LocalPyz) {
    Write-Host "• Copying local build from $LocalPyz to $PyzTarget..." -ForegroundColor Gray
    Copy-Item -Path $LocalPyz -Destination $PyzTarget -Force
} else {
    $LatestUrl = "https://github.com/$Repo/releases/latest/download/apex.pyz"
    Write-Host "• Downloading latest release from $LatestUrl..." -ForegroundColor Gray
    try {
        Invoke-WebRequest -Uri $LatestUrl -OutFile $PyzTarget -UseBasicParsing
    } catch {
        Write-Warning "Could not fetch release binary from GitHub. If building from source, run: python scripts/build_pyz.py"
        exit 1
    }
}

# 3. Create Windows wrapper scripts: apex.cmd and apex.ps1
$cmdContent = @"
@echo off
set PYTHONIOENCODING=utf-8
python "%~dp0apex.pyz" %*
"@
Set-Content -Path $CmdTarget -Value $cmdContent -Encoding ASCII

$ps1Content = @"
`$env:PYTHONIOENCODING = "utf-8"
& python "`$PSScriptRoot\apex.pyz" @args
"@
Set-Content -Path $Ps1Target -Value $ps1Content -Encoding UTF8

# 4. Add $InstallDir to User PATH if missing
$UserPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
if ($UserPath -notlike "*$InstallDir*") {
    Write-Host "• Adding $InstallDir to User PATH..." -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$InstallDir", [EnvironmentVariableTarget]::User)
    $env:Path = "$InstallDir;$env:Path"
}

# 5. Check Ollama Integration
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
$ollamaLocalPath = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"

if ($ollamaCmd -or (Test-Path $ollamaLocalPath)) {
    Write-Host "✓ Local Ollama AI Engine detected on system." -ForegroundColor Green
} else {
    if ($WithOllama) {
        Write-Host "• Installing Ollama AI Engine for local GPU/CPU execution..." -ForegroundColor Cyan
        try {
            Invoke-Expression (Invoke-RestMethod -Uri "https://ollama.com/install.ps1" -UseBasicParsing)
            Write-Host "✓ Ollama installed successfully!" -ForegroundColor Green
        } catch {
            Write-Warning "Ollama auto-install encountered an issue. You can install it anytime with: apex ollama install"
        }
    } else {
        Write-Host "ℹ Ollama not detected. (Apex runs with 100% offline neurosymbolic synthesis out-of-the-box)." -ForegroundColor DarkGray
        Write-Host "  To enable local LLMs (e.g. Qwen 2.5 Coder): run 'apex ollama install'" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "✓ APEX SUCCESSFULLY INSTALLED TO: $InstallDir" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  🚀 Launch the Apple Pro Studio Web Dashboard :" -ForegroundColor White
Write-Host "     apex studio" -ForegroundColor Cyan
Write-Host ""
Write-Host "  🤖 Interactive Autonomous Coding Agent :" -ForegroundColor White
Write-Host "     apex" -ForegroundColor Cyan
Write-Host ""
Write-Host "  🦙 Manage Local Ollama GPU/CPU Models :" -ForegroundColor White
Write-Host "     apex ollama status" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ⚡ Run 5-Stage Live CEGIS Repair Demo :" -ForegroundColor White
Write-Host "     apex demo-live" -ForegroundColor Cyan
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
