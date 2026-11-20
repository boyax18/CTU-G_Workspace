# CTU-G Workspace — AR-6C5B.2 Notification Outbox Design Review

**Document:** Technical design proposal, not an implementation or institutional approval  
**Date:** 2026-11-10  
**Branch checkpoint supplied by developer:** `ronald`, commit `f09b7e1`  
**Scope:** Registration approval/rejection emails only; no enrollment administration or change to role grants

## 1. Where the project stands

- **AR-6C4:** Registration validation and password recovery foundation, with earlier reported passing automated tests. Password recovery remains disabled by default; real email sending was not verified.
- **AR-6C5A:** Best-effort approval/rejection email using `transaction.on_commit()`. The 62-test backend regression suite passed in the local test database. This path is not durable across process death and has no retry mechanism.
- **AR-6C5B.1:** Five retention/audit safeguards and the combined 67-test backend suite passed locally. Rejected accounts are retained, inactive, and not automatically deleted.
- **AR-6C5B.2 (this document):** Reviewable *proposed* persistent outbox contract only. No Django model, migration, worker, key integration or live API activation has been implemented.

The official `docs/database/full_schema.dbml` is not changed. In the available reference snapshot its SHA-256 is `E4362BE913280AB6C23D5C66AF249FC1923FCCB1ACD7B6C2696F7EE95C19D4A0`; re-verify the actual workspace file before any approved amendment.

## 2. Recommended scope and explicit decisions

| Topic | Recommended contract | Approval status |
| --- | --- | --- |
| Storage | One new `registration_notification_outbox` table, initially managed by `apps.accounts` | Proposed only |
| Relation | Required, unique, `PROTECT` FK to `access_audit_logs.access_audit_log_id` (`int` PK) | Proposed only |
| Semantics | One outbox event for each committed review decision when outbox mode is enabled | Proposed only |
| Email target | Snapshot address at review time, encrypt it; never store plaintext in the outbox | Proposed only |
| Confidentiality | Per-event AES-256-GCM data key and nonce; wrapped data key stored separately from the managed wrapping key | Awaiting crypto/key service selection |
| Status | `Pending`, `Leased`, `Retry`, `Delivered`, `Dead`; `Delivered` means backend acceptance, not inbox delivery | Proposed only |
| Queue mechanism | MySQL transactional claim with `SELECT FOR UPDATE SKIP LOCKED` where verified; short lease, then send outside transaction | Proposed only |
| Retries | At most 5 attempts, bounded exponential backoff with jitter (example only, requires operational signoff) | Awaiting approval |
| Retention | Keep rejected account and audit records; no automatic deletion/anonymization. Define email ciphertext retention separately | **Institutional policy required** |
| Activation | Keep review API and worker disabled by default; require approved catalogue/permissions/governance | Not approved |

The proposed V2 DBML lives at `docs/database/proposals/AR6C5B_notification_outbox_PROPOSAL.dbml`. It intentionally adds `recipient_nonce`, `wrapped_data_key`, `recipient_erased_at`, and `template_version` to make the privacy and lifecycle contract explicit. The prior draft had a single encrypted blob and key version but did not specify enough information for a clear envelope-encryption implementation.

## 3. Transactional boundary: what must change in code later

The existing trusted `record_access_audit()` in `apps.access_control.audit` **deliberately returns `None`**. Do not select an ambiguous latest audit record or write raw audit rows in the registration service to find its ID. Implement a narrowly reviewed receipt-capable sibling that shares exactly the same input validation, transaction rollback behavior and append-only insert logic. Keep the existing `record_access_audit()` return contract unchanged for its other callers. Only the trusted registration review flow should call the new receipt-capable API and consume the exact inserted audit PK.

Within the **existing durable MySQL READ COMMITTED review transaction**, and only after role/permission checks and row locks:

1. Update the pending account to Approved or Rejected; assign only the requested Student/Instructor role if approved.
2. Insert the original immutable audit event using the reviewed receipt-capable helper; receive its exact PK.
3. If outbox mode is enabled, atomically insert one outbox row referencing that PK. Use allowlisted template identifiers and an encrypted snapshot of the address.
4. If address is absent or invalid for a historical account, create a `Dead` row with `last_failure_code='recipient_unavailable'`, **no recipient ciphertext**, and surface the issue through restricted operational metrics. Do not invent an address, reveal an applicant's details, or claim an email was sent.
5. If the outbox insert or encryption fails while enabled, fail the whole transaction; account status, role assignment and audit event must all roll back. This guarantees a durable notification disposition for every committed decision, **not** guaranteed receipt.
6. After commit, a separately gated worker can process due rows. Do not also run the AR-6C5A `on_commit` sender for the same event; the two paths are mutually exclusive.

**No SMTP/network I/O within the review transaction.** The existing review API must remain detached/disabled until governance and delegated permissions are approved. An outbox schema approval does not authorize API activation.

## 4. Email key management and privacy

