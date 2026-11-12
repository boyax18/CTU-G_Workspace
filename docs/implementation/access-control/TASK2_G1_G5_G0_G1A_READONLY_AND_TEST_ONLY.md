# CTU-G Workspace — Task 2 G1–G5 Governance, G0/G1A checkpoint

**Status:** Approved policy direction; **candidate implementation ONLY**. No privileged operations approved, no production authorizer, and no permission-catalogue or recovery design finalized.

**Development discipline:** Inspect → Reconcile → Approve (G1–G5, read-only/test-only scope) → Implement (this add-only candidate) → Test (local verification passed) → Document (verified results recorded below) → Commit (pending scoped review) → Continue (requires later approval).

**Provenance:** The user reported `ronald` HEAD `654009e`, existing 743/743 backend regression passing, and no migration drift. The user-reported read-only P2 preflight showed one framework Superuser, one eligible Admin, no Technical Super Admin role, no technical role bindings, no governance overrides, and 15 audit records. This document does **not** assert a fresh check of the user's real database. Source contracts were reconciled with the uploaded `CTU-G Workspace - Copy (2).zip`, the previous Task 2 add-only package, and the G1–G5 approved proposal. Local source may have diverged; verify before installation.

## Approved architecture and security boundaries

- Exactly two CTU-G Workspace application Admin profiles: **Normal Admin** (`Admin` role) and **Technical Super Admin** (active `Admin` + active `Technical Super Admin` roles). Django `is_superuser` is a separate framework concept and is **never** an application permission bypass.
- Real protected operations must require a persisted Approved/active account, both active role assignments, the exact effective active permission, direct-Deny precedence, and a separate approved authorization/evidence contract under stable MySQL locks.
- No user or Django Superuser can self-promote, create technical governance roles, or use ordinary delegation to manage protected authority. Generic registration, Django Admin CRUD, and the existing ordinary delegation engine are not approved pathways.
- G1 **bootstrap** requires a verified human beneficiary, distinct institutional authorizer and technical custodian, fresh evidence, one-time consumption, and separately approved live ceremony. No existing account, including Account ID 3, is nominated automatically.
- G2 **assignment/revocation** is separately reviewed and audited, with no self-change and no unreviewed Admin creation.
- G3 **governance permission catalogue** and core K are still **proposals**, not metadata or grants authorized for seeding. Normal Admin permissions continue through `Admin` role; Technical role will eventually contain only approved governance capability codes.
- G4 **last-effective-operator** check must be performed before and after each indirect/direct change under one deterministic lock protocol. The proposed floor of two for routine removal is not yet approved as an operational quota. An exceptional recovery path must be independently controlled.
- G5 **approval evidence** needs an approved durable ledger (new ERD-governed tables **or** a reviewed external tamper-evident service), reliable one-use semantics, audit-in-transaction, targeted session invalidation, and verified backup/restore. The existing `access_audit_logs` alone is **not** a durable independent approval ledger.

## Add-only files in this candidate

1. `backend/apps/access_control/management/commands/report_technical_governance_g0.py` — **SELECT-only** exact local-DB inventory on MySQL loopback. Reports aggregate role/override state and status of **proposed** K permission codes, not account IDs, student IDs, credentials, or secrets. Fails closed when settings, database, labels or acknowledgement differ. No state change or approval granted. It does not evaluate whether real operators are independently approved for governance changes.
2. `backend/apps/access_control/tests_support/governance_g1a_test_only.py` — non-operational in-memory evidence and operator-floor simulations using the existing permission evaluator. No API, management write command, persistent evidence, lock protocol, or call path from normal application services. **Do not import into production endpoints.**
3. `backend/apps/access_control/test_task2_governance_g1a_contract.py` — isolated MySQL test fixtures for role composition, effective permissions, override Deny, inactive service, stale/expired/mismatched simulated evidence, two distinct signers, self-target denial and last-operator/TOCTOU risk. All fixture writes are test database writes only and are destroyed by the test runner.
4. This documentation — decisions, limitations and verification instructions.

The candidate **does not** create or seed a Technical Super Admin role, assign one, update a permission, consume real approval, add URLs, modify `settings.py`, enable gates, change the official `docs/database/full_schema.dbml`, or alter another module.

