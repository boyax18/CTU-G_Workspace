# Test Results and Evidence — CTU-G Workspace

**As of:** November 8, 2026
**Evidence source:** Local PowerShell outputs and development test reports, plus the November 8, 2026 local protected-ERD hash checks. Results must be revalidated whenever relevant code, schema, or configuration changes.

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
| AR-6C3 registration review integration | Source-based assessment documented; no live integration or new Django test run |
| ADR-003 protected ERD SHA-256 | Both locally matched approved Option A pins on November 8, 2026 |

### Catalogue Planner Classifications

- CREATE: 105
- MATCH: 4
- DEFER: 108
- CONFLICT: 0

The planner did not perform database modifications, permission grants, or service activation.

**Security restriction:** AR-6B1 verification confirms that proposed permission definitions exist in the manifest. The `SCHOOL` scope and three Admin registration-review permissions remain **proposals**, not approved grants or an authorization to activate services.

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

1. Complete the open AR-6C3 release gates after the documented source-based readiness assessment: registration-review object/field scope, API contract and security policy approvals.
2. Approve the minimal registration-review permission definitions and any necessary service/role grants **separately** from ADR-003.
3. Re-run the patched integrity verifier in the approved local read-only environment, with no database mutations.
4. After explicit authorization, test controlled catalogue initialization, grant activation, auditing and rollback.
5. Complete object-level authorization, session revocation, concurrency and transactional audit tests.
6. Conduct browser authentication and registration-review integration tests and verify permission-aware Admin dashboard navigation.
7. Demonstrate registration, authorized approval, login, dashboard and logout end to end only after approved activation.
8. Complete final regression and release-readiness review. Do not infer production readiness from isolated passes.

## 8. ADR-003 Integrity and AR-6C3 Assessment Evidence

**Option A scope:** The owner approved the existing `accounts.is_staff` and `accounts.is_superuser` columns in both protected DBML files. The checks below do **not** activate registration review.

| Evidence | Observed result | Source |
|---|---|---|
| `docs/database/full_schema.dbml` SHA-256 | `e4362be913280ab6c23d5c66af249fc1923fccb1acd7b6c2696f7ee95c19d4a0` — matched | Owner's Windows `Get-FileHash` output, November 8, 2026 |
| `docs/database/schema.dbml` SHA-256 | `3bc2060ae35fce16725d6ca5b90272e819039b8dce855ffe305b654140f77313` — matched | Owner's Windows `Get-FileHash` output, November 8, 2026 |
| Historical pin reconciliation | Removing only the two framework-flag lines **in memory** reproduced both prior recorded fingerprints | Earlier offline ZIP inspection |
| Updated `verify_catalogue_plan.py` Python syntax | Passed for the prepared patch; no local owner result reported | Earlier offline patch inspection |
| AR-6C3 review | Source-based readiness assessment recorded; **not** a new automated integration test run | `docs/implementation/authentication/ar-6c3-integration-readiness-assessment.md` |

**Still pending:** The owner has not supplied a successful execution log for the complete updated read-only Django/MySQL integrity verifier, new Django integration tests, any catalogue activation, or full browser E2E. ADR-003 design approval is **not** permission-catalogue or API activation approval.

## 9. Current Testing Status

**AR-6C1:** Implementation and automated testing verified.

**AR-6C2:** Routing safety and API regression testing verified (25/25). The review API remains inactive.

**AR-6C3:** Source-based readiness assessment recorded. ADR-003 ERD option approved; both local protected-ERD fingerprints confirmed. No new Django integration tests or live registration-review activation are claimed.

**Outstanding:** Registration-review scope and API contract approval, controlled catalogue activation, local verifier execution, live URL integration, full browser testing, and deployment readiness.

**Overall assessment:** Development verification is progressing successfully. The registration-review API is not approved for live operation.
