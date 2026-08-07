param(
    [string]$Printer = "",
    [switch]$NoPathUpdate
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Source = Join-Path $ScriptDir "cast_bullet_workshop_calculator.py"
$InstallDir = Join-Path $env:LOCALAPPDATA "CastBulletWorkshopCalculator\bin"
$Program = Join-Path $InstallDir "cast-bullet-workshop.py"

if (-not (Test-Path $Source)) {
    throw "Cannot find cast_bullet_workshop_calculator.py beside install.ps1."
}

$Python = Get-Command py -ErrorAction SilentlyContinue
if (-not $Python) {
    $Python = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $Python) {
    throw "Python 3.8 or newer is required."
}
$PythonCommand = $Python.Source

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Force $Source $Program

$CmdFile = Join-Path $InstallDir "cast-bullet-workshop.cmd"
$CmdContents = "@echo off`r`n`"$PythonCommand`" `"$Program`" %*`r`n"
Set-Content -Path $CmdFile -Value $CmdContents -Encoding ASCII

$CbwcFile = Join-Path $InstallDir "cbwc.cmd"
Set-Content -Path $CbwcFile -Value $CmdContents -Encoding ASCII

if (-not $NoPathUpdate) {
    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $Parts = @($UserPath -split ";" | Where-Object { $_ })
    if ($Parts -notcontains $InstallDir) {
        $NewPath = (($Parts + $InstallDir) -join ";")
        [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
        Write-Host "Added $InstallDir to your user PATH. Open a new terminal."
    }
}

if ($Printer) {
    & $PythonCommand $Program --no-color --set-printer $Printer
}

Write-Host "Cast Bullet Workshop Calculator installed."
Write-Host "Open a new terminal and run: cast-bullet-workshop"
