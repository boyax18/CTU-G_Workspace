# Task 2 executor implementation and deployment contract

Date: 2026-11-14 (Asia/Manila). Locked scope: P3C6B, P3C7, P4, P5, acceptance.

The operational implementation replaces the earlier test-only executor candidate.
It does not authorize production SQL installation, signer enrollment, secret
issuance, privileged account activation or an official ERD amendment.

## P3C6B: process and database boundaries

The web/runtime process has a restricted database account and only its ordinary
mTLS client identity. It forwards fixed operations to an ordinary executor.
A separate protected executor has a different database credential and accepts
only an independently enrolled protected client certificate. The runtime settings
profile refuses a protected client identity. Executor database credentials and
issuer private keys are never loaded by the web settings profile. Deployment
profiles skip `backend/.env`; private JSON configuration is supplied separately.

Existing service entry points forward registration submit/approve/reject,
reapplication and permission mutations. On the executor they reuse the same
implementations and hybrid permission evaluation, joining the ledger-owned outer
transaction through `writer_atomic()`. Audit records and encrypted outbox rows
commit with the application delta and signed ledger result. Legacy False/unset
writer enforcement remains development compatibility and fails deployment checks.
Enabled enforcement has no fallback when the executor is missing or unavailable.

The fixed dispatcher additionally supports explicitly configured ordinary base
role assignments. A School Admin needs `accounts.role_assignments.manage` and an
explicit, reviewed `WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_POLICY` recipient profile.
No default policy grants this new operation. Registration's existing base-role
assignment is unchanged. Technical management still needs both active Admin
responsibilities, effective action/delegation permissions and reviewed scopes.
Framework flags remain a separate mechanism.

`executor/schema.py` supplies the exact reviewable MySQL 8.4 DDL and grants.
It has **no production installer**, Django model or automatic migration. New
storage is `wex_control`, `wex_requests`, `wex_audits`, `wex_recovery_events`.
Installation requires a specific schema/official-ERD/DBA decision. Do not run
the disposable settings or harness on a real database to install this design.

| Principal | Allowed authority |
| --- | --- |
| Runtime | Read relevant application tables and manage Django session rows; no authorization/account/audit/security-ledger DML, DDL or grant authority |
| Ordinary executor | Existing guarded account/ordinary assignment/permission/audit/outbox writes; no catalogue DML; no control UPDATE; no protected promotion |
| Protected executor | Fixed, independently approved P4/P5 operations and separately gated ordinary first-Admin bootstrap; no audit/evidence deletion or DDL |
| Recovery | Read/update the control row and insert recovery events; no application DML |
| Notifications | Read outbox/audit records and update only delivery-state columns; no recipient-envelope, account, role or audit mutation |
| Schema/DBA/definer custodian | Separately controlled installation and grant administration, outside application credentials |

MySQL `LOCK TABLES` privileges allow executor locking reads without granting
ordinary UPDATE on the catalogue or control row. No application principal gets
CREATE/ALTER/DROP/TRIGGER/GRANT OPTION/PROXY/role administration. Identities have
no inherited/default database roles. The generator's local principals use
`@localhost`; a different deployment host matrix needs its own DBA-reviewed grants.

Triggers require an ATTEMPTED request lease bound to the actual connection ID,
authenticated session user, epoch, incarnation, expiry and unhalted control row.
Setting a session variable alone cannot create a valid lease. Protected writes
also require the actual protected database principal; a ledger label is
insufficient. Ledger INSERT checks principal/kind/connection independently, and
UPDATE permits only the immutable-evidence CLAIMED→ATTEMPTED→APPLIED lifecycle.

Ordinary writes cannot alter reserved role assignments, governance permissions,
protected recipients, catalogue definitions, framework flags or any existing
Approved account's fields. Ordinary assignments are limited to canonical
Student/Instructor roles and exclude protected recipients. Audits are append
only and their actor must match the lease. Each audit is linked to its ledger
request by a database trigger. Ordinary business authorization remains in the
existing locked Django services; the ordinary executor host/credential is trusted
for those ordinary operations. It is not a second database root.

The notification worker is an explicit narrow exception for outbox delivery
UPDATE only. Column grants and immutable-envelope trigger checks preserve its
existing claim/finalize lease logic without giving it authorization writes.
SMTP remains separately gated. The verification harness uses only local-memory
mail and sends no external message.

## P3C7: authentication, signed evidence and recovery

TLS 1.3 authenticates both ends. Clients validate CA/hostname and an exact server
certificate fingerprint. The signed roster independently allowlists client
certificate fingerprints by executor kind. The service has bounded request
sizes, handshake/read timeouts, 32 worker slots and bounded authentication
attempts per client/account. It exposes only authenticate, execute, receipt and
readiness POST operations. There is no SQL, import-path, callback or alias input.

The executor checks the operator password against the current persisted account
and issues a five-minute Ed25519 actor assertion bound to that client certificate
and trust epoch. It never relies on a caller-provided actor ID or a Django
session signature. Browser login stores that assertion in the session;
`ExecutorProofMiddleware` supplies it to service calls. An expired assertion
requires reauthentication for mutations. Server-side permissions are reevaluated
inside the serialized application transaction.

