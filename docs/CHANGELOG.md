# CTU-G Workspace — Development Changelog

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
