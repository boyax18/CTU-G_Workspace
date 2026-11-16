# G1D-P1 — conditional D1–D6 disposable ledger prototype

Date: 2026-11-13 (Asia/Manila)

Status: disposable-test-only milestone passed isolated/full regression and consistency checks; scoped commit subject to final staged review. **D7 LIVE EXECUTION WITHHELD.**

## 1. Authorization, inspected checkpoint, and exact scope

The owner explicitly approved D1–D6 with conditions for design refinement, synthetic asymmetric verification, four-table disposable MySQL prototyping, focused/full regression, documentation, and a scoped commit after successful checks. The approval does not select or deploy real institutional trust, authorize production evidence, adopt a production schema, or release a protected write.

Verified start: `ronald` / `3af80e1b832118198b5871b353f7b0cfcfd12190`; empty index. Existing preparation work was already committed. The untracked production design proposal existed and was read, not overwritten or included in this milestone's commit. Its inspected SHA-256 is `0F8E371B80C6492ECC284DA1A2C3C90451558E0611D801D87A8F2AD3D9ED4D50`.

Inspected current models/account relationships, permission evaluator, delegation/mutation services, audit primitive, G1C/G1D helpers/contracts, P0/P1 commands, four-role initializer, test settings/runner, framework read-only Admin, and relevant account/bootstrap/review/metadata writers. Existing HMAC fixtures and temporary-table uniqueness demonstrations remain unchanged. No completed preparation milestone was reimplemented.

Exactly two application Admin levels remain: **Normal Admin** (`Admin`) and **Technical Super Admin** (`Admin` plus the protected technical role and effective action-specific permissions). Approval responsibilities and a test ticket issuer are not application Admin roles. Django Superuser alone is never application governance authority.

Exactly four new paths belong to this milestone:

| File | Responsibility |
| --- | --- |
| `backend/apps/access_control/tests_support/g1d_p1_authorization_design_test_only.py` | Strict bounded synthetic request/approval/ticket/executor/cancellation contracts and Ed25519 public-key verification. |
| `backend/apps/access_control/tests_support/g1d_p1_ledger_transaction_test_only.py` | Disposable-schema guard; four shared scratch InnoDB tables; admissions/claims/execution reservations; role/audit/consumption; cancellation/revocation fixtures and read-only outcome resolver. |
| `backend/apps/access_control/test_task2_g1d_p1_production_authorization_contract.py` | Synthetic signature contracts and actual committed, competing-connection, rollback and uncertain-outcome tests. |
| This document | Conditional approval record, implemented scope, schema candidate for separate review, verification, limitations and next gate. |

No existing production file, model, migration, settings, dependency manifest, initializer, command, endpoint, authentication or permission behavior was changed. The official ERD remains untouched by this work. No new ledger was created in `ctug_workspace`.

## 2. Implemented test-only evidence contract

All private Ed25519 keys are generated in test-process memory; none are loaded from files, serialized or committed. Fictional public-key registries bind four independent keys to institutional/technical/executor responsibilities and a synthetic ticket issuer. The existing environment already supplies `cryptography==46.0.4`, pinned in `backend/requirements-outbox.txt`; no installation or dependency change was made. Test setup verified Ed25519 signing/verification capability.

Verification binds the exact operation, canonical inactive role metadata, generated test schema, `DISPOSABLE_TEST_ONLY` environment, incarnation, policy/trust epoch, executor person/account/key, before-state hash, synthetic backup/release hashes, times and one-use nonce. Two distinct approval duties must represent different people, each distinct from the executor; duplicate public keys cannot masquerade as independent people. The issuer signs digests of both approval envelopes. The executor signs the request, nonce, release, account and challenge. Signatures are domain-separated by purpose.

The fixture permits only bounded flat printable-ASCII JSON objects, exact safe integers and Booleans, with deterministic serialization, duplicate/unknown-field rejection and strict canonical-byte comparison. Unicode, floats, nested structures and unsafe integers are refused. This is an intentionally restricted canonical subset with a known encoding vector, **not a general RFC 8785/JCS implementation**. Crypto uses the installed maintained library; no hand-written asymmetric algorithm was introduced.

