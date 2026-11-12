# CTU-G Workspace — Task 1: Email Notifications and Verified Reapplication

**Status:** Implemented and verified in automated local tests with feature gates disabled. **NOT deployed or production-approved.** Git commit status is recorded in repository history.

**Approved by project owner:** D1–D5, 12 November 2026. **Development discipline:** Inspect → Reconcile → Approve → Implement → Test → Document → Commit → Continue.

## Scope and exact outcomes

The project owner requested (1) sender branding `CTU-G Workspace`, (2) approved and rejected email messages, including the fixed, Admin-selected rejection reason and appropriate public CTA, (3) Student/Instructor reapplication using the existing `/register` page with a **blank full form**, and (4) compatibility with bulk approval/rejection notifications. This implementation does **not** activate bulk routes, Technical Super Admin capabilities, SMTP, normal registration-review routes or production features.

### D1 — Snapshot the decision at the time it happens

A bounded `rejection_code` in `access_audit_logs.new_value` is allowed for `account.registration.reject`. New **v2** notification-outbox entries read the reason from the immutable decision audit receipt; the email worker does **not** read `Account.rejection_reason`, which may later be cleared on reapplication. Previous **v1** queue rows render as before. The v2 writer is gated by `WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED=1`, default **off**; v2 never puts free-form notes or email into audit JSON. No table or migration changes.

### D2 — Sender, templates and links

`DEFAULT_FROM_EMAIL` is a formatted `CTU-G Workspace <verified-address>` sender, derived from the configured `WORKSPACE_EMAIL_FROM` address. V2 outbox and opt-in legacy after-commit messages use a plain-text body and an HTML alternative, with subject `CTU-G Workspace | Registration Approved/Rejected`, exact status, a fixed rejection-reason label where applicable, and a single login or reapply CTA. Approval uses the existing home route `/` because its hero includes login; rejection goes to the existing `/register` page. No School ID or password is embedded.

Links come from `WORKSPACE_PUBLIC_BASE_URL` and may be included in SMTP emails **only** when the public base URL is HTTPS and its hostname is explicitly allowed by `WORKSPACE_EMAIL_PUBLIC_HOSTS`. Locmem tests may use localhost HTTP; never configure SMTP links with localhost. The real Gmail UI may substitute a saved contact label even when the From display name is branded.

### D3 — Verify existing email before full-form reapplication

`POST /api/v1/auth/reapply/link/` accepts only `{school_id, email}`. It sends a verification link **to the previously stored email**, and only if both submitted values match an eligible rejected account. Response is generic `202`; applicant existence is not disclosed by the text. The signed, purpose-specific, one-hour token contains only account ID, exact last rejection audit receipt ID, and a keyed digest of the previous email. Its URL is `/register#reapply=...` (fragment avoids token in the server request URL).

The link opens the **empty** current registration form, requiring all credentials, personal and role fields again. `POST /api/v1/auth/reapply/complete/` expects precisely the full `RegistrationSerializer` payload plus `reapplication_token` and enforces the same CSRF check, JSON bounds, password rules, and per-IP throttles as original registration. Invalid, expired, stale, altered, or replayed tokens are rejected.

A MySQL transaction locks the existing rejected account and checks it is inactive, non-privileged, requesting Student/Instructor, has no `account_roles` or `account_permissions`, and still matches the exact rejection cycle and previous email. The transition updates the same account/profile, hashes the **new** password, clears review/reset metadata, returns it to Pending/inactive, and records `account.registration.reapply` in an append-only audit entry. The public email-token holder is recorded technically as the target account's own audit actor; this is **not an assertion of institutional identity** and **not an Admin action**. The School Admin must independently verify the applicant before approval. There is no guaranteed recovery without the previous email: administrator-assisted identity verification is an explicitly separate, not-yet-implemented path.

**Existing-account data caveat:** `created_at` is retained as the original account creation date. A new registration submission timestamp cannot be shown from this field; use the reapplication audit timestamp when building future review-history UI.

### D4 — Privacy and operational risks still to resolve

The public registration endpoint `/api/v1/auth/register/` retains its existing generic behavior for duplicate School IDs. The new `/reapply/link/` endpoint is also generic and throttled. Its prototype email dispatch is synchronous to avoid a new table, so a sufficiently capable remote observer might distinguish eligible recipients by response timing. **Do not enable real SMTP reapplication dispatch** until an approved asynchronous, non-enumerating delivery mechanism and shared anti-abuse rate limit have been reviewed and implemented. The implementation has an extra `WORKSPACE_REAPPLICATION_SMTP_DELIVERY_APPROVED` guard as defense in depth; it is **not** an authorization to waive this operational blocker.

