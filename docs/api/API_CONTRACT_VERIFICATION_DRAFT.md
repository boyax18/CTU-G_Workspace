# CTU-G Workspace — API Contract Verification Matrix (Draft)

**Document ID:** CTUG-API-001 | **Date:** November 11, 2026  
**Status:** Read-only review worksheet; not an API activation approval.  
**Sources:** SRS v0.4; November 11 documentation audit; reported backend/frontend checkpoints. Actual paths, serializers, view permissions and response shapes must be checked against the **current checked-out source**, not inferred from UI or proposal files.

## 1. Core rules

- React uses Django **session cookies plus CSRF**, not client-stored JWT for the current web baseline. Sensitive mutations require authentication, CSRF, effective custom permission, resource scope and safe errors.
- A named role, requested role, React menu item, `is_staff` or `is_superuser` is **not** an automatic application API grant.
- A service being implemented or tested is **not** the same as its URL being connected or its feature flags enabled.
- Passwords, password hashes, reset tokens, session cookies, CSRF secrets, raw notification recipients and full security diagnostics must never appear in accessible data or examples.

## 2. Route verification inventory

The column "Observed in earlier project context" is a **clue for auditing**, not independently verified current route registration. Do not implement guessed paths.

| Workflow | Route evidence to inspect | Current gate/status from November 11 audit | Required server contract checks |
|---|---|---|---|
| CSRF bootstrap | Earlier proxy request: `/api/v1/auth/csrf/` | Browser auth implemented/tested; verify live path exists | Session/cookie configuration, safe method and origin checks |
| Login | Earlier log: `POST /api/v1/auth/login/` | Implemented/tested; verify method/serializer/response | Approved+active only, generic errors, rate limit policy, CSRF, session rotation |
| Logout | Path **not recorded in this worksheet** | Implemented/tested per SRS review | Authenticated session invalidation; safe CSRF, no stale app access |
| Current session/permissions | Exact route **to verify** | Frontend shell uses a session/permissions contract; catalogue still ungranted | Current identity, safe role display, exact effective-code hints, deny/service filtering, no false privileges |
| Public Student/Instructor registration | Exact route **to verify** | Implemented/tested | Allowed role request only, normalized input, Pending/inactive, no privilege fields |
| Forgot/reset password | SRS mentions `forgot-password/` and `reset-password/` suffixes; verify full path | **Disabled by default**, pending email/security approval | Anti-enumeration, expiry/single-use, CSRF, token redaction, safe session behavior |
| Individual registration review | Candidate views exist; exact prefixes **to verify** | **Detached** from live root routes | Session+CSRF, approved reviewer permission, scope, self-review denial, atomic audit |
| Immediate bulk selection (1–20) | Detached service/API; exact prefixes **to verify** | **Detached** from live route config | Per-item reauthorization/eligibility, bounded selection, explicit partial results |
| Large bulk durable queue (~200) | **No live route asserted** | Official DBML text only, no confirmed migration/worker | No API until schema/model/concurrency/security reviews approved |
| Django framework Admin | `/admin/` | Read-only registrations tested per audit | Reviewed model allowlist only; no custom Workspace bypass |
| Academic/finance/clearance/rating/announcements | Route set **not yet accepted here** | No live modules inferred from ERD or shell placeholders | Explicit permission + object/period scope and privacy contract per module |

## 3. Fill-in endpoint contract template

Use one completed record **per actually discovered endpoint**. Prefer generated OpenAPI/DRF schema if it reflects deployed route decorators and permissions; manually inspect code for non-documented routes and detached modules.

| Field | Required review result |
|---|---|
| Route + HTTP method | Exact live Django route from current root `urls.py` and included modules |
| Status | `connected`, `detached`, `feature-gated off`, `proposed`, or `removed` |
| Source | File:line for root URL -> view -> serializer/service |
| Roles and effective codes | **Exact** permission code, active service and eligible target rule, not a general role claim |
| Object scope | Self, assigned instructor class, selected school period or approved governance target |
| Authentication | Anonymous/session/framework admin; CSRF for mutations; origin/cookie rules |
| Request schema | Mandatory fields, limits, validation and forbidden client-controlled privilege fields |
| Success contract | JSON shape, status code, privacy/redaction and audit receipt where appropriate |
| Failure contract | `400/401/403/404/409/429` only where *implemented and documented*, with safe non-enumerating body |
| State effect | None/read-only versus transaction, rollback, idempotency, outbox |
| Feature gate and test | Specific flag default, test location, latest passing run ID |
| Release approval | Named approver, date, version; leave blank until approved |

## 4. Client/server integration checklist

1. Inspect Django root `urls.py` and each `include(...)` before classifying a route as live; a view existing in Python is insufficient.
2. Inspect `frontend/src` API client and Vite proxy target; proxy error `ECONNREFUSED 127.0.0.1:8000` means Django was not reachable, not necessarily a broken frontend endpoint.
3. Verify the session GET contract maps actual **effective grants** and service status. The sidebar may show only permitted modules; direct backend requests still require authorization.
4. Revalidate every decision/write API against simultaneous role union, direct Deny, target-owner scope, self-elevation prevention, stale session and expired/revoked permissions.
5. Record throttling, CSRF, preflight behavior, consistent error messages and audit state without sensitive payloads.
6. Use test fixtures and sandbox URLs for approved browser E2E only. **Do not attach detached registration review/bulk routes to live root URLs** through documentation review.

## 5. Known release blockers

Official catalogue/grant manifest and Admin delegation policies; registration-review scope and object-level authorization; safe live route activation decision; SMTP/outbox operational approval; password recovery enablement; two AR-6C5D queue DBML tables awaiting migration review; enterprise privacy/security approvals; campus user acceptance.

**Verification record:** Reviewer ____ | Source revision ____ | Route inventory hash ____ | Date ____ | Security reviewer ____ | Decision ____. No fields are pre-approved.
