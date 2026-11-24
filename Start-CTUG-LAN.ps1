<#
.SYNOPSIS
    CTU-G Workspace - one-command LAN development (synthetic data only).

.DESCRIPTION
    Detects this laptop's active LAN IPv4 address, runs the synthetic-database
    preflight, starts Django on 127.0.0.1:8000 and Vite on <LAN IP>:5173, verifies
    both, prints the application URL and stops both cleanly on Ctrl+C.

    This launcher is deliberately feature-agnostic. It never names a workflow,
    feature flag or API route: feature availability comes from the central
    registry (backend/config/dev_features.py) through `manage.py ctug_lan
    preflight`. Finishing a new module never requires editing this file.

    One-time setup (first run, or after new migrations): .\Initialize-CTUG-LAN.ps1

.PARAMETER LanIp
    Use this private IPv4 address of a local adapter instead of auto-detection.

.PARAMETER InterfaceAlias
    Use the adapter with this name (for example "Wi-Fi" or "Ethernet").

.PARAMETER CheckOnly
    Detect the network and run the preflight, then exit without starting servers.

.EXAMPLE
    .\Start-CTUG-LAN.ps1
.EXAMPLE
    .\Start-CTUG-LAN.ps1 -InterfaceAlias Ethernet
#>
[CmdletBinding()]
param(
    [string]$LanIp,
    [string]$InterfaceAlias,
    [switch]$CheckOnly
)

Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'

$Root = $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'
$StateDir = Join-Path $Root '.local\ctug-lan'
$LogDir = Join-Path $StateDir 'logs'
$SecretsFile = Join-Path $StateDir 'synthetic.env'
$AccountsFile = Join-Path $StateDir 'synthetic-accounts.txt'
$BackendPort = 8000
$FrontendPort = 5173
$PidFile = Join-Path $StateDir 'servers.json'
$Dash = [char]0x2014

class LauncherStop : System.Exception {
    [string]$Hint
    LauncherStop([string]$message, [string]$hint) : base($message) { $this.Hint = $hint }
}

function Stop-Launcher([string]$Message, [string]$Hint = '') { throw [LauncherStop]::new($Message, $Hint) }
function Write-Info([string]$Text) { Write-Host "  $Text" -ForegroundColor DarkGray }
function Write-Warn([string]$Text) { Write-Host "  WARNING: $Text" -ForegroundColor Yellow }

