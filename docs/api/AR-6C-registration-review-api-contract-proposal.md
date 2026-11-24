# CTU-G Workspace — Account Management API Contract and Historical Proposal

## 0. Verified WF-02 implementation — 24 November 2026

This section supersedes the historical candidate routes and payloads in §§1–5 below. Source: `config/urls.py`, the isolated review URLconfs, `registration_review_api.py`, `account_status_api.py`, their services, and the test evidence in `../testing/TEST_RESULTS.md`. Route presence is not activation or release approval. No live account mutations or provisioning were performed for this integration.

### Availability and authorization

All paths below begin with `/api/v1/admin/`. Reads support GET/HEAD/OPTIONS; HEAD has no response body. The normal URLconf mounts only the five read routes. Default-off `WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED` enables applicant list/detail; default-off `WORKSPACE_ACCOUNT_DIRECTORY_ENABLED` independently enables directory/detail/history. The existing `WORKSPACE_ACCOUNT_STATUS_ENABLED` also enables school-account reads in isolated review profiles. These switches do not provision permissions or activate services.

Every data request resolves the authenticated Django Workspace session, checks an Approved/active non-framework account with an active stored Admin assignment, requires both `accounts` and `access_control` services active, and evaluates the exact permission in the current server role context. Technical Super Admin inherits only its actually assigned Admin role's stored grants. Student/Instructor contexts cannot use these operations; account Deny takes precedence. Role names, client permission hints and framework superuser flags do not authorize a request.

| Method | Path after `/api/v1/admin/` | Required exact permission | Normal application | Isolated review profiles |
| --- | --- | --- | --- | --- |
| GET | `registration-requests/` | `accounts.registration_requests.read` | Mounted, read gate default off | Existing decision gate pair also opens reads |
| GET | `registration-requests/{id}/` | Same read permission | Mounted, same read gate | Same eligibility as list |
| POST | `registration-requests/{id}/approve/` | `accounts.registration_requests.approve` | Unmounted (404) | Review API + approval gates; locked service checks |
| POST | `registration-requests/{id}/reject/` | `accounts.registration_requests.reject` | Unmounted (404) | Same gate pair; durable outbox + v2 template required |
| POST | `registration-requests/bulk/` | Exact approve or reject permission, per item | Unmounted (404) | Bulk gate; per-item locked checks, audit and durable outbox |
| GET | `school-accounts/` | `accounts.school_accounts.read` | Mounted, directory gate default off | Existing status gate also opens reads |
| GET | `school-accounts/{id}/` | Same school-account read permission | Mounted, same directory gate | Same target exclusions |
| GET | `school-accounts/{id}/history/` | Same school-account read permission | Mounted, same directory gate | Minimized history only |
| POST | `school-accounts/{id}/suspend/` | `accounts.school_accounts.suspend` | Unmounted (404) | Separate status gate; protected executor refusal |
| POST | `school-accounts/{id}/activate/` | `accounts.school_accounts.activate` | Unmounted (404) | Separate status gate; protected executor refusal |

Local review requires its explicit acknowledgement and loopback restriction; sandbox uses synthetic data. Mounting the full isolated URLconfs in the normal application is prohibited. The provisioning guard accepts only the five exact read classes/paths/names without overrides or write handlers, refuses duplicates/unexpected mounts, and requires both normal read switches off before provisioning. No shared-HTTP/LAN real-data activation is authorized here.

### Read contracts

All list responses use `{ "results": [], "page": 1, "page_size": 20, "has_next": false }`. There is no total count. Pages are 1–10000; unsupported/repeated query fields are rejected. `q` is printable ASCII, at most 50 characters and five whitespace-separated terms: each term matches an ID prefix or a name substring. Omit blank `q`.

