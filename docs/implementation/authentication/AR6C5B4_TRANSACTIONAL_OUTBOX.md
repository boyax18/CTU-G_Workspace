# CTU-G Workspace — AR-6C5B.4 Transactional Outbox Writer

**Development checkpoint:** November 10, 2026  
**Owner scope:** Encryption and atomic notification-intent creation only  
**Release state:** Disabled by default; **no worker, no active Admin review API, no SMTP delivery**

## Implementation

- The existing `accounts.0003_registration_notification_outbox` migration and official ERD are **unchanged**. The outbox table has already been created on the developer's local MySQL database as an earlier approved migration.
- `apps.access_control.audit.record_access_audit()` preserves its existing return value of `None`, validation rules, and rollback semantics. New `record_access_audit_receipt()` shares the same private implementation and returns the *inserted audit ID* for trusted transactional callers. The receipt is provisional until commit.
- When `WORKSPACE_REGISTRATION_OUTBOX_ENABLED=1` **and** the existing guarded registration-review decision is authorized, the same MySQL transaction writes the account decision, optional Student/Instructor role, audit event, and encrypted outbox row. If any step fails, the transaction rolls back.
- The outbox branch **replaces**, rather than supplements, the original best-effort `on_commit` email path. With the outbox flag `0`, the existing behavior stays unchanged.
- Approved/rejected email addresses are encrypted as snapshots at the moment of the decision. Email bodies are **not** persisted. The eventual worker must use approved static templates.
- Existing historic accounts with absent or invalid email produce an outbox row in `Dead` state, with `recipient_unavailable` and no recipient envelope. No address is synthesized.
- The outbox writer never sends email, never grants permissions, and does not change any routing or dashboard behavior.

## Development encryption contract

- Per notification: generate a fresh 32-byte data encryption key (DEK), encrypt address with **AES-256-GCM**, fresh 12-byte nonce, and authenticated associated data binding audit ID + template code + version.
- Wrap the DEK with an independently provisioned 32-byte key encryption key (KEK) using AES-256-GCM with a **separate** random 12-byte nonce. Store wrapped nonce + ciphertext + 16-byte tag inside `wrapped_data_key`.
- Only ciphertext, nonce, wrapped DEK and key version are stored in MySQL. KEKs must stay in secure environment/secret management outside Git, SQL exports and source files.
- For isolated development only, `WORKSPACE_OUTBOX_KEK_V1_B64` is the standard Base64 encoding of exactly **32 random bytes**. `WORKSPACE_OUTBOX_ACTIVE_KEY_VERSION=v1` is the default key identifier. If missing/invalid, the writer fails and rolls back rather than using Django `SECRET_KEY` or writing plaintext.
- Decryption is an **internal library function only** for a future trusted worker; never expose it through an HTTP endpoint, audit log, management listing or untrusted serializer. Tampering/unknown versions fail closed.
- **Production deployment remains blocked:** env-only local key storage is not an institutionally approved KMS/HSM/key rotation/recovery design. A managed key provider and restricted worker identity must be reviewed first.

## Default-off configuration

```env
WORKSPACE_REGISTRATION_OUTBOX_ENABLED=0
WORKSPACE_OUTBOX_ACTIVE_KEY_VERSION=v1
```

Never commit the actual `WORKSPACE_OUTBOX_KEK_V1_B64` value. Do not enable the outbox in development except during controlled testing while the governance and review API gates remain disabled. The isolated test suite generates its own temporary key.

The new dependency is in `backend/requirements-outbox.txt`; install it in the virtual environment with:

```powershell
python -m pip install -r requirements-outbox.txt
```

This supplementary requirements file must eventually be merged into the team's canonical requirements/lockfile before release.

## Installation and test acceptance

From project root, preview then apply the packaged installer (it operates on source files only):

```powershell
python "$patch\scripts\apply_ar6c5b4.py" --repo "."
python "$patch\scripts\apply_ar6c5b4.py" --repo "." --apply
```

From `backend/` with `.venv` activated:

```powershell
python manage.py check
python manage.py makemigrations accounts --check --dry-run
python manage.py test apps.accounts.test_registration_outbox --settings=config.test_settings --noinput
python manage.py test apps.accounts.test_registration apps.accounts.test_password_reset apps.accounts.test_registration_review apps.accounts.test_registration_review_notifications apps.accounts.test_registration_rejection_retention apps.accounts.test_registration_outbox --settings=config.test_settings --noinput
python manage.py migrate --plan
```

Acceptance requires rollback verification for key unavailability and outbox insertion failures; no duplicate best-effort callback; encrypted row and authenticated decryption; missing address dead status; preservation of all prior review/audit/permissions tests. All tests must use `config.test_settings`, never local development data.

## Still deliberately unimplemented

1. Durable worker claiming and sending (lease fencing, safe retries, bounded attempts, poison alerts).
2. Managed production KEK storage, rotation, backup and recovery.
3. Institutional retention and erasure of ciphertext/keys; rejected account retention and lawful disposal.
4. Production SMTP and delivery monitoring, including inbox-delivery semantics.
5. Production activation of review/approval API, permissions, bulk actions, and worker gates.

**Do not run `makemigrations` without `--check --dry-run`, and do not execute `migrate` for this patch.** No new table or column is required.
