# AR-6C7D.6 — Operational Initializer Design Review (No Executable Change)

**Project:** CTU-G Workspace
**Status:** REVIEW DRAFT / APPROVAL BLOCKED / NO DATABASE WRITES
**Prepared:** 2026-11-12
**Verified Git baseline:** `ronald` at `8f2abba`
**Required companion:** `AR-6C7D6_PROTECTED_CHANGE_AUTHORIZATION_RECORD_DRAFT.md`
**Frozen source:** `AR-6C7C5-REGISTRATION-REVIEW-DRAFT`, SHA-256 `12746bcb7b5b73041606768b9641ced10cec75fec0c6ea7d1b9dae16f3f6f315`

> This is a **design review**, not an executable runbook. The previously tested `tests_support/` candidate is designed only for disposable databases. No write-capable operational initializer or approved bootstrap authority exists at this milestone. All four execution phases remain **BLOCKED**.

## 1. Exact intended database state

| Table | Stage P1 / P2 expected delta | Hard invariant |
|---|---|---|
| `services` | P1: `accounts`, `access_control` created **inactive** | Exactly those two service codes; metadata must exactly match pinned proposal |
| `permissions` | P1: three definitions — `.read`, `.approve`, `.reject` for `accounts.registration_requests` | Definitions reference `accounts` service; `Permission` does **not** have `is_active` |
| `roles` | No new rows; use existing active `Admin` | No reserved-role bootstrap or duplicate Admin role |
| `role_permissions` | P2: three `Admin` bindings, **is_active=False**, persisted `granted_by` actor | No active grants; exact unique `(role, permission)` pairs |
| `account_roles` | None | Existing Admin assignment unchanged |
| `account_permissions` | None | No direct Grants, Denies, or overrides added or edited |
| `access_audit_logs` | Future validated, bounded audit events for every independently approved write | Append-only; valid persisted actor; each event in same transaction as its mutation |

The prior preflight on `ctug_workspace` reported `CREATE` for 2 services + 3 permissions and `DEFER` for 3 bindings. This is a **snapshot**, not a standing promise of database state. Stop on any later mismatch; never auto-repair unexpected data.

## 2. Operational authority — unresolved before implementation

The expected operator must be explicitly authorized for the specified stage by an independently authenticated reviewer. **Do not** assume that an existing application `Admin` assignment, a future Technical Super Admin concept, or Django `is_superuser` suffices. Neither `delegation.py` nor `mutations.py` should be bypassed with an ad hoc direct ORM/SQL script; those services deliberately block protected governance writes through normal delegation.

A separate trusted operational entrypoint, access policy and evidence-verification mechanism require independent design approval. **No command name or execution flag is defined here**, and no change to the existing blocked JSON contract is permitted. If approval is obtained, publish a newly reviewed revision rather than editing the frozen draft to impersonate authorization.

## 3. Proposed technical implementation controls — to be approved and tested

1. **Secure entrypoint:** Local, opt-in, phase-specific and unavailable from public Django routes or background jobs; fail closed before any query/mutation if proof of approval or operator identity is absent. Never accept `--force`, an unverified boolean, or a caller-supplied display name as proof of authorization.
2. **State/provenance verification:** Pin the exact catalogue revision/digest; verify schema and allowlisted values, current session/actor eligibility, unique constraints, expected empty-or-complete state, and DB-target identity against the authorized change record. No full-v2 seed and no direct account overrides.
3. **Transaction and concurrency:** Use primary MySQL at the approved isolation level (the review service expects `READ COMMITTED`); serialize overlapping operations under a reviewed and consistently ordered lock strategy. An existing `Admin` role-row mutex is a *candidate*, not yet an approved strategy. Lock ordering, concurrent first-run race handling, and idempotence must be proven in disposable MySQL before any operational deployment.
4. **Audit attribution:** Reuse the existing `record_access_audit` or receipt sibling **inside the same database transaction**, with a persisted authorized actor. Validate event names (existing max length 50), controlled `reason="permission_change"`, and allowed state snapshot fields/size (2,048 bytes). The `old_value`/`new_value` JSON restricts keys to bounded IDs, boolean state, role/permission ID arrays and approved enums; **do not store** free-text tickets, usernames or catalogue hashes in that JSON. Approval provenance must be retained in a separately reviewed, access-controlled change record linked to the transaction evidence. Operational event names and linkage are **NOT YET APPROVED**.
5. **Failure semantics:** Any write or audit error must abort that transaction; no success statement before commit. A repeated operation must validate the entire previously committed state *and* attribution, not merely skip inserts if rows exist. Do not silently auto-heal partial, foreign or unaudited state.
6. **Separation by phase:** Never combine the four independently authorized release phases into one automatic activation. The metadata stage makes no grants. The protected-binding stage makes **inactive** grants only. Even after service activation, inactive bindings remain inactive; any binding activation needs its own explicit authorization and acceptance criteria.
7. **Postcondition:** Verify exact record identities and counts, audit correspondence, actor attribution, zero unapproved overrides, unchanged account-role assignments, and no effective Admin grant while either services or bindings remain inactive.

