# Academic Settings migration and activation runbook — prepared, not executed

26 November 2026. Every database command and activation below is a **future operator procedure**,
subject to the separate authorizations in the [handoff](WF11_Controlled_Activation_Preparation_2026-11-26.md).
The role-scope section records the later authorized live schema observation. The live migration
ledger remains unverified. Launcher `-CheckOnly` performs real database reads, so it belongs to the
separately authorized preflight.

## 1. Exact migration dependency closure

Verified using Django `MigrationLoader(None)` and `MigrationAutodetector`, with every database
connection explicitly forbidden. There is no model drift. The complete machine-readable graph
and expected schema are in [offline_repository_evidence.json](../../review_only/academic_settings_v2_3/offline_repository_evidence.json).

| Migration | Immediate parents |
| --- | --- |
| `access_control.0001_initial` | None |
| `accounts.0001_initial` | `access_control.0001_initial` |
| `academic.0001_initial` | `accounts.0001_initial` (swappable user dependency) |
| `academic.0002_audit_reason_note` | `academic.0001_initial` |
| `academic.0003_academic_configuration` | `academic.0002_audit_reason_note`, `accounts.0001_initial` |
| `finance.0001_semester_fee_configuration` | `academic.0003_academic_configuration`, `accounts.0001_initial` |
| `academic.0004_student_semester_onboarding` | `academic.0003_academic_configuration`, `accounts.0001_initial` |
| `clearance.0001_semester_clearance` | `academic.0004_student_semester_onboarding`, `accounts.0001_initial` |
| `finance.0002_fee_obligation` | `academic.0004_student_semester_onboarding`, `finance.0001_semester_fee_configuration`, `accounts.0001_initial` |

Finance `0001` and academic `0004` are sibling branches after academic `0003`; clearance `0001`
and finance `0002` are not dependencies of each other. Do not infer a dependency from their
generation timestamps. The first two prerequisites must already be recorded and schema-consistent
in the actual application; otherwise stop for a separate baseline migration review. Do not use a
bare `migrate` to apply all unrelated pending workflows.

### Pending role-scope inventory dependency

`access_control.0005_account_permission_role_scopes` creates `account_permission_role_scopes`.
The migration creates the `AccountPermissionRoleScope` model with a one-to-one reference to
`account_permissions` and a foreign key to `roles`. It contains no data migration or backfill.
The 26 November 2026 preflight confirmed that the target table is absent from local
`ctug_workspace`. The migration ledger was outside the seven-table reader scope. The next
preflight must distinguish a pending migration from a ledger/schema mismatch.
[Migration source](../../backend/apps/access_control/migrations/0005_account_permission_role_scopes.py) ·
[Live inventory evidence](../security/WF11_Permission_Inventory_Preflight_2026-11-26.md).

Django's offline migration loader verified this dependency closure with database connections
blocked. The scope migration is a prerequisite for the full permission inventory and any
scope-enabled evaluation. It is separate from the seven Academic Settings schema targets above.

| Migration | Immediate parents |
| --- | --- |
| `access_control.0001_initial` | None |
| `accounts.0001_initial` | `access_control.0001_initial` |
| `access_control.0002_accountrole` | `access_control.0001_initial`, `accounts.0001_initial` |
| `access_control.0003_remaining_access_control` | `access_control.0002_accountrole`, `accounts.0001_initial` |
| `access_control.0004_ordinary_appointments` | `access_control.0003_remaining_access_control`, `accounts.0001_initial` |
| `access_control.0005_account_permission_role_scopes` | `access_control.0004_ordinary_appointments` |

After authorization, verify ledger rows and schema for this closure using a separately bounded
read-only preflight. Review and rehearse `manage.py migrate access_control
0005_account_permission_role_scopes --plan` against an isolated restore. If the ledger already
records `0005` but the table is still absent, stop for schema drift investigation. If any ancestor
is pending, include it explicitly in the plan for review. Apply the migration only after separate
approval of the exact backup, recovery and migration plan. Then verify the table, ledger and
existing overrides before a separately authorized scope-table SELECT grant and full inventory.

