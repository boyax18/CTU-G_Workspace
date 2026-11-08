# CTU-G Workspace — Protected ERD Fingerprint Reconciliation

**Date:** November 8, 2026

**Status:** OWNER DECISION RESOLVED — OPTION A APPROVED; LOCAL RUNTIME REVALIDATION PENDING

**Related decision:** `docs/decisions/ADR-003-django-framework-account-flags.md`

## Original problem and cause

The protected ERD contracts previously failed a strict SHA-256 comparison in `backend/scripts/verify_catalogue_plan.py`. The uploaded ZIP's current DBML files each contained two additional boolean account columns:

```dbml
  is_staff boolean [not null, default: false]
  is_superuser boolean [not null, default: false]
```

Removing only those two lines in memory (preserving the original CRLF bytes and blank-line layout) reproduced both previous pinned fingerprints **exactly**. Thus the cause is a known two-column revision, not unexplained corruption or mere line-ending normalization. Both fields are also reflected in the current Django Account model and the existing `accounts.0002` migration.

## Owner decision and fingerprints

On November 8, 2026, the CTU-G Workspace project owner selected **Option A: retain both Django framework fields in the official ERD**.

| File | Old pin (historical) | Approved pin |
| --- | --- | --- |
| `docs/database/full_schema.dbml` | `e9235a87555ffcd50ecb6ab6c1a45f9c7c54e344ff8f269ecc890579f633e4b2` | `e4362be913280ab6c23d5c66af249fc1923fccb1acd7b6c2696f7ee95c19d4a0` |
| `docs/database/schema.dbml` | `f050f7b910038532ca8e73b283f16a57dedd6b738fdc74d293e64d539a4afac4` | `3bc2060ae35fce16725d6ca5b90272e819039b8dce855ffe305b654140f77313` |

The two protected DBML files already include these fields and are **not rewritten** by the Option A patch. The read-only integrity verifier's expected hashes are updated, while its fail-closed behavior is preserved.

## Verification boundary

- Verified offline against the uploaded ZIP: current raw hashes, the precise two-field difference from original pins, and Python syntax of the updated verifier.
- **Not claimed:** Current user's local files still match these hashes, a fresh Django/MySQL test run, migrations applied in local MySQL, permission-catalogue activation, or live API authorization.
- `is_staff` and `is_superuser` support framework identities, not an automatic bypass of custom Workspace access control. The implementation's `has_perm()` delegates to the effective-permission evaluator.

## Remaining AR-6C3 blockers

Object scope approval, API contract approval, controlled catalogue initialization and role grants, session/audit/recovery policy, controlled routing/feature-flag activation, Admin UI and end-to-end testing remain outstanding. ERD contract approval **does not** release those gates.
