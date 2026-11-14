# Core Task 2 — Technical Super Admin Foundation completion report

Assessment: **2026-11-14, Asia/Manila**. Branch: `ronald`.

## Executive summary and verdict

**IMPLEMENTATION COMPLETE BUT RELEASE BLOCKED.**

| Acceptance dimension | Actual status |
| --- | --- |
| Engineering implementation | Implemented: trusted executor integration, persistent signed evidence/ledger, restricted credentials and DB writer leases, recovery, operational P4/P5 handlers and operator client |
| Isolated security verification | Actual migrated application schema and security objects on a physically separate disposable MySQL 8.4 server; final result recorded below |
| Production release authorized | **NO**: no institutional enrollment, production SQL/ERD approval, credential/privilege activation or live provisioning authorization is inferred |

The previous INCOMPLETE report was correct at `bc9f703`: the trusted executor and
persistent security integration were missing. They now exist in operational
modules, outside `tests_support`, and run through the existing service entry
points. The old candidate and its document are retained as historical provenance.
This verdict does not claim that Core Task 2 is deployed or that a live Technical
Super Admin exists. Production acceptance remains blocked.

No live database privileges/schema/account/role were changed; no official ERD,
private environment, backup, production key or unrelated work was edited. No
Docker requirement, Git push or external email/message was introduced.

## Roadmap status

| Locked phase | Implemented behavior and actual boundary |
| --- | --- |
| Earlier P3C6A and historical G1/P3 foundations | Existing guarded/read-only/test contracts retained; covered by full regression; their synthetic identities are not production trust |
| **P3C6B** | Existing registration submit/approve/reject, reapplication and permission mutations forward to a fixed mTLS dispatcher. Authorized ordinary base-role assignment has an explicit reviewed policy. Runtime SQL cannot write accounts, assignments, permissions, catalogue, audits or security state. Ordinary/protected executor credentials and database checks are separate. |
| **P3C7** | Root-endorsed roster and policy binding, executor-issued certificate-bound actor proofs, persistent signed authorization archives and signed commit receipts, one-use claims, DB connection-bound leases, replay/concurrency controls, dedicated recovery hold/rotation and operational deployment diagnostics. |
| **P4** | Operational protected handler provisions the inactive Technical Super Admin role, exact six Core K definitions/bindings and audit receipts under a verified lease and independently signed approval. |
| **P5** | Operational handler authenticates the operator, validates independent exact-request approval and before-state, and atomically bootstraps a distinct existing School Admin's protected responsibility, bindings and audit. It creates/activates no account. |
| **Final acceptance** | Engineering and isolated verification are assessed here. Institutional production approval, schema installation, actual deployment credentials/fencing and release ceremony remain withheld. |

There are exactly two application Admin tiers: School Admin (`Admin`) and the
Technical Super Admin composite (`Admin` + `Technical Super Admin`). Django
framework superuser/staff flags remain separate. The existing hybrid evaluator,
explicit Deny precedence, service/recipient delegation scopes and transactional
audits remain authoritative; no role-title permission bypass was added.

## Implemented execution and persistence

The web profile holds only a runtime DB credential and ordinary client TLS key.
Its service calls reach a separate ordinary executor. Protected P4/P5 requires a
different client certificate and protected executor/database principal. The
runtime profile refuses protected client configuration; no executor DB password
or issuer key is loaded there. Deployment profiles skip the development `.env`
and require separately provisioned configuration and verified database TLS.

The executor authenticates the actor's password and issues a short-lived,
certificate/epoch-bound Ed25519 proof. It ignores caller role claims and checks
fresh permissions inside the shared transaction. The root-signed roster binds
schema/server UUID, epoch/incarnation, independent signers, issuer keys, peer
certificate scopes, policy hash and release/fence/recovery evidence. It is
reloaded/revalidated; missing, stale, changed or untrusted evidence refuses work.

Admission durably reserves request/nonce and stores a claim hash. The secret
stays in the invocation's memory. ATTEMPTED is committed before application DML.
The next transaction holds the control mutex, validates current evidence, obtains
a connection-bound database lease, runs the existing service and atomically
commits application state, exact audit links, optional encrypted outbox and signed
result. Failure never falls back to local ORM writes or automatic re-execution.

Evidence archives the exact root endorsement and an executor signature over the
sanitized request and execution identity. Commit receipts separately sign the
result, request/evidence hashes and audit IDs. Verification remains possible after
epoch rotation. Passwords, link secrets and public registration PII are redacted;
their fast hashes are not persisted. Signing keys are outside DB/source control.