# ------------------------------------------------------------------ prerequisites
function Test-Prerequisites {
    if (-not (Test-Path $Python)) {
        Stop-Launcher 'The backend Python virtual environment is missing (backend\.venv).' `
            'Create it once: cd backend; python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt (and the other requirements-*.txt files).'
    }
    if (-not (Test-Path (Join-Path $Backend '.env'))) {
        Stop-Launcher 'backend\.env is missing (local MySQL credentials).' 'Copy backend\.env.example to backend\.env and fill in the local MySQL settings.'
    }
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Stop-Launcher 'Node.js was not found on PATH.' 'Install Node.js LTS, then open a new terminal.'
    }
    if (-not (Test-Path (Join-Path $Frontend 'node_modules\vite\package.json'))) {
        Stop-Launcher 'Frontend dependencies are missing (frontend\node_modules).' 'Install them once: cd frontend; npm ci'
    }
    if (-not (Test-Path $SecretsFile)) {
        Stop-Launcher 'The synthetic development database has not been set up yet.' 'Run the one-time setup: .\Initialize-CTUG-LAN.ps1'
    }
}

# ------------------------------------------------------------------ LAN detection
function Test-PrivateIPv4([string]$Address) {
    $ip = $null
    if (-not [System.Net.IPAddress]::TryParse($Address, [ref]$ip)) { return $false }
    if ($ip.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) { return $false }
    $b = $ip.GetAddressBytes()
    return ($b[0] -eq 10) -or ($b[0] -eq 172 -and $b[1] -ge 16 -and $b[1] -le 31) -or ($b[0] -eq 192 -and $b[1] -eq 168)
}

$VirtualPattern = 'Hyper-V|WSL|VirtualBox|VMware|TAP-|Wintun|WireGuard|Tailscale|ZeroTier|OpenVPN|Npcap|Loopback|Bluetooth|Virtual'

function Get-LanCandidates {
    $result = @()
    foreach ($config in @(Get-NetIPConfiguration -ErrorAction SilentlyContinue)) {
        $adapter = $config.NetAdapter
        if (-not $adapter -or $adapter.Status -ne 'Up' -or -not $config.IPv4DefaultGateway) { continue }
        if (-not $adapter.HardwareInterface -or $adapter.Virtual) { continue }
        if ($adapter.InterfaceDescription -match $VirtualPattern -or $adapter.Name -match $VirtualPattern) { continue }
        $metric = 9999
        $route = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -InterfaceIndex $config.InterfaceIndex -ErrorAction SilentlyContinue |
            Sort-Object RouteMetric | Select-Object -First 1
        $ipif = Get-NetIPInterface -InterfaceIndex $config.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue
        if ($route -and $ipif) { $metric = [int]$route.RouteMetric + [int]$ipif.InterfaceMetric }
        foreach ($address in @($config.IPv4Address)) {
            if ($address -and (Test-PrivateIPv4 $address.IPAddress)) {
                $result += [pscustomobject]@{
                    Alias = $adapter.Name; Index = $config.InterfaceIndex; IP = $address.IPAddress
                    Description = $adapter.InterfaceDescription; Metric = $metric
                }
            }
        }
    }
    return @($result | Sort-Object Metric, Alias)
}

function Select-LanAddress {
    if ($LanIp) {
        if (-not (Test-PrivateIPv4 $LanIp)) { Stop-Launcher "-LanIp $LanIp is not a private (RFC 1918) IPv4 address." '' }
        $owned = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $LanIp -ErrorAction SilentlyContinue
        if (-not $owned) { Stop-Launcher "-LanIp $LanIp does not belong to any adapter on this computer." 'Run ipconfig to see the current address.' }
        $adapter = Get-NetAdapter -InterfaceIndex $owned.InterfaceIndex -ErrorAction SilentlyContinue
        if (-not $adapter -or $adapter.Status -ne 'Up') { Stop-Launcher "The adapter for $LanIp is not connected." '' }
        if (-not $adapter.HardwareInterface -or $adapter.InterfaceDescription -match $VirtualPattern) {
            Write-Warn "$LanIp belongs to a virtual/VPN adapter ($($adapter.InterfaceDescription)); other Wi-Fi devices usually cannot reach it."
        }
        return [pscustomobject]@{ Alias = $adapter.Name; Index = $owned.InterfaceIndex; IP = $LanIp; Description = $adapter.InterfaceDescription; Metric = 0 }
    }
    $candidates = @(Get-LanCandidates)
    if ($InterfaceAlias) {
        $match = @($candidates | Where-Object { $_.Alias -eq $InterfaceAlias })
        if ($match.Count -eq 0) {
            $names = ($candidates | ForEach-Object { $_.Alias }) -join ', '
            Stop-Launcher "No connected physical adapter named '$InterfaceAlias' with a private IPv4 address and gateway." "Eligible adapters: $(if ($names) { $names } else { 'none' })"
        }
        return $match[0]
    }
    if ($candidates.Count -eq 0) {
        Stop-Launcher 'No active physical LAN adapter with a private IPv4 address and default gateway was found.' `
            'Connect to Wi-Fi or Ethernet (VPN, WSL, Hyper-V and other virtual adapters are ignored), or pass -LanIp <address>.'
    }
    if ($candidates.Count -eq 1) { return $candidates[0] }

    Write-Host ''
    Write-Host 'More than one LAN adapter is connected:' -ForegroundColor Yellow
    for ($i = 0; $i -lt $candidates.Count; $i++) {
        $c = $candidates[$i]
        Write-Host ("  [{0}] {1,-15} {2}  ({3})" -f ($i + 1), $c.IP, $c.Alias, $c.Description)
    }
    if (-not [Environment]::UserInteractive) {
        Stop-Launcher 'The LAN adapter is ambiguous.' 'Re-run with -InterfaceAlias <name> or -LanIp <address>.'
    }
    $answer = Read-Host "Choose the network other devices will use [1-$($candidates.Count), Enter = 1]"
    if (-not $answer) { $answer = '1' }
    $n = 0
    if (-not [int]::TryParse($answer, [ref]$n) -or $n -lt 1 -or $n -gt $candidates.Count) {
        Stop-Launcher "Invalid choice '$answer'." 'Re-run with -InterfaceAlias <name> or -LanIp <address>.'
    }
    return $candidates[$n - 1]
}

