# Test Results and Evidence — CTU-G Workspace

**As of:** November 24, 2026
**Evidence source:** Current runtime inspection and isolated WF-02 verification below; earlier sections retain their dated historical evidence. Results must be revalidated whenever relevant code, schema, or configuration changes.

## 24 November 2026 — branded HTML email design

| Check | Result |
| --- | --- |
| Design tests (`test_email_design`) | 8/8: OTP as one unbroken selectable run (38 px), never in href/src or preheader, expiry shown; plain-text wording kept (test regexes unchanged); recovery emails have no links; escaping of name/reason/URL; no scripts, fonts or remote resources, viewport meta + 600 px card + media query; approval/rejection content and links; MIME `alternative(text/plain, related(text/html, image/png cid=<ctug-logo> inline))`; plain messages stay single-part |
| Regression (disposable MySQL) | 255/255 across student/instructor OTP, password reset, outbox worker, decision notifications, WF-02.04 rejection/outbox erasure/release settings, WF-02.03 approval, reapplication, local delivery, bulk, audit corrections, public API errors |
| Rendering | Headless Edge, 6 templates at 680 px and 375 px: all fit, no horizontal overflow |
| Live SMTP | 6 `[Design preview]` messages (Student OTP, Instructor OTP, reset OTP, approved, rejected, password changed) ACCEPTED by Gmail SMTP for `juls16125+design-*` aliases only; no database records used |
| Real data | Applicant #11 notification `Pending`, 0 attempts |

## 24 November 2026 — local email delivery (live Gmail SMTP)

| Check | Result |
| --- | --- |
| SMTP settings (`-Local` + opt-in) | `smtp.gmail.com:587`, TLS on, username/App Password present; password recovery enabled; outbox + v2 template on; worker gates pass; decision link `http://localhost:5173/`. Without opt-in: locmem, reset off (unchanged) |
| Registration OTP | Student and Instructor: HTTP 202, Gmail SMTP accepted 1 message each; no Account before verification |
| Password recovery OTP | Neutral 202; Gmail SMTP accepted 1 message, sent on the background thread by design; unknown address: same 202 and no message |
| Decisions to notifications | Approve, reject (registration deleted), bulk approve 2 and bulk reject 2 (Technical Super Admin context): 6 separate outbox rows (3 approved, 3 rejected) |
| Outbox worker (real `--watch 5` process) | `delivered=6, retry=0, dead=0`; every row `Delivered` after 1 attempt; encrypted recipients erased; pre-existing queued row left `Pending`/0 attempts ("1 earlier queued notification(s) are left for a manual --deliver") |
| Safety | Every message checked to be addressed to the approved inbox (+aliases) before sending; no codes, bodies or credentials printed; anonymous decision refused; replica dropped |
| Automated (disposable MySQL, locmem) | 99/99 across `test_local_email_delivery` (watermark, held-back rows, watch fail-closed, dev-link rules), outbox worker, notifications, bulk, password reset and instructor OTP; 28/28 re-run after final edits; registry/gate contracts OK |
| Real data | `ctug_workspace` fingerprint unchanged; applicant #11 rejection notification `Pending`, 0 attempts |
| Inbox arrival | Not observable by the assistant; for the owner to confirm in the approved inbox (9 messages expected) |

## 24 November 2026 — Applicant Reviews automatic filtering

| Check | Result |
| --- | --- |
| Real browser (headless Edge, real frontend + real loopback decision profile, disposable replica, 28 pending incl. three "Janrey" across role/proof) | 19/19: no Apply button; typing "Janrey" (6 keys) sent 1 request `?page=1&status=Pending&q=Janrey`; role, email proof (verified and no-proof) and sort applied immediately; combined `q=Janrey&role=Student&sort=-submitted` ordered newest first; ID prefix search; clearing search restores 20 Students newest first; no-match empty state; Clear filters; page 2 keeps filters; filter change returns to page 1 and clears selection; Approve All on a filtered view approved exactly the 2 rows shown with filters kept; Technical Super Admin context filtering and controls. Replica dropped |
| Mocked browser | `pending-applications-errors` + `applicant-approval-errors`: 26/26 (debounced single request, immediate dropdowns, combined query, Enter, cleared search, invalid text without request, empty states, page reset, keyboard, responsive/AA) |
| Unit / lint / build | 47/47; ESLint on changed files clean; build passed |
| Real data | `ctug_workspace` fingerprint identical to baseline |

## 24 November 2026 — Applicant Reviews selection and decision controls