Grants and triggers fence ten relevant application tables. A lease must match
the actual connection, authenticated DB user, unexpired attempt, epoch/incarnation
and unhalted control row. A protected label alone does not grant protected DB
authority. Ordinary writers cannot alter reserved/governance state or Approved
account fields. Audits and evidence are append/transition restricted. A separate
notification identity can update only existing delivery-state columns and cannot
edit recipients or application authority; SMTP remains separately gated.

Reconciliation verifies signatures and returns APPLIED or HOLD. Actual process
interruption leaves an unfinished attempt. Recovery uses its own credential and
retains events; it can hold writers or apply a newer root-approved epoch and
different incarnation, never reset an attempt or automatically demote an operator.
Routine signed roster renewal preserves the exact trust definition and generation,
requires a strictly higher persisted expiry floor and cannot clear a hold. This
supports continuous short-lived trust without five-minute service shutdowns.

The full implementation and configuration/release contract is
[TASK2_EXECUTOR_DEPLOYMENT_CONTRACT.md](TASK2_EXECUTOR_DEPLOYMENT_CONTRACT.md).

## Exact files created and modified in this continuation

Created under `backend/apps/access_control/executor/` (exact relative filenames):

```text
__init__.py
client.py
diagnostics.py
engine.py
errors.py
protocol.py
provisioning.py
receipts.py
recovery.py
role_assignment.py
runtime.py
schema.py
server.py
trust.py
```

Other files created:

```text
backend/apps/access_control/management/commands/execute_protected_request.py
backend/apps/access_control/management/commands/serve_workspace_executor.py
backend/apps/access_control/test_executor_protocol.py
backend/apps/access_control/tests_support/executor_actual_schema.py
backend/config/executor_isolated_settings.py
backend/config/executor_notifications_settings.py
backend/config/executor_runtime_settings.py
backend/config/executor_settings.py
docs/implementation/access-control/TASK2_EXECUTOR_DEPLOYMENT_CONTRACT.md
```

Modified:

```text
backend/apps/access_control/checks.py
backend/apps/access_control/management/commands/report_task2_acceptance.py
backend/apps/access_control/mutations.py
backend/apps/access_control/test_task2_protected_requests.py
backend/apps/access_control/writer_boundary.py
backend/apps/accounts/admin_bootstrap.py
backend/apps/accounts/outbox_worker.py
backend/apps/accounts/reapplication.py
backend/apps/accounts/registration_review.py
backend/apps/accounts/services.py
backend/apps/accounts/session_auth.py
backend/config/settings.py
docs/implementation/access-control/TASK2_P3C6B_P3C7_P4_P5_SECURITY_CONTRACT.md
docs/implementation/access-control/CORE_TASK_2_COMPLETION_REPORT.md
```

## Database schema and migrations

Existing Django migrations created the **17 actual application tables** on the
new private server. The proposed security SQL then created four InnoDB tables:
`wex_control`, `wex_requests`, `wex_audits`, `wex_recovery_events`, plus fixed
lease/classification functions and authorization/evidence triggers. The harness
used independent runtime, ordinary, protected, recovery and notification users.

These storage objects are reviewable deployment SQL, not approved official ERD
changes or an automatic Django migration. No application models/migrations or
real schema changed. The required migration check returned **No changes detected**.
That result does not imply the proposed security tables are installed in the
real environment. Their production installation and definer/grant ownership
require specific institutional/schema/DBA approval.

The second server used a newly initialized temporary data directory, random
private named pipe, `--no-defaults`, TCP disabled and MySQL X disabled. Actual
data-directory/pipe/server identity was checked before DDL. Stock mysql.exe's
explicit RSA exchange primed disposable named-pipe authentication; production
profiles instead require MySQL TLS `VERIFY_IDENTITY`. No privileges were changed
on the normal MySQL server. All fixture credentials/keys are synthetic and
temporary. The harness cleans up only its own children/server/directory.

## Verification commands and actual results

Commands ran from `backend` using `.venv/Scripts/python.exe -B`. The full suite
enumerates every test module in Accounts and Access Control, the repository's
established backend regression method (57 modules after this continuation).