function Show-NetworkDiagnostics($Selection) {
    # Read-only. The launcher never changes the network profile or firewall rules.
    try {
        $netProfile = Get-NetConnectionProfile -InterfaceIndex $Selection.Index -ErrorAction Stop
        if ($netProfile.NetworkCategory -eq 'Public') {
            Write-Warn "Windows treats '$($netProfile.Name)' as a Public network; other devices are usually blocked from reaching this laptop."
            Write-Info 'If they cannot connect, an administrator can mark this trusted network Private in Settings > Network.'
        }
    } catch { }
    try {
        $nodePath = (Get-Command node).Source
        $rules = @(Get-NetFirewallApplicationFilter -Program $nodePath -ErrorAction Stop | Get-NetFirewallRule -ErrorAction Stop |
            Where-Object { $_.Enabled -eq 'True' -and $_.Direction -eq 'Inbound' })
        if (@($rules | Where-Object { $_.Action -eq 'Block' }).Count -gt 0) {
            Write-Warn 'An enabled Windows Firewall rule BLOCKS inbound Node.js; other devices cannot connect until an administrator changes it.'
        } elseif (@($rules | Where-Object { $_.Action -eq 'Allow' }).Count -eq 0) {
            Write-Info 'No inbound firewall rule for Node.js yet. If Windows asks, allow access on Private networks only.'
        }
    } catch { }
}

# ------------------------------------------------------------------ processes
function Get-PortListener([int]$Port) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $listener) { return $null }
    $proc = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    $name = if ($proc) { $proc.ProcessName } else { 'unknown' }
    return "$name (PID $($listener.OwningProcess)) on $($listener.LocalAddress):$Port"
}

function New-StartInfo([string]$FileName, [string]$Arguments, [string]$WorkingDirectory, [hashtable]$Environment) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FileName
    $psi.Arguments = $Arguments
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    foreach ($key in $Environment.Keys) { $psi.EnvironmentVariables[$key] = [string]$Environment[$key] }
    return $psi
}

function Invoke-Captured([string]$FileName, [string]$Arguments, [string]$WorkingDirectory, [hashtable]$Environment) {
    $psi = New-StartInfo $FileName $Arguments $WorkingDirectory $Environment
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $proc = [System.Diagnostics.Process]::Start($psi)
    $stderr = $proc.StandardError.ReadToEndAsync()
    $stdout = $proc.StandardOutput.ReadToEnd()
    $proc.WaitForExit()
    return [pscustomobject]@{ ExitCode = $proc.ExitCode; Out = $stdout; Err = $stderr.Result }
}

function Start-Logged([string]$Command, [string]$WorkingDirectory, [hashtable]$Environment, [string]$LogFile) {
    # cmd.exe redirects the server output into the log; the launcher keeps the PID tree.
    $line = '/d /s /c "' + $Command + ' > "' + $LogFile + '" 2>&1"'
    $psi = New-StartInfo $env:ComSpec $line $WorkingDirectory $Environment
    return [System.Diagnostics.Process]::Start($psi)
}

