# CTU-G Workspace — HTTPS LAN Development Setup Guide

**Audience:** CTU-G Workspace development team (backend, frontend, and mobile integration)  
**Scope:** Windows 11 development PCs, Django REST API, React/Vite frontend, and trusted test phones  
**Mode:** WF-03.01 HTTPS LAN *development* profile; **not** production deployment  
**Reference package:** `CTUG_WF0301_HTTPS_LAN_DEV.zip`  
**Last updated:** 23 November 2026

> **Important:** This guide is based on the scripts in the HTTPS LAN package. It documents how to install and run that implementation; it does **not** mean HTTPS has already been installed or verified on every team member's computer. This remains a `DEBUG=True` development profile. **Use synthetic accounts and data only.** Do not use real student/staff credentials, actual applicant information, or production records. A locally trusted certificate does not make a Vite development server production-ready.

## 1. Overview

The system uses one development PC as the **HTTPS LAN server**:

```text
Development PC or approved test phone
    |
    | HTTPS: https://<SERVER_WIFI_IP>:5173
    v
Vite HTTPS development server (TLS certificate, exact approved IP)
    |
    | /api/* proxied over loopback HTTP
    | X-Forwarded-Proto set to https by the controlled proxy
    v
Django API: http://127.0.0.1:8000  (NOT exposed to LAN)
    |
    v
Local MySQL: ctug_workspace
```

- The **browser or test phone** accesses Vite using HTTPS on TCP port **5173**.
- Vite forwards API requests to the Django backend on **`127.0.0.1:8000`**.
- Django uses secure session/CSRF cookies and the HTTPS proxy guard. Active Role switching is activated only through the explicit HTTPS LAN development gate.
- Both the web app and the friend's CTU-G Workspace mobile app can test **API connectivity** using the same base URL. Native mobile authentication and certificate trust may require additional app-side implementation.
- The former HTTP Option A and localhost-only modes remain separate; **do not combine their activation variables**.

## 2. Requirements

Each teammate hosting the application needs:

1. A Windows 11 development PC with the CTU-G Workspace repository and the existing functional Python `.venv`, Django, MySQL, Node.js, and frontend dependencies.
2. A repository version compatible with the HTTPS installer. The supplied installer specifically requires the **`ronald` branch**, WF-03 checkpoint `42640b9` in Git history, and the **previous HTTP Option A role-context source**. If incompatible, **stop and reconcile the repository; do not force-install**.
3. PowerShell, `git`, and `winget`; the `mkcert` tool for generating locally trusted HTTPS certificates.
4. One to four **IPv4 addresses assigned to active physical adapters** on a **Private** or **DomainAuthenticated** network. Only RFC1918 private addresses are supported. WSL, Tailscale, ZeroTier, loopback, public addresses, and unassigned historical addresses are rejected.
5. A trusted, isolated test LAN and Windows Firewall rules restricting inbound **TCP/5173** to approved test devices. Do **not** expose TCP/8000, use port forwarding, or create a public tunnel.
6. Synthetic, approved, multi-role test accounts for verifying role switching; no live institutional credentials or personal data.

**Example current hosting IP:** `192.168.100.46` (an example from one developer's Wi-Fi). **Do not copy this blindly**—each hosting PC must use its own actual assigned IP.

## 3. Find the current hosting PC's LAN IP

Run in PowerShell:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.AddressState -eq 'Preferred' } |
    Select-Object InterfaceAlias, IPAddress, InterfaceIndex

Get-NetConnectionProfile |
    Select-Object InterfaceAlias, NetworkCategory
```

Choose the **Wi-Fi or Ethernet** address on the intended physical private network. Example:

```text
Wi-Fi    192.168.100.46
```

If your Wi-Fi network is marked **Public**, do not bypass the HTTPS launcher checks. Use an approved trusted private test network and have an authorized operator configure its network profile appropriately.

**Important distinction:** Your friend's phone has its **own** IP; you usually **do not add the phone's IP** to Django `ALLOWED_HOSTS`. `-LanIps` means the approved **server IP(s) assigned to your PC**, not client IPs.

## 4. One-time HTTPS source installation (per compatible checkout)

**Skip this section if the HTTPS source is already installed in this checkout.** Re-running the installer over existing HTTPS files is intentionally refused to prevent overwrites.

First stop any Django/Vite servers. Obtain `CTUG_WF0301_HTTPS_LAN_DEV.zip` from the team-maintained, verified package location. Do not replace it with an unofficial version. From PowerShell, set **your own repository path**:

```powershell
$repo = 'C:\path\to\CTU-G Workspace'  # CHANGE THIS
$zip = "$HOME\Downloads\CTUG_WF0301_HTTPS_LAN_DEV.zip"
$folder = "$HOME\Downloads\CTUG_HTTPS_LAN_DEV"