```powershell
$testModules = Get-ChildItem apps/accounts,apps/access_control -Filter 'test*.py' -File |
    Sort-Object FullName | ForEach-Object { 'apps.' + $_.Directory.Name + '.' + $_.BaseName }
& .venv/Scripts/python.exe -B manage.py test @testModules --settings=config.test_settings --noinput --verbosity 1
& .venv/Scripts/python.exe -B -m apps.access_control.tests_support.executor_actual_schema
& .venv/Scripts/python.exe -B manage.py makemigrations --check --dry-run --settings=config.settings
& .venv/Scripts/python.exe -B manage.py check --deploy --tag security --settings=config.settings
& .venv/Scripts/python.exe -B manage.py report_task2_acceptance --settings=config.test_settings --require-release
```

| Verification | Actual result |
| --- | --- |
| Starting checkpoint | `bc9f70340267da6680de6010149ee50cfc3354f9`, branch `ronald`; prior report baseline 1,349 tests |
| Focused service compatibility | **88/88 passed**, 23.993 seconds: mutation, registration review and P3C6A boundary modules |
| Initial new protocol/root contracts | **18/18 passed**, 0.224 seconds; an additional policy-hash negative brings the final new module to 19, covered by full regression |
| Focused protocol/evidence/writer guards | **58/58 passed**, 0.143 seconds before the final extra policy case |
| Final protocol/evidence/writer guards | **59/59 passed**, 0.123 seconds, including non-secret request/hash correlation on unavailable-writer errors for explicit receipt recovery |
| Actual-schema initial integration | **23/23 passed** using operational code, not the earlier test-only executor |
| Expanded actual-schema authorization/recovery | **50/50 passed**, including actual executor-process termination/restart and recovery rotation |
| Persistent endorsement/receipt signatures | **53/53 passed**, including tampered evidence/result rejection after rotation |
| Actual-schema run including restricted notification worker | **56/56 passed**, exit 0; all 17 migrated application tables plus four security tables on a fresh private server; no external mail |
| Final actual-schema run with continuous signed roster renewal | **58/58 passed**, exit 0; signed refresh preserves generation/availability and cannot replay/reset validity |
| Final full backend regression | **1,368/1,368 passed**, 177.913 seconds, exit 0; fresh random MySQL schema created/destroyed |
| Migration drift | **No changes detected**, exit 0; no migrate on real DB |
| Deployment diagnostics on existing development settings | **Expected refusal**, exit 1: `access_control.E201`, `access_control.E202`, six existing HTTPS/cookie/DEBUG/host warnings |
| Offline acceptance with `--require-release` | **Expected refusal**, exit 1; implemented engineering is distinguished from unauthorized production release |
| Scoped diff/whitespace review | `git diff --check` passed |

Development failures were corrected rather than counted as security passes:
named-pipe full authentication and strict X.509 fixture prerequisites were fixed;
an unsupported table-level LOCK TABLES grant was removed; the negative-test helper
was corrected to recognize Django's wrapped MySQL 1143 denial. A captured full
run printed 1,368 OK but its PowerShell stderr/Tee wrapper returned 1; the direct
command was rerun and returned exit 0 with the final result above. None of these
failures caused a production change or a weakened authorization assertion.

## Security evidence and authorization outcomes

The actual-schema proof invokes the existing Django service functions through
the mTLS client and separate server processes. It proves public registration,
reapplication, School Admin approval/rejection/base assignment, Technical Super
Admin permission mutations, protected P4 provisioning/P5 bootstrap and atomic
audit/outbox behavior with restricted credentials.

Negative direct SQL uses authenticated principals and requires specific MySQL
privilege/trigger errors, not connection failures. It denies runtime account
approval/password takeover, role assignment/default/override writes, catalogue
and service changes, audit forgery, ledger/control mutation and trigger removal.
It additionally exercises an ordinary executor's forged protected ledger row and
active ordinary lease: neither admits Admin assignment, governance grants or
technical-account password changes. Evidence-state reset and control-floor
forgery are denied at the DB boundary.

Wrong password, missing/wrong-kind client certificate, wrong server pin, request
replay and concurrent network replay fail. Concurrent replay produces one commit
and one audit. A forced audit error rolls back account/assignment/audit/outbox
while retaining ATTEMPTED. Killing only the harness's executor while blocked on
an actual account-row lock leaves the target unchanged and a durable HOLD;
restart cannot replay it. A dedicated recovery hold fences writes, a forged
roster rotation is refused, an approved rotation invalidates old actor proofs,
and fresh authentication works. Signed archives/commit results verify after
rotation; forged evidence/results fail independently.
Same-generation root-signed roster refresh preserves availability; replaying the
refresh cannot reset its validity floor or trust definition.

