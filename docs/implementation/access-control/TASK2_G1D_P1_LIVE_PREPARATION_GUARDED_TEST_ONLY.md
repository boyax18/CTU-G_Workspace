# CTU-G Workspace — Task 2, G1D-P1: Protected Role-Creation Preparation

**Date:** 2026-11-13

**Status:** preparation milestone passed local acceptance. Five new files, no live role creation or grant activation. Live release remains blocked pending separate decisions and authorization.
**Verified branch / HEAD before acceptance:** `ronald` / `91b0858d57b1e0f52e3d83d3ff76df619035c267`.

## 1. Fixed two-level application Admin hierarchy

1. **Normal Admin:** active Approved account with active `Admin` role; authorized school operations only. **No general Access Control Management authority.**
2. **Technical Super Admin:** active Approved account with **both** `Admin` and separately protected `Technical Super Admin` roles, plus the exact effective permission for each sensitive action and independent approval where required.

Django `is_superuser` remains a separate framework flag, **not** a third application Admin level and never a bypass. Institutional approver, technical custodian and executor are **duties**, not new application roles.

## 2. Source reconciliation and latest owner-reported state

The initial candidate was prepared from an older uploaded workspace ZIP. This acceptance task independently inspected the actual Windows repository, its five untracked candidate files, empty Git index, existing access-control models, role services, permission evaluator, delegation rules, audit writer, P0/P1 contracts, and disposable MySQL settings/runner. Branch and full HEAD matched the expected checkpoint above. The pre-existing modified official ERD and unrelated untracked files were preserved. The previous **905/905** regression across 42 modules remains owner-reported historical evidence; current independently executed results are recorded below.

Owner-reported private backup and restore rehearsal for `ctug_workspace` on 2026-11-13:
- Private backup: 36,005 bytes; SHA256 `7A47208D3B21CBCCF42F6A95D89116556261996D7CFB7B486C022B0269C8A26A` (do not commit or upload the dump).
- Clean import into **`ctug_restore_check`**; 17 tables, all 17 matching table names, exact row counts and MySQL EXTENDED content checksums. The uploaded 34-row CSV had 17 matching checksum pairs, no NULL checksum and no mismatch.
- Compared column and index metadata; 0 mismatches reported. Cross-schema foreign-key references: 0. Foreign-key columns: 23 in each, and full derived definition hash: `MATCH`.
- This is strong **local recovery rehearsal** evidence, not cryptographic proof that every data value can never differ, a perpetual live backup, or justification for restoring over later valid development data. Recheck state and backup freshness immediately before any future live change.

## 3. Exactly five ADD-ONLY candidate files

1. `backend/apps/access_control/management/commands/prepare_g1d_p1_protected_role.py` — **read-only** preparation command. Reuses the existing P0 SELECT-only inventory on exact local `config.settings` + `ctug_workspace`, requires explicit `--ack G1D_P1_PREPARATION_ONLY`. **Any `--apply` always refuses, even with otherwise valid options**. Does not create a role, import a writer or accept arbitrary evidence files.
2. `backend/apps/access_control/tests_support/g1d_p1_signed_evidence_test_only.py` — pure-Python *fictional* two-independent-signer/HMAC contract. Exact role label, inactive description, schema, executor, proposed operation, before-state and backup digests, nonce, <=15-minute simulated ticket. Test callers inject **fictional** independent HMAC keys; this is NOT real credential verification, provenance, institutional signature or an external trust store. It rejects one-signer, self-executor, wrong/expired/rejected/altered simulated evidence.
3. `backend/apps/access_control/tests_support/g1d_p1_provisioning_transaction_test_only.py` — **disposable MySQL only**, guard checks `config.test_settings`, random `test_ctug_registration_<16 hex>` database, configured/actual connected schema, exact ack, Approved active Normal Admin executor. Inside one durable Django atomic transaction it locks canonical `Admin`, checks an exact fictional before-state SHA256, rejects protected role aliases and governance drift, creates one **inactive** role, uses the existing `record_access_audit_receipt` with persisted executor and bounded action/snapshot, checks no assignments/grants and returns after the transaction exits. Ordinary caller-owned atomic nesting is refused. Audit failures must roll back the role. No live or production path. Existing MySQL unique role name is the final duplicate guard; the Admin lock does NOT serialize unrelated writers.
4. `backend/apps/access_control/test_task2_g1d_p1_live_preparation.py` — **52 security tests** (31 static + 21 disposable MySQL), including the added ordinary nested-transaction refusal case. Covers exact evidence scope, fake HMAC validation, failure paths, executor/role identity, stale state, transaction/audit atomicity, and deny-by-default live CLI. Full Django tests must run under `config.test_settings` and teardown the disposable MySQL test database.
5. This document — scope, acceptance process, distinct authorization boundaries and pending release gates.

