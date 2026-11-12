# CTU-G Workspace — Task 2 G1D-P0/P1
## Read-only protected-role inventory and disposable test-only role creation

**Status:** G1D-D1–D6 approved for read-only P0 and **disposable-MySQL P1 only**. This candidate is NOT a role initializer for the real `ctug_workspace` database, an operational Technical Super Admin bootstrap, or a governance authorizer. Owner-reported Windows acceptance passed on November 13, 2026; scoped Git review and commit remain pending.

**Baseline:** The developer last reported branch `ronald`, HEAD `6125286` (G1C committed), 876/876 backend regression tests passing, and `No changes detected` from the Django model migration check. Historical P0/G0 output showed one existing `Admin` role, **zero** `Technical Super Admin` records or assignments/grants, and six uninstalled proposed Core K permissions. These are **historical developer-reported results**; run the new P0 for current state before any decisions. Source was reconciled against the uploaded `CTU-G Workspace - Copy (2).zip` and the G0/G1A/G1B/G1C add-only candidates. Source on the user's Windows machine must be checked at the stated HEAD.

### Fixed architecture: exactly TWO application Admin levels

1. **Normal Admin** — `Admin` role, school operational permissions, no protected Access Control Management.
2. **Technical Super Admin** — **both active** `Admin` and protected `Technical Super Admin` roles, plus action-specific effective governance permission and independently approved evidence for a protected operation.

Django `is_superuser` is framework maintenance, **not a third application Admin level** and never an application authority bypass. Approvers, technical custodians and executors are duties, not extra application roles.

### Scope and files: exactly four new paths

1. `backend/apps/access_control/management/commands/report_g1d_p0_role_readiness.py` — exact-scope, SELECT-only local MySQL inventory: checks actual connected schema, protected role labels/aliases, assigned roles, role bindings, active direct governance overrides, proposed six Core K code presence and existing audit count. It refuses drift and cannot create a role. Backup and authorization readiness are **explicitly unverified**.
2. `backend/apps/access_control/tests_support/g1d_p1_dormant_role_test_only.py` — guarded **test-only** fixture creator: it checks exact `config.test_settings`, generated `test_ctug_registration_<16 hex>` schema, configured and actual connected DB, existing active canonical `Admin`, unchanged normal role initializer, absence of the technical role and protected aliases, proposed core metadata and direct governance overrides. **Only in that disposable schema**, it creates exactly one inactive `Technical Super Admin` fixture row with a clearly fictional description, without account assignments or permissions. A second call fails instead of quietly reusing state. Never import into live services.
3. `backend/apps/access_control/test_task2_g1d_dormant_role_contract.py` — isolated Django contract tests for the guard, zero grants/assignments, inactive status, aliases and wrong settings, absence of authority even if the role row exists, Django Superuser separation, and preserved `init_system_roles` behavior. Fixture writes are destroyed with Django's disposable MySQL test database.
4. This documentation — implementation scope, limitations and local commands.

**These files do not modify** `roles` in the real database; `init_system_roles.py`; any existing model, migration, route, permission catalogue, access evaluator, settings or frontend file; or `docs/database/full_schema.dbml`. They add no production/protected role creation command.

### Stage P0 — read-only local acceptance

From the `backend` directory with `.venv` activated:

```powershell
python -B manage.py report_g1d_p0_role_readiness --settings=config.settings --expected-db ctug_workspace --ack G1D_P0_READ_ONLY
if ($LASTEXITCODE -ne 0) { throw "G1D-P0 inventory failed; STOP and reconcile." }
```

Requires `config.settings` with `DEBUG=True`, MySQL loopback, configured DB `ctug_workspace`, actual `SELECT DATABASE()` equal to `ctug_workspace`, and acknowledgement. Reports counts only: no School IDs, account IDs, emails, tokens or passwords. It is not a dry-run of a live initializer and **does not check backup integrity**. If a protected role already exists, metadata/grants have drifted, or aliases appear, it stops. **Never use a P0 success as authorization for a real P1 write.**

### Stage P1 — disposable test-only role creation