# Shutdown helpers use .NET calls only: after Ctrl+C PowerShell runs `finally` inside a
# stopping pipeline, where cmdlets and native-command invocations are aborted.
function Stop-Tree($Process) {
    try {
        if ($Process -and -not $Process.HasExited) {
            $psi = [System.Diagnostics.ProcessStartInfo]::new('taskkill.exe', "/PID $($Process.Id) /T /F")
            $psi.UseShellExecute = $false
            $psi.CreateNoWindow = $true
            $killer = [System.Diagnostics.Process]::Start($psi)
            [void]$killer.WaitForExit(15000)
            [void]$Process.WaitForExit(5000)
        }
    } catch { }
}

function Test-PortListening([int]$Port) {
    foreach ($endpoint in [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()) {
        if ($endpoint.Port -eq $Port) { return $true }
    }
    return $false
}

function Write-Plain([string]$Text, [System.ConsoleColor]$Color = [System.ConsoleColor]::Cyan) {
    try {
        $previous = [Console]::ForegroundColor
        [Console]::ForegroundColor = $Color
        [Console]::WriteLine($Text)
        [Console]::ForegroundColor = $previous
    } catch { }
}

function Test-StopKey {
    # Ctrl+C is read as a keypress so that stopping is ordinary code, not an aborted pipeline.
    try {
        while ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            if (($key.Modifiers -band [ConsoleModifiers]::Control) -and $key.Key -eq [ConsoleKey]::C) { return $true }
        }
    } catch { }
    return $false
}

function Save-ServerRecord([object[]]$Processes) {
    $records = @($Processes | Where-Object { $_ } | ForEach-Object {
        @{ pid = $_.Id; started = $_.StartTime.ToUniversalTime().ToString('o') } })
    ConvertTo-Json -InputObject @($records) | Set-Content -Path $PidFile -Encoding UTF8
}

function Stop-LeftoverServers {
    # A previous launcher window may have been closed without Ctrl+C. Stop only
    # processes proven to be ours: same PID, same start time, and a command line
    # that writes to this launcher's log directory. Anything else is left alone.
    if (-not (Test-Path $PidFile)) { return }
    # Windows PowerShell 5.1 emits a JSON array as ONE object; assign before enumerating.
    $records = @()
    try { $parsed = Get-Content $PidFile -Raw | ConvertFrom-Json; $records = $parsed } catch { }
    foreach ($record in $records) {
        if (-not $record -or -not ($record.PSObject.Properties.Name -contains 'pid')) { continue }
        $proc = Get-Process -Id ([int]$record.pid) -ErrorAction SilentlyContinue
        if (-not $proc) { continue }
        $sameStart = $false
        try { $sameStart = ($proc.StartTime.ToUniversalTime().ToString('o') -eq [string]$record.started) } catch { }
        $cim = Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue
        if ($sameStart -and $cim -and $cim.CommandLine -and $cim.CommandLine.Contains($LogDir)) {
            Write-Info "Stopping a leftover server from an earlier session (PID $($proc.Id))."
            & taskkill.exe /PID $proc.Id /T /F *> $null
        }
    }
    Remove-Item $PidFile -ErrorAction SilentlyContinue
}

function Invoke-Probe([string]$Url, [int]$TimeoutMs = 3000) {
    try {
        $request = [System.Net.HttpWebRequest]::Create($Url)
        $request.Proxy = $null
        $request.Timeout = $TimeoutMs
        $request.AllowAutoRedirect = $false
        $request.Accept = 'application/json, text/html'
        $response = $request.GetResponse()
        $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
        $body = $reader.ReadToEnd()
        $status = [int]$response.StatusCode
        $response.Close()
        return [pscustomobject]@{ Status = $status; Body = $body }
    } catch {
        $ex = $_.Exception
        while ($ex -and -not ($ex -is [System.Net.WebException])) { $ex = $ex.InnerException }
        if ($ex -and $ex.Response) {
            $status = [int]$ex.Response.StatusCode
            $ex.Response.Close()
            return [pscustomobject]@{ Status = $status; Body = '' }
        }
        return [pscustomobject]@{ Status = 0; Body = '' }
    }
}

