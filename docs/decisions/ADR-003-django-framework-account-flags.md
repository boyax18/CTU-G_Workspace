# ADR-003 — Adopt Django framework account flags in the protected ERD

**Decision:** APPROVED (Option A)

**Decision date:** November 8, 2026

**Decision authority:** CTU-G Workspace project owner, explicitly approved in project conversation

**Scope:** `accounts.is_staff`, `accounts.is_superuser`, the two protected DBML fingerprint pins, and documentation only

## Context

CTU-G Workspace has a custom Django `Account` model backed by the `accounts` table and independent Workspace authorization through roles, services and account-specific permission overrides.

The original protected DBML fingerprints predate two framework-operator fields that are already present in the current project snapshot's **both** DBML files, Account model, and migration `accounts.0002_account_is_staff_account_is_superuser`.

A byte-level comparison established that these two fields are the **only additions** required to explain the original-to-current fingerprint differences. No other ERD table, relationship or column changes are approved by this decision.

## Decision

**Adopt Option A:** The approved `accounts` schema includes:

```dbml
  is_staff boolean [not null, default: false]
  is_superuser boolean [not null, default: false]
```

These are **boolean columns**, not entities or application roles. Their default is `false`.

- `is_staff` identifies an account intended to be eligible for Django framework-admin access, subject to the actual admin-site and authentication permission checks.
- `is_superuser` marks the framework superuser identity. **It does not automatically authorize CTU-G Workspace actions.** In this project the custom `Account.has_perm()` delegates to the Workspace effective-permission evaluator, while `has_module_perms()` returns `False`; Django's conventional automatic superuser permission behavior must not be assumed.
- Ordinary School Admin receives authorization through active Workspace `account_roles` and effective permission grants; these flags are not substitutes.
- A future protected Technical Super Admin is a separate governance role and is **not** created or granted by this decision.
- Framework accounts must not bypass per-account Deny precedence, inactive services, API permission checks or audit controls.

## Approved protected DBML versions

The source files already contain the approved columns in the uploaded project snapshot. **No additional DBML byte changes are required for this approval.** The table below pins the exact *raw file bytes* (including existing CRLF line endings), not a normalized representation.

| Protected contract | Previous SHA-256 (historical) | Approved SHA-256 (Option A) |
| --- | --- | --- |
| `docs/database/full_schema.dbml` | `e9235a87555ffcd50ecb6ab6c1a45f9c7c54e344ff8f269ecc890579f633e4b2` | `e4362be913280ab6c23d5c66af249fc1923fccb1acd7b6c2696f7ee95c19d4a0` |
| `docs/database/schema.dbml` | `f050f7b910038532ca8e73b283f16a57dedd6b738fdc74d293e64d539a4afac4` | `3bc2060ae35fce16725d6ca5b90272e819039b8dce855ffe305b654140f77313` |

The two expected SHA-256 strings in `backend/scripts/verify_catalogue_plan.py` are updated to these new approved values. The verifier remains **read-only** and must continue to fail closed if either on-disk DBML differs from its approved raw hash.

## Implementation evidence and limits

- **Already present in uploaded source:** `backend/apps/accounts/models.py` has both boolean fields with `default=False`, `db_default=False`; migration `backend/apps/accounts/migrations/0002_account_is_staff_account_is_superuser.py` adds both columns.
- **Approval does not mean migration re-execution.** Do not create, edit, replay, roll back or fake migrations as part of this reconciliation.
- The approval was checked offline against the user-provided ZIP, using exact byte hashes, a targeted content diff, and Python syntax parsing of the modified verifier.
- Actual local MySQL migration state, Django admin usability, and database-backed verification have **not** been rerun by this documentation patch. Those must be checked independently.

## Explicitly not approved

This ADR does **not** activate any V2 catalogue permissions, grants, services, protected roles, registration-review URL routes or feature flags. It does **not** approve direct Django Superuser authorization for Workspace APIs, nor production deployment. Other AR-6C3 release gates remain blocked.

## Required follow-up verification

1. Confirm both local DBML files have the **approved** SHA-256 values before applying the revised integrity verifier; if not, stop and review drift.
2. Execute the existing tests and targeted Django admin-operator tests in the local isolated test environment when available.
3. Run the existing read-only integrity verifier only against its intended local MySQL target, with credentials kept private; record actual results without exposing data.
4. Update the SRS or architecture reference if it asserts that the custom Account lacks framework flags.
5. Preserve this decision and both historical hashes for traceability; any later ERD change requires its own explicit approval and new pins.
