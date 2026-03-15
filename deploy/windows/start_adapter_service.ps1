$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

if (-not $env:POWER_IMAGE_ADAPTER_HOST) { $env:POWER_IMAGE_ADAPTER_HOST = "0.0.0.0" }
if (-not $env:POWER_IMAGE_ADAPTER_PORT) { $env:POWER_IMAGE_ADAPTER_PORT = "8001" }

python apps\image_adapter\run.py
