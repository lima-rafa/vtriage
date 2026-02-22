param(
  [int]$Seeds = 20,
  [string]$Cmd = "python scripts/sim_harness.py",
  [string]$Workdir = ".\examples\zipcpu",
  [string]$VcdPath = "build\waves.vcd",
  [string]$ArtifactRoot = "artifacts",
  [string]$Out = "report",
  [switch]$NoOpen,
  [string]$Format = "html,md"
)

$ErrorActionPreference = "Stop"

# Resolve paths relative to this script
$RepoRoot   = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$CiRun      = Join-Path $PSScriptRoot "ci_run.ps1"
$ArtifactAbs = if ([System.IO.Path]::IsPathRooted($ArtifactRoot)) { $ArtifactRoot } else { Join-Path $RepoRoot $ArtifactRoot }
$OutAbs      = if ([System.IO.Path]::IsPathRooted($Out)) { $Out } else { Join-Path $RepoRoot $Out }

if (-not (Test-Path $CiRun)) {
  throw "Não encontrei: $CiRun"
}

Write-Host "== vtriage runner =="
Write-Host "RepoRoot:   $RepoRoot"
Write-Host "Workdir:    $Workdir"
Write-Host "ArtifactRoot: $ArtifactAbs"
Write-Host "Out:        $OutAbs"
Write-Host ""

# Run ci_run.ps1 but DO NOT stop the pipeline if it returns exit 1 (failures are expected)
$exitCode = 0
try {
  & powershell -ExecutionPolicy Bypass -File $CiRun `
    -Seeds $Seeds `
    -Cmd $Cmd `
    -Workdir $Workdir `
    -VcdPath $VcdPath `
    -ArtifactRoot $ArtifactAbs `
    -Out $OutAbs `
    -NoAnalyze
  $exitCode = $LASTEXITCODE
} catch {
  # If PowerShell threw, still try to analyze latest run
  Write-Host "[warn] Runner lançou exceção, vou tentar analisar o último run mesmo assim." -ForegroundColor Yellow
  $exitCode = 1
}

# Find latest run dir
$latest = Get-ChildItem $ArtifactAbs -Directory -ErrorAction SilentlyContinue |
  Sort-Object Name -Descending |
  Select-Object -First 1

if (-not $latest) {
  throw "Não encontrei nenhum run em: $ArtifactAbs"
}

$runDir = $latest.FullName
Write-Host ""
Write-Host "== vtriage analyze =="
Write-Host "Run: $runDir"
Write-Host ""

# Analyze
& vtriage analyze $runDir --out $OutAbs --format $Format
$anExit = $LASTEXITCODE

# Open report
$reportHtml = Join-Path $OutAbs "report.html"
if (-not $NoOpen -and (Test-Path $reportHtml)) {
  Start-Process $reportHtml
}

Write-Host ""
Write-Host "Runner exit:  $exitCode"
Write-Host "Analyze exit: $anExit"
Write-Host "Report:       $reportHtml"

# Keep CI semantics: return runner exit code (fails -> 1), but analysis still ran
exit $exitCode
