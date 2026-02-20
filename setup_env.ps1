# setup_env.ps1
# Creates a venv and installs packages from requirements.txt for this project.
# Usage: Open PowerShell in project root and run: .\setup_env.ps1

try {
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force | Out-Null
} catch {
}

function Write-ErrAndExit($msg) {
    Write-Host $msg -ForegroundColor Red
    exit 1
}

# Ensure working directory is the script directory (project root)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if ($scriptDir) { Set-Location $scriptDir }

Write-Host "Working in project folder: $(Get-Location)"

# Find a Python launcher
$pyCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $pyCmd = "py" }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $pyCmd = "python" }

if (-not $pyCmd) {
    Write-ErrAndExit "Python not found. Please install Python 3 from https://www.python.org/downloads/ and ensure 'Add Python to PATH' is enabled. Opening download page..." 
    Start-Process "https://www.python.org/downloads/"
}

# Show python version
Write-Host "Using Python launcher: $pyCmd"
& $pyCmd --version

$venvPath = Join-Path -Path (Get-Location) -ChildPath "venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at .\venv ..."
    & $pyCmd -m venv venv
    if ($LASTEXITCODE -ne 0) { Write-ErrAndExit "Failed to create virtual environment." }
} else {
    Write-Host "Virtual environment already exists at .\venv"
}

# Install packages using the venv pip to avoid PATH issues
$pipExe = Join-Path -Path $venvPath -ChildPath "Scripts\pip.exe"
if (-not (Test-Path $pipExe)) { Write-ErrAndExit "pip not found in venv. Did venv creation fail?" }

if (-not (Test-Path "requirements.txt")) {
    Write-Host "requirements.txt not found in project root; installing minimal required packages"
    & $pipExe install --upgrade pip
    & $pipExe install flask flask-cors python-dotenv mysql-connector-python
    if ($LASTEXITCODE -ne 0) { Write-ErrAndExit "Package installation failed. Check the output above." }
} else {
    Write-Host "Installing packages from requirements.txt"
    & $pipExe install --upgrade pip
    & $pipExe install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Write-ErrAndExit "Package installation failed. Check the output above." }
}

Write-Host "Setup complete. To activate the virtual environment run:"
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "Then you can run the app or use pip to install additional packages." -ForegroundColor Green

exit 0