For the current approved candidate, **local-memory email and isolated MySQL tests only**. The normal Django settings keep feature gates off by default, and `config.review_local_settings` explicitly overrides them to False even when global environment variables are set. No release or DB activation command is included.

### D5 — Feature gates

| Gate | Default or local-review behavior |
|---|---|
| `WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED` | `False`; local real-DB review forces False |
| `WORKSPACE_REGISTRATION_REAPPLICATION_EMAIL_ENABLED` | `False`; local real-DB review forces False |
| `WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED` | `False`; local real-DB review forces False |
| Existing review/approval and bulk routing gates | Not changed |
| Existing email outbox/SMTP worker gates | Not changed |

### Bulk approval and rejection

Existing `registration_bulk.py` processes a maximum of **20 explicit IDs** by calling `approve_registration()` / `reject_registration()` once per account. Since new notification behavior lives in those trusted single-account services, every successful bulk decision receives its own audit snapshot and (when the separately gated outbox writer is enabled) its own outbox entry. Skipped/failed decisions do not receive a success email. There is no all-or-nothing bulk transaction. **Bulk UI/API routes remain separately gated and unmounted in the normal app.**

## Acceptance tests and required local verification

Local code-only checks completed in the patch-authoring container:
- Python byte-compilation for all affected `.py` sources: PASS.
- Node 22 with `--experimental-strip-types`: 14 frontend registration/reapplication tests PASS.
- TypeScript `transpileModule` parser check for the modified frontend files: 0 syntactic diagnostics.

**Patch-authoring container limitations (superseded where noted by Windows results below):** Django/MySQL tests, TypeScript full project build, Vite production build, live email delivery and interactive browser tests were not run in that container. Local Windows regression and build outcomes are recorded below; live email delivery and full browser acceptance remain unverified.

Run from `backend` with the project's activated `.venv`:

```powershell
python -B manage.py test apps.accounts.test_task1_reapplication apps.accounts.test_registration_review_notifications apps.accounts.test_registration_outbox apps.accounts.test_registration_outbox_worker apps.accounts.test_registration_bulk apps.accounts.test_registration apps.accounts.test_registration_rejection_retention apps.access_control.test_audit --settings=config.test_settings --noinput
if ($LASTEXITCODE -ne 0) { throw 'Task 1 Django tests failed. Stop.' }
python -B manage.py makemigrations --check --dry-run --settings=config.settings
if ($LASTEXITCODE -ne 0) { throw 'Unexpected schema/model change. Stop.' }
```

Run from `frontend`:

```powershell
node --test tests/registration.test.mjs tests/reapplication.test.mjs
if ($LASTEXITCODE -ne 0) { throw 'Task 1 frontend tests failed. Stop.' }
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Task 1 frontend build failed. Stop.' }
```

For end-to-end acceptance, use a **separate disposable MySQL test database** with a dedicated test-only `EMAIL_BACKEND=locmem`; do **not** use `ctug_workspace`. Verify token replay, CSRF, email HTML/plain text, exact reason selection, full-form replacement, audit preservation, and bulk per-decision outbox rows. Do not route real email to students.

## Windows verification evidence — 12 November 2026

The project owner ran the patched code in the Windows development workspace and reported these results:

- Focused Django/MySQL tests: **142/142 passed**, disposable Django test database.
- Full Accounts + Access Control regression: **729/729 passed** across 37 test modules, disposable Django test database.
- Frontend registration/reapplication tests: **14/14 passed**.
- Frontend TypeScript + Vite production build: **passed**.
- Django migration consistency: `makemigrations --check --dry-run --settings=config.settings` returned **No changes detected**. This check read development settings but did not generate or apply migrations.
- Reapplication email HTML escape hotfix: replaced Django `escape` import with `from html import escape` to support `quote=True`; included in the passing results.

**Evidence boundary:** These results do not establish live Gmail delivery, production readiness, full real-browser reapplication acceptance or resolution of the synchronous email timing/anti-abuse issue. The normal review, bulk, reapplication and SMTP delivery gates remain separate and must not be enabled by this commit. The official ERD and live database were not modified by Task 1 testing.

## Change control / Git

The patch is based on the **uploaded snapshot** at `df29a52`, not live access to the Windows repository. Verify branch `ronald`, unchanged staged index, and that the existing source is still compatible using `git apply --check` before applying. Do not overwrite another teammate's changes. Review `git diff` and re-run tests before any scoped commit. Never stage `docs/database/full_schema.dbml`, `.env`, `.git`, `node_modules`, unrelated project files or the uploaded project ZIP. This patch does **not** contain an ERD edit or a migration.

**Remaining gate:** Review the exact staged Task 1 changes and create a scoped Git commit. Production and live SMTP/reapplication enablement still require separate approval and operational safeguards.
