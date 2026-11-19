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

## 5C. Database accounts and audit checkpoints (R-2 phase 1 design; NOT applied)

Status: designed and tested on disposable test databases only (`backend/apps/access_control/test_wf0301_r2_audit_integrity.py`). The local application still
connects as MySQL `root`. Applying the accounts below to `ctug_workspace` and changing `backend/.env` need the
owner's separate authorization (decision D-105). Never put passwords in the repository.

- **Runtime account** (for example `ctug_app`, used by the Django application):
  - `GRANT SELECT, INSERT, LOCK TABLES ON ctug_workspace.*`;
  - `GRANT UPDATE, DELETE ON ctug_workspace.<table>` for every table **except** `access_audit_logs`;
  - no DDL, `TRIGGER`, `GRANT OPTION`, `SUPER` or user-management rights.
  - Re-run the per-table `UPDATE, DELETE` grants after a migration adds a table.
- **Migration account** (for example `ctug_migrate`, used only for `manage.py migrate`):
  `CREATE, ALTER, DROP, INDEX, REFERENCES, SELECT, INSERT, UPDATE, DELETE` on `ctug_workspace.*`.
- **Verifier account** (optional): `SELECT` on `ctug_workspace.access_audit_logs` only.
- `root` stays with the database administrator. The tests run with a privileged account because they create
  and drop disposable databases.
- **Checkpoint (prototype):** `manage.py report_access_audit_checkpoint` prints a checkpoint, and
  `--verify <file>` checks the receipts against a checkpoint file kept **outside** the database (for example
  in the D-95 operational record). `--hmac-key-env <NAME>` authenticates it with a key held outside the
  database. Take checkpoints only when no governance operation is running: a receipt that commits late with
  a lower ID makes a later verification fail closed. Cadence, key custody and storage need decision D-105.

## 5D. Session-revocation counter (SR-1; migration 0006 applied locally on 19 Nov 2026, Stage B Gate 2)

Status: `accounts/0006_account_session_revocation_version` is applied to the local `ctug_workspace` (Stage B
Gate 2, 19 November 2026, decision D-106), and all existing sessions were cleared. The non-decrease trigger,
the restricted MySQL accounts and the ERD update are NOT applied (Stage B-2, separate authorization). The owner's
real-account login test (Test A) PASSED on 19 November 2026 (TC-042). Never run `migrate --fake`, a schema rollback or an in-place
restore without the owner's separate authorization.

Local deployment record (Gates 1 and 2; non-sensitive JSON records are kept next to the backup, outside the
repository, as `..._gate1_record.json` and `..._gate2_record.json`):

- **Backup:** `C:\CTUG-Backups\ctug_workspace_pre0006_20261119T095807Z.sql`, 41,752 bytes, SHA-256
  `093c5290181c085fcef37990cbe8d851f063037290450e9f45b8fb1f2cdcfcaf`. The folder and file are restricted to the owner's
  Windows account and SYSTEM. The file holds real account data: never copy it into the repository.
- **Restore verification (Gate 1):** restored into a new scratch schema. All 18 tables matched in row counts,
  `CHECKSUM TABLE` and full row digests, and columns, foreign keys, indexes and constraints were identical. The
  scratch schema was then dropped. **Not tested:** an in-place restore over `ctug_workspace`, and point-in-time
  recovery from the binary logs.
- **Rehearsal (Gate 1) and execution (Gate 2):**
  - exactly two writes, the `ALTER TABLE … ADD COLUMN … CHECK` and one `django_migrations` row;
  - a table rebuild, not an instant change (0.14 s at 6 rows);
  - every other table, and the original account columns, unchanged;
  - 6 accounts at counter 0, and 24 receipts unchanged (checkpoint head unchanged).
- **Session cleanup (Gate 2):** all 5 `django_session` rows were deleted after verification; 0 remained.

