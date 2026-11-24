# CTU-G Workspace — Development Status

**As of:** November 24, 2026
**Basis:** Current WF-02 source inspection and isolated verification below. Older phase records are historical evidence, not a continuous live database audit.

## 0. WF-02 dashboard integration — current checkpoint

- **Inspected/reconciled:** WF-02.01–06 already had implemented services, shared dashboard components, and historical local-development owner approvals. Normal settings exposed applicant reads behind a default-off switch; directory/detail/history and all decisions/status changes were isolated to review profiles. Existing role-context evaluation already lets a Technical Super Admin context inherit stored grants from its actual active Admin assignment; no new permissions or role-name bypass were needed.
- **Implemented:** normal application now mounts only read-only directory, account detail and minimized history alongside existing applicant list/detail. `WORKSPACE_ACCOUNT_DIRECTORY_ENABLED` and `VITE_WORKSPACE_ACCOUNT_DIRECTORY_ENABLED` are independent default-off read switches. Existing isolated status-read behavior is retained. The shared sidebar group is Account management. Backend detail responses report available actions; the UI requires those hints, its mutation build flags and exact session permission hints before displaying controls.
- **Retained:** pending search/category/proof/sort filters, account search/status filters, pagination, applicant details, empty/loading/error states, recorded status dates and minimized history. Approval requires mailbox proof plus institutional attestation; rejection queues encrypted delivery intent and deletes rejected registration data transactionally; status changes retain audit, protected-target checks and persistent session revocation. These mutations remain absent from normal routes and separately gated in isolated profiles.
- **Tests and limitations:** backend 250/250 plus status/outbox supplement 46/46, focused frontend 73/73, browser 62/62 plus read-build 3/3, changed-file lint and production build passed. Full frontend tests retain one existing inventory failure (237/238 pass); full lint retains three existing errors in unchanged WF-03 files. See the 23 November checkpoints in `testing/TEST_RESULTS.md` for exact commands, observed counts, failures and coverage. Those automated checks use synthetic/disposable MySQL data or mocked browser APIs. No real applicant records, live account changes, SMTP delivery or production deployment were used. A temporary loopback-only process activation is documented below; the persistent `.env` remains unchanged, and authenticated live record access is awaiting the account holder's sign-in.
- **Schema:** this task changes no model, migration, table, relationship or DBML file and applies no migration to `ctug_workspace`. Disposable test migrations are test setup only. Historical migration application evidence is not a fresh live schema audit; pending WF-03 schema work remains outside this task.
- **Approval:** preserve the catalogue's prior human approvals and Inspect → Reconcile → Approve → Implement → Test → Commit checklists. This integration records no new Human Approval and does not mark protected WF-03 functionality operational.
- **Git:** branch `ronald`, implementation parent `d9b58da`. Code, tests and these existing documentation records belong in the same local commit, identifiable with `git log -1 --format="%h %s" -- docs/DEVELOPMENT_STATUS.md`. No automatic push. Pre-existing settings/LAN helper/script/guide changes and the mkcert executable remain outside the staged scope.

### 0.1 Pre-activation local runtime inspection — 23 November 2026

- Read-only queries confirmed the configured MySQL database is `ctug_workspace`. It contains 3 eligible Pending Student applications and 1 eligible ordinary approved directory account; no personal fields were selected, logged, or recorded. The `accounts` and `access_control` services are active, both WF-02 read permissions exist, and active Admin grants are present. A read-only effective-permission check using stored role assignments returned both read permissions in Admin and Technical Super Admin selected contexts, and neither in Student or Instructor contexts. The Technical Super Admin assignment has an active Admin assignment. This validates current database grants, not an authenticated browser session.
- The running API returned 503 for both normal read routes. The backend list/directory/status and frontend list/directory/status build flags are unset/default-off. Approval, rejection, status writes, and outbox delivery remain unmounted or gated. No flag was enabled and no real-database mutation was attempted.
- The current Vite listener responds on a private LAN interface over plain HTTP, while `127.0.0.1:5173` is unavailable; the response had no transport-security headers. Therefore the read gates were deliberately left off to avoid exposing real applicant/account data to other devices. No live authenticated browser/API result is claimed.
- A fresh settings import in the inspection shell was refused by the existing uncommitted LAN role-context configuration: its LAN acknowledgement is set while `DJANGO_DEBUG` is unset/false. That configuration and all other pre-existing LAN/HTTPS work were left untouched. Inspection and isolated tests cleared those opt-ins only in their own process environments.
- Verification in this runtime: isolated WF-02 backend tests 86/86; focused frontend/browser tests 60/60; frontend build passed. An expanded frontend selector reproduced the existing navigation-catalogue mismatch (72/73; appointment permission absent from the frozen implemented catalogue). Details are in `testing/TEST_RESULTS.md`.
- This was the pre-activation checkpoint; the temporary localhost-only process activation below supersedes its runtime gate and listener observations.

