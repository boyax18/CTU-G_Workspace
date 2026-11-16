# CTU-G Workspace — Task 2 G1D-P3C1 — Protected-writer exposure inventory (TEST ONLY)

**Source checkpoint:** uploaded VS Code snapshot `ronald` / `211326a2f4247bf4e11538bb1c314bbc47d7755c`, November 13, 2026.
**Status:** Add-only, reviewable development candidate. Owner-local acceptance and scoped commit pending.
**Boundaries:** No live role creation, migrations, database access, credential grants/revocation, trust enrollment, or official ERD edits.

## Problem addressed

The existing disposable G1D-P1 ledger `execute(..., simulate_fenced_writers=True)` accepts a **test caller assertion**, not evidence that competing privileged SQL writers were actually fenced. Its control-row lock does not bind other application services, Django shell, initialization scripts, DBAs, external jobs or direct MySQL sessions. This remains a critical production release blocker regardless of successful synthetic Ed25519 signatures or 1,105 passing backend tests.

This phase adds a reproducible **read-only source inventory** to help discover and prioritize Python code locations that may directly modify the protected Role/AccountRole/RolePermission/AccountPermission/Permission/Service tables. It is not an enforced fence.

## Results on the uploaded checkpoint

The ZIP was scanned **in memory, only for safe Python source files** under `backend/apps/` and `backend/config/`; test modules, migrations, tests_support, Git internals, dependencies, `.env`, `.gitignore` and binaries were excluded.

- **118** application Python source files reviewed by the static heuristic.
- **14** matching direct ORM mutation call sites (not 14 different DB principals).
- No explicit static dangerous SQL mutation strings were identified by the heuristic. This does **not** mean dynamic SQL or untracked writers are absent.
- **20/20** pure offline unit tests passed on the candidate scanner. Django/MySQL and full regression **not yet rerun** after installation.

### Candidate writer-path inventory

| Detected path | Suspected operation |
| --- | --- |
| `apps/access_control/management/commands/init_registration_review_inactive_bindings_local_dev.py` | `RolePermission.create` |
| `apps/access_control/management/commands/init_registration_review_metadata_local_dev.py` | `Service.create`, `Permission.create` |
| `apps/access_control/management/commands/init_system_roles.py` | `Role.get_or_create` |
| `apps/access_control/mutations.py` | `RolePermission.create`, `AccountPermission.create` |
| `apps/accounts/admin_bootstrap.py` | `AccountRole.create` |
| `apps/accounts/management/commands/seed_review_sandbox.py` | `Role.create`, `AccountRole.create` (2), `Service.create`, `Permission.create`, `RolePermission.create` |
| `apps/accounts/registration_review.py` | `AccountRole.create` |

The scanner reports source paths and line numbers; it does **not** print source contents, process data, credentials, or private keys. Existing audit and delegation mechanisms must still be inspected at each route; a flagged call is **not** automatically a vulnerability.

## Added files — exact scope

1. `backend/apps/access_control/tests_support/g1d_p3c1_writer_inventory_test_only.py` — AST-only Python source triage, CLI, and permanent `release_status: BLOCKED` report.
2. `backend/apps/access_control/test_task2_g1d_p3c1_writer_inventory.py` — pure unittest contract and negative tests.
3. `docs/implementation/access-control/TASK2_G1D_P3C1_WRITER_EXPOSURE_INVENTORY_TEST_ONLY.md` — this evidence and limitations document.

### Run the read-only local scan

From the `backend` directory:

```powershell
python -B -m apps.access_control.tests_support.g1d_p3c1_writer_inventory_test_only --backend-root .
```

From the same directory, first run the new focused unit tests:

```powershell
python -B manage.py test apps.access_control.test_task2_g1d_p3c1_writer_inventory --settings=config.test_settings --noinput
```

The focused tests are pure Python and should not create a database. Then run the full explicitly enumerated Accounts + Access Control test modules using `config.test_settings`, followed by `makemigrations --check --dry-run --settings=config.settings`. Baseline was **1,105** tests; expected increment here is **20**, so approximately **1,125** subject to local test discovery and current changes.

## Release gates still missing (G1D-P3C2 / P3C3)

**P3C2 — real privileged writer fence:** Obtain an exact DBA-verified principal/grants inventory of every actor that can modify protected metadata; include actual `SHOW GRANTS`, stored routines, triggers, migration identity, superusers, backup/restore operators, all application/worker credentials, direct SQL and external jobs. Restrict and drain competing write-capable sessions, provision least-privilege execution credentials, hold a maintenance/revocation barrier, and independently verify the state again within the actual release window. A Python-only source scan cannot attest any of these. Never treat `simulate_fenced_writers=True` as evidence or use it in live code.

**P3C3 — recovery and evidence:** Keep independent signed root-key custody, separately verified executor identity, approved ledger schema/retention, encrypted offsite receipts, fresh backup and actual restore rehearsal (including newly approved schema), uncertain-COMMIT reconciliation, and audit/postcondition checks. The previous 17-table restore check does not attest a future ledger schema.

**P4/P5 remain blocked:** Creating the inactive Technical Super Admin role, granting governance permissions, assigning the Admin + Technical Super Admin dual role, and bootstrap all require a separate operationally verified release gate. General standing approval permits *development*, but cannot substitute for real identities, DB credential control, safety evidence or release attestation. The command `prepare_g1d_p1_protected_role --apply` must remain disabled.

Exactly **two application Admin levels** remain Normal Admin and Technical Super Admin; Django framework superuser is separate. No blanket role-name bypass may be added.

## Git and safety

Install only these three **new** paths. Preserve existing modified `docs/database/full_schema.dbml`, `.env.example` and unrelated files. Inspect `git status`, confirm branch/HEAD, and stage/commit only after the owner-local full regression and migration check pass. **No GitHub push.**