## 2. Required backup and pre-migration validation

1. Obtain explicit authorization naming the seven Academic Settings migrations, database/server, settings profile,
   maintenance window, operator and restore strategy. Permission inventory authorization alone
   permits none of this. Keep every Academic Settings feature off and all application/worker/
   administration writers stopped for backup, migration and verification.
2. Using the approved existing local settings and credential mechanism, verify `SELECT DATABASE(),
   @@hostname, @@port, VERSION();` identifies the intended local `ctug_workspace`. Record MySQL
   version, engine, charset/collation, SQL mode, time zone and available disk space. Require the
   supported MySQL version and enforced CHECK constraints; do not substitute SQLite/MariaDB.
   Check the required account/access-control baseline, foreign-key target types and migration
   ledger; inventory other pending migrations without applying them.
3. Capture schema definitions, row counts and protected snapshots of existing role bindings,
   account overrides and scopes. Confirm the expected new Academic Settings tables do not exist
   unless their migrations are already applied and validated. A table/ledger disagreement is a
   partial migration requiring investigation, not an invitation to use `--fake`.
4. Create a **full schema+data backup**, including `django_migrations`, triggers/routines/events
   and existing permission rows. Use the owner-installed, server-compatible executable paths
   and a pre-existing owner-protected option file (first client argument); do not place a password
   on the command line or change database credentials. Example PowerShell, future approved window:

```powershell
# $MySqlDump and $MySql are verified full executable paths supplied by the operator.
# $ExistingClientOptions is an EXISTING protected file for the approved backup identity.
# $BackupSql is a new restricted absolute file path outside Git, without an existing backup there.
& $MySqlDump "--defaults-extra-file=$ExistingClientOptions" --single-transaction --quick --routines --triggers --events --hex-blob --set-gtid-purged=OFF --no-tablespaces --default-character-set=utf8mb4 --skip-lock-tables "--result-file=$BackupSql" ctug_workspace
if ($LASTEXITCODE -ne 0) { throw 'Backup failed; do not migrate.' }
Get-FileHash -LiteralPath $BackupSql -Algorithm SHA256
```

5. Check the backup is nonempty and complete and retain its checksum, protected location, server
   identity, application commit and exact ledger. Rehearse restoration to an empty schema on an
   isolated replacement MySQL instance; verify row counts, schema, ledger and critical data before
   accepting the backup. Keep its event scheduler disabled during rehearsal; review routines,
   definers and hardcoded schema references so they cannot contact the actual database. A dump
   completing successfully alone is insufficient restore evidence.
6. Generate offline evidence again at the reviewed commit:

```powershell
backend\.venv\Scripts\python.exe review_only\academic_settings_v2_3\inspect_offline.py --write
```

   Rehearse the **same** dependency-aware migration sequence on the restored isolated copy, not
   just an empty test schema. Review each target's `sqlmigrate` output for native enums, timestamps,
   CHECKs, uniqueness, foreign keys and operation order. The real live precheck and rehearsal are
   still outstanding; this task's isolated test database migrations do not replace that evidence.

