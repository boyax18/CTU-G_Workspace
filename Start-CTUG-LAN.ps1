<#
.SYNOPSIS
    CTU-G Workspace - one-command development startup on the normal development database.

.DESCRIPTION
    Uses backend/.env (ctug_workspace and your existing accounts). Runs a read-only
    preflight, starts Django on 127.0.0.1:8000 and Vite, verifies both, prints the
    application URL and stops both cleanly on Ctrl+C. It never changes the
    database schema, seeds accounts or resets data.

      .\Start-CTUG-LAN.ps1          LAN mode: detects this laptop's Wi-Fi/Ethernet IPv4
                                    address and serves http://<LAN IP>:5173 through the
                                    existing Option A gate (role switching, applicant
                                    and directory reads).
      .\Start-CTUG-LAN.ps1 -Local   Loopback mode: http://127.0.0.1:5173 with the existing
                                    loopback-only decision profile (approve/reject/bulk).

    The launcher is feature-agnostic: modes, settings profiles and feature flags come
    from backend/config/dev_features.py via backend/scripts/ctug_dev_preflight.py.
    Finishing a new module never requires editing this file.

.PARAMETER Local
    Loopback-only mode with the existing applicant-decision profile (this laptop only).

.PARAMETER LanIp
    LAN mode: use this private IPv4 address of a local adapter instead of auto-detection.

.PARAMETER InterfaceAlias
    LAN mode: use the adapter with this name (for example "Wi-Fi" or "Ethernet").

.PARAMETER CheckOnly
    Run detection and the preflight, then exit without starting servers.
