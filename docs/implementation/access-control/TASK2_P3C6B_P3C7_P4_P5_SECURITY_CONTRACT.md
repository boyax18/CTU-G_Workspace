# Task 2 remaining security controls and isolated execution contract

**Historical checkpoint, superseded 2026-11-14:** the operational executor,
persistent security integration and actual-schema verification are now described
in [the executor deployment contract](TASK2_EXECUTOR_DEPLOYMENT_CONTRACT.md) and
the current completion report. The gaps below describe the earlier candidate;
they are retained as provenance, not the current implementation status.

Date: 2026-11-13, Asia/Manila. Source checkpoint: `29af78e`, branch `ronald`.

**Production release: BLOCKED. Remaining Task 2 implementation: INCOMPLETE.**
This document stays within P3C6B, P3C7, P4, P5 and acceptance. It does not
approve a schema change, enroll a person/key, nominate an account, change MySQL
privileges, or authorize live execution. The earlier untracked G1D-P1 design
proposal remains a proposal; its inactive-role-only release contract is not
silently expanded by these broader disposable tests.

## Implemented runtime boundaries

`technical_admin.has_technical_authority` requires an active, Approved persisted
account, active canonical `Admin` and `Technical Super Admin` assignments, and
the existing hybrid evaluator's effective action-specific permission. School
Admin is the persisted `Admin` role. Technical Super Admin composes those two
responsibilities. These are the two application administrative tiers. Django
framework staff/superuser flags are separate and confer no application authority.

The ordinary permission-mutation services now enforce this predicate through
`require_governance_authority`, for both management and delegation authority.
Their existing transaction, lock order, reviewed service/recipient scopes,
reserved-role exclusions, self-target exclusions, explicit Deny precedence,
idempotency and audit behavior remain in force. Their positive test actors now
have the required composite profile; the reserved-target negative tests remain.
No existing account/assignment is changed by this source update. Existing local
operators lacking that profile will be denied access-control mutations; this is
the requested two-tier policy, and must be considered before release.

Registration approval/rejection continue to use their separate School Admin
authorization and ordinary Student/Instructor assignment rules. They do not
require Technical Super Admin. Writer-unavailable errors now become a generic
503 at the registration API, without leaking infrastructure details.

The P3C6A writer boundary still denies all five covered operations when its gate
is exactly True. No new success token, context override, arbitrary callback,
connection alias, or test import bypasses it. Legacy False/unset behavior remains
available for the previously approved development workflows and is **not
production eligible**. Do not enable enforcement on a live service as an
uncoordinated configuration change: the trusted executor is still unavailable.

New deployment checks report `access_control.E201` for disabled/malformed
enforcement and `access_control.E202` for the absent verified production
architecture. `report_task2_acceptance --require-release` exits unsuccessfully.
These are deployment diagnostics, not a DB fence or a mandatory startup hook;
an operator can bypass/silence checks, which does not make deployment safe.

## Signed evidence validation (P3C7)

`protected_requests.py` is an I/O-free validation library. It contains public
key verification only, no signing key, real trust enrollment, DB connection,
permission mutation or production executor. Its optional dependency is pinned
in `backend/requirements-security.txt` to the already installed cryptography
version. Normal application startup does not import the optional package.

The versioned request binds these exact fields:

| Binding | Meaning |
| --- | --- |
| operation | Exactly `technical_role.provision` or `technical_admin.bootstrap` |
| request_id, nonce | Independent 256-bit hexadecimal identifiers |
| actor_id, target_id | Enrolled actor/account binding; distinct bootstrap target |
| schema, incarnation, epoch | Exact deployment/database scope and current trust generation |
| release_hash, fence_hash, recovery_hash | Independently supplied expected evidence digests |
| before_hash | Exact approved application-state digest |
| issued_at, expires_at | No future issuance; maximum 120-second request lifetime |
| permission_codes | Exact sorted six-code Core K candidate subset |

Three domain-separated Ed25519 signatures cover the entire canonical request,
signer key ID and duty: actor, institutional approver, technical approver. Trust
must supply distinct persons and distinct public keys. An actor key is bound to
one persisted account ID. Unknown fields, malformed types, boolean IDs/epochs,
missing/duplicate duties, extra permissions, expired requests/trust, context
substitution and signature tampering fail closed. Evidence is bounded to 32 KiB.
Trust snapshots must expire within 300 seconds of the trusted verification time.