Request/approval validity is bounded at 24 hours, ticket validity at 15 minutes and executor proof at five minutes, with nested expiry/issue constraints. The fixture uses a fixed injected test clock; it does not implement trusted UTC monitoring or production expiry enforcement. Revoked/expired test keys, wrong identity/key/account/challenge, altered signed scope, rejected/missing/duplicate approval and signature-purpose substitution fail closed.

Real person enrollment, root endorsement and key custody are **not implemented**. The injected public-key registry is fictional test trust, not independently verified institutional identity. Synthetic digests do not prove a real backup/release. There is no signing UI, real ticket service, root-store activation, real approval-admission service or live executor authentication.

## 3. Disposable database isolation and transaction protocol

Every exposed database operation requires the exact test-only acknowledgment, `config.test_settings`, `config.test_runner.IsolatedMySQLRunner`, loopback MySQL, matching configured/connection/TEST schema names of the form `test_ctug_registration_<16 hex>`, actual `SELECT DATABASE()` equality, and READ COMMITTED. Guards run before scratch DDL or fixture writes; worker threads independently verify their own connections. Configuration failures never fall back to main settings.

The unchanged runner creates a fresh unpredictable database, refuses `--keepdb` and parallel clones, checks actual database identity after setup, and destroys the disposable database. Four **ordinary shared** scratch tables are created outside the protected transaction and dropped in reverse FK order before per-test cleanup. A name collision is refused, not adopted with `IF NOT EXISTS`. These tables are deliberately not MySQL connection-local `TEMPORARY TABLE` objects: separate connections must share the same durable test rows to exercise races.

The implementation uses real `TransactionTestCase` commits, rather than treating Django `TestCase` savepoints as proof of commit. Control-row and governance-Service locks precede request/approval/account/assignment/role locks. Existing canonical Admin eligibility is rechecked from persisted state; no Technical Super Admin is required to authorize its own first inactive metadata fixture, and framework flags supply no shortcut.

The modeled protocol has deliberately separate durable boundaries:

1. Verify synthetic signed evidence, compare selected before-state and admit one Ready request, two immutable-by-service approval records and a ready event. Identical currently valid admissions return status only, including after successful consumption; changed bytes under the same ID fail. Invalid submissions are not admitted as historical approval records.
2. Claim Ready -> Attempted under locks; persist only a hash of a random in-memory secret plus claim history. The secret is never logged or accepted from a CLI. A second claim is refused.
3. Reserve execution in a short separate transaction by appending a unique `executing` event. This remains after a later rollback or crash simulation. The same request/claim cannot re-enter execution, including reconstruction with the same secret. An uncertain reservation acknowledgment never starts the role transaction.
4. Inside one owning durable atomic block, revalidate stored signatures/evidence/epoch and executor state after locks, compare selected before-state, refuse technical role/aliases/governance drift/prior success, insert exactly one inactive role, write a trusted actor audit, validate exact stored postconditions, conditionally consume the request with role/audit references and success scope, and append the consumption event. All these protected changes commit or roll back together. Admission, claim and execution-reservation history intentionally survive a protected rollback.
5. A separate lock-aware resolver verifies stored signed evidence at its historical admission/consumption time, its persisted approval rows, before-state/result correlation, exact audit/role state and consumption event. It returns COMMITTED, NOT_COMMITTED or UNKNOWN. It waits for an in-flight writer to finish before classifying; there is no automatic retry, repair, reset, delete or permission operation.

The bounded existing audit writer is reused unchanged: `technical_admin.role_metadata.create`, persisted executor, new role, null old/target/permission, `policy_enforcement`, and exact role-ID/inactive state. Evidence correlates through unique ledger FKs rather than unsupported request fields in audit JSON. Success tests close/reopen the physical connection and inspect committed results.