### 0.2 Temporary localhost-only runtime activation — 23 November 2026

- Replaced the prior LAN-bound Vite and stale Django development processes with Django at `127.0.0.1:8000` and Vite at `127.0.0.1:5173`. Both listeners were verified loopback-only. Vite proxies `/api` to the local Django server.
- Resolved the conflicting LAN/local role-context settings only in the Django launch process: it loaded the existing local environment, cleared LAN/HTTPS role-context opt-ins in that process, and enabled the existing localhost-only role-context acknowledgement. No `.env`, source, or pre-existing LAN/HTTPS files were edited.
- Enabled only the backend applicant-list/directory read gates and matching Vite read flags for these processes. Account-status, approval, rejection, outbox, SMTP and protected executor writes remain off; live mutation routes returned 404.
- Smoke results through the actual browser origin: dashboard 200; CSRF endpoint 200; session endpoint 200 with `authenticated=false`; applicant and account-directory reads returned 401, proving their gates are open while authentication is still enforced. Vite-transformed modules confirmed applicant and directory flags true and decision/status flags false. The browser displayed the real sign-in screen; no applicant/account data was displayed.
- The database remains the configured MySQL `ctug_workspace`; no account changes, permission changes, migrations or other database writes were made. Source inspection and the preceding read-only database check confirm real eligible data and Admin/Technical Super Admin effective read grants. No authenticated list response has yet been obtained.
- **One user action remains:** sign in at `http://127.0.0.1:5173` with an existing approved account that has an active Admin or Technical Super Admin assignment. Then verify Applicant Reviews and Account Directory in that selected context. Credentials were not available to the assistant; the role-specific live browser result is therefore not claimed. The running process flags are temporary and revert to the unchanged `.env` defaults if these processes stop.

### 0.3 WF-02.03/02.04 durable notifications and bulk decisions — source checkpoint

- **Implemented:** Approval and rejection require the durable outbox, usable active encryption key and valid recipient. Each decision atomically records its audit evidence and one encrypted notification row with the account decision. Rejection's outbox item survives deletion of the registration account/profile. A `queued` response is not a delivery claim; the worker's `Pending`, `Leased`, `Retry`, `Delivered`, and `Dead` states remain authoritative.
- **Bulk UI/service:** Pending Applicants supports row checkboxes, Select All on Current Page, Clear Selection, count, action-specific confirmation, and per-applicant results. Requests use 1–20 unique explicit IDs and independent locked decisions. Permissions and target eligibility are rechecked per applicant; each committed decision has its own audit and notification. An uncertain result halts the batch and is not retried automatically.
- **Authorization and activation:** No role-name bypass or new permission was added. School Admin requires the exact effective action permission and active Admin assignment; Technical Super Admin relies on the same effective inherited Admin grant in its selected context. The bulk URLconf remains detached from normal application URLs and its backend/frontend switches default off. Approval/rejection remain unmounted from `config.urls`; decision, outbox-worker and SMTP activation were not enabled.
- **Verification:** 78/78 backend API/approval/bulk tests, 36/36 backend notification/outbox/review tests, and 6/6 dashboard action-availability integration tests passed on disposable MySQL databases; focused frontend tests 47/47 and applicant-review browser tests 22/22 passed; production build passed. These checks used synthetic data; no real records were mutated and no SMTP was sent. The historical read-only database observations remain separate in §0.1.
- **Release boundary:** This is source implementation and isolated test evidence, not live authenticated decision verification, local write activation, production readiness, or a new Human Approval. Previous workflow IDs and approval fields are unchanged. No real database mutation or migration was performed.

### 0.4 Isolated bulk route and current activation blockers — 24 November 2026

