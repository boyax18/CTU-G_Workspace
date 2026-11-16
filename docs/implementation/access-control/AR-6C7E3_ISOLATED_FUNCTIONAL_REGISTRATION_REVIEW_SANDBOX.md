# AR-6C7E.3 — Isolated Functional Registration Review Sandbox

**Project:** CTU-G Workspace
**Scope:** Local loopback sandbox demonstration only; **never** `ctug_workspace`
**Status:** Add-only integration candidate. No production/live activation.

## Why this approach

The normal CTU-G Workspace backend has unmounted Registration Review routes, and the frontend has a hard-disabled API gate and null route. The user's real development database also has inactive review services and role bindings. This stage does **not** circumvent those controls in the normal application.

The sandbox uses a **new empty MySQL schema** `ctug_review_sandbox` with synthetic accounts. A distinct Django settings module selects the schema by hard-coded name, mounts the existing protected review API only in the sandbox URLconf, and disables SMTP/outbox. A dedicated Vite config aliases the existing gate and route modules *only for the sandbox dev process*. The production frontend files are unchanged. The sandbox is loopback-only (including a request-peer middleware check) and must not be deployed.

## Setup (PowerShell / MySQL Workbench)

1. In MySQL Workbench, while connected to **local MySQL**, run: `CREATE DATABASE ctug_review_sandbox CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;` (Use a fresh, empty schema. Do not import data from `ctug_workspace`.)
2. In your project `backend/` terminal, activate `.venv` and run:

   ```powershell
   $env:CTUG_REVIEW_SANDBOX_ACK = "SANDBOX_ONLY"
   python -B manage.py migrate --settings=config.review_sandbox_settings --noinput
   python -B manage.py seed_review_sandbox --settings=config.review_sandbox_settings
   python -B manage.py seed_review_sandbox --settings=config.review_sandbox_settings --apply --confirm CTUG-REVIEW-SANDBOX-SEED-ONLY
   ```

   The seed command prompts for a **unique sandbox-only Admin password**; do **not** reuse any real Admin password. It creates four clearly fictional accounts, active synthetic services and Admin grants, and three audit receipts. It refuses any nonempty application schema or unexpected target.
3. Start Django in that **same terminal**:

   ```powershell
   python -B manage.py runserver 127.0.0.1:8001 --settings=config.review_sandbox_settings
   ```

4. Start a **second** terminal in `frontend/`:

   ```powershell
   $env:CTUG_REVIEW_SANDBOX_ACK = "SANDBOX_ONLY"
   $env:VITE_CTUG_REVIEW_SANDBOX = "SANDBOX_ONLY"
   npx vite --config vite.review-sandbox.config.ts
   ```

5. Open `http://127.0.0.1:5175` (not the normal port). Log in with `SANDBOX-ADMIN-001` and the unique password. Open **Dashboard → Registration review**. You should see synthetic pending Student and Instructor requests. Approve one; reject the other using an approved code. Confirm that the queue refreshes and the underlying sandbox account statuses change.
6. Log out and log in as `SANDBOX-STUDENT-ACTIVE-001` with the same demo password to confirm there is no Admin Registration Review module.
7. Stop both servers with Ctrl+C. The sandbox remains isolated; no actual students or accounts in `ctug_workspace` were modified.

## Automated checks

```powershell
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend"
python -B manage.py test apps.accounts.test_review_sandbox_boundary --settings=config.test_settings --noinput

cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\frontend"
node --test tests/registration-review-sandbox-boundary.test.mjs
npm run build
```

The normal production frontend build must remain **disabled**. Do not build and deploy the sandbox Vite config. The sandbox itself mounts real API routes, so keep both servers bound to `127.0.0.1` only and use invented data only. The sandbox middleware refuses non-loopback request peers even if a client spoofs a localhost Host header.

## Safety controls / non-goals

- The sandbox settings **force a fixed, distinct schema**, regardless of `backend/.env`'s `DB_NAME`.
- The seed command verifies both configured and connected schema identity, and refuses any other database or nonempty application tables.
- Django review endpoints continue to enforce actual sessions, CSRF, role membership, both active services, and exact effective permissions; React does not grant authority.
- No existing production settings/routes, ERD, migrations, `.env`, or real account table is modified.
- This does **not** activate the normal dev database or constitute a backup/recovery plan; keep the normal activation lock.
- Sandbox records are fictional, but still use a non-reused password and do not publish the demo on a shared network.
- No UI changes are made automatically beyond the sandbox-only Vite aliases.

## Verify API decisions (read only)

After approving/rejecting the two synthetic registrations, in a **third** terminal in `backend/`:

```powershell
$env:CTUG_REVIEW_SANDBOX_ACK = "SANDBOX_ONLY"
python -B manage.py report_review_sandbox --settings=config.review_sandbox_settings
```

The report prints only the four synthetic School IDs, their statuses, and counts of approval/rejection audit receipts. Both decisions should appear if you approved one and rejected one. No changes are made by this report.

**Note:** The unique demo password is shared only among the four synthetic accounts for convenience; never reuse a real credential. To repeat the exercise, create a **fresh** separate sandbox schema rather than modifying or clearing `ctug_workspace`.
