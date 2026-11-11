# AR-6C7C.5 — Protected Registration Review Initialization Contract (DRAFT)

**Project:** CTU-G Workspace
**Status:** Unapproved design and isolated contract tests; **no production/development DB initializer is implemented by this package**.
**Scope:** Only the Registration Review permissions; no architectural redesign.

## Verified entry evidence

- Local user-run offline subset tests: **10/10 passed**.
- Local user-run isolated initialization preflight tests: **18/18 passed**.
- Local user-run MySQL preflight: exactly 2 missing services and 3 missing permission definitions; 3 Admin role bindings **DEFER**; all gates blocked; no writes.
- Exact v2 source proposal SHA-256: `12746bcb7b5b73041606768b9641ced10cec75fec0c6ea7d1b9dae16f3f6f315`.
- These results **do not** establish metadata/grant/write approval, role governance bootstrap authority, or deployed API behavior.

## Immutable minimum scope

| Kind | Exact entries | Current/next state |
|---|---|---|
| `services` | `accounts`; `access_control` | Missing; **future metadata initially inactive** |
| `permissions` | `accounts.registration_requests.read`; `.approve`; `.reject` | Missing; definitions only, no independent `is_active` field |
| `roles` | Existing `Admin` | Existing active role; never recreate |
| `role_permissions` | `Admin` → each of the three permissions | Deferred, **no current grant**, independent authorization required |
| `account_permissions` | None | No overrides and no direct per-user grants planned |
| `account_roles` | Existing Admin assignment unchanged | Do not alter roles, users, or bootstrap state |
| `access_audit_logs` | Exact bounded append-only events | Required in same transaction as *each* future write |

`accounts.profile.self.read` is independent of this minimum release. The full v2 95-permission / 106-binding proposal remains unapproved. Do not modify v2, the protected ERD, role union/explicit-Deny semantics, or AR-6C5D queue work.

## Four independently authorized stages — all BLOCKED now

1. **Metadata:** Confirm owner, reviewer, exact digest and a reviewed operator procedure; separately approve only 2 *inactive* Service metadata rows and 3 Permission definitions. Do not create a role grant in the metadata stage.
2. **Protected grants:** After metadata verification and independent authorization, separately approve the 3 Admin role defaults. Ordinary `mutations.py` deliberately forbids this governance target. A later implementation must **not** bypass it with an unreviewed direct ORM/SQL script; it needs a separately reviewed trusted operation and an attributable non-self-grant operator.
3. **Service activation:** Separately authorize activation of the two services only after object-level authorization tests, full impact/preview and rollback planning. Since `permissions` has no `is_active` column, inactive service state (and grant state) supplies the fail-closed boundary.
4. **API activation:** Separately review the detached Registration Review URL configuration, feature flags, CSRF/session protections, UI list-field redaction, target eligibility and browser E2E tests. Never enable solely because grants exist.

**This contract does not supply or mint approval evidence.** `authorization` fields are intentionally null and the contract validation intentionally refuses editing them. After actual institutional/security approval, create a **new reviewed revision**; do not change the draft JSON in place to say `APPROVED`.

## Operator and database transaction requirements for a later separately authorized implementation

- Existing first Workspace Admin bootstrap only provisioned an Admin; it does **not** grant permission-catalogue authority. Django `is_superuser` alone is not an application-governance bypass. A legitimate technical operator and independent reviewer must be explicitly recorded, and the system must prohibit self-approval/self-grants.
- The later write-capable entrypoint must be opt-in, single-purpose, disabled by default and unavailable to public routes and untrusted service callers. Its authorization design must be reviewed independently; it is **not included** here.
- All future modifications must be scoped to the exact allowlist. Never use the unrestricted 95-permission seed, assign new roles, install direct account overrides or change other services.
- Verify local primary MySQL, approved isolation level, current schema, exact v2 digest, exact profile digest, current signed approvals, inactive baseline and no unexpected records **inside the same serialized database transaction** used for writes. Choose and document a fixed lock order that serializes overlapping initialization attempts; the existing Admin role row can be a candidate mutex only after concurrency testing.
- Each separate permitted mutation must be atomic with a real persisted, attributable actor and **`record_access_audit` inside the same transaction**. Audit errors must roll back all affected changes, even if the exception is caught.
- Existing `access_audit_logs.old_value/new_value` accept only bounded authorization-state keys (IDs, booleans, approved enums), **not** arbitrary text such as ticket IDs, catalogue digests or usernames. Audit actions must fit the existing 50-character bounded code contract and `reason` must use an approved code. The independent approval-timeline/digest evidence therefore needs a separately reviewed durable record mechanism or approved reference procedure before a live write; do not smuggle it into free-text audit snapshots.
- Keep review evidence outside logged secrets; never echo operator credentials, reset tokens or raw personal data.
- On failure during a transaction, roll back; after a committed change, use a separately reviewed audited compensating procedure, not a silent delete/reset or assumption that restoring a ZIP rolls back the database.

