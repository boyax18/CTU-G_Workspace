# Core Task 2 — Technical Super Admin Foundation completion report

Assessment date: 2026-11-13, Asia/Manila. Branch: `ronald`.

## Executive summary and final verdict

**INCOMPLETE. Production release is BLOCKED.**

This work implements the two-tier access-control management restriction, safe
API failure handling, strict signed evidence validation, deployment rejection
checks, and tested disposable MySQL provisioning/bootstrap/ledger candidates.
It does **not** complete P3C6B's production trusted executor integration or P3C7's
institutional trust, persistent production storage and actual-schema writer
fencing. P4/P5 run only in guarded disposable tests. Their operational release
is unavailable. Passing tests are not production authorization.

No live protected role/account was created, promoted or activated. No live
database DML, privilege changes, migrations, credential issuance, ERD edits,
Git push, Docker installation or external messaging was performed. The ordinary
School Admin bootstrap remains its existing separately gated mechanism; it is
not a Technical Super Admin bootstrap.

## Checkpoint reconciliation and phase statuses

Inspected HEAD matched the supplied checkpoint exactly:
`29af78ec98bb9820a163005f65ab9e678db884a7`, on `ronald`. The initial index was
empty. The reported 1,286-test baseline was independently rerun successfully.
Historical documents contain older source-export and pending-verification
language; they are not current production attestations. The new assessment and
security contract record the actual results without rewriting that history.

| Phase/control | Actual status at this assessment |
| --- | --- |
| Earlier profile/preflight and G0/G1A/G1B/G1C/G1D P0/P1 foundations | Existing read-only tools and test candidates; covered by the passing checkpoint regression; no operational authority inferred |
| P3A root-endorsed registry | Existing synthetic/test-only contracts; no institutional enrollment |
| P3B root-bound executor/ledger | Existing disposable composition; no production executor |
| P3C1 writer inventory | Existing static triage; cannot enumerate every DB/external writer |
| P3C2 grants triage / P3C4 DBA visibility | Existing read-only tools; production grants/session inventory not newly attested |
| P3C3 recovery holds | Existing test contracts; no institution-approved recovery ceremony |
| P3C5 privilege rehearsal | 21/21 actual checks passed on a newly initialized separate MySQL 8.4 server; demonstration schema only; Windows cleanup corrected and rerun successfully under P3C7 recovery scope |
| P3C6A | Existing opt-in fail-closed guard preserved; enabled enforcement still denies all covered writes |
| **P3C6B** | **PARTIAL:** runtime two-tier governance restriction and unavailable-writer HTTP handling implemented; authenticated trusted database execution/ordinary-writer integration absent |
| **P3C7** | **PARTIAL:** signature validator, disposable persistent ledger, one-use attempts, concurrency/rollback/uncertain-outcome tests and deployment diagnostics implemented; production security prerequisites and remaining integrations absent |
| **P4** | **ISOLATED CANDIDATE:** inactive technical role plus exact six inactive bindings and audit tested against application tables; no live apply path |
| **P5** | **ISOLATED CANDIDATE:** independently signed existing-School-Admin bootstrap tested with atomic activation, assignment, effective permission checks and audit; no live account nomination/elevation |
| **Final acceptance** | **NOT MET:** regression and migration drift checks pass; production architecture and institutional gates remain unresolved |

No new major phase is introduced. Remaining engineering belongs within these
locked phases; the verdict is not IMPLEMENTATION COMPLETE BUT RELEASE BLOCKED,
because production integration work itself remains unfinished.

## Exact source changes

Created:

1. `backend/apps/access_control/technical_admin.py` — protected composite-profile predicate using the existing dynamic evaluator.
2. `backend/apps/access_control/protected_requests.py` — bounded canonical, exact-context, three-signature Ed25519 verification without I/O or write capabilities.
3. `backend/apps/access_control/checks.py` — explicit deployment security errors for absent enforcement and unverified executor/security gates.
4. `backend/apps/access_control/management/commands/report_task2_acceptance.py` — offline status/blocker report; release-required mode refuses.
5. `backend/apps/access_control/tests_support/task2_protected_executor_test_only.py` — actual-table disposable provisioning/bootstrap and scratch durable ledger candidate.
6. `backend/apps/access_control/tests_support/task2_signed_fixture_test_only.py` — ephemeral fictional signer/key fixtures.
7. `backend/apps/access_control/test_task2_protected_requests.py` — evidence and release rejection tests.
8. `backend/apps/access_control/test_task2_protected_executor.py` — guarded MySQL provisioning, bootstrap, replay, concurrent execution and recovery tests.
9. `backend/requirements-security.txt` — optional verification dependency, pinned to the already installed version.
10. `docs/implementation/access-control/TASK2_P3C6B_P3C7_P4_P5_SECURITY_CONTRACT.md` — behavior, threat boundaries, storage and remaining implementation/release contract.
11. `docs/implementation/access-control/CORE_TASK_2_COMPLETION_REPORT.md` — this report.

