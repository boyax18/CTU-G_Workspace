# CTU-G Workspace — AR-6C5D approved ERD amendment review

**Owner approval:** November 10, 2026  
**Status:** Approved for official ERD text amendment and Django model/migration **review only**. Not approved for migration execution, live API/worker activation, or production emails.  
**Starting ERD SHA-256:** `0CDE2A267BBC18F702701CA63D606F39AE0320D0D51FF23E91CCAE3CA4DB1FF6` (verified by project owner).  
**Reference bulk review Git commit:** `ef53dbe` on `ronald`; the earlier AR-6C5C test suite passed 115/115.

## Scope and data design

AR-6C5D adds two separate tables to the existing 9+ table CTU-G Workspace ERD:

| Table | Role |
|---|---|
| `registration_bulk_jobs` | One actor-scoped, idempotent request, including action, selection digest, counters, cancellation and status |
| `registration_bulk_job_items` | Immutable membership snapshot, one selected account per item, with lease fencing, retry scheduling and audit receipt |

No existing table is replaced or deleted. An example 200-account selection produces one job record and 200 items. The existing `registration_notification_outbox` remains responsible for email notifications. These two new tables handle **registration reviews only**, not CTU main-system enrollment.

## Foreign keys and protection

- `registration_bulk_jobs.requested_by_account_id` -> `accounts.account_id` (`int`, PROTECT).
- `registration_bulk_job_items.bulk_job_id` -> `registration_bulk_jobs.bulk_job_id` (`bigint`, PROTECT).
- `registration_bulk_job_items.target_account_id` -> `accounts.account_id` (`int`, PROTECT).
- `registration_bulk_job_items.decision_audit_log_id` -> `access_audit_logs.access_audit_log_id` (`int`, nullable UNIQUE, PROTECT).

Unique `(requested_by_account_id, idempotency_key_hash)` prevents actor-scoped duplicate jobs. Unique `(bulk_job_id, target_account_id)` prevents duplicate membership within a job. The audit reference is one-to-one, preventing a decision audit event from being attached to multiple items.

## Guarantees that depend on APPLICATION CODE (not only the schema)

1. The current Admin's active role, effective exact permission, Deny overrides, and relevant service status must be rechecked before **every** account decision; queued jobs never become durable authorization.
2. One account decision, relevant account-role assignment, append-only audit, encrypted outbox entry, and `registration_bulk_job_items` finalization **must commit in a single DB transaction**. The trusted existing review service needs an internal callback/refactor to make that possible; its current durable transaction cannot be naively nested.
3. Workers claim briefly with row locks and unpredictable lease token. All finalization must verify current lease token; expired workers cannot overwrite results.
4. Transient errors back off with a future `next_attempt_at`, while terminal failures remain terminal. Prevent infinite retries.
5. `decision_audit_log_id` must be populated for `Approved` and `Rejected` items; enforce it in service code and tests. A database CHECK on a foreign-key column may conflict with MySQL referential-action restrictions, so the draft deliberately avoids that particular CHECK.
6. Progress counters reconcile: `selection_count = succeeded_count + skipped_count + failed_count + cancelled_count + outstanding_items`, with no double-counting on lease reclaim/retry.
7. For Select All Matching, freeze server-selected account IDs at job submission. The request fingerprint must include the *submitted* action/filter specification; same actor+idempotency key with a different payload must return conflict.
8. Cooperative cancellation never reverts previously committed approvals/rejections. Revoked authorization must stop processing; do not auto-resume a stopped job without reviewed intervention.
9. Do not log personal email addresses, tokens, account private data, or raw infrastructure exception text. Do not auto-delete rejected accounts or audit history. Retention rules need institution approval.

## Review-only artifacts

- Approved DBML fragment: `docs/database/proposals/AR6C5D_BULK_QUEUE_APPROVED_FOR_REVIEW.dbml`.
- Guarded official ERD append script: `scripts/ar6c5d/apply_approved_bulk_schema.py`.
- Detached draft models: `review_only/backend/apps/accounts/bulk_queue_models.py`.
- Detached draft migration: `review_only/backend/apps/accounts/migrations/0004_registration_bulk_queue.py`.

**Blocking checks for later migration approval:** Inspect actual running model and migration heads, review generated SQL on current MySQL 8.4, verify FK PK type match, test integrity and migration rollback on isolated test database, performance-test 200 selections, verify safe job/item state transitions and permissions, approve operational limits and retention policy. No production activation is included.
