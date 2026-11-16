# Account email uniqueness

**Subsequent lifecycle change:** Future eligible rejections now remove the
applicant account/profile and release its credentials for ordinary registration,
while retaining rejection evidence and notifications. See
[rejection deletion implementation](REJECTION_DELETION_IMPLEMENTATION.md).
The inspection, migration and test record below describes the original email
uniqueness commit `c13f5c7` and its earlier retained-account reapplication policy.

Reviewed on 2026-11-15 (Asia/Manila). Source and migration implementation only;
the live migration has **not** been applied. School ID remains the unique login
identifier (`USERNAME_FIELD = "school_id"`).

## Inspection and reconciliation

The original model and migration `accounts.0001` defined
`EmailField(max_length=150, null=True, blank=True)` without uniqueness.
`AccountManager` lived in `models.py` and used Django's domain-only lowercase
normalization. The public serializer already required an email even though
the model permitted NULL. That distinction is preserved.

A SELECT-only inspection inside `START TRANSACTION READ ONLY` confirmed:

| Property | Existing development database |
| --- | --- |
| Server/schema | MySQL 8.4.13 / `ctug_workspace` |
| Email type/default | `varchar(150)`, nullable, default NULL |
| Character set/collation | `utf8mb4` / `utf8mb4_unicode_ci` |
| Email constraints | None |
| Existing unique identifiers | `account_id` primary key; `school_id` unique |
| Account migrations applied | `0001`, `0002`, `0003` |
| Accounts / NULL emails | 3 / 1 |
| Blank/whitespace-only emails | 0 |
| Normalized duplicate groups | 0 |
| Values needing normalization | 0 |

Both MySQL `GROUP BY LOWER(TRIM(email))` under the actual column collation and
Python `strip().lower()` over non-null emails found no collisions. Python also
checked surrounding Unicode whitespace. No email addresses or credentials were
printed. No records required correction; no account was deleted, merged or
overwritten.

Inspection covered the manager/model, registration serializer/service/view,
executor dispatch and transaction ownership, School ID login, password recovery,
reapplication API/service, approval/rejection, notifications/outbox, bootstrap,
sandbox account creation, account tests, frontend registration/reapplication
payloads, actual indexes and all three existing account migrations.

## Implemented policy

Non-null addresses use Python `email.strip().lower()` across the entire address.
This is a deliberate account identity policy, including the local part. No
provider-specific dot or plus-address rewriting is performed. Empty strings
become NULL through the manager/model; public registration still requires a
valid nonblank email.

