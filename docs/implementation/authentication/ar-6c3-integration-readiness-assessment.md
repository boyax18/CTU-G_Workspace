# CTU-G Workspace — AR-6C3 Registration Review Integration Readiness

**Date:** November 8, 2026

**Phase:** AR-6C3

**Status:** READINESS ASSESSED — ERD GATE RESOLVED BY ADR-003; LIVE INTEGRATION NOT APPROVED

**Source:** User-uploaded CTU-G Workspace ZIP and current documentation. This assessment made no source-code, migration, database, permission, feature-flag, or deployment changes.

## 1. Objective

Identify the exact conditions that must be satisfied before connecting the already-implemented registration-review API to the Admin dashboard. Avoid duplicating AR-6A1, AR-6C1, or AR-6C2 implementations and preserve fail-closed authorization.

## 2. Observed code contracts

| Component | Exact source file | Observed state |
| --- | --- | --- |
| Session login, logout, session lookup and explicit unsafe-method CSRF | `backend/apps/accounts/session_auth.py` | Implemented; Django session resolved server-side |
| Registration review domain transactions | `backend/apps/accounts/registration_review.py` | Implemented for Student/Instructor Pending requests; approval/rejection/audit guarded by `WORKSPACE_REGISTRATION_APPROVAL_ENABLED` |
| Registration review HTTP views | `backend/apps/accounts/registration_review_api.py` | Implemented candidate list/approve/reject views; both `WORKSPACE_REGISTRATION_REVIEW_API_ENABLED` and `WORKSPACE_REGISTRATION_APPROVAL_ENABLED` required |
| Candidate URL patterns | `backend/apps/accounts/registration_review_urls.py` | Isolated; 3 candidate routes defined |
| Root URL configuration | `backend/config/urls.py` | Exposes `/admin/` and `/api/v1/auth/` only; does **not** include registration-review URLs |
| Effective permissions | `backend/apps/access_control/services.py` | Read-only DB-derived evaluator; account Deny overrides prevail; inactive services block permissions |
| Permission catalogue | `backend/apps/access_control/catalogue/v2_0.json` | Proposal: 10 services, 95 permissions, 106 proposed role-permission bindings; **not approved or activated** |
| Existing dashboard | `frontend/src/features/dashboard/SessionDashboardPage.tsx`, `frontend/src/App.tsx` | Session/profile view; no Admin review screen or registration-review route |

The API requires a currently eligible Workspace Admin assignment **and** the exact effective permission on each operation. A role name or client-provided list does not authorize a request. The transactional domain service independently rechecks approval/rejection authorization and writes an audit record.

## 3. Exact requested permissions and service dependencies

| Operation | Exact permission code | Target constraints |
| --- | --- | --- |
| `GET` pending queue | `accounts.registration_requests.read` | Pending, inactive, Student/Instructor requested role, unreviewed and not already assigned; minimized fields |
| `POST` approval | `accounts.registration_requests.approve` | Eligible Pending target; reviewer != target; approve and assign only requested base role; transactional audit |
| `POST` rejection | `accounts.registration_requests.reject` | Same target restrictions; one of four allowlisted non-sensitive rejection codes; transactional audit |

The current code additionally requires active `accounts` and `access_control` services, an active Admin role assignment for the reviewer, and a current effective grant. Those dependencies are **not equivalent** to approval to activate them. `ADR-002-registration-review-scope-proposal.md` remains PROPOSED.

## 4. Release blockers

