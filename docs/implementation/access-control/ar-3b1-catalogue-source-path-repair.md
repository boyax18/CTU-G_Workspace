# AR-3B1 — Catalogue Source-Path Compatibility Repair

Date: 7 November 2026, Asia/Manila. Status: completed and verified.

This maintenance task corrects the canonical source location for historical C1 v1.
It does not approve catalogue v2, role grants, initialization, activation or any
administrator provisioning. The existing read-only planner remains planning-only.

## Repair and exact changed files

The restored original was located and hashed **before any repair**. Its exact
bytes match the already pinned source-content SHA-256:

`02EB308DB5AFF1491EA2D024F5F7F1074125E3A7B9BB02DBD1409F6A6170A99E`

Old source reference:

`docs/phase1h-c1-permission-catalogue-governance-proposal.md`

Corrected source reference:

`docs/implementation/access-control/phase1h-c1-permission-catalogue-governance-proposal.md`

| Changed file | Exact purpose |
| --- | --- |
| `backend/apps/access_control/catalogue/c1_v1.json` | Replace only `source.path` with the corrected canonical path. |
| `backend/apps/access_control/catalogue/validation.py` | Replace only `SOURCE` with that same path so strict manifest/source matching remains intact. |
| `backend/apps/access_control/test_catalogue.py` | Add three focused source-path regression tests and necessary imports. |
| `docs/implementation/access-control/ar-3b1-catalogue-source-path-repair.md` | New verification and handoff report. |

This uses a direct canonical-path correction in the two existing matching
references. No fallback resolver, recursive search or reconstructed replacement
document is introduced. Stale or arbitrary paths are rejected before source I/O;
missing or altered canonical source still fails closed. The source digest check,
source-table reconciliation and all planner/mutation contracts are unchanged.

The manifest file's bytes necessarily change because its path metadata changes.
Its **pinned source-content hash** remains unchanged. Byte-level verification
reversed the single path replacement in memory and recovered the exact original
manifest file SHA-256:

`a28d4066ff511b91d6d2cd066575e606520a3189660819eccfcef93b947ab55a`

The same inverse replacement recovered the validator's original file hash. A
semantic digest of the complete parsed manifest excluding only `source.path`
also matched before and after:

`c878a23192fae74ff3b3b64612f7ced52e66899c5f5d7522ada1e03fb69260e6`

Thus the source hash, 10 services, 82 permission definitions, 96 proposed bindings,
five role definitions, readiness, delegation candidates and open/blocked policy
metadata were preserved. The 14 AR-3A candidate additions were not applied.

## Tests and checks executed

From the repository's `backend` directory:

```powershell
& '.\.venv\Scripts\python.exe' -B manage.py check
& '.\.venv\Scripts\python.exe' -B manage.py test apps.access_control.test_catalogue --settings=config.test_settings --noinput --verbosity 1
& '.\.venv\Scripts\python.exe' -B scripts/verify_catalogue_plan.py
```

- Django system checks: **passed, no issues**.
- Focused catalogue suite: **61 passed, 0 failed, 0 skipped**, in 5.142 seconds.
  This includes all 58 existing catalogue tests and three new regressions.
- The new tests verify the exact relocated path and unchanged digest against
  actual original bytes; verify that validation reads only that canonical file;
  and reject stale/arbitrary manifest paths before reading a document.
- Existing missing-source, changed-content, immutable-baseline, read-only SQL,
  MySQL conflict/collation, preservation and repeated-planner tests passed.
- The existing guarded runner created a fresh disposable MySQL database, applied
  existing migrations only there, and destroyed that schema after the suite.
  Test fixtures and independent read-only-write-rejection tests never targeted
  the development database. No disposable schemas remained afterward.
- No full backend or frontend regression suite was needed for the two path-string
  changes. The historical 286-test result is not represented as a new run.

## Actual read-only planner results

The existing verifier ran the real management command twice against the intended
loopback `ctug_workspace` database, MySQL 8.4.13. Both reports were identical:

| Classification | Actual result |
| --- | ---: |
| CREATE | 92 |
| MATCH | 4 |
| CONFLICT | 0 |
| DEFER | 97 |