- **Pending list:** optional `status=Pending`, `role=Student|Instructor`, `proof=verified|legacy`, `sort=submitted|-submitted|school_id|-school_id` (default `submitted`), `page`, `q`. Results contain exactly `account_id` (integer), `school_id` (string), `full_name` (string/null), `requested_role` (Student/Instructor), `created_at` (ISO timestamp), `email_verified` (boolean). Pending status is implicit in this endpoint. Eligible rows are Pending/inactive with an active requested Student/Instructor role, no assigned roles or reviewer fields, no framework privileges, excluding the viewer. Missing/stale email proof remains visible as unverified; approval independently requires current-address proof.
- **Applicant detail:** no query parameters. Fields: `account_id`, `school_id`, `id_label` (`CTU-G ID`), `name` (`first`, `middle`, `last`, `suffix`, each string/null), `full_name`, `email` (string/null, detail only), `requested_role`, `request_status` (`Pending`), `created_at`, `email_evidence` (`state`, `verified_at`), `institutional_check` (`subject`, `verified_by_workspace=false`), `data_notes` (array). Evidence states are `verified`, `no_email`, `no_proof`, `address_changed`; only verified has a timestamp. Institutional subject is `enrollment` or `employment`; mailbox proof never establishes institutional eligibility. Notes are limited to missing profile/first name/last name indicators.
- **Directory:** optional `page`, `q`, `status=active|inactive`. Results contain exactly `account_id`, `school_id`, `id_label`, `full_name`, `roles` (active role-name strings), `is_active` (boolean). Only Approved non-framework accounts without any reserved administrator/governance assignment are eligible; the viewer is excluded. Pending/Rejected accounts and protected administrators are excluded. No broader Technical Super Admin inventory is supplied.
- **School-account detail:** no query parameters. Directory item fields plus `name`, `request_status=Approved`, `created_at`, `can_reactivate` (active-role hint only), `approved_at` (ISO timestamp/null), `last_status_change` (history entry/null). Approval date comes from the approval audit time, falling back to recorded `reviewed_at`; missing dates are null, never inferred. Current active state comes from the account row.
- **History:** only optional `page`. Same target eligibility and envelope as directory. Entries contain `event`, `description`, `occurred_at` (ISO timestamp), `actor` (`You` or `An administrator`). Allowed event/description pairs: `registration_approved`/`Registration approved`, `account_deactivated`/`Account deactivated`, `account_reactivated`/`Account reactivated`. Status events also contain `previous_is_active`, `new_is_active` (booleans, or both null if the stored transition is invalid). Newest audit primary key first. No raw JSON, reasons, attestations, actor identities/IDs or governance audit events are exposed.

Successful applicant/account detail responses include `X-Workspace-Available-Actions`, a comma-separated subset of `approve,reject` or `suspend,activate`; the pending-list response may additionally advertise `bulk-approve,bulk-reject` when the detached bulk route is mounted in its review URLconf. An empty/missing/invalid header means no actions may be advertised. Hints require mounted exact mutation classes, enabled backend gates, effective permissions and no protected executor. Approval/rejection hints also require the enabled outbox and valid active encryption-key configuration (rejection additionally requires the v2 template). Hints do not certify every target-specific recipient or state prerequisite; services recheck inside transactions. This header adds no JSON fields. The frontend retains separate default-off mutation build flags and exact permission checks.

### Mutation contracts — protected, not normal application routes

Approval body: `{ "eligibility_confirmed": true, "eligibility_source": "ctu_main_system_records" }` for Student, or `institutional_employment_records` for Instructor. Only these two keys are accepted. The service requires current email ownership proof, eligible Pending state, a matching positive institutional attestation, and a configured durable outbox recipient. Success: `{ "account_id": 123, "status": "Approved", "notification": "queued" }`. The encrypted approval notification is committed atomically with the decision and audit. `queued` is not a delivery receipt. Only the requested Student/Instructor base role is assigned; a later directory read includes the eligible approved account.

Rejection body: `{ "rejection_code": "identity_mismatch" }`. Allowed codes: `incomplete_submission`, `ineligible_registration`, `identity_mismatch`, `duplicate_request`. Success: `{ "account_id": 123, "status": "Rejected", "notification": "queued" }`. The transaction queues the encrypted notification snapshot, preserves minimized audit evidence, and deletes rejected registration/account/profile data according to the service's dependency checks. Queueing is not email delivery. Failure rolls back the decision/deletion; stale/deleted targets are unavailable. The ID/email may be reused through normal registration where policy permits; there is no rejected-account reactivation or previous-identity field. Local review suppresses external SMTP and uses locmem mail.

Suspend body: `{ "expected_active": true }`; activate body: `{ "expected_active": false }`. Exactly one boolean field is accepted. Success: `{ "account_id": 123, "is_active": false }` (or true for activation). The locked service checks the expected state, target eligibility, permissions and protected-account restrictions, changes active status, advances the persistent session-revocation counter, and records the audit event atomically. Reactivation requires an existing active role and never restores old sessions. Approval, identity, roles and permissions are not edited here. Protected-executor status writes remain refused.

### Bulk applicant decisions — implemented; isolated route mounted, still gated

