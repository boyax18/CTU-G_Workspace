# Academic Settings migration and activation runbook

26 November 2026. Continued from `7d9624f` on `ronald`: the owner-authorized live
`access_control.0004`/`0005` migrations, scope-table reader grant and full permission inventory
are complete. The seven Academic Settings migrations passed an isolated restored-data rehearsal
and remain **unapplied to the actual database**. v2.3 is inactive, all 14 backend/frontend switch
pairs are OFF, all 11 relevant launcher mode lists are empty, and independent governance review
is OPEN. The remaining activation gates are in the
[handoff](WF11_Controlled_Activation_Preparation_2026-11-26.md). Launcher `-CheckOnly` performs
actual database reads and still belongs to its separately authorized preflight.

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

**Completed in the authorized maintenance window below.** The earlier dependency and rehearsal
records are retained as history.

`access_control.0005_account_permission_role_scopes` creates `account_permission_role_scopes`.
The migration creates the `AccountPermissionRoleScope` model with a one-to-one reference to
`account_permissions` and a foreign key to `roles`. It contains no data migration or backfill.
The seven-table inventory first confirmed that the target table was absent from local
`ctug_workspace`. The migration ledger was outside that reader's scope. The separately
authorized check below reconciles the ledger and schema.
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

Before any live migration, verify the ledger and schema again in the approved window. If the
ledger records `0005` while the table is absent, stop for schema drift investigation. If an
ancestor is pending, include it explicitly in the forward plan. Apply the targets only after
separate approval of the exact backup, recovery and migration plan. Then verify the table,
ledger and existing overrides before a separately authorized scope-table SELECT grant and full
inventory.

### Authorized ledger check and isolated restore rehearsal

- Verified MySQL 8.4.13 at `127.0.0.1:3306/ctug_workspace` with TLS and the server identity
  pinned by the reduced inventory. The read-only ledger had 29 entries and the schema had
  20 InnoDB tables. Access-control `0001`–`0003` and the account baseline were present once each.
  Both `0004_ordinary_appointments` and `0005_account_permission_role_scopes` had zero entries,
  and both target tables were absent. There were zero entries for the seven Academic Settings
  migrations, and all 24 of their expected tables were absent.
- Captured a single-transaction schema and data export with the ledger and programmable-object
  metadata. The source had zero routines, triggers, events, views and cross-schema foreign
  keys. No Workspace writer process or other open transaction was observed. The two idle
  Workbench sessions' statement counts, server write counters, schema, ledger and all table
  data hashes remained stable across export. The existing credential reached only the export
  client's process environment. The owner-only CurrentUser DPAPI archive
  `wf11-rehearsal-20261126-143306-dfbfb974.sql.dpapi` and its encrypted baseline are stored in
  the ignored local inventory vault. Archive SHA-256
  `5218cdb259057ae7f101e26926f5a281bd9f8390f5ff39c7a632cf7b1721f12e`.
- Restored to a separate MySQL 8.4.13 instance with a unique Windows named pipe, a disposable
  data directory, TCP and MySQL X disabled, and the event scheduler disabled. The restored
  ledger, row counts and row digests matched for all 20 tables. Column and table collation
  metadata matched the source. The restore check paused on 17 `SHOW CREATE TABLE` text differences.
  Each disappeared after normalizing the redundant `CHARACTER SET utf8mb4` spelling immediately
  before the same `COLLATE utf8mb4_unicode_ci`. The original dump definitions matched the live
  definitions exactly.
- Reviewed each forward plan and its DDL, then ran `access_control.0004_ordinary_appointments`
  followed by `access_control.0005_account_permission_role_scopes` on that copy with all 14 Academic
  Settings switches off. Both new tables had zero rows and the corresponding plans were empty
  afterwards. Verified the appointment primary and unique keys, lookup and expiry indexes and
  seven foreign keys. The scope table has primary key `account_permission_id` and two foreign
  keys to `account_permissions` and `roles`. Django database checks passed.
- All 17 existing application tables retained their schema and row data. Django appended two
  migration records, two content types and eight framework permissions. The rehearsal instance
  was shut down and its disposable data directory was removed. Post-rehearsal live verification
  still showed 29 ledger rows and 20 tables, with both scope dependency entries and tables absent.

