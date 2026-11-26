# Academic Settings controlled local activation preparation

26 November 2026 · branch `ronald` · starting commit `2a1bca1`.
**Current follow-up from `7d9624f`: authorized access-control maintenance and full inventory
complete; seven Academic Settings migrations rehearsed only. Operational acceptance NOT PERFORMED.**
Ronald completed the two authorized live access-control migrations, exact scope-table reader
grant and full read-only inventory in the owner-confirmed current-session window. All seven
Academic Settings migrations remain unapplied to `ctug_workspace`. v2.3 stays inactive, switches
OFF and independent governance review OPEN. The original preparation and existing implementation
milestones are preserved; no HDAC provisioning, launcher approval, feature activation, workflow
Human Approval, WF-11.02–11.04 work, push or merge occurred.
The existing untracked `docs/workflows/WF11_Reconciliation_2026-11-25/` is preserved and is not
included in this commit. It is supporting evidence already present in the owner's workspace;
the committed workflow catalogue and governance proposals also contain the relevant boundaries.

## 1. Governance verification and candidate status

Reviewed the [consolidated proposal](../security/WF11_AcademicSettings_Permission_Governance_Proposal_2026-11-26.md),
[fee proposal](../security/WF11_FeeSchedulePermission_Overlay_Proposal_2026-11-25.md), pinned v2.0,
v2.1/v2.2 deltas and validators, effective resolver, genuine Admin/Student checks, selected-role
inheritance, account override role scopes, ordinary appointment gate and affected permission constants.
The manifests are static planning specifications; effective runtime authority comes from stored
role grants/account overrides and the resolver. A static delta is not provisioning.

Candidate: [v2_3_delta.json](../../review_only/academic_settings_v2_3/v2_3_delta.json),
[proposed addendum](../../review_only/academic_settings_v2_3/ADDENDUM_PROPOSED.md),
[offline validator](../../review_only/academic_settings_v2_3/proposal.py),
[unapplied application patch](../../review_only/academic_settings_v2_3/runtime_changes_PROPOSED.patch).
They reside outside the active catalogue directory and have **no runtime loader or installer**.
All existing protected source/catalogue pins and validators remain unchanged. The unchanged v2.2
validator passes, with effective digest
`192ba955d1dae06bfbdf574e52ef454390b9fd41b803f63778d1d220b6cd8c6d`.
Both prior overlays still report independent review `OPEN`; do not imply that v2.3 resolves that.

| Boundary | Current stored-default specification / runtime | Proposed only |
| --- | --- | --- |
| Semester fee | Treasurer default; runtime additionally requires a genuine Admin **role grant**, so pinned defaults authorize nobody | Move `finance.fee_schedule.manage` Treasurer → Admin. Definition/service/scope unchanged; direct Grant alone still insufficient. |
| Official verification | `academic.profiles.manage`; genuine Admin and valid Admin/TSA-inherited context | `academic.enrollment_verifications.record` → Admin |
| Own onboarding writes | `clearance.requests.self.submit`; genuine Student and selected Student context | `academic.semester_onboarding.self.submit` → Student |
| Historical participation | Both `academic.periods.manage` and `academic.profiles.manage`; genuine Admin | `academic.historical_participation.correct` → Admin; protection/two-person rule pending |
| Curricula / offerings | `academic.courses.manage` / `academic.periods.manage` plus separate switches | Keep exact codes, clarify definitions only; instructor assignment remains separate |

The candidate has 98 permission definitions and 109 default bindings (v2.2: 95 / 106).
School Admin gains no `access_control.*`; Technical Super Admin gains no business default and
still needs its stored Admin assignment. Treasurer retains collection/payment/receipt/ledger
authority. Student gains no verification, signing or fee-management authority. No broad Allow
is copied to a replacement code. New role defaults and missing/disabled live bindings still need
holder-by-holder impact review; equality of intended role names is not proof of unchanged access.