- Added `/api/v1/admin/registration-requests/bulk/` to the shared registration-review URLconf. It is included only by loopback local-review/decision-local profiles and the synthetic sandbox; normal `config.urls` and production remain unchanged. This is the narrow local-route scope requested by the owner after D-53; it does not change permission policy or mark WF-02.03/02.04 newly approved.
- Added `config.review_decision_local_settings` and its URLconf for this runtime: loopback-only, applicant decisions plus read-only dashboard routes, no account-status or WF-03 mutation routes. Normal `config.urls` remains unchanged.
- Focused evidence: isolated routing 11/11; bulk decision and release safeguard 50/50; frontend bulk/API contract 36/36. No test used `ctug_workspace` for writes.
- A read-only count against `ctug_workspace` found 4 eligible Pending applicants and 1 eligible ordinary directory account; the decision outbox has zero rows. No personal fields were selected. No valid active wrapping key was present in process, user, machine or project `.env` configuration, so the backend advertises no usable decision actions and approval/rejection refuse before mutation.
- Django and Vite are now running on `127.0.0.1:8000` and `127.0.0.1:5173`. Applicant-list, account-directory and bulk frontend switches are enabled in these local processes; bulk OPTIONS returns 200. The browser renders the sign-in page; session is unauthenticated, CSRF is 200, and applicant/directory APIs return 401 without a session. No authenticated School Admin/Technical Super Admin browser result is claimed.
- Account-status writes are disabled and absent from the decision-local URLconf. The profile uses locmem mail and SMTP off; the outbox worker and SMTP-delivery approval remain disabled. No SMTP authentication or delivery was attempted. No real account decisions, migrations, permission changes, secrets or SMTP messages were made; production readiness is not claimed.

### 0.10 Branded HTML email design — 24 November 2026

- **Implemented:** one shared design (`email_design.py`) for registration OTPs, password recovery and password-changed notices, and approval/rejection notifications, individual and bulk. It is an HTML + plain-text multipart message with the approved campus logo inline (CID), inline CSS, a responsive table layout and a large copyable OTP, and every dynamic value is escaped. Senders keep a drop-in `send_mail`. Django 6.1 no longer supports `mixed_subtype`, so the logo is added with the standard `add_related` on the HTML part. Business rules, OTP policy, outbox/encryption/audit and SMTP settings are unchanged.
- **Verified:**
  - New design tests 8/8.
  - Existing email-related suites 255/255: student/instructor OTP, password reset, outbox worker/erasure, approval, rejection, bulk, reapplication, release settings and local delivery, with the release-settings test now pinning the default posture and covering the opt-in.
  - Headless Edge renders at 680 px and 375 px: no horizontal overflow.
  - Six design previews (`[Design preview]`, sample data) accepted by Gmail SMTP for the approved test inbox only; inbox arrival is for the owner to confirm.
- **Real data:** `ctug_workspace` was not accessed for sending; applicant #11's notification remains `Pending`.

### 0.9 Local email delivery — 24 November 2026

- **State before this change:**
  - LAN mode already sent OTP mail through Gmail when `WORKSPACE_EMAIL_SMTP_ENABLED=1`.
  - `-Local` forced in-memory mail and turned password recovery off.
  - The outbox worker existed (lease, retry/backoff, dead-letter, recipient erasure) but was manual-only, and decision emails required an approved HTTPS link.
- **Implemented:**
  - An owner-approved opt-in in `config.review_local_settings` (`WORKSPACE_LOCAL_EMAIL_DELIVERY=1`) reuses the validated SMTP settings, restores password recovery per .env, and allows loopback http links in decision emails (DEBUG + local profile only).
  - `process_registration_outbox --deliver --watch` uses a start-time watermark, so historical queued rows are never sent automatically.
  - A registry feature makes `-Local` start and stop that watcher. The launcher handles background workers generically.
  - The three opt-in flags were added once to the git-ignored `backend/.env`. No other value changed and the outbox key was preserved.
- **Live verification** (disposable replica; all recipients +aliases of the approved inbox; Gmail SMTP acceptance counted in-process, no content logged):
  - Student OTP, Instructor OTP and password-reset OTP were accepted.
  - No account was created before OTP verification, and an unknown reset address was sent no email.
  - 1 approve + 1 reject (School Admin) and bulk 2 approve + 2 reject (Technical Super Admin context) produced 6 separate notifications. The real worker process delivered all 6 (`Delivered`, 1 attempt each, recipients erased).
  - A pre-existing queued row stayed `Pending` with 0 attempts.
  - Inbox arrival is for the owner to confirm.