Expand-Archive -LiteralPath $zip -DestinationPath $folder -Force

powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File "$folder\Apply-CTUG-HTTPS-LAN.ps1" `
    -RepoRoot $repo

if ($LASTEXITCODE -ne 0) {
    throw 'HTTPS installation refused. Stop; do not force changes.'
}

Set-Location $repo
git status --short
```

The installer verifies the package's file hashes, checks the known settings anchor, backs up `backend/config/settings.py`, adds five HTTPS-related code/test files, updates only that settings file, runs **13 Python gate tests**, and performs Python compilation checks. It **does not** edit `.env`, migrate MySQL, enable protected governance writes, commit, or push.

Record the displayed backup folder, e.g.:

```text
%USERPROFILE%\Downloads\CTUG_WF0301_HTTPS_LAN_BACKUP_<timestamp>
```

**If installation refuses:** preserve the repository and share the exact failure message with the maintainer. Do not use `git reset --hard`, force Git patching, delete other files, or manually remove the security guards.

> **Team-source option:** Once the HTTPS source has been reviewed, tested, and committed on the approved team branch, teammates should normally **pull that commit** instead of re-running the one-time installer. The certificate and startup procedure below are still performed separately on each hosting machine.

## 5. One-time local TLS certificate setup

Install `mkcert` if necessary:

```powershell
winget install -e --id FiloSottile.mkcert
```

Open a **new** PowerShell terminal after installation:

```powershell
mkcert -version

$folder = "$HOME\Downloads\CTUG_HTTPS_LAN_DEV"
$ips = '192.168.100.46'  # REPLACE with current hosting PC Wi-Fi/Ethernet IP

powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File "$folder\Setup-CTUG-HTTPS-Certificate.ps1" `
    -LanIps $ips
```

The script runs `mkcert -install` and creates the TLS certificate and private server key outside the repository:

```text
%LOCALAPPDATA%\CTUGWorkspace\lan-https\ctug-lan-cert.pem
%LOCALAPPDATA%\CTUGWorkspace\lan-https\ctug-lan-key.pem
```

It also prints the location of **`rootCA.pem`**, the **public root certificate** that test devices may need to trust. You can rediscover the CA directory by running:

```powershell
mkcert -CAROOT
```

**Certificate security rules:**

- **Never** commit TLS keys or the mkcert root CA private key to Git or upload them to chat/shared storage.
- **Never** share `rootCA-key.pem`; it can be used to create certificates trusted by devices that installed the corresponding root CA.
- The public `rootCA.pem` is shareable only through a trusted, verified team channel with the test device owner's consent. Verify its fingerprint through a separate trusted channel where possible.
- Each hosting developer has a locally generated CA and server certificate; test devices must trust the correct developer's CA.
- If the script says `TLS certificate/key already exists`, **do not overwrite them blindly**. Reuse the existing certificate for unchanged IPs, or coordinate a controlled regeneration if the set of IP addresses changes.

### More than one server IP

If the PC truly has two qualifying physical private LAN IP addresses, pass both to **certificate generation and both startup scripts**, e.g.:

```powershell
$ips = '192.168.100.46,192.168.1.239'  # EXAMPLE ONLY
```

All IPs must be assigned to the **same hosting PC**; 1–4 approved IPs are supported. The certificate must include every selected IP in its Subject Alternative Names (SANs). A change in the IP list may require regenerating the certificate after preserving the old cert/key and reviewing trust impact.

## 6. Everyday HTTPS startup (two PowerShell terminals)

**Do not start HTTPS mode with plain `python manage.py runserver` and `npm run dev`.** Those commands do not activate the explicit HTTPS configuration. Stop old servers with `Ctrl+C` first; ensure port **5173** is free on the approved interface.

Set the **same `$repo`, `$folder`, and `$ips`** in both terminals.

### Terminal A — Django backend

```powershell
$repo = 'C:\path\to\CTU-G Workspace'  # CHANGE THIS
$folder = "$HOME\Downloads\CTUG_HTTPS_LAN_DEV"
$ips = '192.168.100.46'               # CHANGE THIS

powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File "$folder\Start-CTUG-HTTPS-Backend.ps1" `
    -RepoRoot $repo `
    -LanIps $ips
```

Expected: Django `check` passes and Django listens at **`http://127.0.0.1:8000` only**. That local HTTP hop is intentional; **Vite is the HTTPS entry point**.

### Terminal B — Vite HTTPS frontend

```powershell
$repo = 'C:\path\to\CTU-G Workspace'  # SAME PATH
$folder = "$HOME\Downloads\CTUG_HTTPS_LAN_DEV"
$ips = '192.168.100.46'               # SAME IP LIST

powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File "$folder\Start-CTUG-HTTPS-Frontend.ps1" `
    -RepoRoot $repo `
    -LanIps $ips
```

