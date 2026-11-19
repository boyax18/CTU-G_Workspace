# CTU-G Workspace — Development Changelog

### 19 November 2026 — WF-03.01 D-107: S0-first Technical Super Admin provisioning (decision and readiness)

- **Owner decision (local development only):** the first Technical Super Admin grant may create S0, the six existing v2.0 governance codes. The three S1 codes are deferred to the D-102 extension (OD-2, OD-7). D-101 stays OPEN, and OD-7 is not bypassed.
- Amended the D-102 "first grant creates S1" text in readiness sections 1, 3.3, 3.8 and 4, and added section 4.1 (first-grant prerequisites).
- **Read-only checks:** gate and command present; migration 0006 applied; no Technical Super Admin role; School Admin has zero `access_control` permissions; the runtime catalogue is v2.0; the S0 definitions are field-identical to v2.2; **no eligible Approved Instructor exists**.
- **Not done:** no grant, no operator designation, no environment change. Documentation only.

### 19 November 2026 — WF-03.01 D-93/D-95: development-database gate for the protected Superuser command

- `framework_roles` replaces the unconditional `DEVELOPMENT_DATABASE_APPROVED` block with a default-deny development gate. It accepts `ctug_workspace` only when every condition is positively verified, in the configuration and on the live connection.
- The confirmation is database-bound (`ctug_workspace:WF-03.01:<operation>:<id>`).
- The operator allowlist comes only from the process environment, never from a settings module or `backend/.env`; no settings file was changed.
- The low-level mutators refuse outside the protected procedure.
- Tests: new `test_wf0301_d93_development_gate`. The one assertion that referenced the removed flag is updated. backend/apps/access_control/test_wf0301_d93_development_gate.py 11/11; affected regression of every apps.access_control and apps.accounts module (87 modules) 1971/1971, 0 failed, 0 errors, 0 skipped; manage.py check no issues.
- **Not done:** no operator is designated, and nothing was run against `ctug_workspace`. The S0/S1 choice, D-95 evidence, D-99, an approved Instructor, a fresh backup and the first-grant authorization remain open. D-101 is OPEN; D-102 is not implemented; the WF-03.01 Human Approval is not recorded.

### 19 November 2026 — WF-03.01 SR-1 Stage B Gate 2 closure: real-account login verified

- **Test A passed:** the owner ran it privately. Workspace login 200, session authenticated, role Admin (School Admin) with 6 effective permissions (current local provisioning), no Technical Super Admin, logout 200, then unauthenticated.
- **Server-side corroboration:** the server log and read-only database checks agree. No session remains, and accounts, roles, permissions and receipts are unchanged.
- SR-1 Stage B is complete for the local database. **Still open:** Stage B-2 (trigger, restricted accounts, test-runner credential, SR-1a fix, checkpoint anchoring, restore procedure) and the ERD update. D-101 is OPEN; D-102 is not implemented; the WF-03.01 Human Approval is not recorded.

### 19 November 2026 — WF-03.01 SR-1 Stage B Gates 1 and 2: migration 0006 applied to the local database

- **Gate 1:** a consistent backup of `ctug_workspace` was taken outside the repository (SHA-256 `093c5290…cdcfcaf`). It was restore-verified into a scratch schema (18/18 tables equal), and migration 0006 was rehearsed there. The isolated SR-1, D-85 and session suites passed 94/94.
- **Gate 2:** migration 0006 was applied to the local `ctug_workspace` with two writes and a table rebuild. All 6 accounts were preserved at counter 0, and the 24 receipts, roles, permissions and bindings are unchanged. All 5 existing sessions were deleted, and the MySQL 1054 failure is resolved.
- **Smoke tests:** old cookie refused, admin login page, and health/CSRF/session limits all passed. **Pending:** the owner's real-account login/logout test (Test A).
- **Not done:** ERD update, trigger, restricted accounts, test-runner credential, SR-1a fix, and the restore procedure (in-place restore and point-in-time recovery not tested). D-101 is OPEN; D-102 is not implemented; the WF-03.01 Human Approval is not recorded.

### 19 November 2026 — WF-03.01 SR-1 Stage A: session revocation hardened against audit tampering (isolated implementation and tests)

