<#
.SYNOPSIS
    CTU-G Workspace - one-time setup of the synthetic LAN development database.

.DESCRIPTION
    Run once before the first .\Start-CTUG-LAN.ps1, and again whenever the
    launcher reports that the synthetic schema is behind the code (new
    migrations) or the pending-applicant pool should be topped up.

    * creates the git-ignored local secrets file .local\ctug-lan\synthetic.env
      (dedicated session key and outbox encryption key; never overwritten);
    * creates the hard-named MySQL schema ctug_lan_synthetic with a synthetic marker
      (an existing unmarked schema of that name is refused, never adopted);
    * applies the repository migrations to THAT schema only;
    * creates any missing synthetic roles, accounts and pending applicants, and the
      catalogue permissions of features approved in backend/config/dev_features.py;
    * writes synthetic sign-in details to .local\ctug-lan\synthetic-accounts.txt.

    It never selects, migrates or writes ctug_workspace, never copies real records,
    and never resets existing synthetic data unless -Reset is given explicitly.

.PARAMETER Reset
    Drop and recreate the MARKED synthetic schema (asks for confirmation).
#>
[CmdletBinding()]
param([switch]$Reset)

Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'

$Root = $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'

if (-not (Test-Path $Python)) {
    Write-Host 'The backend Python virtual environment is missing (backend\.venv).' -ForegroundColor Red
    Write-Host '  Create it once: cd backend; python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt (and the other requirements-*.txt files).' -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path (Join-Path $Backend '.env'))) {
    Write-Host 'backend\.env is missing (local MySQL credentials).' -ForegroundColor Red
    exit 1
}
if ($Reset) {
    Write-Host 'This permanently deletes ALL data in the synthetic database ctug_lan_synthetic (ctug_workspace is not affected).' -ForegroundColor Yellow
    if ((Read-Host 'Type RESET to continue') -ne 'RESET') { Write-Host 'Cancelled; nothing changed.'; exit 1 }
}

# Scoped to this script: the caller's session environment is restored afterwards.
$scoped = @{ DJANGO_SETTINGS_MODULE = 'config.dev_lan_settings'; CTUG_DEV_LAN_IP = ''; PYTHONIOENCODING = 'utf-8' }
$saved = @{}
foreach ($name in $scoped.Keys) { $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$code = 1
Push-Location $Backend
try {
    foreach ($name in $scoped.Keys) { [Environment]::SetEnvironmentVariable($name, $scoped[$name], 'Process') }
    & $Python 'scripts\ctug_lan_local_secrets.py'
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the local synthetic secrets file.' }
    $arguments = @('manage.py', 'ctug_lan', 'initialize')
    if ($Reset) { $arguments += '--reset' }
    & $Python @arguments
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        Write-Host ''
        Write-Host 'Synthetic LAN database ready. Start everyday development with: .\Start-CTUG-LAN.ps1' -ForegroundColor Green
    } else {
        Write-Host 'Setup did not complete; see the message above. Nothing was written to ctug_workspace.' -ForegroundColor Red
    }
} finally {
    Pop-Location
    foreach ($name in $saved.Keys) { [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
}
exit $code
