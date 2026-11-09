# Apex Sovereign PowerShell Native Runner
$env:PYTHONIOENCODING = "utf-8"
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) {
    Write-Error "Python 3 is required. Please install Python 3.10+."
    exit 1
}
& $py.Source "$PSScriptRoot\main.py" @args