- **Other checks:** focused tests 99/99, then 28/28 after final changes; registry/gate contracts pass.
- **Real data:** `ctug_workspace` is unchanged, and applicant #11's queued rejection remains `Pending` (owner decision: leave it queued).
- **Not verified:** the launcher starting the worker on ports 8000/5173 itself, because the owner's session occupied them and was left running. The worker command and the launcher's worker code path were verified separately.

### 0.8 Applicant Reviews automatic filtering — 24 November 2026

- **Changes:** Apply filters was removed. Search (debounced ~300 ms; Enter applies at once), Requested role, Email proof and Sort by now update the table automatically and together, through the unchanged server query and pagination (20 per page). Any change returns to page 1 and clears the selection. Responses superseded by a newer request are discarded. Previous rows stay dimmed and inert while loading, and errors replace them. Decision controls are unchanged.
- **Real browser** (real frontend and decision profile on a disposable replica with 28 pending applicants; dropped afterwards), 19/19:
  - One request for six typed characters; each dropdown and the sort applied at once.
  - Combined Janrey + Student + Email verified + newest-first query; CTU-G ID prefix search; cleared search restores results; filtered empty state; Clear filters.
  - Page 2 keeps filters; a filter change resets to page 1 and clears the selection.
  - Approve All on a filtered view decided exactly the shown rows; Technical Super Admin context works.
- **Other checks:** mocked browser 26/26; unit 47/47; lint and build pass. `ctug_workspace` unchanged.

### 0.7 Applicant Reviews selection and decision controls — 24 November 2026