These match the historical planning baseline: 10 missing services + 82 missing
permissions; four matching roles; the proposed Technical Super Admin role and
96 proposed bindings deferred. No unexpected catalogue records or account-override
groups were found. These are proposed operations, not applied changes or grant
approval. Existing roles remain Student, Instructor, Treasurer and Admin.

Both planner runs together captured 210 statements: SELECTs, explicit
session/transaction controls and rollback. The comparison runs in a MySQL
READ ONLY consistent snapshot with the existing SELECT-only guard. **No development
DML, DDL, audit insert, activation, role assignment or timestamp update occurred.**

Demonstration commands, from `backend`:

```powershell
& '.\.venv\Scripts\python.exe' -B manage.py plan_permission_catalogue
& '.\.venv\Scripts\python.exe' -B manage.py plan_permission_catalogue --format json
```

The report now identifies the actual canonical C1 source path. Neither command
has an apply/seed mode.

## Development database and file preservation

A read-only preflight snapshot was captured before source edits and focused tests.
The verifier then captured snapshots around both development planner runs. All
three snapshots agree on all 16 tables' row counts/content digests, schema metadata
and all 22 migration-history records. The original C1 document remains untouched.

| Records | Before repair/tests | After verification |
| --- | ---: | ---: |
| accounts / users | 1 / 1 | 1 / 1 |
| roles | 4 | 4 |
| services / permissions | 0 / 0 | 0 / 0 |
| account_roles / role_permissions / account_permissions | 0 / 0 / 0 | 0 / 0 / 0 |
| access_audit_logs | 0 | 0 |
| django_migrations | 22 | 22 |
| auth_permission / django_content_type | 56 / 14 | 56 / 14 |
| auth_group / auth_group_permissions / django_admin_log / django_session | 0 each | 0 each |

One account/profile already existed at this task's initial snapshot, unlike the
older empty-account report. They were preserved; no identity details were printed.
This pre-existing difference does not change catalogue classifications.

Identical before/after fingerprints, using the existing verifier's algorithm:

| Evidence | SHA-256 |
| --- | --- |
| All-table row-content digests | `c5e8b2b45a56b43c4a06454ee41c00d2f5a259f006921bc6d0823728274a5314` |
| Schema metadata | `3b350d46b536e563a19d7000a35e1ba0ae8b7a5bf17f8f377d533576c39619de` |
| Migration history | `911161da48b379bcfa5ee8707049e556e08cda8c7254f1d024f8e216fcdb20e5` |
| Full ERD | `E9235A87555FFCD50ECB6AB6C1A45F9C7C54E344FF8F269ECC890579F633E4B2` |
| Auth ERD | `F050F7B910038532CA8E73B283F16A57DEDD6B738FDC74D293E64D539A4AFAC4` |

All pre-existing paths outside the three listed source/test files, including
existing tracked/untracked work and deletions, were preserved. The planner,
verification script, models, migration files, ERDs, registration, settings,
frontend, B1/B2 services and all existing documentation are unchanged. No reset,
clean, discard, commit or push was performed.

## Remaining catalogue-v2 prerequisites and stop boundary

The source-location defect identified by AR-2/AR-3A is repaired. C1 v1 remains
historical planning data, not an approved revised grant catalogue. Before v2:

1. Record owner decisions on role composition/name, ordinary/protected assignment,
   finer recipient scopes, self/assigned-role changes, independent review and the
   effective-last-operator invariant.
2. Review and freeze actual v2 definitions, exact default pairs, blocked codes,
   one SSG Advisor responsibility and monitoring/privacy scopes. Derive/validate
   final totals from the accepted data; the 14 candidates are not approval.
3. Design separate version-aware validation/planning with SRS/decision provenance,
   preserving v1 and existing-record/zero-write guarantees.
4. Resolve durable approval/audit evidence, first real human attribution,
   first-init serialization and recovery. Review Django framework flags and
   session/event storage/schema choices independently.
5. Authorize any initialization, grants, activation or privileged provisioning
   separately after the relevant trusted services and disposable-MySQL security
   tests are complete. No such action is part of this repair.

AR-3B1 stops after this verified path correction and report.
