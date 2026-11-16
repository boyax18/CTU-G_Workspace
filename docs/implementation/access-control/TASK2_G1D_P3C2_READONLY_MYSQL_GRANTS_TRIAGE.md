# CTU-G Workspace — Task 2 G1D-P3C2: current MySQL credential/grant triage

**Source checkpoint:** P3C1 committed `a636a91` on branch `ronald` (based on uploaded source at `211326a`).
**Status:** Add-only, read-only DEVELOPMENT CANDIDATE. This is not the real writer fence or permission to deploy privileged provisioning.

## Why this increment exists

The G1D-P3C1 AST inventory found 14 direct ORM mutation sites across 118 source files, but code locations are not MySQL principals. The existing `simulate_fenced_writers=True` argument is a synthetic assertion, not a fence.

G1D-P3C2 adds a narrowly scoped, **read-only query** against the *currently connected local development MySQL account* (`SHOW GRANTS FOR CURRENT_USER()`). It classifies visible grant lines without printing them or any usernames. Dangerous, unknown, and role-based grants require manual DBA reconciliation. Its release status is **always `BLOCKED`**, even when only SELECT/USAGE appears; a single-account query cannot prove exclusive or comprehensive writer controls.

## Exact add-only files

1. `backend/apps/access_control/tests_support/g1d_p3c2_grants_triage_test_only.py` — pure Python fail-closed grants parser; never considers any observation release approval.
2. `backend/apps/access_control/management/commands/report_g1d_p3c2_current_grants.py` — explicitly guarded, `config.settings` / loopback / `ctug_workspace` report command; only `SELECT DATABASE()` and `SHOW GRANTS FOR CURRENT_USER()`.
3. `backend/apps/access_control/test_task2_g1d_p3c2_current_grants.py` — 31 pure offline contract tests.
4. `docs/implementation/access-control/TASK2_G1D_P3C2_READONLY_MYSQL_GRANTS_TRIAGE.md` — limits and next operational controls.

No `.env`, `.gitignore`, official `docs/database/full_schema.dbml`, models, migrations, access-control grants, admin roles, or live protected commands are modified.

## Local acceptance

From the `backend` folder, run the unit tests with disposable settings:

```powershell
python -B manage.py test apps.access_control.test_task2_g1d_p3c2_current_grants --settings=config.test_settings --noinput
```

After that, run the report against the exact local development DB only if comfortable inspecting **the current MySQL credential's permissions**:

```powershell
python -B manage.py report_g1d_p3c2_current_grants --settings=config.settings --expected-db ctug_workspace --ack P3C2_READ_ONLY_CURRENT_USER
```

This command **never changes database state**. It prints only aggregated classifications and constant release block; never post raw `SHOW GRANTS` or usernames to chat. Lack of access to see other principals, roles and accounts is expected.

Finally, run the explicit module-by-module Accounts + Access Control full regression under `config.test_settings`, run `makemigrations --check --dry-run --settings=config.settings`, and stage exactly the four new paths. Baseline: 1,125 backend tests after P3C1; proposed pure offline additions: 31.

## What remains before a real writer fence

- Owner/DBA inventory of **all** MySQL users, host-specific grants, mandatory/default/activated roles, global and schema/table privileges, stored routines/triggers/events and DEFINER/SQL SECURITY settings; MySQL root/operator/backup/migration credentials and external programs must be explicitly identified. Querying only CURRENT_USER cannot prove these.
- DBA-approved narrow per-operation credentials and privilege matrix; ordinary application/web/worker identities must not hold protected metadata INSERT/UPDATE/DELETE or DDL rights during a release.
- Maintenance window, identified and drained competing sessions, independently attested host/DB admission boundary, verified read-only preflight/after-state, and emergency halt/recovery handling. Django transaction/row locks do not constrain outside writers.
- Separate operational approvals for any GRANT/REVOKE/CREATE USER/role provisioning, production migrations, key enrollment, live application role creation, account assignments or privilege promotion.
- Fresh protected backup and successful restore rehearsal that covers any subsequently approved ledger tables. Historical 17-table rehearsal does not cover future schema.

**No release is authorized by this patch**. Exactly two application-level Admin tiers remain Normal Admin and Technical Super Admin; Django `is_superuser` remains framework-only. Do not enable `prepare_g1d_p1_protected_role --apply`.
