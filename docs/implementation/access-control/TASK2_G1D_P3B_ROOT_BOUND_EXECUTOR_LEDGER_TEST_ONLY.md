# CTU-G Workspace — Task 2 / G1D-P3B

## Root-bound executor evidence and existing disposable-ledger composition (TEST ONLY)

**Status:** ADD-ONLY CANDIDATE. Expected local branch `ronald`, HEAD `ab7ab81` after G1D-P3A. Owner-local acceptance and scoped commit are pending. The original inspected source snapshot was `c2d501c` plus the G1D-P3A patch previously delivered and reported committed. Reconcile differences before applying.

### Purpose and boundaries

Build a deliberately non-operational verification layer between the **G1D-P3A synthetic root-endorsed roster** and the **existing G1D-P1 disposable MySQL one-use ledger**. Do not implement a second ledger, live authority, production Django permission, actual key enrollment, or any production database writes.

Exactly two application Admin levels remain **Normal Admin** and **Technical Super Admin**. Framework `is_superuser` never grants application governance authority. No account promotion or permission grant is in scope.

### New add-only files (exact scope)

1. `backend/apps/access_control/tests_support/g1d_p3b_root_bound_executor_test_only.py` — pure Ed25519/root-bound receipt requiring independently supplied exact schema, incarnation, minimum trust epoch, roster hash, approved actor, challenge, request hash, full bundle hash, ticket nonce, before-state hash, backup hash and release hash.
2. `backend/apps/access_control/tests_support/g1d_p3b_root_bound_ledger_test_only.py` — guarded adapter that verifies the root-bound bundle before handing off admission, claim and execution to the **unchanged existing** `DisposableLedger`; read-only ambiguity reconciliation uses that ledger's resolver.
3. `backend/apps/access_control/test_task2_g1d_p3b_root_bound_executor.py` — 29 pure cryptographic/negative tests, no database access.
4. `backend/apps/access_control/test_task2_g1d_p3b_root_bound_ledger.py` — 11 local disposable MySQL integration tests covering successful inactive-only creation/audit, one-use replay denial, signed-roster failures, epoch revocation, executor deactivation, explicit simulated fence and ambiguous-commit reconciliation.
5. This documentation file.

### Security claims explicitly NOT made

- Root public-key pins, trust epoch floors, expected release hashes and expected bundle hashes are provided by **test callers**. This code CANNOT prove independent institutional control, actual human appointment, hardware-backed key custody, or current identity revocation. Production must derive these from separately trusted deployment and evidence channels.
- `simulate_fenced_writers=True` is an assumption in the existing **disposable test fixture**; it does not fence privileged MySQL writers. Production writer fencing is outstanding and mandatory.
- The existing ledger owns persistent replay protection, one-use claims, durable commit, audit receipts and unknown-outcome reconciliation. The pure receipt is **not** a capability or persisted authorization.
- An adapter is not a live authorization endpoint; it is located under `tests_support` and must never be imported into production code.
- Signed evidence and preflight can expire or be revoked after any individual check; operational trust refresh, atomic check/use and mandatory writer controls are still unresolved.
- No live `--apply`, production model, migration, ledger table, official ERD change, role, grant or assignment is authorized. D7 remains withheld.

### Checks performed outside the user's Windows environment

- New Python file compilation passed.
- Pure offline tests passed: **29/29 G1D-P3B** and **32/32 existing G1D-P3A**, **61/61 combined**.
- The 11 new Django/MySQL integration tests were authored but **could not be run in this environment** because Django and the user's disposable MySQL test service are not available. Do not mark them passed until executed locally.
- No production or local user database was connected or modified.

### Owner-local acceptance — mandatory before commit

From `backend`, with the existing `.venv` active:

```powershell
python -B manage.py test apps.access_control.test_task2_g1d_p3b_root_bound_executor apps.access_control.test_task2_g1d_p3b_root_bound_ledger --settings=config.test_settings --noinput
```

Expect **40 new tests**, subject to test discovery. Confirm the test runner creates an isolated random `test_ctug_registration_<hex>` MySQL schema, checks the physical connection and destroys it. Never use `--keepdb` or `config.settings` for these tests. If any test fails, stop and reconcile; do not stage or commit.

Run the full discovered Accounts + Access Control regression using the established PowerShell module enumeration. Baseline after G1D-P3A was **1,065**; expected result with 40 new tests is **1,105** if no other files or tests have changed. Then run:

```powershell
python -B manage.py makemigrations --check --dry-run --settings=config.settings
python -B manage.py prepare_g1d_p1_protected_role --settings=config.settings --expected-db ctug_workspace --ack G1D_P1_PREPARATION_ONLY
```

Migration result should be `No changes detected`; the protected command must perform **read-only inventory** and still report no live `Technical Super Admin` role and no live `--apply` capability. Do not run `migrate`.

Before committing, confirm branch `ronald` and expected HEAD `ab7ab81`, empty Git index, no collision with any of the five target files, and inspect the exact five-file staged diff. Preserve pre-existing changed `backend/.env.example`, `docs/database/full_schema.dbml` and every unrelated or untracked path. Commit only upon all successful local tests and explicit final scoped diff review. Do not push.

### Next after P3B

G1D-P3C: establish independently verifiable production root enrollment, authenticated executor identification and custody, approved ledger schema/retention, real DB write fencing, and audited crash/backup recovery. These require separate owner approvals. No live `Technical Super Admin` provisioning until all required gates pass.
