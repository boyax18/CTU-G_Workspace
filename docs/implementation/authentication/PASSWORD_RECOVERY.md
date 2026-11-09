# CTU-G Workspace — Password Recovery

**Feature ID:** AR-6C4  
**Document type:** Technical feature specification and verification record  
**Status:** Implemented and automated tests passed; **disabled by default / not production-released**  
**Last reviewed:** 2026-11-10  
**Scope:** CTU-G Workspace browser-based account recovery; not the Django `/admin/` password-reset process.

## 1. Purpose and scope

Provide an eligible CTU-G Workspace account holder with a way to request a password-reset link and choose a replacement password without an administrator manually changing credentials. The public interface uses **School ID plus registered email**, because email is not unique in the current ERD. This feature does not approve registrations, assign permissions, or change enrollment records.

## 2. Implemented components

| Component | Source location | Responsibility |
| --- | --- | --- |
| Recovery API | `backend/apps/accounts/password_reset.py` | Request validation, eligibility, token issuance, email attempt, confirmation and password update |
| Recovery routes | `backend/apps/accounts/urls.py` | Registers the two API endpoints |
| Backend configuration | `backend/config/settings.py` | Opt-in feature gate, reset timeout, public base URL and email transport |
| Forgot Password page | `frontend/src/features/auth/ForgotPasswordPage.tsx` | Collects School ID and registered email; gives neutral response |
| Reset Password page | `frontend/src/features/auth/ResetPasswordPage.tsx` | Accepts link fragment and new password; removes token fragment from browser URL |
| Frontend API helpers | `frontend/src/features/auth/passwordReset.ts` | Requests reset and submits confirmation |
| Frontend routing | `frontend/src/App.tsx` | Routes `/forgot-password` and `/reset-password` |
| Backend tests | `backend/apps/accounts/test_password_reset.py` | Isolated MySQL test cases |
| Frontend tests | `frontend/tests/password-reset.test.mjs` | Client-side recovery flow checks |

## 3. Workflow

1. The user opens `/forgot-password` and submits a School ID and the email associated with the account.
2. `POST /api/v1/auth/forgot-password/` checks that recovery is enabled, validates the request and applies throttling and the existing CSRF/session API protections.
3. The backend looks for an account that is **Approved, active, not Django staff or superuser, and assigned at least one active role**. It matches the School ID and registered email; the email match is case-insensitive.
4. For a matching account, Django's default password-reset token generator creates a signed, expiring token. The email contains a link of the form `http://localhost:5173/reset-password#uid=...&token=...` (the configured base URL replaces the example).
5. The public request response is neutral: HTTP **202** and a generic message, whether or not an eligible account was found. Mail exceptions do not reveal account existence to the caller.
6. The user opens the link, chooses a new password, and submits it to `POST /api/v1/auth/reset-password/` with `uid`, `token`, `password`, and `password_confirmation`.
7. The backend checks account eligibility again, validates the token and applies Django password validators before hashing and saving the new password within a database transaction. On success it returns HTTP **200**.
8. The token no longer validates after the password changes. The frontend removes the token fragment from the visible browser URL after loading it.

**Note:** A URL fragment is not transmitted as part of an ordinary HTTP request path, but a reset token is still a credential. Do not paste links, console email output, or tokens into Git, issue trackers, screenshots, or shared logs.

## 4. Configuration and API contract

| Setting | Default in the AR-6C4 implementation | Notes |
| --- | --- | --- |
| `WORKSPACE_PASSWORD_RESET_ENABLED` | `0` / False | Feature must be explicitly enabled for local manual testing |
| `PASSWORD_RESET_TIMEOUT` | `1800` seconds | 30-minute token validity |
| `WORKSPACE_PUBLIC_BASE_URL` | `http://localhost:5173` | Must match the actual frontend origin used for the emailed link |
| `WORKSPACE_EMAIL_SMTP_ENABLED` | `0` / False | Console email backend is used by default |
| `WORKSPACE_EMAIL_FROM` | `ctuginatilanextensioncampus@gmail.com` | Default sender label; does **not** establish that Gmail delivery is configured |
| `WORKSPACE_EMAIL_USERNAME`, `WORKSPACE_EMAIL_APP_PASSWORD` | Required only when SMTP is enabled | Keep values in untracked environment settings, never documentation or Git |

**API routes:**

- `POST /api/v1/auth/forgot-password/` — JSON `{ "school_id": "0012345", "email": "user@example.edu" }`; neutral **202** when enabled, **503** when disabled.
- `POST /api/v1/auth/reset-password/` — JSON `{ "uid": "...", "token": "...", "password": "...", "password_confirmation": "..." }`; **200** on success, validation error for an invalid or expired link, **503** when disabled.

Both requests use the project's CSRF-protected frontend API client. The request and confirmation endpoints implement rate limits; password recovery is not a role-authorization or account-activation mechanism.

## 5. Safety boundaries

- No Workspace password reset for Pending, Rejected, inactive, unassigned, or inactive-role accounts, or for Django staff/superusers.
- Never include a password, token, or account-existence indication in a public response.
- Reset links are sensitive; restrict access to the development console, where the console email backend displays the complete link.
- Use HTTPS, appropriate host/origin settings, approved mail service credentials, and a security review before any production activation.
- The feature adds **no database migration and no change to the official ERD**.

## 6. Verified testing as of 2026-11-10

| Verification | User-reported result | Scope |
| --- | --- | --- |
| Django system check | Passed; 0 issues | Configuration/import checks |
| Registration + recovery backend tests | **38/38 passed** | Includes password recovery and public registration |
| Frontend tests | **28/28 passed** | Earlier AR-6C4 frontend checkpoint |
| Frontend TypeScript/build | Passed | `npx tsc -b --pretty false` and production build |
| Combined registration/recovery/review/notification tests | **62/62 passed** | Later AR-6C5A regression checkpoint |
| Real Gmail SMTP test | **Not performed** | No production mailbox/delivery validation |
| Complete manual browser-to-email-to-reset test | **Not confirmed** | Requires an explicitly controlled local environment |

Re-run relevant tests from `backend/`:

```powershell
python manage.py check
python manage.py test apps.accounts.test_registration apps.accounts.test_password_reset --settings=config.test_settings --noinput
```

Re-run from `frontend/`:

```powershell
npm test
npm run build
```

The backend test settings use an isolated test database; **never** run these destructive test setups against the main development or production database.

## 7. Remaining work / release gate

- [x] Implement backend recovery and frontend pages.
- [x] Validate expired/invalid/reused credentials in the tested recovery logic.
- [x] Pass the focused backend and frontend test checkpoints.
- [ ] Perform a controlled browser-to-console-email-to-reset-to-login end-to-end test.
- [ ] Confirm actual frontend port and public base URL in deployment configuration.
- [ ] Complete security/operations review, including sending limits, console output hygiene and HTTPS setup.
- [ ] Configure and validate an authorized real email transport before production launch.
- [ ] Explicitly approve and enable the recovery feature for the intended environment.

**Release classification:** Code and automated tests complete for the current development scope; **not yet deployed or operationally verified**.
