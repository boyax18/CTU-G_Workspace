# CTU-G Workspace — AR-6C Registration Review API Contract (Proposal)

**Prepared:** 2026-11-08
**Phase:** AR-6B1A contract design for future AR-6C implementation
**State:** DESIGN PROPOSAL — AR-6C1 candidate implemented and tested; not approved for live activation
**Scope:** The three proposed `accounts.registration_requests.*` permissions; no service/permission activation, grant, migration, or endpoint deployment in this phase.

## 1. Evidence and dependencies

- First Workspace Admin bootstrap succeeded and was audited. This does **not** imply catalogue authorization or permissions.
- AR-6A1 registration review service passed 17 isolated Django/MySQL tests. Its code explicitly defers HTTP-level security to a future API.
- V2 planner reported 10 services, 95 permissions, 106 proposed bindings; 105 CREATE, 4 MATCH, 108 DEFER and no conflicts; V2 is unapproved and planning-only.
- AR-6B1 static manifest check verified exact read/approve/reject definitions, proposed `Admin` binding, scope `SCHOOL`, and continued operational blocks.
- Existing Workspace auth uses Django sessions + CSRF; live endpoint wiring and browser authorization are **not** established by these results.

### Required effective permissions

| Operation | Exact code | Role name alone sufficient? |
| --- | --- | --- |
| List pending requests | `accounts.registration_requests.read` | **No** — check current effective grant on every request |
| Approve eligible request | `accounts.registration_requests.approve` | **No** — domain service rechecks grant and target rules inside its transaction |
| Reject eligible request | `accounts.registration_requests.reject` | **No** — domain service rechecks grant and target rules inside its transaction |

Permission checks must include approved/active actor, active assigned role, active services, role union, per-account Deny precedence, and no framework superuser shortcut. The caller's browser-provided roles/permission list is never authoritative.

## 2. Proposed HTTP surface — not yet registered

Final routes and shape require owner agreement and inspection of the existing `urls.py` and DRF parsers. The following are **candidates**, not a declaration of existing APIs.

| Method and candidate path | Intended result |
| --- | --- |
| `GET /api/v1/registration-requests/?status=Pending` | Paginated, minimized, eligible requests after explicit `read` permission check |
| `POST /api/v1/registration-requests/{account_id}/approve/` | Approve one eligible Pending Student/Instructor with body `{}` only |
| `POST /api/v1/registration-requests/{account_id}/reject/` | Reject one eligible request with body `{"rejection_code":"incomplete_submission"}` (example allowlisted code) |

The service's actual allowlist is `incomplete_submission`, `ineligible_registration`, `identity_mismatch`, `duplicate_request`. Do not accept unrestricted free-text reasons at this endpoint. Reject unknown JSON fields and malformed IDs. Never put passwords, reset tokens, hashes, cookies, or hidden admin flags in the response.

For pending-request list, initial candidate fields are `account_id`, `school_id`, `requested_role`, `created_at`, `first_name`, and `last_name` where permitted. Final field policy and records visible must be explicitly approved; presence of a field in the model does not justify returning it. The current schema does not establish a separate campus/tenancy object model; do not invent campus ID filtering as though it were implemented. If future multitenancy is required, block release until it is designed.

## 3. Mandatory HTTP enforcement

1. Feature flag remains **OFF by default** until all relevant policy, catalogue, and service readiness gates are approved. Disabled endpoint responds with a safe `503` (or is absent), never a partial write.
2. Confirm a current Django session identity server-side. If a DRF `APIView` sets `authentication_classes=[]`, `request.user` can be anonymous even when the underlying Django session exists; use an explicit, reviewed session-resolution design rather than trusting frontend headers or claimed role values.
3. Apply explicit CSRF protection to **every unsafe method**, including anonymous attempts, because DRF `APIView` is exempt from Django's ordinary CSRF middleware by default and session authentication's conditional CSRF path may not cover every situation. Enforce origin/referer where relevant; use `HttpOnly`, `SameSite`, and Secure cookies appropriately in deployment.
4. Require fresh effective permission for listing and each mutation; do not cache grants in the session, local storage, or a frontend role label. A direct `Deny` must block permission despite Admin membership.
5. List/detail scope: only Pending, inactive, role-requesting Student/Instructor records eligible for review, excluding staff/superusers, previously reviewed or already role-assigned targets. Minimize visible profile fields, paginate, filter on the server, and do not enable arbitrary query fields.
6. The mutation service must use its trusted atomic audit path and enforce non-self-review, one final decision, and base-role-only assignment. Do not wrap its existing `transaction.atomic(durable=True)` inside an outer atomic transaction without revisiting its transaction contract.
7. Limit request size and JSON type, require exact payload allowlists, throttle by appropriate actor and client IP, prevent speculative target-ID enumeration, and set `Cache-Control: no-store` on sensitive responses.
8. Errors must not reveal another person's account or whether an inaccessible target exists. Candidate response classes: `400` invalid input, `401` unauthenticated, `403` unauthorized/CSRF, `404` inaccessible target, `409` stale/already decided, `429` throttled, `503` review unavailable. Exact mapping is **to be finalized and tested**, not assumed existing behavior.
9. Audit important decisions, failed attempts as policy permits, and permission/role revocations without logging secrets. The exact auth-event retention source and step-up/revocation policy remain governance blockers.
10. The Django `/admin/` site, framework Superuser, first Admin bootstrap, catalogue initialization, grant editing, and protected-role changes are separate surfaces and never aliases of the registration review API.

## 4. Release prerequisites / owner decisions

- [ ] Registration scope and allowed list fields accepted by designated system/data owner.
- [ ] Exact APIs, request/response schemas, and error codes accepted.
- [ ] V2 proposal decision and **separate versioned minimal activation profile** explicitly approved; published digest and authority recorded. Do not edit pinned V2 silently.
- [ ] Independent review/attribution and audit contract accepted; associated V2 gates explicitly closed where applicable.
- [ ] Required `accounts` and `access_control` services, three permission definitions and three approved Admin bindings exist and are active through an audited activation procedure.
- [ ] CSRF/session, role/Deny precedence, object policy, throttling, concurrency, replay, rollback, and negative tests pass on isolated MySQL.
- [ ] `docs/DEVELOPMENT_STATUS.md`, `docs/testing/TEST_RESULTS.md`, `docs/security/ACCESS_CONTROL_GATES.md`, and endpoint inventory updated with evidence; no claim that proposal equals deployed API.

**Do not activate grants, services, review feature flags or endpoints based on this proposed contract alone.**
