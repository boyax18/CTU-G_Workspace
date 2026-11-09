# CTU-G Workspace — AR-6C4 Registration Review and Account Recovery Workflow

**Date:** November 9, 2026  
**Status:** Owner-specified workflow requirements; technical implementation and release authorization pending  
**Scope:** Student/Instructor self-registration, Workspace Admin review, email notifications, bulk decisions, and forgot password

## 1. Decision summary

The project owner specified these workflow rules:

1. Rejected registration credentials/accounts must be deleted, freeing the School ID for a new application; applicants must receive an email outcome notification for both approval and rejection.
2. School IDs accepted in the Student/Instructor registration form contain **1–7 ASCII digits**, with a maximum of seven, and are stored as strings so leading zeroes survive. Apply this to server validation as well as the React form. Do not apply this change to Django framework-operator creation without a separate compatibility assessment.
3. The Admin registration queue shows **School ID, Name, Requested Role, Email, Registration Date, Status, Actions**. Name display is `Last Name, First Name M. Suffix` with Middle Initial and Suffix omitted when absent.
4. Actions support individual **Approve** and **Reject/Delete**, plus row checkboxes for bulk approval and rejection. Rejection causes removal of the applicant's credentials/account after a reliable notification-and-audit process; it must not silently remove unrelated approved accounts.
5. Outbound registration-result emails and password-reset emails should use **ctuginatilanextensioncampus@gmail.com** as the configured sending address once the project operator has authorized and configured that account.
6. Add a **Forgot Password** workflow using one-time, expiring email reset links; never send a user's password.

**Important:** These are approved *business requirements*, not an approval to enable live URLs, activate grants or migrate schemas. School-wide Admin permissions are still subject to the separately proposed authorization governance policy.

## 2. Registration input validation

| Field | Rule |
| --- | --- |
| School ID | Required; regular expression `^[0-9]{1,7}$`; store as string, not integer; preserve leading zeroes; enforce client-side and server-side |
| First name, last name | Required; respect existing length and normalization constraints |
| Middle name | Optional; store as entered; show only first initial (e.g. `Maria`) in review name (`M.`) |
| Suffix | Optional; show only when supplied |
| Email | Required for new applicants once notifications and email recovery launch; validate and verify mailbox ownership before relying on it for recovery |
| Requested role | Student or Instructor only |
| Password | Follow Django configured password validators; never store raw passwords |

**Existing-schema caution:** `Account.school_id` currently permits 50 characters, and existing database values or Django framework accounts might rely on that. First enforce the 7-digit restriction on public Student/Instructor registration endpoints. A DB column-size migration is a separate, reviewed decision, not an automatic consequence of this UI rule.

## 3. Queue content and actions

| Column | Data and display |
| --- | --- |
| Select | Checkbox available for eligible pending requests only |
| School ID | String; preserve leading zeroes |
| Name | `Last Name, First Name M. Suffix`; omit `M.` or suffix when absent |
| Requested Role | Student / Instructor |
| Email | Applicant email, visible only to properly authorized reviewers |
| Registration Date | Date/time; display local timezone consistently |
| Status | Pending for active queue; Approved may be available in a separate authorized history view; rejected accounts are removed, so rejection history must come from a privacy-conscious audit/history mechanism |
| Actions | Approve, Reject/Delete; require confirmation on destructive actions |

Reading full name and email expands the current candidate API's data disclosure. It requires explicit field-minimization/object-scope acceptance and tests. Never return passwords, hashes, reset tokens, or unrelated account fields.

## 4. Approval workflow

1. Actor has an approved, active Workspace Admin assignment, active required services, and an effective `accounts.registration_requests.approve` grant; an individual Deny still wins.
2. Lock and revalidate the target's Pending, inactive, Student/Instructor eligibility. Prevent self-review and double-processing.
3. In a transaction, set Approved/active, assign **only** the requested base role, and append an accurate review audit event.
4. After commit, enqueue an email notification to the verified applicant address; preserve a retry path without approving twice if email fails.
5. UI refreshes the queue and displays individual outcome; no live activation until release gates pass.

## 5. Rejection, notification, and deletion workflow

1. Actor needs the exact effective `accounts.registration_requests.reject` permission and must supply an allowed non-sensitive rejection reason.
2. Lock and recheck the eligible Pending account, confirm Reject/Delete, and prevent concurrent approvals or repeated processing.
3. Reliably persist the rejection outcome and mail delivery intent (for example in a durable outbox) **before** removing the account data. Dispatch the applicant's notification; handle failed delivery with monitored retries.
4. Delete the rejected registration's credentials and associated applicant profile in an audited, integrity-safe cleanup after notification has been reliably handled. This releases the unique School ID for another application. Do not delete approved accounts through this operation.
5. Keep a minimal, access-controlled audit/history record showing the reviewer, action, reason code, and time, while applying retention and privacy rules. Avoid retaining the rejected applicant's password hash or unnecessary personal information.

**Current implementation conflict:** `registration_review.py` currently marks the target `Rejected` and retains the account; `AccessAuditLog.target_account` and `UserProfile.account` are `on_delete=PROTECT`. A direct hard delete would fail or risk breaking audit integrity. Design the durable notification, referential integrity and audit-retention changes together, and approve any required model/ERD/migration changes before implementation. Do **not** simply call `account.delete()` inside the current reject method.

