# CTU-G Workspace — AR-6C5B: Rejection Retention and Reliable Notification Design

**Feature:** AR-6C5B  
**Document class:** Design and security approval draft  
**Status:** Test-only safety checkpoint packaged; transactional outbox **proposed, not implemented**  
**As of:** 2026-11-10  
**Existing remote checkpoint:** `a0baae2` on `ronald` (user-reported)  

## 1. Current implementation: facts vs pending decisions

The existing registration review service approves or rejects pending Student/Instructor requests within a protected MySQL transaction and writes an access audit event. AR-6C5A optionally schedules informational email using `transaction.on_commit` after successful commit. The previously reported combined regression result is **62/62** passing. **That is not guaranteed email delivery**: an in-memory callback may be lost on process termination and has no retry queue.

The existing `accounts` table has `Pending`, `Approved`, `Rejected`, `is_active`, `reviewed_by`, `reviewed_at` and `rejection_reason`. Rejected accounts remain inactive and retain their credential hash, email and linked user profile. `access_audit_logs`, `users` and some role records have `PROTECT` foreign-key relationships; a direct hard delete of reviewed accounts is unsafe and generally blocked. Neither the official ERD nor the existing application models contain a durable email outbox.

**Decisions now retained:** Never delete a rejected account during the review transaction; never purge profiles, hashes, email, or audit data automatically. Do not enable registration-review URLs or grant any catalogue roles/permissions as part of this phase.

## 2. Safe rejection lifecycle (now)

1. Keep the existing rejection transaction, `request_status='Rejected'`, `is_active=False`, reviewer/time/code, and audit event.
2. Do not assign a role to a rejected account; reject a second decision.
3. Treat the account as **retained**, not erased or anonymized. Present no false deletion claim to an applicant.
4. Prohibit new cleanup/purge endpoints or batch delete jobs until the institution has approved a retention policy, relevant privacy notices, foreign-key strategy, and proof that required audit history remains intact.
5. Review whether reapplication should create a new account or reopen a rejected request. Existing school-ID uniqueness currently prevents a fresh duplicate account without a deliberate reapplication policy.

### Outstanding institutional policy questions

- How long should a rejected registration (including hashed credentials and user profile) be retained?
- Is there a right/need to reapply with the same School ID? Should that be a controlled reset, appeal, or fresh request?
- Does the school require permanent audit references by account ID or a minimized archival/tombstone identity?
- When should email addresses be removed, and which campus office may approve the disposal?

Do not invent a retention period or silently choose a deletion policy.

## 3. Transactional outbox proposal (schema approval required)

**Why a new table is needed:** AR-6C5A `on_commit` is best-effort; it does not guarantee a durable record across crashes. `user_notification_reads` in the official ERD is a read-state table, not an outbound email queue. Overloading immutable `access_audit_logs` as a mutable retry queue would violate its audit purpose.

See `docs/database/proposals/AR6C5B_notification_outbox_PROPOSAL.dbml` for a **standalone proposed table**. The official `docs/database/full_schema.dbml` is intentionally untouched; the proposal must not be migrated until its ERD/schema contract is approved.

**Proposed atomic flow:**

1. Validate Admin role, exact effective permission, service gates and target eligibility using existing locked transaction.
2. Mutate the account, assign the requested base role if approved, and record the audit event.
3. If notifications are enabled and a valid recipient exists, **insert exactly one outbox event in the SAME database transaction** using a unique audit-event reference. The current `record_access_audit` returns no identifier, so an owner-reviewed API adjustment or narrowly scoped retrieval strategy is required; do not query an ambiguous "latest" audit event.
4. Commit. If the outbox insert fails, roll back the decision instead of silently reporting success when reliable delivery is contractually required.
5. A separate authorized worker leases eligible events using MySQL row locks (`SELECT ... FOR UPDATE SKIP LOCKED` where supported), commits the lease, sends the email outside the transaction, then atomically marks Delivered or schedules Retry with bounded exponential backoff and jitter.
6. Recover expired leases and alert an operator on Dead events. Never log recipient addresses, tokens, passwords, freeform rejection reasons or raw SMTP errors.

**Delivery semantics:** At-least-once *attempts*, not exactly-once email delivery. A crash after SMTP acceptance but before the Delivered write can cause duplicate emails. Gmail SMTP does not supply a general idempotent-send guarantee. Use non-sensitive, repeat-safe copy and stable event IDs, then explicitly document duplicates as possible.

**Privacy:** The proposal uses envelope-encrypted recipient storage rather than a plaintext email column; encryption key rotation, separate key storage, data retention, disposal, and access controls must be specified and tested before this schema is approved. Do not store passwords, reset tokens or custom private rejection text in the outbox. The worker must run with least privilege.

## 4. Proposed worker and retry contract

- **Leasing:** Only Pending/Retry due records or expired Leased records; concurrent workers cannot hold the same lease. Validate token on final update to reject stale workers.
- **Boundaries:** Fixed maximum attempts (propose 5; subject to approval), backoff with randomized delay and bounded upper limit; Dead items are reviewed by an authorized operator, never blindly retried forever.
- **Observability:** Track queue age, due backlog, delivered/failed counts, retry counts and expired leases without recording recipient PII.
- **Fail closed:** Review API remains gated; the worker and new table must have separate deployment controls. No automated cleanup of rejected registration data.
- **Data lifecycle:** Define a separate outbox retention period; discard encrypted recipients after delivery/retention expires while preserving a minimal delivery receipt if legally justified.

## 5. Test plan (AR-6C5B)

**Ready to run now, no schema change:** The packaged `test_registration_rejection_retention.py` tests safe status, audit/profile persistence, protected account deletion, reviewer audit protection, second-decision rejection, and confirms that personal data is still retained. These tests **do not implement deletion**.

**Required before outbox implementation:**

- Audit + outbox + review all roll back on any failed write.
- Exactly one event per committed decision; no event on invalid or repeated decision.
- Process restart retains due events.
- Concurrent workers do not concurrently claim one event.
- Lease timeout and retry policy work; send failure cannot rewrite committed review.
- Marking Delivered and handling failures is guarded by current lease token.
- Missing recipient has explicit, testable behavior.
- Key version/encryption, renewal, redaction, authorized worker and eventual encrypted-recipient disposal are tested.
- Duplicate-email scenario is documented and the template is safe to repeat.
- Complete existing registration review/API and permission regression suites still pass.

## 6. Gate checklist and progress

| Checkpoint | Current state |
| --- | --- |
| AR-6C4 recovery and frontend testing | Previously reported passing; disabled by default |
| AR-6C5A post-commit email | Previously reported 62/62 combined tests; best-effort only |
| AR-6C5B safe rejection retention | New non-destructive tests provided; **not yet run in user's local MySQL** |
| AR-6C5B durable outbox schema | Proposed; **no migration/activation** |
| AR-6C5B reliable email worker | Not implemented |
| Rejection deletion/anonymization policy | Awaiting institution approval |
| Bulk approval/rejection | Not started |
| Real Gmail SMTP | Not configured or verified |
| Admin review API release gates | Still disabled |

**Do not call AR-6C5B complete yet.** It has reached a safe design/test checkpoint; durable delivery and disposal are blocked by explicit schema and retention decisions.
