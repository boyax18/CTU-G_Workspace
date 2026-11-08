# CTU-G Workspace — Development Status

**As of:** November 8, 2026
**Basis:** Previously verified local build/test outputs, read-only planner/preflight evidence, an offline AR-6C3 source review, and the project owner's November 8 local SHA-256 checks. This document is not a continuous live database audit.

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
| AR-6C3 — API Integration Readiness Assessment | Source-based assessment documented; ADR-003 approved and both local ERD hashes matched | Assessment recorded; scope, catalogue, routing, security, UI and E2E gates remain blocked |
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

**Operational restriction:** The API remains disconnected from the live root URL configuration. Its feature gates remain disabled, and no live permission activation has been approved. AR-6C3 was a source-based readiness assessment, not a new Django/MySQL test run or an authorization to connect these endpoints.

## 5. Security and Authorization Rules

The following distinctions must remain separate:

- **Provisioned:** An account and its role assignment exist.
- **Defined:** Permission codes and service metadata exist.
- **Granted:** An authorized active permission binding exists.
- **Enforced:** Django validates effective permissions and applicable object scope.
- **Available:** The service and its dependent workflows have been approved and activated.

A Workspace Admin role assignment alone does not grant access to protected features.

Django Superuser credentials must not automatically authorize Workspace application actions. The owner-approved `accounts.is_staff` and `accounts.is_superuser` fields are Django framework flags, not automatic grants in the custom Workspace permission evaluator (ADR-003).

## 6. Immediate Next Tasks

1. Obtain an explicit decision on the proposed `SCHOOL` registration-review scope, eligible targets, minimized response fields, and the three proposed permissions; these are **not approved** by ADR-003.
2. Approve the versioned registration-review API contract and complete remaining AR-6C3 release-gate evidence. Keep both feature flags and live review routes disabled.
3. Review the pinned V2 catalogue and design narrow, audited initialization, grants, service activation and rollback; perform none without separate authorization.
4. Recheck the updated read-only ERD verifier in the intended local environment, with its database safeguards; the two local DBML hashes have already been verified.
5. Verify session revocation, object-level authorization, replay/concurrency, audit consistency, and recovery rules before any live rollout.
6. Implement the permission-aware Admin registration management interface only after backend release requirements are approved.
7. When activation is authorized, verify the complete registration → Admin review → login → dashboard → logout workflow in an isolated test environment.
8. Reconcile affected SRS, ERD, architecture, API, security, and testing documentation with actual evidence.
9. Review and commit outstanding source-code changes separately; exclude `.env`, local databases, personal data, and generated files.

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

**Current development checkpoint:** AR-6C2 routing safety and API regression tests historically verified (25/25). AR-6C3 source-based readiness assessment recorded. Option A framework flags approved via ADR-003; both protected ERD SHA-256 hashes were subsequently verified by the owner on the local Windows workspace. No Django/MySQL tests or live API activation were performed for this documentation update; controlled verifier execution and remaining release gates are still pending.

## 9. Approved Framework-Flag ERD Reconciliation (ADR-003)

On November 8, 2026, the project owner approved adopting the existing `accounts.is_staff` and `accounts.is_superuser` boolean columns (each defaulting to `false`) in both protected DBML contracts. They already appear in the Django `Account` model and existing migration `accounts.0002`. No additional ERD edits, migrations, roles, grants, or feature activations were authorized.

| Protected ERD file | Approved SHA-256 | Local Windows check (November 8, 2026) |
|---|---|---|
| `docs/database/full_schema.dbml` | `e4362be913280ab6c23d5c66af249fc1923fccb1acd7b6c2696f7ee95c19d4a0` | Match confirmed |
| `docs/database/schema.dbml` | `3bc2060ae35fce16725d6ca5b90272e819039b8dce855ffe305b654140f77313` | Match confirmed |

**Verification boundary:** The local `Get-FileHash` checks verified the actual DBML file bytes. The updated verifier's Python syntax was checked against the prepared patch, but executing the full read-only Django/MySQL integrity verifier on the owner's Windows environment remains pending. Do not interpret this decision as an approval of registration-review permissions, grants, service activation, or live routes.

See `docs/decisions/ADR-003-django-framework-account-flags.md`, `docs/implementation/access-control/erd-fingerprint-provenance-2026-11-08.md`, and `docs/implementation/authentication/ar-6c3-integration-readiness-assessment.md`.
