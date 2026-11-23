# Test Results and Evidence — CTU-G Workspace

**As of:** November 23, 2026
**Evidence source:** Current runtime inspection and isolated WF-02 verification below; earlier sections retain their dated historical evidence. Results must be revalidated whenever relevant code, schema, or configuration changes.

## 23 November 2026 — Current local runtime activation inspection

This is a read-only runtime/configuration check, separate from the isolated synthetic tests below. It did not expose or record personal fields, change `.env`, alter the real database, or claim live authenticated browser verification.

| Check | Observed result |
| --- | --- |
| Database | Read-only connection confirmed `ctug_workspace`; 3 eligible Pending Student applications and 1 eligible ordinary Approved directory account (before viewer exclusion) were counted without selecting personal fields |
| Services and grants | `accounts` and `access_control` services active; both WF-02 read permissions exist with active Admin grants |
| Effective role-context permissions | Current database assignments evaluated both reads as allowed in Admin and Technical Super Admin contexts; Student and Instructor contexts were denied. The Technical Super Admin assignment has an active Admin assignment. No session or role assignment was changed |
| Backend/frontend read flags | Applicant-list, account-directory and account-status flags unset/default-off; normal list/directory API probes returned 503 |
| Mutations and delivery | Approval/rejection and status-write routes remain unmounted or separately gated; outbox delivery is off |
| Network safety | Vite answered on a private LAN interface over plain HTTP, with no transport-security headers; `127.0.0.1:5173` was unavailable. Real-data read flags were not enabled |
| Fresh local startup | A fresh settings import was refused because the existing uncommitted LAN role-context acknowledgement is set while `DJANGO_DEBUG` is unset/false. Existing LAN/HTTPS work was preserved; inspection/test processes cleared only their own environment variables |
| Verification | Isolated backend: 86/86 passed. Focused frontend/browser: 60/60 passed. Frontend production build passed. An expanded selection including dashboard navigation had 72/73 pass; the one failure is the existing appointment-permission/frozen-catalogue mismatch described below and in the historical checkpoint |

The browser cases here use synthetic fixtures/mocked APIs and do **not** prove live integration. The live checks establish database counts, stored grants, configured gates and endpoint availability only. Remaining activation requirements are a loopback-only or approved secure origin, a valid local startup configuration, the two read flags, and an authenticated end-to-end check. No real account data was displayed.

## 23 November 2026 — WF-02 dashboard integration

Source baseline: branch `ronald`, parent `d9b58da`; pre-existing LAN/settings/script changes left outside this implementation commit. These are source, synthetic database and mocked-browser checks, not live release or human approval evidence.

| Check | Observed result |
| --- | --- |
| Final backend integration/regression | 250/250 passed, 0 failed/errors/skipped across 15 selected modules; fresh disposable MySQL database destroyed after the run |
| Backend status/outbox/release supplement | 46/46 passed in 3 additional modules; separate fresh disposable MySQL database destroyed |
| Focused frontend contracts/clients and role context | 73/73 passed, 0 failed/skipped |
| Six existing WF-02/dashboard browser suites | 62/62 passed, 0 failed/skipped |
| Independent read-only directory build/browser suite | 3/3 passed, 0 failed/skipped; School Admin and Technical Super Admin access with only the directory read build flag; no status controls/POST; Student denied |
| Full frontend unit suite | 238 tests: 237 passed, 1 existing failure (`dashboard-navigation.test.mjs`: appointment permission absent from frozen v2.0 inventory) |
| Changed/new frontend source and tests lint | Passed, 0 problems |
| Full frontend lint | 3 existing `react-hooks/set-state-in-effect` errors: `RoleContextSwitcher.tsx` lines 16 and 19, `RolePermissionsPanel.tsx` line 52; these files are unchanged by this task |
| `npm.cmd run build` | Passed: TypeScript and Vite production bundle |
| Django system checks | No issues during isolated test setup; all three normal WF-02 backend flags observed unset/default-off |
| Schema/migrations | No model/migration/DBML change; no migration applied to `ctug_workspace` |
| Git diff validation | `git diff --check` passed; source comparison confirmed every original catalogue approval/checklist line unchanged and all six existing WF-02 sections updated |

Backend coverage includes the real normal read URLconf, exact permissions and Admin assignment, Technical Super Admin inheritance in its own selected context, actual role-context switch to Instructor and subsequent denial, Student/Instructor/anonymous denials, Deny precedence, revoked inherited assignment, protected-target exclusion, search/status filtering, default-off read gates, no mounted normal writes/governance, no-store responses and server action hints under isolated mutation gates. Existing approval/rejection/status/history suites retain transaction, proof, deletion/outbox, conflict, audit and revocation coverage. Release-guard tests cover exact read mounts and refusal of moved/renamed/overridden/subclassed/duplicate mounts, status writes and provisioning while the new read gate is on.

