# WF-03.01 D-115 — Protected executor compatibility and refusal boundary

**Baseline:** locally confirmed `ronald` at `e370bad` (20 November 2026). **Scope:** source-stage reconciliation and fail-closed defense only. The author of this patch is NOT the D-101 independent reviewer. **No tests executed, migration applied, role granted, feature enabled, executor deployed, or approval recorded.**

## 1. Source findings and operation comparison

| Operation | Isolated review application | Existing executor dispatch | D-115 decision |
| --- | --- | --- | --- |
| School Admin assign/revoke (D-87) | `assign_school_admin` / `revoke_school_admin` with Technical Super Admin authority and audit/session revocation | No matching executor command; `role.assign` is a distinct legacy **Student/Instructor base-role assignment** subject to School Admin and policy conditions | Keep both unavailable under protected writer |
| Treasurer / SSG Advisor assign/revoke (D-100) | Separate permission `access_control.role_assignments.ordinary.manage`, appointment and role eligibility checks | No matching ordinary responsibility or revocation command | Keep both unavailable under protected writer |
| Appointment submit/verify/reject/revoke (D-110/D-112) | Independent recording/review permission, two-person verification, receipt linkage | No appointment commands; registry migration not applied to development database | Keep registry unavailable under protected writer |
| Session active-role context (D-113) | Per-request, session-held selection with role-scoped permission evaluator | Executor authenticates an actor via certificate-bound proof, **not** the selected role; protocol does not carry an authenticated role context | Keep role switching unavailable under protected writer |
| Permission overrides (WF-03.03/03.04) | Active context suppresses AccountPermission Grants pending binding policy; Deny applies | Executor supports `account_permission.*` without active-role binding | Preserve deny-first restriction; resolve cross-process semantics during WF-03.03, not by granting broader authority |

The protected executor uses mTLS actor proofs and a fixed operation allowlist (`executor/protocol.py` and `executor/engine.py`), with database writer fencing. It must not be altered via an application route or by simply inserting a new operation string. Existing database write commands, audit receipts and P3B recovery invariants remain out of scope.

## 2. Bounded source hardening staged in D-115

- `RoleAssignmentAPI.initial` now refuses **all** isolated role/appointment endpoints before processing, even read-only listing, when `executor.client.enabled()` is true. Its derived `OrdinaryRoleAssignmentAPI` and `AppointmentRegistryAPI` inherit the same early guard; the standard error mapping returns HTTP 503.
- `RoleContextSwitchView.post` independently returns 503 when the protected executor is required, even if middleware is accidentally omitted or reordered. D-113 middleware's existing broader 503 behavior remains unchanged.
- Existing direct service-level `refuse_while_protected_writer_enabled()` checks are unchanged. The database still owns the true writer fence; these Python refusals only prevent unsupported application entry points.
- When the verified writer is off, all D-87/D-100/D-110/D-113 gates remain independently **default OFF**. No production URL route or executor protocol was changed. No new permission code, role assignment, migration or authorization was added.

## 3. Proposed independent executor parity project (NOT authorized by D-115)

Before any guarded feature can be activated under a protected executor, the owner must separately approve a design that covers **all** of the following: operation schema, actor authentication and active-role identity binding, exact authorization at the executor, approval/appointment evidence lifecycle, clock and expiry semantics, actor-recorder-reviewer separation, target-role locking order and conflict detection, idempotence, session invalidation, transaction-bound audit receipts, retry and unknown-outcome reconciliation, recovery/P4 invariants, and database least privilege. Do not interpret the legacy executor `role.assign` as permission to grant Treasurer or SSG Advisor. Do not treat a browser-selected role or arbitrary payload as a verified actor proof.

## 4. Outstanding governance and release blockers

- D-101: actual independent v2.1 then v2.2 catalogue review and reproductions; both sign-offs missing.
- D-102: owner-approved design, implementation and S0-to-S1 privilege extension **not authorized**. No direct inserts or operator workaround.
- Campus official appointment reviewer/source designation missing; no reviewed provisioning of appointment permissions.
- Migration `access_control.0004_ordinary_appointments` remains unapplied pending a separately authorized plan, backup and disposable database validation.
- WF-03.03 must settle account-specific Grant/Deny treatment in selected role contexts; currently account Grants are excluded in D-113 role scope.
- `ronald` diverged from `origin/ronald` (owner last reported ahead 8/behind 4 at `e370bad`). Do not auto-pull, force-push, or amend the user-owned history.
- All application tests, compiler/build checks, and migration rehearsal deferred by the temporary WF-03 execution sequence; final WF-03.01 Human Approval remains unchecked.

## 5. Deferred acceptance checks

1. The new `test_wf0301_d115_executor_boundary.py` must run in the consolidated WF-03 test environment and confirm all isolated API families, session switching, and direct services fail closed when the verified writer is required.
2. Re-run the pre-existing protected-executor protocol, actual-schema MySQL, audit/receipt, P3B/P4 recovery and session tests on approved disposable infrastructure.
3. Independently verify **no** protected writer bypass through direct service imports, local-review URLconf, alternate request middleware order, task worker or direct executor call.
4. Test active-role context, AccountPermission grants and Denies, shared permission codes, expiry/revocation, concurrent modifications and split-brain/multi-tab session changes.
5. Confirm D-101/102, appointment policy and migration preconditions are approved before any live rollout. Keep final Human Approval pending until integrated verification is complete.
