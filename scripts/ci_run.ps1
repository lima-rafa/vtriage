param(
  [int]$Seeds = 20,
  [string]$Cmd = "make sim SEED={seed}",
  [string]$Workdir = ".",
  [string]$ArtifactRoot = "artifacts",
  [string]$RunId = "",
  [string]$VcdPath = "build\waves.vcd",
  [switch]$NoAnalyze,
  [string]$Out = "report"
)

$ErrorActionPreference="Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

# Make paths deterministic (Pattern A): artifacts/report always under repo root
if (-not [System.IO.Path]::IsPathRooted($ArtifactRoot)) {
  $ArtifactRoot = Join-Path $RepoRoot $ArtifactRoot
}
if (-not [System.IO.Path]::IsPathRooted($Out)) {
  $Out = Join-Path $RepoRoot $Out
}

# Resolve workdir to absolute (so Vcd/log copy always works)
$WorkdirAbs = (Resolve-Path $Workdir).Path

if ([string]::IsNullOrWhiteSpace($RunId)) {
  $RunId = "run_" + (Get-Date -Format "yyyy-MM-dd_HH-mm-ss")
}

$runDir   = Join-Path $ArtifactRoot $RunId
$testsDir = Join-Path $runDir "tests"
New-Item -ItemType Directory -Force -Path $testsDir | Out-Null

Write-Host "Run dir: $runDir"
Write-Host "Workdir:  $WorkdirAbs"
Write-Host ""

@{ run_id=$RunId; created_at=(Get-Date).ToString("o"); workdir=$WorkdirAbs; cmd_template=$Cmd } |
  ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $runDir "meta.json")

$failCount = 0

for ($seed=1; $seed -le $Seeds; $seed++) {
  $seedP = "{0:D4}" -f $seed
  $caseDir = Join-Path $testsDir ("seed_" + $seedP)
  New-Item -ItemType Directory -Force -Path $caseDir | Out-Null

  $realCmd = $Cmd.Replace("{seed}", $seed.ToString())
  $logPath = Join-Path $caseDir "log.txt"
  Write-Host "==> seed=$seed :: $realCmd"

  $logAbs = [System.IO.Path]::GetFullPath($logPath)

  # build dir absoluto (à prova de cwd)
  $buildAbs = Join-Path $WorkdirAbs "build"
  $env:BUILD_DIR = $buildAbs
  $env:SEED = $seed.ToString()

  # fonte do VCD sempre absoluta e determinística
  $src = Join-Path $buildAbs "waves.vcd"

  # remove VCD antigo
  if (Test-Path $src) { Remove-Item -Force $src }

  Push-Location $WorkdirAbs
  $cmdline = "$realCmd 1> `"$logAbs`" 2>&1"
  & cmd.exe /d /s /c $cmdline | Out-Null
  $rc = $LASTEXITCODE
  Pop-Location

  if (Test-Path $src) {
    Copy-Item -Force $src (Join-Path $caseDir "waves.vcd")
  } else {
    Write-Host "   -> (no waves generated)" -ForegroundColor Yellow
  }

  if ($rc -ne 0) {
    $failCount++
    @{ seed=$seed; exit_code=$rc } | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $caseDir "fail.json")
    Write-Host "   -> FAIL (rc=$rc)"
  } else {
    Write-Host "   -> PASS"
  }
}

Write-Host ""
Write-Host "Done. Failures: $failCount/$Seeds"

# Copy run path to clipboard (best-effort)
try {
  Set-Clipboard -Value $runDir
  Write-Host "Copied run path to clipboard."
} catch {
  Write-Host "Clipboard not available (ok)."
}

Write-Host "Run created: $runDir"
Write-Host ""

if (-not $NoAnalyze) {
  Write-Host "Running: vtriage analyze $runDir --out $Out --format html,md"
  try { vtriage analyze $runDir --out $Out --format html,md } catch {}
  Write-Host ("Report: " + (Join-Path $Out "report.html"))
}

if ($failCount -gt 0) { exit 1 } else { exit 0 }
