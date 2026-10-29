[CmdletBinding()]
param(
    [string]$Version = "7.99"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($env:OS -ne "Windows_NT") {
    throw "This script must run on Windows."
}

$KnownLocations = @(
    "${env:ProgramFiles(x86)}\Nmap\nmap.exe",
    "${env:ProgramFiles}\Nmap\nmap.exe"
)

if ($KnownLocations | Where-Object { Test-Path $_ }) {
    Write-Host "Nmap is already installed." -ForegroundColor Green
    exit 0
}

$InstallerName = "nmap-$Version-setup.exe"
$DownloadUrl = "https://nmap.org/dist/$InstallerName"
$DownloadPath = Join-Path $env:TEMP $InstallerName

try {
    Write-Host "Downloading official Nmap $Version installer..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $DownloadPath -UseBasicParsing

    $Signature = Get-AuthenticodeSignature -FilePath $DownloadPath
    if ($Signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
        throw "The downloaded Nmap installer has an invalid digital signature: $($Signature.Status)"
    }

    Write-Host "Digital signature verified. Starting the official Nmap installer..." -ForegroundColor Cyan
    $Process = Start-Process -FilePath $DownloadPath -Verb RunAs -Wait -PassThru
    if ($Process.ExitCode -ne 0) {
        throw "The Nmap installer exited with code $($Process.ExitCode)."
    }

    if (-not ($KnownLocations | Where-Object { Test-Path $_ })) {
        throw "Nmap installation finished, but nmap.exe was not found in a standard installation directory."
    }

    Write-Host "Nmap installed successfully." -ForegroundColor Green
}
finally {
    if (Test-Path $DownloadPath) {
        Remove-Item -LiteralPath $DownloadPath -Force
    }
}
