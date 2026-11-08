> **RECOVERED / RECONSTRUCTED DOCUMENT — NOT THE ORIGINAL FILE**  
> Reconstructed on 2026-11-07 from previous CTU-G Workspace development reports, known milestones, and the original C1 proposal. Statements about tests and environment are **historical reports supplied by Codex**, not newly run or independently verified. Exact original wording, every test assertion, source line, and implementation nuance may differ. Treat current backend code and test results as authoritative when discrepancies occur.  
> **Status:** Historical implementation handoff; **not an authorization** to initialize or change roles, privileges, services, or database records. Current SRS v0.3 revises the administrator use cases; earlier access-governance assumptions need reconciliation.  

# Phase 1H-B2 — Trusted Permission Management Services

## 1. Purpose and historical scope

Phase 1H-B2 added internal audited mutation services for ordinary role-permission grants/revocations and individual account Grant/Deny overrides. Live permission mutations were intentionally kept **disabled** until explicit catalogue and delegation governance approval.

Reported result: **53 new tests; 228 total backend tests passed**, zero failed or skipped. The historical report said four new files were created and existing source/schema was untouched.

## 2. Components and APIs

Reported files:

- `backend/apps/access_control/delegation.py` — explicit delegation-scope and reserved-policy validation.
- `backend/apps/access_control/mutations.py` — transactional service functions.
- `backend/apps/access_control/test_mutations.py` — mutation tests.
- `docs/phase1h-b2-trusted-permission-management.md` — prior report, now reconstructed here.

The original C1 proposal names the following internal operations:

| Operation | Intent |
| --- | --- |
| `grant_role_permission` | Create/enable an approved role permission |
| `revoke_role_permission` | Disable a role grant, without creating a direct Deny |
| `grant_account_permission` | Create/update a direct account-specific `Grant` |
| `deny_account_permission` | Create/update a direct account-specific `Deny` |
| `deactivate_account_override` | Disable a current account override; removing a `Deny` may **increase** effective access |

Exact signatures, exception types, action codes, and parameter names are to be checked in `mutations.py`; they are not reproduced without original source inspection.

## 3. Authorization model

Historical B2 checks require the acting account to be persisted, approved, active and holding at least one active role. They also require separate:

- Management authority: `access_control.role_permissions.manage` or `access_control.account_permissions.manage`, as applicable.
- Service-specific delegation authority: e.g., `access_control.delegate.finance`, supplied through an explicitly approved scope policy.
- Exact allowed permission codes and eligible recipient roles for that service.

The project owner had not authorized the actual delegation registry; **no live scope should be inferred from a proposed code or role name**. An account merely possessing a business permission is not necessarily authorized to grant it to others.

## 4. Protective rules reported

- Ordinary functions do not edit the actor's own account overrides.
- The actor cannot edit permissions of a role already assigned to that actor.
- Reserved Admin and Technical Super Admin role mutations use a separately governed path.
- Governance/auth/security permissions (including `accounts` and `access_control` namespaces) are hard-protected from these ordinary operations.
- Target account and role must satisfy strict active/approved eligibility.
- For account overrides, **all** the target account's active roles must fit the approved recipient scope. This conservative rule may block Student + Treasurer until a finer policy is implemented.
- Explicit direct `Deny` takes precedence after successful mutation; removing that Deny is a privilege-increasing operation needing the same stringent check.
- A role grant removal may leave effective access from another active role or direct Grant; revocation should not be misrepresented as guaranteed denial.

The previous C1 policy used a per-service `ApprovedDelegationScope` and `ACCESS_CONTROL_DELEGATION_POLICY`, with no unrestricted role/permission wildcard.

## 5. Transactions, audit, concurrency

The historical report described a durable atomic mutation boundary, locks/current-state checks, an `access_control` Service mutex, same-transaction `record_access_audit`, and no audit entry for an authorized no-op. Failed audit insertion aborts the permission change. Do not call the ordinary mutation services from an incompatible outer transaction without reviewing the actual durable-atomic implementation.

Historical test coverage included authorization failures, self-escalation, inactivity, reserved governance, override precedence, idempotency, concurrency, and mutation/audit rollback.

## 6. Historical verification summary

| Check | Reported result |
| --- | --- |
| New B2 tests | 53 |
| Backend tests total | 228 passing |
| Local MySQL | 16 tables, 22 migrations, four roles |
| Development accounts / catalogue / grants / audit | 0 at that point |
| Schema/migration/ERD changes | None |
| Existing source files edited | None (as originally reported) |

The test counts and database state are historical and not independently reverified during recovery.

## 7. Known limitations and changed requirements

The original C1 proposal documents major gaps: restricted roles and their defaults cannot be managed through B2, service-wide cross-product recipient scopes cannot safely model all multi-role combinations, business object-level authorization is separate, and protected operator bootstrap needs a new reviewed path.

**Critical later SRS change (v0.3):** The project owner now requires two `Admin` permission profiles—Normal Admin (school) and Super Admin (school + technical governance)—plus multiple assigned roles (e.g., Student + Treasurer, Instructor + Admin, Instructor + SSG Advisor/Finance Monitor). These are **new requirements**, not evidence the original B2 implementation already permits the combinations. Reconcile reserved-role restrictions and recipient scopes before enabling B2.

## 8. Handoff

Do not implement unbounded grant APIs, secretly broaden recipient lists, initialize privileged grants, or run write commands based on this recovered report. Verify exact implementation in the current code and review SRS v0.3 and the approved future governance policy first.

