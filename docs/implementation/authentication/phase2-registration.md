# Phase 2 registration implementation and handoff

## Preflight and scope

The interrupted run had not created registration implementation files. Existing
tracked, deleted, and untracked work was retained. The branch is `ronald` at
`8e1ead5`; the earlier app-directory reorganization remains uncommitted.

The full ERD has 42 tables and 80 relationships. Both DBML files are read-only:

| File | Approved SHA-256 |
| --- | --- |
| `database/full_schema.dbml` | `E9235A87555FFCD50ECB6AB6C1A45F9C7C54E344FF8F269ECC890579F633E4B2` |
| `database/schema.dbml` | `F050F7B910038532CA8E73B283F16A57DEDD6B738FDC74D293E64D539A4AFAC4` |

The relevant preflight confirmed local MySQL 8.4.13, `ctug_workspace`, 16 tables,
22 applied migrations, four active roles (Student, Instructor, Treasurer, Admin),
zero accounts/profiles/grants, and no model or migration drift. Existing account,
profile, access-control models, custom SQL fields, and migrations are reused.

This change implements public Student/Instructor registration only. It does not
implement approval, login/logout, Technical Super Admin, dashboards, permission
mutation services, or additional ERD tables.

## Implemented behavior

- `/register` renders a responsive, labelled form using the existing branding,
  Input, Button, public layout, and theme.
- `/` retains the homepage and its explicitly unfinished embedded login.
- Native page navigation supports the two public routes without another routing
  dependency; unknown routes show a public not-found message.
- Homepage navigation returns to homepage sections from registration. Section
  snapping is disabled on registration so the form scrolls normally.
- The shared client bootstraps CSRF, sends same-origin cookies and the CSRF header,
  maps field errors, bounds network waiting, and never automatically retries POST.
- Ref-based submission locking plus disabled fields/button prevent accidental
  double submission. Successful submission clears form state and shows the review
  message without creating authentication state or opening a dashboard.
- The backend requires anonymous CSRF and trusted Origin checks before parsing,
  hashing, or creating records. It accepts JSON only, with a 16 KiB input limit,
  rejects duplicate JSON keys and unsupported fields, validates strict strings,
  ERD lengths, email, password confirmation, and Django password policies.
- Requested roles resolve from active existing canonical records. The existing
  manager hashes the password. Account and profile are created atomically with
  Pending/inactive state. No AccountRole or permission grant is created.
- Duplicate school IDs, including MySQL collation-equivalent duplicates, return
  the same neutral acknowledgement as eligible new requests. Existing records
  are never updated. Hashing occurs before the attempted insert on either path.
- Per-IP limits are 5 requests/minute and 30/day, using REMOTE_ADDR rather than
  trusting arbitrary X-Forwarded-For. Errors do not echo technical exceptions or
  submitted values; unexpected-error logging records only the exception class.

## Files changed by this implementation

Existing files edited:

| Path | Change |
| --- | --- |
| `backend/apps/accounts/views.py` | Replace scaffold with public JSON/CSRF/registration views, parser and throttles |
| `backend/config/urls.py` | Include versioned accounts routes |
| `frontend/package.json` | Add dependency-free Node test command |
| `frontend/src/App.tsx` | Dispatch public homepage, registration, and not-found pages |
| `frontend/src/features/auth/RegisterPage.tsx` | Fill existing registration placeholder |
| `frontend/src/layouts/PublicLayout.tsx` | Scope paging/snap behavior and homepage anchor arrival |
| `frontend/src/utils/scroll.ts` | Return to homepage sections/login from other public pages |
| `frontend/vite.config.ts` | Add same-origin `/api` proxy, preserving Host/Origin |

New files:

| Path | Purpose |
| --- | --- |
| `backend/apps/accounts/serializers.py` | Public input contract and password validation |
| `backend/apps/accounts/services.py` | Atomic account/profile creation and duplicate handling |
| `backend/apps/accounts/urls.py` | CSRF and registration URL definitions |
| `backend/apps/accounts/test_registration.py` | 30 registration HTTP/security/transaction tests |
| `backend/config/test_settings.py` | Fresh disposable local MySQL configuration |
| `backend/config/test_runner.py` | Refuse development targets, reuse, clones, and create-error database replacement |
| `backend/scripts/registration_demo.py` | Temporary isolated backend and persisted-state evidence |
| `frontend/src/api/client.ts` | Cookie/CSRF-aware HTTP behavior and safe errors |
| `frontend/src/features/auth/registration.ts` | Registration types, client validation and allowlisted request |
| `frontend/tests/registration.test.mjs` | Nine client/validation tests |
| `frontend/scripts/registration_demo.mjs` | Real HTTP demonstration using the production frontend client |
| `docs/phase2-registration.md` | This report and runnable handoff |

Existing modifications to settings.py and theme.css, old scaffold deletions,
untracked backend foundation, and DBML files were preserved. No package was
installed and no dependency lockfile change was needed.

## API contract

`GET /api/v1/auth/csrf/` sets the Django CSRF cookie and returns:

```json
{"csrfToken": "<masked CSRF token>"}
```

`POST /api/v1/auth/register/` requires `Content-Type: application/json`, the CSRF
cookie, and `X-CSRFToken` obtained from bootstrap. Browser Origin must match the
served origin (or an explicitly trusted deployment origin).

```json
{
  "school_id": "2026-001",
  "email": "student@example.edu",
  "first_name": "Maria",
  "middle_name": "Cruz",
  "last_name": "Santos",
  "suffix": "",
  "requested_role": "Student",
  "password": "<your password>",
  "password_confirmation": "<same password>"
}
```

`school_id`, `first_name`, `last_name`, `requested_role`, `password`, and
`password_confirmation` are required. Email, middle name, and suffix may be
omitted or blank. Passwords are 8–128 characters, subject to configured Django
validators. Only canonical `Student` and `Instructor` role names are accepted;
numeric IDs and privilege/review fields are rejected.

New requests and valid duplicates return HTTP 202 with no account identifier,
account-state disclosure, password/hash, authentication token, or session login:

```json
{"message":"Registration request received. Eligible new accounts are pending administrative review."}
```

Validation errors return HTTP 400:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Check the submitted registration details.",
    "fields": {"password_confirmation": ["Passwords do not match."]}
  }
}
```

Other codes are `csrf_failed` (403), `method_not_allowed` (405),
`not_acceptable` (406), `unsupported_media_type` (415), `throttled` (429 with
Retry-After), and `registration_unavailable` (503). Responses use no-store.
Malformed/oversized JSON receives the safe 400 envelope without parser internals.

## Verification

Run backend checks from `backend`:

```powershell
.\.venv\Scripts\python.exe -B manage.py check
.\.venv\Scripts\python.exe -B manage.py test apps.accounts.test_registration apps.accounts.tests apps.access_control.tests --settings=config.test_settings --noinput --verbosity 1
```

Verified: Django checks pass and **91 tests pass** (30 registration tests plus
61 existing regression tests). MySQL runs are disposable; a random
`test_ctug_registration_<16 hex>` database is created, populated using existing
migrations, verified with SELECT DATABASE(), and removed afterward. The runner
does not point the default connection at ctug_workspace, and it refuses to
replace any pre-existing database after a creation error. Do not use --keepdb or
parallel clones with this runner.

Run frontend checks from `frontend`:

```powershell
npm.cmd test
node .\node_modules\typescript\bin\tsc -p tsconfig.app.json --noEmit --incremental false
node .\node_modules\typescript\bin\tsc -p tsconfig.node.json --noEmit --incremental false
npm.cmd run lint
npm.cmd run build
```

Verified: nine client tests pass; application/config TypeScript checks and the
production build pass. ESLint still has the pre-existing
`ThemeToggle.tsx:17` no-useless-assignment error. The previous vite.config.ts
blank-line-at-EOF finding is also retained. Neither unrelated finding was
silently cleaned up.

Client tests cover cookie/CSRF request semantics, bootstrap refusal, field errors,
public-field allowlisting, network failures without POST retry, safe non-JSON
errors, required inputs, and optional email. They use mocked transport and do not
constitute visual browser testing.

## Safe demonstration

Use three terminals. These commands intentionally use a disposable database:

```powershell
# Terminal 1, from backend. Automatically cleans up after 5 minutes or Ctrl+C.
.\.venv\Scripts\python.exe -B -u scripts\registration_demo.py --seconds 300

