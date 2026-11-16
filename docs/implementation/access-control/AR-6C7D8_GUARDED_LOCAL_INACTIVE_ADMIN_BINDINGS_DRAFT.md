# AR-6C7D.8 — Guarded local-development P2 inactive Admin bindings (draft)

**Project:** CTU-G Workspace
**Target:** local MySQL `ctug_workspace` only, using `config.settings` and `DEBUG=True`
**Owner scope decision:** three Registration Review permission defaults for the existing Admin role
**Operational state:** implementation prepared for local tests; no Phase 2 write executed by installation

## Starting point

AR-6C7D.7 Phase 1 has been reported and verified on local MySQL: two inactive services (`accounts`, `access_control`), three exact permission definitions, five associated append-only audit receipts attributed to an approved application Admin, zero role grants, and zero account overrides. Both Registration Review backend activation settings are false; the routes are not mounted. The official `docs/database/full_schema.dbml` is not part of this change.

This document and code do **not** establish an independent institutional security sign-off. The project owner has authorized the three intended permission defaults and continuing local development. **Do not execute Phase 2 writes until a restorable private backup of the current `ctug_workspace` state is verified.**

## Exact Phase 2 operation

The new command `init_registration_review_inactive_bindings_local_dev` creates exactly three rows in the existing `role_permissions` table, each with:

- Existing **Admin** `role_id`.
- One existing permission: `accounts.registration_requests.read`, `.approve`, or `.reject`.
- `is_active=False` and `granted_by` referencing the existing persisted, approved application Admin audit actor (previously verified as account ID `3` in the user's local database; the command rechecks identity and authority at runtime).

In the same durable database transaction, it appends three audit receipts using action `workspace.review.role_binding.stage`, reason `permission_change`, and exact bounded snapshots containing the role, permission, new role-binding ID, and inactive flag. These are **stored but ineffective** role bindings. `permissions` has no separate `is_active` column; the services and role grants enforce inactivity.

No account is approved, no roles are assigned to accounts, and no services, permission definitions, account overrides, grant-activation states, Django URLs, frontend feature gates, or configuration flags are changed. The command does not touch unrelated AR-6C5D work or migrations.

## Execution safeguards

- The operator must supply explicit `--apply`, numeric audit actor ID, and the exact phase-specific confirmation string. The command has no implicit write path.
- Reuses the Phase 1 local-host, selected-database, MySQL `READ COMMITTED`, isolated-test-runner, route-detachment, and two-disabled-backend-flags checks. It refuses other database configurations.
- Validates the frozen catalogue and exact two-service/three-permission metadata, and verifies **all five** original P1 audit receipts and their actor before inserting anything.
- The audit actor must still be an approved, active application Admin, not a Django staff user or superuser, and must match the P1 receipts.
- Uses the existing P1 named MySQL advisory mutex, matching P1 lock order, and a durable atomic transaction.
- Requires zero account permission overrides and either **zero** staged bindings/receipts or **exactly three** matching inactive bindings and receipts. Partial, foreign, active, unattributed, unaudited, or modified rows are refused without automatic repair.
- On an exception before commit, the transaction rolls back every new role binding and receipt. A completed exact rerun only verifies state and reports `ALREADY_COMPLETE`.
- Retains P1 audit history. Does not grant effective permissions or activate review endpoints.

## Install and isolated test commands

Copy only the two new Python files and this document into the matching paths. From `backend/` after activating the existing `.venv`:

```powershell
python -B manage.py test apps.access_control.test_registration_review_inactive_bindings_local_dev --settings=config.test_settings --noinput

python -B manage.py test apps.access_control.test_audit apps.access_control.test_mutations apps.access_control.test_registration_review_metadata apps.access_control.test_registration_review_inactive_grants apps.access_control.test_registration_review_protected_candidate apps.access_control.test_registration_review_metadata_local_dev apps.access_control.test_registration_review_inactive_bindings_local_dev --settings=config.test_settings --noinput
```

Never use `--keepdb`, `--parallel`, or `config.settings` for these tests. **Expected discovery** based on prior tests: 19 new P2 tests and 168 combined tests. These are expectations, not claimed local results.

After tests, obtain a **verified restorable database backup**, confirm the Phase 1 audit actor identity, review the exact installed source and preflight state, and ensure no concurrent operator is writing metadata. The local-development confirmation required by the command is:

`ctug_workspace:AR-6C7D8:P2:INACTIVE-BINDINGS-ONLY`

The write command should be issued **only after** those checks are completed and intentional Phase 2 execution has been authorized. This document does not provide an automatic execution step. In a disposable test database, the different confirmation `AR-6C7D8:DISPOSABLE-TEST:P2` is used by test cases only.

## Post-execution acceptance (when separately performed)

Verify, read-only, that the two services remain inactive, three permission definitions are unchanged, there are exactly three inactive Admin bindings with the intended actor, and `access_audit_logs` contains exactly five P1 receipts plus three P2 receipts with the intended attribution and snapshots. `account_permissions` remains empty; both review backend flags remain false; the review URL is unmounted; the Admin's effective permissions remain empty. Re-run the relevant MySQL tests only in the disposable test database.

An exception before transaction commit should roll back P2 inserts and P2 audit receipts. Git rollback is **not** a database rollback. For an unexpected committed state, investigate and use a separately authorized, audited corrective operation; never silently delete append-only audit history.

**Out of scope:** Phase 3 service/grant activation, Phase 4 Admin Registration Review API/UI release, ordinary runtime governance access management, Technical Super Admin bootstrap, and production release approval.