No changes to `docs/database/full_schema.dbml`, Django models, migrations, ordinary `init_system_roles`, permission evaluator, active catalogue, actual account assignments, existing APIs or frontend. No new application Admin tier. No automatic account promotion.

## 4. Deliberate fail-closed boundary and limitations

**This is NOT an independently authorized, operational role-creation command.** It models the transaction and evidence requirements in a disposable environment, with a live command that fails closed. Actual institutional identities, signature trust roots, revocation, signer-eligibility validation, real-time preflight digest, evidence custody, ticket issuance/one-use replay protection, durable approvals, environment binding to `ctug_workspace`, approval expiry, trusted executor identification, release flags and authorization policy have **NOT been implemented**. Accepting fictional test keys from a caller would be unsafe in production. A commit is not authority to change the database.

`access_audit_logs` is an attribution record, **not** a substitute for a durable approval-evidence ledger or actual identity verification. The proposed role-creation event uses the already supported audit action code `technical_admin.role_metadata.create`, `reason=policy_enforcement`, and a bounded `new_value` with `role_id` and `is_active=False`; it does not store personal data or fictional signing secrets.

A true live implementation will require independently approved signer trust roots and identity proof, exact signed request scope, nonce uniqueness/ticket consumption, database locks, pre/post-state review, verified executor policy, fresh backup, a second source inspection, tests under real local conditions, and **a separate explicit owner authorization of the exact one-row metadata-only P1 write**. No `--apply` operation may be enabled before these are agreed. Later P2 ledger, P3 governance metadata/bindings, P4 first Technical Super Admin account bootstrap and P5 protected management all have their own approval gates.

## 5. Windows local verification and staging discipline

At this continuation's start, all five candidate files were already present and untracked; no extraction or reinstall was needed. Require Git branch `ronald`, HEAD `91b0858`, and an empty Git index before staging. Preserve the locally modified official ERD and unrelated docs or scripts; never stage `.env`, personal backups, `Scripts/`, `review_only`, `backend/apps/config/`, or other work.

From `backend` with the existing `.venv`:

```powershell
python -B manage.py prepare_g1d_p1_protected_role --settings=config.settings --expected-db ctug_workspace --ack G1D_P1_PREPARATION_ONLY
if ($LASTEXITCODE -ne 0) { throw 'P1 read-only preparation failed. Stop.' }

python -B manage.py test apps.access_control.test_task2_g1d_p1_live_preparation --settings=config.test_settings --noinput
if ($LASTEXITCODE -ne 0) { throw 'P1 disposable security tests failed. Stop.' }
```

The command's `--apply` **always refuses** and is not for developer experimentation. No live mutation command should be run.

If isolated checks pass, enumerate `backend/apps/accounts/test*.py` and `backend/apps/access_control/test*.py` module names and run full test suite with `--settings=config.test_settings`. Baseline is 905 tests; the revised candidate adds 52 and, **if unchanged**, should discover about **957 tests** across 43 modules. Check runner's actual result. Then run:

```powershell
python -B manage.py makemigrations --check --dry-run --settings=config.settings
if ($LASTEXITCODE -ne 0) { throw 'Migration drift. Stop.' }
```

Expect `No changes detected`. Only once local test results and Git scope are reviewed, update this document with actual acceptance results, stage **exactly five paths**, inspect `git diff --cached --check` and `git diff --cached`, then commit. Never push without an explicit team workflow decision. **Do not create, activate, assign or grant the actual Technical Super Admin role as part of this checkpoint.**

## 6. Unresolved decision register for a future P1 Live release

- Real person identities and independently checked institutional/technical signing eligibility (two independent humans; executor distinct).
- Exact trusted executor policy for first dormant-role metadata creation that does not accidentally give Normal Admin access to broader governance.
- Signed immutable operation, authorized before-state snapshot, backup verification, environment and policy version; trusted verifier and replay-safe single-use ticket.
- Storage/retention for approval evidence and append-only audit correlation, and whether any official ERD change is needed (not authorized here).
- Final MySQL lock order, protection against unrelated writers and safe recovery after a post-commit mistake.
- Fresh read-only P0 inventory and backup state; approved source tree/commit, exact payload, execution and verification instructions; explicit release owner authorization.

## 7. Independently executed local acceptance — 2026-11-13

