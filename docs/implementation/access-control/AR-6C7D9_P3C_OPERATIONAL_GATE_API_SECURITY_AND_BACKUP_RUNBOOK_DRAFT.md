# AR-6C7D.9 — P3C Operational Scope Gate, API Security Tests, and Recovery Runbook

**Project:** CTU-G Workspace
**Status:** Prepared candidate; not operational activation approval
**Target:** Local MySQL `ctug_workspace` for read-only inspection; disposable MySQL for HTTP tests
**Last verified user checkpoint:** Branch `ronald`, P3B commit `aad4fa6`; 219 combined security tests passed

## 1. Scope and restrictions

P1 created two **inactive** services and three permission definitions, and P2 inserted exactly three **inactive** Admin role bindings. P3A read-only inspection and P3B disposable-MySQL-only activation/compensation exercises passed in the user's environment. The verified impact scope at the time of P3A was exactly one eligible application Admin, audit actor account ID `3`.

This P3C package **does not** activate any services or grants, mount any Django review route, enable any flags, run migrations, modify the official ERD, authorize real registration decisions, or change existing account records. It provides an additional **read-only exact-ID scope gate** and separate disposable-database **authenticated API regression tests**.

A verified backup **and a successful restore test have not been reported**. This blocks *all operational activation writes* even if the P3C checks pass. Don't infer backup validation from an SQL file existing or from passing tests.

## 2. Files

1. `backend/apps/access_control/management/commands/report_registration_review_operational_gate_p3c.py` — read-only Admin impact-scope inspection; no `--apply` or write option.
2. `backend/apps/access_control/test_registration_review_operational_gate_p3c.py` — 12 disposable-MySQL tests for exact scope, unexpected Admin assignments, untouched receipts and disabled gates.
3. `backend/apps/accounts/test_registration_review_p3c_authenticated_boundary.py` — 18 disposable-MySQL HTTP tests using an isolated candidate URLconf, with simulated active permissions *inside the test database only*.
4. This design/recovery runbook.

The new suite contains **30** tests by source count. Add to the previously reported 219 for **249** expected combined tests if no other counts changed. These are **expected** values, not results from the user's environment.

## 3. Required isolated tests

Activate `.venv` and run from `backend/`:

```powershell
python -B manage.py test apps.access_control.test_registration_review_operational_gate_p3c apps.accounts.test_registration_review_p3c_authenticated_boundary --settings=config.test_settings --noinput
if ($LASTEXITCODE -ne 0) { throw "P3C isolated tests failed. Stop." }
```

The HTTP tests temporarily use `apps.accounts.registration_review_urls` as the test `ROOT_URLCONF` and enable flags only under disposable test settings. They test anonymous, Student, Instructor, requested-Admin-without-assignment, Django superuser, CSRF, Origin, per-account Deny, revoked roles/grants during a session, inactive services and exact per-action permissions. The only successful approvals/rejections occur within the disposable test database and are checked for an audit receipt.

For the combined regression, append BOTH P3C test modules to the earlier nine access-control test modules. To preserve API and routing coverage, also run existing `apps.accounts.test_registration_review_api` and `apps.accounts.test_registration_review_routing` separately or include them in a later complete test pass. **Do not** use `--keepdb` or point these test modules at `config.settings`.

## 4. Read-only operational scope report

Only after the isolated tests pass, from `backend/`:

```powershell
python -B manage.py report_registration_review_operational_gate_p3c --actor-account-id 3 --expected-admin-account-ids 3
if ($LASTEXITCODE -ne 0) { throw "P3C operational gate refused. Stop." }
```

The gate reuses the P3A exact P1/P2 catalogue, record, audit and disabled-feature checks, rejects staff/superusers with Admin assignments, and requires the full eligible Admin ID set to match the **explicit** supplied IDs. If a second Admin exists, do not silently add their ID; review the scope first.

The command uses short-lived `SELECT FOR UPDATE` locks during inspection, which do not change row values but may momentarily block other database operations. It always prints `ACTIVATION: BLOCKED (NO WRITES EXECUTED)` even on success. Its result does not attest a restorable backup, owner authorization, reviewed release plan, or API test success.

## 5. Mandatory manual backup and restore checkpoint

**Before any actual MySQL activation writes:**

1. Select a quiet period and capture current database schema/version, Git commit and the intended Admin ID set in a private release note. No School IDs, passwords or `.env` contents should be added to Git.
2. In MySQL Workbench: **Server → Data Export → `ctug_workspace` → Dump Structure and Data → Export to Self-Contained File**. Save to a private folder **outside** the repository and confirm successful export. Include all tables required for application and audit recovery.
3. **Inspect the dump** for `CREATE DATABASE`, `USE ctug_workspace`, or any other database-switch statement. Never import a dump that could target the active `ctug_workspace` schema during a restore test. Prefer a dump created with the "Include Create Schema" option disabled.
4. Create a **separately named empty schema**, e.g. `ctug_workspace_restore_check`, under local MySQL. In Workbench **Server → Data Import**, select the dump and choose that **separate** schema only. Check the selected schema and dump again before starting import. If the dump contains `USE`/`CREATE DATABASE` statements targeting the development database, stop and regenerate a safely scoped dump.
5. Compare table counts, required nine application tables, relevant Django migrations, service/permission/binding row counts, and eight P1/P2 audit receipts between the original and restored schemas. Verify representative test-safe records and DB constraints. No need to reveal School IDs or passwords in chat. Document import success, validation evidence, backup date, and a recovery owner. Do **not** restore over active `ctug_workspace`.
6. Maintain the secure backup until after any future activation release and verify an actual restore again if the schema or data has changed materially.

**A Git commit is not a MySQL backup.** An audit log is evidence of actions, not a substitute for a restorable database snapshot. For deployment, account for coordinated frontend/backend settings and operational notification outbox behavior separately.

## 6. Requirements before operational activation (not included here)

- A **reviewed and restorable** backup, with a documented failure/rollback operator and mechanism.
- Explicit approval of the exact potentially affected Admin account IDs. Account `3` is the previously validated local Admin; do not assume the scope is unchanged.
- An operational activation command separate from test-only P3B, with local-MySQL pins, atomic writes, trustworthy audit receipts, concurrency control, idempotency policy, exact P1/P2 provenance and zero unintended grants. Also implement/test audited **compensation** when services and grants are active.
- Defined emergency containment and timing. Enabling both services plus Admin bindings creates **effective** permissions even if registration-review URL routes are still unmounted; do not treat an unmounted route as a complete permission control.
- Full authenticated API tests (both positive and negative), concurrent duplicate decision tests, session/CSRF and throttling checks, approval/rejection audit and notification/outbox behavior, and a separate reviewed API/UI routing and rollout decision.
- Preserve all existing controls: no Django `is_superuser` bypass, no requested-role authority, per-account Deny precedence, no grant caching across requests.

**Stop conditions:** unexpected Admin assignee, P1/P2 receipt mismatch, missing or altered permission record, any active grant/Service, enabled feature flag, route already mounted, database target mismatch, unexpected migrations, failed tests, or missing verified backup. Do not repair these conditions by silently modifying the ERD or grants.

## 7. Git hygiene

After tests pass, stage only the four files listed in Section 2. Inspect `git diff --cached --name-status` and `git diff --cached --check`, confirm there are exactly four additions, then commit on branch `ronald`. Do not stage `docs/database/full_schema.dbml`, `.env`, `backend/apps/config/`, or unrelated drafts. A local commit is not evidence of a push to GitHub.
