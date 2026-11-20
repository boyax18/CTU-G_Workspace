# WF-03.01 D-114 — Final integration/security reconciliation (source staged)

**Date:** 20 November 2026. **Baseline:** local branch `ronald` at `cb8b56a` (D-113 installed and committed). Read-only source inspection of D-87, D-100, D-110, D-111, D-112 and D-113; D-114 is a narrow code hardening, not a release approval.

## Confirmed gap and bounded correction

D-100 originally checks Student/Instructor base roles and conflicting role assignments **when issuing** an ordinary role. The D-111 runtime checks independent appointments on permission evaluation, but does not continuously check that the base assignment remains active or that incompatible assignments were added later. D-114 adds this missing condition in `ordinary_role_runtime.verified_ordinary_roles_for`. No database mutation or new privileges are introduced.

- Treasurer requires current active Student role; SSG Advisor requires current active Instructor role.
- Any conflicting persisted Student, Instructor, Treasurer, SSG Advisor, Admin or Technical Super Admin assignment blocks the affected ordinary role, even when the conflicting role is inactive.
- Expired/revoked/missing/unverified appointment, absent assigner, unsupported framework account or database failure continues to deny ordinary-role authority. Ordinary assignment remains a stored record until an authorized actor revokes it.
- A separate, already-granted base-role permission is not removed merely because an ordinary role is ineligible.

## Inspected integration boundaries — not silently activated

| Area | Evidence and disposition |
| --- | --- |
| Active role context (D-113) | Session-held role ID is revalidated. Only actual active RolePermission grants in selected role (plus stored Admin grant on Technical context) apply. Invalid selection denies; direct AccountPermission Grant is excluded pending WF-03.03 role-binding decision. AccountPermission Deny remains global. **Do not enable** until the policy is reconciled. |
| Appointment evidence (D-110/D-111) | Registry migration `access_control.0004_ordinary_appointments` not applied. Official campus verifying authority, independent source documents and reviewer permission provisioning remain unapproved. D-114 does not authorize any of them. |
| S0→S1 governance (D-101/D-102) | Independent v2.1/v2.2 catalogue sign-off and separately authorized S0→S1 technical governance extension remain blocked. Do not synthesize a reviewer approval or grant `access_control.role_assignments.ordinary.manage`. |
| Protected executor | D-113 middleware refuses isolated review API operations whenever protected executor mode is enabled; executor cannot yet enforce selected role context. No change to its protocol, trust, protected commands, or writer privileges. Remains a release blocker. |
| Audit/session boundary | Successful assignment/revocation services use recorded audit receipts and session-revocation counter. D-114 runs **read-only** during permission checks and does not alter protected audit snapshots or counters. |
| Normal production routing | `config.settings` and `config.urls` are unchanged. Local-review/sandbox features remain independently default-off. |
| Remote branch | User-confirmed `ronald` diverged from `origin/ronald` (ahead 6/behind 4 at `cb8b56a`). Reconcile intentionally before push; never automatic pull/force-push as part of this patch. |

## Deferred verification and acceptance

- [ ] Confirm base-role loss and dormant conflicting assignments remove ordinary privileges, including session role selector and permission API, in disposable MySQL.
- [ ] Verify independent evidence is required and revoked/expired records deny on every permission evaluation.
- [ ] Verify shared permission codes, account-specific Grant/Deny, role switch multi-tab concurrency, CSRF, session revocation, and fail-closed handling.
- [ ] Verify protected executor parity in a separately approved boundary project; refuse all live role-context rollout before reconciliation.
- [ ] Resolve campus reviewer authority, official evidence source, catalogue D-101 signoff and D-102 separate authorization.
- [ ] Review/authorize migration with backup and rollback, then test it only in a disposable environment before any real database change.
- [ ] After all WF-03 subflows are implemented, execute retained tests, correct failures, and request final WF-03.01 Human Approval.

**No tests executed**, no migration applied, no gates enabled, no production code routes mounted, no privilege provisioned. D-114 is an implementation-stage source change only.