A separately pinned Ed25519 institutional root authenticates the short-lived
roster. It binds database schema/server UUID, epoch/incarnation, release/fence/
recovery evidence hashes, policy hash, independent actor/approver enrollment,
issuer public keys and peer certificate scopes. The configured delegation and
ordinary-assignment policies must hash to the root-endorsed value. Root pins and
the minimum trust epoch are deployment inputs outside the database backup.
The executor checks the actual DB principal, UUID, UTC READ COMMITTED session,
InnoDB storage and privileges. Production profiles require verified MySQL TLS;
only the physically verified second-server harness permits a private named pipe.

Admission commits a unique request/nonce and an unpredictable claim hash. The
claim secret stays in the invocation's memory. The one-use attempt is committed
before application DML. A new transaction rechecks current trust/time/identity,
holds the shared control mutex and commits application changes, audit links,
outbox rows and signed result together. The response follows that commit.
Protected initial-ceremony scopes are unique within each incarnation.

Each request archives its exact root-signed roster plus an executor signature
over the sanitized command, peer/actor proof and database connection identity.
The committed result has a separate signature bound to that evidence hash,
request and exact audit IDs. Independent receipt verification detects forged
evidence or results even after root-roster rotation. Passwords, verification-link
secrets and public registration PII are redacted before persistence; their fast
hashes are not stored. Signing keys remain outside MySQL and source control.

Network failure never triggers automatic re-execution. Authenticated receipt
reconciliation returns a verified APPLIED result or HOLD. Infrastructure failures
expose non-secret request/hash correlation attributes to trusted service callers
for explicit receipt reconciliation; browser API errors stay generic. An unfinished protected
attempt holds new writes in its epoch/incarnation. The recovery credential can
record a conservative hold, or rotate only from a held state to a strictly newer
root-approved epoch and different incarnation, retaining evidence and recovery
events. It never resets an attempt, deletes an audit or automatically demotes an
operator. Old actor proofs and leases cannot authorize the new generation.

Routine root-signed roster renewal does not require repeated service holds or
generation changes: `RecoveryControl.refresh` accepts only the identical trust
definition with strictly increasing validity expiry. A persisted definition hash
and expiry floor reject changed scopes, replayed refresh or validity rollback.
It cannot clear a hold. Trust/peer/key/policy changes use explicit hold/rotation;
renewal and rotation retain their signed evidence as recovery events.

The initial protected dispatcher has no general demotion, catalogue-edit, role
deletion or governance-revocation operation. Ordinary services cannot perform
those writes. This prevents ordinary last-operator removal. Future protected
revocation APIs require their own serialized last-effective-operator design;
they must not be added as generic CRUD.

## P4/P5: operational protected handlers

The protected service verifies the existing three-party request signatures:
enrolled actor, distinct institutional approver and distinct technical approver.
It binds exact operation, database generation, release/fence/recovery hashes,
nonce/request ID, before-state hash, short expiry and the six Core K codes.
The operator must also authenticate and have an active ordinary Admin assignment.

P4 creates one inactive Technical Super Admin role and six inactive bindings.
If absent, it creates only those exact six permission definitions under the
existing active governance service, with audit receipts. Existing definition
placement must match. The actor approves the source/release and exact subset;
there is no arbitrary catalogue import or default-all-permissions seed.

P5 targets a distinct, existing active Approved School Admin with a usable
password and no framework flags or conflicting core overrides. It atomically
activates the exact role/bindings, adds the technical responsibility, retains
other operational roles and verifies every effective Core K permission. It does
not create or activate an account, set its password or bypass Deny precedence.

`execute_protected_request` reviews a signed bundle by default. Explicit `--apply`
requires an interactive enrolled operator, hidden password entry, a separate
protected mTLS identity, current signed evidence and the installed executor.
It performs no schema/grant installation. The old preparation command's apply
path remains disabled. This new operational client was not used on a live DB.

## Configuration and release decisions

Production configuration contains no embedded sample secrets. The deployment
profiles read private JSON files named by `WORKSPACE_RUNTIME_CONFIG`,
`WORKSPACE_EXECUTOR_CONFIG` or `WORKSPACE_NOTIFICATIONS_CONFIG`. Each database
dictionary uses Django's MySQL fields and OPTIONS including `ssl_mode` set to
`VERIFY_IDENTITY` and approved CA configuration. `DJANGO_SECRET_KEY`, SMTP and
outbox wrapping keys come from separately provisioned environments/secret custody.

Runtime configuration contains database, allowed_hosts, identity (schema,
principal, server_uuid) and only an ordinary clients entry (url, CA file,
certificate/private-key paths, server fingerprint). Executor configuration adds
server kind/principal/schema/UUID/minimum_epoch, root public-key pin, roster and
issuer-key paths, TLS files and bind address, policy_hash, reviewed delegation
and ordinary-assignment policies, and outbox enablement. Notification configuration
contains only its database/identity and uses the existing explicit delivery gates.

Before a production rollout, institutions must approve the evidence schema,
retention/privacy policy, official ERD amendments, definer/account ownership and
grant matrix; appoint the real root/signers/operators and key custodians; verify
host ACLs, clocks, revocation/roster refresh, credential/session draining and all
external writers; test the actual deployment's DB TLS and privilege denials;
independently verify backup restoration and a fresh recovery incarnation; approve
the exact protected catalogue, human target and release delta. No such decision
is inferred from a synthetic fixture or a digest supplied by the request.

Deployment checks probe installed storage/trust and authenticated readiness;
they do not install anything or equate isolated verification with production
authorization. The existing development profile still fails production checks.
Passing deployment diagnostics is necessary but does not replace institutional
approval, threat review or environment-specific security testing.
