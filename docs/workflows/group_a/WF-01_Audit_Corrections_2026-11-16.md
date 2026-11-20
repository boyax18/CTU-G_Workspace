# WF-01.01 / WF-01.02 — Audit corrections record

16 November 2026 (Asia/Manila). Process: Inspect → Reconcile → Approve → Implement → Test → Commit.
Parent: [workflow catalogue](../CTU-G_Workspace_System_Workflow_Catalogue.md) (now v0.3.2). Related: [WF-01.01 implementation](WF-01.01_Student_Registration_Implementation.md), [WF-01.02 feedback consistency](WF-01.02_Feedback_Consistency.md).

Baseline: branch `ronald`, commit `952687d`, with 73 pre-existing uncommitted paths that were preserved. The catalogue available at inspection was v0.3.1; no 0.3.2 existed.

## Approval evidence

The project owner reviewed the Phase 1–2 reconciliation report and replied:

> 1.a, 2. yes, 3. i approve your recommendation, 4.i approved 5. let me handle that later

| Item | Owner decision |
| --- | --- |
| OD-1 | (a) Keep the shared Student error feedback for Instructor (16 Nov consistency instruction) and update the catalogue to match |
| OD-2 | Yes: apply per-identity rate limits to Student |
| OD-3 | Approved recommendation: one generic line with the configured code lifetime and a spam/junk-folder hint, paired with R-05; no recipient display, no live code countdown |
| Scope | Packages P1–P4 approved, including the proposed tests |
| R-16 | Deferred: the owner will handle the WF-01.01 Human Approval line. It was not changed |

This approves the scope of these corrections only. It is not workflow Human Approval and does not approve D-01–D-09 or D-14 policy.

## Finding status

| ID | Severity | Status | Correction |
| --- | --- | --- | --- |
| R-01 | High | **Fixed (docs)** | Catalogue WF-01.02, D-07, D-13, Appendix A/B reconciled to the implemented shared feedback; v0.3.2 change log |
| R-02 | Medium | **Fixed** | `_prepare_code` stores the digest inside the locked transaction; `_deliver_code` sends after commit and, on failure, clears only that same digest (`registration_staging.py`) |
| R-03 | Medium | **Fixed** | `_identity_limits` now applies to both roles at admission, status and OTP actions; keys are shared across roles |
| R-04 | Low | **Fixed** | Status view declares the OTP IP throttles, which run before any lookup, for both roles (`student_registration_api.py`) |
| R-05 | Medium | **Fixed** | One-shot, non-identifying sessionStorage flag; the code screen explains that resubmitted details were not used and that a wrong email requires Cancel registration |
| R-06 | Low | **Fixed** | Neutral no-saved-registration wording on first load instead of "has expired" |
| R-07 | Low | **Fixed (dead branch)** | Unreachable direct-registration success branch removed from `RegisterPage.tsx`. Double validation and the unused support setting are deliberately kept (see Deferred) |
| R-08 | Low | **Fixed** | Resend button's visible text equals its accessible name, with the countdown as a linked description; ID/password hint linked by `aria-describedby`; registration and code field errors no longer add a second alert beside the summary (`Input.tsx` opt-out, default unchanged for other forms) |
| R-09 | Low | **Fixed** | No `maxLength` truncation; digits kept and capped at six |
| R-10 | Low | **Fixed (registration client)** | `timeoutSignal()` falls back to `AbortController` plus a timer |
| OD-3 | — | **Implemented** | Success summaries carry `code_valid_seconds` (D-01); screen shows "The code is valid for N minutes. If you don't see the email, check your spam or junk folder." |
| R-11 | Low | Deferred | Role-row lock contention needs a load test first |
| R-12 | High (prod) | Deferred | Production hardening (DEBUG, secure cookies/HSTS, shared cache, console mail backend, HTTP-on-LAN) is a separate task |
| R-13 | Low | Deferred | `.env.example` placeholders (PostgreSQL defaults; SMTP example) need the owner's confirmation |
| R-14 | Medium | Deferred | SRS UC-01/FR-REG-02/03 change control (OTP step; anti-enumeration policy) |
| R-15 | Low | Deferred | Official ERD is read-only; stale "legacy/Instructor" proof note and uncommitted ERD additions await the owner |
| R-16 | Open | Owner | WF-01.01 Human Approval line left exactly as found |
| R-17 | Possible | Deferred | Reapplication (flag off) proof mismatch belongs to WF-02.04 |

Also deferred: `session.ts` (login, WF-01.03) and the admin review client still call `AbortSignal.timeout` directly. Validation still runs twice (view and service): low value, and removing it carries regression risk. `WORKSPACE_REGISTRATION_SUPPORT_CONTACT` stays until the official support contact is decided.

