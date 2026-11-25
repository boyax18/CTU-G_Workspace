# CTU-G Workspace — Registration Decision Notifications

**Feature ID:** AR-6C5A / AR-6C5B
**Document type:** Technical feature specification and verification record  
**Status:** Durable decision notifications implemented and tested; decision routes remain gated/unmounted and are not production-released
**Last reviewed:** 2026-11-23
**Scope:** Mandatory durable email notification for individual and bulk Student/Instructor registration decisions.

## Assisted email recovery for existing accounts (25 November 2026)

Legacy accounts approved before OTP registration have no email proof, so password recovery refuses them (D-21, unchanged).

| Situation | Path |
| --- | --- |
| Can sign in | My profile → Email verification → Send verification code → enter code. Proof is recorded only after the correct code. |
| Cannot sign in | Operator: Account directory → account → **Assisted email recovery** → attest identity → Send recovery code. Holder: Forgot Password → **I have an account recovery code** → email + code → new password. |

- **Operator API:** `POST /api/v1/admin/school-accounts/<id>/assisted-recovery/` with `{"identity_confirmed": true}`, mounted only in the loopback `-Local` URLconf.
  - Requires the exact permission `accounts.school_accounts.assist_recovery`, re-checked under the WF-02.05 lock order, plus an active Admin assignment.
  - Refuses the operator's own account (`own_account`) and Admin, Technical Super Admin or framework targets (`privileged_account`): mailbox control alone must never restore privileged access, and no privileged policy exists yet.
  - Also refuses `inactive_account`, `no_operational_role`, `email_missing` and `already_verified`, and enforces the resend wait (`recovery_wait`).
  - Audits `account.assisted_recovery.authorize`. The response never contains the code.
- **Public API:** `POST /api/v1/auth/account-recovery/verify/` with `{"email", "code"}`.
  - Every failure returns the same `recovery_code_invalid` 400, using the password-reset throttles and identity budget.
  - Success records `email_verified_at`/`email_verified_address` and audits `account.assisted_recovery.verified`.
  - It then issues the existing single-use reset ticket (HttpOnly cookie), so the password is set by the normal `reset-password` call under D-21.
- **Binding:** the code lives in `account_email_verification` with purpose `assisted`, digest-separated from self codes. It is bound to the current address, so an email change invalidates it. Same 10-minute expiry, 60 s resend, 5-attempt lockout and 30-minute window as the signed-in flow.
- **Gates:** `WORKSPACE_ASSISTED_RECOVERY_ENABLED` (on only in the `-Local` decision profile) and `WORKSPACE_PASSWORD_RESET_ENABLED`. Inert until migration `accounts 0008` is applied and the permission is provisioned and granted through governance.

## Security mail outbox, email verification and delivery diagnostics (24 November 2026)

**Durable security mail.** Password-reset codes, the password-changed notice and email-verification codes now go through a durable table, `security_mail_outbox` (migration `accounts 0007`). It replaces the in-memory daemon queue, which lost mail on restart and never retried.
- The OTP is sealed with AES-256-GCM under the existing outbox key (`WORKSPACE_OUTBOX_KEK_V1_B64`, v1, not regenerated). The AAD binds the row token, kind and account. Plaintext codes are never stored or logged.
- Rows move `Pending → Leased → Accepted`. A temporary SMTP failure moves a row to `Retry` with backoff from 30 s up to 10 min. A row becomes `Dead` after 5 attempts or on a permanent 5xx/recipient refusal. Claims use `SELECT … FOR UPDATE SKIP LOCKED` with a 120 s lease, and every finish is fenced by the lease token.
- Before each attempt the worker re-checks the challenge. A code that has expired or been replaced by a newer one is marked `Expired`/`Superseded` and is never sent. On every terminal state the sealed secret is erased.
- After commit, the request kicks a background sender. The `-Local` watch worker (`process_registration_outbox --watch`) also drains due rows, so pending mail survives a restart. The reset API still answers a neutral `202`.

**Signed-in email verification.** `GET/POST /api/v1/auth/email-verification/`, `…/request/` and `…/confirm/` require a signed-in session and CSRF, and use the registration OTP policy and rate limits.
- The code goes to the account's current address. The code digest is bound to the account, the challenge and that address, so changing the email invalidates the code.
- Only a correct code records `email_verified_at` and `email_verified_address`. Wrong codes count toward a lockout.
- An `account.email.verified` audit event is written with no state snapshot: no address, code or digest.
- The D-21 password-reset eligibility rule is unchanged. A verified account simply meets it.
- The UI is the Email verification card on My profile.
- Accounts that cannot sign in need a separately authorized assisted-recovery procedure (not implemented).