- SR-1 Stage A (19 Nov 2026): the session hash now binds the persistent accounts.session_revocation_version counter (v2 domain, no fallback) instead of the receipt-derived status_epoch; every approved session-ending event advances it once in the same transaction, so deleting, changing or forging receipts no longer revives a session.
- New `apps/accounts/session_revocation.py` (`advance`). It is called once per operation by WF-02.05 suspension and reactivation, School Admin and Technical Super Admin grant and revoke (Technical Super Admin path and Superuser procedure), password-reset completion, and the dormant executor's `technical_admin.bootstrap` (D-83 reconciled).
- Application guards: a stale full `save()` never writes the counter; ORM writes naming it are refused. The login view re-reads the counter after `login()`.
- Migration `accounts/0006_account_session_revocation_version`: authored, and applied only to disposable test databases.
- Tests: new `test_wf0301_sr1_session_revocation`. The SR-1 test is inverted. Four existing assertions that encoded the old hash contract are updated, and one fixture now signs in with the current row. backend/apps/access_control/test_wf0301_sr1_session_revocation.py 34/34; affected regression of every apps.access_control and apps.accounts module (86 modules) 1960/1960, 0 failed, 0 errors, 0 skipped; manage.py check no issues; makemigrations --check no changes (read-only migration-history check); no temporary account, grant, trigger or test database left behind.
- SR-1a confirmed: CSRF polling keeps a revoked session row alive up to the 8-hour limit. It cannot authenticate after Stage A; the middleware is unchanged pending approval.
- **Not done:** Migration 0006 is authored but NOT applied to ctug_workspace (still at 0005; the branch's application therefore fails closed there with MySQL 1054 until a controlled deployment is authorized); the trigger was tested only on disposable databases and is NOT installed; the authoritative ERD is NOT updated; restricted MySQL accounts, external checkpoints and the restore procedure are NOT activated. D-101 OPEN; D-102 not started; WF-03.01 Human Approval not recorded.

### 19 November 2026 — WF-03.01 R-2: Option D phase 1 verification and prototypes (local development only)

- Confirmed: the application connects to `ctug_workspace` as MySQL `root`, so audit receipts are append-only by convention only. **SR-1 confirmed (activation blocker):** deleting an account's latest suspension or role-change receipt moves its session epoch backwards and revives an unused revoked session. The proposed fix (a monotonic revocation epoch) needs separate approval.
- Tested on disposable databases only:
  - a least-privilege runtime account (no UPDATE, DELETE or DDL on `access_audit_logs`; `LOCK TABLES` needed for its locking reads) that runs every governance path;
  - a separate migration account (runs a full `migrate`);
  - a SELECT-only verifier account.
- Added the read-only prototype `report_access_audit_checkpoint` (`apps/access_control/audit_checkpoint.py`): a hash chain over every receipt, verified against a checkpoint held outside the database (optional HMAC). It is not wired into any governance or session path.
- Tests: new `test_wf0301_r2_audit_integrity` 16/16 (two runs); affected regression 1926/1926 in 85 modules, 0 skipped; `manage.py check` and `makemigrations --check` clean.
- **Not done:** no account, grant, trigger, migration, `.env` or connection change on `ctug_workspace`; R-2 OPEN (decisions D-105); D-101 OPEN; D-102 not started; WF-03.01 Human Approval not recorded.

### 19 November 2026 — WF-03.01 D-101: independent reviewer handoff (documentation only)

- Added section 19 to `docs/security/WF-03.01_D-89_CATALOGUE_V2_1_INTEGRITY_REVIEW_PACKAGE.md`: what the reviewer approves (v2.1, then v2.2) and what is out of scope, the evidence status (rechecked versus agent-reported), the exact bytes (SHA-256 and Git blob IDs of the 19 in-scope artefacts), PowerShell-safe and Git commands, the checklist mapping, decision criteria and post-sign-off prohibitions.
- Verified at `b015936`: in-scope files unchanged since `14125f9`, `28d46e1` and `9e259e7`; all pins and both effective digests match; section 12 command 101/101; F-1 regression 4/4; R-1 + K-4/K-6 + D-85 37/37.
- **Not done:** no review or sign-off (D-101 OPEN); no source, test, catalogue or pin change; D-102 blocked.

### 19 November 2026 — WF-03.01 R-1 follow-up: K-4 and K-6 initializer lock order (local development only)

- The P1, P2 and WF-02.05 initializer commands now lock the shared service rows first, inside their existing durable transactions and behind their unchanged advisory lock.
- Covered cycles, each reproduced as a MySQL 1213 deadlock before the correction:
  - K-4a: initializers vs Superuser role changes;
  - K-4b: a P1 rerun vs a role change on the P1 actor;
  - K-6: initializers vs the read-only P3D/P4 compensation previews, created by the R-1 snapshot change.
- On a fresh database the P1 prelude locks nothing. The tests verify that competing protected paths then refuse or wait while holding nothing, that the advisory lock refuses concurrent initializers, and that bootstrap records and receipts are unchanged.
- Tests: new `test_wf0301_k4_initializer_lock_order` 11/11 with the R-1 module 10/10 in three consecutive runs; affected regression 1910/1910 in 84 modules, 0 skipped; `manage.py check` and `makemigrations --check` clean.
- The no-concurrent-initializer operating rule is kept as defence in depth; removing it needs an owner decision.
- **Not done:** R-2 and R-3 remain open. No D-102, D-93/D-95 or D-87 work; nothing provisioned; D-101 OPEN; WF-03.01 Human Approval not recorded.

### 19 November 2026 — WF-03.01 R-1: protected lock-order correction (local development only)

- The protected P3B snapshot (shared by P3D and P4) and the Django-Superuser procedure (`framework_roles.configure_role`) now lock the shared service rows first, before the Admin role, the operator's account or any other overlapping row. Concurrent role changes and compensation now queue instead of deadlocking.
- Covered cycles: K-1 (Admin role), K-2 (actor account), K-3 (Admin assignments) and K-5 (operator account, through a plan-dependent join lock), each reproduced as a MySQL 1213 deadlock before the correction.
- Unchanged: authentication, authorization, the D-85 compensation refusal, the P4 rollback scope, D-102 (OD-1 to OD-7, C-1), Deny handling, atomicity and receipts.
- Tests: new `test_wf0301_r1_lock_order` 10/10 (three consecutive runs); affected regression 1899/1899 in 83 modules, 0 skipped; `manage.py check` and `makemigrations --check` clean.
- **Not done:** K-4 (P1, P2 and WF-02.05 initializers; no concurrent reruns) and R-2 remain open. No D-102, D-93/D-95 or D-87 work; nothing provisioned; D-101 OPEN; WF-03.01 Human Approval not recorded.

### 19 November 2026 — WF-03.01 D-102 C-1: Deny preservation policy approved (documentation only)

- The owner approved C-1: an authorized S0-to-S1 `extend-technical-governance` operation may proceed despite an existing Technical Super Admin holder's account-specific Deny on an extension permission. Every Deny stays unchanged and keeps precedence, and the extension never removes, modifies or overrides it. Affected holders are reported to the authorized operator and recorded in audit evidence, and a Deny-blocked permission is never reported as effective. OD-4 is unchanged: a new grant is still refused when the target has a Deny.
- Recorded the design in `docs/security/WF-03.01_PROTECTED_PROVISIONING_READINESS.md` (sections 3.4, 3.5 and 3.8): the separation of the role extension, account-specific Denies and derived effective permissions; per-holder `framework.governance.deny_preserved` receipts within the existing audit allowlist; and an operator report shown only after commit in the protected TTY session, with no personal data. Planned C-1 tests were added to TC-039.
- Synchronized the decision register (D-102), ADR-004, Access Control Gates, the RTM and the WF-03.01 Workflow Catalogue entries (version 0.3.27). SRS and Use Case amendments are deferred to the implementation.
- **Not done:** no protected code, test, catalogue, pin or database change. D-102 implementation is blocked until the D-101 independent sign-off (v2.1, then v2.2) and a separate authorization. R-1 and R-2 stay open. D-101 OPEN; WF-03.01 Human Approval not recorded.

### 19 November 2026 — WF-03.01 D-102: owner decisions approved, protected scope finalized (documentation only)

- The owner approved D-102 decisions OD-1 to OD-7. Recorded the approved design in `docs/security/WF-03.01_PROTECTED_PROVISIONING_READINESS.md` section 3:
  - only the S0 (6 codes, 1 + 6 + 6 receipts) and S1 (9 codes, 1 + 9 + 9) governance states are accepted, field-exact;
  - a separately confirmed `extend-technical-governance` operation turns S0 into S1;
  - one designated operator per receipt block, which may differ between blocks;
  - a target's own Deny refuses the grant;
  - only `access_control.school_access.inspect`, `access_control.role_assignments.ordinary.manage` and `access_control.audit.school.read` are added;
  - partial base profiles are refused, never repaired.
- Recorded clarification C-1, the open lock-order inversion R-1 (needs a reviewed decision before real-database activation), R-2 and R-3, and planned test TC-039.
- Updated the decision register (D-102), ADR-004, Access Control Gates, the Master Test/UAT Plan (TC-035, TC-039), the RTM and the WF-03.01 Workflow Catalogue entries (version 0.3.26). SRS and Use Case amendments are deferred to the implementation.
- **Not done:** no protected code, test, catalogue, pin or database change. D-102 implementation is blocked until the D-101 independent sign-off (v2.1, then v2.2) and a separate authorization. D-101 OPEN; WF-03.01 Human Approval not recorded.

### 19 November 2026 — WF-03.01: five-area security verification and D-104 (documentation and evidence only)

- Owner direction D-104: Permission Catalogue v2.2 is the current target specification; v2.1 is maintained only as its verified dependency. No runtime consumer was switched (all still read v2.0) and nothing was provisioned.
- Verified role-based authorization, the v2.0 → v2.1 → v2.2 chain (v2.2: 10 services, 95 permissions, 6 roles, 106 bindings, Admin 32, Technical Super Admin 13; only indices 97, 98 and 102 differ from v2.0) and the F-1 correction already committed in `9e259e7`. Effective digests are unchanged.
- Added `docs/security/WF-03.01_PROTECTED_PROVISIONING_READINESS.md`, with the D-102 and D-93/D-95 requirements and the remaining dependencies. Recorded D-100 (ordinary roles, F-4) and D-104 in the decision register.
- Synchronized the WF-03.01 Workflow Catalogue entries (version 0.3.25), SRS v0.4, Use Case v0.4.1 (.md and .docx), TC-016, RTM, ADR-004, Access Control Gates and the D-101 records.
- Tests: 82 access_control and accounts modules, 1889/1889 (0 skipped); frontend role-assignment and navigation 19/19.
- **Not done:** no independent D-101 sign-off (D-101 OPEN); D-102, D-93/D-95, D-87 and provisioning not implemented; WF-03.01 Human Approval not recorded.

### 19 November 2026 — WF-03.01 D-101: documentation corrections D-1 and D-2 (documentation only)

- D-2: recorded the F-1 correction commit `9e259e79000be960569a55a82b8bc1841257dc37` (corrected `validation_v2_1.py` blob `e176f9267b69baae7546d060064254d26a3e7df7a106b6505e941cb5b83d98b3`) and the review scope (v2.1 = `14125f9` + `9e259e7`; v2.2 = `28d46e1`) in the pre-review, review package section 17, workflow catalogue and decision register.
- D-1: the pre-review now records 39 genuine independent tamper probes rejected. The two probes that mocked the second read return the pinned digest by design after the correction; earlier wording overstated the count.
- **Not done:** no source, test, pin or digest change; D-3 (`role_assignment.py` docstring, F-6) is left for the next authorized source revision; D-101 OPEN; sign-offs blank; WF-03.01 Human Approval not recorded.

### 19 November 2026 — WF-03.01 D-101: F-1 validator correction (local development only)

- `validation_v2_1.py` now parses the v2.0 base only from the bytes it has already hashed against the pin and validated with the v2 validator. Before, with default arguments it re-read `v2_0.json` without verification, so a file replaced between the reads could weaken guarantees in a standalone v2.1 result; the v2.2 chain already rejected this. Pins, addenda, deltas and both effective digests are unchanged.
- Tests: 4 new regression tests on the real file-reading path (failing before, passing after); the `test_catalogue_v2_2` baseline records the revised validator digest. Focused catalogue tests 101/101, D-85 16/16, other catalogue suites 73/73.
- Recorded D-101 F-2: Permission Catalogue v2.1 is a historical validated dependency only; operational adoption must use the approved v2.2 chain.
- **Not done:** no independent review or sign-off (D-101 OPEN); nothing provisioned or activated; WF-03.01 Human Approval not recorded.

### 19 November 2026 — WF-03.01 D-103: Permission Catalogue v2.2 (local development only)

- Added Permission Catalogue v2.2 as a second versioned overlay: the pinned AR-3B2A v2.2 addendum, `v2_2_delta.json` and `validation_v2_2.py`. v2.0 and v2.1 stay byte-identical and are validated first. `access_control.school_access.inspect` and `access_control.audit.school.read` move from Admin to Technical Super Admin, so School Admin holds no `access_control.*` default and keeps its WF-02 `accounts.*` permissions.
- Tests: v2.2 static 16/16; runtime (disposable database) 9/9; affected suites 921/921 in 37 modules (catalogue v2/v2.1/v2.2 and planners, registration-review P1 to P4, D-85, D-89, WF-03.01, WF-02.05 account status and P3B/provisioning, WF-02.06 history, release safeguard).
- **Not done:** validated specification only. Nothing was provisioned, and no consumer, route, navigation item or audit screen changed. P3B/P4 are unchanged (D-102 OPEN), and independent review of the addendum pins is OPEN (D-101).

### 19 November 2026 — WF-03.01 Stage D: D-89 Permission Catalogue v2.1 (local development only)

- Added Permission Catalogue v2.1 as a separately versioned overlay: the pinned AR-3B2A v2.1 addendum, `v2_1_delta.json` and `validation_v2_1.py`. v2 stays byte-identical and validates first. The only binding change moves `access_control.role_assignments.ordinary.manage` from Admin to Technical Super Admin, and the Admin and Technical Super Admin eligibility rules are restated. Every v2 security guarantee is re-checked.
- Tests: v2.1 static 17/17; runtime (disposable database) 9/9; affected suites 884/884 in 34 modules (every module reading the catalogue, the registration-review P1 to P4 suites, D-85, WF-03.01, WF-02.05 and the release safeguard).
- **Not done:** validated specification only. Nothing was provisioned and no consumer switched to v2.1; no real role or account changed; no API, switch, executor or production change; independent review of the addendum pin is OPEN.

### 18 November 2026 — WF-03.01 Stage D: D-85 P3B compatibility (local development only)

- The protected P3B compensation check now distinguishes registration-review, WF-02.05 school-account and the exact Technical Super Admin governance rows. The governance profile is accepted only when its definitions, bindings and 1 + 6 + 6 receipts match catalogue v2 and the database exactly, and compensation refuses while the governance profile exists.
- Tests: new D-85 module 16/16; affected suites D-85 16/16, test_wf0301_role_assignment 26/26, test_wf0205_p3b_compatibility 17/17, test_wf0205_school_accounts_provisioning 7/7 (first draft 7 errors, corrected), plus the P1/P2/P3B/P3C/P3D/P3E/P4, release-safeguard and WF-02.05 account-status suites, all within the regression below; accounts/access_control regression every accounts and access_control module (78) 1834/1834 OK; manage.py check no issues; makemigrations --check --dry-run no changes.
- **Not done:** no catalogue v2.1, no Technical Super Admin or administrator provisioning, no `ctug_workspace` change, no API activation, no executor/wex-1, no ERD or migration change, no push.

### 18 November 2026 — WF-03.01 staged implementation (local development only)

- Implemented and tested in the disposable test database: the Django-Superuser-exclusive `configure_workspace_roles` command (designated, re-authenticated framework operator; School Admin and Technical Super Admin grant/revoke; Instructor kept; exact catalogue v2 governance profile; audited; refuses `ctug_workspace`), Technical Super Admin School Admin assignment/revocation (service and isolated API, default-off, not mounted), the role-change session epoch, and Access control → Role assignments behind `VITE_WORKSPACE_ROLE_ASSIGNMENT_ENABLED`.
- Tests: 26 backend, 6 frontend unit and 6 browser tests; affected accounts/access_control regression 1818/1818; `npm test` 217/217; all browser suites 128/128; build passed; lint fails only on the two unchanged baseline findings (no WF-03.01 exception approved).
- **Not done:** no real administrator, role or permission changed; ordinary roles (catalogue v2.1), P3B/P4 compatibility, executor parity, API mounting and production remain blocked; pinned contracts, ERD and migrations unchanged.

### 18 November 2026 — WF-03.01 administrator authority alignment (documentation draft)

- Recorded the owner's updated rules: approved Instructor retains Instructor when assigned School Admin; only Django Superuser may grant/revoke Technical Super Admin, and Django Superuser may configure all data and roles through protected audited procedures. School Admin cannot manage any roles or permissions; Technical Super Admin may manage eligible School Admin and ordinary roles but not Technical Super Admin.
- Updated editable SRS v0.4 review draft, Use Case Specification working copies, WF-03.01, Master Test/UAT plan, traceability, decision register and access-control release-gate document; added ADR-004. No historical implementation, test results, Human Approvals, pins, official ERD or database objects changed.
- **Pending:** existing protected two-Admin/three-signer bootstrap, read-only Django Admin, permission catalogue v2 pins/validator, P3B/P4 and `wex-1` schema/security approval. No production authority or code implementation is inferred from the documentation amendments.


Document meaningful changes after they are verified. Avoid including credentials, secrets, or personal account information.

## 2026-11-08 — Local Development Checkpoint

### Confirmed

- Frontend production build passed using `npm run build`.
- Frontend automated tests passed: 25/25.
- Backend authentication and registration regression tests passed: 44/44.
- AR-6A1 Registration Review Service tests passed: 17/17.
- AR-6A2 First Workspace Admin Bootstrap tests passed: 15/15.
- First Workspace Admin successfully provisioned and audited in the local development database.
- Temporary bootstrap settings were removed after provisioning.
- Permission Catalogue V2 planner executed in read-only mode with zero conflicts.

### Permission Catalogue V2

- 10 proposed services.
- 95 proposed permissions.
- 106 proposed role-permission bindings.
- 105 CREATE, 4 MATCH, 108 DEFER, and 0 CONFLICT classifications.

**Status:** Planning-only. No permission catalogue activation was authorized.

---

## 2026-11-08 — AR-6B1 Permission Catalogue Governance Review

### Changed

- Added the registration-review permission scope proposal.
- Documented the intended Admin permissions for reading, approving, and rejecting registration requests.
- Created a read-only static catalogue verification script.
- Added governance and authorization restrictions to the implementation documentation.

### Verified

- Static catalogue verification passed.
- Three registration-review permissions confirmed in the V2 manifest.
- All three permissions proposed for the Admin role with `SCHOOL` scope.
- Catalogue remains unchanged and inactive.

### Security and Authorization

- No services or permissions activated.
- No role-permission grants applied.
- No modifications to the pinned V2 catalogue.
- Outstanding governance requirements remain unresolved.

**Status:** Static verification completed; governance approval pending.

---

## 2026-11-08 — AR-6C1 Inactive Registration Review API

### Changed

- Added candidate registration-review API views.
- Implemented API operations for listing pending registrations, approving requests, and rejecting requests.
- Added an isolated API URL configuration.
- Reused the existing registration-review domain service.
- Integrated session authentication, CSRF protection, effective-permission evaluation, and transactional auditing.
- Preserved disabled-by-default API and registration-approval feature gates.

### Verified

- Django system check passed with zero issues.
- Registration Review API tests passed: 18/18.
- Registration Review and Session Authentication regression tests passed: 31/31.
- Combined AR-6C1 test executions: 49/49 passed across two runs (not 49 distinct tests).
- Isolated MySQL test databases were destroyed after testing.

### Data and Migrations

- No new database migrations were introduced for AR-6C1.
- No permission grants or service activations were performed.
- Existing local development records were not modified by the isolated test runs.

### Security and Authorization

- Anonymous requests and unauthorized users are denied.
- CSRF protection is enforced.
- Effective permissions are validated.
- Individual Deny overrides take precedence over role grants.
- Django Superuser does not automatically receive Workspace API authority.
- Audit failures trigger transactional rollback.
- Registration approval API routes remain disconnected from the live root URL configuration.

### Documentation Updated

- `docs/DEVELOPMENT_STATUS.md`
- `docs/testing/TEST_RESULTS.md`
- `docs/implementation/authentication/ar-6c1-registration-review-api-inactive.md`
- `docs/api/AR-6C-registration-review-api-contract-proposal.md`
- `docs/testing/AR-6C-registration-review-api-test-matrix.md`

### Blocked / Follow-up

- Permission catalogue approval and activation.
- Final API security and governance review.
- Controlled URL integration.
- Full browser-based end-to-end testing.
- Permission-aware Admin dashboard implementation.

**Status:** Implemented and tested; not activated or approved for live use.

---

## 2026-11-08 — AR-6C2 Routing Safety Verification

### Changed

- Added `backend/apps/accounts/test_registration_review_routing.py` with seven routing safety tests.
- Preserved the isolated candidate URL configuration; no live root URL changes were made for this phase.

### Verified

- Routing safety tests passed: 7/7.
- Existing registration-review API tests passed again: 18/18.
- Combined run passed: 25/25 with zero failures.
- Existing `/api/v1/auth/session/` route remained resolvable.
- Isolated MySQL test database was destroyed after execution.

### Data and Migrations

- No migrations, permission grants, service activation, or live database changes were performed during this test run.

### Security and Authorization

- The pending-registration, approve, and reject routes remain absent from `config/urls.py`.
- Feature flags default to disabled; enabling flags in isolated tests alone does not publish the routes.
- The isolated candidate URL configuration resolves only when used explicitly for testing.
- Catalogue activation and live registration review remain blocked pending governance approval.

### Documentation Updated

- `docs/implementation/authentication/ar-6c2-routing-safety-verification.md`
- `docs/DEVELOPMENT_STATUS.md`
- `docs/testing/TEST_RESULTS.md`
- `docs/CHANGELOG.md`

### Blocked / Follow-up

- AR-6C3 integration-readiness and security-gap assessment.
- Governance decisions, activation policy, object authorization, and live end-to-end verification.

**Status:** Routing safety and regression tests passed; live API remains inactive.

---

## 2026-11-08 — ADR-003 Option A and AR-6C3 Readiness Assessment

### Changed

- Approved Option A: retain the existing `accounts.is_staff` and `accounts.is_superuser` boolean fields in the official protected ERD.
- Recorded the decision in `docs/decisions/ADR-003-django-framework-account-flags.md`.
- Reconciled the ERD fingerprint discrepancy in `docs/implementation/access-control/erd-fingerprint-provenance-2026-11-08.md` and prepared updated expected hashes for `backend/scripts/verify_catalogue_plan.py`.
- Documented registration-review API integration blockers in `docs/implementation/authentication/ar-6c3-integration-readiness-assessment.md`.

### Verified and Evidence Limits

- Offline inspection of the uploaded project snapshot identified the same two columns in both protected DBML files, the Django Account model, and migration `0002`.
- The prior pinned fingerprints were reproduced by removing only the two added field lines **in memory**; no DBML files were modified by this review.
- Approved current raw SHA-256 values are recorded in ADR-003. Matching those pins against the current Windows workspace and rerunning Django/MySQL tests remain separate local verification tasks.
- AR-6C3 is a **readiness assessment**, not a newly completed live integration or test run.

### Data, Security and Authorization

- No new migrations, schema writes, service activations, or permission grants were authorized by Option A.
- Django framework flags do not automatically grant Workspace API permissions; effective permissions remain governed by Workspace access-control checks.
- Registration-review routes and feature gates remain inactive pending separate scope, API contract, security, and activation approvals.

### Blocked / Follow-up

- Verify the approved DBML fingerprints and the read-only catalogue verifier on the current local checkout.
- Complete the remaining AR-6C3 governance and operational release gates before any live Admin approval UI or API activation.

**Status:** ERD design decision approved; local verification and registration-review integration remain pending.

---

## Changelog Template

### YYYY-MM-DD — Phase / Code Reference

- **Changed:** Description of implementation changes.
- **Verified:** Exact test commands and results.
- **Data/Migrations:** Schema changes or database effects.
- **Security/Authorization:** Permission and access-control impacts.
- **Documentation Updated:** Relevant documentation files.
- **Blocked/Follow-up:** Remaining requirements and risks.
- **Status:** Current implementation and operational status.