# Terminal 2, from frontend.
$env:CTUG_API_TARGET = 'http://127.0.0.1:8765'
npm.cmd run dev -- --host 127.0.0.1 --port 5174 --strictPort

# Terminal 3, from frontend. Submits Student and Instructor through the real client.
node scripts\registration_demo.mjs
```

The HTTP demonstration refuses to POST unless the backend advertises the guarded
disposable database. It uses the same registration client as the React page,
through the real Vite proxy and real Django/MySQL stack. The backend prints only
aggregate persistence evidence: account/profile counts, Pending/inactive flags,
hashed-password flags, and zero role assignments.

The real HTTP demonstration passed for both Student and Instructor through the
actual frontend client and Vite proxy. The isolated MySQL evidence was:

```json
{
  "database": "test_ctug_registration_30c5a18690679edd",
  "accounts": 2,
  "profiles": 2,
  "all_pending": true,
  "all_inactive": true,
  "all_passwords_hashed": true,
  "role_assignments": 0
}
```

Both POSTs returned HTTP 202. The first demo attempt against port 8000 refused
to submit because the response lacked the disposable-server identification
header. The successful demo used dedicated ports 8765/5174 and an exclusive
backend listener, preserving any existing development server.

For manual UI verification while that disposable backend runs, visit
`http://127.0.0.1:5174/register`, submit synthetic Student/Instructor details, and
verify the administrative-review success message. Also check `/`, its registration
links, homepage section links from registration, and the unchanged unavailable
login behavior. No test data needs to be inserted into ctug_workspace.

Automated browser access was unavailable in this environment. Form rendering,
interaction, mobile layout, and visual appearance still need manual browser
verification; no screenshot or browser-submission success is claimed.

For normal development against the real development database, start
`python manage.py runserver 127.0.0.1:8000` with the usual environment, but do not
use real-development registration as an automated test fallback. Production
hosting must route `/api` to Django under the same origin; Vite's proxy is for
development only. The normal proxy target is port 8000; CTUG_API_TARGET switches
only the demo terminal to the dedicated disposable backend on port 8765.

## Integrity and remaining dependencies

No development database DDL/DML or new migration generation/application was
performed. Existing migrations are used only to provision disposable test
databases. No account roles, privileged accounts, new permission grants, or
Technical Super Admin record were created in the development database.

Final read-only verification confirmed ctug_workspace still has 16 tables,
22 applied migrations, no pending migrations/conflicts/model changes, zero
accounts and profiles, four unchanged active roles, and zero grants/audit rows.
No test_ctug_registration_* database remained after cleanup. Both ERD hashes
match the preflight values. Existing model/custom-field/migration files and the
pre-existing settings/theme changes also match their available Codex snapshot.

Before multiworker deployment, configure a shared throttle cache and upstream
rate limits. Django's default local-memory throttle cache is per process and
its counters are approximate under concurrency. A trusted reverse proxy must
establish REMOTE_ADDR correctly; client forwarding headers remain ignored.
Production HTTPS, secure cookies, and deployment settings remain deployment
prerequisites; this feature does not weaken them.

The next implementation phase should be the centralized permission evaluator,
trusted assignment services, transactional secret-free audit writing, and their
tests. Approval/bootstrap/login remain dependent on those reviewed security
services, last-administrator policy, bootstrap audit semantics, and session
revocation policy. Stop implementation at registration in this run.
