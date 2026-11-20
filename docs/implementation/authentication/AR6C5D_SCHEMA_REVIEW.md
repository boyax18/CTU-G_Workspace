# CTU-G Workspace — AR-6C5D Background Bulk Registration Queue: Schema Review

**Review date:** November 10, 2026  
**Reference checkpoint:** `ef53dbe` on `ronald` (user-confirmed, pushed)  
**Source under review:** `docs/database/proposals/AR6C5D_BULK_QUEUE_PROPOSAL.dbml` (AR-6C5C package)  
**Recommended revision:** `docs/database/proposals/AR6C5D_BULK_QUEUE_REVIEW_v2.dbml`  
**Status:** Design recommendation only. NOT APPROVED for official ERD changes, Django models, migrations, or live deployment.

## 1. Review scope and provenance

The proposed AR-6C5D queue has TWO tables: `registration_bulk_jobs` and `registration_bulk_job_items`. It is separate from the previously approved and implemented `registration_notification_outbox` email-delivery queue. The available ERD snapshot and prior approved outbox table establish that `accounts.account_id` and `access_audit_logs.access_audit_log_id` are `int` keys; the new queue's `bigint` keys refer back to those `int` keys.

**Limitation:** The current on-disk `docs/database/full_schema.dbml` at user checkpoint `ef53dbe` is not accessible here. Prior uploaded snapshots and approved outbox design were reviewed. Before adopting any official-ERD amendment, inspect the live local file and confirm no overlapping tables, changed key types, naming conflicts or drift. Never overwrite that file from an older ZIP.

This feature processes registration decisions only, NOT academic enrollment or CTU's main enrollment records.

## 2. Recommendation

Approve the **two-table architecture in principle**, but do not migrate the original v1 proposal as written. The revised v2 proposal supplies missing due-time, response-idempotency, decision-receipt, and cancellation fields. The exact schema still needs project-owner review and an institutionally approved retention policy before production operation.

| Decision | Finding |
| --- | --- |
| One job per bulk submission | Appropriate, with actor-scoped idempotency and immutable selection snapshot |
| One job item per selected account | Appropriate; unique `(bulk_job_id, target_account_id)` prevents duplicates within one job |
| 200 account example | One job + 200 items; no attempt to lock 200 accounts in one transaction |
| Separate email outbox | Required; successful decisions create outbox rows via the existing secure review service, not directly from the bulk worker |
| Existing hybrid permissions | Must be re-evaluated per item, with active role, exact permission, Deny precedence and service checks; no superuser bypass |
| Live UI/API/routes | Remain disabled pending governance and explicit approval |

## 3. Changes recommended to the v1 proposal

1. Add **`request_fingerprint binary(32)`** to `registration_bulk_jobs`. A replay of the same actor's idempotency key must return the original job if the canonical submitted request matches, and must return a conflict if its action/rejection reason/selection specification differs. Re-resolving a changed All Matching filter must NOT silently create a different job for the same idempotency key.
2. Add **`selection_digest binary(32)`** to the job for a stable checksum of the sorted server-selected target PKs; the immutable `registration_bulk_job_items` still remains the authoritative snapshot.
3. Add **`next_attempt_at datetime`** to job items for scheduled transient-error retries and bounded backoff. `Failed` is a terminal failure; retryable items return to `Pending` with a future due time.
4. Add **`decision_audit_log_id int UNIQUE nullable`** to each item. A successful `Approved` or `Rejected` item must reference the exact immutable audit event for its committed registration decision.
5. Add **`Cancelled`** to item states and `cancelled_count` / `cancel_requested_at` to jobs to account for work never performed after cancellation.
6. Add an allowlisted **`stop_reason_code`** to jobs, and `(bulk_job_id, status)` / due-time indexes to support accurate progress counts and due-item selection.

## 4. Critical atomicity requirement: no double decisions after crash

The existing trusted `approve_registration()` / `reject_registration()` functions handle their own durable MySQL transaction, auditing and encrypted outbox insertion. A naive worker that does this:

```
call trusted review service -> COMMIT registration decision
then mark bulk job item Approved -> COMMIT job item
```

has an unavoidable crash gap. If the process dies between those commits, the account was approved but the job item may remain `Leased`; a retry could misattribute the outcome as `Skipped`, and job totals would be incorrect.

**Implementation requirement:** Extend the trusted review service through a carefully reviewed internal receipt/finalization callback or equivalent trusted composition so that the account state, base-role assignment (approval only), access audit row, encrypted outbox row and job-item `Approved`/`Rejected` status plus `decision_audit_log_id` commit **in ONE atomic transaction**. The callback must verify the current job-item lease token before committing; a stale worker must roll back without changing an account. Preserve the public single-review service's security policy and do not wrap an existing `transaction.atomic(durable=True)` block inside another atomic block without redesign.

The queue's claim step remains a brief separate transaction (`Pending`/expired `Leased` -> `Leased`), using MySQL row locks and a fresh random fencing token. The processing transaction must verify its token. Do not hold database locks during network/email operations; the email outbox worker is separate.

For `Skipped`, `Failed`, `Cancelled`, counters and result transitions need idempotent, transactionally consistent updates; counters can be derived or updated with compare-and-swap controls, never incremented blindly after retries. A retry after an uncertain outcome must reconcile the committed decision audit and item state before any new action.