The selected before-state includes complete role names/descriptions/activation, executor approval/activation, account count, assignments, relevant service/catalogue/binding/override fields and audit IDs. It is a versioned test snapshot, **not every database column or a signed institutional preflight**. Expected ledger changes are excluded. After the protected write, removing only the new role/audit from that snapshot must reproduce the approved baseline; unexpected assignments/grants/account or protected-state changes refuse/roll back.

## 4. Separate four-table schema candidate — owner approval still required

This section presents the refined candidate separately from the official ERD. It does **not** approve production DDL, Django models, migration files or deployment. Executable scratch DDL is confined to the guarded test helper.

| Candidate entity / scratch table | Implemented scratch fields and database protections | Required production review |
| --- | --- | --- |
| Control / `g1d_p1_proto_control` | Singleton checked PK `1`; positive epoch, incarnation, checked halted Boolean, checked retention code. Serialization row; missing state refuses. | Signed trust-manifest bytes/digest/history, environment identity, independently held minimum epoch/incarnation, fail-closed enrollment/update and real release policy. Scratch initialization is synthetic and starts unhalted for tests only. |
| Requests / `g1d_p1_proto_requests` | UUID PK; UNIQUE idempotency key, request hash and nullable ticket nonce; exact request/bundle/before-state blobs; challenge and executor FK; lifecycle/version/expiry; claim hash/time; UNIQUE result role FK, result audit FK and stable success scope; consumption time. CHECKs require nonce for Ready/Attempted/Consumed, claim fields for Attempted/Consumed, all result fields for Consumed and no result fields otherwise. | Stable environment/resource scope, canonical signed byte retention, trusted UTC, full evidence columns/size limits and lifecycle/CAS service. Final typed columns and explicit bounds require schema review. |
| Approvals / `g1d_p1_proto_approvals` | Approval UUID PK, request FK, institutional/technical duty, person ID, UNIQUE envelope digest, exact payload/signature bytes; UNIQUE(request,duty) and UNIQUE(request,person). | Real signer registry/key/version/decision/expiry/withdrawal evidence, retention/access and no-UPDATE credential enforcement. Signed decisions/times currently live in verified payloads. |
| Events / `g1d_p1_proto_events` | Monotonic PK, UNIQUE event UUID, optional request/account FKs, controlled event type, timestamp and evidence bytes. UNIQUE(request,event_type) enforces one admission/claim/execution reservation/consumption per request; NULL request allows independent global revocation fixtures. | Production event taxonomy, multiple reconciliation/history requirements, authenticated recorders, append-only grants and external receipt custody. The one-event-per-kind constraint is specific to this one-attempt prototype and must not silently constrain a future general ledger. |

All four tables use InnoDB and case-sensitive ASCII identifier comparisons; binary signed payloads remain BLOBs. FKs restrict deletion; no cascades. Existing role name uniqueness is retained. Database constraints enforce structural invariants, while signatures, separate-person rules, exact scope and legal transitions require trusted locked services. Database uniqueness over success scope is tested independently of the role-name check.

The candidate does not add/change any existing account or role column. A future four-table adoption would add relationships from requests/events to accounts, requests to roles/audit, and approvals/events to requests. It requires a separate official ERD amendment, model/migration review, hash/pin reconciliation, credential matrix, backup rehearsal and explicit deployment authorization. Ledger infrastructure must precede any live P1; the earlier phase labels do not authorize reversing that dependency.

**Retention policy in this prototype:** preserve all admitted synthetic request/approval/claim/execution/cancellation/revocation/consumption rows until that test's guarded scratch-table teardown; preserve test results in this document/Git. No purge method or production retention default was added. Real evidence retention, access, encryption/backup, legal hold and erasure periods remain owner/institution decisions before real enrollment or ingestion.

## 5. Privileged writer inventory and demonstrated limits