### Authorized local maintenance execution, 26 November 2026

- Named operator: **Ronald**. The owner confirmed the current session as the local maintenance
  window, with application, worker and administration writers stopped through verification.
  Live migration began at **20:18:12 Asia/Manila**; final verification finished at **20:20:55**.
  The verified target remained MySQL 8.4.13 at `127.0.0.1:3306/ctug_workspace`.
- A fresh full schema/data export was captured at **20:06:46**. It included the 29-row migration
  ledger and programmable-object metadata; routines, triggers, events, views and cross-schema
  foreign keys were absent. No writer or open transaction was observed. Schema, row hashes,
  ledger and server write counters stayed unchanged through export and isolated rehearsal.
  CurrentUser DPAPI archives are in the existing owner-protected ignored vault
  `.local/wf11-inventory-private/`, with prefix `wf11-activation-20261126-200645-ec7ff448`.
  Backup `.sql.dpapi` SHA-256:
  `8bc3c5341e4d0d15d837ae06b2f869f79f34d7b49c13fcf96de743982abeb988`.
  Encrypted readback and the vault ACL were verified.
- Restored to an isolated MySQL 8.4.13 instance using a unique Windows named pipe, with TCP,
  MySQL X and events disabled. All 20 source tables, row hashes, ledger and schema metadata
  matched. As in the earlier rehearsal, 17 redundant `CHARACTER SET utf8mb4` DDL spellings
  normalized to the same collation. Rehearsed `access_control.0004`, `0005`, then the seven
  targets in §3. All 24 Academic Settings tables and **224 columns** matched, including native
  types/defaults, nullability, keys, named constraints and indexes. All **90 prepared integrity
  queries** passed across 144 read-only statements; Django database checks and final leaf plans
  passed. The combined nine-migration restore ended with 46 tables and 38 ledger entries,
  adding 26 content types and 104 framework permissions; all 26 new business/audit tables were
  empty. All 17 original application tables were unchanged. The instance was stopped and its
  disposable data directory removed. Rehearsal `.rehearsal.dpapi` SHA-256:
  `48af604a22d0e6d5d2e639723d7c433da3d9777ddaeae1bbed84d86011173bfc`.
- Applied **only** `access_control.0004_ordinary_appointments`, then
  `access_control.0005_account_permission_role_scopes`, using `config.settings`, existing
  credentials and TLS required in the operator process. Each actual forward plan contained
  exactly its target and its DDL matched the verified rehearsal. Both new tables are empty;
  schema, indexes and all nine new foreign keys match the restored reference. The live database
  has **22 tables / 31 ledger entries**. All 17 original application tables retain their schema
  and row hashes; only two ledger rows, two content types and eight framework permissions were
  added. **35 foreign-key checks, 42 unique-key checks and nine enforced CHECK constraints**
  have zero violations. Django checks passed and six default-off read endpoints returned 503.
  All seven Academic Settings ledger entries and all 24 target tables remain absent.
- Verification stopped before migration until TLS was required. A later hash comparison stopped
  because the baseline reader used `SYSTEM` time and Django used UTC. Matching-session checks
  proved all existing application rows unchanged and reproduced the UTC snapshot exactly;
  no data repair or live migration retry was needed. The isolated checker also accounted for
  MySQL's equivalent timestamp, Boolean and decimal type/default spellings.
- After schema/integrity verification, granted the existing reader SELECT on
  `account_permission_role_scopes` and positively verified USAGE plus exactly eight table SELECTs,
  no other privileges, no roles and unchanged credentials. The full inventory completed at
  **20:19:41**, with persisted scopes available and both scoped-Grant scenarios modeled.
  [Full inventory results](../security/WF11_Permission_Inventory_Preflight_2026-11-26.md).
  Inventory `.inventory.dpapi` SHA-256:
  `6296ac94c9df5cea7d95a9f0b5200fad4bacbb3269522a7a533a06aa9d2372fa`.