| Check | Result |
| --- | --- |
| Runtime cause | Owner's session was LAN mode (`config.settings`): list response advertises no actions; decision routes unmounted (by design). `-Local` profile readiness unchanged and correct |
| Real browser (headless Edge, real frontend, real `review_decision_local_settings`, disposable replica of `ctug_workspace` schema, 15 test accounts, 10 pending) | 16/16: header order `[select]` CTU-G ID, Name, Requested role, Submitted, Email proof, Status, Actions; toolbar hidden with no selection; one selection shows Approve, Reject, Select All on Current Page and Unselect All; individual approve (confirm, result, row removed) and reject (School Admin); "queued; delivery not confirmed" wording; detail page not "read-only" with decisions available; 2 selected keep Approve/Reject; TSA bulk approve 2 in default context; all rows selected show Approve All/Reject All and hide Select All; Unselect All hides toolbar; Reject All of 6 in TSA context empties the list; Student/Instructor/Treasurer no controls, API 403 |
| Replica database | 3 approved (active, Student role, reviewer); 7 rejected and deleted with profiles; 10 outbox rows (3 approved, 7 rejected) `Pending`, none delivered, key v1, plaintext address absent, 10/10 decrypt; one audit per decision; rejected ID/email re-creatable. Replica dropped |
| Mocked browser | `applicant-approval-errors` + `pending-applications-errors`: 25/25, including new single-approval (individual endpoint body), uncertain-single (unconfirmed, one POST), All-label and hidden-toolbar tests, responsive/AA checks |
| Unit | `registration-review-bulk`, `registration-review-approval`, `registration-review-api-contract`: 47/47 |
| Lint / build | ESLint on changed files clean; `npm run build` passed |
| Real data | `ctug_workspace` counts + `CHECKSUM TABLE` identical to baseline; no existing applicant decided |
| Not performed | Owner sign-in at `127.0.0.1:5173` (owner's LAN launcher was running; credentials not used) |

## 24 November 2026 — WF-02 decisions in `-Local` mode

| Check | Result |
| --- | --- |
| Prerequisites (read-only) | `ctug_workspace`: approve/reject permissions bound to Admin, both services active, 0 outbox rows, no key in process/user/machine/.env. After provisioning: key decodes to 32 bytes; decision gates open; approval/rejection notification ready; approve/reject/bulk resolve to their views; executor off; status writes off; mail locmem |
| Real browser (headless Edge, real frontend + real `review_decision_local_settings`, disposable replica of the exact `ctug_workspace` schema, 13 test accounts) | 19/19: bulk buttons shown and disabled with no selection; School Admin sees Approve and Reject; approve confirmation dialog then success, applicant leaves Pending and appears in Account Directory; reject confirmation then "rejection email has been queued", applicant leaves Pending; Technical Super Admin role switch; Select All on Current Page; Clear Selection; Bulk Approve 2 and Bulk Reject 2 with result summaries and list refresh; Student/Instructor/Treasurer no controls, API 403 |
| Replica database effects | 10/10: approved accounts Approved/active with Student role and reviewer; rejected accounts and profiles deleted; 6 outbox rows (3 approved, 3 rejected), all `Pending`, none delivered, key v1, no plaintext address; 6/6 decrypt with the stored key; one audit row per decision; rejected ID and email re-creatable; untouched applicants intact. Replica dropped |
| Real `-Local` app on `ctug_workspace` (no sign-in) | Ready 4/4 features; anonymous reads 401; approve/reject/bulk GET 405 (mounted); anonymous POST 403; suspend and role-assignments 404; LAN address unreachable; decision build flags `1` |
| Focused tests (disposable MySQL) | `test_wf0203_approval`, `test_registration_bulk`, `test_wf02_dashboard_integration`, `test_registration_review_notifications`, `test_registration_review_routing`: 82/82; with `.env` key loaded and `test_registration_outbox`: 83/83; launcher/Option A contracts OK |
| Launcher ownership | Second start while a launcher runs: refused, listeners unchanged (2→2). Owner window killed: next start stopped the 2 recorded server trees, record removed |
| Real data | `ctug_workspace` counts + `CHECKSUM TABLE` (11 tables) identical before/after; the four existing applicants not decided |
| Not performed | Decisions by the owner on real applicants (owner's choice in the app); SMTP delivery |

## 24 November 2026 — synthetic setup removal and `ctug_workspace` startup

| Check | Result |
| --- | --- |
| Database integrity | Read-only `COUNT(*)` + `CHECKSUM TABLE` on `accounts`, `roles`, `account_roles`, `services`, `permissions`, `role_permissions`, `account_permissions`, `access_audit_logs`, `registration_notification_outbox`, `django_migrations`: identical before cleanup and after a live LAN run (8 accounts, 4 pending applicants) |
| Settings | `config.settings` (LAN/Option A) and `config.review_decision_local_settings` (`-Local`) both load; preflight confirms the connected schema is `ctug_workspace`; role context enabled in both |
| Launcher | `-CheckOnly` passes in both modes; LAN run on `http://192.168.100.46:5173` printed Running only after page 200, proxied session, anonymous 401 and direct-Django refusal |
| Live read-only probes | Page 200; CSRF 200; session `authenticated=false`; anonymous applicant/directory 401; Django returns 404 for approve/bulk in LAN mode (unmounted; Vite answers bare OPTIONS itself with 204); direct `:8000` from LAN refused; build flags list/directory `1`, decision/status/governance `0` |
| WF-01 (disposable MySQL) | `test_session_auth`, `test_password_reset`, `test_instructor_registration_otp`: 68/68 |
| WF-02/WF-03 (disposable MySQL) | `test_wf02_dashboard_integration`, `test_registration_review_routing`, `test_wf0301_option_a_proxy`, `test_registration_bulk`, `test_wf0203_approval`, `test_registration_review_notifications`, `test_registration_outbox`, `test_wf0301_d113_role_context`: 103/103 |
| Contracts | `config.test_dev_features` + `config.test_wf0301_lan_dev_gate`: 43/43 (restored Option A gate accepts `ctug_workspace`; launcher feature-agnostic and ASCII) |
| Not performed | Sign-in with the owner's existing accounts (credentials not used by the assistant); no real-data decisions; no migrations; no SMTP |

## 24 November 2026 — permanent one-command LAN development system (superseded; synthetic variant removed)

| Check | Result |
| --- | --- |
| LAN IP detection | `-CheckOnly` selected Wi-Fi `192.168.100.46`; ZeroTier (APIPA default gateway), Tailscale, WSL/Hyper-V and Bluetooth adapters excluded; public/APIPA/CGNAT `CTUG_DEV_LAN_IP` values refused |
| Synthetic initialization | Schema created with marker; all migrations applied to `ctug_lan_synthetic` only; seeded 6 roles, 2 services, 8 accounts, 24 pending applicants, 4 catalogue permissions, 4 audited Admin bindings; second run created 0 rows (idempotent) |
| Startup | Launcher printed the success block for `http://192.168.100.46:5173` only after page 200, proxied session `authenticated=false`, anonymous directory 401 and direct `:8000` LAN connection refused |
| Live end-to-end (`manage.py ctug_lan verify --mutate-synthetic`) | 34/34: frontend and registry build flags (WF-02 `1`, governance `0`); proxy; marked synthetic DB; Option A refuses `ctug_workspace`; anonymous 401; loopback-only Django; School Admin sign-in with role context and 4 WF-02 permissions; pending list, search/filter, detail and server-advertised approve/reject/bulk actions; directory list/detail/history; suspend route 404; Technical Super Admin role switch and inherited WF-02 in its own context; governance routes 404; Student, Instructor and Treasurer denied (403, including a reject POST); approval (Approved/active, role, audit, encrypted Pending outbox row); duplicate approval 404; rejection (account and profile deleted, encrypted outbox row retained); bulk approve 2/2; bulk reject skipping an already-decided ID; 21-ID bulk 400; outbox row count exact; sign-out |
| Rate limits | Running the verifier twice within a minute returns HTTP 429 from the existing login (8/min) and bulk (3/min) throttles. These were left unchanged; one run per minute passes |
| Refusals | `ctug_lan initialize/preflight` under `config.settings` refused before any write; Option A with `ctug_workspace` raises `ImproperlyConfigured` |
| Shutdown | Ctrl+C keypress: exit 0, ports 8000/5173 free, 0 server processes. Console Ctrl+C signal: same. Frontend killed: launcher stopped the backend tree (exit 1). Abruptly closed launcher: next start stopped only the 2 recorded process trees and the record was removed |
| Unit/contract | `python -m unittest config.test_dev_lan_profile config.test_wf0301_lan_dev_gate config.test_wf0301_https_lan_gate`: 66/66, including launcher feature-agnostic and ASCII guards |
| Regression (disposable MySQL) | `manage.py test --settings=config.test_settings` for `test_wf02_dashboard_integration`, `test_registration_review_routing`, `test_wf0301_option_a_proxy`, `test_registration_bulk`, `test_wf0203_approval`, `test_registration_review_notifications`, `test_registration_outbox`: 98/98; database destroyed |
| Not verified | Access from a second physical device: Windows reports the Wi-Fi as a Public network. SMTP delivery is intentionally off |

## 24 November 2026 — isolated bulk route integration

| Check | Result |
| --- | --- |
| Review-route resolution | 11/11 passed; `/bulk/` resolves in local-review, decision-local and sandbox URLconfs, remains absent from normal `config.urls`, and decision-local omits status-write routes |
| Bulk decision and release safeguard | 50/50 passed across `test_registration_bulk` and `test_wf0201_release_safeguard`; disposable test database destroyed |
| Frontend bulk/API contract | 36/36 passed across the bulk and applicant-review API contract tests |
| Decision-local profile | Django system check clean; account-status writes disabled, SMTP disabled, applicant/directory reads enabled |
| Runtime database | Read-only `ctug_workspace` count: 4 eligible Pending applicants, 1 eligible ordinary directory account; outbox status count zero; no personal fields selected |
| Local services / browser | Django and Vite both bound to `127.0.0.1`; browser renders sign-in page; session `authenticated=false`; CSRF 200; applicant and directory APIs 401 unauthenticated; bulk OPTIONS 200 |
| Runtime outbox readiness | No valid active wrapping key found in process, user, machine, or project `.env` configuration; decisions remain fail-closed |
| Real records / email | No account decisions, migrations, SMTP authentication, or SMTP delivery performed |
| Activation | Local backend bulk/read gates and frontend WF-02 flags are enabled only in the current localhost processes. The route is mounted only in isolated local-review/decision-local/sandbox URLconfs; the active key is absent, so no decision controls are advertised. SMTP worker/delivery remains separately gated and off |

The routing and bulk suites ran with `config.test_settings` against disposable MySQL test databases. Environment and outbox checks queried only key-format presence and aggregate status counts; no key contents or personal fields were printed. Live authenticated School Admin/Technical Super Admin access and role-level Student/Instructor denial were not browser-verified because no credentials were supplied; existing authorization tests remain the evidence for those paths.

## 23 November 2026 — WF-02.03/02.04 durable notifications and bulk decisions

| Check | Result |
| --- | --- |
| Backend decision/bulk API | 78/78 passed across `test_registration_review_api`, `test_wf0203_approval`, and `test_registration_bulk`; isolated disposable MySQL database destroyed |
| Backend notification/outbox/review | 36/36 passed across `test_registration_review_notifications`, `test_registration_outbox`, and `test_registration_review`; separate isolated disposable MySQL database destroyed |
| Dashboard action availability | 6/6 passed in `test_wf02_dashboard_integration`; a third isolated disposable MySQL database destroyed |
| Outbox availability | Bulk action hints are omitted when the outbox gate or active wrapping key is unavailable; decision services fail closed before writes |
| Frontend decision/bulk contracts | 47/47 passed across the pending API contract, approval, and bulk tests |
| Applicant-review browser checks | 22/22 passed across pending-applicant and approval suites, including active-gate approval/rejection confirmations and disabled controls when gates are off |
| Production build | `npm.cmd run build` passed (TypeScript and Vite) |
| Real database / delivery | No records or migrations changed in `ctug_workspace`; no SMTP delivery attempted |
| Activation | Bulk URLconf and approval/rejection mutation routes remain unmounted from the normal application; default-off decision gates were not enabled |
| Live authenticated decision | Not verified. Browser tests use synthetic fixtures and mocked APIs; they do not prove authenticated live decisions or mail delivery |

Test targets from `backend/`. They were invoked with the existing virtual environment and a process-local runner that loads `.env` without printing values, clears the three role-context acknowledgements only for the test process, and runs each target under `config.test_settings`. No environment file was changed:

```powershell
python manage.py test apps.accounts.test_registration_review_api apps.accounts.test_wf0203_approval apps.accounts.test_registration_bulk --settings=config.test_settings --noinput
python manage.py test apps.accounts.test_registration_review_notifications apps.accounts.test_registration_outbox apps.accounts.test_registration_review --settings=config.test_settings --noinput
python manage.py test apps.accounts.test_wf02_dashboard_integration --settings=config.test_settings --noinput
```

Commands from `frontend/`:

```powershell
node --test tests/registration-review-bulk.test.mjs tests/registration-review-api-contract.test.mjs tests/registration-review-approval.test.mjs
node --test tests/browser/pending-applications-errors.test.mjs tests/browser/applicant-approval-errors.test.mjs
npm.cmd run build
```

## 23 November 2026 — Temporary localhost-only runtime activation

The earlier pre-activation inspection is retained below in the development-status history. This checkpoint reflects the current running processes; the read flags were set in process environments only, not persisted in `.env`.

| Check | Observed result |
| --- | --- |
| Bindings and proxy | Django `127.0.0.1:8000`; Vite `127.0.0.1:5173`; no LAN listener on these ports. Vite `/api` proxy targets the local Django server |
| Local role context | Normal localhost-only role-context acknowledgement loaded; conflicting LAN/HTTPS acknowledgements cleared in the Django process after loading existing `.env`. No configuration files changed |
| Read flags | Backend applicant list and account directory on; matching Vite flags on. Status, approval, rejection, outbox, SMTP and protected executor writes off |
| Browser/app smoke | `http://127.0.0.1:5173/` returned 200 and rendered the real sign-in screen; CSRF endpoint 200; session endpoint 200 with unauthenticated state |
| API auth/gates | Applicant and directory reads returned 401 through the Vite proxy (not 503), confirming enabled read gates with authentication still enforced |
| Mutation protection | Applicant approve/reject and account activate/suspend paths returned 404 |
| Frontend gate inspection | Vite-transformed applicant/directory modules report enabled read flags; approval/rejection/status flags report disabled |
| Database | Existing local MySQL `ctug_workspace`; prior read-only check found 3 eligible Pending Student applications and 1 eligible ordinary Approved directory account before viewer exclusion. Services and Admin read grants are active. No database changes or personal fields were accessed in this smoke check |
| Authenticated outcome | Not yet verified: the browser has no signed-in session and no credentials were supplied. No live applicant/account payload or role-specific browser access is claimed |

Both servers are currently running in attached tool sessions. Their flags are temporary and revert to the unchanged `.env` defaults if the processes stop. One user action remains: sign in at `http://127.0.0.1:5173` using an existing approved Admin or Technical Super Admin account, then open Applicant Reviews and Account Directory. Existing synthetic browser tests and the prior database-backed role permission check remain supporting evidence, not a substitute for this live authenticated step.

## 23 November 2026 — Pre-activation local runtime inspection

This read-only inspection preceded the localhost-only process activation. It did not expose or record personal fields, change `.env`, alter the real database, or claim live authenticated browser verification.

| Check | Observed result |
| --- | --- |
| Feature gates | Backend and frontend read flags were unset/default-off; normal read probes returned 503 |
| Network safety | Vite was bound to a private LAN interface over plain HTTP; localhost was unavailable. Real-data flags were not enabled |
| Startup configuration | A fresh settings import was refused because the existing uncommitted LAN role-context acknowledgement conflicted with normal localhost role context. The uncommitted LAN/HTTPS implementation was preserved |
| Focused verification | Isolated backend 86/86; frontend/browser 60/60; build passed. An expanded selector had 72/73 pass, reproducing the existing appointment-permission/frozen-catalogue mismatch documented in the historical checkpoint |

The browser tests use synthetic fixtures/mocked APIs and do **not** prove live integration. No database writes, migrations or applicant/account personal-data access occurred in that inspection.

## 23 November 2026 — WF-02 dashboard integration

Source baseline: branch `ronald`, parent `d9b58da`; pre-existing LAN/settings/script changes left outside this implementation commit. These are source, synthetic database and mocked-browser checks, not live release or human approval evidence.

| Check | Observed result |
| --- | --- |
| Final backend integration/regression | 250/250 passed, 0 failed/errors/skipped across 15 selected modules; fresh disposable MySQL database destroyed after the run |
| Backend status/outbox/release supplement | 46/46 passed in 3 additional modules; separate fresh disposable MySQL database destroyed |
| Focused frontend contracts/clients and role context | 73/73 passed, 0 failed/skipped |
| Six existing WF-02/dashboard browser suites | 62/62 passed, 0 failed/skipped |
| Independent read-only directory build/browser suite | 3/3 passed, 0 failed/skipped; School Admin and Technical Super Admin access with only the directory read build flag; no status controls/POST; Student denied |
| Full frontend unit suite | 238 tests: 237 passed, 1 existing failure (`dashboard-navigation.test.mjs`: appointment permission absent from frozen v2.0 inventory) |
| Changed/new frontend source and tests lint | Passed, 0 problems |
| Full frontend lint | 3 existing `react-hooks/set-state-in-effect` errors: `RoleContextSwitcher.tsx` lines 16 and 19, `RolePermissionsPanel.tsx` line 52; these files are unchanged by this task |
| `npm.cmd run build` | Passed: TypeScript and Vite production bundle |
| Django system checks | No issues during isolated test setup; all three normal WF-02 backend flags observed unset/default-off |
| Schema/migrations | No model/migration/DBML change; no migration applied to `ctug_workspace` |
| Git diff validation | `git diff --check` passed; source comparison confirmed every original catalogue approval/checklist line unchanged and all six existing WF-02 sections updated |

Backend coverage includes the real normal read URLconf, exact permissions and Admin assignment, Technical Super Admin inheritance in its own selected context, actual role-context switch to Instructor and subsequent denial, Student/Instructor/anonymous denials, Deny precedence, revoked inherited assignment, protected-target exclusion, search/status filtering, default-off read gates, no mounted normal writes/governance, no-store responses and server action hints under isolated mutation gates. Existing approval/rejection/status/history suites retain transaction, proof, deletion/outbox, conflict, audit and revocation coverage. Release-guard tests cover exact read mounts and refusal of moved/renamed/overridden/subclassed/duplicate mounts, status writes and provisioning while the new read gate is on.

Browser suites use fresh headless Edge profiles, localhost-only Vite and synthetic/mocked APIs. They cover read content, search/filter/pagination, unavailable/expired/forbidden/error/empty states, confirmations, uncertain-write handling with no replay, hidden disabled actions, keyboard/focus behavior and 360/768/1024/1440px layouts in Light, System-dark and Dark with contrast checks. Backend behavior is established separately by isolated MySQL tests; browser mocks are not live API E2E evidence. The 250-case backend run and 46-case supplement used 18 distinct selected modules in separate databases. The 73 focused frontend tests overlap the full 238 and must not be added as unique cases. The 62 and 3 browser cases ran separately.

Commands from `frontend/`:

```powershell
npm.cmd test
node --test tests/account-status.test.mjs tests/registration-review-api-contract.test.mjs tests/registration-review-approval.test.mjs tests/registration-review-rejection.test.mjs tests/role-context-immediate-selection.test.mjs tests/role-context-normal-app.test.mjs tests/role-context-switching.test.mjs
node --test tests/browser/pending-applications-errors.test.mjs tests/browser/applicant-detail-errors.test.mjs tests/browser/applicant-approval-errors.test.mjs tests/browser/applicant-rejection-errors.test.mjs tests/browser/account-directory-errors.test.mjs tests/browser/dashboard-shell-errors.test.mjs
node --test tests/browser/account-management-readonly-errors.test.mjs
npm.cmd run lint
npm.cmd run build
```

Changed-file lint used the frontend-relative paths from `git diff --name-only --relative`, plus `src/features/admin/managementAvailability.ts` and `tests/browser/account-management-readonly-errors.test.mjs`. `npm.cmd` avoids this machine's PowerShell script execution restriction; it does not change execution policy.

Backend command from `backend/` (existing local virtual environment). The preamble loads local credentials without printing them and clears only three process-local development acknowledgements; existing `.env`/settings files are not edited:

```powershell
@'
from dotenv import load_dotenv
load_dotenv('.env')
import os, sys, runpy
for key in ('CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK', 'CTUG_ROLE_CONTEXT_LAN_DEV_ACK', 'CTUG_ROLE_CONTEXT_HTTPS_LAN_DEV_ACK'):
    os.environ[key] = ''
modules = [
    'apps.accounts.test_wf02_dashboard_integration',
    'apps.accounts.test_wf0201_pending_list',
    'apps.accounts.test_wf0202_applicant_detail',
    'apps.accounts.test_wf0203_approval',
    'apps.accounts.test_wf0204_rejection',
    'apps.accounts.test_wf0205_account_status',
    'apps.accounts.test_wf0206_account_history',
    'apps.access_control.test_wf0201_release_safeguard',
    'apps.access_control.test_wf0301_d113_role_context',
    'apps.accounts.test_registration_review_routing',
    'apps.accounts.test_registration_review_api',
    'apps.accounts.test_review_sandbox_boundary',
    'apps.access_control.test_registration_review_metadata_local_dev',
    'apps.access_control.test_registration_review_operational_gate_p3c',
    'apps.access_control.test_registration_review_local_release_p4',
]
sys.argv = ['manage.py', 'test', *modules, '--settings=config.test_settings', '--noinput']
runpy.run_path('manage.py', run_name='__main__')
'@ | .\.venv\Scripts\python.exe -
```

The 46-case supplement used the same backend wrapper with `modules = ['apps.accounts.test_wf0205_stage2', 'apps.accounts.test_wf0204_outbox_erasure', 'apps.accounts.test_wf0204_release_settings']`.

`config.test_settings`/`IsolatedMySQLRunner` selects a fresh unpredictable `test_ctug_registration_<16 hex>` database, refuses reuse/cloning and verifies the connected database before fixtures. Test migrations are disposable setup; no development-database migration or account mutation is authorized by this command. Final database teardown is recorded with the final result above.

Intermediate outcomes are retained honestly: the first backend command stopped at the existing LAN startup guard before database access. The first 177-case regression then had 176 successes and one error in the new action-hint fixture because its temporary URLconf omitted applicant detail; the fixture was corrected and the final expanded run is reported above. The first frontend run also exposed a missing-header compatibility issue in older mocks; the client now fails closed for absent headers, with regression coverage. Full frontend test/lint blockers persist independently of these fixes: the frozen-inventory mismatch exists in the original navigation, and all three lint findings are in unchanged files. The initial 46-case supplement hit two stale assertions within the old no-normal-routes test; it was updated to verify mounted reads return 503 by default and status writes remain unmounted. Its rerun passed all 46 cases. The expected audit-writer failure simulation can log a safe RuntimeError; the legacy date fixture emits a naive-datetime warning.

Remaining unverified: real applicant data over approved HTTPS, live permission/service readiness, live SMTP delivery, shared-LAN safety, production deployment, pending protected WF-03 activation/migrations and full backend repository regression outside the selected suites. No new Human Approval, grant/provisioning, protected executor activation or push is inferred from passing tests.

## 1. Frontend Verification

| Area | Verification | Result |
|---|---|---|
| React production build | `npm run build` | Passed |
| Frontend automated tests | `npm test` | 25/25 passed |
| Browser end-to-end authentication | Manual browser verification | Pending |
| Permission-aware dashboard | Role-based navigation and access tests | Pending |

The successful frontend build confirms TypeScript compilation and Vite bundling. It does not independently establish end-to-end authentication or authorization correctness.

## 2. Backend Test Results

| Phase | Test Suite | Observed Result |
|---|---|---|
| AR-5A — Session Authentication | Session and registration regression | 44/44 passed |
| AR-6A1 — Registration Review Service | Registration approval/rejection service | 17/17 passed |
| AR-6A2 — First Admin Bootstrap | Initial Admin provisioning and security tests | 15/15 passed |
| AR-6C1 — Registration Review API | Session, CSRF, permissions, review actions, audit | 18/18 passed |
| AR-6C1 — Regression Verification | Registration review and session authentication | 31/31 passed |
| AR-6C2 — Routing Safety Verification | Routing safety plus registration-review API | 25/25 passed (7 routing + 18 API) |
| Django System Check | `python manage.py check` and checks during test setup | Passed; 0 issues |

**AR-6C1 final verification date:** November 8, 2026.

The AR-6C1 API suite initially recorded 17 passes and one failure caused by an incomplete CSRF-cookie setup in the test fixture. After correcting the fixture, all 18 tests passed.

The subsequent 31 regression tests also passed.

**Combined AR-6C1 test executions:** 49 successful test executions across two separate test commands. These are execution counts, not 49 unique test cases.

The tests ran using isolated temporary MySQL databases, which were destroyed after execution.

### AR-6C2 Final Routing Verification

**Date verified:** November 8, 2026

**Command (from `backend/`):**

```powershell
python manage.py test apps.accounts.test_registration_review_routing apps.accounts.test_registration_review_api --settings=config.test_settings --noinput --verbosity 2
```

- **Discovered:** 25 tests.
- **Passed:** 25/25 (7 routing safety tests and 18 API tests).
- **Failed:** 0.
- **Database:** Temporary isolated MySQL test database, successfully destroyed after the run.
- **Scope:** Routes remain absent from the live root URL configuration; feature flags still default to OFF.

The 18 API tests were rerun in AR-6C2; they are not 18 additional, distinct test cases. A logged `RuntimeError` during the intentional audit-writer failure simulation is expected; the corresponding negative test passed.

## 3. Database and Security Verification

| Verification | Observed Result |
|---|---|
| Initial Workspace Admin bootstrap | Successfully provisioned and audited |
| Post-bootstrap preflight | 1 Admin assignment and 1 bootstrap event |
| Permission catalogue V2 planner | Completed in read-only mode |
| Catalogue conflicts | 0 |
| Proposed services | 10 |
| Proposed permission definitions | 95 |
| Proposed role-permission bindings | 106 |
| AR-6B1 static catalogue inspection | Passed |
| Registration-review permission definitions | All 3 verified |
| Registration-review permission scope | `SCHOOL` |
| Live permission catalogue activation | Not performed |
| AR-6C1/AR-6C2 live URL integration | Not performed |
| AR-6C3 registration review integration | Source-based assessment documented; no live integration or new Django test run |
| ADR-003 protected ERD SHA-256 | Both locally matched approved Option A pins on November 8, 2026 |

### Catalogue Planner Classifications

- CREATE: 105
- MATCH: 4
- DEFER: 108
- CONFLICT: 0

The planner did not perform database modifications, permission grants, or service activation.

**Security restriction:** AR-6B1 verification confirms that proposed permission definitions exist in the manifest. The `SCHOOL` scope and three Admin registration-review permissions remain **proposals**, not approved grants or an authorization to activate services.

## 4. AR-6C1 and AR-6C2 Security Test Coverage

The API and routing tests cover:

- Anonymous and authenticated requests.
- Session authentication requirements.
- CSRF and invalid-origin rejection.
- Django Superuser separation from Workspace Admin.
- Effective permission evaluation and individual Deny overrides.
- Inactive services and disabled feature flags.
- Registration listing and pagination validation.
- Registration approval and rejection.
- Self-review prevention and previously reviewed account refusal.
- Permission revocation after session creation.
- Transactional rollback when audit writing fails.
- Explicit confirmation that review routes are not present in the live URL configuration.
- Explicit confirmation that isolated candidate routes resolve without publishing them.
- Preservation of the existing session endpoint.

**Results:** AR-6C1 18/18; AR-6C2 combined 25/25.

The API implementation remains isolated from the live root URL configuration. Its security-related feature gates remain disabled.

## 5. Regression Commands

Run these commands from the appropriate project directories.

### Frontend

```powershell
cd frontend
npm run build
npm test
```

### Backend

```powershell
cd backend
python manage.py check
python manage.py test apps.accounts.test_session_auth apps.accounts.test_registration --settings=config.test_settings --noinput
python manage.py test apps.accounts.test_registration_review apps.accounts.test_admin_bootstrap --settings=config.test_settings --noinput
python manage.py test apps.accounts.test_registration_review_api --settings=config.test_settings --noinput --verbosity 2
python manage.py test apps.accounts.test_registration_review_routing apps.accounts.test_registration_review_api --settings=config.test_settings --noinput --verbosity 2
```

### Read-Only Permission Catalogue Verification

From the backend directory:

```powershell
python manage.py plan_permission_catalogue_v2
python scripts/check_registration_review_catalogue.py
```

These commands must not activate services or grant permissions.

## 6. Evidence Quality Rules

- Passing automated tests does not establish production readiness.
- Keep sanitized terminal logs or CI results as evidence for future runs.
- Never publish passwords, tokens, `.env` contents, personal account information, or private database credentials.
- Verify the configured database before any database-changing operation.
- Test successful authorization alongside explicit denial cases.
- Verify transaction rollback and audit consistency.
- Record the difference between proposed, implemented, tested, approved, and activated functionality.

## 7. Next Verification Requirements

1. Complete the open AR-6C3 release gates after the documented source-based readiness assessment: registration-review object/field scope, API contract and security policy approvals.
2. Approve the minimal registration-review permission definitions and any necessary service/role grants **separately** from ADR-003.
3. Re-run the patched integrity verifier in the approved local read-only environment, with no database mutations.
4. After explicit authorization, test controlled catalogue initialization, grant activation, auditing and rollback.
5. Complete object-level authorization, session revocation, concurrency and transactional audit tests.
6. Conduct browser authentication and registration-review integration tests and verify permission-aware Admin dashboard navigation.
7. Demonstrate registration, authorized approval, login, dashboard and logout end to end only after approved activation.
8. Complete final regression and release-readiness review. Do not infer production readiness from isolated passes.

## 8. ADR-003 Integrity and AR-6C3 Assessment Evidence

**Option A scope:** The owner approved the existing `accounts.is_staff` and `accounts.is_superuser` columns in both protected DBML files. The checks below do **not** activate registration review.

| Evidence | Observed result | Source |
|---|---|---|
| `docs/database/full_schema.dbml` SHA-256 | `e4362be913280ab6c23d5c66af249fc1923fccb1acd7b6c2696f7ee95c19d4a0` — matched | Owner's Windows `Get-FileHash` output, November 8, 2026 |
| `docs/database/schema.dbml` SHA-256 | `3bc2060ae35fce16725d6ca5b90272e819039b8dce855ffe305b654140f77313` — matched | Owner's Windows `Get-FileHash` output, November 8, 2026 |
| Historical pin reconciliation | Removing only the two framework-flag lines **in memory** reproduced both prior recorded fingerprints | Earlier offline ZIP inspection |
| Updated `verify_catalogue_plan.py` Python syntax | Passed for the prepared patch; no local owner result reported | Earlier offline patch inspection |
| AR-6C3 review | Source-based readiness assessment recorded; **not** a new automated integration test run | `docs/implementation/authentication/ar-6c3-integration-readiness-assessment.md` |

**Still pending:** The owner has not supplied a successful execution log for the complete updated read-only Django/MySQL integrity verifier, new Django integration tests, any catalogue activation, or full browser E2E. ADR-003 design approval is **not** permission-catalogue or API activation approval.

## 9. Current Testing Status

**AR-6C1:** Implementation and automated testing verified.

**AR-6C2:** Routing safety and API regression testing verified (25/25). The review API remains inactive.

**AR-6C3:** Source-based readiness assessment recorded. ADR-003 ERD option approved; both local protected-ERD fingerprints confirmed. No new Django integration tests or live registration-review activation are claimed.

**Outstanding:** Registration-review scope and API contract approval, controlled catalogue activation, local verifier execution, live URL integration, full browser testing, and deployment readiness.

**Overall assessment:** Development verification is progressing successfully. The registration-review API is not approved for live operation.
