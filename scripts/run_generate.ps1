param(
  [int]$Seeds = 20,
  [string]$Cmd = "python scripts/sim_harness.py",
  [string]$Workdir = ".\examples\zipcpu",
  [string]$VcdPath = "build\waves.vcd",
  [string]$ArtifactRoot = "artifacts",
  [string]$Out = "report",
  [string]$RunId = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$CiRun    = Join-Path $PSScriptRoot "ci_run.ps1"

$ArtifactAbs = if ([System.IO.Path]::IsPathRooted($ArtifactRoot)) { $ArtifactRoot } else { Join-Path $RepoRoot $ArtifactRoot }
$OutAbs      = if ([System.IO.Path]::IsPathRooted($Out)) { $Out } else { Join-Path $RepoRoot $Out }

if (-not (Test-Path $CiRun)) { throw "Não encontrei: $CiRun" }

& powershell -ExecutionPolicy Bypass -File $CiRun `
  -Seeds $Seeds `
  -Cmd $Cmd `
  -Workdir $Workdir `
  -VcdPath $VcdPath `
  -ArtifactRoot $ArtifactAbs `
  -Out $OutAbs `
  -RunId $RunId `
  -NoAnalyze

# Print latest run created (best guess: newest dir)
$latest = Get-ChildItem $ArtifactAbs -Directory | Sort-Object Name -Descending | Select-Object -First 1
if ($latest) {
  Write-Host ""
  Write-Host "Created (latest): $($latest.FullName)"
}
exit $LASTEXITCODE
