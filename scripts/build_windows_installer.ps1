[CmdletBinding()]
param(
    [switch]$SkipToolInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($env:OS -ne "Windows_NT") {
    throw "This script must run on Windows."
}

$ProjectDir = Split-Path -Parent $PSScriptRoot
$VenvDir = Join-Path $ProjectDir ".venv-windows"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$InstallerScript = Join-Path $ProjectDir "installer\windows\IPHunter.iss"
$InstallerOutput = Join-Path $ProjectDir "installer-output\IPHunter-Setup.exe"

Set-Location $ProjectDir

Write-Host "==> Preparing Windows Python environment" -ForegroundColor Cyan
if (-not (Test-Path $VenvPython)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $VenvDir
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $VenvDir
    }
    else {
        throw "Python 3 was not found. Install it from https://www.python.org/downloads/windows/"
    }
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install --requirement requirements.txt

Write-Host "==> Building IPHunter.exe" -ForegroundColor Cyan
& $VenvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name IPHunter `
    gui.py

$PortableExe = Join-Path $ProjectDir "dist\IPHunter.exe"
if (-not (Test-Path $PortableExe)) {
    throw "PyInstaller did not create $PortableExe"
}

$InnoCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
)
$Iscc = $InnoCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $Iscc -and -not $SkipToolInstall) {
    Write-Host "==> Installing Inno Setup" -ForegroundColor Cyan
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        & winget install --id JRSoftware.InnoSetup --exact `
            --accept-package-agreements --accept-source-agreements --silent
    }
    elseif (Get-Command choco -ErrorAction SilentlyContinue) {
        & choco install innosetup --yes --no-progress
    }
    else {
        throw "Install Inno Setup 6 from https://jrsoftware.org/isdl.php and run this script again."
    }
    $Iscc = $InnoCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $Iscc) {
    throw "Inno Setup 6 was not found. Install it, or rerun without -SkipToolInstall."
}

Write-Host "==> Building IPHunter-Setup.exe" -ForegroundColor Cyan
& $Iscc $InstallerScript

if (-not (Test-Path $InstallerOutput)) {
    throw "Inno Setup did not create $InstallerOutput"
}

$Installer = Get-Item $InstallerOutput
Write-Host ""
Write-Host "Windows installer created successfully:" -ForegroundColor Green
Write-Host $Installer.FullName
Write-Host ("Size: {0:N2} MB" -f ($Installer.Length / 1MB))
