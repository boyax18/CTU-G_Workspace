# AR-6C7D.9 — P3A Read-Only Registration Review Activation Readiness

**Project:** CTU-G Workspace
**Branch:** `ronald` (operator must verify locally)
**Status:** implementation candidate; **no activation authorized or performed by these files**
**Scope:** inspect the existing Phase 1/P2 metadata and security boundaries; *do not change* the ERD, migrations, accounts, roles, frontend, Django routes, flags, services, or bindings.

## 1. Confirmed baseline from local terminal reports (November 12, 2026)

- Local development MySQL `ctug_workspace`; the previously verified Phase 1 created 2 **inactive** services (`accounts`, `access_control`), 3 permissions, and 5 audit receipts.
- Phase 2 created exactly 3 **inactive** `Admin` role-permission bindings and 3 audit receipts, all attributed to the previously verified application Admin account ID `3`.
- No `account_permissions` overrides, no effective grants, registration-review API flags disabled, registration-review routes not mounted.
- Phase 2 isolated suite: 19/19; combined regression: 168/168; Phase 2 implementation commit `a9c5717`.
- A verified **restorable backup has NOT been confirmed**. Do not activate any services, grants or API routes until a private structure+data backup has been restored into a separate database and validated.

This is a last-reported snapshot. The command rechecks live state rather than trusting those figures.

## 2. P3A deliverable

New management command: `report_registration_review_activation_readiness`, which accepts only `--actor-account-id <id>` and **has no** `--apply`, write or activation option.

- Reuses the exact pinned catalogue and target/feature-gate checks from the committed P1/P2 implementations. It accepts only local `config.settings`/`ctug_workspace`, or a rigorously isolated disposable MySQL `config.test_settings` database.
- Within a short-lived database transaction, rechecks P1 metadata and **5** exact audit receipts; P2's **3** inactive Admin bindings and **3** exact audit receipts; correct actor and existing active Admin assignment; no account overrides; no effective permissions; no services/bindings activated; review flags disabled; review URL absent.
- Prints the **number** of eligible application Admin accounts whose effective permissions could be expanded by future activation. It does not reveal account names or school IDs. An Admin role grant affects *all* eligible Admin role assignees, not just account ID `3`.
- Reports **ACTIVATION BLOCKED** even if every database check passes, because a backup/recovery test, scope review and separate release safeguards cannot be established by this command.
- Uses `SELECT FOR UPDATE` only for brief state validation. This transiently locks rows but does not change their values; schedule during a quiet development period if needed.
- On any mismatch or unexpected exception, raises `CommandError` and reports no success. It does not auto-repair partial or changed states.

## 3. Install and test

From the root of `CTU-G Workspace`, extract **only** these new files, preserving paths:

1. `backend/apps/access_control/management/commands/report_registration_review_activation_readiness.py`
2. `backend/apps/access_control/test_registration_review_activation_readiness.py`
3. `docs/implementation/access-control/AR-6C7D9_P3A_READ_ONLY_ACTIVATION_READINESS_DRAFT.md`

In the already-configured virtual environment from `backend/`:

```powershell
python -B manage.py test apps.access_control.test_registration_review_activation_readiness --settings=config.test_settings --noinput
```

**Expected** 14 new tests, based on source; not verified against the user's Windows environment. The test creates/destroys only a disposable test database. Never invoke this test using ordinary `config.settings`, `--keepdb`, or `--parallel`.

After that passes, run the combined regression:

```powershell
python -B manage.py test apps.access_control.test_audit apps.access_control.test_mutations apps.access_control.test_registration_review_metadata apps.access_control.test_registration_review_inactive_grants apps.access_control.test_registration_review_protected_candidate apps.access_control.test_registration_review_metadata_local_dev apps.access_control.test_registration_review_inactive_bindings_local_dev apps.access_control.test_registration_review_activation_readiness --settings=config.test_settings --noinput
```

Expected combined count **182** if the previously measured 168 and all 14 new tests are discovered. Source syntax and ZIP integrity have been checked in the authoring environment; these are **not** claims of passing Django tests.

After test success, inspect the exact Git staged paths and commit only these three files. Never `git add .`; leave `docs/database/full_schema.dbml` and all other unrelated files unchanged.

## 4. Read-only local preflight (AFTER tests pass)

```powershell
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend"
python -B manage.py report_registration_review_activation_readiness --actor-account-id 3
```

Expected if Phase 2 data is still exact:

```
AR-6C7D.9 P3A: DATABASE INSPECTION PASSED (READ ONLY)
Audit actor account ID: 3
Eligible application Admin accounts affected by future grants: <computed count>
Services: 2 inactive; permission definitions: 3
Admin bindings: 3 inactive; account overrides: 0
Operational audit receipts: P1=5; P2=3
Effective permissions for audit actor: 0
Registration Review backend flags: disabled; route: not mounted
ACTIVATION: BLOCKED (NO WRITES EXECUTED)
Manual gates remain: verified database restore, approved impact scope,
separate activation/compensation design, and authenticated API security tests.
```

Count is computed; no particular count is assumed. **No activation command exists in this package.**

## 5. Activation design for separate review (NOT implemented in P3A)

### P3B — Activate services and bindings, with independent safeguards

1. Verify the database backup is restorable and capture a private change record separate from `access_audit_logs` (whose JSON fields are restricted). Confirm operator/audit actor and all eligible Admin assignees affected. This approval is **distinct** from previous authorization to insert inactive bindings.
2. Create separate guarded, single-purpose MySQL activation capability with explicit phase confirmation, local target pins, transactional audit receipts, exact P1/P2 provenance checks, concurrency testing and a tested compensation pathway. **Do not** repurpose P1/P2 commands, which intentionally refuse active services/bindings.
3. Analyze the moment permissions become effective. `Service.is_active=True` plus `RolePermission.is_active=True` makes effective `accounts.registration_requests.*` grants available to **all eligible Admin accounts**, even while the API is unmounted. Never assume URL detachment alone is the authorization boundary.
4. Exercise negative cases on disposable MySQL: direct Deny precedence; Student/Instructor refusal; absent/disabled Admin assignment; Django staff/superuser not automatically an app Admin; self-approval; inactive services; audit failure rollback; concurrent writes; exact idempotency; stale/partial/unaudited data. Keep backend API/approval gates and routes **disabled** during P3B.
5. Following independently approved P3B activation, verify the services/bindings state, exact audit receipts, effective grants, non-Admin denial and a tested, audited compensation plan. Avoid deleting audit history or assuming Git rollback restores MySQL.

### P4 — API/UI rollout (separate authorization)

- Choose and review the route mount prefix and API authorization boundaries. Check Django session+CSRF handling, response types, rate limiting, rejection codes, immutable reviews, notifications/outbox, and duplicate/concurrent decisions.
- Run authenticated end-to-end tests for approved Admin vs unauthenticated, Student, Instructor, inactive/rejected accounts; review `401/403/404/429/503` behavior; then enable flags and frontend gate independently with an immediate containment procedure.
- The isolated review backend APIs, currently unmounted, must **not** become reachable as a side effect of P3A/P3B.

## 6. Recovery and stop conditions

If the reported state differs, **STOP**. Do not alter the production or development database simply to make a readiness check pass. A verified restorable backup is necessary before executing P3B. Keep DB backups private and out of version control. No Phase 3 grants, activation, settings or URLs are approved by this document.