## 2. Guarded read-only impact inventory

The eight-table preflight found `account_permission_role_scopes` absent. After the owner authorized
the reduced scope, the seven-table reader was created, verified and used. The reduced snapshot
found zero of 13 definitions, zero in-scope bindings and overrides, and none of the three service
rows. After the separately authorized access-control maintenance and exact scope-table SELECT
grant, the full inventory completed at 20:19:41 Asia/Manila with the same zero counts. Persisted
scope evidence is available and both scoped-Grant scenarios are modeled.
[Full and earlier inventory results](../security/WF11_Permission_Inventory_Preflight_2026-11-26.md).

[permission_inventory.py](../../review_only/academic_settings_v2_3/permission_inventory.py) is a
standalone DB-API reader. Its default invocation prints the query plan **without importing a
driver or connecting**. It accepts no SQL or database name from the caller. The explicitly
authorized path requires the exact acknowledgment below, loopback MySQL, an existing SELECT-only
identity (no write privileges, role grants or GRANT OPTION), an owner-held pseudonym key, expected
InnoDB tables, verified database identity, and a read-only consistent transaction. Failure stops;
there is no fallback to application credentials. Session transaction settings and ROLLBACK are
the only non-SELECT/SHOW operations; the script never creates, updates or deletes a record.

Prepared operator invocation from the repository root, **only after specific owner authorization**:

```powershell
# In a fresh operator process, supply an EXISTING read-only identity without printing its secret.
# WF11_INVENTORY_DB_HOST=127.0.0.1; WF11_INVENTORY_DB_PORT=3306
# WF11_INVENTORY_DB_USER / WF11_INVENTORY_DB_PASSWORD: owner-supplied, SELECT only.
# WF11_INVENTORY_HMAC_KEY: owner-held random secret of at least 32 bytes; retain separately.
backend\.venv\Scripts\python.exe review_only\academic_settings_v2_3\permission_inventory.py --authorize-read-only OWNER_AUTHORIZED_CTUG_WORKSPACE_PERMISSION_SELECT_ONLY
```

Do not substitute the application's writer/root identity or create/change credentials during this
task. If no suitable reader already exists, stop and arrange that separately. Capture stdout in
an owner-restricted file outside Git. Do not paste personal identities or the pseudonym key into
chat, source control or acceptance evidence. Account tokens are HMACs of internal numeric IDs;
the owner can resolve a specific token locally using the retained key. No name, school ID, email,
password or verification reference is selected. Even pseudonymous reports remain restricted evidence.

The report enumerates active/inactive role bindings, account `Grant` (**Allow**) / `Deny` entries,
Grant role scopes, potential holders of old codes, multi-role combinations, per-context potential
expansion/loss and Denies requiring review. It distinguishes losing the Treasurer HDAC fee code
from losing fee-setting operations (already refused without an Admin-role source).
It models source-based **potential** impact, not a live permission attestation: feature switches,
appointment verification, scoped-grant gate state, eligibility and the real selected request
context must also be checked before provisioning. The full mode requires the scope table and
consistent storage. The separately authorized `--without-role-scopes` mode requires the exact
seven reader grants and marks role scope as unavailable. Counts and pseudonymous row evidence
must be reviewed before any grant plan.

## 3. Deny preservation and rollback of permission transitions

The unapplied patch narrows the effective resolver with a **Deny-only** predecessor map:

| Replacement | Old active account Denies that still block it |
| --- | --- |
| `academic.enrollment_verifications.record` | `academic.profiles.manage` |
| `academic.semester_onboarding.self.submit` | `clearance.requests.self.submit` |
| `academic.historical_participation.correct` | Either `academic.profiles.manage` or `academic.periods.manage` |