- **Cause of the disabled buttons:** the owner was running LAN mode, whose `config.urls` mounts no decision route. The server therefore advertised no actions, but the page still drew a permanent, disabled bulk toolbar. Backend gates, outbox readiness and the `-Local` profile were already correct, and no backend change was made.
- **New queue layout:** Select | CTU-G ID | Name | Requested role | Submitted | Email proof | Status | Actions, plus a header select-all checkbox.
  - The toolbar appears only while applicants are selected: Approve/Reject (labelled Approve All/Reject All when every current-page row is selected), Select All on Current Page while rows remain unselected, and Unselect All.
  - One selection uses the existing individual endpoints (with the role's required eligibility source); 2–20 selections use the bulk endpoint. Every decision is confirmed first, with a destructive confirm for reject.
  - The results panel reports approved, rejected, skipped, failed and unconfirmed outcomes; queued is never shown as delivered, and nothing is retried automatically. The table refreshes after each decision.
  - Without decision availability, as in LAN mode, there are no checkboxes and the page says decisions are not available in this session.
- **Verified in a real browser** (headless Edge, real frontend and the real loopback decision profile, disposable replica of the `ctug_workspace` schema, dropped afterwards), 16/16:
  - Column order and hidden toolbar; School Admin individual approve and reject.
  - Technical Super Admin bulk approve in its default context without a switch, then Approve All/Reject All labels, Unselect All, and Reject All in the Technical Super Admin context.
  - The detail page no longer claims read-only when decisions are available; Student, Instructor and Treasurer see no controls and get 403.
- **Database effects:** one audit record and one encrypted `Pending` outbox row per decision (10/10 decrypt with the stored key; the address is absent from stored fields). Approved accounts are active with the requested role; rejected registrations and profiles are deleted, and the ID and email can register again.
- **Other checks:** mocked browser suites 25/25 (including 360–1440 px in Light, System-dark and Dark with AA contrast); related unit tests 47/47; changed-file lint and production build pass. `ctug_workspace` is unchanged and no existing applicant was decided.
- **Not done:** a sign-in at `http://127.0.0.1:5173` with the owner's own accounts. The owner's LAN launcher was running on those ports and was left untouched; the assistant has no credentials.

### 0.6 WF-02.03/02.04 decisions operational in `-Local` — 24 November 2026

- **Resolved blockers:** The only missing prerequisite was the outbox key encryption key. With 0 outbox rows and no key anywhere (process, user, machine, `.env`), a v1 key was generated once and stored in the git-ignored `backend/.env`, following the documented env-only development contract. `.\Start-CTUG-LAN.ps1 -Local` now reports all four WF-02 features ready. The existing loopback decision profile mounts approve, reject and bulk, approval/rejection notification readiness is true, and the frontend gets the decision build flags from `dev_features.py`. No application code, permission, role binding, migration or route policy changed. LAN mode still mounts no decision route.
- **Verified in a real browser** (headless Edge, real frontend and the real decision profile, on a disposable replica of the exact `ctug_workspace` schema with test accounts; dropped afterwards), 19/19:
  - School Admin individual approve and reject, each with its confirmation dialog; the approved account appears in the Account Directory.
  - Technical Super Admin Active Role switch, then Select All / Clear Selection and Bulk Approve / Bulk Reject with per-applicant results.
  - Disabled bulk buttons with no selection; Student, Instructor and Treasurer see no controls and get 403.
- **Database effects** (10/10): one audit record and one encrypted `Pending` outbox row per decision, all decrypting with the stored key; rejected registration and profile deleted, with the ID and email free to register again.
- **Focused tests:** 82/82 on disposable MySQL, and 83/83 with the `.env` key loaded.
- **Real-data safety:** the `-Local` app was probed only with requests that cannot write (decision routes 405 on GET, anonymous POST 403, status/governance routes 404, LAN address unreachable). `ctug_workspace` counts and checksums are identical to the baseline. The four existing pending applicants were not decided.
- **Launcher fix:** a second start no longer stops another running launcher's servers. Earlier today one `-Local` test start stopped the owner's running LAN session (no data change). The process record now names its owning launcher, so a running launcher causes a refusal and only a closed window's servers are cleaned up (verified).
- **Remaining:** SMTP delivery of queued notifications stays off (worker not started; queued ≠ delivered). `access_control` migrations 0004/0005 remain unapplied; the decision path does not use those tables. LAN-mode decisions would need a separately secured (HTTPS) mode.

### 0.5 One-command development startup on `ctug_workspace` — 24 November 2026

- **Current:** `Start-CTUG-LAN.ps1` starts Django and Vite on the normal development database (`ctug_workspace`, existing accounts). LAN mode (`config.settings` + the existing Option A gate for the detected Wi-Fi address) provides sign-in, Active Role switching, Pending Applicants and the Account Directory. `-Local` uses the existing loopback decision profile for individual/bulk decisions. Mode and feature selection live in `backend/config/dev_features.py`; the launcher is feature-agnostic. The preflight is read-only.
- **Removed:** the synthetic-database variant committed earlier the same day (`aee13ba`): the `ctug_lan_synthetic` profile, its initializer and seeding, the synthetic launcher requirements, and the Option A change that refused `ctug_workspace`. The Option A gate is back to its original form. The `ctug_lan_synthetic` schema and git-ignored `.local/ctug-lan/` files still exist pending the owner's explicit deletion decision; nothing uses them.
- **Preserved:** WF-01 authentication, registration/OTP and password recovery; WF-02 reads, individual/bulk decision services, durable encrypted outbox, status services; WF-03 role context, permission-based navigation, Technical Super Admin inheritance and protected Access Control Management. No application module was changed.
- **Verified:** `ctug_workspace` row counts and `CHECKSUM TABLE` for 11 account/access-control/outbox/migration tables were identical before and after the cleanup and a live LAN run. The running LAN app served the page, proxied the API and returned 401 for anonymous protected reads; decision routes were unmounted in LAN mode and Django was not reachable directly. Focused WF-01 68/68 and WF-02/WF-03 103/103 tests passed on disposable MySQL; registry and Option A contracts passed 43/43. Sign-in with the owner's existing accounts was not performed (no credentials used); see `testing/TEST_RESULTS.md`.
- **Blockers carried forward:** `access_control` migrations 0004/0005 are unapplied to `ctug_workspace` (reported, never applied). The outbox key gap was resolved in §0.6. Plain HTTP LAN carries real credentials, so use trusted networks only. Windows classifies the current Wi-Fi as Public.

The sections below retain the November 8 historical baseline. Their earlier inactive/deferred statements must be read with this checkpoint and the current workflow catalogue, including its later local-development approvals and protected WF-03 blockers. API contracts are in `api/AR-6C-registration-review-api-contract-proposal.md` §0; operational access and governance separation are in `security/ACCESS_CONTROL_GATES.md`.

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
