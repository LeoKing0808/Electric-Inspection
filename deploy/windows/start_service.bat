@echo off
setlocal

cd /d "%~dp0\..\.."

if "%POWER_INSPECTION_HOST%"=="" set POWER_INSPECTION_HOST=0.0.0.0
if "%POWER_INSPECTION_PORT%"=="" set POWER_INSPECTION_PORT=8000

python apps\inspection_service\run.py
