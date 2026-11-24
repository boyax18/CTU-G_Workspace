# CTU-G Workspace
Integration of School Systems

The account identifier is displayed as **CTU-G ID** for every role. Its database column remains `accounts.school_id`, and API requests and responses continue to use `school_id`.

## Development startup

From the repository root in PowerShell (uses `backend/.env`, i.e. `ctug_workspace` and your existing accounts):

```powershell
.\Start-CTUG-LAN.ps1          # LAN: detects the Wi-Fi address, starts Django + Vite, prints the URL
.\Start-CTUG-LAN.ps1 -Local   # this laptop only: adds the loopback applicant-decision profile
```

Feature availability comes from `backend/config/dev_features.py`, never from editing the launcher.
Details and troubleshooting: `docs/operations/LOCAL_SETUP_RELEASE_RUNBOOK_DRAFT.md` §2A.
§2A.