- Recovery remains the existing §5 plan: preserve this verified backup, restore to an empty
  isolated replacement and compare schema/data/ledger before any separately owner-authorized
  live replacement or cutover. No destructive restore, reversal, fake ledger entry, HDAC
  provisioning, feature activation, launcher approval or independent review occurred.

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
   CHECKs, uniqueness, foreign keys and operation order. The authorized maintenance record above
   completes the seven-target isolated restored-data rehearsal. Applying those seven migrations
   to the actual database remains outside the current authorization.

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

### Reviewed minimum for phase 1

The validated v2.2 catalogue and the live reduced inventory support this minimum proposal.
The inventory found zero definitions or bindings for the five codes and neither service was
present. The existing cohort includes two eligible accounts with genuine `Admin` assignments.

| Phase-one capability | Active owning service | Exact permission | Proposed binding |
| --- | --- | --- | --- |
| School years and Draft semesters | `academic` | `academic.periods.manage` | `Admin` |
| Courses | `academic` | `academic.courses.manage` | `Admin` |
| Sections | `academic` | `academic.sections.manage` | `Admin` |
| Subjects and lecture/lab units | `clearance` | `clearance.subjects.manage` | `Admin` |
| Current-period dashboard header | `academic` | `academic.catalogue.read` | `Admin` |

All management calls also require the active `academic` service and a genuine active Admin
assignment on an eligible, approved account. Where role context is enforced, a selected Technical
Super Admin context can inherit that account's stored Admin assignment. Exact account Denies
retain precedence, and the protected writer boundary still applies. The catalogue endpoint
authorizes any eligible holder of its exact read permission. Its pinned defaults include Instructor,
Student and Treasurer, so the School Admin-only proposal scopes the initial database binding to
`Admin`. [Management authorization source](../../backend/apps/academic/services.py) ·
[Catalogue authorization source](../../backend/apps/academic/catalogue.py).

Provisioning would require separate authorization for two services, five existing v2.2 definitions
and five active Admin bindings. The schema and launcher gates above still apply. The three phase-one
features currently have empty launcher mode lists. The phase-one decision can use the existing
v2.2 definitions while v2.3 is pending. The live `0004`/`0005` migrations, exact reader grant and
full scope-aware inventory are now complete; the inventory still finds the proposed services,
definitions and bindings absent. Actual Academic Settings migrations, provisioning, launcher
approval and operational acceptance remain pending. Independent governance review and workflow
Human Approval remain open.

#### Phase 1 provisioning and local activation, 26 November 2026

Owner-authorized (Task 2 provisioning and Task 3 local phase-1 activation), at commit `d451c67`.
The audit actor was application Admin account 3, the attributed registration-review operator, as in
the WF-02.05 precedent.

- **Before:** read-only check of `ctug_workspace` (MySQL 8.4.13), 38 ledger rows. Both services and
  all five definitions were absent. There were 2 services, 12 definitions, 12 role bindings, **0
  account overrides**, 47 access-audit rows, eligible Admin accounts 3 and 9, and every Academic
  Settings switch off. No server or worker was running.
- **Provisioning:** `manage.py provision_academic_settings_phase1_local_dev` (the established
  fixed-purpose pattern) ran the phases `metadata` → `bindings` → `activate` → `verify`, each with
  its exact confirmation, at **21:09:26–21:09:31 Asia/Manila**. It created the two services
  (inactive, then activated), the five pinned v2.2 definitions and five Admin bindings (staged
  inactive, then activated), with **19** attributable receipts. The v2.2 chain validated with
  digest `192ba955…6d`.
- **After:** 4 services (all active), 17 definitions, 17 active bindings and **0 account overrides**
  (unchanged). Every other service, definition, binding, role assignment and role scope is unchanged
  (verified inside the transaction). Exactly accounts **3** and **9** hold the five codes, both
  through their stored Admin assignment. Account 9's Technical Super Admin and Instructor roles add
  nothing.
- **Launcher:** `wf11.academic_periods`, `wf11.academic_configuration` and `wf11.academic_catalogue`
  are approved for `local` only. `-Local -CheckOnly` passed: `ctug_workspace` via
  `config.review_decision_local_settings`, 8 of 8 mode features available. The local plan turns on
  exactly `WORKSPACE_ACADEMIC_PERIODS_ENABLED`, `WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED` and
  `WORKSPACE_ACADEMIC_CATALOGUE_ENABLED` and their VITE flags. Every other Academic Settings
  feature is `not-in-mode`, and `lan` is unapproved.