Expected output includes:

```text
CTU-G HTTPS development: https://192.168.100.46:5173/
```

Open from the host PC or a trusted test device:

```text
https://192.168.100.46:5173/
```

API base URL for the friend's mobile client (after its TLS trust is configured):

```text
https://192.168.100.46:5173/api/v1/
```

**Never use `http://` for these HTTPS tests.** Do not proceed past certificate errors or disable certificate validation. If Vite cannot bind to the address, recheck the currently assigned Wi-Fi/Ethernet IP, adapter status, network profile, and whether another process already uses port 5173.

### `.env` behavior

The HTTPS startup scripts set the necessary environment variables **for their own processes**, including the explicit HTTPS acknowledgment, Secure cookies, approved hosts and CSRF origins, and the HTTPS public URL. They do **not** rewrite `backend/.env` or database secrets. In HTTPS mode, do **not** simultaneously activate `CTUG_ROLE_CONTEXT_LAN_DEV_ACK` or `CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK`; the scripts clear those acknowledgments in their own process scope.

A developer may retain the previous HTTP `.env` for separate synthetic-data tests, but **must use the supplied launchers for HTTPS mode**. Avoid manually changing just `WORKSPACE_HTTPS=1` in `.env`—that does not establish a trusted TLS listener or satisfy the new gate.

## 7. Enable a trusted test phone / mobile app

1. Connect the phone to a network that can reach the hosting PC's selected Wi-Fi/Ethernet IP; verify Wi-Fi client isolation and Windows Firewall do not block it.
2. With the device owner's consent, **securely transfer only the public `rootCA.pem`** belonging to the hosting developer's mkcert CA. Do **not** transfer `rootCA-key.pem` or the server's private key.
3. Install and explicitly trust that certificate according to the phone's OS requirements. The exact controls vary by Android/iOS version and device management policy.
4. Browse to `https://<SERVER_IP>:5173/`. The connection must succeed **without a certificate warning**.
5. For a **native Android app**, the app may **not** trust user-installed CAs by default; a debug-only network security configuration may be needed. For iOS, an installed certificate may require separate full-trust enablement. **Never bypass TLS verification in app code.**
6. Point the app's **development API base URL** to `https://<SERVER_IP>:5173/api/v1/`. Test connectivity first with non-sensitive endpoints and synthetic data.
7. Mobile login and role switching require deliberate cookie/CSRF **or** token authentication integration. Working browser HTTPS does **not** by itself mean the native app can authenticate.

**Important:** A client phone does **not** need to be added to `WORKSPACE_ALLOWED_HOSTS`; approved **server** addresses go there. Limit which phone IPs can connect through appropriately scoped firewall rules instead.

## 8. Security and functional acceptance checklist

Record a pass/fail for each item. Do not commit or announce HTTPS readiness until the required local checks pass.

- [ ] Only approved current physical private LAN server IPs are configured.
- [ ] The HTTPS installer completed and its **13 gate tests** passed, or the equivalent reviewed source was pulled from Git.
- [ ] `mkcert` certificate is valid for **every configured server IP**.
- [ ] Host browser opens `https://<SERVER_IP>:5173/` without warnings.
- [ ] Phone browser opens the same URL without bypassing certificate checks.
- [ ] HTTPS backend starts through `Start-CTUG-HTTPS-Backend.ps1`, with Django on `127.0.0.1:8000` only.
- [ ] HTTPS frontend starts through `Start-CTUG-HTTPS-Frontend.ps1`, without an extra HTTP development listener.
- [ ] Synthetic test-account login works with Secure session cookies; CSRF-protected requests work.
- [ ] An approved multi-role test account sees Active Role and switches **Instructor ↔ School Admin** correctly.
- [ ] Switching role changes server-authorized permissions and dashboard navigation.
- [ ] Unassigned/revoked roles and unauthorized operations are refused.
- [ ] School Admin does **not** gain Technical Super Admin protected governance access; protected writes/executor remain gated.
- [ ] Windows Firewall restricts **TCP/5173** to approved test devices; **TCP/8000** is not exposed to LAN.
- [ ] No real institutional credentials, student records, applicant personal information, or production database migrations were used.

### Optional Django guard tests (no intended database mutation)

Run in a separate terminal; the command uses the repository's existing isolated test settings:

```powershell
Set-Location 'C:\path\to\CTU-G Workspace\backend'  # CHANGE THIS

$env:CTUG_ROLE_CONTEXT_HTTPS_LAN_DEV_ACK = ''
$env:CTUG_ROLE_CONTEXT_LAN_DEV_ACK = ''
$env:CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK = ''

.\.venv\Scripts\python.exe manage.py test `
    apps.accounts.test_wf0301_https_lan_proxy `
    --settings=config.test_settings `
    --noinput

