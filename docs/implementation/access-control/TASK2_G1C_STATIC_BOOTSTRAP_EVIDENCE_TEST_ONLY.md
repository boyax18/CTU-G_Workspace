# CTU-G Workspace — Task 2 / G1C-A: First Bootstrap and Approval Evidence
## Approved design, static and disposable test-only checkpoint

**Status:** G1C-D1–D6 approved for **architecture, static/read-only and disposable-test-only implementation**. This is an **add-only candidate**, NOT an operational bootstrap or approval system. Local static verification, isolated security tests, full backend regression and migration consistency have passed as reported by the developer; the scoped Git review and commit remain pending. Source inspection was against an earlier uploaded snapshot; the developer reported branch `ronald`, HEAD `ace9f06` after G1B, 817/817 backend regression passing, and no pending model migrations.

**Exactly two application Admin levels:**

1. **Normal Admin** = an Approved/active account assigned the `Admin` role; school operations only, as authorized by explicit permissions.
2. **Technical Super Admin** = an Approved/active account assigned **both** `Admin` + protected `Technical Super Admin` roles; explicit governance permission checks are additionally required.

Django `is_superuser` is a separate framework maintenance flag, **not** a third application tier or a permission bypass. Institutional reviewer, technical custodian and executor are **approval responsibilities, not new Admin roles**. The existing Normal Admin, including any previously identified account, has **not** been nominated or promoted.

### Approved G1C-D1–D6 limits

- G1C-D1: retain precisely the above two-level hierarchy; no third application Admin profile.
- G1C-D2: plan a dedicated trusted, independently authorized **offline first-bootstrap** of a separately nominated, verified existing Normal Admin. Nothing here nominates anyone, or provides a real bootstrap pathway.
- G1C-D3: **propose** a separate durable MySQL evidence ledger, subject to official ERD, schema/constraint, model, migration, retention, and alternative-storage review. Neither MySQL nor another storage architecture is operationally selected or implemented by this package.
- G1C-D4: bind **fictional** approvals and a ≤15-minute execution ticket to exact request digest, scope, target, environment, before-state, policy and catalogue. Human approval collection is distinct from execution-ticket lifetime; these tests do **not** authenticate real humans, sign evidence, or establish replay-safe consumption.
- G1C-D5: demonstrate one-effective-operator hard floor (design) and possible two-operator routine-removal target (unapproved operational parameter), and illustrate race conditions. Real operations require database-level serialization, pre/post re-evaluation, transactional audit and session invalidation, none of which is built here.
- G1C-D6: only static source checks and isolated disposable-MySQL fixtures are authorized now; all actual privilege/bootstrap changes remain blocked.

### Four add-only candidate files

1. `backend/apps/access_control/tests_support/g1c_evidence_test_only.py` — pure-Python immutable fictional request, two-approver evidence and execution-ticket **structure check**; canonical SHA-256 proposal fingerprint, in-memory request/idempotency/nonce conflict snapshot, operator-floor/concurrency demonstration. **No database calls, cryptographic signer verification, authority, locks or mutation functions. Production endpoints MUST NOT import this module.** A successful structural comparison grants nothing.
2. `backend/apps/access_control/management/commands/report_g1c_bootstrap_static.py` — **filesystem-only static report** reconciling G1C's two-profile policy with G1B's exact six-code *planning* catalogue. Requires `--ack G1C_STATIC_ONLY`. **No database queries or writes.**
3. `backend/apps/access_control/test_task2_g1c_evidence_contract.py` — **59 tests**: pure static/negative contracts, fictional role/expiry/separation and replay checks, simulated stale-read operator loss; isolated MySQL `TestCase` fixtures validating existing role/permission evaluator and audit rollback; an isolated `TransactionTestCase` using a **MySQL TEMPORARY TABLE created and removed only inside the disposable test database** to demonstrate primary-key and unique idempotency/nonce constraints. These are **not** official ledger tables, models, migrations, durable evidence or a live governance service. Module-level test-settings guard and actual connected-schema checks block ordinary settings.
4. This document, recording scope and verification instructions.

### Why the separate approval ledger is still required

The existing `access_audit_logs` records authorized security-change attribution and snapshots but cannot verify independent human approvals, ensure exact one-use request/nonce consumption, or serialize governance changes. A report, plain signed-off Markdown, in-memory `consumed=False` field or hash is **never** evidence of authentic institutional authorization. The static tool deliberately does not install Core K metadata or grant privileges.