| Actor/state | Verified result |
| --- | --- |
| School Admin + effective ordinary operational permission | Registration approval/rejection and reviewed base assignment succeed |
| School Admin without technical composite profile | Access-control management refused |
| Technical Super Admin composite + action/delegation permissions and eligible reviewed target | Existing ordinary permission mutation succeeds and audits |
| Role title alone, missing/expired proof, explicit Deny, inactive/revoked state or unreviewed scope | Denied by existing evaluator/service contracts and new executor checks |
| Framework flags alone | Do not grant application technical authority |
| Runtime DB credential using direct SQL | Cannot write authorization/account/audit/security state |
| Ordinary executor credential trying protected state, even with a forged ordinary lease | Denied by database identity/grant/trigger boundary |
| Protected P4/P5 with exact independent approvals and active enrolled operator | Executed only on disposable actual schema in this work |

## Remaining release requirements and limitations

Production is **not authorized**. The remaining requirements are concrete
deployment/institutional decisions, not missing executor or ledger code:

1. Approve the four-table security evidence design, retention/privacy/access
   policy, trigger/functions, official ERD amendments and installation/rollback
   procedure. Install nothing automatically through application migrations.
2. Appoint real signers/operators and root/key custodians; provision real TLS,
   issuer and institutional keys/pins, protected host ACLs and independent current
   roster/epoch custody. No fixture key/person is a production signer.
3. Approve and activate the actual DB account/definer/host grant matrix. Inventory
   every external script, worker, inherited role, admin surface and active session;
   drain old writers and verify direct SQL denials using actual deployment
   credentials and MySQL TLS. This work proves the isolated pattern, not that
   unrelated existing production principals have been fenced.
4. Independently verify fresh backup restoration, storage durability, trusted
   clocks, restore-resistant external minimum epoch/incarnation and the actual
   recovery/revocation ceremony. Process interruption tests are not power-loss or
   full disaster-restore evidence. Root rosters expire within five minutes; real
   operational signing/refresh/revocation custody must maintain that requirement.
5. Approve exact protected metadata/release hashes, business recipient policies,
   real human target, authentication and concrete live release delta. Only then
   explicitly authorize a live P4/P5 invocation. No account is nominated here.

The executor host/private credentials, DB/definer administration, institutional
root and session confidentiality remain trusted boundaries. A compromised DBA
or privileged executor host is not made harmless by Python, SQL triggers or
signatures. The ordinary credential is trusted for ordinary service execution;
it cannot cross the database's protected-principal boundary. Actor proofs are
short-lived bearer assertions bound to a TLS client, not hardware MFA. Production
load/host/security review remains necessary. General future privileged demotion
or governance-revocation CRUD is deliberately absent; it needs separate
last-effective-operator rules rather than weakening the initial bootstrap scope.

## Commits and preserved workspace

- Starting implementation/report commits: `185c27ef9ffa903ad2af06861c31c983e104702b`
  and `bc9f70340267da6680de6010149ee50cfc3354f9`.
- This continuation's verified implementation commit:
  `6632fe93bc16371a7f2d1216e475272f92347357`
  (`feat(access-control): integrate trusted MySQL executors and durable evidence`, 36 scoped files).
- This report is committed afterward. Resolve its own exact hash with
  `git log -1 --format=%H -- docs/implementation/access-control/CORE_TASK_2_COMPLETION_REPORT.md`.
- No push was performed. The final index is empty; only the original unrelated
  modified/untracked work remains outside the scoped commits.

Preserved tracked modifications are `backend/.env.example` and
`docs/database/full_schema.dbml`. Their working-copy SHA-256 values remain:

```text
full_schema.dbml BEFB42DF64A6D10B1AA0828A8E2A0A62FF3167B2B35DADCFA973FECF6D54C6D1
.env.example    3AB15E4485AF2EA76481F0F2FBF2BD17736623166735800834F99E2EE8AD7AE7
```

All original untracked Scripts, review_only, backend/apps/config, operations,
traceability, inspection, SRS/API/decision/security/testing/schema-review proposal
documents and install_superuser_admin.py remain untracked and untouched. No
environment secret, private key, backup, dependency tree or fixture data directory
is included in either commit.

## Core Task 3 readiness

Core Task 3 engineering can use the implemented fixed boundary and isolated
fixtures. It must not assume a live technical operator, seed generic privileges,
reuse fictional signing identities or bypass the pending production gates.
Privileged integration/deployment remains contingent on the institutional and
environment-specific release requirements above. No new major roadmap phase has
been added.
