# AR-6C7D.7 — Local development P1 metadata initializer (owner-authorized)

**Project:** CTU-G Workspace
**Document class:** local-development implementation draft; not a production release
**Target:** local MySQL `ctug_workspace` (not a remote instance)
**Scope authorization:** project system architect/full-stack developer explicitly approved the three Registration Review permissions and local development continuation in conversation on 2026-11-12. This is an owner declaration, **not an independently authenticated or signed institutional review**.

## Important boundary

This implementation establishes a **new, narrowly scoped, local-development-only operational entrypoint**. It does **not** amend or claim approval of the existing frozen `AR-6C7C5-REGISTRATION-REVIEW-DRAFT` contract. That contract remains blocked, and production/release authorization is still separate. The current user's approval does not constitute a technical proof that the CLI operator is who they claim to be. The CLI verifies an existing approved/active Workspace Admin for audit attribution, not a cryptographically validated owner signature.

P1 writes only these records (if *all* are absent):

- `services`: `accounts`, `access_control` with `is_active=False`.
- `permissions`: `accounts.registration_requests.read`, `.approve`, `.reject` with full, pinned catalogue metadata. The `permissions` table has **no** `is_active` field.
- `access_audit_logs`: five bounded operational receipts, one per created metadata record, with persisted Admin actor and `permission_change` reason, inserted atomically with the records.

P1 **never** writes `role_permissions`, `account_permissions`, `account_roles`, or `roles`, and never changes accounts, backend flags, route registrations, frontend gates or the official ERD. Future P2 protected bindings, P3 activation and P4 review API release require distinct decisions.

## Runtime guards

The management command `init_registration_review_metadata_local_dev` refuses operations unless all of these are true:

- Explicit `--apply`, a persisted actor account PK, and an exact target/phase confirmation string are provided (these are operator confirmations, **not signatures**).
- A single configured `default` MySQL database, host `localhost`/`127.0.0.1`/`::1`, and `READ COMMITTED` transaction isolation are verified against `SELECT DATABASE()`.
- Either local `config.settings`, `DEBUG=True` and database `ctug_workspace`, or the existing random disposable `config.test_settings` isolated MySQL runner is in use. The command refuses all other databases, testing flags, unknown aliases and remotely hosted DBs.
- The exact source catalogue matches the existing pinned SHA-256 and the existing frozen draft remains blocked.
- Both backend review flags remain false and the pending-review URL is unmounted.
- Exactly one active Admin role exists, the audit actor has a persisted active approved Workspace Admin assignment and is **not** a Django framework admin.
- No role grants or account overrides exist and no unexpected services/permissions exist.
- Either the **entire** expected metadata and five matching attributable audit receipts already exist, or **none** exist. Incomplete or conflicting states fail closed; no automatic repair or silent audit rewrite.
- A MySQL advisory lock serializes runs of this initializer; a single durable atomic transaction covers all five metadata inserts and five audit receipts. A duplicate exact execution is read-only.

These checks reduce local-development risk but do not replace backup/restore verification, external code review or institutional change management for deployment.

## Safe testing (before any development database write)

From `backend/` in the existing virtual environment:

```powershell
python -B manage.py test apps.access_control.test_registration_review_metadata_local_dev --settings=config.test_settings --noinput
python -B manage.py test apps.access_control.test_audit apps.access_control.test_mutations apps.access_control.test_registration_review_metadata apps.access_control.test_registration_review_inactive_grants apps.access_control.test_registration_review_protected_candidate apps.access_control.test_registration_review_metadata_local_dev --settings=config.test_settings --noinput
python -B manage.py plan_registration_review_initialization --format text
```

Never add `--keepdb` or `--parallel` and never run the test suite under `config.settings`.

## Local execution policy (separate manual action)

Even with owner approval, do **not** run the write command automatically on installation. First: (1) pass all isolated tests; (2) verify a restorable backup of `ctug_workspace` using the team's approved local method; (3) check there is no concurrent developer or background initializer; (4) rerun the read-only preflight and inspect any differences; (5) select the correct **numeric primary key** of the approved, active application Admin to attribute five audit receipts.

The new command is not a generic permission grant/activation command. Never execute a `tests_support/` initializer against `ctug_workspace`, and never use the new initializer outside local development. The separate confirmation required by the command is:

`ctug_workspace:AR-6C7D7:P1:METADATA-ONLY`

The operator must intentionally enter the command with `--apply`, `--actor-account-id`, and `--confirm-local-dev-phase1` after reviewing the outputs above. No account school IDs, email addresses, passwords, or secrets belong in this authorization record.

## Postcondition and recovery

After a committed P1 execution: both services remain inactive; permission definitions exist without usable grants; role and account permissions remain unchanged; backend flags remain false and routes detached. Expect five attributable audit events. A failed atomic operation rolls back all five inserts and all audit writes. A committed write cannot be undone by Git: investigate unexpected states and use an expressly authorized, audited compensating change rather than deleting append-only audit history.

**Next milestone:** P2 protected Admin bindings require a fresh review and separately authorized operation. This P1 procedure does not grant effective permissions to any Admin.