This affects session hints and every fresh operation/locked recheck. Old-service deactivation or
a Grant's selected-role scope cannot neutralize an account-wide Deny. A new-code Deny also wins;
query failure grants nothing. Fee uses the same code, so existing fee Denies continue directly.
Keep **every** old Deny, including inactive history. Before cutover, independently review the
inventory's missing new-code Denies and Grant conflicts. Do not overwrite an existing new-code
Grant blindly: the database permits only one override per account+permission.

Permission cutover, if later approved: features off → snapshot relevant bindings/overrides/scopes
and pin/code versions → reviewed new permissions/bindings and any approved Deny additions → install
the reviewed runtime/validator together → verify effective permissions in each selected context →
only then consider feature activation. The current protected executor/provisioner has **no v2.3
operation authorized by this package**. Its separate reviewed contract remains a blocker.
Rollback first turns affected features off, restores the prior runtime and precisely the reviewed
old role-binding state, retains all Denies, deactivates only newly approved Allow bindings if
authorized, and rechecks old-code Deny behavior. Do not delete new Denies or old Denies, and do
not restore a whole database over intervening authorized business writes without a recovery plan.

## 4. Targeted boundary and regression evidence

Selected Student context was already exclusive even when the account also had Admin/Instructor
assignments. The notice-only overview belongs to the legacy **unselected union** context; its
Student semester data remains gated. Non-Student selected contexts retain authorized work.
The actual bypass was the provider's generic `access_denied` → `inactive` conversion, and its
dependence solely on the presence of a read permission. A Student read Deny/stale permission set
could therefore expose the normal home before onboarding. The committed correction keeps a
selected Student gated on refusals/missing read permission and unavailable sources. A validated
selected non-Student context does not depend on the Student status endpoint, even when an
account Grant gives it a Student read hint. Student status refusals never unlock the gate.
The provider also remounts on a confirmed context change: a Student → other role → Student
roundtrip cannot reuse an earlier semester's completion while the fresh status read is pending.
That stale-completion exposure was reproduced with a held status response before correction.
Role metadata here only narrows routing; exact permissions still control modules and every API.
The frontend flag still defaults off; no backend authority or permission constant is activated.

The reported frontend failures are **the same failure**: suite `dashboard-navigation.test.mjs`,
test “every permission code in the registry exists…”, assertion
`appointment-evidence: access_control.appointments.record`. Reproduced from immutable Git sources
at `51d0904` (before Academic Settings), `13da643` and `2a1bca1`, using the same installed test
toolchain. `appointment-evidence` is a navigation item, not a newly failing test suite.
The test reads `v2_0.json`; that permission is absent there. No pinned catalogue, navigation
expectation or test has been weakened to hide it. Reproducer:

```powershell
node review_only/academic_settings_v2_3/reproduce_frontend_baseline.mjs
```

Results and limitations are recorded in [verification evidence](WF11_Activation_Verification_2026-11-26.md).
No full new backend-regression claim is made from targeted suites alone.

## 5. Owner/security decisions still required

| Decision | Concrete evidence and required resolution |
| --- | --- |
| Fee revision after any obligation | Current approval refuses `obligations_assessed` once **any** Student obligation exists, including a zero-value obligation. A proposed Draft may remain saved but cannot replace the approved rate. This prevents silent differences between Students and preserves immutable snapshots. Confirm this conservative policy; no adjustment/waiver/refund workflow is included. |
| Historical two-person review / protection | Current correction may be performed by the School Admin who recorded the evidence; self-correction is refused, but no second-Admin comparison or review receipt exists. Decide whether a distinct second authorized School Admin is mandatory and what protected handling means. Keep the correction switch off pending resolution; the candidate's ORD metadata is provisional, not approval. |
| Adviser clearance sign-off | SRS v0.4 `FR-CLR-02` limits signing to an actual current teaching, **adviser**, Treasurer or fixed-signatory appointment. WF-06.02 step 4 currently enumerates subject Instructors, applicable Treasurer fee sign-off and School Admin final approval. The SRS lists appointment conditions; it does not by itself mandate every listed appointment as a requirement. Decide whether adviser sign-off is required in this campus workflow, its exact purpose/period and appointment source; do not equate it with the read-only SSG Advisor role. |
| Fixed-signatory appointment | Current clearance creation snapshots real subject instructors; Treasurer and School Admin requirements are Pending role requirements with no invented person. No fixed-signatory appointment resolver or signing workflow is implemented in this slice. Decide which existing approved appointment source, validity dates, replacement/revocation and separation rules apply before any signing is enabled. No additional signatory role is proposed. |

