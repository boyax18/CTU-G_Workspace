# CTU-G Workspace — Development Status

**As of:** 2026-11-08  
**Basis:** Shared local build/test outputs and read-only planner/preflight results. This document is not a live database audit.

## System in scope

- Frontend: React + TypeScript + Vite + Tailwind CSS; public landing page with embedded login and a preliminary shared dashboard route.
- Backend: Django + Django REST Framework, Django session authentication with CSRF protection.
- Database: MySQL database `ctug_workspace` in local development; isolated ephemeral MySQL databases for Django tests.
- Access model: application roles and permissions with hybrid dynamic access control. Framework Django Superuser is separate from application Admin and protected Technical Super Admin.

## Status by phase

| Phase | Verified result | Operational status |
| --- | --- | --- |
| Frontend public registration and session integration (AR-5B) | `npm run build` passed; `npm test` passed 25/25 | Built/tested; full browser end-to-end authorization still requires verification |
| Backend session authentication (AR-5A) | 14 session tests and 30 registration regression tests reported passing | Tested; production hardening/deployment not asserted |
| AR-6A1 registration review service | 17 isolated tests reported passing | Service implemented/tested; live approval endpoint/grants not activated |
| AR-6A2 initial Workspace Admin bootstrap | 15 isolated tests passed; read-only preflight succeeded | One Workspace Admin provisioned and audited in local DB; one-time bootstrap settings removed |
| Catalogue V2 planner | Read-only planner ran; no conflicts reported | **Not approved for activation** |
| AR-6B1 catalogue governance review | Planner findings gathered | **Current work** |
| AR-6B2 controlled permission activation | Not performed | Blocked pending governance review |
| AR-6C registration approval API | Not demonstrated | Pending |
| AR-6D permission-aware Admin dashboard | Not demonstrated | Pending |

## Last observed local database facts

These are historical observations, not continuously refreshed metrics.

- Bootstrap preflight after provisioning: one active `Admin` role assignment; one previous first-bootstrap audit event; one framework operator.
- Catalogue V2 planner: 10 proposed services, 95 proposed permissions, 106 proposed role bindings, 6 role definitions (4 existing role matches; 2 optional roles deferred), one retired tombstone.
- Planner classifications: `CREATE=105`, `MATCH=4`, `DEFER=108`, `CONFLICT=0`, `unexpected existing rows=0`.
- Planner was **read-only**; no DDL/DML, grants, service activation, or repair occurred.
- The Admin account was provisioned, but **services/permissions/default grants were not activated** by bootstrap.

## Key separation of states

- **Provisioned:** an account and Admin role assignment exist.
- **Defined:** a permission code/service is present as metadata.
- **Granted:** a role/account permission binding is explicitly authorized and active.
- **Enforced:** the backend checks effective permissions and object scope on each protected request.
- **Available:** a service is enabled and all dependent workflows are safe/ready.

These states are not interchangeable.

## Immediate next tasks

1. Review scoped account registration permissions and the V2 blocked governance decisions. Record approval evidence and object-level restrictions.
2. Decide whether to approve V2 as-is or produce a versioned, documented revision. **Do not silently edit the pinned proposal**.
3. Implement/review read-only and deny-path tests for catalogue activation and effective-permission evaluation before applying grants.
4. Build an authenticated registration-review API only after permission and scope policy is approved.
5. Integrate approved Admin workflow into the shared dashboard; verify it in a browser end to end.
6. Reconcile database DBML, architecture, SRS, and API docs with code/migrations.

## Risks and holds

- Catalogue planner explicitly labels initialization, grants, service activation, live mutations, first-operator governance evidence, object authorization, session revocation and other gates **blocked**.
- `Technical Super Admin` and `SSG Advisor` remain optional/deferred; bootstrap did **not** create or assign them.
- Do not re-enable the one-time bootstrap feature in routine settings or run `--apply` again.
- Local bootstrap operation produced a real dev account. Protect credentials; avoid publishing identifiers or logs containing personal information.

## Completion standard

A phase can be labeled **complete** only after code review, passing relevant tests, validated migrations/configuration if applicable, documented security impacts, updated SRS/ERD/API docs if affected, and a reviewed commit. Track any incomplete verification explicitly.