A real request/approval/receipt/serialization-guard design needs dedicated review for who can sign and verify, credentials/trust roots, tamper evidence, unique keys, row locks, operator availability, failure rollback, session revocation, backups and restoration. Do not copy test-only dataclasses into Django models. The six Core K codes and their Technical-only proposed bindings remain **planning definitions**, not live grants.

### Local Windows acceptance steps (PowerShell)

From project root, check branch `ronald`, HEAD `ace9f06`, clean Git index, and **absence** of all four target paths before extracting. Inspect ZIP contents before extracting. The modified official `docs/database/full_schema.dbml` and all unrelated untracked files must remain outside scope.

In `backend` with `.venv` active:

```powershell
python -B manage.py report_g1c_bootstrap_static --settings=config.settings --ack G1C_STATIC_ONLY
if ($LASTEXITCODE -ne 0) { throw "G1C static preflight failed; STOP." }

python -B manage.py test apps.access_control.test_task2_g1c_evidence_contract --settings=config.test_settings --noinput
if ($LASTEXITCODE -ne 0) { throw "G1C isolated tests failed; STOP." }
```

The test module **must never run** with `config.settings` or any settings targeting the main `ctug_workspace` database. The isolated settings generate an unpredictable `test_ctug_registration_...` schema, and the test runner destroys it. The G1C temporary uniqueness table exists only for the duration of its fixture test. Stop if the test runner does not report database teardown.

After isolated acceptance, run the known working complete Accounts + Access Control test-module enumeration (40 earlier modules + new G1C module = **41 modules** if unchanged), then read-only migration consistency:

```powershell
python -B manage.py makemigrations --check --dry-run --settings=config.settings
if ($LASTEXITCODE -ne 0) { throw "Migration drift; STOP." }
```

Expected total if 817 previous tests remain unchanged and the 59 new tests are found: **876 tests**; the actual runner output is authoritative. Record outputs and Git status before staging. Inspect four file diffs, stage *only* these four files, `git diff --cached --check`, and commit only after approval of verified local results. **No push, release, privilege change or live migration is implied by a commit.**

### Windows local acceptance record — November 13, 2026 (developer-reported)

The developer supplied the following VS Code PowerShell results after installing the four G1C files. These results are reported from the developer's Windows environment; they are not an independent connection to that environment.

- **G1C static verification:** `report_g1c_bootstrap_static --settings=config.settings --ack G1C_STATIC_ONLY` passed. Report confirmed exactly two application Admin levels (Normal Admin, Technical Super Admin), six planning-only Core K codes, a proposed 15-minute execution-ticket maximum, and no database reads or writes.
- **G1C isolated security tests:** 59/59 passed under `config.test_settings`; Django reported creation and destruction of the disposable test database.
- **Full Accounts + Access Control regression:** 876/876 tests passed in 129.695 seconds under `config.test_settings`. Logged simulated `RuntimeError` messages did not cause failures; Django reported successful test-database destruction.
- **Migration consistency:** `makemigrations --check --dry-run --settings=config.settings` returned `No changes detected`.
- **Git boundary:** The expected pre-commit branch is `ronald` at HEAD `ace9f06`. Recheck the branch, HEAD, clean index, and the four exact new paths before staging; **the developer has not yet supplied a fresh post-regression Git status for this checkpoint**.

**Acceptance outcome:** Testing passed for the static/test-only G1C scope. This does not authorize an operational bootstrap, real approvals, privileged assignments, catalogue seeding, governance writes, ERD changes, or release activation.

### Explicitly unresolved / not authorized

- Named beneficiary and verified human authorizers, trust roots and signing process.
- Canonical official ERD update, ledger schema/constraints, integration, persistence/retention and migration.
- First bootstrap or technical-role mutation service; database guard lock order and reusable evidence consumption.
- Last-effective-operator computation with session/step-up usability, real concurrent operations, audit receipts and session invalidation.
- Verified backup/restore rehearsal, emergency recovery, actual privilege metadata installation and environment-specific release approval.

**Repository policy:** Add only the four files listed above. Never stage, edit or silently resolve `docs/database/full_schema.dbml`, `.env`, `review_only`, `Scripts`, unrelated docs or team files. Do not activate registration-review, SMTP, reapplication or bulk workflow gates as part of this checkpoint.
