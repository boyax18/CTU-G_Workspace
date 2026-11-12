# AR-6C7E.4 — Controlled Local-Development Registration Review Release Candidate

**Project:** CTU-G Workspace
**Branch:** `ronald`
**Baseline:** `00a1ea2` (sandbox functional verification)
**Scope:** Local-development opt-in, `ctug_workspace` only. **Not production.**
**Release status:** Candidate code; do not execute the write command before local regression and review.

## Context and decision

The isolated `ctug_review_sandbox` already demonstrated logged-in Admin list/approve/reject, two resulting audit receipts, 401 for unauthenticated callers, and 403 for an authenticated Student. The main `ctug_workspace` still has two inactive services, three inactive Admin bindings, and eight P1/P2 receipts. Its ordinary API and UI are hard-disabled.

The developer declined a database backup. We respect that choice for local work, but **cannot guarantee recovery** from disk failure, corruption, a committed data change, or a wrong review decision. An atomic transaction and compensation can undo permission state; compensation does **not** undo approvals/rejections, emails, or other data changed by normal business workflows. Do not process real student accounts until a recoverable release process is agreed.

This candidate delivers a *separate, expressly opted-in local release* without modifying `config/settings.py`, `config/urls.py`, the production React gate/route, the ERD, migrations, or the locked P3D code. Running the normal Django/Vite commands remains disabled. The write command requires exact role scope, pinned fingerprint, explicit risk acknowledgement, and a separate acceptance step. It does not enable the API or frontend by itself.

## Installed files

1. `backend/apps/access_control/management/commands/release_registration_review_local_dev_p4.py` — guarded local activation/compensation CLI
2. `backend/apps/access_control/test_registration_review_local_release_p4.py` — 12 isolated MySQL transaction/security tests
3. `backend/config/review_local_settings.py` — opt-in real local database settings, loopback only
4. `backend/config/review_local_urls.py` — opt-in Registration Review routes, normal URLconf untouched
5. `frontend/local_review/registrationReviewApiGate.ts` — opt-in Vite-only alias target
6. `frontend/local_review/registrationReviewLiveConfig.ts` — opt-in approved local route
7. `frontend/vite.review-local.config.ts` — loopback-only Vite server, ports 5176 → 8002; refuses build
8. `frontend/tests/registration-review-local-release-boundary.test.mjs` — six frontend boundary tests
9. This documentation

## Preconditions and tests (NO WRITES TO DEVELOPMENT DATABASE)

- Stop the sandbox backend and frontend before any local release test; **do not** share sessions/passwords between sandbox and main.
- Confirm branch `ronald`, note current commit and unrelated dirty work, especially the official ERD. Do not `git add .`.
- Run 12 isolated backend tests using `--settings=config.test_settings`; they create/destroy their own temporary MySQL test DB.
- Run the combined previous 301 tests plus the 12 new tests, then the 6 frontend boundary tests, existing integration tests, and normal `npm run build`.
- Run read-only P3E fingerprint and P4 preview under **normal** `config.settings`, with exact Admin scope. The fingerprint must match the current database state; never substitute a guessed value.
- Explicitly examine the five intended toggles, who has the Admin role, test account policy, notification consequences, and the fact that any committed decision cannot be undone merely by disabling permissions.

### Read-only preview (no writes)

```powershell
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend"
.\.venv\Scripts\Activate.ps1
python -B manage.py report_registration_review_release_gates_p3e --actor-account-id 3 --expected-admin-account-ids 3
# Use exactly the SHA-256 printed above, only if it matches the current state.
python -B manage.py release_registration_review_local_dev_p4 --mode activate --actor-account-id 3 --expected-admin-account-ids 3 --expected-fingerprint <PASTE_CURRENT_SHA256>
```

### Operational cutover (NOT part of candidate's initial test step)

After passing ALL tests and an independent review of the implementation, operator can explicitly accept the risk of having no backup and run the command below on their private LOCAL development machine. This command **will mutate real `ctug_workspace` authorization metadata**:

```powershell
# CAUTION: do not execute until reviewed and authorized as a separate step.
python -B manage.py release_registration_review_local_dev_p4 --mode activate --actor-account-id 3 --expected-admin-account-ids 3 --expected-fingerprint <PASTE_CURRENT_SHA256> --apply --confirm-local-release ctug_workspace:AR-6C7E4:LOCAL-ONLY-TRANSITION --risk-ack I_ACCEPT_UNBACKED_LOCAL_DEVELOPMENT_RISK
```

It atomically changes exactly two service flags and three role-binding flags from false to true, appending five P3B-compatible receipts. It checks Admin scope, original eight receipts, absence of overrides, baseline fingerprint, effective grants, disabled normal API flags, and unmounted normal routes; repeats checks before commit. It may refuse if any state is unexpected or there are more than 100 accounts in the local DB (the current test exercise bounds). Do not force past refusal.

**Do not enable any API until the five metadata changes have been independently verified.** For an authorized private local interactive trial, use only the separate opt-in processes below (never deploy them):

```powershell
# Terminal 1: Django local-opt-in (real development accounts may be modified)
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend"
$env:CTUG_REVIEW_LOCAL_ACK = "LOCAL_REVIEW_ONLY"
python -B manage.py runserver 127.0.0.1:8002 --settings=config.review_local_settings

# Terminal 2: Vite local-opt-in (real development accounts may be modified)
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\frontend"
$env:CTUG_REVIEW_LOCAL_ACK = "LOCAL_REVIEW_ONLY"
$env:VITE_CTUG_REVIEW_LOCAL = "LOCAL_REVIEW_ONLY"
npx vite --config vite.review-local.config.ts
# Browser: http://127.0.0.1:5176/
```

Real review POSTs change actual account statuses. Only test against deliberately created local test accounts after confirming their identity. Avoid the existing real pending registrations. In particular, do not reuse sandbox IDs or passwords; main and sandbox are separate schemas.

### Compensation (revokes permissions, not earlier account decisions)

1. **Stop the opt-in Vite and Django servers** with Ctrl+C. Do not run more approval/rejection requests.
2. In normal `config.settings`, run a read-only compensation preview:

   ```powershell
   python -B manage.py release_registration_review_local_dev_p4 --mode compensate --actor-account-id 3 --expected-admin-account-ids 3
   ```

3. Only if the preview passes and the operator confirms the real database state, execute the explicit compensation command:

   ```powershell
   python -B manage.py release_registration_review_local_dev_p4 --mode compensate --actor-account-id 3 --expected-admin-account-ids 3 --apply --confirm-local-release ctug_workspace:AR-6C7E4:LOCAL-ONLY-TRANSITION --risk-ack I_ACCEPT_UNBACKED_LOCAL_DEVELOPMENT_RISK
   ```

4. Independently verify both services and three bindings are inactive and five deactivation receipts appended. Restart *normal* Django + frontend only. Do not repeat a failed or ambiguous command blindly.

**Important:** Compensation does not delete audit logs, reset registration decisions, roll back committed user data, or replace a restorable database backup. Initial P3E fingerprint will not match after an activation/compensation history is appended; this is expected and must be reviewed rather than ignored.

## Release constraints

- Normal `config.settings` + `config.urls`, and normal frontend build remain unchanged and disabled.
- Only `config.review_local_settings` exposes routes. That settings module requires an explicit marker, local MySQL name, loopback peer middleware, no SMTP, isolated cookies, and DEBUG mode.
- The local Vite configuration requires an explicit marker, binds `127.0.0.1:5176`, proxies solely to `127.0.0.1:8002`, and refuses `vite build`.
- Do not deploy, push secrets, change official DBML, change existing roles, or automatically approve accounts.
- This code's Python syntax and frontend static boundary checks may pass without proving all Django transactional cases; run local isolated MySQL tests before any write.
