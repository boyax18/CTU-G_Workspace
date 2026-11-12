# CTU-G Workspace — AR-6C7E.1 Real-Data Registration Review UI Candidate

**Status:** Functionally implemented frontend candidate; **NOT ACTIVATED**. No MySQL writes, no backend route mounting, no service/role activation, no changes to the official ERD.

## What this changes

A live-data-ready React registration review panel is provided using the existing AR-6C7D.2 typed API client, strict backend response contract, and shared dashboard layout. It supports:

- GET pending Student and Instructor requests, 20 records per page (no fabricated total count).
- Search by School ID and filter requested role on **the current page only**; no unsupported backend query fields.
- Permission-hint-based hiding of buttons and Admin-role presentation restriction. **Only backend checks authorize requests.**
- Individual approval (empty JSON body) and rejection (one of four allowed codes), with explicit confirmation.
- Session cookie + CSRF via the previously reviewed `postJSON`; no retry of ambiguous state-changing requests.
- Refresh after a server-confirmed action. Failed/ambiguous actions require the operator to refresh first.
- Safe, fixed user-facing error messages; no display of raw backend exception text.
- Accessible status/error labels and responsive table within the existing university dashboard design.

## Files

- `frontend/src/features/admin/RegistrationReviewLivePanel.tsx`
- `frontend/src/features/admin/registrationReviewLiveViewModel.ts`
- `frontend/src/features/admin/registrationReviewLiveConfig.ts` — **approved backend root remains null**
- `frontend/tests/registration-review-live-ready.test.mjs` — Node frontend tests, no network
- `frontend/scripts/apply_registration_review_live_panel_safe.py` — optional dashboard integration with `--check` and `--apply`
- This design document.

## Security invariants

1. The existing `REGISTRATION_REVIEW_LIVE_API_ENABLED: boolean = false` is **unchanged**. Backend gates still false and URLconf still unmounted. The approved route root is additionally **null**, to block accidental access.
2. Do not set the route root or live gate independently. Before release, the root must match an explicitly approved Django URL mount, and backend/services/grants must pass authorized transition and authenticated tests.
3. Multi-role sessions do not bypass authorization. `Admin` role and exact read code are display hints; backend permission evaluator checks actual DB state with Deny precedence per request.
4. No bulk approval/rejection, no enrollment-management changes, no new schema/migrations.
5. Don't touch the modified official `docs/database/full_schema.dbml`, unrelated `backend/apps/config/`, or any `.env` files.
6. No functional activation until the operational risk and recovery approach is resolved. User declined a backup; skip backup-dependent writes rather than pretending transaction rollback can recover every failure.
7. UI does not automatically retry an ambiguous POST, and displays only server-confirmed decisions.

## Install and verify (from repo root, branch `ronald`)

1. Extract package add-only files. Stop if a destination already exists.
2. In `frontend/`, run `node --test tests/registration-review-live-ready.test.mjs`; then `npm test`, `npm run build`, `npm run lint`.
3. Optional: `python -B frontend/scripts/apply_registration_review_live_panel_safe.py --check`; if compatible, `--apply`. This patches **only** `SessionDashboardPage.tsx`, adding a branch behind the existing false live gate; no API calls become reachable.
4. Review scoped `git diff`; stage only the package files and optionally patched dashboard file. Do not use `git add .`.
5. Maintain the existing Phase 3E read-only release baseline and backend tests.

## Release work still outstanding

A coordinated later change must approve an exact URL prefix, mount `registration_review_urls.py`, activate two services and three Admin bindings with audited compensation, enable both backend flags, enable the live frontend gate, and run actual authenticated browser integration tests (Admin, Student, Instructor, Django superuser, CSRF, stale request, double-submit, denial). These are **not** performed by this package. A backup/restore or equivalent accepted recovery plan is strongly recommended before any real write.
