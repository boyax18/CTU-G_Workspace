# CTU-G Workspace
Integration of School Systems

The account identifier is displayed as **CTU-G ID** for every role. Its database column remains `accounts.school_id`, and API requests and responses continue to use `school_id`.

## LAN development (synthetic data only)

From the repository root in PowerShell:

```powershell
.\Initialize-CTUG-LAN.ps1   # once: synthetic database ctug_lan_synthetic, local keys, synthetic accounts
.\Start-CTUG-LAN.ps1        # every day: detects the Wi-Fi address, starts Django + Vite, prints the URL
```

Features become available through the central registry `backend/config/dev_features.py`, never by editing
the launcher. Details, accounts and troubleshooting: `docs/operations/LOCAL_SETUP_RELEASE_RUNBOOK_DRAFT.md` §2A.
