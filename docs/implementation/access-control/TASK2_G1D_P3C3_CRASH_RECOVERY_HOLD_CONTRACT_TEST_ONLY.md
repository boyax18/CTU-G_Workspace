# CTU-G Workspace — Task 2 / G1D-P3C3: crash-recovery hold contract (TEST ONLY)

**Source basis:** `ronald` / `6d94564` (user-reported P3C2 Git commit), November 13, 2026.
**Status:** Add-only candidate, local acceptance required. Development approval covers test-only changes. Nothing in this artifact establishes live release approval.

## Why P3C3 exists

The existing synthetic ledger may return `NOT_COMMITTED` when reconciling an uncertain execution. **That is not permission to retry**: an execution reservation may already have been committed. The existing `ExecutionUnknown` behavior must remain a stop condition until a separate investigation resolves the discrepancy. A valid-looking post-state must not be confused with independent proof that the correct signer, DBA, or backup custodian approved a privileged action.

P3C3 provides a small **pure-Python, offline classifier** for synthetic crash/restore observations. It does **not** execute queries, create role metadata, grant permissions, inspect the actual ledger, authenticate the fact source, or implement a database fence. The classifier intentionally returns `release_status=BLOCKED`, `allow_retry=False`, and `allow_provisioning=False` in **every** case, including when its caller claims all operational controls are satisfied.

## Files (add-only)

1. `backend/apps/access_control/tests_support/g1d_p3c3_recovery_hold_test_only.py` — validation of synthetic ledger outcome, one-time execution evidence, role/audit references, trust epoch and independently claimed receipt; missing or contradictory evidence results in a security hold.
2. `backend/apps/access_control/test_task2_g1d_p3c3_recovery_hold.py` — 36 isolated offline tests (no Django DB) for unknown commits, not-committed-after-attempt, contradictory role/audit evidence, fake release signals and malformed observations.
3. `docs/implementation/access-control/TASK2_G1D_P3C3_CRASH_RECOVERY_HOLD_CONTRACT_TEST_ONLY.md` — this runbook.

No alterations to `.env`, `.gitignore`, `docs/database/full_schema.dbml`, Django models/migrations, database accounts, Git internals or actual role/permission data.

## What the statuses mean

- `SYNTHETIC_NO_MUTATION_OBSERVED`: the *caller-provided* facts resemble a never-attempted or fully non-mutating ledger; still no retry, provisioning, or live authorization.
- `SYNTHETIC_COMMIT_COHERENT`: the *caller-provided* consumed state has one reservation, one consumption event, unique role/audit references, inactive role and asserted receipt match; **not** independently attested or permission to run again.
- `SECURITY_HOLD`: unknown outcome, reserved execution, mismatched snapshots or receipt, incomplete role/audit linkage, stale trust epoch, or other contradictions. No automatic compensation or replay.
- `RecoveryRefused`: malformed facts, including non-disposable schema names; fail closed.

The prototype's `simulate_fenced_writers=True` is **not** proof of fencing, and the P3C2 grants report shows that the current development account has privileged capability. The real writer fence therefore remains unverified.

## Read-only recovery and operational checklist

Before any real privileged operation, an authorized DBA and independent custodians must obtain and preserve verified evidence outside this codebase:

1. Independently identify **every** role/permission writer: application/web workers, initializers, shell scripts, migration identities, SQL administrators, scheduled jobs, DEFINER routines and active MySQL sessions; compare with the P3C1 source inventory and P3C2 grants triage.
2. Use a controlled maintenance/admission protocol with independent DBA attestation. Reduce credentials to least privilege and drain/deny competing sessions; confirm that a non-participating privileged writer cannot race the intended release.
3. Produce and restore-test a fresh protected backup of the **actual then-current schema** (including the ledger if it is separately approved and migrated), verify tables, rows, constraints and evidence-link integrity. Historical 17-table restore tests alone do not cover a future ledger.
4. Bind release and request to independently verified real-world signer public keys, custody, trust epoch, expiration/revocation and separate executor. Test-only self-asserted booleans or generated keys are not authorization.
5. If COMMIT/connection acknowledgment is lost, **halt**, open a fresh read-only connection under approved credentials, verify exact role, audit and ledger consumption links and an independently held receipt; treat any mismatch as **UNKNOWN**, and never automatically retry.
6. Confirm operational halt, reversal/compensation policy and recovery personnel before a production change. Keep protected events and receipts under approved retention controls.

**Standing owner approval permits development and testing of G1D-P3C3. It does not supply real people, signer keys, operational DBA attestation, backups, D7 evidence, or a live privileged-write release.**

## Local acceptance (Windows PowerShell, backend virtual environment)

```powershell
python -B manage.py test apps.access_control.test_task2_g1d_p3c3_recovery_hold --settings=config.test_settings --noinput
```

Expected new tests: 36. Then run the established explicit Accounts + Access Control module enumeration under `config.test_settings` (previous baseline: 1,156 tests / 49 modules; expected with P3C3: 1,192 tests / 50 modules if unchanged). Run `python -B manage.py makemigrations --check --dry-run --settings=config.settings` (read-only migration comparison; **never** `migrate`). Stage and commit only the three add-only files after inspecting the staged diff. No push.
