# Virtual Environment Setup Script for Dumu Apparels
# Windows PowerShell Script

Write-Host "Setting up virtual environment for Dumu Apparels..." -ForegroundColor Cyan

# Check Python version
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

Write-Host "Found: $pythonVersion" -ForegroundColor Green

# Check if Python 3.11+
$versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
if ($versionMatch) {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-Host "Error: Python 3.11+ is required. Found Python $major.$minor" -ForegroundColor Red
        exit 1
    }
}

# Create virtual environment
if (Test-Path "venv") {
    Write-Host "Virtual environment already exists. Removing old one..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "venv"
}

Write-Host "Creating virtual environment..." -ForegroundColor Cyan
python -m venv venv

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to create virtual environment" -ForegroundColor Red
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install requirements
Write-Host "Installing requirements..." -ForegroundColor Cyan
pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to install requirements" -ForegroundColor Red
    exit 1
}

Write-Host "`nSetup complete! Virtual environment is ready." -ForegroundColor Green
Write-Host "To activate the virtual environment, run:" -ForegroundColor Yellow
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "`nTo run the application:" -ForegroundColor Yellow
Write-Host "  uvicorn main:app --reload" -ForegroundColor White