## Boundaries kept

- No ERD, model, migration, permission, role, review-gate or executor change.
- No change to Student conflict wording or main flow; Staff ID rules unchanged.
- No password, cookie, CSRF or OTP safeguard weakened; no automatic POST retry added.
- No `.env` value, credential, code or recipient printed; no real applicant or email.
- Human Approval lines and AI checklists untouched.

## Files changed by this work

- **Backend:** `apps/accounts/registration_staging.py`, `apps/accounts/student_registration_api.py`; new `apps/accounts/test_registration_audit_corrections.py`.
- **Frontend:** `src/api/client.ts`, `src/components/common/Input.tsx`, `src/features/auth/registration.ts`, `registrationFeedback.ts`, `RegisterPage.tsx`, `VerifyEmailPage.tsx`; new `tests/registration-audit.test.mjs`; updated `tests/browser/registration-errors.test.mjs`, `tests/browser/instructor-registration-errors.test.mjs`.
- **Docs:** catalogue (v0.3.2), `docs/api/REGISTRATION_ERROR_CONTRACT.md`, this record.

Several of these files already held uncommitted owner work before this task; that work was preserved, not reverted.

## Test evidence

All backend runs used `config.test_settings`, which creates a randomly named disposable MySQL database and destroys it afterwards.

| Check | Before | After |
| --- | --- | --- |
| Focused backend: `manage.py test apps.accounts.tests apps.accounts.test_registration apps.accounts.test_email_uniqueness apps.accounts.test_public_api_errors apps.accounts.test_student_registration_otp apps.accounts.test_instructor_registration_otp [apps.accounts.test_registration_audit_corrections] --settings=config.test_settings --noinput` | 165 passed | **175 passed** (10 new) |
| Related backend: `manage.py test apps.accounts.test_session_auth apps.accounts.test_password_reset apps.accounts.test_registration_review apps.accounts.test_registration_review_api apps.accounts.test_registration_review_routing apps.accounts.test_registration_rejection_retention apps.accounts.test_framework_admin_readonly apps.accounts.test_admin_bootstrap --settings=config.test_settings --noinput` | 93 passed | **93 passed** |
| Focused frontend: `node --test tests/registration.test.mjs tests/registration-layout.test.mjs tests/api-errors.test.mjs` | 51 passed | **51 passed**, plus **8/8** in `tests/registration-audit.test.mjs` |
| Mocked headless browser (Edge): `npm run test:registration-ui` | 29 (prior report) | **36 passed** (7 new) |
| Real acceptance: `scripts/verify_instructor_registration_live.py` (real React/Edge, Vite, CSRF Django, disposable MySQL, protected Pending read) | — | **1 passed**; no activation or role assigned |
| Full frontend: `npm test` | 139/140 | **147/148**; the one failure is the pre-existing, unrelated `registration-review-api-contract.test.mjs` dashboard/mock-isolation assertion |
| Typecheck / lint / build | — | `tsc --noEmit` clean; ESLint clean on changed files; `npm run build` succeeded |

New test coverage:
- **Backend:** mail sent with no open transaction after the stage and digest commit (register and resend, both roles); failed send clears only its own digest and never a newer one; status endpoint returns 429 for both roles before any lookup; Student identity budget across IPs and shared across roles; Student OTP identity budget; `code_valid_seconds` present in success bodies only.
- **Frontend:** timeout fallback; `code_valid_seconds` validation; guidance wording; pasted-code normalization; one-shot resumed flag (including blocked storage); neutral no-session wording.
- **Browser:** resumed notice for both roles (and its absence on a fresh submission); guidance shown or hidden; pasted "123-456" submits "123456"; single alert on validation with linked field errors; accessible Resend name and countdown.

## Limitations and remaining risks

- Not performed: real inbox delivery, manual screen-reader testing, colour-contrast measurement, cross-browser runs beyond headless Edge, and load testing.
- Throttles still use the default per-process cache; multi-worker enforcement needs a shared cache (R-12).
- Per-identity limits allow a third party to exhaust a victim's registration budget for that ID or email (already an accepted D-14 first-claim risk, now covering Student too).
- This is development verification, not production readiness.

## Workflow status

| | Inspect | Reconcile | Approve | Implement | Test | Commit | Human Approval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WF-01.01 | ☒ | ☒ | ☒ (scope) | ☒ | ☒ | ☐ | ☐ (owner handling R-16) |
| WF-01.02 | ☒ | ☒ | ☒ (scope) | ☒ | ☒ | ☐ | ☐ |

Commit requires the owner's explicit permission. No commit or push has been made.