Modified:

1. `backend/apps/access_control/apps.py` — register deployment checks.
2. `backend/apps/access_control/delegation.py` — require the protected composite profile plus effective management/delegation authority.
3. `backend/apps/access_control/test_mutations.py` — give positive fixtures the required composite profile, preserve negative protections, add three profile-removal/School Admin denial cases.
4. `backend/apps/accounts/registration_review_api.py` — map writer-unavailable failures to generic HTTP 503.
5. `backend/apps/accounts/test_registration_review_api.py` — two no-write API tests for enabled writer enforcement.
6. `backend/apps/access_control/tests_support/g1d_p3c5_windows_pipe_fence_test_only.py` — verified graceful shutdown, absolute-path cleanup guards and surfaced cleanup failure.
7. `backend/apps/access_control/test_task2_g1d_p3c5_windows_isolated.py` — four offline recovery/cleanup tests.

## Database schema and migrations

No application model, migration, official ERD or real-database schema changed.
`makemigrations --check --dry-run --settings=config.settings` returned
**No changes detected**. No `migrate` command was run against the real database.

The isolated candidate explicitly creates `task2_candidate_control` and
`task2_candidate_ledger` only inside a fresh guarded test schema. Both use
InnoDB, exact binary ASCII evidence identifiers, unique request/nonce/operation
scopes and application/audit foreign keys. They are dropped after each test;
the runner destroys the disposable database. This is storage design/testing,
not approval or installation of a persistent production evidence schema.

The existing separate-server privilege rehearsal creates synthetic tables/users
only in its own fresh data directory/private named-pipe instance. It does not
use the normal MySQL service for privilege experiments.

## Git commits

- Starting checkpoint: `29af78ec98bb9820a163005f65ab9e678db884a7`.
- Verified implementation/security-contract commit: `185c27ef9ffa903ad2af06861c31c983e104702b`
  (`feat(access-control): enforce technical governance and test protected ceremonies`, 17 files).
- This report is committed separately after verification. Its own commit can be
  resolved with `git log -1 --format=%H -- docs/implementation/access-control/CORE_TASK_2_COMPLETION_REPORT.md`;
  a commit cannot contain its own eventual hash.
- No push was performed.

## Regression commands and actual results

All Python commands used `backend/.venv/Scripts/python.exe -B` from `backend`.
The base Python executable initially required sandbox escalation; the approved
verification commands then ran using the existing environment. No dependencies
were installed. Versions observed: Python 3.13.7, Django 6.1.2, cryptography 46.0.4.

Full-suite PowerShell enumeration (54 checkpoint modules, 56 after additions):

```powershell
$testModules = Get-ChildItem apps/accounts,apps/access_control -Filter 'test*.py' -File |
    Sort-Object FullName | ForEach-Object { 'apps.' + $_.Directory.Name + '.' + $_.BaseName }
& .venv/Scripts/python.exe -B manage.py test @testModules --settings=config.test_settings --noinput --verbosity 1
```

| Verification | Actual result |
| --- | --- |
| Checkpoint full regression | **1,286/1,286 passed**, 356.945 seconds; random MySQL database created/destroyed |
| Initial new evidence/executor suite | **50/50 passed**, 30.641 seconds |
| Mutations + registration-review API + P3C6A focused suite | **91/91 passed**, 19.884 seconds |
| Expanded new suite with concurrency/interruption/lost acknowledgment | **54/54 passed**, 29.678 seconds |
| Full regression before the rehearsal cleanup correction | **1,345/1,345 passed**, 311.715 seconds |
| Windows adapter suite including four cleanup tests | **21/21 passed**, 0.027 seconds; offline, no DB startup |
| Final full regression | **1,349/1,349 passed**, 423.343 seconds; all 56 modules, disposable MySQL database created/destroyed |
| Migration drift, normal settings, check/dry-run | **Passed: No changes detected**, exit 0 |
| Deployment security check | **Expected refusal**, exit 1: `access_control.E201`, `access_control.E202`, plus six existing deployment warnings |
| Offline acceptance with `--require-release` | **Expected refusal**, exit 1: verdict INCOMPLETE and precise blockers |
| Existing Windows separate-server MySQL privilege rehearsal | **21/21 passed**, exit 0; production writer fence explicitly False |
| Existing source-only writer scanner | **125 Python files scanned; 15 findings** (14 ORM mutation, one dynamic SQL), requiring review across eight files; not proof of exclusive writers |
| Scoped whitespace/diff review | `git diff --check` passed |