- **Accessibility check:** Django and Vite were started with the launcher-identical local
  environment, without the email worker that the existing local email opt-in would add. All probes
  were read-only.
  - Anonymous requests to school years, courses, subjects, sections and the current period returned
    401 (gate open, session required). Semester fees, onboarding, verification and historical
    correction returned 503 (gate closed). The dashboard served the app shell, and the Vite proxy
    reached Django.
  - With role context enforced and the Admin context selected, accounts 3 and 9 were allowed
    `academic.periods.manage` (including the school-year list), course, subject and section access
    (including the course list) and the current period.
  - Fee configuration was unavailable. The curriculum, offering and teaching-assignment switches
    are off. Account 9 in its Instructor context was refused (`admin_context_required`), and the
    three eligible non-Admin accounts were refused (`access_denied`).
  - No business record was written, and both servers were stopped afterwards.
- **Not performed:** an interactive School Admin sign-in and the write cases of the acceptance
  checklist (SA01–SA04, SA12), which need the owner's credentials and approved test data. Rollback
  remains: turn the phase-1 flags off by removing the `local` mode approval; to withdraw access,
  deactivate exactly these five bindings and two services with compensating receipts.

#### Phase 2 provisioning and local activation, 26 November 2026

This applies the owner policy decisions of 26 November 2026 (School Admin controls the semester fee;
all authorized roles view the current period; no fee revision after any obligation; the
returning-student exception and atomic onboarding creation are kept). Commit `519badd`; audit
actor account 3.

- **Scope:** only pinned v2.2 definitions and default bindings, so no catalogue change was needed:
  - `clearance.teaching_assignments.manage` → Admin (new definition).
  - `academic.catalogue.read` → Student, Instructor and Treasurer (Admin was bound in phase 1).

  Curriculum and offering writes reuse the phase-one `academic.courses.manage` and
  `academic.periods.manage` Admin bindings. Nothing from the v2.3 candidate was provisioned: the fee
  binding move, the three narrow codes and the definition restatements still need independent review.
- **Backup safeguard:** `.local/wf11-phase2-safeguard.py` (ignored; reuses the established helpers
  unchanged).
  - Quiet server; full encrypted dump `wf11-phase2-20261126-215019-574912bc`, SHA-256
    `7ec4243c781c1fc825059ce731a3749e8976efbb53805c6cb380cb8238c59257`.
  - Restored to an isolated pipe-only instance: all 46 tables and 38 ledger rows matched, with every
    row hash and all metadata. The 35 normalised differences are the known redundant charset
    spelling. The disposable copy was removed, and the live database was unchanged before provisioning.
- **Provisioning:** `provision_academic_settings_phase2_local_dev` ran `metadata` → `bindings` →
  `activate` → `verify` (9 receipts), then phase 1 `verify` passed again.
- **Post-check:** only `permissions` (+1), `role_permissions` (+4) and `access_audit_logs` (+9)
  changed. The other 43 tables are byte-for-byte unchanged, including accounts, role assignments,
  account Grants/Denies (still 0), Grant role scopes, services and every business table.
- **Launcher:** `wf11.academic_configuration_governed_writes` is approved for `local`.
  `-Local -CheckOnly` passed with 9 of 9 mode features available. The local plan turns on the
  periods, configuration, curriculum, offering, teaching-assignment and catalogue switches and their
  VITE flags. Lifecycle, fees, verification, onboarding and historical correction remain
  `not-in-mode`, and `lan` is unapproved.
- **Live check:** launcher-identical local environment, Django and Vite only, read-only.
  - Anonymous requests to all phase 1–2 routes returned 401. Fees, onboarding, verification and
    historical correction returned 503.
  - With role context enforced, the Admin contexts of accounts 3 and 9, and account 9's Technical
    Super Admin context through its stored Admin assignment, may manage school years, courses,
    subjects, sections, curricula, offerings and instructor lookup, and view the current period.
  - Students 6 and 15, Instructor 13 and account 9 in its Instructor context may view the current
    period only; every management call is refused. Fee configuration is unavailable. There is no live
    Treasurer account, so the Treasurer binding is covered by isolated tests.