## G0 read-only inventory (owner's Windows VS Code PowerShell)

```powershell
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend"
.\.venv\Scripts\Activate.ps1
python -B manage.py report_technical_governance_g0 --settings=config.settings --expected-db ctug_workspace --ack READ_ONLY_G0
if ($LASTEXITCODE -ne 0) { throw "G0 inventory failed. Stop." }
```

The target must be configured **and actually connected** to `ctug_workspace` over loopback, with Django DEBUG enabled and the exact `config.settings` module. The report will not disclose individual account details. The candidate K codes are **never** to be seeded or granted by this report. If any protected role/grant/override is already present, reconcile it before new design.

## G1A disposable MySQL security tests

```powershell
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend"
.\.venv\Scripts\Activate.ps1
python -B manage.py test apps.access_control.test_task2_governance_g1a_contract --settings=config.test_settings --noinput
if ($LASTEXITCODE -ne 0) { throw "G1A tests failed. Stop." }
```

`config.test_settings` creates a fresh unpredictable `test_ctug_registration_...` schema and destroys it afterward. This module **refuses normal/live settings**. The tests simulate good and bad approvals, but a passing test **does not authorize a real operation**. The dual-role/operator snapshot is a point-in-time read without production locks. In particular, two independently evaluated removals could each appear safe while jointly removing every operator; a future write service must implement serialized before/after checks.

After isolated tests, run full Accounts and Access Control regressions using your known working method (enumerate individual test files, not package-level autodiscovery), then:

```powershell
python -B manage.py makemigrations --check --dry-run --settings=config.settings
if ($LASTEXITCODE -ne 0) { throw "Migration drift. Stop." }
```

Do **not** run `migrate`, seed roles, start SMTP, enable review/bulk/reapplication gates, or try actual bootstrap/promotion.

## Windows local acceptance record — 2026-11-12

The project owner supplied these VS Code PowerShell results from branch `ronald` at HEAD `654009e`. These are operator-reported outputs, not an independent inspection of the owner's machine:

- **G0 read-only report:** passed against `ctug_workspace` with no writes. Exactly one `Admin` role; zero `Technical Super Admin` role records, assignments, technical bindings or direct governance overrides. One active `access_control` service. All six proposed core K permission codes absent. No bootstrap or governance authority authorized by the inventory.
- **G1A isolated contract tests:** 26/26 passed under `config.test_settings`; Django reported that it created and destroyed a disposable MySQL test database.
- **Full Accounts + Access Control regression:** 769/769 passed from 39 test modules under `config.test_settings`; Django reported disposable test database teardown. Logged simulated errors were not test failures.
- **Migration consistency:** `makemigrations --check --dry-run --settings=config.settings` returned `No changes detected`.
- **Git scope before commit:** `ronald` / `654009e`, four new untracked G0/G1A paths as listed in this document. The modified official `docs/database/full_schema.dbml` and unrelated untracked files remain outside the intended commit.

**Acceptance status:** Test stage passed for this **read-only/test-only** checkpoint. These results do not authorize or implement any privileged role creation, elevation, governance catalogue seeding, approval ledger, operational write service or live permission activation.

## Outstanding approval gates

1. Institutional signer / technical custodian identities and institutional verification procedure.
2. Evidence storage: reviewed database tables (requiring **separate ERD/model/migration approval**) or tamper-evident external ledger with durable single-use enforcement.
3. Final versioned permission manifest, defaults, exact core K, definition of an **effective usable operator**, and minimum operator quorum.
4. Explicit protected write service policy: trusted actors, lock order, B1 audit atomicity, concurrency, session invalidation and recovery.
5. Verified backup+restore rehearsal, exact environment, release candidate and separate owner authorization for any real writes or privileged grants.

**Status to record after testing:** G0 output, G1A isolated tests count/result, full regression count/result, no-migration result, staged names. No credential dumps, no pasted `.env`, no actual account IDs in public documentation beyond previously approved references.

**Commit boundary:** Only the four add-only paths listed above, once the user verifies the source branch/HEAD `ronald`/`654009e`, checks that no files existed before extraction, runs the tests, reviews staged files and confirms unrelated work including the official ERD remains unstaged. This checkpoint contains **no live governance capability**.