## 5. Select All Matching (200 accounts example)

- UI sends a bounded, allowlisted filter specification, never a fabricated `select_all=true` privilege or an arbitrary SQL-like expression. Submission requires a valid authenticated session, CSRF, active approval/rejection permissions and a confirmation dialog with the action and requested scope.
- Server resolves the filter under current Admin visibility and pending-registration eligibility, sorts unique PKs and checks a configured cap (proposed pilot max **500**). Reject requests above the limit; do NOT silently truncate.
- Persist the job and all item IDs in one transaction. Once created, membership is immutable even if registrations or matching filters change. Recheck eligibility at processing time.
- Store only IDs, hashed digests, action, allowlisted reason and safe metadata; no names, student IDs, emails, exception details or recipient addresses in queue records.
- Prevent job ownership exposure: progress and cancellation endpoints require authenticated, currently authorized scoped access; not possession of a guessed job ID alone.
- A second Admin can review a target during processing. At most one review should commit due to the existing account lock and Pending-only preconditions; the losing item should become `Skipped` without another notification.

## 6. Job and item states

**Jobs:** `Queued` -> `Running` -> `Completed` (all terminal, no skipped/failures), `Partial` (terminal with skipped/failed), `Stopped` (security gate revoked, operator stop or infrastructure halt), or `Cancelled` (cooperative cancellation). If cancelled partway through, completed account decisions remain committed; untouched items become `Cancelled`. `Stopped` may contain pending items awaiting explicit authorized intervention; it must never auto-resume when authority is lost.

**Items:** `Pending` -> `Leased` -> (`Approved` / `Rejected` / `Skipped` / `Failed`); transient failures return to `Pending` with `next_attempt_at` and increasing `attempt_count`. Pending items can become `Cancelled` when allowed. Lease timeouts permit reclaim, but every finalization requires the current lease token.

Progress counters describe *terminal item outcomes*; pending/leased remainder is `selection_count - succeeded_count - skipped_count - failed_count - cancelled_count`. For rejection jobs, `succeeded_count` counts `Rejected` items. Verify invariants in tests and, where supported, MySQL check constraints.

## 7. Security, retention and operations to approve

- Actor authorization is NOT permanently delegated by a queued job. Recheck the originally requesting Admin's active account, active Admin role, service status and exact effective permission before every decision, including explicit Deny precedence; stop on revocation.
- Workers are trusted internal executors, NOT a new high-privilege role, bypass or publicly exposed endpoint. The API and worker must each have separate off-by-default flags and bounded concurrency.
- `idempotency_key_hash` is computed from a high-entropy validated key, scoped by `requested_by_account_id`; never log the raw key. Canonicalize request fingerprint deterministically and resolve the existing idempotency record before re-running an All Matching filter.
- Backoff, claim lease length, timeout, maximum attempts and cap must be configurable and tested on MySQL; default trial values are engineering proposals, not deployment authorizations.
- No plaintext personal data in queue failure codes or logs. `accounts` and `access_audit_logs` foreign keys should use protective deletion semantics consistent with existing retention. Rejected accounts must remain inactive and retained as previously designed.
- Institution must approve a job/result data retention schedule, who may view progress and the operational policy for cancelled/stopped jobs. Do not invent retention periods or delete audit records.
- Email outbox delivery remains at-least-once; queue success means account decision committed, not email accepted/delivered.

## 8. Verification plan before migration

1. Check active local `docs/database/full_schema.dbml` and SHA-256; compare current account/audit PK types, outbox inclusion and existing relations. Preserve original file and calculate a reviewed diff.
2. Approve exact v2 table definitions and operational safeguards. **Owner approval for the conceptual feature is not equivalent to migration approval.**
3. Implement Django models and migration as separate review-only patch. Inspect `sqlmigrate` against MySQL 8.4 and table/constraint/index names before applying. Use isolated test DB first.
4. Test concurrent job creation with repeated idempotency keys and conflicting payloads; All Matching snapshot stability and >cap rejection.
5. Test two workers claiming same item, expired leases, stale lease tokens, crash after reviewed decision, audit/outbox atomicity, actor role revoked mid-job, stop/cancel, skips on stale accounts, accurate counters and retries.
6. Test 200-account fixture with workers in a bounded staging environment; verify all terminal item counts reconcile and no duplicate approvals or outbox rows appear.
7. Keep public routes, Admin approvals, bulk worker and external email disabled until a separate release/security signoff.

## 9. Suggested safe local review commands

From the CTU-G Workspace repository root:

```powershell
git status --short
Get-FileHash "docs/database/full_schema.dbml" -Algorithm SHA256
Select-String -Path "docs/database/full_schema.dbml" -Pattern '^Table (accounts|access_audit_logs|registration_notification_outbox|registration_bulk_jobs|registration_bulk_job_items)\b'
git diff -- "docs/database/full_schema.dbml"
```

These commands are read-only. No `makemigrations` or `migrate` is needed for a design review.

## 10. Decision needed before code or ERD changes

**Requested approval:** Approve the two-table AR-6C5D *review v2* schema for a **review-only** official ERD amendment and Django model/migration preparation. This would not authorize running migrations, registering routes, enabling the worker or live Admin bulk processing. Current status: **not yet granted**.