Focused commands:

```powershell
& .venv/Scripts/python.exe -B manage.py test apps.access_control.test_task2_protected_requests apps.access_control.test_task2_protected_executor --settings=config.test_settings --noinput --verbosity 1
& .venv/Scripts/python.exe -B manage.py test apps.access_control.test_mutations apps.accounts.test_registration_review_api apps.access_control.test_task2_g1d_p3c6a_writer_boundary --settings=config.test_settings --noinput --verbosity 1
& .venv/Scripts/python.exe -B manage.py makemigrations --check --dry-run --settings=config.settings
& .venv/Scripts/python.exe -B manage.py check --deploy --tag security --settings=config.settings
& .venv/Scripts/python.exe -B manage.py report_task2_acceptance --settings=config.test_settings --require-release
& .venv/Scripts/python.exe -B -m apps.access_control.tests_support.g1d_p3c5_windows_pipe_fence_test_only --ack P3C5_SECOND_SERVER_NO_PRODUCTION
```

The first standalone migration-check attempt used `config.test_settings` and
failed with MySQL error 1049 because that settings module chooses an uncreated
random name outside the test runner. It made no database change. The corrected
read-only normal-settings check passed. This environmental failure is not hidden
or counted as a passing test.

## Security evidence and authorization results

The 54 new tests plus nine new cases in existing modules add 63 tests. Evidence
covers tampered signatures/context, key/person separation, revoked epochs,
strict IDs/types, future/expired requests, permission expansion, replay,
state drift, catalogue placement/collision, audit rollback, holds and fresh
permission evaluation. Two independent connection tests verify a single winner
for concurrent admission and concurrent execution. A simulated lost commit
acknowledgment reconciles APPLIED on a new connection without re-execution;
simulated interruption/failed audit leaves HOLD and rolls back application DML.
These are fault simulations, not power-loss, hardware-durability or institutional
disaster-recovery tests.

The first 21-check rehearsal exposed an inherited cleanup bug during post-run
process inspection: terminating the launcher left its child server alive. Only
this task's child was stopped after verifying its exact data directory, private
pipe and creation time. Initial directory deletion hit a transient locked file;
after confirming the process had exited, removal of that exact directory passed.
The harness was then corrected to authenticate/reverify its own server, issue
graceful SHUTDOWN and fail on incomplete cleanup. A second actual rehearsal
passed all 21 checks, and process/directory inspection confirmed no new instance
remained. Two older temporary rehearsal instances, created before this task,
were identified and left untouched. Their cleanup is a separate owner operation;
they are not production-fence or readiness evidence.

| Actor/state | Verified application result |
| --- | --- |
| School Admin with explicit registration permission | Existing review/ordinary Student or Instructor assignment flow passes regression |
| School Admin with an explicit access-control management grant but no technical profile | Role/default and account-override mutations denied with no changes |
| Technical title without School Admin responsibility | Management denied even when evaluator reports a management grant |
| Both profiles plus effective action and delegation permissions, reviewed scope/eligible target | Ordinary permission mutations succeed and audit atomically |
| Composite profile with missing grant, explicit Deny, inactive service/role/account or revoked assignment | Denied on fresh evaluation; cached Python attributes do not restore authority |
| Framework superuser/staff flags alone | No application Technical Super Admin authority |
| Ordinary mutation targeting reserved roles, governance permissions or self/assigned roles | Existing prohibitions remain; regression passed |
| Writer enforcement enabled but no trusted executor | Covered writes refused; registration API returns generic 503 and no mutation |

## Known limitations, vulnerabilities and production readiness

**Not production ready.** The production gaps are substantive:

1. P3C6B's authenticated runtime/executor transport and fixed dispatcher are not
   implemented. The normal services still use ORM writes in legacy development
   mode. An enabled writer gate stops them; it cannot safely route them yet.
