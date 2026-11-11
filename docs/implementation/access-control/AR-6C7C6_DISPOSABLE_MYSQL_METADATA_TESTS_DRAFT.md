# AR-6C7C.6 — Disposable MySQL Metadata Transaction Tests

**Project:** CTU-G Workspace
**Status:** TEST-ONLY IMPLEMENTATION DRAFT — NO LIVE INITIALIZATION OR APPROVAL

## Purpose

Exercise the existing Django `Service`, `Permission` and `AccessAuditLog` models in a disposable MySQL database. This is a test fixture, **not** an application initializer, migration, management command, bootstrap, permission grant workflow, or a path to live activation.

## Exact scope

- Two services: `accounts`, `access_control`, both created with `is_active=False`.
- Three permission definitions: `accounts.registration_requests.read`, `.approve`, `.reject`, using the exact pinned v2 metadata.
- Five bounded audit events when all five definitions are initially missing; events are attributable to a *synthetic test audit actor* and inserted inside the same atomic transaction.
- No `RolePermission`, `AccountPermission`, `AccountRole`, framework flags, or active service changes.
- `permissions` has **no** `is_active` column. The inactive service state and absence of grants preserve deny-by-default behavior.

## Guard rails

The helper requires `config.test_settings`, `config.test_runner.IsolatedMySQLRunner`, a random disposable MySQL database named `test_ctug_registration_<16 lowercase hex>`, matching configured `NAME` / `TEST.NAME`, and verification of the **actual connected database** using `SELECT DATABASE()`.

It also validates the original unapproved contract, blocked gates, exact SHA-256-pinned v2 catalogue, existing Admin role, absence of other catalogue data and all grants/overrides. No management command or API calls the helper.

The helper explicitly refuses execution on the normal `ctug_workspace` database. It may not be generalized for production. Its synthetic test actor is **not approval evidence** and does not solve protected real-world governance attribution.

## Install (only if no file already exists)

Add the three Python files from the package to their named paths. Add this Markdown document to `docs/implementation/access-control/`. Do not edit existing files, ERD, settings, migrations or feature flags.

## Test command — database-writing, disposable test DB only

From `backend/`, with the current project's existing virtual environment activated:

```powershell
python -B manage.py test apps.access_control.test_registration_review_metadata --settings=config.test_settings --noinput
```

Do **not** use `--keepdb`, `--parallel`, or normal `config.settings`. The existing isolated runner creates a new database and destroys it after testing.

The source package was syntax-checked offline. Actual Django/MySQL test results must come from the local Windows environment and are **not claimed** until the command succeeds there.

## Acceptance criteria

1. Exact two inactive services and three permissions are created only in disposable MySQL.
2. Exactly five bounded append-only audit events accompany first creation.
3. Repeated identical execution creates no duplicates and no new audits.
4. Simulated mid-transaction audit failure rolls back metadata and audit rows.
5. Active/conflicting/extraneous metadata, grants/overrides, tampered contract, missing Admin, unsaved actor, or non-test database configuration are rejected.
6. No protected grants, service activation or API changes occur; no existing role assignment is modified.
7. Existing 95 audit/mutation regression tests should continue to pass independently.

## Deferred and explicitly not authorized

- No protected Admin role grants.
- No real metadata initialization in the development database.
- No institution/operator approval inferred from the tests.
- No registration-review API or worker activation.
- No changes to `full_schema.dbml`, the v2 catalogue or AR-6C5D bulk queue.
- Concurrency and live approved execution require separate governance review and additional isolated testing.

**Workflow remains unchanged:** Registration → Pending → Admin Review → Approval/Rejection → Authorized Login → Shared Dashboard. Multiple assigned roles, role-union permissions, and direct Deny precedence remain unchanged.
