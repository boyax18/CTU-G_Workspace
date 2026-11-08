# CTU-G Workspace â€” Development Status

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
| AR-5A â€” Backend Session Authentication | 14 session tests and 30 registration regression tests passed | Implemented and tested |
| AR-5B â€” Frontend Session Integration | Production build successful; 25/25 tests passed | Implemented and tested; browser E2E pending |
| AR-6A1 â€” Registration Review Service | 17/17 tests passed | Implemented and tested; live activation restricted |
| AR-6A2 â€” First Workspace Admin Bootstrap | 15/15 tests passed | First Workspace Admin provisioned and audited |
| Catalogue V2 Planner | Read-only execution; zero conflicts | Planning-only; activation not approved |
| AR-6B1 â€” Catalogue Governance Review | Static verification passed; review draft documented | Review ongoing; governance approval pending |
| AR-6B2 â€” Controlled Permission Activation | Not performed | Blocked pending approval |
| AR-6C1 â€” Registration Review API | 18/18 API tests and 31/31 regression tests passed | Implemented and tested; live routes inactive |
| AR-6C2 â€” Controlled API Integration Preparation | Not started | Next planned implementation phase |
| AR-6D â€” Permission-Aware Admin Dashboard | Not implemented | Pending |

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

## 4. AR-6C1 â€” Registration Review API Verification

**Date verified:** November 8, 2026

| Verification | Result |
|---|---|
| Django system check | Passed |
| Registration Review API tests | 18/18 passed |
| Registration Review and Session Authentication regression tests | 31/31 passed |
| Combined executed tests | 49/49 passed |

The implementation includes candidate endpoints for viewing pending registrations, approving requests, and rejecting requests.

Security coverage includes session authentication, CSRF enforcement, effective-permission checking, individual Deny precedence, Admin-role validation, self-review prevention, and transactional audit rollback.

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
2. Prepare AR-6C2 controlled API integration tests while keeping live endpoints disabled.
3. Review the pinned V2 catalogue and document any explicitly approved revisions.
4. Design controlled permission initialization and activation procedures, subject to governance approval.
5. Complete the registration-approval API release checks before connecting it to live Admin functions.
6. Develop the permission-aware Admin dashboard after the backend access rules are approved.
7. Verify end-to-end registration, approval, login, and dashboard behavior when activation is authorized.
8. Reconcile affected SRS, ERD, architecture, API, and testing documentation with the implemented code.

## 7. Outstanding Risks and Restrictions

- Catalogue initialization, role grants, service activation, and live access-control mutations remain blocked pending approval.
- Technical Super Admin and SSG Advisor remain deferred role implementations.
- The one-time Admin bootstrap must not be re-enabled for routine use.
- The inactive registration-review API must not be registered into the live URL configuration until the required authorization and governance controls are approved.
- Session revocation, authentication-event retention, recovery governance, and full object-level authorization policies require further review.
- Sensitive credentials, `.