| Writer class inspected or accounted for | Protected state it can affect / release requirement |
| --- | --- |
| `access_control/mutations.py` | Role grants/account overrides under an existing Service mutex. Reserved-role protections exist, but it is not coupled to the prototype control row. |
| `accounts/admin_bootstrap.py`, `registration_review.py`, `models.py`, `services.py` | Account activation/approval, role assignments or account creation affect executor eligibility and selected before-state; bootstrap/review locks differ. These must be fenced/accounted for in a real maintenance window. |
| `init_system_roles`, registration-review metadata/binding/transition/release/recovery management commands | Canonical roles, services/permissions, binding activation or compensating changes. Their distinct guards/release gates are not proof they share a global provisioning protocol. Keep unchanged and exclude concurrent invocation. |
| Sandbox seeders, test helpers, manual Django shell/ORM, ad hoc scripts | May directly create/update security rows when credentials permit. Enforce their environment guards; never run them against the live protected target during release. Existing untracked `Scripts/`, `review_only/` and administrative scripts were preserved, not executed or certified. |
| Framework Django Admin | Inspected registrations are read-only. A framework flag is not app authority; custom shell/DB access remains a separate writer capability. |
| Web/API/worker/deployment processes, DBA SQL clients, scheduled jobs and external tools | Repository inspection cannot attest all deployed sessions or credentials. A future DBA-approved admission fence, active-transaction drain and least-privilege execution credential must positively account for these. No session termination, grant, revocation or production fence was performed. |

The scratch `simulate_fenced_writers=True` parameter is an explicit **test assumption**, not an implemented fence or independent authorization. One test holds the control-row lock while a separate uncooperative SQL/ORM writer successfully commits a lookalike role; provisioning then refuses. This demonstrates that locks constrain participants and existing records, not every absent alias or privileged writer. Passing concurrency tests does not certify global protection.

For this narrow prototype, any non-ASCII existing role name also forces refusal. This conservatively rejects cross-script test lookalikes but is **not** a production Unicode-confusable implementation or a change to ordinary role policy. Final Unicode strategy and writer exclusion remain release blockers.

## 6. Tests and actual results

Commands use the existing virtual environment from `backend`, with `-B`; the shell does not expose the interpreter on PATH. Access to the installed interpreter/MySQL required approved execution escalation. No dependency/environment file changed.

```powershell
.\.venv\Scripts\python.exe -B manage.py test apps.access_control.test_task2_g1d_p1_production_authorization_contract --settings=config.test_settings --noinput
```

- Initial run: 69 tests, failed with two fixture errors. The superuser-negative fixture regenerated an unrelated incarnation and was refused before reaching the intended eligibility boundary. A cursor mock through Django's connection proxy interfered with `SimpleTestCase` teardown. Both fixture root causes were corrected without weakening security assertions.
- Review strengthened durable one-attempt handling, actual consumption-event correlation, constraint tests and competing physical-connection assertions. Intermediate isolated run: **74/74 passed**, 14.305 seconds. Intermediate full regression: **1031/1031 passed**, 155.063 seconds, before the final idempotency refinement.
- The idempotency refinement passed **75/75** isolated tests (18.903 seconds) and **1032/1032** full tests (163.311 seconds). Final review then hardened the guard to reject routing hooks and secondary database aliases before writes. The additional router-negative test initially used an unimportable fake router name; Django rejected the fixture during settings override. It was replaced with an actual redirector object, keeping the isolation assertion intact.
- Final isolated source: **76/76 passed**, 18.342 seconds, exit 0; 28 static/signature contracts and 48 actual disposable-MySQL cases. Django reported database creation/destruction and clear system checks. No `--keepdb`.
- Final full regression against the frozen final source: **1033/1033 passed across 44 modules**, 225.372 seconds, exit 0. The established sorted Accounts/Access Control `test*.py` module-enumeration pattern was used. Count reconciles to the previous 957 plus 76 new tests. Django reported fresh database creation/destruction and clear system checks; no `--keepdb`. Simulated existing RuntimeError log messages did not fail the suite. The intermediate regressions are not substituted for this final result.
- Migration consistency: `.\.venv\Scripts\python.exe -B manage.py makemigrations --check --dry-run --settings=config.settings` returned **No changes detected**, exit 0. No model/migration or main-schema change was introduced and no live migration was applied.
- Post-test SELECT-only main-schema verification: preparation/P0 report passed against configured/actual `ctug_workspace`; 1 active canonical Admin, **0 Technical Super Admin roles/aliases/assignments/bindings**, 0 active direct governance overrides, 0/6 Core K definitions, 1 active governance Service, and **15 audit records**. Introspection confirmed **17 tables** and **0 prototype/production governance-ledger tables**. The four-role initializer remains unchanged. No main-database write was performed; live `--apply` remains unavailable. This did not repeat or certify backup/restore readiness.

