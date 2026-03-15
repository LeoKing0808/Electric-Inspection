$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

if (-not $env:POWER_INSPECTION_HOST) { $env:POWER_INSPECTION_HOST = "0.0.0.0" }
if (-not $env:POWER_INSPECTION_PORT) { $env:POWER_INSPECTION_PORT = "8000" }

python run_service.py