- **Automated isolated verification** (disposable MySQL, mocked browser APIs): backend
  `apps/academic apps/finance apps/clearance apps/access_control` 1,686 run, all passed; Academic Settings
  browser suites 46/46 (run one file at a time; the same suites timed out when run concurrently with the backend suite, and each failing case passed alone). These cover fee approval, activation, onboarding, atomic
  participation, clearance and obligation creation, and duplicate and rollback prevention. Fees,
  activation and onboarding cannot run live until v2.3 is independently approved and provisioned.

#### Catalogue v2.3 provisioning and local activation, 27 November 2026

This was authorized under the owner's project-governance amendment
([local-development authorization](../security/WF11_Owner_Local_Development_Authorization_2026-11-27.md)).
**It is not independent approval.** The v2.1, v2.2 and v2.3 independent reviews stay OPEN and remain mandatory
for production release. Code commit: `3d10933` (reviewed patch `13782a25…` applied unchanged, plus the separate
owner-authorization path). Audit actor: account 3.

- **Backup safeguard:** `.local/wf11-v23-safeguard.py` (ignored; it reuses the established helpers).
  - The server was quiet: the owner stopped the launcher first.
  - Encrypted full dump `wf11-v23-20261127-015824-8e44fa15`, SHA-256
    `f5994f6bd312776a999d8efce6b756640f8688ea25058e68b49aca1663df9076`.
  - Restored to an isolated pipe-only instance: all 46 tables and 38 ledger rows matched, with every row hash
    and all metadata (35 normalised charset spellings). The live database was unchanged by the check.
- **Provisioning:** `provision_academic_settings_v2_3_local_dev` ran `verify` (NOT_STARTED) → `metadata` →
  `restate` → `bindings` → `activate` → `verify` (VERIFIED), with basis
  `owner_local_development_authorization`. Phase 1 and phase 2 `verify` passed afterwards.
  - Service `finance`.
  - Five definitions: `finance.fee_schedule.manage`, `academic.profile.self.read`,
    `academic.enrollment_verifications.record`, `academic.semester_onboarding.self.submit` and
    `academic.historical_participation.correct`.
  - The receipted restatements of `academic.courses.manage` and `academic.periods.manage`.
  - Five bindings: Admin → fee, verification and historical correction; Student → onboarding and profile read.
  - No Treasurer fee binding, account Grant or Deny was created.
- **Post-check:** only `services` +1, `permissions` +5, `role_permissions` +5 and `access_audit_logs` +19
  changed. The other 42 tables are byte-for-byte unchanged, including accounts, role assignments, account
  Grants/Denies and role scopes. It was re-confirmed after the live check.
- **Launcher:** every Academic Settings feature is approved for `local` only; `lan` and production are
  unchanged. `-Local -CheckOnly` passed with 16 of 16 mode features available.
- **Live check:** launcher-identical local environment, Django and Vite only, read-only, role context enforced.
  - **Anonymous requests:** all 12 Academic Settings routes, including fees, onboarding, verification and
    historical correction, returned 401. The dashboard served the app shell.
  - **Admin contexts** (accounts 3 and 9, and account 9's Technical Super Admin context through its stored
    Admin assignment): allowed configuration, fee configuration and approval, semester lifecycle, period
    corrections, verification and historical correction. Onboarding was refused.
  - **Students 6 and 15:** allowed onboarding read, write and finalization, and the current period; every
    management operation was refused.
  - **Instructor 13, and account 9 in its Instructor context:** current period only (`access_denied` or
    `admin_context_required`).
  - No business record was written.
- **Not performed:** the interactive acceptance cases, which need the owner's credentials and approved test
  data. Human Approval is unchanged. Rollback: remove the `local` mode approvals, then deactivate exactly these
  five bindings and the finance service with compensating receipts.

Rollback activation by turning **both** backend and frontend approved phase flags off, stopping
the corresponding servers/workers, reloading/rebuilding the frontend and checking refusal behavior.
This disables access; it must not reverse schema migrations, delete onboarding/fee records, erase
Denies or undo previously committed business events. Reconcile uncertain write outcomes by reads
before retrying. Preserve all prior-phase evidence and obtain approval before resuming.