| Gate | Current finding | Minimum acceptance evidence |
| --- | --- | --- |
| G1 — Protected ERD contract | **Owner-approved Option A (ADR-003)** adopts both columns; expected hash pins updated to current raw DBML bytes | **Design approval recorded**; local file fingerprint and read-only runtime verifier still need recheck. See `docs/implementation/access-control/erd-fingerprint-provenance-2026-11-08.md` |
| G2 — Object scope and field minimization | `SCHOOL` scope and eligible list fields are proposed, not formally adopted | Signed/recorded acceptance of eligible account subset, returned fields, and cross-account access policy |
| G3 — API contract | Routes and request/response/error format are candidates; not adopted | Approved versioned endpoint contract and acceptance criteria |
| G4 — Catalogue initialization | Required services/permissions/bindings are planning-only | Reviewed minimal, versioned activation profile, owner authorization, independent execution/audit and negative test evidence; do not activate whole V2 implicitly |
| G5 — Security & recovery policy | Session revocation/step-up, audit retention, attribution, replay, concurrency and recovery rules are still governance questions | Approved policy and isolated MySQL tests for revocation, parallel decisions, failure rollback, effective permission Deny and audit consistency |
| G6 — Operational and routing enablement | URLconf lacks review routes; both gates disabled by default | Controlled, separately approved URL/flag deployment after G1–G5; fail-closed rollback plan |
| G7 — Admin frontend | `App.tsx` has no Admin review route; dashboard is a session display | Permission-aware, accessible queue with loading/empty/error/403/503 handling, confirmation, no unsafe auto-retry, and backend-authoritative checks |
| G8 — End-to-end verification | Browser registration -> decision -> login -> dashboard not yet demonstrated | Real browser E2E and full backend/frontend regression evidence in a controlled test environment |

## 5. Verification evidence and limitations

- **Prior local evidence supplied by the user:** AR-6C2 7 routing tests plus AR-6C1 18 API tests passed together (**25/25**); earlier AR-6C1 isolated API suite passed **18/18** and separate regressions **31/31**. These were **not rerun** during this read-only AR-6C3 assessment.
- **Current ZIP inspection:** exact URL isolation, feature gates and permission checks were read from source. Python syntax and frontend tests were verified during the earlier inspection of this same archive (**126/126 source parse; 25/25 frontend tests**).
- **Not verified in this AR-6C3 run:** local MySQL state, migrations applied in the user's Windows installation, Django integration tests, live permissions, browser E2E, or institutional approvals.
- **Documentation inconsistency observed in ZIP:** `docs/implementation/authentication/ar-6c2-routing-safety-verification.md` still labels its result *pending*, whereas `docs/DEVELOPMENT_STATUS.md` records AR-6C2 as tested. Update the older report using the verified 25/25 terminal output; do not claim it was rerun here.

## 6. Minimal implementation sequence

1. **ERD decision recorded:** Option A approved in ADR-003; verify the revised DBML hashes and read-only verifier locally. Obtain separate owner approval for the minimal registration-review scope.
2. **Design with no activation:** Confirm the exact approved API fields and expected Admin interface behavior; write testable acceptance criteria.
3. **After independent approval:** Implement and verify the narrow catalogue/service activation transaction with a versioned profile, protected reviewer/executor separation, audit and rollback; verify exact effective grants.
4. **Only after those gates pass:** Register the review URLconf and enable the two feature flags in a controlled environment, keeping all other module permissions inactive.
5. **Admin UI:** Extend `frontend/src/App.tsx` and dashboard routing; add a dedicated `frontend/src/features/admin/` feature and a typed registration-review API client (existing `frontend/src/api/client.ts` currently supports CSRF-protected POST). Backend stays authoritative on every read/write.
6. **Integration:** Test Pending registration -> authorized Admin decision -> new account's active base-role assignment -> login -> dashboard -> logout, including Deny/revocation, race conditions, audit rollback, denial and stale-request responses.
7. **Documentation and release:** Update `docs/DEVELOPMENT_STATUS.md`, `docs/testing/TEST_RESULTS.md`, `docs/security/ACCESS_CONTROL_GATES.md`, SRS/API contracts, and release checklist from actual evidence.

## 7. Exact next action

**The `is_staff` / `is_superuser` ERD decision is resolved by ADR-003. Request a separate project-owner decision on the three-permission registration-review minimum scope and verify local integrity pins before any operational changes.** No database or deployment change is safe until those decisions are recorded. Continue reviewing the source and writing tests without enabling live routes or grants.

**Conclusion:** AR-6C3 readiness analysis is complete, but **registration-review activation is still blocked**. This report does not authorize further protected-ERD changes, catalogue activation, grants, or exposing the API. It records the separately approved Option A fingerprint reconciliation only.
