# Apex Unified Master Verification & Test-All Runner
# Usage: .\test_all.ps1
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# Ensure UTF-8 console output encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "      APEX MASTER VERIFICATION RUNNER (Windows PowerShell)       " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Error "Python 3 is required but was not found on PATH."
    exit 1
}

$repoRoot = $PSScriptRoot
if (-not $repoRoot) {
    $repoRoot = (Get-Location).Path
}

$pyzPath = Join-Path $repoRoot "dist\apex.pyz"
if (Test-Path $pyzPath) {
    Write-Host "Executing unified verification via standalone zipapp (dist/apex.pyz)..." -ForegroundColor Gray
    & python $pyzPath test-all
} else {
    Write-Host "Executing unified verification via source tree (apex_council)..." -ForegroundColor Gray
    & python -m apex_council.test_all_runner
}

$exitCode = $LASTEXITCODE
if ($exitCode -eq 0) {
    Write-Host "`n[SUCCESS] All systems verified operational and ready." -ForegroundColor Green
} else {
    Write-Host "`n[FAILURE] Verification encountered errors (exit code: $exitCode)." -ForegroundColor Red
}

exit $exitCode
