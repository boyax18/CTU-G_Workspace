> **RECOVERED / RECONSTRUCTED DOCUMENT — NOT THE ORIGINAL FILE**  
> Reconstructed on 2026-11-07 from previous CTU-G Workspace development reports, known milestones, and the original C1 proposal. Statements about tests and environment are **historical reports supplied by Codex**, not newly run or independently verified. Exact original wording, every test assertion, source line, and implementation nuance may differ. Treat current backend code and test results as authoritative when discrepancies occur.  
> **Status:** Historical implementation handoff; **not an authorization** to initialize or change roles, privileges, services, or database records. Current SRS v0.3 revises the administrator use cases; earlier access-governance assumptions need reconciliation.  

# Phase 1H-A — Hybrid Dynamic Access Control Permission Evaluator

## 1. Purpose and historical scope

Phase 1H-A implemented an application-level, database-backed effective-permission evaluator for CTU-G Workspace. It was designed for the custom Account and custom access-control tables, not for stock Django groups or Django's unrestricted superuser permission path.

**Implementation reported complete** in the prior Codex handoff. At the time: 42 newly added evaluator tests; 133 total backend tests passed. This document reconstructs the technical contract from that report, not the full original 1H-A document.

## 2. Source components and relevant data

- `backend/apps/access_control/services.py` — centralized evaluator logic (reported).
- `backend/apps/accounts/models.py` — `Account.has_perm()` delegates to the evaluator (reported).
- `backend/apps/access_control/test_permissions.py` — evaluator tests (reported).
- Existing custom tables: `accounts`, `roles`, `account_roles`, `services`, `permissions`, `role_permissions`, `account_permissions`.
- Permission identifiers use `permissions.permission_code`, not hardcoded numeric primary keys.

## 3. Effective-permission contract

A permission is permitted only when all eligibility and grant checks succeed:

1. Account is persisted, `request_status=Approved`, and `is_active=True`.
2. The account has at least one assigned, active role through `account_roles` and `roles`.
3. The requested permission code exists and belongs to an active `services` row.
4. An active role-permission binding **or** a permitted active direct account `Grant` contributes the positive grant.
5. An active account-specific `Deny` takes precedence over all positive grants.
6. Invalid/unknown codes, missing records, inactive components, and failed checks deny access.

In logical form:

`eligible_account AND active_service AND (active_role_grant OR active_direct_grant) AND NOT active_direct_deny`

A requested role from registration (`accounts.requested_role_id`) is **not** an assigned role and never supplies authorization. Role names `Admin` and `Technical Super Admin` do not automatically confer all permissions. The original evaluator intentionally does not add a blanket `is_superuser` bypass.

**Important:** The historic evaluator reports denying object-specific `has_perm(code, obj)` calls when `obj` is not `None`; business-record ownership checks must be implemented separately. A global permission alone is insufficient to access a different student's payment, an unrelated instructor's section, or someone else's rating records.

## 4. Runtime behavior and cache assumptions

- Effective permissions are re-read when evaluated; historical report describes one read-only query per evaluation and no cross-request cache.
- Do not rely on client-side menu visibility for authorization.
- Role grants combine across assigned active roles, with direct Deny taking priority.
- Removing one grant source does not necessarily revoke effective access if another independent source still grants the code.
- Service activation is a broad gate: the present schema has no per-permission `is_active` field.

## 5. Historical verification summary

Previously reported results:

| Check | Prior report |
| --- | --- |
| Newly added evaluator tests | 42 |
| Backend tests total following 1H-A | 133 passing |
| Database/schema changes | None |
| Super Admin creation | Not performed |
| Permission catalogue initial population | Not performed |

The user-provided summary described eligible/ineligible accounts, union of role grants, direct Grant/Deny, unknown codes, inactive services, absence of role-name bypass, and no cross-request permission caching. Exact test names and fixtures should be verified in source control rather than inferred here.

## 6. Limits and later dependencies

- This evaluator does **not** assign roles or grant permissions; separate authorized mutation workflows are needed.
- This evaluator does **not** authorize the first privileged administrator to bootstrap itself.
- Business object scopes and conflicts of interest are separate authorization policies.
- Approved Student/Instructor registration must assign the approved default role through a future trusted atomic approval service before ordinary application permissions become effective.
- Later SRS v0.3 changed the intended Admin/Super Admin role composition; this document preserves the original phase contract without declaring new policies approved.
- Integrating Django's built-in Superuser must be specifically designed and tested; do not quietly bypass this evaluator.

## 7. Verification and handoff

To verify the reconstruction against the repository, inspect `services.py`, `Account.has_perm()`, `test_permissions.py`, existing model names/constraints, and the actual test runner. Reconfirm the priority rules, inactive-role/service behavior, object-specific handling, and cache behavior.

**Preservation rule:** no changes to either ERD, existing migrations, database schema, or live permission records are authorized by this document.