Caller-supplied `ExecutionTrust` and `now` values are **not authenticated** by
this library. No production loader or trusted clock/revocation channel exists.
Hashes prove equality to expected bytes, not the validity of a fence, backup,
release approval, institutional appointment or identity. A verified request is
not an authorization capability. Production must obtain current trust/time from
independent channels and repeat checks after lock waits, not trust HTTP input.

## Persistent ledger candidate (P3C7; disposable only)

`tests_support/task2_protected_executor_test_only.py` can operate only with the
existing guarded runner, `config.test_settings`, local MySQL READ COMMITTED,
one default alias, a random `test_ctug_registration_<16 hex>` name, matching
configured connection name and an independently queried `SELECT DATABASE()`.
It refuses normal settings before connecting. No operational code imports it.

The candidate creates two scratch InnoDB tables outside transactions, since
MySQL DDL implicitly commits. It never adopts an existing table with `IF NOT
EXISTS`. Tests destroy the tables and their entire disposable database. No model,
migration or application/official ERD change installs these tables elsewhere.

| Table | Persistent candidate contents |
| --- | --- |
| task2_candidate_control | Singleton mutex, trust epoch, incarnation, halted state, release/fence/recovery digests |
| task2_candidate_ledger | Unique request ID, nonce, canonical request digest and one-time operation scope; full signed evidence; actor/target FKs; state/times; exact role and audit FKs |

Admission commits `CLAIMED`. Execution first commits `ATTEMPTED` in a separate
transaction, then starts the application transaction. That transaction locks the
control and request rows, revalidates stored signatures/current supplied trust,
checks the approved before-state and account/catalogue prerequisites, and commits
the mutation, audit receipt and `APPLIED` ledger state together. Unique operation
scope prevents another request/nonce from repeating this initial ceremony.

Both application rollback and an uncertain commit acknowledgment produce an
unresolved outcome. The persistent attempt is never reset automatically.
Reconciliation uses an exact request ID/digest on a fresh connection: `APPLIED`
identifies committed success; any unfinished entry returns `HOLD`. Unknown or
mismatched evidence is refused. A separately committed hold prevents subsequent
claims/execution. There is no automatic resume, privileged demotion, audit
deletion, ledger reset or compensation command.

The state digest covers relevant accounts, credential hashes, role definitions,
service/permission placement, assignments, grants and overrides. Credential
hashes contribute only to the in-memory digest; no passwords or credential
hashes are persisted in signed evidence/audit snapshots. Full evidence stays in
the scratch ledger rather than being squeezed into the existing bounded audit
JSON/reason fields.

## Provisioning and bootstrap candidates (P4/P5)

P4 requires an existing active canonical governance service and all six exact
permissions with matching service/module/action placement. It refuses protected
role collisions, creates one **inactive** Technical Super Admin role and six
**inactive** attributed bindings, and writes one audit receipt. It creates no
account or assignment. This is a broader isolated P4 scenario, not execution of
the earlier narrower P1 metadata-only proposal.

P5 requires a fresh independently signed bootstrap request and before-state.
It targets a distinct, existing active Approved School Admin with a usable
password, no framework privilege flags and no existing core governance override.
It requires the exact inactive technical role/bindings and no technical-role
assignment. It atomically activates that role/bindings, preserves all existing
operational roles, adds the protected responsibility and audits the result.
Every Core K effective permission is checked before commit. It never creates,
approves, activates or sets a password on an account. Existing explicit Deny,
service deactivation or profile removal subsequently revokes effective authority.

All fixture identities/keys/passwords are fictional, ephemeral test inputs. No
production signer or account is enrolled. The existing protected preparation
command's `--apply` continues to refuse unconditionally.

## Unimplemented production architecture and required approvals

These are material implementation gaps, not a checklist whose booleans release
the code. Consequently the verdict is INCOMPLETE, not implementation complete.