- **Environment:** existing `backend/.venv`, Python 3.13.7 / Django 6.1.2. The shell did not expose `python` on PATH, so commands used `.\.venv\Scripts\python.exe -B` from `backend`. Sandbox access to the installed interpreter required an approved execution escalation; no environment or dependency files were changed.
- **Scoped corrections:** removed the operational preparation command's import of fictional test-only evidence constants and its associated fixture drift check. The unchanged P0 inventory enforces the live role/initializer baseline. Added `durable=True` to the disposable helper's transaction so an ordinary outer transaction cannot defer commit behind a returned receipt. Strengthened the invalid-receipt rollback test to insert a real audit row before returning an invalid receipt; both inserted role and audit are then absent. Added one nested-transaction refusal test, taking the candidate from 51 to 52 tests.
- **Read-only preparation:** independently rerun after the command correction; exit 0. Actual configured/connected target `ctug_workspace`; 1 canonical active Admin, 0 technical roles, aliases, assignments, bindings or active direct governance overrides; 0/6 Core K codes; 1 active access-control service; 15 audit rows. Initializer unchanged. No role, grant, assignment, account, approval-ledger or audit write was performed.
- **Isolated security suite:** `manage.py test apps.access_control.test_task2_g1d_p1_live_preparation --settings=config.test_settings --noinput`; **52/52 passed**, 0.311 seconds, exit 0, system checks clear. Django reported disposable database creation and destruction. No `--keepdb` was used.
- **Isolation evidence:** settings independently showed local MySQL at `127.0.0.1`, generated `test_ctug_registration_<16 hex>` configured and TEST names, and `config.test_runner.IsolatedMySQLRunner`. Each process generates a new name. The runner checks configured aliases before creation and verifies `SELECT DATABASE()` after setup; the P1 fixture and helper repeat actual-schema checks before writes. The unchanged runner refuses reuse/parallel clones and preserves any pre-existing schema on a name collision.
- **Rollback coverage and limits:** audit-storage exception rolls back role creation; invalid audit receipt after an actual audit INSERT rolls back both role and audit. Success creates exactly one inactive role and one actor-attributed audit with zero assignments/bindings; inactive/unapproved/non-Admin executors, framework superuser alone, stale state and governance drift are refused. These `TestCase` cases run inside Django's special test transactions; they do not prove a real outermost commit, crash recovery, signer identity, durable replay prevention, or cross-connection serialization against unrelated writers. The Admin lock and database uniqueness were inspected, not concurrency stress-tested.
- **Production boundary:** no operational code imports either new test-only security helper after correction; the live command remains SELECT-only and any `--apply` refuses before database access. No new endpoint, model, migration, role level, seed, permission or live authorization path was introduced. Existing models, evaluator, delegation rules, audit writer and four-role initializer were unchanged.
- **Migration consistency:** `manage.py makemigrations --check --dry-run --settings=config.settings` returned `No changes detected`, exit 0. No development migrations were applied.
- **Full Accounts + Access Control regression:** enumerated the established `test*.py` module paths, sorted by full path; **957/957 passed across 43 modules**, 158.733 seconds, exit 0. System checks clear; Django reported creation and destruction of the disposable database. No `--keepdb` was used. The observed count is 905 historical tests plus 52 candidate tests. Simulated failure-path RuntimeError log messages did not fail the suite.
- **Repository preservation:** branch/HEAD rechecked at the approved checkpoint; index empty before scoped staging. No tracked file was modified by this task. The pre-existing official ERD modification was preserved byte-for-byte (SHA256 `BEFB42DF64A6D10B1AA0828A8E2A0A62FF3167B2B35DADCFA973FECF6D54C6D1`). Only the five authorized new paths are eligible for this commit. No model, migration, settings, environment, backup, unrelated script/documentation or team file belongs in the staged change. No push is authorized.

**Current result:** G1D-P1 preparation verification **passed**: read-only inventory, 52 isolated security tests, 957 full regression tests, and migration consistency. A scoped commit may proceed only after the five-file staged review and whitespace check pass. The real `Technical Super Admin` role has **NOT** been created. Live `--apply` remains unavailable. Recovery rehearsal evidence in section 2 is owner-reported and was not independently repeated here. Real signer trust, independent identity verification, durable one-use evidence, live executor authorization and the protected command release gate remain unresolved.

**Next phase:** prepare a separate owner-reviewed implementation plan covering signer trust/identity, first-executor policy, one-use evidence storage and consumption, lock order and unrelated writers, fresh recovery evidence, exact inactive-role payload, actor-attributed audit, and post-write verification. Resolve any required architecture/ERD decision separately. Obtain explicit approval of that plan and the exact live write before enabling or executing a protected command. This preparation commit authorizes no live role creation, activation, grant or assignment.