Browser suites use fresh headless Edge profiles, localhost-only Vite and synthetic/mocked APIs. They cover read content, search/filter/pagination, unavailable/expired/forbidden/error/empty states, confirmations, uncertain-write handling with no replay, hidden disabled actions, keyboard/focus behavior and 360/768/1024/1440px layouts in Light, System-dark and Dark with contrast checks. Backend behavior is established separately by isolated MySQL tests; browser mocks are not live API E2E evidence. The 250-case backend run and 46-case supplement used 18 distinct selected modules in separate databases. The 73 focused frontend tests overlap the full 238 and must not be added as unique cases. The 62 and 3 browser cases ran separately.

Commands from `frontend/`:

```powershell
npm.cmd test
node --test tests/account-status.test.mjs tests/registration-review-api-contract.test.mjs tests/registration-review-approval.test.mjs tests/registration-review-rejection.test.mjs tests/role-context-immediate-selection.test.mjs tests/role-context-normal-app.test.mjs tests/role-context-switching.test.mjs
node --test tests/browser/pending-applications-errors.test.mjs tests/browser/applicant-detail-errors.test.mjs tests/browser/applicant-approval-errors.test.mjs tests/browser/applicant-rejection-errors.test.mjs tests/browser/account-directory-errors.test.mjs tests/browser/dashboard-shell-errors.test.mjs
node --test tests/browser/account-management-readonly-errors.test.mjs
npm.cmd run lint
npm.cmd run build
```

Changed-file lint used the frontend-relative paths from `git diff --name-only --relative`, plus `src/features/admin/managementAvailability.ts` and `tests/browser/account-management-readonly-errors.test.mjs`. `npm.cmd` avoids this machine's PowerShell script execution restriction; it does not change execution policy.

Backend command from `backend/` (existing local virtual environment). The preamble loads local credentials without printing them and clears only three process-local development acknowledgements; existing `.env`/settings files are not edited:

```powershell
@'
from dotenv import load_dotenv
load_dotenv('.env')
import os, sys, runpy
for key in ('CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK', 'CTUG_ROLE_CONTEXT_LAN_DEV_ACK', 'CTUG_ROLE_CONTEXT_HTTPS_LAN_DEV_ACK'):
    os.environ[key] = ''
modules = [
    'apps.accounts.test_wf02_dashboard_integration',
    'apps.accounts.test_wf0201_pending_list',
    'apps.accounts.test_wf0202_applicant_detail',
    'apps.accounts.test_wf0203_approval',
    'apps.accounts.test_wf0204_rejection',
    'apps.accounts.test_wf0205_account_status',
    'apps.accounts.test_wf0206_account_history',
    'apps.access_control.test_wf0201_release_safeguard',
    'apps.access_control.test_wf0301_d113_role_context',
    'apps.accounts.test_registration_review_routing',
    'apps.accounts.test_registration_review_api',
    'apps.accounts.test_review_sandbox_boundary',
    'apps.access_control.test_registration_review_metadata_local_dev',
    'apps.access_control.test_registration_review_operational_gate_p3c',
    'apps.access_control.test_registration_review_local_release_p4',
]
sys.argv = ['manage.py', 'test', *modules, '--settings=config.test_settings', '--noinput']
runpy.run_path('manage.py', run_name='__main__')
'@ | .\.venv\Scripts\python.exe -
```

The 46-case supplement used the same backend wrapper with `modules = ['apps.accounts.test_wf0205_stage2', 'apps.accounts.test_wf0204_outbox_erasure', 'apps.accounts.test_wf0204_release_settings']`.

`config.test_settings`/`IsolatedMySQLRunner` selects a fresh unpredictable `test_ctug_registration_<16 hex>` database, refuses reuse/cloning and verifies the connected database before fixtures. Test migrations are disposable setup; no development-database migration or account mutation is authorized by this command. Final database teardown is recorded with the final result above.

Intermediate outcomes are retained honestly: the first backend command stopped at the existing LAN startup guard before database access. The first 177-case regression then had 176 successes and one error in the new action-hint fixture because its temporary URLconf omitted applicant detail; the fixture was corrected and the final expanded run is reported above. The first frontend run also exposed a missing-header compatibility issue in older mocks; the client now fails closed for absent headers, with regression coverage. Full frontend test/lint blockers persist independently of these fixes: the frozen-inventory mismatch exists in the original navigation, and all three lint findings are in unchanged files. The initial 46-case supplement hit two stale assertions within the old no-normal-routes test; it was updated to verify mounted reads return 503 by default and status writes remain unmounted. Its rerun passed all 46 cases. The expected audit-writer failure simulation can log a safe RuntimeError; the legacy date fixture emits a naive-datetime warning.

Remaining unverified: real applicant data over approved HTTPS, live permission/service readiness, live SMTP delivery, shared-LAN safety, production deployment, pending protected WF-03 activation/migrations and full backend repository regression outside the selected suites. No new Human Approval, grant/provisioning, protected executor activation or push is inferred from passing tests.

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