## Isolated acceptance-test matrix for the future write-capable implementation (NOT yet executed)

| ID | Test | Expected outcome |
|---|---|---|
| W01 | No independent approval evidence | Deny all writes |
| W02 | Wrong source/profile hash | Deny all writes |
| W03 | Invalid/inactive actor or self-grant | Deny all writes |
| W04 | Existing active or unexpected service/permission | Deny and report drift |
| W05 | Create only 2 inactive services and 3 permission definitions | Exactly allowed metadata, with audit |
| W06 | Attempt extra permission or service | Deny and roll back |
| W07 | Attempt Admin grant through ordinary mutations | Existing governance denial preserved |
| W08 | Audited 3 protected grants, separately approved | Only 3 grants; correct actor; no other role affected |
| W09 | Audit writer raises mid-transaction | All related rows roll back |
| W10 | Duplicate/concurrent run | One consistent outcome; no duplicate grants or audit success claims |
| W11 | Inactive service/role/account | Protected operations fail closed |
| W12 | Account-level direct Deny | Deny wins over Admin role grant |
| W13 | Multi-role account | Valid role union remains; no active-role switching introduced |
| W14 | Django Superuser without Workspace grants | No Workspace authorization bypass |
| W15 | Student/Instructor/pending account attempts review | Denied |
| W16 | Admin reviews own request or wrong target | Denied |
| W17 | CSRF/session manipulation or forged URL | Backend denies appropriately |
| W18 | Role/grant revocation with existing session | No stale protected access |
| W19 | API gate disabled | Endpoints remain detached/inaccessible |
| W20 | Developer DB execution without separately signed authorization | Denied even when dry-run is clean |

**No W01–W20 mutation or E2E tests have been executed.** They are acceptance requirements for a later reviewed implementation tested first on disposable MySQL.

## Included artifacts and local commands

- `backend/apps/access_control/catalogue/registration_review_execution_contract_v0_1_draft.json`: frozen **unapproved** execution contract with all gates blocked.
- `backend/scripts/validate_registration_review_execution_contract.py`: offline static validator, uses only local known JSON; no Django, MySQL or writes.
- `backend/scripts/test_registration_review_execution_contract.py`: isolated negative tamper tests; does not test a live initializer.

From the project `backend` directory, after installing only these **new** files:

```powershell
python -B -m unittest scripts.test_registration_review_execution_contract -v
python -B scripts/validate_registration_review_execution_contract.py
```

## Decision log: still open; no silent architecture changes

- **Owner + independent security reviewer:** names, sign-off evidence, exact reviewed revision, real authorization to each separately scoped phase.
- **First protected-grant operator:** separately approved attribution and governance bootstrap method; the existing Admin assignment is not enough.
- **Durable approval trace:** location and integrity requirements that work with existing restrictive audit snapshots and unchanged ERD.
- **Transaction locks / rollback:** exact SQL and concurrency strategy to approve after isolated MySQL tests.
- **API and object policy:** redaction/retention, rejection behavior, school scope, session revocation and web E2E outcomes.

**AR-6C7C.5 completion condition:** contract draft and offline validation pass; security/technical approvals recorded separately; no execution authorized by this package. The next development code milestone (a separately approved trusted protected initializer plus isolated MySQL tests) is **not** provided here.