## 6. Bulk actions

- Allow multiple eligible Pending row selections with a Select All **on the current page** control and a selection count.
- Require a separate effective permission for each operation: approve grant for bulk approval; reject grant for bulk rejection. Server must revalidate every item independently.
- Require clear confirmation; bulk rejection requires a permitted reason code, with a transparent destructive-action warning.
- Process a bounded list (proposed initial cap **25 account IDs per request**) with per-account atomicity and idempotent/duplicate-safe handling. Present `approved`, `rejected`, `unavailable`, and `failed` counts with specific, non-sensitive per-item outcomes. Do not auto-retry destructive actions from the browser.
- Audit each accepted decision. Notification queues, failure isolation, and privacy constraints apply just as for single actions.
- No broad "delete any account" permission is implied by registration rejection.

## 7. Gmail sender and notification templates

**Sender address:** `ctuginatilanextensioncampus@gmail.com`

- Approval email: state registration was approved, user's School ID, and how to sign in. **Never include a password**.
- Rejection email: state application was rejected, provide a safe reason category and instructions to apply again after deletion. Do not disclose sensitive internal security decisions.
- Password reset email: secure single-use, expiring link to the official frontend, plus a warning if the recipient did not request it.
- Django local development currently uses `django.core.mail.backends.console.EmailBackend`; real delivery is **not configured**.
- Configure SMTP authentication with an account-authorized mechanism (e.g. Google 2-Step Verification + eligible App Password, or OAuth). Store secrets only in ignored environment variables, never the repository, documentation, or chat. Use a sandbox/test email backend for automated tests.
- Use an outbox and post-commit dispatch/retry strategy to avoid lost notifications or duplicate account decisions; never send mail while holding authorization/decision database locks.

## 8. Forgot Password

1. Public `Forgot password?` link on login, with a form asking for the registered email address.
2. Always return a neutral response such as `If an eligible account exists, we will email a reset link.` Avoid account enumeration.
3. Rate-limit per requester and per destination; permit reset only for eligible, verified, active accounts. Define a separate recovery procedure for accounts with missing or unverified email.
4. Create a high-entropy, one-time token with short expiration (proposed **30 minutes**); store only a token hash, never the raw token. Do not reuse account passwords or reveal their hashes.
5. Deliver reset URL through the authorized Gmail sender. Link opens a secure frontend reset page (no password in email).
6. Validate token, set a new password using Django validators, invalidate token and existing sessions as appropriate, and notify the user of a successful password change. Avoid replay and information leakage.
7. Log security events without saving the token or new password.

The ERD already defines `password_reset_token` and `password_reset_token_expires`, but the uploaded snapshot has no public reset endpoint and no operational email delivery. Implementation needs focused service, API, frontend, and security tests.

## 9. Exact code areas to inspect/change

| Code location | Planned work |
| --- | --- |
| `frontend/src/features/auth/registration.ts` | Required email and 1–7 digit School ID validation |
| `frontend/src/features/auth/RegisterPage.tsx` | Numeric-input UX, max 7 digits, validation messages |
| `backend/apps/accounts/serializers.py` | Authoritative ID/email validation for public registration |
| `backend/apps/accounts/models.py` | Review deletion constraints and existing reset-token fields; change only with schema approval |
| `backend/apps/accounts/registration_review.py` | Replace retained Rejected flow with safe audited notification-and-purge workflow |
| `backend/apps/accounts/registration_review_api.py` | Extend authorized list projection; planned bulk endpoints and error handling |
| `backend/apps/accounts/registration_review_urls.py` | Candidate bulk routes; keep isolated until approved |
| `backend/apps/accounts/urls.py` | Add independently reviewed public password-reset request/confirm routes |
| `backend/config/settings.py` and `backend/.env.example` | Environment-driven mail configuration and safe testing backend |
| `frontend/src/features/auth/` and `frontend/src/api/` | Forgot-password and reset-password screens/client |
| Focused backend/frontend tests | Validation, privacy, email delivery/retries, deletion/audit, bulk races, token security |

## 10. Acceptance tests and blocked release gates

- School IDs such as `0001234` validate and retain leading zeroes; alphabetic input and >7 digits fail on client and server.
- Invalid or missing applicant email cannot enter workflows that depend on email notification/recovery.
- Reviewer sees correct formatted names, status, dates, and no secrets.
- Approve/reject are denied without the exact effective permission, regardless of Django superuser status; Deny overrides remain enforced.
- Rejection does not leave login credentials or a blocked School ID after completed purge; notification and minimal audit remain available according to policy.
- SMTP failures/retries do not produce duplicate approvals, lost rejection notifications, or unaudited deletions.
- Bulk actions respect per-item eligibility, concurrency, authorization, partial failure, and bounded batch size.
- Forgot-password responses do not enumerate accounts; expired/used tokens fail; passwords are never emailed; sessions/tokens are invalidated correctly.
- Keep catalogue activation, live review URLs and feature flags disabled until separate governance and deployment approvals.

**Suggested implementation order:** (1) finalize scope/retention and email identity verification policy, (2) School ID/email validation, (3) safe email service and password reset, (4) audited reject/delete refactor, (5) authorized queue fields and bulk endpoints, (6) Admin UI, (7) isolated MySQL and browser end-to-end testing, (8) controlled activation approval.
