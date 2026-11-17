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
- [ ] HTTPS, secure cookie and trusted-origin configuration reviewed for deployment (`WORKSPACE_DEPLOYMENT_PROFILE=production`, section 5A); no secrets in committed files or built frontend assets.
- [ ] Daily `clearsessions` schedule installed and its first run recorded (section 5B).
- [ ] Service-separated permissions tested; no Django Superuser automatic Workspace bypass; account-role and Deny matrix passes.
- [ ] Email sender identity, app credential rotation, backend delivery behavior, worker leases/retries and alerting approved independently.
- [ ] Logging/retention/privacy and user rights assessed; no plaintext recipients, hashes or reset tokens.
- [ ] Operational alarms, queue monitoring, incident escalation, off-site backup policy and **test restore evidence**.
- [ ] E2E and campus UAT signed; accessibility/mobile-browser checks and performance thresholds evaluated.
- [ ] Deployment/recovery owner, exact version/revision, changes, and rollback trigger recorded.

## 5A. Session and security settings (WF-01.06, owner-approved 17 Nov 2026)

These are read and validated by `backend/config/security_settings.py` at startup. Invalid or inconsistent values stop Django with an `ImproperlyConfigured` message that names the variable but never shows any value. Put real values only in your untracked `backend/.env` or the deployment's secret store.

| Variable | Default | Meaning |
|---|---|---|
| `WORKSPACE_DEPLOYMENT_PROFILE` | `local` | `local` allows plain HTTP for development. `production` refuses to start unless `WORKSPACE_HTTPS=1`, `DJANGO_DEBUG` is off and `WORKSPACE_ALLOWED_HOSTS` has no `*`. |
| `DJANGO_DEBUG` | off | `1` turns on Django debug pages. **Local development tools that require DEBUG** (`config.review_local_settings` and the `*_local_dev` management commands) need `DJANGO_DEBUG=1` in your local `.env`. Never in production. |
| `WORKSPACE_HTTPS` | off | `1` makes the session and CSRF cookies Secure and redirects HTTP to HTTPS. Required for production. |
| `WORKSPACE_SSL_REDIRECT` | on when HTTPS | `0` only if a verified reverse proxy already redirects HTTP to HTTPS. |
| `WORKSPACE_TRUST_PROXY_SSL_HEADER` | off | `1` trusts `X-Forwarded-Proto: https`. Set only when the proxy is verified to strip and set this header itself; otherwise clients could forge HTTPS. Requires `WORKSPACE_HTTPS=1`. |
| `WORKSPACE_HSTS_SECONDS` | `0` | HSTS lifetime. Start small (for example 3600) after HTTPS is verified on every host; requires `WORKSPACE_HTTPS=1`. |
| `WORKSPACE_CSRF_TRUSTED_ORIGINS` | none | Comma-separated exact origins (`https://host[:port]`) only when the browser origin differs from the Django host, for example behind a proxy. No wildcards; https only when HTTPS is on. |
| `WORKSPACE_SESSION_IDLE_SECONDS` | `1800` | D-18: a session ends after 30 minutes without activity. |
| `WORKSPACE_SESSION_ABSOLUTE_SECONDS` | `28800` | D-18: a session ends 8 hours after sign-in, whatever the activity. |

Always on, not configurable: HttpOnly session and CSRF cookies (D-29; the browser takes the CSRF token from `GET /api/v1/auth/csrf/`), SameSite=Lax, no cross-origin (CORS) access and never credentialed CORS. Production host names, proxy and certificate details must be verified before activation; none are assumed here.

Local HTTP development needs none of these variables. After upgrading, every existing signed-in session ends once (sessions created before WF-01.06 have no sign-in timestamp) and users sign in again.

## 5B. Expired-session cleanup (WF-01.06 D-30, owner-approved 17 Nov 2026)

Session expiry is enforced on every request by `SessionTimeoutMiddleware`; cleanup only removes old rows and is **not** part of security enforcement. Run Django's built-in command once a day:

```powershell
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend"
.\.venv\Scripts\python.exe manage.py clearsessions
```

It deletes only rows in `django_session` whose expiry has passed; valid sessions are untouched. It needs the normal database settings and no other privileges or secrets.

Scheduler templates (adapt paths and the service account; **do not install on a server without verified deployment access and approval**):

- **Windows Task Scheduler** (development machine or Windows host): create a daily task that runs `<repo>\backend\.venv\Scripts\python.exe manage.py clearsessions` with "Start in" set to `<repo>\backend`, under a non-administrator account that can read the backend `.env`, with "Run whether user is logged on or not" and no stored credentials beyond that account.
- **Linux cron** (deployment): `17 3 * * * cd /srv/ctug/backend && ./.venv/bin/python manage.py clearsessions >> /var/log/ctug/clearsessions.log 2>&1`, run as the application's unprivileged user with the same environment as the web process (environment file readable only by that user).
- **systemd timer** (deployment alternative): a `ctug-clearsessions.service` (`Type=oneshot`, `User=` the application user, `EnvironmentFile=` the protected environment file, `WorkingDirectory=` the backend directory, `ExecStart=` the command above) plus a `ctug-clearsessions.timer` with `OnCalendar=daily` and `Persistent=true`.

Record the schedule, owner and first successful run in the operations records (section 7).

## 6. Safe repository/archive checklist

Do not distribute workspace source archives containing `.env`, `.git`, `.venv`, `node_modules`, local SQL backups, student data, test secrets, logs or build caches. Earlier reviewed source ZIP was reported to contain `.env`; treat that archive as sensitive. Prefer tracked-source export and a separately reviewed secrets configuration process. If secret values were shared outside trusted recipients, coordinate credential rotation. Never add a real `.env` to the repository.

## 7. Operations records required later

**Deployment record:** tag/commit, approvals, exact config version (names only), migrations, service flags, tests, operator and rollback decision.  
**Worker record:** deployment version, queue scope, retry/dead-letter alerts, delegated owner and manual recovery steps.  
**Backup record:** time, location reference (not password), retention, restoration test, measured RPO/RTO and sign-off.  
**Incident record:** severity, containment, notification duties, affected records/period and postmortem.

This runbook is a starter for **safe local work and release gates**; it is deliberately **not** a command-by-command production deployment manual without a defined hosting environment and approved operations architecture.
