# CTU-G Workspace — Development Changelog
Document meaningful changes after they are verified. Avoid including credentials, secrets, or personal account information.
## 2026-11-08 — Local Development Checkpoint

### Confirmed

- Frontend production build passed using `npm run build`.
- Frontend automated tests passed: 25/25.
- Backend authentication and registration regression tests passed: 44/44.
- AR-6A1 Registration Review Service tests passed: 17/17.
- AR-6A2 First Workspace Admin Bootstrap tests passed: 15/15.
- First Workspace Admin successfully provisioned and audited.
- Temporary bootstrap settings removed after provisioning.
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
- Combined AR-6C1 test executions: 49/49 passed.
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

## Changelog Template

### YYYY-MM-DD — Phase / Code Reference

- **Changed:** Description of implementation changes.
- **Verified:** Exact test commands and results.
- **Data/Migrations:** Schema changes or database effects.
- **Security/Authorization:** Permission and access-control impacts.
- **Documentation Updated:** Relevant documentation files.
- **Blocked/Follow-up:** Remaining requirements and risks.
- **Status:** Current implementation and operational status.