2. Real DB runtime/executor/migration/recovery credential separation, full writer
   inventory, session draining and actual-schema DB denial have not been
   verified or applied. Direct SQL/privileged writers bypass Python checks.
3. Persistent production evidence/control/approval/event storage and retention
   are unapproved/unimplemented. The official ERD does not acquire scratch
   tables merely because the tests pass.
4. No real institutional roots, actor/approver appointments, authenticated roster
   loader, executor identity/custody, trusted time or revocation-refresh channel
   is installed. Validator trust/time arguments require an independently trusted
   supplier; they cannot be accepted from an untrusted request.
5. The disposable candidate's control mutex serializes its own operations, not
   other ORM/SQL writers. It has no production executor-bound claim capability.
   Its before-state checks do not constitute a real DB fence.
6. Backup/restore evidence, restore-resistant incarnation/epoch, independently
   approved hold resolution, last-effective-operator recovery and production
   rollback/revocation ceremonies remain outstanding. No automatic compensation
   can safely demote the only effective operator.
7. Protected catalogue/metadata release, real target appointment/authentication
   and live P4/P5 apply authorization remain absent. No new operational endpoint
   or live apply command is provided; old preparation `--apply` stays disabled.
8. Deployment diagnostics additionally found DEBUG True, empty ALLOWED_HOSTS,
   missing HSTS/HTTPS redirection and insecure session/CSRF cookie deployment
   configuration. These development settings were not silently changed.

The exact contracts, grant separation requirements and remaining implementation
work are detailed in
[the remaining security contract](TASK2_P3C6B_P3C7_P4_P5_SECURITY_CONTRACT.md).

## Required manual/institutional approvals

Approve the real evidence schema/official ERD and migration design; independent
identity appointments, roots/keys/custody/revocation; runtime/executor DB grant
matrix and authenticated transport; complete writer/maintenance fencing; backup
restoration and crash/recovery procedures; exact protected catalogue and bootstrap
target. Then implement and verify the remaining production integration in a
schema-compatible disposable environment. Only afterward seek explicit live
release authorization for the concrete reviewed delta. None is inferred here.

## Preserved workspace and final Git status

The original unrelated changes remain excluded from scoped commits:

```text
 M backend/.env.example
 M docs/database/full_schema.dbml
?? Scripts/
?? backend/apps/config/
?? docs/CTU-G_Workspace_Technical_Inspection_2026-11-08.md
?? docs/SRS/CTU-G_Workspace_SRS_v0.4_COMPANION_PROPOSALS.md
?? docs/api/API_CONTRACT_VERIFICATION_DRAFT.md
?? docs/database/proposals/AR6C5D_BULK_QUEUE_APPROVED_FOR_REVIEW.dbml
?? docs/database/proposals/AR6C5D_BULK_QUEUE_REVIEW_v2.dbml
?? docs/decisions/DOCUMENTATION_DECISION_REGISTER_DRAFT.md
?? docs/implementation/access-control/TASK2_G1D_P1_PRODUCTION_AUTHORIZATION_DESIGN_PROPOSAL.md
?? docs/implementation/authentication/AR6C5D_APPROVED_SCHEMA_REVIEW.md
?? docs/implementation/authentication/AR6C5D_SCHEMA_REVIEW.md
?? docs/operations/
?? docs/security/SECURITY_PRIVACY_OPERATIONS_GATES_DRAFT.md
?? docs/testing/MASTER_TEST_UAT_PLAN_DRAFT.md
?? docs/traceability/
?? install_superuser_admin.py
?? review_only/
```

The preserved official ERD working-copy SHA-256 is
`BEFB42DF64A6D10B1AA0828A8E2A0A62FF3167B2B35DADCFA973FECF6D54C6D1`;
the preserved `.env.example` SHA-256 is
`3AB15E4485AF2EA76481F0F2FBF2BD17736623166735800834F99E2EE8AD7AE7`.
No `.env`, secret/key material, backup, dependency directory or unrelated work
is part of the commits. Final status intentionally remains dirty for the
pre-existing user work; the index is empty after the scoped commits.

## Core Task 3 readiness

Independent read-only design and work using ordinary existing authorization may
continue. Task 3 must not depend on a live Technical Super Admin, treat the new
test fixtures as credentials, or assume Task 2 acceptance has passed. Resolve the
P3C6B/P3C7 production implementation and institutional storage/trust/fence gates
before privileged Task 3 integration or deployment. Keep the fail-closed boundary
and rerun the actual-schema negative tests after that integration.
