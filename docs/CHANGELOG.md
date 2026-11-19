# CTU-G Workspace — Development Changelog

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
