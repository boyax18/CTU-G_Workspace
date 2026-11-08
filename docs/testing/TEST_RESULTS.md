# Test Results and Evidence — CTU-G Workspace

**As of:** November 8, 2026
**Evidence source:** Local PowerShell outputs and development test reports. Results must be verified again whenever relevant code, database schemas, or configuration changes.

## 1. Frontend Verification

| Area | Verification | Result |
|---|---|---|
| React production build | `npm run build` | Passed |
| Frontend automated tests | `npm test` | 25/25 passed |
| Browser end-to-end authentication | Manual browser verification | Pending |
| Permission-aware dashboard | Role-based navigation and access tests | Pending |

The successful frontend build confirms TypeScript compilation and Vite bundling. It does not independently establish end-to-end authentication or authorization correctness.

## 2. Backend Test Results

| Phase | Test Suite | Observed Result |
|---|---|---|
| AR-5A — Session Authentication | Session and registration regression | 44/44 passed |
| AR-6A1 — Registration Review Service | Registration approval/rejection service | 17/17 passed |
| AR-6A2 — First Admin Bootstrap | Initial Admin provisioning and security tests | 15/15 passed |
| AR-6C1 — Registration Review API | Session, CSRF, permissions, review actions, audit | 18/18 passed |
| AR-6C1 — Regression Verification | Registration review and session authentication | 31/31 passed |
| AR-6C2 — Routing Safety Verification | Routing safety plus registration-review API | 25/25 passed (7 routing + 18 API) |
| Django System Check | `python manage.py check` and checks during test setup | Passed; 0 issues |

**AR-6C1 final verification date:** November 8, 2026.

The AR-6C1 API suite initially recorded 17 passes and one failure caused by an incomplete CSRF-cookie setup in the test fixture. After correcting the fixture, all 18 tests passed.

The subsequent 31 regression tests also passed.

**Combined AR-6C1 test executions:** 49 successful test executions across two separate test commands. These are execution counts, not 49 unique test cases.

The tests ran using isolated temporary MySQL databases, which were destroyed after execution.

### AR-6C2 Final Routing Verification

**Date verified:** November 8, 2026

**Command (from `backend/`):**

```powershell
python manage.py test apps.accounts.test_registration_review_routing apps.accounts.test_registration_review_api --settings=config.test_settings --noinput --verbosity 2
```

- **Discovered:** 25 tests.
- **Passed:** 25/25 (7 routing safety tests and 18 API tests).
- **Failed:** 0.
- **Database:** Temporary isolated MySQL test database, successfully destroyed after the run.
- **Scope:** Routes remain absent from the live root URL configuration; feature flags still default to OFF.

The 18 API tests were rerun in AR-6C2; they are not 18 additional, distinct test cases. A logged `RuntimeError` during the intentional audit-writer failure simulation is expected; the corresponding negative test passed.

## 3. Database and Security Verification

| Verification | Observed Result |
|---|---|
| Initial Workspace Admin bootstrap | Successfully provisioned and audited |
| Post-bootstrap preflight | 1 Admin assignment and 1 bootstrap event |
| Permission catalogue V2 planner | Completed in read-only mode |
| Catalogue conflicts | 0 |
| Proposed services | 10 |
| Proposed permission definitions | 95 |
| Proposed role-permission bindings | 106 |
| AR-6B1 static catalogue inspection | Passed |
| Registration-review permission definitions | All 3 verified |
| Registration-review permission scope | `SCHOOL` |
| Live permission catalogue activation | Not performed |
| AR-6C1/AR-6C2 live URL integration | Not performed |

### Catalogue Planner Classifications

- CREATE: 105
- MATCH: 4
- DEFER: 108
- CONFLICT: 0

The planner did not perform database modifications, permission grants, or service activation.

**Security restriction:** AR-6B1 verification confirms that proposed permission definitions exist in the manifest. It does not authorize activating those permissions.

## 4. AR-6C1 and AR-6C2 Security Test Coverage

The API and routing tests cover:

- Anonymous and authenticated requests.
- Session authentication requirements.
- CSRF and invalid-origin rejection.
- Django Superuser separation from Workspace Admin.
- Effective permission evaluation and individual Deny overrides.
- Inactive services and disabled feature flags.
- Registration listing and pagination validation.
- Registration approval and rejection.
- Self-review prevention and previously reviewed account refusal.
- Permission revocation after session creation.
- Transactional rollback when audit writing fails.
- Explicit confirmation that review routes are not present in the live URL configuration.
- Explicit confirmation that isolated candidate routes resolve without publishing them.
- Preservation of the existing session endpoint.

**Results:** AR-6C1 18/18; AR-6C2 combined 25/25.

The API implementation remains isolated from the live root URL configuration. Its security-related feature gates remain disabled.

## 5. Regression Commands

Run these commands from the appropriate project directories.

### Frontend

```powershell
cd frontend
npm run build
npm test
```

### Backend

```powershell
cd backend
python manage.py check
python manage.py test apps.accounts.test_session_auth apps.accounts.test_registration --settings=config.test_settings --noinput
python manage.py test apps.accounts.test_registration_review apps.accounts.test_admin_bootstrap --settings=config.test_settings --noinput
python manage.py test apps.accounts.test_registration_review_api --settings=config.test_settings --noinput --verbosity 2
python manage.py test apps.accounts.test_registration_review_routing apps.accounts.test_registration_review_api --settings=config.test_settings --noinput --verbosity 2
```

### Read-Only Permission Catalogue Verification

From the backend directory:

```powershell
python manage.py plan_permission_catalogue_v2
python scripts/check_registration_review_catalogue.py
```

These commands must not activate services or grant permissions.

## 6. Evidence Quality Rules

- Passing automated tests does not establish production readiness.
- Keep sanitized terminal logs or CI results as evidence for future runs.
- Never publish passwords, tokens, `.env` contents, personal account information, or private database credentials.
- Verify the configured database before any database-changing operation.
- Test successful authorization alongside explicit denial cases.
- Verify transaction rollback and audit consistency.
- Record the difference between proposed, implemented, tested, approved, and activated functionality.

## 7. Next Verification Requirements

1. AR-6C3 integration readiness review, including authorization, security gaps, and governance release requirements.
2. Formal review and authorization of the proposed permission catalogue.
3. Controlled catalogue initialization, authorization, and activation tests.
4. Complete object-level authorization and audit policy verification.
5. Browser-based authentication and registration-review integration tests.
6. Verification of permission-aware Admin dashboard navigation.
7. End-to-end registration, approval, login, and logout testing after authorized activation.
8. Final security regression and release-readiness review.

## 8. Current Testing Status

**AR-6C1:** Implementation and automated testing verified.

**AR-6C2:** Routing safety and API regression testing verified (25/25). The review API remains inactive.

**Outstanding:** Governance approval, controlled permission activation, live URL integration, full browser testing, and deployment readiness.

**Overall assessment:** Development verification is progressing successfully. The registration-review API is not approved for live operation.