```powershell
python -B manage.py test apps.access_control.test_task2_g1d_dormant_role_contract --settings=config.test_settings --noinput
if ($LASTEXITCODE -ne 0) { throw "G1D-P1 test-only checks failed; STOP." }
```

Run the module **only** under `config.test_settings`. It verifies the random schema name through `SELECT DATABASE()` before creating any fixture row, which is rolled back/destroyed by the test runner. The helper is never exposed through a Django command, API or UI, and it is not importable as a privilege service. All fixture role-creation tests run inside disposable MySQL. The tests deliberately show that an inactive role cannot confer permissions; they do not verify real approval identity, signatures or durable one-use consumption.

### Full regression, migration check and Git discipline

Enumerate individual `backend/apps/accounts/test*.py` and `backend/apps/access_control/test*.py` modules (package-only autodiscovery previously failed). Run `python -B manage.py test <modules> --settings=config.test_settings --noinput`. If the prior 876 tests are unchanged, expect that number **plus** this candidate's test cases; use the runner's actual count. Then:

```powershell
python -B manage.py makemigrations --check --dry-run --settings=config.settings
if ($LASTEXITCODE -ne 0) { throw "G1D model drift; STOP." }
```

Check `git branch --show-current` and HEAD `6125286` before extraction; check clean Git index and **absence** of the four new files. Validate ZIP membership; do not overwrite. After tests and documentation record, stage only the four exact new paths and run `git diff --cached --check`, inspect `git diff --cached`, and commit. Never stage the modified official ERD, `.env`, unrelated docs or teammates' files.

### Separate decisions BEFORE any real database role creation

- Explicit approval of the **exact live P1 command/payload**, intended target database and trusted actor/audit attribution.
- Verified backup/restore rehearsal and rollback plan; do not treat a successful `makemigrations --check` as a data backup.
- Clear treatment of protected role aliases, partial state and concurrent attempts; unique-key/serialization/recheck design for the real transaction.
- A real audit receipt with approved executor identity, and documented first bootstrap later. No `get_or_create` or arbitrary SQL workaround.
- Independent approval for each later stage: role metadata **P1**, evidence ledger/ERD **P2**, permission installation and staged inactive role bindings **P3**, first-account bootstrap **P4**, protected Access Control Management **P5**.

**Never auto-promote an existing Normal Admin or assume Django Superuser can bypass these gates.** No actual privileges may change during this checkpoint. The six Core K permission definitions are planning contracts only.

### Windows local acceptance record — November 13, 2026 (owner-reported)

These outcomes were provided from the developer's VS Code PowerShell terminal and were not independently obtained from the local Windows/MySQL environment:

- **P0 read-only inventory:** passed against local `ctug_workspace`. One canonical `Admin` role; zero `Technical Super Admin` role records, aliases, assignments, technical role bindings or active governance overrides. Zero of six proposed Core K codes installed; one active `access_control` service; 15 existing audit rows. The ordinary `init_system_roles` command remains unchanged. The report expressly did not verify backup/restore readiness, independent approval or any live-write authorization, and executed no database writes.
- **P1 disposable isolated tests:** 29/29 passed under `config.test_settings`; Django reported creation and destruction of the disposable MySQL test database.
- **Full Accounts + Access Control regression:** 905/905 tests passed across 42 test modules under `config.test_settings` in 326.444 seconds. Simulated RuntimeError logs did not fail tests; the disposable test database was destroyed.
- **Migration consistency:** `python -B manage.py makemigrations --check --dry-run --settings=config.settings` returned `No changes detected`.
- **Git scope before commit:** `ronald` at HEAD `6125286`; the four G1D paths are untracked and the index is empty. Existing modifications to `docs/database/full_schema.dbml` and unrelated untracked files remain outside this checkpoint.

**Acceptance status:** P0/P1 read-only/test-only checkpoint passed local verification. **Scoped Git review and commit are pending.** These results do not authorize creating the protected role in the real database, changing any grants or assignments, seeding the permission catalogue, or modifying the official ERD. A separate P1-live approval and verified recovery plan are still required.
