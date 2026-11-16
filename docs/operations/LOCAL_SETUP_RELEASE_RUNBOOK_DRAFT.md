# CTU-G Workspace — Local Setup and Release Readiness Runbook (Draft)

**Document ID:** CTUG-OPS-001 | **Date:** November 11, 2026  
**Classification:** Non-secret team instructions, **development only**.  
**Caution:** Source checkout was not executed from this document. Confirm package scripts, Python dependencies and DB configuration against current repo before relying on commands.

## 1. Architecture in scope

- Web: React + TypeScript + Vite + Tailwind in `frontend/`.
- API: Django + Django REST Framework in `backend/`, browser sessions + CSRF.
- Local development DB: MySQL, previously reported as database `ctug_workspace` and server 8.4.13. This is **not** a production configuration endorsement.
- Database design reference: protected `docs/database/full_schema.dbml`. **Never** run migrations simply because design tables appear in DBML.
- Django framework Superuser is separate from Workspace Admin and Technical Super Admin application authority.

## 2. Before local startup (Windows PowerShell)

1. Use your **existing repo checkout**, not a ZIP containing `.env` or `node_modules`.
2. Check that you are on the expected branch and have no unreviewed changes:

```powershell
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace"
git status --short --branch
git rev-parse --show-toplevel
```

3. Confirm a local untracked backend `.env` exists only on your own machine; use `backend/.env.example` for a shareable list of required keys. **Do not print, paste, copy to docs or commit real passwords.**
4. Verify your local MySQL service is available. The current settings/active database engine must come from `backend/config/settings.py` and sanitized environment variable names, not this older checkpoint.
5. Do **not** enable recovery SMTP, outbox worker, registration-review routes or permission grants as part of normal startup.

## 3. Start backend and frontend in separate terminals

**Terminal 1 — backend:**

```powershell
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend"
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py showmigrations
python manage.py runserver 127.0.0.1:8000
```

`showmigrations` is a **read-only inspection**. Do not run `migrate`, `makemigrations`, admin bootstrap, seeding, or worker commands without reviewed changes and a separate authorization. If the virtual environment does not exist on a fresh machine, follow your repo's actual Python dependency manifest first; this document does not guess a requirements-file name.

**Terminal 2 — frontend:**

```powershell
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\frontend"
npm install
npm run dev
```

Use the **actual Vite Local URL** printed by the terminal (`localhost:5173` or another free port). `npm run build` is the known production build script, but this does not deploy the project. Do not use `npm run server` in `backend/`; the Django server is started through `manage.py`, while npm scripts belong in `frontend/`.

## 4. Safe troubleshooting

| Symptom | First read-only check | Not the remedy |
|---|---|---|
| Vite `ECONNREFUSED 127.0.0.1:8000` | Is `python manage.py runserver` actually running? Check its terminal and proxy target. | Do not disable CSRF or authorization to hide proxy error. |
| `npm` ENOENT missing `package.json` | Run npm inside `frontend/` and inspect `frontend/package.json`. | Do not create an unrelated `package.json` in repo root. |
| Login `401` | Account approval/active state, password, and safe API error in server logs. | Do not manually grant Admin or modify login to bypass restrictions. |
| Frontend port already in use | Read Vite's printed alternate port; inspect prior Vite sessions. | Do not assume the app failed to start. |
| Django DB error | Confirm MySQL service and sanitized env key *presence*; inspect migrations read-only. | Do not paste `.env` or credentials into chat/issue tracker. |
| Expected module absent from sidebar | Verify approved permissions/service availability and real implementation status. | Do not seed every role, grant generic access or infer defect from an empty catalogue. |

## 5. Pre-release environment checklist (not yet complete)

- [ ] Explicit campus system owner and security/privacy review of **SRS**, ERD, API, feature flags and approved permission catalogue.
- [ ] Known migration sequence/SQL, isolated database tests, backup verification and rollback plan, particularly AR-6C5D `0004` candidate.
- [ ] HTTPS, secure cookie and trusted-origin configuration reviewed for deployment; no secrets in committed files or built frontend assets.
- [ ] Service-separated permissions tested; no Django Superuser automatic Workspace bypass; account-role and Deny matrix passes.
- [ ] Email sender identity, app credential rotation, backend delivery behavior, worker leases/retries and alerting approved independently.
- [ ] Logging/retention/privacy and user rights assessed; no plaintext recipients, hashes or reset tokens.
- [ ] Operational alarms, queue monitoring, incident escalation, off-site backup policy and **test restore evidence**.
- [ ] E2E and campus UAT signed; accessibility/mobile-browser checks and performance thresholds evaluated.
- [ ] Deployment/recovery owner, exact version/revision, changes, and rollback trigger recorded.

## 6. Safe repository/archive checklist

Do not distribute workspace source archives containing `.env`, `.git`, `.venv`, `node_modules`, local SQL backups, student data, test secrets, logs or build caches. Earlier reviewed source ZIP was reported to contain `.env`; treat that archive as sensitive. Prefer tracked-source export and a separately reviewed secrets configuration process. If secret values were shared outside trusted recipients, coordinate credential rotation. Never add a real `.env` to the repository.

## 7. Operations records required later

**Deployment record:** tag/commit, approvals, exact config version (names only), migrations, service flags, tests, operator and rollback decision.  
**Worker record:** deployment version, queue scope, retry/dead-letter alerts, delegated owner and manual recovery steps.  
**Backup record:** time, location reference (not password), retention, restoration test, measured RPO/RTO and sign-off.  
**Incident record:** severity, containment, notification duties, affected records/period and postmortem.

This runbook is a starter for **safe local work and release gates**; it is deliberately **not** a command-by-command production deployment manual without a defined hosting environment and approved operations architecture.