### Approval questions still requiring decisions

- What authenticated system and role defines the change owner and the *independent* security reviewer?
- Who is the non-self-grant execution operator, how are their identity and authority verified, and how is the first-governance bootstrap performed without inventing a Technical Super Admin?
- Where does the durable approval/ticket/digest evidence reside, given the existing audit JSON restrictions?
- Which exact operational audit action codes and lock strategy will be adopted after concurrent-run tests?
- What verified backup/restore and post-commit compensation process applies to `ctug_workspace`?

Until these answers are approved and evidenced, the operational implementation should **not** be released or used.

## 4. Four-stage change plan and acceptance gates

| Phase | Work to consider *after separate approval* | Before any commit or activation | Current decision |
|---|---|---|---|
| **P1 Metadata** | 2 inactive service rows; 3 exact permission definitions; independently attributed audits | Reviewed P1 authorization, pinned source + live diff, approved initializer, verified backup, transaction/rollback tests | **BLOCKED** |
| **P2 Protected defaults** | 3 `Admin` → permission bindings inserted explicitly inactive; independently attributed audits | Reviewed P2 authorization, no self-grant, unchanged existing roles/overrides, audit + concurrency acceptance | **BLOCKED** |
| **P3 Activation** | Independently consider service and binding activation after controlled impact review | Separate signed activation approval, direct-Deny and revocation checks, inactive/active state impact test and rollback strategy | **BLOCKED** |
| **P4 API/UI release** | Approve a chosen URL prefix for the existing isolated registration-review URLconf; individually review backend and frontend gates | Separate release authorization and authenticated web E2E with genuine positive and denial paths | **BLOCKED** |

**Django/API findings already verified:** `registration_review_urls.py` currently has pending-list, approve and reject views, but it is **not mounted** in `config.urls`. `WORKSPACE_REGISTRATION_REVIEW_API_ENABLED` and `WORKSPACE_REGISTRATION_APPROVAL_ENABLED` were `False` at the last runtime check. The React mock preview and typed client are independently hard-disabled. Do not change those conditions in P1 or P2.

## 5. Recovery and stop-policy review

| Failure point | Approved general behavior | Unresolved prior to live change |
|---|---|---|
| Preflight mismatch or missing signoff | Stop **before** writes; retain read-only findings | Evidence repository, independent decision path |
| Any mutation or audit error **before commit** | Database atomic rollback of that phase; no success report | Operational rollback/concurrency test results |
| Unexpected committed metadata/bindings | Keep audit history; assess affected access; use separately authorized audited compensation, **not** blanket DELETE or Git rollback | Recovery owner, approved compensating procedure |
| P3/P4 misconfiguration after activation | Contain/revoke via approved change procedure; reverify all backend gates and effective permissions | Restore/release protocol and incident owner |
| Test-only candidate invoked on real DB | Refuse and report security process violation | Independent code review and prevention controls |

A Git commit or ZIP backup does **not** roll back MySQL. Do not remove append-only audit logs to conceal changes. Protect any collected evidence from disclosing raw credentials or students' personal details.

## 6. Future isolated acceptance tests (design criteria, not claims)

Before an operational initializer can be approved, implement and pass disposable MySQL tests for: missing/forged/expired approval; invalid operator; same-person authorization/execution; changed source hash; conflicting existing objects; transaction rollback on every possible audit failure; parallel first-run operations; exact idempotent second run; stale/partially completed phases; zero effective rights when inactive; direct Deny precedence; multi-role union; and refusal to run under unsafe settings. **Existing 137 passing tests only exercise the current isolated candidate and security foundation.**

Release must additionally pass authenticated browser/API tests for session and CSRF validation, unauthorized Student/Instructor access, 401/403/404/429/503 responses, stale/duplicate requests, race-safe approval/rejection, audit/outbox behavior where enabled, and explicit negative paths. None are proven simply by successful compilation or offline contract tests.

## 7. Safe commands for collecting *read-only* evidence

From `backend/` in the existing local development environment:

```powershell
python -B -m unittest scripts.test_registration_review_execution_readiness -v
python -B -m scripts.report_registration_review_execution_readiness --format text
python -B manage.py plan_registration_review_initialization --format text
```

These scripts **do not approve or execute** the change. Do not pass invented `--execute`, `--apply` or approval switches; do not enable routes, role bindings or service flags to turn a readiness warning green. Do not copy the disposable `tests_support/` fixture into an operational management command.

## 8. Design review disposition

- **Scope consistency:** Identified — 2 service definitions, 3 permissions, 3 initially inactive Admin defaults.
- **Functional readiness:** Offline typed frontend contract and isolated database candidate tested.
- **Operational authorization:** **NOT ESTABLISHED** — evidence E01–E07 from companion record still open.
- **Approved write-capable implementation:** **NOT AVAILABLE**.
- **Current outcome:** **BLOCKED — DOCUMENTATION ONLY**. No changes to `ctug_workspace`, official ERD, protected execution contract, Django routes, role permissions, or release flags.