- Use an audited cryptographic library and a concrete external key-wrapping service before writing production encryption code. Generate an independent random data key and 96-bit random GCM nonce for each event. Use `decision_audit_log_id` and template identity as authenticated associated data.
- Persist only ciphertext with authentication tag, nonce, wrapped data key, and a nonsecret key identifier. Master/wrapping keys must live **outside MySQL and Git**. Define key rotation, escrow, restoring backups, and loss-of-key behavior before migration.
- Disable debug logging for email internals. Never log raw recipients, passwords, reset tokens, rejection narratives, wrapped-key secret material, raw SMTP responses, or exception strings that may contain addresses.
- Minimize content: email only approval/rejection information and neutral support guidance. Unverified applicant email addresses are an existing operational risk; address verification and delivery policy must be decided before release.
- After an approved outbox retention period, erase ciphertext, nonce, wrapped key and key identifier, stamp `recipient_erased_at`, and retain only approved nonpersonal delivery metadata. **No retention duration is assumed.** Do not purge account/profile/audit rows as part of outbox cleanup.

## 5. State machine and concurrency

| Prior state | Trigger | Next state | Required safety check |
| --- | --- | --- | --- |
| Pending / Retry | Due and worker claims row | Leased | Row lock; set random lease token + expiry; increment attempt count |
| Leased | Backend accepts email | Delivered | Same lease token; clear lease and due time; set `delivered_at` |
| Leased | Retryable failure | Retry | Same lease token; sanitized code; bounded future due time |
| Leased | Permanent failure / attempt limit | Dead | Same lease token; sanitized code; no automatic retry |
| Leased | Expired lease | Leased (new worker) | Reclaim under lock with a new token; old worker cannot finalize |
| Pending | Recipient absent or invalid at insertion | Dead | No send attempt; no personal address stored |

Each claiming transaction must commit **before** a network send. The final status update is conditional on that worker's current lease token. Two workers cannot hold the same active lease. With SMTP, a crash after provider acceptance but before recording Delivered can produce a duplicate email; this system guarantees at-least-once *attempts*, not exactly-once external delivery. Use repeat-safe messages and include only neutral event IDs in permitted metrics.

`next_attempt_at`, `lease_expires_at`, and `delivered_at` use UTC. Pending/Retry require a due time; Leased requires token/expiry; Delivered/Dead are terminal and must not be automatically requeued. Application/database validation should enforce legal state combinations. Ensure MySQL 8.4 SQL types and generated Django migrations exactly match the approved DBML before applying anything.

## 6. Guardrails for implementation

- **Current state:** Nothing needs to be migrated or activated. No `makemigrations` or `migrate` command should be run for the outbox proposal.
- Proposed config flags (both default `False`): `WORKSPACE_REGISTRATION_OUTBOX_ENABLED` and `WORKSPACE_REGISTRATION_OUTBOX_WORKER_ENABLED`. Preserve existing review API/approval gates.
- Use existing verified `config.test_settings` and a fresh test database. Do not test on development records.
- When outbox mode is enabled, replace the AR-6C5A best-effort send path rather than sending a second email.
- Keep the outbox model within the Django migration registry; a separate Python module must be imported from models or else migration autodetection may miss it.
- Never change `docs/database/full_schema.dbml` or grant new permissions until there is explicit approval. Preserve the official ERD checksum before and after review.
- Follow the campus privacy officer's retention, appeal/reapplication and record-disposal decisions before any account purge endpoint or automated cleanup.

## 7. Mandatory acceptance tests before any release

1. Successful approval/rejection creates one linked audit + one outbox row; second decision creates neither.
2. Invalid reviewer, inactive service/role, explicit Deny, or rejected transaction creates no notification.
3. Failure during encryption/audit/outbox insert rolls back account, role, audit, outbox together.
4. Missing address yields an explicitly Dead notification disposition (no sensitive data), while decision remains audited.
5. Process crash after commit retains Pending/Retry row for next worker process.
6. Two workers cannot claim the same row at once; token/expiry prevent stale status updates.
7. Retry limit, transient/permanent failure mapping, delayed due time, and poison row alert work.
8. Envelope encryption decrypts only with authorized key access and correct authenticated associated data; corruption, key loss and rotation fail safely.
9. Recipient erasure is tested after an *approved* retention period, leaving permissible metadata only.
10. Same registration action is never sent through both best-effort callback and outbox.
11. Full existing registration, approval, API, access-control and password-reset regressions pass.
12. Worker runs least privilege, SMTP credentials stay outside Git, delivery metrics do not reveal PII.

## 8. Dependencies to decide before migrating

1. **Institutional approval:** Is an additional audit-linked outbox table authorized in the official ERD? Who approves migration?
2. **Cryptographic implementation:** Which managed wrapping-key/KMS provider will protect per-event data keys, and how are keys rotated and restored?
3. **Policy:** How long may encrypted recipients and delivery metadata remain? How will reapplications and rejected accounts be handled?
4. **Operations:** Worker hosting/cadence, retry cap, maximum lease, SMTP sender authority, incident alerts, and deliverability monitoring.
5. **Production safety:** Does email verification need to precede an Admin decision? Who resolves missing/incorrect recipients?

**Status after this package:** Design review prepared for owner approval. **Not an implemented outbox, not a migrated table, not a released feature.**