**Diagnostics.** The `ctug.email` logger writes one line per event with a correlation ID: `request_accepted`, `account_ineligible`, `otp_created`, `email_queued`, `smtp_attempt`, `smtp_accepted`, `temporary_failure`, `permanent_failure`, `retry_scheduled`, `expired`, `superseded`, `recipient_unconfirmed`. Each line carries the outbox id, the attempt, the Message-ID, and a masked recipient (`ab***@domain`), never a code or secret. `manage.py email_delivery_report` is a read-only summary of both outboxes.

**`smtp_accepted` means Gmail accepted the message for relay. It is not proof that the message reached the inbox; arrival is always `recipient_unconfirmed` until the recipient confirms.**

**Delivery evidence (25 November 2026).**
- **Provider reply:** real SMTP now goes through `email_design.TracedSMTPBackend` (Django's backend plus the `DATA` reply). `smtp_accepted` lines carry `reply=250_2.0.0_OK_<time>_<queue id>_-_gsmtp`, so each message has Gmail's own acceptance, not just Django's count. `EMAIL_BACKEND` keeps its approved value, so the delivery gates are unchanged.
- **Receipt proof:** `recipient_confirmed` is logged when the code from that exact message is entered correctly: My profile verification, Forgot Password verify, and Student/Instructor registration verify. It shares the original correlation ID. A registration code's ID is derived from the stage's keyed code digest. Notices without a code (password changed, decisions) stay `recipient_unconfirmed`.
- **Durable trace:** with `WORKSPACE_LOCAL_EMAIL_DELIVERY=1`, the `-Local` profile also appends the trace to `.local/ctug-dev/logs/email-trace.log` (git-ignored). The server and the worker share it, and it survives launcher restarts. `backend.log` is still overwritten on every start.
- **One message, end to end:** `manage.py email_delivery_report --trace <corr>` prints the outbox row, its final known state (`queued`, `processing`, `retry scheduled`, `permanently failed`, `expired`, `superseded`, `SMTP accepted; receipt unconfirmed` or `receipt CONFIRMED (code redeemed)`) and every trace line for that ID. Decision rows use `dec-<outbox id>`.
- **Finding a message in Gmail:** search the recipient mailbox with `in:anywhere rfc822msgid:<Message-ID without angle brackets>`. That covers Inbox, every tab, Spam and Trash.

## Branded email design (24 November 2026)

All CTU-G Workspace emails share one design in `backend/apps/accounts/email_design.py`. That covers the registration OTP (Student and Instructor), the password-recovery OTP, the password-changed notice, and approval and rejection, including each applicant's separate email from a bulk decision.

- **Structure:** multipart `alternative(text/plain, text/html)`, with no images of any kind. The plain-text fallback keeps its established wording. There are no remote images, web fonts, scripts or tracking.
- **No embedded logo (25 Nov 2026):** the campus logo used to travel inline (`multipart/related`, `cid:ctug-logo`). From the campus Gmail sender, those messages were accepted by Gmail (250 OK, in Sent, no bounce) but never reached the recipient, in any folder. Owner-authorized single-variable tests to the same mailbox showed:
  - plain text arrived;
  - the OTP plain text arrived;
  - the same branded HTML without the logo arrived;
  - the identical message with the logo did not.

  The logo was therefore removed. `email_assets/ctug-logo.png` is kept but unused. Do not add images back without a real inbox-delivery test.
- **Layout:** table-based with inline CSS, a 600 px card and a phone media query; forest-green header, emerald accents, white rounded card, footer identifying CTU-G Workspace.
- **OTP:** one run of digits at 38 px bold monospace with visual letter-spacing only, so copying yields exactly the six digits. It is never in a link, image URL or the inbox preview text. The expiry and a security reminder are shown, and recovery emails contain no links.
- **Decisions:** approval shows a success pill and the login button; rejection shows a respectful message, the reason, the fact that registration data was removed, and the option to register again with the same CTU-G ID and email.
- **Greeting:** OTP emails greet by first name when known. Decision emails stay neutral because they render only the immutable decision snapshot (no account lookup).
- **Safety:** every dynamic value is HTML-escaped. Senders keep a module-level `send_mail` (same signature) so failure handling, retries and tests are unchanged. OTP generation, validation, expiry, rate limits, the outbox, encryption, audit and SMTP settings are unchanged.


## Current implementation status — 23 November 2026

This update supersedes the historical best-effort design and checklist below. The approval and rejection services now require the existing durable outbox, a usable active encryption key and a valid recipient before making a decision. The encrypted recipient, individual audit record and decision-specific outbox row are written atomically with the decision. Rejection preserves its outbox row while deleting the rejected account and registration profile in the same transaction. The old post-commit best-effort email path cannot substitute for or bypass the outbox.

The API response reports `notification: queued`; this confirms only durable queuing, not delivery. The worker distinguishes `Pending`, `Leased`, `Retry`, `Delivered` and `Dead`; delivery is completed only at `Delivered`, while `Dead` is terminal failure. SMTP operation and production delivery are not verified. Local tests use synthetic records, a disposable MySQL test database and the in-memory email backend.

Bulk decisions use explicit unique account IDs, at most 20 per request, and the existing locked single-applicant service independently for each applicant. Each committed decision has its own audit and encrypted notification row. The UI presents confirmation and per-applicant outcomes; an uncertain result stops processing and is not automatically retried. The endpoint remains detached from normal URL configuration; backend/frontend bulk and mutation gates remain off by default.

No real applicant/account data was mutated, no notification was sent through SMTP, and no new Human Approval or production authorization is recorded. For the current API shape and route status, see [the Account Management API contract](../../api/AR-6C-registration-review-api-contract-proposal.md); for focused test evidence, see [the test results](../../testing/TEST_RESULTS.md).

## Historical AR-6C5A design record — 10 November 2026 (superseded)

## 1. Purpose and scope

Notify a registration applicant after an authorized CTU-G Workspace Admin has approved or rejected a pending Student/Instructor account request. **This feature extends the existing review service; it does not replace its security controls or enable the Admin review API.** Email messages are informational and contain neither passwords nor sensitive rejection details.

This phase **does not** implement guaranteed delivery, deletion of rejected accounts, a transactional outbox, bulk decisions, approval UI activation, new permissions, or an ERD change.

## 2. Implemented components

| Component | Source location | Responsibility |
| --- | --- | --- |
| Review service | `backend/apps/accounts/registration_review.py` | Existing approval/rejection transaction, permission checks, role assignment and audit; now schedules optional email |
| Notification helper | `backend/apps/accounts/registration_notifications.py` | Plain-text messages and post-commit email attempts |
| New notification tests | `backend/apps/accounts/test_registration_review_notifications.py` | Tests commit timing, approval, rejection, disabled setting, missing email, audit rollback, mail failure and duplicate decision |
| Existing review tests | `backend/apps/accounts/test_registration_review.py` | Existing review authorization, role assignment, Deny precedence and rollback checks |
| Existing review API | `backend/apps/accounts/registration_review_api.py` | Remains protected by separate review/approval feature gates; routes remain detached |

The notification helper calls Django `transaction.on_commit(...)` using the primary database connection. The callback is registered **after** the review's account-state and audit writes, so no email is attempted for a transaction that rolls back.

## 3. Approval and rejection workflow

### Approval

1. The existing review service requires `WORKSPACE_REGISTRATION_APPROVAL_ENABLED` and validates a persisted eligible actor, active services, an active Admin role assignment, and the exact effective `accounts.registration_requests.approve` permission.
2. It locks/rechecks relevant MySQL records and confirms the target is a valid Pending, inactive Student/Instructor request with no assigned role.
3. It changes the account to `Approved`, activates it, assigns **only** the requested base role, and writes an access audit event in the same transaction.
4. **If** the optional notification flag is enabled and the target has an email, it registers an `on_commit` callback.
5. After the transaction commits, the helper tries to send a plain-text approval message stating the applicant may sign in with their School ID and password.

### Rejection

1. The same review protections apply, using the exact `accounts.registration_requests.reject` permission and a permitted nonsensitive rejection code.
2. It changes status to `Rejected`, leaves the account inactive, stores reviewer/time/reason code, and records the rejection audit event.
3. After commit, the helper attempts to send a neutral *registration not approved* email if notifications are enabled and an email is available.
4. **The rejected account is retained**; this implementation performs no hard deletion, anonymization or archival.

The review API also requires the separate `WORKSPACE_REGISTRATION_REVIEW_API_ENABLED` gate and approved registration-review route wiring before HTTP callers can use it. The code currently remains **inactive for users** pending governance authorization.

## 4. Notification behavior and failure semantics

| Situation | Behavior in current AR-6C5A draft |
| --- | --- |
| Decision transaction commits and notification is enabled | Register a callback; attempt email after commit |
| Review/audit fails and transaction rolls back | No email callback should execute |
| Notification feature disabled | No notification callback registered |
| Applicant has no usable email | Notification skipped; approved/rejected decision remains valid |
| Email backend fails after commit | Error is logged without raw exception details; **database decision is not rolled back** |
| Same account is decided a second time | Existing service denies the second decision; no second email |
| Process crashes after commit but before send | Notification can be lost; **no retry queue exists** |

**This is best-effort notification, not guaranteed delivery.** The callback lives in application memory and is not itself persisted. A durable transactional outbox, operational retry mechanism, and approved data/retention design would be required before making reliable-delivery claims or tying rejection deletion to email completion.

## 5. Configuration and privacy

The helper reads `WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED` via `getattr(settings, ..., False)`, so it **defaults to False even if no explicit declaration was added**. The AR-6C5A README proposes adding this optional explicit setting in `backend/config/settings.py`:

```python
WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED = (
    os.environ.get("WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED", "0") == "1"
)
```

Do not turn it on in a normal environment while the underlying review feature and API are awaiting approval. The developer must **confirm whether this explicit line was added locally**; the most recent Git status showed only the three review/notification Python files changed.

Email delivery uses Django's configured backend. With `WORKSPACE_EMAIL_SMTP_ENABLED=0`, the configured backend is console-only; messages are written to the Django server console, **not sent to Gmail**. The tests explicitly use Django's in-memory email backend. Console output can contain recipient addresses and must not be published. Never commit mailbox passwords or `.env` files.

## 6. Verified testing as of 2026-11-10

| Verification | User-reported result | Scope |
| --- | --- | --- |
| Django system check | Passed; 0 issues | Imports/configuration |
| New notification tests | **7/7 passed** | Isolated MySQL-backed test suite |
| Combined regression tests | **62/62 passed** | Public registration, password reset, registration review and notifications |
| Real SMTP/Gmail delivery | **Not tested** | Mailbox and network delivery not configured |
| Live Admin approval/rejection API | **Not enabled** | Feature gates and route wiring still withheld |
| Guaranteed notification delivery | **Not implemented** | No durable outbox/retries |

Commands used from `backend/`:

```powershell
python manage.py check
python manage.py test apps.accounts.test_registration_review_notifications --settings=config.test_settings --noinput
python manage.py test apps.accounts.test_registration apps.accounts.test_password_reset apps.accounts.test_registration_review apps.accounts.test_registration_review_notifications --settings=config.test_settings --noinput
```

Test settings create and tear down a separate MySQL test database. The **62-test run is a targeted regression set**, not a claim that every backend suite or the inactive review API's full coverage has been rerun.

## 7. Governance, audit and future development

The existing review service relies on active `accounts` and `access_control` services, dynamic permissions with Deny precedence, a valid Workspace Admin assignment, MySQL transaction locking and an audit record written atomically with the decision. A Django framework superuser is **not** a bypass for these application permissions.

- [x] Add plain-text approval/rejection notification helper.
- [x] Schedule messages using `transaction.on_commit`.
- [x] Verify no email is sent on transaction rollback and that mail failure does not undo a committed decision.
- [x] Pass 7 notification tests and 62 combined backend regression tests.
- [ ] Review local settings and confirm the intended default-disabled notification flag.
- [ ] Obtain institutional approval for the review API, permission catalogue and activation gates; do **not** grant live permissions automatically.
- [ ] Design a **durable outbox** and retry/observability policy if reliable delivery is required.
- [ ] Decide compliant retention/anonymization/deletion for rejected accounts while preserving required audit relationships; do **not** hard-delete the existing account directly.
- [ ] Implement protected bulk approval/rejection with individual authorization, audit and failure semantics.
- [ ] Add complete Admin review UI fields and test controlled end-to-end operations.
- [ ] Configure and verify real email sending before production release.

**Release classification:** AR-6C5A implementation and targeted regression testing passed locally; **not ready for activation or production use**. No database migration or official ERD edit was introduced by this patch.
