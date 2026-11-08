# Test Results and Evidence â€” CTU-G Workspace

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
| AR-5A â€” Session Authentication | Session and registration regression | 44/44 passed |
| AR-6A1 â€” Registration Review Service | Registration approval/rejection service | 17/17 passed |
| AR-6A2 â€” First Admin Bootstrap | Initial Admin provisioning and security tests | 15/15 passed |
| AR-6C1 â€” Registration Review API | Session, CSRF, permissions, review actions, audit | 18/18 passed |
| AR-6C1 â€” Regression Verification | Registration review and session authentication | 31/31 passed |
| Django System Check | `python manage.py check` | Passed; 0 issues |

**AR-6C1 final verification date:** November 8, 2026.

The AR-6C1 API suite initially recorded 17 passes and one failure caused by an incomplete CSRF-cookie setup in the test fixture. After correcting the fixture, all 18 tests passed.

The subsequent 31 regression tests also passed.

**Combined AR-6C1 test executions:** 49 successful test executions across two separate test commands.

The tests ran using isolated temporary MySQL databases, which were destroyed after execution.

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
| AR-6C1 live URL integration | Not performed |

### Catalogue Planner Classifications

- CREATE: 105
- MATCH: 4
- DEFER: 108
- CONFLICT: 0

The planner did not perform database modifications, permission grants, or service activation.

**Security restriction:** AR-6B1 verification confirms that proposed permission definitions exist in the manifest. It does not authorize activating those permissions.

## 4. AR-6C1 Security Test Coverage

The 18 API tests cover:

- Anonymous and authenticated requests.
- Session authentication requirements.
- CSRF and invalid-origin rejection.
- Django Superuser separation from Workspace Admin.
- Effective permission evaluation.
- Individual Deny overrides.
- Inactive services and disabled feature flags.
- Registration listing and pagination validation.
- Registration approval and rejection.
- Self-review prevention.
- Previously reviewed account rejection.
- Permission revocation after session creation.
- Transactional rollback when audit writing fails.

**Result:** 18/18 passed.

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

1. AR-6C2 controlled API integration testing with live routes still disabled.
2. Formal review and authorization of the proposed permission catalogue.
3. Controlled catalogue initialization, authorization, and activation tests.
4. Complete object-level authorization and audit policy verification.
5. Browser-based authentication and registration-review integration tests.
6. Verification of permission-aware Admin dashboard navigation.
7. End-to-end registration, approval, login, and logout testing after authorized activation.
8. Final security regression and release-readiness review.

## 8. Current Testing Status

**AR-6C1:** Implementation and automated testing verified.

**Outstanding:** Governance approval, controlled permission activation, live URL integration, full browser testing, and deployment readiness.

**Overall assessment:** Development verification is progressing successfully. The registration-review API remains inactive and is not approved for live operation.