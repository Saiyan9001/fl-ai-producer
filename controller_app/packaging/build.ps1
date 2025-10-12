# FL-AI-Producer Build Script
# Builds standalone Windows executable using PyInstaller

$ErrorActionPreference = "Stop"

Write-Host "=" * 80
Write-Host "FL-AI-Producer Build Script"
Write-Host "=" * 80

# Check if PyInstaller is installed
Write-Host "`nChecking for PyInstaller..."
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "PyInstaller not found. Installing..."
    pip install pyinstaller
}

# Navigate to controller_app directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$appPath = Split-Path -Parent $scriptPath
Set-Location $appPath

Write-Host "`nBuilding executable..."
Write-Host "App path: $appPath"

# Run PyInstaller
pyinstaller --name fl-ai-producer `
    --onefile `
    --windowed `
    --icon=assets/icon.ico `
    --add-data "ui;ui" `
    --add-data "ai/providers;ai/providers" `
    --add-data "ai/templates;ai/templates" `
    --add-data "ai/guardrails.py;ai" `
    app.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n" + "=" * 80
    Write-Host "Build completed successfully!"
    Write-Host "Executable location: dist/fl-ai-producer.exe"
    Write-Host "=" * 80
} else {
    Write-Host "`nBuild failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