Reconcile FR-CLR-02 and WF-06.02 by recording an owner decision referencing both, then a separately
reviewed specification amendment **if** a required signatory is added/removed or semantics change.
Neither approved text nor Human Approval is changed here. Creating Pending requirements is not
authorization to sign. Student onboarding activation needs explicit acceptance of this minimum
scope and the unresolved signatory boundary; signing/issuance remains outside this delivery.

## 6. Migration and progressive activation handoff

Use the exact [migration and activation runbook](WF11_Migration_and_Activation_Runbook_2026-11-26.md)
and [operational acceptance checklist](WF11_Operational_Acceptance_2026-11-26.md).
The generated [offline evidence](../../review_only/academic_settings_v2_3/offline_repository_evidence.json)
contains the complete dependency closure, expected columns/constraints and the actual launcher
registry. All 11 relevant registry features have empty approved mode lists. The runbook inventories
14 backend switches and their 14 frontend counterparts. Live read-only verification found the
seven Academic Settings migrations and their 24 tables pending.
[Live ledger and schema evidence](WF11_Migration_and_Activation_Runbook_2026-11-26.md#authorized-ledger-check-and-isolated-restore-rehearsal).

The first proposed access phase is School Admin Draft periods and Academic settings, followed by
curricula/offerings/instructors, fee configuration/approval and explicit semester activation.
Student onboarding/finalization and historical correction remain separate later approvals.
Do not change `modes` or export a flag as a workaround during this preparation.

## 7. Authorization and next controlled activation decision

> I authorize only the prepared read-only permission impact inventory against local
> `ctug_workspace`, using an existing SELECT-only account and owner-held pseudonym key.
> No records, credentials, permissions, migrations, feature switches or launcher approvals may change.

The owner subsequently authorized both live access-control migrations, their verification, the
existing reader's scope-table SELECT grant, the full inventory and the isolated seven-migration
Academic Settings rehearsal. The owner confirmed **Ronald** as operator and the current session
as the maintenance window, with writers stopped through verification. A fresh encrypted backup
passed restored-data verification before live execution. `0004` and `0005` are now present once
each; their two new tables are empty and all 17 original application tables are unchanged.
The full inventory completed and the seven-target isolated rehearsal passed all 24 expected
tables, 224 columns and 90 prepared integrity queries. Final live checks at 20:20:55 Asia/Manila
confirmed all seven Academic Settings migrations and their 24 tables still absent.
[Maintenance and recovery evidence](WF11_Migration_and_Activation_Runbook_2026-11-26.md#authorized-local-maintenance-execution-26-november-2026).

The genuine remaining phase-one gates are separately authorized **actual Academic Settings
migrations**, the existing minimum **two services, five v2.2 definitions and five active Admin
bindings**, and the runbook's governance/provisioning, launcher and operational acceptance
approvals. The full inventory still finds those services/definitions/bindings absent.
[School Admin phase-one minimum](WF11_Migration_and_Activation_Runbook_2026-11-26.md#reviewed-minimum-for-phase-1).
The existing fee, proof/retention, signatory and historical-protection decisions in §5 continue
to gate their respective later phases. v2.3 remains proposed/inactive; its independent governance
review is OPEN. All 14 switch pairs stay OFF, launcher modes are unchanged, and workflow Human
Approval remains pending. The live scope dependency, reader grant, full inventory and isolated
seven-migration rehearsal are complete and are no longer activation blockers.
