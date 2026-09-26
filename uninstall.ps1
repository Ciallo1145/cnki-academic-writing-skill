param([switch]$RemoveBackend)

$ErrorActionPreference = "Stop"

$Skill = Join-Path $HOME ".agents\skills\cnki-academic-writing-v2"
$Backend = Join-Path $HOME ".agents\tools\cnki-search-skill-backend"

if (Test-Path $Skill) {
    Remove-Item -Recurse -Force $Skill
    Write-Host "Removed skill: $Skill"
} else {
    Write-Host "Skill not installed: $Skill"
}

if ($RemoveBackend) {
    if (Test-Path $Backend) {
        Remove-Item -Recurse -Force $Backend
        Write-Host "Removed backend: $Backend"
    }
} else {
    Write-Host "CNKI backend was preserved. Use .\uninstall.ps1 -RemoveBackend to remove it too."
}
