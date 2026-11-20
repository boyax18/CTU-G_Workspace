# CTU-G Workspace — AR-6C1 Registration Review API (Inactive Implementation)

**Prepared:** 2026-11-08
**Status:** IMPLEMENTED AND TESTED — NOT DEPLOYED OR APPROVED
**Phase:** AR-6C1 — create isolated URLconf and guarded Django REST views, tests; do not link to live root URLconf

## Motivation and authority

Existing `session_auth.py` implements cookie-based Django sessions and explicit CSRF, while `registration_review.py` implements the atomic approve/reject domain service. AR-6B1 confirmed the pinned V2 catalogue is planning-only. These API views reuse the existing components, but do **not** confer authority from account role names alone. The first Workspace Admin was provisioned, but still has no active catalogue grants.

## New files

- `backend/apps/accounts/registration_review_api.py`: list, approve, reject candidate API with two independent feature gates defaulting to OFF.
- `backend/apps/accounts/registration_review_urls.py`: **isolated** candidate URLconf, **NOT registered** in `config/urls.py`.
- `backend/apps/accounts/test_registration_review_api.py`: 18 isolated MySQL tests, temporarily mounting candidate URLs via `override_settings` and enabling the two flags in the test process ONLY.

No existing files, migrations, schema, role definitions, grants, or services are modified. No route becomes live when these files are copied.

## Proposed endpoints (not yet live)

Once institutional review and security gates are accepted, a later explicitly approved change may include this isolated URLconf under `/api/v1/registration-requests/`:

- `GET /api/v1/registration-requests/?page=1&status=Pending`: pending, eligible Student/Instructor requests only; 20 per page; candidate fields `account_id`, `school_id`, `requested_role`, `created_at`.
- `POST /api/v1/registration-requests/{account_id}/approve/`: only `{}` JSON, calls AR-6A1 domain service.
- `POST /api/v1/registration-requests/{account_id}/reject/`: only a service-approved `rejection_code`, calls AR-6A1 domain service.

Missing/invalid session, missing active `Admin` assignment, or missing exact effective permission blocks the action. Role name alone never suffices. An individual `Deny` overrides a role grant. Framework Superuser cannot use the Workspace API. Mutations still require active `accounts` and `access_control` services, and the domain service transaction handles locks and audit; API does not wrap that durable transaction in another transaction.

## Inactive by default

1. `WORKSPACE_REGISTRATION_REVIEW_API_ENABLED` defaults to `False` when absent.
2. `WORKSPACE_REGISTRATION_APPROVAL_ENABLED` also defaults to `False` when absent.
3. The candidate URLconf is not linked into `config.urls`.

**Do not enable these flags or include these routes until the V2 governance gates, independent reviews, signed activation profile, approved data scope, and end-to-end security tests are completed.** Only tests should override them in an isolated environment.

## Validation

After copying the three files, from `backend/`:

```powershell
python manage.py check
python manage.py test apps.accounts.test_registration_review_api --settings=config.test_settings --noinput --verbosity 2
python manage.py test apps.accounts.test_registration_review apps.accounts.test_session_auth --settings=config.test_settings --noinput
```

Local verification completed on November 8, 2026. All 18 Registration Review API tests and 31 regression tests passed. The isolated MySQL test databases were destroyed after testing. The API remains inactive and is not registered in the live URL configuration. Record actual discoveries, passes/failures, and DB cleanup in `docs/testing/TEST_RESULTS.md`. Update `docs/DEVELOPMENT_STATUS.md`, the endpoint inventory, and security gates after review; never state the route is deployed before it is registered and authorized.

## Outstanding design and release checks

- Final school/object scope, minimal data-field approval and retention. Current ERD does not define a campus tenant; do not invent one.
- Independent authorization/activation approvals, including catalogue digest, break-glass and recovery policies, audited grants/activation.
- Authentication-event log, stage/access traceability, error semantics, IP + identity throttling, concurrent HTTP requests, denied-attempt audit policy and security regression tests.
- Integration with the Admin dashboard only after server-side permissions and positive + negative tests are proven.


## AR-6C1 — Test Verification

**Date:** November 8, 2026
**Project:** CTU-G Workspace
**Phase:** AR-6C1 — Inactive Registration Review API

### Test Results

- Django system check: Passed
- Registration Review API: 18/18 passed
- Registration Review and Session Authentication regression: 31/31 passed
- Combined executed tests: 49/49 passed

### Implementation Status

The registration approval API implementation has passed isolated tests. It supports authorization checks, session authentication, CSRF validation, registration review, and transactional auditing.

The endpoints remain disconnected from the live URL configuration. Permission catalogue activation and operational governance approvals remain pending.

**Status:** Implementation tested; not activated for live use.