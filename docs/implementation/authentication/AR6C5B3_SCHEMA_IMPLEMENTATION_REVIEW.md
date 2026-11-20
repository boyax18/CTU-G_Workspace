# CTU-G Workspace — AR-6C5B.3 Outbox Schema Implementation Review

**Scope:** Development-only schema approval, November 10, 2026
**Owner decision:** Approved adding the v2 `registration_notification_outbox` table to the official ERD and preparing a Django model/migration **for review**.
**Release status:** **Not migrated**, no retry worker, no encryption service, no live Admin review API, no new permission grants.
**Reference proposal:** `docs/database/proposals/AR6C5B_notification_outbox_PROPOSAL.dbml`, v2 SHA-256 `ed8c746b8cb87c9d6c3700746891ea8340c08397876946eca836e0594907f2cd`.

## Approved changes

- Add precisely one `registration_notification_outbox` table to `docs/database/full_schema.dbml`, retaining all existing tables and references.
- Link `decision_audit_log_id` uniquely to the existing `access_audit_logs.access_audit_log_id` (Django OneToOneField, `PROTECT`).
- Register one new Django model in the existing `accounts` app, with custom MySQL fields for exact `VARBINARY`, `BINARY(12)`, native ENUM and second-precision DATETIME mapping.
- Draft an `accounts.0003_registration_notification_outbox` migration depending on `accounts.0002` and `access_control.0003`.
- Add no application endpoints, audit-helper changes, email sends, jobs, key material, seeds, grants, flags, account deletion, or enrollment features.

The official ERD baseline was verified against previously pinned SHA-256 `e4362be913280ab6c23d5c66af249fc1923fccb1acd7b6c2696f7ee95c19d4a0`. The installer checks this baseline (with only line-ending normalization permitted) and aborts on genuine content drift. It modifies **only** the official ERD table/reference insertions and adds a single outbox model import at the end of `backend/apps/accounts/models.py`.

## Mapping: DBML → Django

| Proposed DBML | Django field |
| --- | --- |
| `bigint` primary key | `BigAutoField` |
| `int` unique audit FK | `OneToOneField(..., on_delete=PROTECT)` |
| `varchar(64)` template and key labels | `CharField(max_length=64)` |
| `varbinary(1024)` | `MySQLVarBinaryField(max_length=1024)` |
| `binary(12)` | `MySQLFixedBinaryField(max_length=12)` |
| `varbinary(512)` | `MySQLVarBinaryField(max_length=512)` |
| `enum(Pending, Leased, Retry, Delivered, Dead)` | Existing `MySQLEnumField` |
| `datetime` | `MySQLDateTimeSecondsField`, second precision |
| `timestamp DEFAULT CURRENT_TIMESTAMP` | Existing `MySQLTimestampField`, `CurrentTimestamp` |
| Two query indexes | Explicit `outbox_due_idx` and `outbox_lease_idx` |

Two additional CHECK constraints express the existing design's numeric invariants: `attempt_count >= 0`, `template_version >= 1`. **Review generated MySQL 8.4 SQL before applying**. Other invariants, such as status-dependent lease fields and complete envelope-key sets, must be implemented and tested together with the *future trusted service/worker*, and if feasible later reinforced with additional schema constraints by separate approval. Merely creating this table must **not** be mistaken for complete outbox functionality.

## Deliberate deferrals

1. **No automatic mailing:** AR-6C5A best-effort `on_commit` remains the only existing sender when explicitly gated. Durable outbox mode is not wired. Do not run both send paths for the same review decision.
2. **No new audit helper:** `record_access_audit()` continues returning `None`. The receipt-capable sibling required for an exact audit link will be a separately tested code change.
3. **No crypto material:** Envelope encryption implementation and managed external key wrapping/rotation/recovery are not selected. Do not write plaintext recipient addresses into the new columns.
4. **No retention assumption:** Institutional policy for encrypted email data and delivery metadata remains unset. Rejected accounts stay inactive and retained; historical audit records remain protected.
5. **No production enablement:** Existing review/approval and notification gates remain disabled, and the worker does not exist.
6. **No production migration:** The supplied hand-authored migration is for inspection and isolated-test review. It has **not** been executed against any database in this package.

## Before any migration approval

- Verify the current project has no competing `accounts.0003` migration and that the official ERD matches the pinned baseline.
- Run `python manage.py check`, `python manage.py makemigrations accounts --check --dry-run`, `python manage.py showmigrations accounts`, and `python manage.py sqlmigrate accounts 0003` using the intended settings; verify generated SQL types, table/constraint/index names, FKs and timezone handling.
- Compare the hand-authored draft against Django's autodetector and the MySQL 8.4 test database. Do not apply to the development database just to test the draft.
- Add isolated MySQL migration/constraint tests before allowing the migration, then repeat all account and access-control regressions.
- Obtain separate permission to execute the migration after the SQL and tests pass, including a rollback/backup plan.

**Approval boundary:** This document records **development schema approval only**. Production encryption, retention, retries, SMTP delivery, and Admin API activation remain blocked.