1. **P3C6B:** implement authenticated runtime-to-executor transport, independently
   bound actor/session/step-up identity and a fixed operation dispatcher. Preserve
   account approval, ordinary assignment, permission mutation, audit and outbox in
   their owning transactions. Do not grant the web process executor credentials
   or accept caller-chosen SQL, actor IDs as authentication, callbacks or aliases.
2. **P3C6B/P3C7:** approve the real per-operation DB grant matrix. Web/runtime,
   migration/DBA, executor, evidence reader and recovery identities must be
   separate. Restrict direct writes to roles, permissions, services, assignments,
   grants, overrides, evidence and audits. Preserve public registration's needed
   account inserts without admitting direct approval/privilege writes. Account
   table column privileges alone cannot enforce row/role eligibility. Fixed
   procedures or a fully fenced writer service need actual-schema proof.
3. **P3C7:** approve the security evidence/control/request/approval/event schema,
   official ERD changes, migrations, retention/privacy/access rules and recovery
   lifecycle. The two scratch tables are not a reviewed production storage design.
   Install nothing until that approval exists. Enforce append-only evidence/audit
   and one-use claims at the DB privilege boundary.
4. **P3C7:** institutionally enroll roots, signer-to-person/account appointments,
   independent approvers and executor identity; establish protected custody,
   root-authenticated roster distribution, revocation freshness, trustworthy time,
   key rotation and minimum epoch/incarnation state surviving restores. Prevent
   synthetic identities and request-owned public keys from entering trust.
5. **P3C7:** implement authenticated executor-bound claim possession/expiry and
   revocation. The disposable candidate has request IDs and one-use states, not
   production executor authentication or an ephemeral claim capability. Its
   singleton mutex only coordinates its own operations. It does not serialize
   other ORM/direct SQL writers or close their snapshot/check-use races.
6. **P3C6B/P3C7:** verify schema-compatible restricted credentials on a separate
   MySQL instance, including the real registration/outbox/permission services and
   competing direct writers. Inventory external scripts, jobs, administrative
   surfaces, inherited/default roles, grants, active sessions and definer objects.
   Coordinate all writer lock orders. The old 21-check demonstration does not
   supply these missing results.
7. **P3C7:** approve/freshly verify independent backup restoration, stale-evidence
   invalidation, process/session draining, crash recovery, last-effective-operator
   protection and audited recovery/revocation. The new tests simulate failures and
   lost acknowledgments; they do not test power loss or institution recovery.
8. **P4/P5:** approve exact catalogue metadata, protected deltas, human target,
   authentication and institutional bootstrap ceremony. Add a released operational
   workflow only after all prerequisite implementations and negative DB tests.
   Obtain explicit live release authorization immediately before live execution.

Current `config.settings` is development configuration: DEBUG True, no deployment
hosts, no secure cookie/HSTS/HTTPS configuration. Configure these under a reviewed
deployment profile and transport plan; blindly changing them here could break
the authorized local development flows. No production settings are certified.

## Disposable rehearsal recovery correction

Post-run process inspection exposed an existing Windows cleanup failure: killing
the launcher handle could leave its child MySQL server and locked temporary data
directory alive. The rehearsal now authenticates and rechecks its private server
identity before issuing graceful `SHUTDOWN`, waits for its launcher to exit,
validates the resolved directory against the exact temporary root/name/data path,
and refuses silent success if shutdown or recursive cleanup fails. Four offline
tests cover identity mismatch, graceful shutdown ordering, unowned directories
and surfaced deletion failure. A new full 21-check rehearsal passed with no new
server process or temporary directory afterward. This is a P3C7 recovery-safeguard
fix within the existing test infrastructure, not another phase.

## Reference semantics

MySQL definer routines can execute with privileges unavailable to their callers;
their authorization and EXECUTE grants therefore need explicit review. See
[MySQL 8.4 stored object access control](https://dev.mysql.com/doc/refman/8.4/en/stored-objects-security.html)
and [routine privileges](https://dev.mysql.com/doc/refman/8.4/en/stored-routines-privileges.html).
Keep ledger DDL outside application transactions; see
[statements causing implicit commits](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html).
Signature verification follows the
[cryptography Ed25519 API](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/).
These references describe mechanisms, not verification of this deployment.