if ($LASTEXITCODE -ne 0) { throw 'HTTPS proxy guard tests failed.' }
```

**Do not run `python manage.py migrate` merely to make role switching appear.** Existing pending `access_control` migrations are a separate, approval-gated workflow.

## 9. Common issues and fixes

| Symptom | Likely cause | Safe action |
|---|---|---|
| `LAN role switching requires normal, DEBUG-only local settings` | Started Django normally or mixed HTTP/HTTPS environment flags | Stop the server; launch through `Start-CTUG-HTTPS-Backend.ps1`. Check output; don't weaken the gate. |
| Launcher refuses an IP | Address is old, unassigned, virtual, or on a Public network | Check `Get-NetIPAddress`, `Get-NetAdapter`, `Get-NetConnectionProfile`; select an eligible physical private LAN IP. |
| Certificate error / `ERR_CERT_AUTHORITY_INVALID` | mkcert CA not trusted on this device | Trust the correct public development root CA through OS-approved steps; never click through warnings. |
| Certificate name/IP mismatch | Current server IP isn't in certificate SAN list | Coordinate certificate regeneration for the exact new IP set; don't disable hostname validation. |
| HTTPS frontend won't start / port in use | Previous Vite instance still listening on 5173 | Stop the old instance; don't silently change ports (gate and certificates expect 5173). |
| API returns HTTP 400 `DisallowedHost` | Opened the app using an unapproved hostname/IP | Use exactly the IP passed to `-LanIps`; don't expand the host list to unrelated virtual/public addresses. |
| Login works but role selector missing | HTTPS role gate wasn't activated, wrong URL/server, or account lacks multiple eligible roles | Confirm both launchers were used, then check server session response and account role eligibility. |
| Phone cannot connect but PC can | Firewall, Wi-Fi isolation, network route, or certificate trust | Check network access, firewall scope, and root CA trust on phone. Do not expose Django directly. |
| Native app HTTPS works but API login fails | App has not implemented supported session/cookie/CSRF or token flow | Treat this as a mobile authentication integration task; do not disable CSRF or permissions. |
| Installer refuses because files exist | HTTPS patch is already installed, or source differs | Inspect the repository and installer output; do not overwrite or force-install. |
| Warning about 2 unapplied migrations | Separate database workflow status | **Do not migrate** as part of HTTPS troubleshooting. |

## 10. Stop servers and rollback

To stop development servers, press **Ctrl+C** in both HTTPS launcher windows.

If a **fresh, uncommitted** HTTPS source installation must be rolled back, use the exact backup directory printed by the installer:

```powershell
$repo = 'C:\path\to\CTU-G Workspace'  # CHANGE THIS
$folder = "$HOME\Downloads\CTUG_HTTPS_LAN_DEV"
$backup = "$HOME\Downloads\CTUG_WF0301_HTTPS_LAN_BACKUP_<actual_timestamp>"  # CHANGE THIS

powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File "$folder\Restore-CTUG-HTTPS-LAN.ps1" `
    -RepoRoot $repo `
    -BackupDir $backup
```

The rollback script verifies settings and file hashes; it will refuse if later edits are present. Once HTTPS source changes are **committed**, use a reviewed Git revert rather than deleting files manually. Rolling back source does **not** revoke installed mkcert CA trust or delete generated keys: those are separately managed on each device.

## 11. Team roles and handoff

| Responsibility | What to record/share |
|---|---|
| Hosting developer | Approved LAN server IP(s), PC name/adapter, whether source was installed or pulled, HTTPS URL, test results |
| Backend developer | Django settings check, login/session/CSRF checks, role-context validation, permission denial results |
| Frontend developer | HTTPS Vite startup, browser trust, navigation and role switcher acceptance |
| Mobile developer | Phone OS/version, certificate trust result, HTTPS API connectivity, chosen mobile authentication design |
| Team reviewer | Firewall scope, absence of live data, unchanged protected gates, and decisions before any deployment |

**Do not share:** `.env`, passwords, login cookies, API tokens, certificate/private CA keys, real student data, or privileged executor credentials.

## 12. What this does not complete

This procedure enables **HTTPS LAN development**, not institutional production hosting. Production readiness still requires a hardened reverse proxy/application server, `DEBUG=False`, trustworthy device/certificate management, secure native mobile authentication and revocation, privacy review, monitoring, backups, and separate approvals for protected role/permission governance operations.

**Primary source:** The scripts and source files supplied in `CTUG_WF0301_HTTPS_LAN_DEV.zip` (particularly its `README.md`, PowerShell installers/launchers, IP validator, Python HTTPS gate, proxy guard, and Vite launcher). For mkcert background, see <https://github.com/FiloSottile/mkcert>.