#>
[CmdletBinding()]
param(
    [switch]$Local,
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
$StateDir = Join-Path $Root '.local\ctug-dev'
$LogDir = Join-Path $StateDir 'logs'
$Preflight = Join-Path $Backend 'scripts\ctug_dev_preflight.py'
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

function Get-ProcessStamp($Process) {
    try { return $Process.StartTime.ToUniversalTime().ToString('o') } catch { return '' }
}

function Save-ServerRecord([object[]]$Processes) {
    # The record names its owner (this launcher's PowerShell process) so that another
    # start can tell a closed window's leftovers from a launcher that is still running.
    $me = Get-Process -Id $PID
    $servers = @($Processes | Where-Object { $_ } | ForEach-Object { @{ pid = $_.Id; started = (Get-ProcessStamp $_) } })
    $record = @{ owner = @{ pid = $PID; started = (Get-ProcessStamp $me) }; servers = $servers }
    ConvertTo-Json -InputObject $record -Depth 4 | Set-Content -Path $PidFile -Encoding UTF8
}

function Test-SameProcess($Entry) {
    if (-not $Entry -or -not ($Entry.PSObject.Properties.Name -contains 'pid')) { return $null }
    $proc = Get-Process -Id ([int]$Entry.pid) -ErrorAction SilentlyContinue
    if ($proc -and (Get-ProcessStamp $proc) -eq [string]$Entry.started) { return $proc }
    return $null
}

function Stop-LeftoverServers {
    # Only a launcher that is GONE (window closed without Ctrl+C) can leave servers
    # behind. If the recorded owner is still running, refuse instead of stopping its
    # servers. Stop only processes proven to be ours: same PID, same start time and a
    # command line writing to this launcher's log directory. Records without an owner
    # (older format) are never acted on.
    if (-not (Test-Path $PidFile)) { return }
    $record = $null
    try { $record = Get-Content $PidFile -Raw | ConvertFrom-Json } catch { }
    if (-not $record -or -not ($record.PSObject.Properties.Name -contains 'owner')) {
        Remove-Item $PidFile -ErrorAction SilentlyContinue
        return
    }
    $owner = Test-SameProcess $record.owner
    if ($owner -and $owner.Id -ne $PID) {
        Stop-Launcher "CTU-G Workspace is already running from another window (PowerShell PID $($owner.Id))." `
            'Use that window, or stop it there with Ctrl+C before starting again.'
    }
    foreach ($entry in @($record.servers)) {
        $proc = Test-SameProcess $entry
        if (-not $proc) { continue }
        $cim = Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue
        if ($cim -and $cim.CommandLine -and $cim.CommandLine.Contains($LogDir)) {
            Write-Info "Stopping a leftover server from a closed launcher window (PID $($proc.Id))."
            Stop-Tree $proc
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
$workers = @()
$exitCode = 0
try {
    $mode = if ($Local) { 'local' } else { 'lan' }
    $title = if ($Local) { 'Local Development' } else { 'LAN Development' }
    Write-Host ''
    Write-Host "CTU-G Workspace $Dash $title (starting)" -ForegroundColor Cyan
    Test-Prerequisites

    $ip = '127.0.0.1'
    if (-not $Local) {
        $selection = Select-LanAddress
        $ip = $selection.IP
        Write-Info "LAN address: $ip ($($selection.Alias))"
        Show-NetworkDiagnostics $selection
    }

    Stop-LeftoverServers
    foreach ($port in @($BackendPort, $FrontendPort)) {
        $owner = Get-PortListener $port
        if ($owner) {
            Stop-Launcher "Port $port is already in use by $owner." 'Stop that program (for example an earlier dev server) and try again. The launcher never stops processes it did not start.'
        }
    }

    Write-Info 'Checking the database and development features (read-only)...'
    $check = Invoke-Captured $Python ('"' + $Preflight + '" --mode ' + $mode + ' --lan-ip ' + $ip) $Backend @{ PYTHONIOENCODING = 'utf-8' }
    $json = ($check.Out -split "`r?`n" | Where-Object { $_.Trim().StartsWith('{') } | Select-Object -Last 1)
    if (-not $json) {
        $detail = (($check.Err -split "`r?`n") | Where-Object { $_.Trim() } | Select-Object -Last 3) -join ' '
        Stop-Launcher 'The backend preflight could not run.' $detail
    }
    $report = $json | ConvertFrom-Json
    foreach ($warning in @($report.warnings)) { if ($warning) { Write-Warn $warning } }
    if (-not $report.ok) {
        Stop-Launcher ('Preflight refused to start: ' + (@($report.errors) -join ' ')) ''
    }

    $features = @($report.features)
    $approved = @($features | Where-Object { $_.status -ne 'not-in-mode' -and $_.status -ne 'optional' })
    $available = @($features | Where-Object { $_.status -eq 'available' })
    $blocked = @($features | Where-Object { $_.status -eq 'blocked' })

    $backendEnv = @{}
    foreach ($property in $report.backend_env.PSObject.Properties) { $backendEnv[$property.Name] = [string]$property.Value }
    $frontendEnv = @{}
    foreach ($property in $report.frontend_env.PSObject.Properties) { $frontendEnv[$property.Name] = [string]$property.Value }
    $frontendCommand = 'node ' + ((@($report.frontend_args) | ForEach-Object { '"' + $_ + '"' }) -join ' ')
    $appUrl = [string]$report.url

    if ($CheckOnly) {
        Write-Host ''
        Write-Host "Preflight passed: $($report.database) via $($report.settings_module); $($available.Count) of $($approved.Count) mode features available. (-CheckOnly: no servers started)" -ForegroundColor Green
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
    $vite = Start-Logged $frontendCommand $Frontend $frontendEnv $frontendLog
    Save-ServerRecord @($django, $vite)
    Wait-Http "$appUrl/" $vite 90 $frontendLog 'The frontend'

    # Background commands declared by the feature registry (for example a delivery worker).
    $workerLogs = @()
    $index = 0
    foreach ($command in @($report.workers)) {
        if (-not $command) { continue }
        $index++
        $workerLog = Join-Path $LogDir ("worker-$index.log")
        $line = '"' + $Python + '" ' + ((@($command) | ForEach-Object { '"' + $_ + '"' }) -join ' ')
        $workers += Start-Logged $line $Backend $backendEnv $workerLog
        $workerLogs += $workerLog
        Save-ServerRecord (@($django, $vite) + $workers)
    }
    if ($workers.Count -gt 0) {
        Start-Sleep -Seconds 4
        for ($i = 0; $i -lt $workers.Count; $i++) {
            if ($workers[$i].HasExited) {
                Show-LogTail $workerLogs[$i]
                Stop-Launcher 'A background worker stopped during startup (its configuration gates refused it).' "See $($workerLogs[$i])"
            }
        }
    }

    # Verify the real request path and the security posture before claiming success.
    $proxy = Invoke-Probe "$appUrl/api/v1/auth/session/"
    if ($proxy.Status -ne 200 -or $proxy.Body -notmatch '"authenticated"') {
        Stop-Launcher "The frontend API proxy did not reach the backend (HTTP $($proxy.Status))." "See $frontendLog and $backendLog"
    }
    $anonymous = Invoke-Probe "$appUrl/api/v1/admin/school-accounts/"
    if ($anonymous.Status -notin @(401, 403)) {
        Stop-Launcher 'Security check failed: protected data must require sign-in.' "anonymous=$($anonymous.Status)"
    }
    if (-not $Local) {
        $direct = Invoke-Probe "http://$ip`:$BackendPort/api/v1/auth/session/" 1500
        if ($direct.Status -ne 0) { Stop-Launcher 'Security check failed: Django must stay loopback-only behind Vite.' "direct=$($direct.Status)" }
    }

    $featureLine = if ($approved.Count -gt 0 -and $available.Count -eq $approved.Count) { 'Ready' } else { "$($available.Count) of $($approved.Count) ready" }
    Write-Host ''
    Write-Host "CTU-G Workspace $Dash $title" -ForegroundColor Cyan
    Write-Host ''
    Write-Host 'Backend: Running'
    Write-Host 'Frontend: Running'
    Write-Host "Database: $($report.database) (existing development database)"
    Write-Host "Development features: $featureLine"
    Write-Host "Security: Role-based access enforced$(if ($report.role_context) { '; Active Role switching on' })"
    Write-Host ''
    Write-Host "Application: $appUrl" -ForegroundColor Green
    Write-Host ''
    foreach ($f in $available) { Write-Info "+ $($f.title)" }
    foreach ($f in $blocked) { Write-Warn "$($f.title) unavailable: $(@($f.reasons) -join '; ')" }
    foreach ($f in @($features | Where-Object { ($_.status -eq 'not-in-mode' -or $_.status -eq 'optional') -and @($_.reasons).Count -gt 0 })) {
        Write-Info "- $($f.title): $(@($f.reasons) -join '; ')"
    }
    if ($workers.Count -gt 0) { Write-Info "Background workers: $($workers.Count) running (logs: worker-*.log)" }
    Write-Info "Sign in with your existing CTU-G accounts. Logs: $LogDir"
    if (-not $Local) {
        Write-Warn 'Plain HTTP over Wi-Fi: passwords and applicant data are readable on this network. Use only a trusted network.'
    }
    Write-Host ''
    Write-Host 'Press Ctrl+C to stop.' -ForegroundColor Cyan
    try { [Console]::TreatControlCAsInput = $true } catch { }

    while ($true) {
        if (Test-StopKey) { break }
        if ($django.HasExited) { Write-Warn "The backend stopped unexpectedly. See $backendLog"; $exitCode = 1; break }
        if ($vite.HasExited) { Write-Warn "The frontend stopped unexpectedly. See $frontendLog"; $exitCode = 1; break }
        $stopped = @($workers | Where-Object { $_.HasExited })
        if ($stopped.Count -gt 0) { Write-Warn "A background worker stopped unexpectedly. See $LogDir\worker-*.log"; $exitCode = 1; break }
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
        foreach ($worker in $workers) { Stop-Tree $worker }
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
