<#
.SYNOPSIS
  Deploy the Speedrun anki-sync-server to Fly.io with free-tier guardrails.

.DESCRIPTION
  Run `fly auth login` first (interactive; new Fly accounts must add a card).
  Then run this script. It rewrites app/region in fly.toml, creates the app and
  a single 1GB volume, stores your sync password as a secret, and deploys ONE
  machine (--ha=false) that auto-stops to zero when idle.

.EXAMPLE
  ./fly-deploy.ps1 -App speedrun-sync-frank -Region iad -User frank -Password 'choose-a-strong-pass'
#>
param(
  [Parameter(Mandatory = $true)] [string]$App,
  [Parameter(Mandatory = $true)] [string]$Region,
  [Parameter(Mandatory = $true)] [string]$User,
  [Parameter(Mandatory = $true)] [string]$Password,
  [int]$VolumeSizeGb = 1
)

# Fly writes normal progress to stderr; do NOT let that abort the script. We gate
# on the captured exit code instead, and `throw` still stops us on real failures.
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot

function Get-FlyExe {
  $fly = Get-Command fly -ErrorAction SilentlyContinue
  if (-not $fly) { $fly = Get-Command flyctl -ErrorAction SilentlyContinue }
  if (-not $fly) {
    throw "Fly CLI not found. Install it:  pwsh -c `"iwr https://fly.io/install.ps1 -useb | iex`"  then restart the terminal."
  }
  return $fly.Source
}

# Run a fly command quietly: stderr goes to a temp file (so PowerShell does not
# wrap Fly's normal stderr as scary NativeCommandError records), stdout is
# captured. Echoes combined output, throws on non-zero exit unless -AllowFail,
# and preserves the real exit code in $LASTEXITCODE for the caller.
function Invoke-Fly {
  param([Parameter(Mandatory = $true)][string[]]$FlyArgs, [switch]$AllowFail)
  $errFile = [System.IO.Path]::GetTempFileName()
  try {
    $stdout = & $script:flyExe @FlyArgs 2> $errFile
    $code = $LASTEXITCODE
    $stderr = ''
    if (Test-Path $errFile) { $stderr = [string](Get-Content -Raw -ErrorAction SilentlyContinue $errFile) }
  } finally {
    Remove-Item $errFile -ErrorAction SilentlyContinue
  }
  $combined = (($stdout | Out-String) + $stderr)
  if ($combined.Trim()) { Write-Host $combined.TrimEnd() }
  if (-not $AllowFail -and $code -ne 0) {
    throw ("fly " + ($FlyArgs -join ' ') + " failed (exit $code)")
  }
  $global:LASTEXITCODE = $code
  return $combined
}

$script:flyExe = Get-FlyExe
Write-Host "Using Fly CLI: $script:flyExe"

# Confirm we are logged in before touching anything.
Invoke-Fly @('auth', 'whoami') | Out-Null

# Bake the chosen app + region into fly.toml. CRITICAL: write UTF-8 WITHOUT a BOM,
# because Fly's TOML parser rejects a leading BOM ("invalid character at start").
$toml = Get-Content -Raw -Encoding UTF8 ./fly.toml
$toml = $toml -replace "^\uFEFF", ""
$toml = [regex]::Replace($toml, '(?m)^app\s*=.*$', "app = `"$App`"")
$toml = [regex]::Replace($toml, '(?m)^primary_region\s*=.*$', "primary_region = `"$Region`"")
[System.IO.File]::WriteAllText((Join-Path $PSScriptRoot 'fly.toml'), $toml, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "fly.toml -> app=$App region=$Region"

# Create the app (idempotent: ignore 'already exists/taken' by you).
$create = Invoke-Fly @('apps', 'create', $App) -AllowFail
if ($LASTEXITCODE -ne 0 -and $create -notmatch 'already') {
  throw "fly apps create failed (the name may be taken by someone else; pick another -App)."
}

# One small persistent volume in the SAME region as the machine.
$vols = Invoke-Fly @('volumes', 'list', '--app', $App) -AllowFail
if ($vols -match 'anki_data') {
  Write-Host "Volume 'anki_data' already exists; skipping create."
} else {
  Invoke-Fly @('volumes', 'create', 'anki_data', '--app', $App, '--region', $Region, '--size', "$VolumeSizeGb", '--yes')
}

# Store the sync credential as a secret (username:password, auto-hashed server-side).
Invoke-Fly @('secrets', 'set', "SYNC_USER1=${User}:${Password}", '--app', $App)

# Deploy exactly ONE machine. --ha=false prevents Fly creating a 2nd standby VM.
# Run directly (no redirection) so progress streams live and cleanly.
& $script:flyExe deploy --app $App --ha=false
if ($LASTEXITCODE -ne 0) { throw "fly deploy failed." }

Invoke-Fly @('status', '--app', $App) -AllowFail | Out-Null

Write-Host ""
Write-Host "Done. Sync endpoint:  https://$App.fly.dev/"
Write-Host "Use username '$User' and your password in the desktop + AnkiDroid sync settings."
Write-Host "Verify it is awake:   curl https://$App.fly.dev/health"