function Wait-Http([string]$Url, $Process, [int]$Seconds, [string]$LogFile, [string]$What) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) {
            Show-LogTail $LogFile
            Stop-Launcher "$What stopped during startup (exit code $($Process.ExitCode))." "See $LogFile"
        }
        if ((Invoke-Probe $Url 2000).Status -eq 200) { return }
        Start-Sleep -Milliseconds 500
    }
    Show-LogTail $LogFile
    Stop-Launcher "$What did not become ready within $Seconds seconds." "See $LogFile"
}

function Show-LogTail([string]$LogFile) {
    if (Test-Path $LogFile) {
        Write-Host '  --- last log lines ---' -ForegroundColor DarkGray
        Get-Content $LogFile -Tail 15 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
    }
}

# ------------------------------------------------------------------ main
$django = $null
$vite = $null
$exitCode = 0
try {
    Write-Host ''
    Write-Host "CTU-G Workspace $Dash LAN Development (starting)" -ForegroundColor Cyan
    Test-Prerequisites

    $selection = Select-LanAddress
    $ip = $selection.IP
    Write-Info "LAN address: $ip ($($selection.Alias))"
    Show-NetworkDiagnostics $selection

    Stop-LeftoverServers
    foreach ($port in @($BackendPort, $FrontendPort)) {
        $owner = Get-PortListener $port
        if ($owner) {
            Stop-Launcher "Port $port is already in use by $owner." 'Stop that program (for example an earlier dev server) and try again. The launcher never stops processes it did not start.'
        }
    }

    # Only two inputs cross into Django; config/dev_lan_settings.py derives the rest.
    $backendEnv = @{
        DJANGO_SETTINGS_MODULE = 'config.dev_lan_settings'
        CTUG_DEV_LAN_IP = $ip
        PYTHONIOENCODING = 'utf-8'
        PYTHONUNBUFFERED = '1'
    }

    Write-Info 'Checking the synthetic database and development features...'
    $check = Invoke-Captured $Python 'manage.py ctug_lan preflight --json' $Backend $backendEnv
    $json = ($check.Out -split "`r?`n" | Where-Object { $_.Trim().StartsWith('{') } | Select-Object -Last 1)
    if (-not $json) {
        $detail = (($check.Err -split "`r?`n") | Where-Object { $_.Trim() } | Select-Object -Last 3) -join ' '
        Stop-Launcher 'The backend preflight could not run (configuration or database error).' $detail
    }
    $report = $json | ConvertFrom-Json
    foreach ($warning in @($report.warnings)) { if ($warning) { Write-Warn $warning } }
    if (-not $report.ok) {
        Stop-Launcher ('Preflight refused to start: ' + (@($report.errors) -join ' ')) ''
    }

    $features = @($report.features)
    $approved = @($features | Where-Object { $_.status -ne 'not-approved' })
    $available = @($features | Where-Object { $_.status -eq 'available' })
    $blocked = @($features | Where-Object { $_.status -eq 'blocked' })

    # The frontend listener script is named by the backend profile, not by this launcher.
    $viteLauncher = Join-Path $Frontend ([string]$report.frontend_script)
    if (-not $report.frontend_script -or -not (Test-Path $viteLauncher)) {
        Stop-Launcher "The LAN frontend listener script is missing: $viteLauncher" ''
    }

    $frontendEnv = @{}
    foreach ($property in $report.frontend_env.PSObject.Properties) { $frontendEnv[$property.Name] = [string]$property.Value }

    if ($CheckOnly) {
        Write-Host ''
        Write-Host "Preflight passed for $ip; $($available.Count) of $($approved.Count) approved features available. (-CheckOnly: no servers started)" -ForegroundColor Green
        foreach ($f in $blocked) { Write-Warn "$($f.title): $(@($f.reasons) -join '; ')" }
        return
    }

    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $backendLog = Join-Path $LogDir 'backend.log'
    $frontendLog = Join-Path $LogDir 'frontend.log'

    Write-Info 'Starting backend (127.0.0.1:8000)...'
    $django = Start-Logged ('"' + $Python + '" manage.py runserver 127.0.0.1:' + $BackendPort) $Backend $backendEnv $backendLog
    Save-ServerRecord @($django)
    Wait-Http "http://127.0.0.1:$BackendPort/api/v1/auth/csrf/" $django 90 $backendLog 'The backend'

    Write-Info "Starting frontend ($ip`:$FrontendPort)..."
    $vite = Start-Logged ('node "' + $viteLauncher + '"') $Frontend $frontendEnv $frontendLog
    Save-ServerRecord @($django, $vite)
    $appUrl = "http://$ip`:$FrontendPort"
    Wait-Http "$appUrl/" $vite 90 $frontendLog 'The frontend'

    # Verify the real request path and the security posture before claiming success.
    $proxy = Invoke-Probe "$appUrl/api/v1/auth/session/"
    if ($proxy.Status -ne 200 -or $proxy.Body -notmatch '"authenticated"\s*:\s*false') {
        Stop-Launcher "The frontend API proxy did not reach the backend (HTTP $($proxy.Status))." "See $frontendLog and $backendLog"
    }
    $anonymous = Invoke-Probe "$appUrl/api/v1/admin/school-accounts/"
    $direct = Invoke-Probe "http://$ip`:$BackendPort/api/v1/auth/session/" 1500
    if ($anonymous.Status -notin @(401, 403) -or $direct.Status -ne 0) {
        Stop-Launcher 'Security check failed: protected data must require sign-in and Django must stay loopback-only.' "anonymous=$($anonymous.Status) direct=$($direct.Status)"
    }

    $featureLine = if ($approved.Count -gt 0 -and $available.Count -eq $approved.Count) { 'Ready' } else { "$($available.Count) of $($approved.Count) ready" }
    Write-Host ''
    Write-Host "CTU-G Workspace $Dash LAN Development" -ForegroundColor Cyan
    Write-Host ''
    Write-Host 'Backend: Running'
    Write-Host 'Frontend: Running'
    Write-Host "Database: Synthetic development database ($($report.database))"
    Write-Host "Development features: $featureLine"
    Write-Host 'Security: Role-based access enforced'
    Write-Host ''
    Write-Host "Application: $appUrl" -ForegroundColor Green
    Write-Host ''
    foreach ($f in $available) { Write-Info "+ $($f.title)" }
    foreach ($f in $blocked) { Write-Warn "$($f.title) unavailable: $(@($f.reasons) -join '; ')" }
    Write-Info "Synthetic sign-in details: $AccountsFile"
    Write-Info "Logs: $LogDir"
    Write-Info 'Plain HTTP on a shared network: use only the synthetic accounts and data.'
    Write-Host ''
    Write-Host 'Press Ctrl+C to stop.' -ForegroundColor Cyan
    try { [Console]::TreatControlCAsInput = $true } catch { }

    while ($true) {
        if (Test-StopKey) { break }
        if ($django.HasExited) { Write-Warn "The backend stopped unexpectedly. See $backendLog"; $exitCode = 1; break }
        if ($vite.HasExited) { Write-Warn "The frontend stopped unexpectedly. See $frontendLog"; $exitCode = 1; break }
        Start-Sleep -Milliseconds 500
    }
} catch [LauncherStop] {
    Write-Host ''
    Write-Host "Cannot start: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Hint) { Write-Host "  $($_.Exception.Hint)" -ForegroundColor Yellow }
    $exitCode = 1
} finally {
    try { [Console]::TreatControlCAsInput = $false } catch { }
    if ($django -or $vite) {
        Write-Plain ''
        Write-Plain 'Stopping CTU-G Workspace...'
        Stop-Tree $vite
        Stop-Tree $django
        $left = ''
        foreach ($port in @($BackendPort, $FrontendPort)) { if (Test-PortListening $port) { $left += " $port" } }
        try { [System.IO.File]::Delete($PidFile) } catch { }
        if (-not $left) { Write-Plain 'Stopped. Backend and frontend are no longer running.' }
        else { Write-Plain "WARNING: port(s)$left still in use; check Task Manager." ([System.ConsoleColor]::Yellow) }
    }
}
if ($exitCode -ne 0) { exit $exitCode }
