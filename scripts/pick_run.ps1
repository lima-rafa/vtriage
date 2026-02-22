param(
  [string]$ArtifactRoot = "artifacts",
  [string]$Out = "report",
  [string]$Format = "html,md",
  [int]$Pick = -1,
  [switch]$Latest,
  [switch]$Interactive,
  [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ArtifactAbs = if ([System.IO.Path]::IsPathRooted($ArtifactRoot)) { $ArtifactRoot } else { Join-Path $RepoRoot $ArtifactRoot }
$OutAbs      = if ([System.IO.Path]::IsPathRooted($Out)) { $Out } else { Join-Path $RepoRoot $Out }

if (-not (Test-Path $ArtifactAbs)) {
  throw "Não existe ArtifactRoot: $ArtifactAbs"
}

$runs = Get-ChildItem $ArtifactAbs -Directory |
  Where-Object { $_.Name -like "run_*" } |
  Sort-Object Name -Descending

if (-not $runs) {
  throw "Nenhum run encontrado em: $ArtifactAbs"
}

Write-Host ""
Write-Host "Available runs (newest first):"
for ($i=0; $i -lt $runs.Count; $i++) {
  Write-Host ("[{0}] {1}" -f $i, $runs[$i].FullName)
}

$runDir = $null
if ($Latest) {
  $runDir = $runs[0].FullName
} elseif ($Pick -ge 0 -and $Pick -lt $runs.Count) {
  $runDir = $runs[$Pick].FullName
} elseif ($Interactive) {
  $ans = Read-Host "Digite o índice do run para analisar"
  if ($ans -match '^\d+$' -and [int]$ans -lt $runs.Count) {
    $runDir = $runs[[int]$ans].FullName
  } else {
    throw "Índice inválido: $ans"
  }
} else {
  Write-Host ""
  Write-Host "Use -Latest, -Pick <idx> ou -Interactive."
  exit 2
}

Write-Host ""
Write-Host "Analyzing: $runDir"
& vtriage analyze $runDir --out $OutAbs --format $Format

$reportHtml = Join-Path $OutAbs "report.html"
if (-not $NoOpen -and (Test-Path $reportHtml)) {
  Start-Process $reportHtml
}

Write-Host "Report: $reportHtml"
exit $LASTEXITCODE