The shared helper is used by the manager, registration serializer and model
`save()`. Partial saves that omit email do not touch the stored email, so approval
and password-only writes retain their existing field scope. Current account
creation and reapplication pathways use these saves. Future import/bulk/SQL
writers must canonicalize explicitly: Django `QuerySet.update()` and bulk writes
do not invoke model `save()` ([Django documentation](https://docs.djangoproject.com/en/5.2/ref/models/querysets/)).

The field now has `unique=True`, retaining length, nullability and blank handling.
The existing case-insensitive MySQL collation enforces uniqueness for database
inserts even if application validation is bypassed. Its existing accent-insensitive
comparison semantics are retained. MySQL permits multiple NULL values in a
nullable unique index ([MySQL 8.4 documentation](https://dev.mysql.com/doc/refman/8.4/en/create-index.html)).

Registration still hashes passwords and attempts an atomic account/profile
creation. After MySQL error 1062 rolls back the savepoint, the service checks for
an existing School ID or canonical email and returns the same HTTP 202 body as
a new request. It does not reveal which field conflicted or change the owner.
Unrelated integrity/database failures remain a generic HTTP 503. The database
constraint resolves races; an application existence check is not the authority.

Rejected accounts retain their email reservation. Verified reapplication may
retain the same account's email or choose an available one. A collision rolls
back the account/profile changes and returns the same acknowledgement as success,
leaving the rejection cycle and link available for another submission. A nested
savepoint keeps an executor-owned ledger transaction usable after that conflict.
The existing account ID, School ID, review history and audit attribution remain
part of the existing lifecycle. No previous-credential fields were introduced.
Remote dispatch, writer gates and deployment policies remain in place.

## Migration SQL review and deployment boundary

`accounts.0004_account_email_unique` depends only on the existing account `0003`.
Its frozen, SELECT-only preflight refuses blanks, noncanonical values, duplicate
values under Python normalization or the actual database collation, unsupported
database engines, and a column without a case-insensitive collation. It never
repairs data. If it refuses, stop and obtain owner-directed reconciliation.

The forward DDL from `sqlmigrate accounts 0004` is exactly:

```sql
ALTER TABLE `accounts` ADD CONSTRAINT `accounts_email_200aa879_uniq` UNIQUE (`email`);
```

The disposable migration test also verifies the actual reverse DDL:

```sql
ALTER TABLE `accounts` DROP INDEX `accounts_email_200aa879_uniq`;
```

Reverse `sqlmigrate` on the **unmigrated live schema** reports no-op because
Django introspects whether the index exists. The reverse execution assertion was
therefore performed after forward migration in a disposable schema. Both
directions preserve every account field value, including passwords and IDs.
The RunPython preflight appears as a Python operation in SQL output and must be
reviewed separately; `sqlmigrate` does not execute it.

No live DDL, grants, privileged-account changes, executor installation, email
delivery or GitHub push was performed. The user's request authorizes this code,
migration preparation, isolated testing and local commit. Live deployment remains
a separately controlled DBA release; it requires backup/recovery review,
coordinated account-writer quiescence, repeat preflight and approved migration
credentials. MySQL DDL is not transactionally reversible. Deploy all writers with
the canonical policy before reopening writes; do not rely on a stale inspection
to replace the deployment preflight. Review index-build duration/locking for the
deployment's actual table size. The current small development table is not a
production performance assessment.

`docs/database/full_schema.dbml` is untouched by this work; its existing local
changes belong to the user and are excluded from the commit. Its observed
SHA-256 remains `BEFB42DF64A6D10B1AA0828A8E2A0A62FF3167B2B35DADCFA973FECF6D54C6D1`.
The owner will amend the official ERD manually. No protected-role schema or
authorization approval is implied by this account-email change.

## Verification

- Final focused MySQL suite: 130 tests passed in 36.480 seconds (email invariants,
  registration, manager, reapplication, login and recovery).
- Additional final migration/reapplication checks: 11 tests passed, including
  exact reverse DDL and conflict recovery within a simulated executor-owned
  transaction. This test context does not grant live executor authority.
- Full applicable backend suite: 1,468 tests passed in 191.334 seconds.
- Django `makemigrations --check --dry-run`: no changes detected.
- Django `check`: no issues; `git diff --check`: passed.
- Focused frontend registration/reapplication/recovery/session: 26 tests passed.
- Full frontend `npm test`: two existing failures in unchanged frontend files:
  `registration-layout.test.mjs` expects registration text absent from the current
  page, and `registration-review-api-contract.test.mjs` forbids the dashboard's
  existing review API gate reference. No frontend file differs from HEAD.

Coverage includes accepted unique emails; case/space duplicate rejection with
identical public responses; raw SQL case-duplicate rejection; multiple NULLs;
retained School ID uniqueness; no orphan profiles; password-only update scope;
approval/rejection, audit and notification regressions; reapplication retaining
its own email; unchanged rejected state after collisions; fail-closed unavailable
executor; and two genuinely simultaneous inserts on separate MySQL connections
using different roles and School IDs, resulting in one account and profile.

Tests use the existing isolated runner with unpredictable
`test_ctug_registration_<16 hex>` schemas and reject database reuse. No new
database users or grants are needed. Normal backend discovery has existing
namespace-package and script import-path issues; the complete run enumerates
every test module explicitly, with `backend/scripts` on that process's import path:

```powershell
# From backend/
$env:PYTHONPATH = (Resolve-Path scripts).Path
[string[]]$testModules = @(rg --files apps scripts -g 'test*.py' |
    ForEach-Object { ($_ -replace '\\','.' -replace '/','.' -replace '\.py$','') })
& .venv/Scripts/python.exe manage.py test @testModules --settings=config.test_settings --noinput --verbosity=1
```

Read-only fingerprints taken during and after the backend regression run matched
for `accounts` (3 rows), `users` (1), `account_roles` (1), `access_audit_logs` (15),
`registration_notification_outbox` (0), and `django_migrations` (24). Live email
indexes remain absent and the account migration head remains `0003`.
Further deployment and the official ERD update are pending owner/DBA action.

## Changed files

| File under `backend/apps/accounts/` | Change |
| --- | --- |
| `email_identity.py` | Shared trim/lowercase/NULL policy |
| `models.py` | Nullable unique field; manager and model save normalization |
| `serializers.py` | Canonical registration input before validation |
| `services.py` | Non-enumerating database email-conflict handling |
| `reapplication.py` | Conflict rollback and executor savepoint compatibility |
| `password_reset.py` | Update the recovery-contract comment; behavior retained |
| `migrations/0004_account_email_unique.py` | Frozen read-only preflight and unique DDL |
| `tests.py` | Replace the former non-unique/domain-only expectation |
| `test_email_uniqueness.py` | API, database, concurrency and migration coverage |
| `test_task1_reapplication.py` | Reapplication collision/own-email/executor tests |

This report is the only changed documentation file. Existing unrelated workspace
changes are excluded from the commit.
