param([switch]$Purge)

$InstallDir = Join-Path $env:LOCALAPPDATA "CastBulletWorkshopCalculator\bin"
$DataDir = Join-Path $env:LOCALAPPDATA "CastBulletWorkshopCalculator"

if (Test-Path $InstallDir) {
    Remove-Item -Recurse -Force $InstallDir
}

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$Parts = @($UserPath -split ";" | Where-Object { $_ -and $_ -ne $InstallDir })
[Environment]::SetEnvironmentVariable("Path", ($Parts -join ";"), "User")

if ($Purge -and (Test-Path $DataDir)) {
    Remove-Item -Recurse -Force $DataDir
    Write-Host "Removed the program and saved workshop data."
} else {
    Write-Host "Removed the program. Saved workshop data was retained."
}
