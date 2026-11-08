# CTU-G Workspace — Development Status

**As of:** November 8, 2026
**Basis:** Verified local build/test outputs and read-only planner/preflight results. This document is not a continuous live database audit.

## 1. System in Scope

- **Frontend:** React, TypeScript, Vite, and Tailwind CSS. Includes public pages, embedded login, registration, and a preliminary shared dashboard.
- **Backend:** Django and Django REST Framework using session authentication and CSRF protection.
- **Database:** MySQL (`ctug_workspace`) for local development, with isolated temporary MySQL databases for testing.
- **Access Control:** Hybrid Dynamic Access Control with application roles, role permissions, individual permission overrides, and audit logging.
- **Administrator Separation:** Django Superuser, Workspace Admin, and protected Technical Super Admin are distinct authorities.

## 2. Development Status by Phase

| Phase | Verified Result | Operational Status |
|---|---|---|
| AR-5A — Backend Session Authentication | 14 session tests and 30 registration regression tests passed | Implemented and tested; deployment hardening not asserted |
| AR-5B — Frontend Session Integration | Production build successful; 25/25 tests passed | Implemented and tested; browser E2E pending |
| AR-6A1 — Registration Review Service | 17/17 tests passed | Implemented and tested; live activation restricted |
| AR-6A2 — First Workspace Admin Bootstrap | 15/15 tests passed | First Workspace Admin provisioned and audited in local development |
| Catalogue V2 Planner | Read-only execution; zero conflicts | Planning-only; activation not approved |
| AR-6B1 — Catalogue Governance Review | Static verification passed; review draft documented | Governance approval pending |
| AR-6B2 — Controlled Permission Activation | Not performed | Blocked pending approval |
| AR-6C1 — Registration Review API | 18/18 API tests and 31/31 regression tests passed | Implemented and tested; live routes inactive |
| AR-6C2 — Routing Safety Verification | 7/7 routing and 18/18 API tests passed (25/25 combined) | Implemented and tested; live API inactive |
| AR-6C3 — API Integration Readiness Assessment | Not started | Next planned phase |
| AR-6D — Permission-Aware Admin Dashboard | Not implemented | Pending |

## 3. Last Observed Database Facts

These are verified historical observations, not continuously refreshed values.

- One Workspace Admin assignment was created.
- One successful first-Admin bootstrap audit event was recorded.
- One Django Superuser operator existed during the last bootstrap preflight.
- The temporary first-Admin bootstrap setting was removed.
- No services, permission definitions, or role-permission defaults were activated by the bootstrap.

### Permission Catalogue V2

| Item | Count |
|---|---:|
| Proposed services | 10 |
| Proposed permissions | 95 |
| Proposed role-permission bindings | 106 |
| Proposed roles | 6 |
| Existing matching roles | 4 |
| Deferred optional roles | 2 |
| CREATE classifications | 105 |
| MATCH classifications | 4 |
| DEFER classifications | 108 |
| CONFLICT classifications | 0 |

The planner operated in read-only mode. No database schema changes, permission grants, service activation, or catalogue repairs were performed.

## 4. Registration Review API Verification

**Date verified:** November 8, 2026

| Verification | Result |
|---|---|
| Django system check | Passed |
| AR-6C1 registration-review API tests | 18/18 passed |
| AR-6C1 registration review and session regression tests | 31/31 passed |
| AR-6C1 combined executed tests | 49/49 across separate runs |
| AR-6C2 routing safety tests | 7/7 passed |
| AR-6C2 API tests rerun | 18/18 passed |
| AR-6C2 combined executed tests | 25/25 passed |
| Isolated MySQL test database | Destroyed after the AR-6C2 run |

The API implementation includes candidate endpoints for viewing pending registrations, approving requests, and rejecting requests. Security coverage includes session authentication, CSRF enforcement, effective-permission checking, individual Deny precedence, Admin-role validation, self-review prevention, transactional audit rollback, and URL isolation.

AR-6C2 re-ran the 18 existing API tests alongside seven new routing tests; these are not 25 new, unique API tests.

**Operational restriction:** The API remains disconnected from the live root URL configuration. Its feature gates remain disabled, and no live permission activation has been approved.

## 5. Security and Authorization Rules

The following distinctions must remain separate:

- **Provisioned:** An account and its role assignment exist.
- **Defined:** Permission codes and service metadata exist.
- **Granted:** An authorized active permission binding exists.
- **Enforced:** Django validates effective permissions and applicable object scope.
- **Available:** The service and its dependent workflows have been approved and activated.

A Workspace Admin role assignment alone does not grant access to protected features.

Django Superuser credentials must not automatically authorize Workspace application actions.

## 6. Immediate Next Tasks

1. Complete the registration-review authorization-policy review and outstanding governance decisions.
2. Begin AR-6C3 API Integration Readiness Assessment. Review authorization, security requirements, and deployment dependencies while keeping live endpoints disabled.
3. Review the pinned V2 catalogue and document any explicitly approved revisions.
4. Design controlled permission initialization and activation procedures, subject to governance approval.
5. Complete registration-approval API release checks before connecting it to live Admin functions.
6. Develop the permission-aware Admin dashboard after backend access rules are approved.
7. Verify end-to-end registration, approval, login, and dashboard behavior when activation is authorized.
8. Reconcile affected SRS, ERD, architecture, API, and testing documentation with the implemented code.
9. Review and stage the still-untracked backend implementation separately; do not stage secrets or unfinished changes blindly.

## 7. Outstanding Risks and Restrictions

- Catalogue initialization, role grants, service activation, and live access-control mutations remain blocked pending approval.
- Technical Super Admin and SSG Advisor remain deferred role implementations.
- The one-time Admin bootstrap must not be re-enabled for routine use.
- The inactive registration-review API must not be registered into the live URL configuration until the required authorization and governance controls are approved.
- Session revocation, authentication-event retention, recovery governance, and full object-level authorization policies require further review.
- Sensitive credentials, `.env` files, and personally identifying account information must not be committed.
- Existing automated test coverage does not establish deployment approval or a completed browser end-to-end workflow.

## 8. Phase Completion Standard

A development phase can be labeled complete only after code review, passing relevant tests, validated migrations/configuration if applicable, documented security impacts, updated SRS/ERD/API documents when affected, and a reviewed Git commit. Track incomplete verification explicitly.

**Current development checkpoint:** AR-6C2 routing safety and API regression tests verified. Documentation synchronization underway. AR-6C3 is next; live registration approval remains blocked.
