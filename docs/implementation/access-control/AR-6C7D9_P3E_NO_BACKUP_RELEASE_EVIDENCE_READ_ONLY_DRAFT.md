# AR-6C7D.9 — P3E No-Backup Risk and Read-Only Release Evidence

**Project:** CTU-G Workspace
**Branch / prior checkpoint:** `ronald` / `5f4fa4c`
**Status:** Inspection and test candidate; **NOT a live activation release**
**Scope:** Existing local MySQL `ctug_workspace`, no ERD or migration changes

## Decision and limitations

The project owner elected to **skip a manual backup** for this local-development milestone. Respect that decision without treating it as verified recovery. There is no credible guarantee that every database failure can be reversed. In particular, an atomic transaction is not a substitute for a disaster-recovery copy; compensation is only possible when the database and audit tables remain usable and consistent.

Therefore **P3E adds no development-database write path**. P3D's `LOCAL_DEV_WRITES_RELEASED = False` code-level barrier remains intact. Do not toggle it, bypass it with a fake test settings module, or copy a test command into the development environment. The operator may do additional no-write validation while accepting that an actual future activation will require a distinct, reviewed release decision and recovery arrangement.

## Functionality and evidence

New command `report_registration_review_release_gates_p3e`:

- Reuses P3C's exact MySQL identity, canonical P1/P2 catalogue and eight receipt checks, disabled flags/unmounted routes, zero active grants, and exact eligible Admin account set checks.
- Asserts the P3D code-level local activation barrier remains shut.
- Reads the pinned authorization rows and all P1/P2/P3 transition receipts inside the same transaction as P3C inspection, then hashes their canonical JSON representation. Only the **SHA-256 digest** is printed; audit payloads and private School IDs are not.
- Optionally accepts `--expected-fingerprint` to fail on changed security state. A matching fingerprint is an **integrity comparison**, not a verified backup, concurrency-proof activation authorization, or evidence of comprehensive security.
- Reports that backup/restore, integration test evidence, and release authorization cannot be established by this command. There is no `--apply` argument, migration, role grant, service activation, flag or route edit.

This fingerprint is stable while the selected metadata, bindings, and receipts remain unchanged. It may change if legitimate IDs or audited fields change, even though the schema is still valid. It covers **only** the listed security metadata and audited transitions, not the entire application or database.

## Install and test

Extract the companion ZIP into the **repository root** on branch `ronald`. The package adds **exactly three new paths**; it does not replace existing files:

1. `backend/apps/access_control/management/commands/report_registration_review_release_gates_p3e.py`
2. `backend/apps/access_control/test_registration_review_release_gates_p3e.py`
3. This document.

From `backend/` with `.venv` active:

```powershell
python -B manage.py test apps.access_control.test_registration_review_release_gates_p3e --settings=config.test_settings --noinput
if ($LASTEXITCODE -ne 0) { throw "Phase 3E tests failed; stop." }
```

Then rerun all prior 271 access-control tests plus the new test module. All writes in tests MUST occur only inside the disposable Django test DB and be destroyed afterward. Do not run this test module under `config.settings`.

## Local read-only command

```powershell
python -B manage.py report_registration_review_release_gates_p3e --actor-account-id 3 --expected-admin-account-ids 3
```

Expected on the previously verified inactive database: the command prints `READ-ONLY RELEASE EVIDENCE PASSED`, a SHA-256 fingerprint, and `ACTUAL ACTIVATION: BLOCKED; NO WRITES EXECUTED`.

For a subsequent drift check, copy the fingerprint (not secrets) and rerun:

```powershell
python -B manage.py report_registration_review_release_gates_p3e --actor-account-id 3 --expected-admin-account-ids 3 --expected-fingerprint THE_64_CHARACTER_SHA256
```

Do not modify the fingerprint to force a pass. Investigate any mismatch first.

## Release boundary

- Live local activation: **blocked**.
- Permission services and three Admin role bindings: **inactive**.
- Effective Registration Review permissions: **zero**, according to the exact P3C/P3A checks.
- Registration Review API: **disabled and unmounted**.
- Source of truth: official `docs/database/full_schema.dbml` remains untouched.
- No-backup choice: **not equivalent to recovery verification**. If the owner later chooses to activate without a backup, that would require an explicit separate risk decision and a code-reviewed release adapter; P3E does not grant this authorization.

For Git, stage only the three new paths. Never use `git add .` on the working tree with unrelated ERD and draft modifications.