Verified backup procedure, for the next deployment. Put credentials in a temporary option file or a login path,
never on the command line:

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe" --defaults-extra-file=<temporary file> --single-transaction --source-data=2 --routines --triggers --events --hex-blob --no-tablespaces --default-character-set=utf8mb4 --set-gtid-purged=OFF --result-file="C:\CTUG-Backups\<name>.sql" ctug_workspace
```

- **Never add `--databases`.** The dump must contain no `CREATE DATABASE` or `USE`, so it can never restore over
  `ctug_workspace` by accident.
- `--source-data=2` takes a brief global read lock to read the binary-log position, so run it only when no other
  connection exists.
- **To prove a backup is restorable:**
  1. Create a new, uniquely named schema.
  2. Pass the raw dump bytes to `mysql.exe <schema>`, not through a PowerShell text pipeline.
  3. Compare counts, checksums and row digests against the source.
  4. Drop the scratch schema.

Migration failure handling:

- **Column added but migration not recorded:** MySQL commits DDL immediately, so the `ALTER` and the
  `django_migrations` insert are separate steps. If the column exists but 0006 is not recorded, STOP. Compare the
  column with its definition, then decide with the owner between `migrate --fake` and a restore. Never re-run
  blindly.
- **Application fails after the migration:** prefer a code-only rollback to the previous commit, leaving the column
  in place (old code ignores it, and inserts use the default 0). **First delete all `django_session` rows:** the
  old receipt-derived session hash is vulnerable to SR-1 and would accept unused older sessions.
- **Restore over `ctug_workspace`:** it can overwrite newer data and reverse revocations, so it needs separate owner
  approval.

Stage B-2 (OPEN; required before any real Technical Super Admin provisioning):

1. Have the DBA install the non-decrease trigger. This needs the TRIGGER privilege, and `SUPER` or
   `log_bin_trust_function_creators` because binary logging is on. Never grant TRIGGER to the runtime or
   migration account.

   ```sql
   CREATE TRIGGER accounts_session_revocation_no_decrease BEFORE UPDATE ON accounts FOR EACH ROW
   BEGIN
     IF NEW.session_revocation_version < OLD.session_revocation_version THEN
       SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'session_revocation_version cannot decrease';
     END IF;
   END
   ```

2. Create the restricted runtime and migration accounts (section 5C) and a separate privileged test-runner
   credential, then switch `backend/.env` (owner action).
3. Start the application; confirm `CURRENT_USER()` and `SHOW GRANTS`.

Schema rollback (unapplying 0006) drops the counter and the SR-1 protection with it. Avoid it: use the code-only
rollback above. If it is ever approved, drop the trigger first, then delete all `django_session` rows.

Restore: a restore that also restores the counter can revive sessions that were revoked after the backup was
taken. After every restore, delete all `django_session` rows. Then re-apply revocations recorded since the
backup from the external operational record. The trigger does not stop a privileged administrator or a table
reload.

## 6. Safe repository/archive checklist

Do not distribute workspace source archives containing `.env`, `.git`, `.venv`, `node_modules`, local SQL backups, student data, test secrets, logs or build caches. Earlier reviewed source ZIP was reported to contain `.env`; treat that archive as sensitive. Prefer tracked-source export and a separately reviewed secrets configuration process. If secret values were shared outside trusted recipients, coordinate credential rotation. Never add a real `.env` to the repository.

## 7. Operations records required later

**Deployment record:** tag/commit, approvals, exact config version (names only), migrations, service flags, tests, operator and rollback decision.  
**Worker record:** deployment version, queue scope, retry/dead-letter alerts, delegated owner and manual recovery steps.  
**Backup record:** time, location reference (not password), retention, restoration test, measured RPO/RTO and sign-off.  
**Incident record:** severity, containment, notification duties, affected records/period and postmortem.

This runbook is a starter for **safe local work and release gates**; it is deliberately **not** a command-by-command production deployment manual without a defined hosting environment and approved operations architecture.
