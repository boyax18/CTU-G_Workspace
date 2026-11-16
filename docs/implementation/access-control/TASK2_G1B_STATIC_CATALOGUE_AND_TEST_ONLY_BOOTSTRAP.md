# CTU-G Workspace — Task 2 G1B Catalogue and Bootstrap Contract

**Status:** G1B-D1–D6 approved **for planning, read-only/static contracts and disposable test-only implementation only**. This package is a review candidate; Windows acceptance tests have passed as reported by the project owner, while scoped Git review and commit remain pending. The implementation is NOT a live governance authorization mechanism.

**Development discipline:** Inspect → Reconcile → Approve (G1B-D1–D6, limited scope) → Implement (this add-only candidate) → Test (owner-reported local verification passed) → Document (acceptance recorded) → Commit (pending) → Continue (later separate approval).

**Reference Git checkpoint:** User reported branch `ronald` and HEAD `cf1f113` after G0/G1A commit, 769/769 Accounts + Access Control backend tests passed under isolated MySQL settings, and no migration drift. The operator must verify the actual current branch/HEAD before extracting these files. This authoring environment has NOT connected to the user's Windows/MySQL database or independently tested against the current Git working tree.

**Source reconciliation:** The source snapshot `CTU-G Workspace - Copy (2).zip`, in particular `backend/apps/access_control/catalogue/v2_0.json`, `models.py`, `services.py`, and `delegation.py`, plus the approved G1B-D1–D6 proposal and previous G0/G1A files. These new files do not change the pinned v2 manifest or the official ERD.

## Approved design boundaries

- Exactly two application Admin profiles: **Normal Admin** (`Admin` role) and **Technical Super Admin** (`Admin` + protected `Technical Super Admin` role). The separate Django `is_superuser` maintenance flag NEVER grants application Technical Super Admin authority.
- The **six Core K definitions** are approved at the paper/static-contract level only: `access_control.catalogue.read`, `access_control.role_permissions.manage`, `access_control.account_permissions.manage`, `access_control.effective_permissions.inspect`, `access_control.audit.read`, `access_control.admin_assignments.manage`.
- `access_control.role_permissions.manage` and `access_control.account_permissions.manage` are **ordinary scoped B2 mutation capabilities**, not blanket permission to edit protected role templates, technical grants or protected access-control state. Any eventual protected operation needs dual-role composition, exact effective permission, independently approved durable evidence, target-scope policy, properly locked state, and audit.
- For these six proposed codes, the pinned v2 **default binding proposal** lists only `Technical Super Admin`. This is **not** an activation, provisioning authorization or approval of the entire 95-definition/106-binding v2 proposal. Normal Admin's other historical `access_control.*` school-only proposals are OUTSIDE this six-code decision and must not be silently changed.
- `access_control.diagnostics.read` is optional, not core K; historical `access_control.role_assignments.manage` stays retired; protected recovery, initializers and governance-grant codes remain blocked.
- First Technical Super Admin: only a separately nominated and verified existing Approved/active Admin account, with distinct institutional approver, technical custodian and executor, bound to exact environment, version, change, before-state digest and short expiry; a **simulation cannot verify real identities**. No account, including the current Normal Admin or Django Superuser, is nominated or promoted by this implementation.
- Durable one-use approval evidence, real locking, last-effective-operator quorum, backup/restore, migrations (if ever authorized), provisioning and recovery are **not implemented or authorized**.

## Add-only files (exactly four)

1. `backend/apps/access_control/tests_support/g1b_catalogue_test_only.py` — pure Python static exact-match validator for the six-code v2 planning subset; reads (but never modifies) the existing manifest file. Includes a fictional, in-memory first-bootstrap blueprint predicate that only accepts a disposable test-schema label; NOT a production approval service or credential check.
2. `backend/apps/access_control/management/commands/report_g1b_catalogue_static.py` — filesystem-only static verification command requiring an explicit acknowledgement. No ORM, no MySQL cursor, no DB reads, no state mutation.
3. `backend/apps/access_control/test_task2_g1b_catalogue_contract.py` — 48 tests; static manifest negative cases, simulated bootstrap refusal cases, and disposable MySQL fixture cases for A+G composition, explicit permission, direct Deny precedence and framework superuser separation. The test module refuses normal settings.
4. This documentation file.

