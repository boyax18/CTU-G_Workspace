# CTU-G Workspace — Registration Decision Notifications

**Feature ID:** AR-6C5A  
**Document type:** Technical feature specification and verification record  
**Status:** Draft implementation with passing automated tests; **disabled by default / not production-released**  
**Last reviewed:** 2026-11-10  
**Scope:** Best-effort email notification after an authorized Student/Instructor registration approval or rejection.

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