`--single-transaction` is consistent for InnoDB data; concurrent DDL can invalidate a dump, and
nontransactional tables need a separately reviewed backup/lock method. Keep writers and DDL
quiesced. [MySQL backup documentation](https://dev.mysql.com/doc/refman/8.4/en/mysqldump.html).

## 3. Exact forward execution sequence (after approval only)

Use an owner-approved fresh operator process, repository `backend/`, the reviewed Python venv,
existing **`config.settings` local deployment profile** and existing credentials. Do not use the
test wrapper/settings for actual migration. Confirm all 14 feature flags remain off in that
process, and that the existing role-context startup validations pass without bypassing them.

For **each target below**, in order: inspect the actual ledger first; skip an already-applied target
only after schema validation; otherwise run `migrate APP NAME --plan --settings=config.settings`.
Stop if the plan contains any unapply/backward step, baseline/unrelated migration, or unexpected
operation. Then run `sqlmigrate APP NAME --settings=config.settings` for review and execute the
corresponding command. Stop on the first error; do not continue to later commands.

```powershell
# Run only unapplied, prevalidated targets, one at a time. Check $LASTEXITCODE after EACH command.
.\.venv\Scripts\python.exe manage.py migrate academic 0001_initial --settings=config.settings --noinput
.\.venv\Scripts\python.exe manage.py migrate academic 0002_audit_reason_note --settings=config.settings --noinput
.\.venv\Scripts\python.exe manage.py migrate academic 0003_academic_configuration --settings=config.settings --noinput
.\.venv\Scripts\python.exe manage.py migrate finance 0001_semester_fee_configuration --settings=config.settings --noinput
.\.venv\Scripts\python.exe manage.py migrate academic 0004_student_semester_onboarding --settings=config.settings --noinput
.\.venv\Scripts\python.exe manage.py migrate clearance 0001_semester_clearance --settings=config.settings --noinput
.\.venv\Scripts\python.exe manage.py migrate finance 0002_fee_obligation --settings=config.settings --noinput
```

These are not a paste-and-run batch: Django can reverse newer migrations when an older target is
requested, hence the mandatory ledger/forward-plan gate before **every** target. Changes to Django
content types/permissions from normal post-migrate handlers must be included in the reviewed plan;
they are framework metadata, not HDAC v2.3 provisioning. Do not run catalogue initialization,
role-assignment or Grant/Deny commands as an implicit part of schema migration.

## 4. Post-migration schema, ledger and integrity validation

Keep features and writers off. Under the separately approved read-only validation operation:

- Run the prepared [schema_and_integrity_checks.sql](../../review_only/academic_settings_v2_3/schema_and_integrity_checks.sql)
  against the verified database using a reader. It contains identity, read-only transaction,
  `SHOW CREATE TABLE`, row counts, foreign-key orphan checks, UNIQUE duplicate checks and
  participation/onboarding/clearance/fee consistency queries, ending with ROLLBACK.
- Compare **all 24** Academic Settings tables against `expected_schema` in the offline evidence:
  columns, lengths/decimal precision, nullability, native enum choices, PK/FK targets, unique
  lifecycle slots and CHECK constraints. Compare default expressions, indexes and full DDL with
  the reviewed `sqlmigrate` output/restored isolated reference. Do not rely just on table presence.
- Confirm each of the seven exact `(app,name)` ledger rows exists once, with no unexpected
  applied/unapplied migrations. `showmigrations academic clearance finance --settings=config.settings`
  and each current leaf's `migrate ... --plan` must agree with SQL ledger evidence and show no
  remaining operation for these targets. Do not assert that unrelated pending migrations vanished.
- Fresh installation must have zero rows in the new business/audit tables: migrations create
  schema, not years, students, fees or participations. Every orphan, duplicate and consistency
  violation count must be zero. If any target schema already existed, compare against its approved
  pre-migration snapshot instead of assuming it was empty.
- Compare old business-table counts and a protected canonical data-only dump/hash against the
  maintenance-window baseline; account/role/Grant/Deny/scope data must be unchanged. Account for
  reviewed framework post-migrate metadata and intended seven ledger additions separately.
  Run Django model checks against the schema and application smoke reads with switches still off;
  expect refusals, not usable Academic Settings. Retain evidence without personal fields.
- Rerun integrity checks after later approved onboarding acceptance: one participation, one
  clearance and one fee obligation per Student+semester; confirmed subjects/signatories match;
  original fee snapshot unchanged; atomic rollback/idempotence and older records preserved.

## 5. Partial-failure recovery

MySQL DDL can implicitly commit. A Django migration can leave some tables/constraints committed
without its final ledger row; a transaction rollback cannot promise to undo the migration.
Even atomic individual DDL statements do not make the multi-statement migration atomic.
[MySQL implicit-commit documentation](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html).

On error: stop all writers and later targets; retain switches off; capture the error, last attempted
migration, actual `SHOW CREATE TABLE`/constraint inventory and ledger in restricted evidence.
Preserve the pre-change backup. Do not retry blindly, fake ledger rows, drop conflicting objects,
reverse migrations over data, or relax constraints. Reproduce the exact partial state on an isolated
restore to determine whether a reviewed forward repair is sufficient.

Preferred recovery when rollback is required: DBA restores the full pre-change dump into an empty
`ctug_workspace` on a separate isolated replacement instance and verifies schema/data/ledger against
the recorded checksum and counts. The dump was made without `--databases`, allowing an explicitly
chosen empty recovery schema. Example restore command (future approved recovery only):

```powershell
# Options must identify the ISOLATED recovery instance, not the running application server.
# Use a simple reviewed forward-slash backup path; the recovery schema must be empty.
& $MySql "--defaults-extra-file=$ExistingRecoveryClientOptions" --database=ctug_workspace "--execute=source $ReviewedBackupPath;"
if ($LASTEXITCODE -ne 0) { throw 'Restore failed; preserve evidence and keep writers stopped.' }
```

After comparison, the owner/DBA authorizes the exact replacement/cutover or forward-repair procedure.
Actual destructive restoration/replacement is not preauthorized here. If business writes occurred
after backup, reconcile them using the approved log/recovery strategy before cutover; do not discard
them. Restore the matching application version, keep the Deny compatibility strategy intact, rerun
identity/ledger/schema/integrity checks, then obtain a separate restart/activation approval.

## 6. Exact feature-switch inventory and dependencies

Every switch is true only for literal environment value `1`; default is off. Backend source:
`config/settings.py`; frontend sources: `academicPeriodsConfig.ts`, `academicConfigurationConfig.ts`,
`academicCatalogueApi.ts`, `semesterFeesConfig.ts`, `onboardingConfig.ts`. The generated registry
snapshot lists exact `Feature.requires` values. Codes below are current → candidate where changed.
All mutations also require approved active non-framework accounts, genuine role assignment, the
valid selected context, active owning services, effective exact permission, Deny precedence and
locked reauthorization. The protected executor has no academic operation; it must not be bypassed.

| Backend environment variable | Exact frontend environment variable | Runtime dependency / permission |
| --- | --- | --- |
| `WORKSPACE_ACADEMIC_PERIODS_ENABLED` | `VITE_WORKSPACE_ACADEMIC_PERIODS_ENABLED` | Draft periods; `academic.periods.manage`; Admin context |
| `WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED` | `VITE_WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED` | Periods flag; `academic.periods.manage`; real valid dates + offerings + approved fee for activation; live impact/obligation sources |
| `WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED` | `VITE_WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED` | Periods flag; `academic.periods.manage`; reason and acknowledged real impacts |
| `WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED` | `VITE_WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED` | Own server gate; courses `academic.courses.manage`, subjects `clearance.subjects.manage`, sections `academic.sections.manage`; matching code for area reads |
| `WORKSPACE_ACADEMIC_CURRICULUM_WRITES_ENABLED` | `VITE_WORKSPACE_ACADEMIC_CURRICULUM_WRITES_ENABLED` | Configuration flag; `academic.courses.manage` |
| `WORKSPACE_ACADEMIC_OFFERING_WRITES_ENABLED` | `VITE_WORKSPACE_ACADEMIC_OFFERING_WRITES_ENABLED` | Configuration flag; `academic.periods.manage`; matching published curriculum + section + semester |
| `WORKSPACE_ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED` | `VITE_WORKSPACE_ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED` | Configuration flag; `clearance.teaching_assignments.manage`; eligible genuine Instructor and period offering |
| `WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED` | `VITE_WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED` | Own server gate, academic+finance services; `finance.fee_schedule.manage` through genuine Admin **role binding** |
| `WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED` | `VITE_WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED` | Fee configuration flag; same exact code; explicit confirmation, separate zero confirmation; no obligations for revisions |
| `WORKSPACE_ACADEMIC_CATALOGUE_ENABLED` | `VITE_WORKSPACE_ACADEMIC_CATALOGUE_ENABLED` | Own gate, academic service; `academic.catalogue.read`; no Admin assignment needed |
| `WORKSPACE_STUDENT_ONBOARDING_ENABLED` | `VITE_WORKSPACE_STUDENT_ONBOARDING_ENABLED` | Periods flag; `academic.profile.self.read` reads, `clearance.requests.self.submit` → `academic.semester_onboarding.self.submit` writes; Student context and prior-clearance/gap eligibility |
| `WORKSPACE_ENROLLMENT_VERIFICATION_ENABLED` | `VITE_WORKSPACE_ENROLLMENT_VERIFICATION_ENABLED` | Own runtime gate; registry requires periods; `academic.profiles.manage` → `academic.enrollment_verifications.record`; Admin context, target Student, no self-verification |
| `WORKSPACE_STUDENT_ONBOARDING_FINALIZATION_ENABLED` | `VITE_WORKSPACE_STUDENT_ONBOARDING_FINALIZATION_ENABLED` | Onboarding flag; matching Verified evidence, valid subjects/instructors, approved fee; active academic+clearance+finance services; one atomic transaction |
| `WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED` | `VITE_WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED` | Runtime periods gate; frontend also requires verification flag; registry requires verification + fee configuration; both old broad codes → `academic.historical_participation.correct`; original fee + reviewed evidence; Closed/Archived only |

Additional practical dependencies: readiness reads actual finance/clearance/onboarding tables even
before Student access, so apply/validate the **whole seven-migration closure** before lifecycle use.
Verification UI uses configuration course/subject lists; make them accessible to the authorized
Admin first. Finalization registry requires onboarding + fee configuration, but the safe operational
sequence also requires fee approval, governed offerings/assignments and verification readiness.
Catalogue, configuration and fee runtime gates are independently coded; do not invent a base-flag
dependency where source has none. The recommended order deliberately establishes periods first.

Registry bundles: lifecycle has **both** transitions and corrections; governed configuration writes
has **all three** curriculum/offering/teaching flags. Merely approving either bundle for a mode
would enable more than one capability. A later phase-limited activation requires a separately
reviewed split/selection of those registry bundles; this preparation does **not** make that change.

## 7. Launcher modes and safest proposed activation order

Actual launcher modes are `local` (`.\Start-CTUG-LAN.ps1 -Local`,
`config.review_decision_local_settings`, loopback `http://127.0.0.1:5173`) and `lan`
(`.\Start-CTUG-LAN.ps1`, `config.settings`, HTTP LAN Option A synthetic-only guard). Both point to
the existing `ctug_workspace` settings. There is **no currently approved mode for any of these 11
Academic Settings features** (`modes=frozenset()`). The launcher forces their frontend flags to `0`.
Its status is `not-in-mode`; assigning `.env` values cannot substitute for mode approval.
All academic switches are refused at startup outside `WORKSPACE_DEPLOYMENT_PROFILE=local`.
No production release guard, route whitelist, executor or ordinary-appointment safeguard is changed.

Propose `local` first, after review; leave `lan` unapproved. A loopback process is a smaller
operational exposure, not an approval. Existing local WF-02 decisions/email options remain governed
by their own settings: do not accidentally activate workers, send notifications or alter their gates.

| Proposed phase, each separately approved | Exact switches from §6 | Acceptance gate |
| --- | --- | --- |
| 0. Prepare | None | Live read-only inventory reviewed; independent governance/provisioning plan; full backup/restore rehearsal; seven migrations validated; code/pins reviewed |
| 1. School Admin entry | `WORKSPACE_ACADEMIC_PERIODS_ENABLED`, `WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED`, `WORKSPACE_ACADEMIC_CATALOGUE_ENABLED`, and matching VITE flags | Open School years & semesters and Academic settings, create Draft year/semesters, courses/subjects/sections. Student onboarding, fee approval, lifecycle confirmations still off. |
| 2. Curriculum, offerings, instructors | `WORKSPACE_ACADEMIC_CURRICULUM_WRITES_ENABLED`, `WORKSPACE_ACADEMIC_OFFERING_WRITES_ENABLED`, `WORKSPACE_ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED`, matching VITE flags | Publish versioned plan, create offerings, assign actual eligible instructors; verify exact-area Denies. Reviewed curriculum/offering governance required. |
| 3. Fee Draft then approval | First `WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED`, then `WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED`, matching VITE flags | Reviewed Admin fee binding provisioned; Draft does not approve; approved rate does not activate; zero requires confirmation; Treasurer refused. |
| 4. Explicit semester activation | `WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED`, matching VITE flag | Dates/offerings/approved fee ready; review warning/version/current Active identity; explicit owner-approved School Admin confirmation. Bundle must be split if corrections are not also approved. |
| 5. Optional controlled period corrections | `WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED`, matching VITE flag | Separate owner approval of scope/impact acknowledgments; can remain off while initial access is accepted. |
| 6. Official verification | `WORKSPACE_ENROLLMENT_VERIFICATION_ENABLED`, matching VITE flag | Accepted proof/source/privacy policy, narrow permission and legacy Deny guard installed under separate approval; real in-person review only; no CTU integration invented. |
| 7. Student onboarding Drafts | `WORKSPACE_STUDENT_ONBOARDING_ENABLED`, matching VITE flag | School Admin phases accepted; Active semester ready; selected Student and prior-clearance/gap checks accepted; finalization stays off. |
| 8. Atomic Student finalization | `WORKSPACE_STUDENT_ONBOARDING_FINALIZATION_ENABLED`, matching VITE flag | Accepted minimum clearance/signatory scope, fee policy, all services and schemas; separate approval for creation of real participation+clearance+fee records; idempotence/security acceptance. |
| 9. Historical correction (optional, last) | `WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED`, matching VITE flag | Resolve two-person/protection policy; original rate and evidence available; independent historical record protection accepted. May remain off indefinitely without blocking phases 1–8. |

At each approved phase, review the exact code change to registry mode membership/bundle selection,
review generated launch environment, then separately authorize `-CheckOnly` (actual DB reads) and
launch. Check only the named features are `available`, permissions are effective in the selected
context, browser requests reach the matching default-off server gates and UI has no stale build.
VITE flags are build/dev-server inputs, so a backend-only restart cannot update the frontend.
Do not paste the entire feature matrix as environment assignments or approve every feature at once.

Phase 1 uses only existing exact permissions. It can be reviewed and authorized separately while
v2.3 remains pending, after the actual inventory, schema/backup gates and existing-boundary review.
Installing the candidate is not a prerequisite for merely opening Draft periods/courses/subjects/
sections. New grants, governed curriculum/offering writes, fee configuration and narrow Student
permission transitions retain their own independent governance and operational gates.

Rollback activation by turning **both** backend and frontend approved phase flags off, stopping
the corresponding servers/workers, reloading/rebuilding the frontend and checking refusal behavior.
This disables access; it must not reverse schema migrations, delete onboarding/fee records, erase
Denies or undo previously committed business events. Reconcile uncertain write outcomes by reads
before retrying. Preserve all prior-phase evidence and obtain approval before resuming.
