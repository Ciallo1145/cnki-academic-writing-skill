param(
    [switch]$UpdateBackend
)

$ErrorActionPreference = "Stop"

$SkillName = "cnki-academic-writing-v2"
$PackageVersion = "2.7.3"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceSkill = Join-Path $Here $SkillName
$SkillRoot = Join-Path $HOME ".agents\skills"
$TargetSkill = Join-Path $SkillRoot $SkillName
$ToolsRoot = Join-Path $HOME ".agents\tools"
$Backend = Join-Path $ToolsRoot "cnki-search-skill-backend"
$Repo = "https://github.com/LongMarching/cnki-search-skill.git"

Write-Host "CNKI Academic Writing Skill V$PackageVersion"
Write-Host ""
Write-Host "[1/5] Checking prerequisites..."

$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
$UsePyLauncher = $false
if (-not $PythonCmd) {
    $PythonCmd = Get-Command py -ErrorAction SilentlyContinue
    if (-not $PythonCmd) { throw "Python 3 was not found. Install Python 3 and reopen PowerShell." }
    $UsePyLauncher = $true
}
$PythonExe = $PythonCmd.Source

$GitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $GitCmd) { throw "Git was not found. Install Git for Windows and reopen PowerShell." }
$GitExe = $GitCmd.Source

if (-not (Test-Path $SourceSkill)) { throw "Skill source folder was not found next to install.ps1: $SourceSkill" }

Write-Host "[2/5] Installing/upgrading Codex skill..."
New-Item -ItemType Directory -Force -Path $SkillRoot | Out-Null
if (Test-Path $TargetSkill) {
    $Backup = "$TargetSkill.backup-$(Get-Date -Format yyyyMMdd-HHmmss)"
    Write-Host "Existing skill found. Backing it up to: $Backup"
    Move-Item -Force $TargetSkill $Backup
}
Copy-Item -Recurse -Force $SourceSkill $TargetSkill

Write-Host "[3/5] Checking CNKI backend..."
New-Item -ItemType Directory -Force -Path $ToolsRoot | Out-Null
if (Test-Path (Join-Path $Backend ".git")) {
    if ($UpdateBackend) {
        Write-Host "Existing backend found. Updating because -UpdateBackend was specified."
        & $GitExe -C $Backend pull --ff-only
        if ($LASTEXITCODE -ne 0) { throw "git pull failed with exit code $LASTEXITCODE" }
    } else {
        Write-Host "Existing backend found. Reusing it unchanged."
        Write-Host "Use .\install.ps1 -UpdateBackend only when you intentionally want to update it."
    }
} elseif (Test-Path $Backend) {
    throw "Backend path exists but is not a Git clone: $Backend"
} else {
    Write-Host "Backend not found. Cloning it now."
    & $GitExe clone --depth 1 $Repo $Backend
    if ($LASTEXITCODE -ne 0) { throw "git clone failed with exit code $LASTEXITCODE" }
}

Write-Host "[4/5] Verifying files..."
$Wrapper = Join-Path $TargetSkill "scripts\cnki_backend.py"
$Ledger = Join-Path $TargetSkill "scripts\provenance_ledger.py"
$Intake = Join-Path $TargetSkill "scripts\assignment_intake.py"
$PreciseAudit = Join-Path $TargetSkill "scripts\precise_audit.py"
$ProsePolish = Join-Path $TargetSkill "scripts\prose_polish.py"
$LayoutGuard = Join-Path $TargetSkill "scripts\layout_guard.py"
$VersionFile = Join-Path $TargetSkill "VERSION"
$IntakeRequirements = Join-Path $TargetSkill "references\01-INTAKE-REQUIREMENTS.md"
$ResearchEvidence = Join-Path $TargetSkill "references\02-RESEARCH-EVIDENCE.md"
$AuditPolicy = Join-Path $TargetSkill "references\03-AUDIT.md"
$WritingPolicy = Join-Path $TargetSkill "references\04-WRITING.md"
$DeliveryQaPolicy = Join-Path $TargetSkill "references\05-DELIVERY-QA.md"
$BackendRun = Join-Path $Backend ".claude\skills\cnki-search\run.py"
foreach ($Required in @($Wrapper, $Ledger, $Intake, $PreciseAudit, $ProsePolish, $LayoutGuard, $VersionFile, $IntakeRequirements, $ResearchEvidence, $AuditPolicy, $WritingPolicy, $DeliveryQaPolicy, $BackendRun)) {
    if (-not (Test-Path $Required)) { throw "Missing required file: $Required" }
}

if ($UsePyLauncher) {
    & $PythonExe -3 $Wrapper --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Backend verification failed with exit code $LASTEXITCODE" }
    & $PythonExe -3 $Ledger --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Ledger helper verification failed with exit code $LASTEXITCODE" }
    & $PythonExe -3 $Intake --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Assignment intake helper verification failed with exit code $LASTEXITCODE" }
    & $PythonExe -3 $PreciseAudit --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Precision audit helper verification failed with exit code $LASTEXITCODE" }
    & $PythonExe -3 $ProsePolish --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Prose polish helper verification failed with exit code $LASTEXITCODE" }
    & $PythonExe -3 $LayoutGuard --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Layout guard helper verification failed with exit code $LASTEXITCODE" }
} else {
    & $PythonExe $Wrapper --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Backend verification failed with exit code $LASTEXITCODE" }
    & $PythonExe $Ledger --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Ledger helper verification failed with exit code $LASTEXITCODE" }
    & $PythonExe $Intake --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Assignment intake helper verification failed with exit code $LASTEXITCODE" }
    & $PythonExe $PreciseAudit --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Precision audit helper verification failed with exit code $LASTEXITCODE" }
    & $PythonExe $ProsePolish --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Prose polish helper verification failed with exit code $LASTEXITCODE" }
    & $PythonExe $LayoutGuard --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Layout guard helper verification failed with exit code $LASTEXITCODE" }
}

Write-Host "[5/5] Done."
Write-Host ""
Write-Host "Skill version: $PackageVersion"
Write-Host "Skill:         $TargetSkill"
Write-Host "Backend:       $Backend"
Write-Host ""
Write-Host "The existing CNKI backend was preserved unless -UpdateBackend was specified."
Write-Host "Restart Codex so the updated skill instructions reload."
Write-Host "Your command remains: `$cnki-academic-writing-v2"