The bounded bulk service and UI are implemented. `/bulk/` is part of `apps.accounts.registration_review_urls`, included only by the loopback-only `config.review_local_urls`, the narrower `config.review_decision_local_urls`, and synthetic `config.review_sandbox_urls`. The decision-local profile mounts no account-status or WF-03 mutation routes. Bulk remains absent from normal `config.urls` and production configuration. The backend `WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED` and frontend `VITE_WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED` switches default off. In the inspected local environment the active outbox wrapping key is absent, so approval/rejection actions are not advertised and the services fail closed before writes. Local review suppresses external SMTP; delivery requires the separately gated, approved worker.

The request is an explicit snapshot, never a filter or `select_all` instruction:

- Approve: `{ "action": "approve", "account_ids": [123, 124], "eligibility_confirmed": true }`. IDs must be unique integers; batch size is 1–20. The server verifies each account and derives the applicable fixed eligibility source from its requested role while locked. The reviewer affirmation applies to every selected applicant.
- Reject: `{ "action": "reject", "account_ids": [123, 124], "rejection_code": "identity_mismatch" }`. The rejection code is one of the individual workflow's fixed allowlisted values and applies to each selected applicant.

The endpoint validates the complete request before processing, then independently rechecks session authority, exact action permission, active services and each target using the existing locked single-applicant service. For approval, the reviewer explicitly confirms eligibility for every selected applicant; the service derives the fixed D-45 source from each locked requested role and records the attestation in that applicant's audit. Every committed item has its own transaction, audit record and encrypted notification row. The response includes aggregate counts and per-ID `Approved`, `Rejected`, `Skipped`, `Failed` or `Unconfirmed` outcomes; notification status `queued` is not delivery confirmation. A permission/service change stops the batch. An infrastructure/commit-acknowledgement uncertainty is reported as `Unconfirmed`, stops further work and must not be automatically retried. Duplicate IDs in a request are rejected; already-decided accounts are not processed again.

The dashboard offers row checkboxes, Select All on Current Page, Clear Selection, count, action-specific confirmation and a result summary. It refreshes after confirmed outcomes and does not replay a request whose outcome is uncertain. Bulk decisions are not available to mobile clients; the future-client authentication constraints below still apply. Route resolution and automated tests do not prove live authenticated access or production authorization.

### Authentication, errors and future mobile clients

Use the existing session contract: GET `/api/v1/auth/csrf/` to initialize CSRF, POST `/api/v1/auth/login/`, GET `/api/v1/auth/session/`, POST `/api/v1/auth/role-context/` only where its independent gate permits, POST `/api/v1/auth/logout/`. Send session cookies and `Accept: application/json`; unsafe requests require JSON, the CSRF cookie and `X-CSRFToken`, and valid origin/referer under configured policy. No bearer-token/mobile-specific authentication endpoint has been implemented. A future mobile client needs a session cookie jar and CSRF lifecycle over approved HTTPS, must consume server role-context/permission state, and must not combine grants or infer authorization from role labels.

Responses use `Cache-Control: no-store` and an opaque `X-Request-ID`; never persist applicant/account responses in browser or mobile storage. Read throttle: 60/minute per authenticated account (anonymous fallback: socket address); mutation throttle: 20/minute per socket address. Reads are not automatically retried by the clients; writes must never be blindly replayed after a timeout. Re-read status after an uncertain result.

Errors use `{ "error": { "code": "...", "message": "..." } }`, with a fixed `reason` only for policy conflicts. The following applies to mounted WF-02 views; unmounted routes return routing-level 404 and must not be assumed to have a JSON envelope.

| HTTP | Code / meaning |
| --- | --- |
| 400 | `invalid_request`: unsupported query, invalid value, unexpected JSON fields or malformed body |
| 401 | `authentication_required`: no eligible authenticated Workspace session |
| 403 | `access_denied`: exact permission, active Admin assignment, role-context or CSRF denial |
| 404 | `request_unavailable`: missing, stale or inaccessible target, intentionally indistinguishable |
| 405 / 406 / 415 | `method_not_allowed` / `not_acceptable` / `unsupported_media_type` |
| 409 | `approval_not_allowed`: `email_unverified` or `eligibility_unconfirmed`; `rejection_not_allowed`: `recipient_unverified`, `direct_permissions`, `protected_history`; `account_status_conflict`: `state_changed`, `protected_account`, `no_operational_role` |
| 429 | `rate_limited` |
| 503 | `review_unavailable`: gate off, inactive required service, database outage, unavailable notification/writer prerequisites; unexpected exceptions use the inherited safe `auth_unavailable` response |

Passwords/hashes, OTPs, reset tokens, credentials and private audit details are never part of these contracts. Protected WF-03 governance routes, provisioning and schema activation remain separate.

## Historical proposal (8 November 2026; retained for traceability)

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