The existing `backend/apps/access_control/catalogue/v2_0.json` is **read-only source material**, NOT included in the candidate ZIP. No existing source files are overwritten by the ZIP. The new candidate imports the previous test-only helper solely in its test module. Normal endpoints and existing permission evaluation remain unchanged.

## G1B static inspection — safe local command

From the backend directory with venv activated:

```powershell
python -B manage.py report_g1b_catalogue_static --settings=config.settings --ack STATIC_G1B_ONLY
if ($LASTEXITCODE -ne 0) { throw "G1B static contract or pinned v2 proposal drift. Stop." }
```

Expected: `G1B STATIC-ONLY CATALOGUE CONTRACT PASSED`, six exact definitions, planned Technical Super Admin-only bindings for these codes, and no DB operations. If the command detects a manifest conflict/collation variant or different version, **STOP**; do not auto-repair or overwrite the canonical v2 proposal.

## G1B disposable MySQL tests

```powershell
python -B manage.py test apps.access_control.test_task2_g1b_catalogue_contract --settings=config.test_settings --noinput
if ($LASTEXITCODE -ne 0) { throw "G1B isolated test failure. Stop." }
```

Expected: **48 tests** in a generated `test_ctug_registration_...` MySQL database that Django creates and destroys. Do not run this module under `config.settings` or with any normal/live database. Its module-level guard fails closed, and fixture setup independently checks the connected database name. Fixture role/permission records are fake test data, not live metadata installation.

## Full regression, migration consistency and review

Only after the static and isolated tests pass, run the previously validated module-by-module test enumeration for Accounts and Access Control. If the prior 769 tests remain unchanged and the new 48 run, expect **817 tests**, but use the actual test-runner output as the authoritative count.

```powershell
python -B manage.py makemigrations --check --dry-run --settings=config.settings
if ($LASTEXITCODE -ne 0) { throw "Unexpected migrations. Stop." }
```

Check `git status --short`, `git diff --cached --name-status`, `git diff --cached --check`. Stage **only** the four G1B files, and commit **only after** the owner reports acceptance output. Preserve unrelated files and the modified `docs/database/full_schema.dbml`; do not stage it.

## Windows acceptance results — 2026-11-13 (owner-reported)

The project owner supplied the following VS Code PowerShell output from branch `ronald`, HEAD `cf1f113`; these results are from the owner's local machine, not an independent connection from the authoring environment:

- **Static catalogue contract:** `report_g1b_catalogue_static --settings=config.settings --ack STATIC_G1B_ONLY` passed; pinned `catalogue-v2.0 / v2.0-review-1`; six exact Core K definitions; proposed Technical Super Admin-only bindings for those six codes; no database access or writes reported.
- **G1B isolated security tests:** 48/48 passed using `config.test_settings`; Django reported creation and destruction of the test database.
- **Full Accounts + Access Control regression:** 817/817 passed across 40 test modules in 125.334 seconds under `config.test_settings`; logged simulated `RuntimeError` messages did not cause failures.
- **Migration consistency:** `makemigrations --check --dry-run --settings=config.settings` returned `No changes detected`.
- **Git boundary at verification:** branch `ronald`, HEAD `cf1f113`, four new G1B paths untracked, no staged files. The modified official `docs/database/full_schema.dbml` and unrelated untracked files were outside the intended commit.

**Acceptance outcome:** The static/test-only G1B checkpoint passed local checks. This evidence does **not** authorize governance seeding, elevated accounts, protected write APIs, role grants, migrations or activation. Scope review and a local commit remain separate steps.

## Not solved by passing tests

- The static report verifies the pinned planning manifest on disk, NOT current live DB catalogue rows, real grants or signer identities.
- The fictional bootstrap blueprint can be satisfied by invented IDs and an in-memory `consumed=False`; it does not verify approval signatures, persist evidence, prevent cross-process replay, enforce transactional locking, nominate a beneficiary or implement first-bootstrap operations.
- Live **G1B Core K** metadata creation, role creation, role bindings, account promotion, protected API routes, approvals ledger, operational grants, migration, recovery, session invalidation, email changes, and UI remain **separately blocked**.
- Choosing a durable evidence ledger (official ERD-reviewed MySQL tables versus external approved tamper-evident service), exact institutional reviewers, core operator quorum, concurrency policy, verified backup+restore and the exact live deployment plan requires its own future review and explicit approval.

**Commit/activation warning:** A successful commit of these four files would complete only this **static/test-only checkpoint**. It would neither push to GitHub nor authorize an operational Technical Super Admin.
