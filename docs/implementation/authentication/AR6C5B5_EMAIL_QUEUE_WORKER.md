# CTU-G Workspace — AR-6C5B.5 Email Queue Worker

**Date:** November 10, 2026  
**Stage:** Local development patch. **Not production activated.**  
**Upstream checkpoint:** AR-6C5B.4, commit `97722fa`, branch `ronald` (per developer's terminal output).

## Scope

This patch adds **new files only** to the existing `backend/apps/accounts/` package. It does **not** replace or edit `settings.py`, `registration_review.py`, `audit.py`, models, migrations, `full_schema.dbml`, or the existing outbox writer. There are no new database columns or tables.

The outbox writer from AR-6C5B.4 retains responsibility for saving the approved/rejected decision, exact audit receipt, and encrypted notification in the same MySQL transaction. This worker handles **delivery of already-recorded jobs only**.

## Worker state transitions

- **Pending (immediately) / Retry (due)** → **Leased**: short `SELECT ... FOR UPDATE SKIP LOCKED` transaction, new random 43-character token, increment attempt count, lease expiry. Send outside DB transaction.
- **Leased → Delivered**: Django backend returned acceptance count `1`; clear lease, store `delivered_at`. **This is backend acceptance, not proof of inbox delivery.**
- **Leased → Retry**: transient backend failure or unavailable decryption key; store a generic failure code and schedule exponential retry after 60, 120, 240, or 480 seconds (maximum 3600 seconds).
- **Leased → Dead**: invalid recipient/unsupported template/permanent recipient failure, or when maximum 5 attempts are exhausted.
- **Expired Leased**: another invocation can reclaim an expired lease. If it exhausted all 5 attempts, mark Dead.
- **Lease token fencing**: an old worker cannot finalize a job claimed by a later worker.

**Delivery semantics:** At least once, never exactly once. If SMTP accepts a message and the process dies before the DB acknowledgment, the next worker may resend it. The unique audit FK prevents duplicate *outbox records*, not duplicate SMTP deliveries.

## Security

- `WORKSPACE_OUTBOX_WORKER_ENABLED` **defaults to `0`** (read directly from the process environment). Delivery also requires `WORKSPACE_REGISTRATION_OUTBOX_ENABLED=1` through existing Django settings. Neither is enabled by this patch.
- Local console backend requires additional `WORKSPACE_OUTBOX_LOCAL_CONSOLE_ACK=1`: Django's console backend prints plaintext recipients and email bodies, so use **only a private local terminal**. Prefer `locmem` for automated tests.
- SMTP backend requires `WORKSPACE_EMAIL_SMTP_ENABLED` and additional `WORKSPACE_OUTBOX_SMTP_DELIVERY_APPROVED=1`. **Do not set this approval gate until institutional authorization and credential/key management reviews.**
- No credentials or KEKs are generated or written in source code, Git, or logs. Recipient is decrypted only for sending. Only static template version `1` is supported; unknown template versions are dead-lettered.
- The management command defaults to a read-only count and requires explicit `--deliver` for sending. No HTTP endpoint, scheduler, daemon, or implicit startup behavior exists.
- The error field receives generic codes only; no backend exception messages, recipient addresses, or decrypted content.
- The worker processes at most 100 jobs per invocation and imposes a 15-second email backend connection timeout to reduce the chance of a lease expiring in-flight.
- Rejected accounts remain inactive and retained. No account deletion or audit rewriting is performed.

## Required local checks

From `CTU-G Workspace/backend/`, with `.venv` activated:

```powershell
python manage.py check
python manage.py makemigrations accounts --check --dry-run
python manage.py test apps.accounts.test_registration_outbox_worker --settings=config.test_settings --noinput
python manage.py test apps.accounts.test_registration apps.accounts.test_password_reset apps.accounts.test_registration_review apps.accounts.test_registration_review_notifications apps.accounts.test_registration_rejection_retention apps.accounts.test_registration_outbox apps.accounts.test_registration_outbox_worker --settings=config.test_settings --noinput
python manage.py migrate --plan
```

The worker test suite uses the isolated `config.test_settings` MySQL test database, `locmem` email backend, and random temporary wrapping key. Never run these tests with development DB settings.

Read-only command (may be used while both delivery gates are OFF):

```powershell
python manage.py process_registration_outbox
```

**Do not run `--deliver` or turn on feature gates in the normal development workspace yet.** After formal activation approval, a trusted operator can run a bounded batch with `--deliver --limit 10`. There is no automatic repeat schedule; the production runner, monitoring, replay/dead-letter policy, key rotation/recovery, rate limits, and SMTP provider controls are separate sign-off items.

## Acceptance limits

The included tests check gate enforcement, read-only preview, worker success/failure, retry and backoff, stale-lease fencing, expired lease reclamation, max attempts, template validation, and encrypted recipient handling in the isolated test DB. **They do not establish production-grade concurrent multi-worker correctness**, operating-system crash recovery, provider deliverability, or institutional retention compliance. Do not claim live reliability from passing these tests alone.