Covered results include independent synthetic signatures, purpose/scope tampering, duplicate people/keys, revocation/expiry/cancellation, actor eligibility and framework separation, no grants/assignments, exact inactive role/audit/consumption, shared-table uniqueness/FKs/CHECKs, durable reservations, nested-transaction refusal, stale selected state, actual concurrent claim/resource consumption with distinct MySQL connection IDs, rollback after real audit INSERT, rollback after consumption/event INSERT, unexpected assignment rollback, and a blocked in-flight resolver.

Commit tests inject errors at the driver `commit()` boundary: one raises before the protected COMMIT and resolves NOT_COMMITTED; another actually calls MySQL COMMIT then raises an acknowledgment error and resolves COMMITTED on a fresh connection. Reservation acknowledgment and postcommit reporting failures are also covered. These are real transaction/commit tests with injected acknowledgment faults, **not server-process crashes, network-partition tests, power-loss tests or production disaster recovery**.

The tests do not install governance permissions, promote a real account, enable `--apply`, change the general initializer, enroll a real signer or create anything in `ctug_workspace`. Every role/ledger/audit/assignment fixture write is inside the generated disposable database and is torn down.

## 7. Production blockers and next approval gate

- Independently verified people/appointments, authenticated enrollment, pinned real roots, signed current trust manifests, issuer custody, protected signing devices/clients and real executor proof remain unavailable. Injected test trust is never real approval.
- Final ledger schema/constraints/retention/grants require owner/DBA approval, official ERD/migration/pin review and a separate deployment decision. No production model or migration was created.
- Pending/rejected human admission workflows, independently authenticated revocation administration, root rotation, evidence access controls and tamper-resistant retention are not operational. The revocation method is explicitly a synthetic fixture hook; it cannot establish real governance authority.
- Global writer fencing, least-privilege credentials, complete deployed-writer/session inventory, real clock health and production environment/server/incarnation checks remain unimplemented. The prototype proves neither credential confinement nor privileged DBA exclusion.
- General JCS/Unicode decisions and real dependency/release certification remain open. Current encoding/ASCII refusal is deliberately narrower.
- Independent append-only receipt custody, external anti-rollback trust/consumption checkpoints, fresh ledger-aware encrypted backup/restore, RPO/RTO, actual crash/network-fault tests and a reviewed UNKNOWN/recovery runbook remain separate operations/security acceptance work. No automatic retry is permitted.
- Existing production preparation `--apply` remains disabled. Activation, assignment, Core K installation/grants, first-account bootstrap and later protected management remain separately blocked.

Next: owner review of the separate schema candidate and outstanding trust/retention/fencing/recovery decisions. Do not proceed to production infrastructure, migrations or live authorization from passing prototype tests. **D7 remains withheld.**

## 8. Repository and commit gate

Commit eligibility is limited to the three new test-only Python paths and this acceptance/schema-review document, after final tests/checks and exact staged review. Preserve the existing untracked design proposal and all unrelated work. No push.

The official ERD's inspected SHA-256 is `BEFB42DF64A6D10B1AA0828A8E2A0A62FF3167B2B35DADCFA973FECF6D54C6D1`; retain its pre-existing modification byte-for-byte. Never stage `.env`, credentials, private keys, backups, `Scripts/`, `review_only/`, unrelated documentation/team files or the ERD. Verify branch/HEAD, empty index before scoped staging, exactly four staged paths, tested working bytes matching the index, no production imports of the new helpers, and `git diff --cached --check` before committing.
