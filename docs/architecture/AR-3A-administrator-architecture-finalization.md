# AR-3A — Administrator Architecture Finalization and Implementation Planning

Date: 7 November 2026, Asia/Manila.
**Status: PROPOSED final architecture and development plan; approval pending.**

This phase authorizes only this new document. It does not approve a schema,
catalogue, grant, bootstrap identity, governance exception or live mutation.

Evidence labels used throughout:

- **CONFIRMED:** existing behavior verified by focused source/static inspection;
  not a claim that tests or a live database were rerun.
- **USER-STATED:** intended behavior explicitly required by the current request
  and SRS v0.3; implementation details may still need approval.
- **PROPOSED:** recommended implementation, not approved or implemented.
- **UNRESOLVED:** a security/operational decision that blocks dependent work.
- **NOT IMPLEMENTED:** no complete working capability is evidenced in inspected
  application source. A proposed code or UI does not establish that capability.

## 1. Executive summary

**USER-STATED:** Normal Admin uses the existing `Admin` application role. Super
Admin combines school administration and protected access governance; Django
framework Superuser is separate and cannot bypass CTU-G application checks.
One Account retains multiple eligible roles. SSG Advisor and Finance Monitor
are one read-only monitoring responsibility, never two roles.

**PROPOSED:** finalize role composition as `Admin` + protected governance role,
provisionally retaining the persisted name `Technical Super Admin` for compatibility.
Display the combined application profile as **Super Admin**. Use one optional
`SSG Advisor` role, assigned to an eligible Instructor. Keep permissions dynamic:
roles contribute defaults, direct Grant adds, direct Deny overrides every source,
and business services enforce ownership, appointment, period and conflict rules.

**CONFIRMED:** the existing evaluator and schema already represent these role
unions and Grant/Deny semantics. B2 intentionally rejects actor-assigned roles,
reserved roles/governance codes and some multi-role recipients. Those protections
must remain in the ordinary path; a new protected workflow and finer policies are
needed. The existing services are not a complete revised administrator system.

**PROPOSED:** Django compatibility should use explicit persisted framework flags
and a restricted framework authorization adapter, without adding PermissionsMixin
or merging Django permissions into custom effective permissions. The preferred
minimum Account change is two false-default Boolean columns; it requires separate
ERD/model/migration approval. Session revocation and durable approval/event evidence
have additional storage decisions, described separately rather than hidden in that
two-column proposal.

The next small development task should repair the C1 source-location dependency
without weakening its hash or changing historical grant data. In parallel with
that planning dependency, the owner must resolve the decision register before
catalogue-v2 approval, protected writes, privileged provisioning or activation.

## 2. Recommended final architecture

### 2.1 Requirements, provenance and present evidence

**CONFIRMED:** the actual Markdown requirements file is
[docs/SRS/CTU-G_Workspace_SRS_v1.md](../SRS/CTU-G_Workspace_SRS_v1.md).
Its content identifies **SRS v0.3**, dated 7 November 2026, with status proposed
for review. `CTUG_Workspace_SRS_v0.3.md` is not present at the requested locations.
An adjacent v0.3 DOCX exists; this review uses the Markdown content, without
claiming equivalence between the two formats. No document was renamed.

| Source | Actual location / evidence status |
| --- | --- |
| AR-2 | [Architecture proposal](AR-2-revised-administrator-access-control.md), original review document; proposals still require decisions. |
| SRS v0.3 | Markdown above; SHA-256 `AF4EAD4F88BDB0877AB6C3B8965BEC5CAF0F058D74AB0D878EC690379210346F`. |
| C1 | [Original catalogue proposal](../implementation/access-control/phase1h-c1-permission-catalogue-governance-proposal.md); original content preserved under relocated path. SHA-256 `02EB308DB5AFF1491EA2D024F5F7F1074125E3A7B9BB02DBD1409F6A6170A99E`. |
| A / B1 / B2 | [Evaluator report](../implementation/access-control/phase1h-a-permission-evaluator.md), [audit report](../implementation/access-control/phase1h-b1-transactional-audit.md), [mutation report](../implementation/access-control/phase1h-b2-trusted-permission-management.md); explicitly reconstructed historical reports. Current source is authoritative. |
| C2A | [Planner report](../implementation/access-control/phase1h-c2a-catalogue-validator-readonly-planner.md); reconstructed, not the deleted original implementation report. |
| Registration | [Implementation report](../implementation/authentication/phase2-registration.md), checked against relevant registration source. |
| ERDs | [Full DBML](../database/full_schema.dbml), [auth DBML](../database/schema.dbml); strictly read-only. |

The 286 passing backend tests, MySQL 8.4.13, 16 live tables, 22 applied migrations,
four initialized roles and empty application catalogue are **previously reported**
baseline facts, not independently rerun in AR-3A. No database connection, test-suite
execution, Django setup or migration command was necessary for this review.

Focused inspection covered Account/manager/registration, access-control models,
evaluator, B1 audit allowlists, B2 delegation/mutation boundaries, catalogue JSON
and validator, settings/URLs and the guarded test runner. AR-2 already records
installed Django 6.1.2 auth/admin behavior and its official references. No full
project audit or frontend inspection was repeated.

### 2.2 Role composition and service boundaries — PROPOSED

1. **Normal Admin:** active assigned `Admin` role, approved school defaults and
   exact effective action permissions. No default role-template editing, protected
   promotion, governance grants or framework privilege.
2. **Application Super Admin:** active `Admin` plus active protected governance
   role, account eligibility and effective governance permissions. The governance
   role by itself is not the complete profile. Title or membership never replaces
   code, delegation, target and object checks.
3. **Django Superuser:** separately provisioned framework privilege, independently
   authenticated and audited. No implicit application roles or custom permissions.
4. **SSG Advisor:** one optional responsibility role added to Instructor; exactly
   the three approved monitoring reads in §5, without Treasurer write powers.

Keep separate trusted boundaries for ordinary school-role assignment, ordinary
Super Admin default/override management, protected promotions/governance changes,
framework maintenance, and one-time bootstrap/recovery. Do not expose a universal
“edit account privileges” service that accepts arbitrary role/permission IDs.

This final recommendation prefers composition over Admin plus per-account profile
Grants: direct overrides lack profile version/lifecycle and can leave partial
governance privileges after removal. Separate flat Normal/Super Admin roles would
duplicate school defaults and complicate the existing `Admin` contract. A new
profile table is unnecessary for composition; approval/evidence storage is a
different requirement. See AR-2 §3 for the full option comparison.

**UNRESOLVED:** approve the governance role's persisted name. Retaining `Technical
Super Admin` preserves existing reserved-name behavior; renaming requires explicit
manifest, reserved-name classification, collation and test changes. It cannot be
treated as a cosmetic UI rename.

## 3. Administrator comparison matrix

All operational abilities below are **USER-STATED targets** with **PROPOSED**
authorization boundaries, not implemented interfaces or current grants.

| Operation | Normal Admin | Application Super Admin | Django Superuser |
| --- | --- | --- | --- |
| Approve/reject Student/Instructor registration | Exact school permission; other-account review only | Same school duties | No automatic CTU-G authority |
| School accounts, academic settings, instructors/advisers/sections, clearance and announcements | Approved school scope and contextual checks | Same approved school scope | No automatic CTU-G authority |
| Attach/remove eligible additional ordinary role | Explicit recipient/role allowlist; no self-assignment | Same ordinary rules | No automatic CTU-G authority |
| Promote/remove Normal Admin | No default authority | Protected Admin-assignment workflow | No automatic CTU-G authority |
| Promote/remove another Super Admin | Never ordinary assignment | Independent protected review, exact delta, last-operator safety | Framework flag alone is insufficient |
| Edit role defaults | Denied, even with a misplaced direct management Grant | Effective composite profile + authority + approved service/code/recipient scope; protected/shared-role changes require stronger workflow | No automatic CTU-G authority |
| Account Grant/Deny/deactivation | Default no; narrow delegation only after separate approval | Exact operation/target policy, no self-targeting ordinary changes | No automatic CTU-G authority |
| Auth/security monitoring | Redacted eligible school events only | Approved redacted governance/event scope | Reviewed technical event surface |
| Governance settings / activation | No | Versioned, specifically approved settings/change workflow; no blanket configuration write | No automatic application-policy change |
| Confidential student/payment/rating/signature records | Per-record school duty only | Same record/privacy requirements; no title bypass | Custom APIs remain subject to custom evaluator and object policies |
| Django Admin | No by default | No by default | Only reviewed registered maintenance surface; no generic protected-model CRUD |

## 4. Multi-role authorization matrix

### 4.1 Confirmed equation and dynamic behavior

**CONFIRMED:** for a persisted default-database Account that is Approved/active,
has at least one active assigned role and requests a permission in an active Service:

`Effective = (union(active role grants) ∪ active direct Grants) − active direct Denies`

Requested roles do not contribute. Inactive grants, roles and Services do not
contribute. Invalid references/codes and evaluation failures deny. `Account.has_perm`
delegates to the evaluator and denies object-specific calls until an object policy
exists. No role name or Django flag supplies a custom bypass.

Role-default changes update `role_permissions` once, not every holder's account
overrides. After commit, subsequent fresh permission reads see the change under
the normal READ COMMITTED workflow. They do not retroactively undo an in-flight
action or an older transaction snapshot. No permission set may be persisted as
authoritative session data. Frontend menu visibility follows capability reads;
each backend action still rechecks current permission and resource scope.

| Account composition | USER-STATED behavior | PROPOSED safeguards / current gap |
| --- | --- | --- |
| Student + Treasurer | Preserve student tools and authorized Treasurer operations | Deny conflicting own-payment collection, receipt issuance, exemptions and sign-off; require another authorized person where appropriate. Check Account→profile→payment ownership. Expenses do not encode all beneficiary conflicts. |
| Instructor + Admin | Preserve teaching duties plus Normal Admin authority | Ordinary academic/registration duties remain scoped. No self-review or self-appointment to gain access; no ordinary editing of any assigned Instructor/Admin template. |
| Instructor + Admin + governance | Super Admin and teaching duties through one identity | Separate reviewed governance assignment; no self-grant, unrestricted assessment/finance access or automatic framework flags. |
| Instructor + SSG Advisor | Retain Instructor and add one read-only financial responsibility | Three approved projections, appointment/period scope, no Treasurer write bundle, audited appointment/revocation. |
| Any combination with active Deny | Deny wins over all contributing roles/Grants | Role selection in the UI cannot bypass Deny. Removing Deny is privilege-increasing and fully authorized/audited. |

**PROPOSED:** ordinary additional-role assignment initially permits only
`Treasurer` for an eligible Student and `SSG Advisor` for an eligible Instructor.
Initial Student/Instructor base membership comes from approval. Changing/removing
base identity roles is not an ordinary extra-role action. Broader combinations
require a separately approved eligibility rule. Existing base roles are retained.

Direct overrides are account-wide, not linked to the role that justified them.
Removing Treasurer can leave a finance Grant effective through an active Student
role. Revocation must assess every positive source and dependent override; remove
or deactivate explicitly reviewed dependent Grants, or require continuing
appointment eligibility at the protected business boundary. Do not create a broad
Deny merely to simulate role revocation or silently delete unrelated overrides.
Instructor removal likewise cannot leave an ineligible Advisor appointment active.

No duplicate School ID, second account, temporary role detachment, role-name
relabeling or selected “active role” is an acceptable authorization workaround.

## 5. SSG Advisor / Finance Monitor clarification

**USER-STATED and settled terminology:** one responsibility. Do not ask whether
these should be separate roles, and do not create both. **PROPOSED representation:**
one optional role named `SSG Advisor`, added to Instructor, with exactly these
three new scoped-read candidates:

| Financial view | PROPOSED permission | Data boundary; NOT IMPLEMENTED |
| --- | --- | --- |
| Financial Overview | `finance.monitoring.overview.read` | Approved period aggregates; no individual balances, payer identifiers, credential data or raw images. |
| Financial Reports | `reports.monitoring.financial.read` | Approved Final-report projection only; totals/approved lines, no Draft working data, generation, finalization or export authority. |
| Transaction History | `finance.monitoring.transactions.read` | Approved dates/types/amounts/status and non-sensitive references; exclude school IDs/names by default, raw receipts, signatures, expense images and secrets. Any identified detail needs a separately approved requirement. |

Exact report lines, date ranges, appointment periods, redaction and aggregation
rules are **UNRESOLVED**. These defaults describe a privacy-minimizing recommendation,
not a claim that existing reports already expose only these fields. Query services
must enforce access on lists, detail links, downloads and cross-period requests.

Existing `finance.summary.read` and `reports.financial.final.read` may later share
implementation primitives if their scopes truly align, but are not silently
redefined or granted to Advisor. `finance.ledger.read` and `finance.payments.read`
are working/detail reads, not safe synonyms for monitoring history. Separate codes
avoid granting broader historic permissions while the new projection is reviewed.

No payment recording, transaction editing, receipt issuance, expenses, exemptions,
role management or export permission is a default Advisor grant. Missing grants
suffice; do not install global Denies that unexpectedly defeat another reviewed
role. Because union can add rights from Treasurer, **PROPOSED** default policy
forbids Advisor/Treasurer coappointment for the same monitoring scope unless an
independent conflict exception is approved. A read-only role does not make a
multi-role account read-only.

Appointment duration/revocation must be documented before use. `account_roles`
has no expiry/period fields; explicit independently audited revocation is
representable, automatic duration is not implemented. Approve an enforceable
appointment record/expiry mechanism or keep time-limited appointments blocked.

## 6. Existing compatibility and implementation-ready governance policies

### 6.1 Reuse and conflicts

| Component | CONFIRMED reusable behavior | NOT IMPLEMENTED / required revision |
| --- | --- | --- |
| `accounts`, registration service/views/serializers | Hashed credentials; anonymous CSRF; atomic Pending/inactive Account and profile; no assigned roles | Separate approval/provisioning/session workflows. Do not expand public inputs or route privileged creation through registration. |
| Evaluator and `Account.has_perm()` | Union, Deny, fresh eligibility, strict codes, fail-closed behavior | Retain global semantics; implement business object/appointment checks around them. |
| `roles`, `account_roles` | Shared roles and unique multiple memberships; assigned-by/time | New assignment/promotion services. Removal deletes membership link; audit before/after atomically. No role-link active/expiry field. |
| `role_permissions`, `account_permissions` | Shared defaults; unique current Grant/Deny with active flag and attribution | New Super Admin gate, approved templates/recipients, protected workflow and lifecycle handling. One override per account/code cannot encode several independent exceptions. |
| B1 writer | Persisted real actor, constrained snapshots, owning atomic transaction, failure rollback | Authentication/anonymous events, full metadata, framework flags and approval evidence need reviewed event contracts. B1 does not authenticate or authorize its caller. |
| B2 ordinary services | Exact management + service-delegation authority, locked rereads, durable transaction, no-op behavior, self/reserved/governance protection | Cannot manage protected roles or all required combinations. New entry contracts must enforce effective Super Admin profile; ordinary function availability is not SRS v0.3 compliance. |
| C1/C2A | Exact historical 10/82/96 comparison, strict source validation, read-only planning and MySQL collation checks | Stale C1 location, fixed five-role/default matrix, no SRS compatibility model. Preserve history; add a distinct v2 representation later. |
| Settings/admin | Custom Account, auth/session/admin middleware, mounted `/admin/`, application models unregistered | No working framework provisioning or revised AdminSite/backend. Django Admin route alone is not compatibility. |

### 6.2 Protected service contract — PROPOSED

All future change services use trusted persisted actor/target references resolved
from authenticated context, canonical permission/role identifiers, controlled reason,
explicit operation and an expected state/policy revision. Protected operations also
require a verified approved-change reference. A raw actor ID or supplied approval
Boolean is not authentication. The caller does not choose their authority/scope.

| Operation | Actor and target rules | Required behavior before commit |
| --- | --- | --- |
| Approve/reject registration | Eligible Normal/Super Admin with exact school permission; another Pending Student/Instructor request | Lock/reread request and role eligibility. Approval atomically sets review/Approved/active and base role; rejection preserves proper attribution. No copied per-account defaults. |
| Ordinary additional role | Exact ordinary-assignment authority; allowlisted Student→Treasurer or Instructor→SSG Advisor; no self-target | Retain base role; validate appointment/conflicts and dependent grants on removal; audit actual link delta. Admin/governance targets are not silently admitted. |
| Normal Admin promotion/removal | Effective Super Admin plus protected Admin-assignment authority; eligible other account | Apply only approved Admin membership; retain Instructor if held. Removing Admin from a governance holder invokes protected/last-operator checks. No implicit governance or framework flags. |
| Additional Super Admin | Protected governance-assignment authority, independent approval and verified real target | Exact composite-profile delta, eligible human, effective authority analysis, minimum-quorum/recovery checks; no ordinary role-assignment route. |
| Ordinary role-default edit | Effective composite Super Admin, management code, service delegation and exact permission/recipient rule; actor holds no target role | Preview and recheck exact role/code enable/disable delta and affected counts/overrides. No protected namespace/role or actor-access change through this path. |
| Individual override | Exact Grant, Deny or deactivation policy and target eligibility | No self-targeted ordinary writes. Reserved/admin recipients use protected workflow. Deny removal/replacement requires explicit privilege-increasing authorization; preserve unrelated state. |
| Protected template/governance/config change | Additional protected authority and independently bound approval; no general bypass switch | Check current actor impact, minimum effective operator predicate, approval expiry/replay and exact state. Only reviewed settings keys/policy revision; no arbitrary file/model edits. |
| Recovery | Separate in-band protected workflow or independently authorized out-of-band ceremony if no operator remains | Real identity, bounded approved delta, full evidence/audit, session revocation and checkpoint. No fake actor, global Deny removal or temporary unrestricted role. |

Role-default authority is exclusive to the effective Super Admin profile. A Normal
Admin holding an erroneous direct management Grant must still be refused. Having
the composite roles without the exact effective code or with active Deny is also
insufficient. Recheck this gate under locks, not in an unlocked façade/UI only.

**PROPOSED result semantics:** return changed/no-op and the approved bounded result
only after the owning transaction commits. Authorize and validate even a repeated
no-op; no duplicate audit or refreshed timestamps for a genuinely authorized
unchanged operation. Denial, stale review/policy, invalid reference or audit failure
returns no success and leaves all mutation state unchanged. No hidden retry of an
approval, bootstrap or side-effecting request after uncertain commit status.

### 6.3 Precise limits on default edits and self-escalation

**PROPOSED:** retain ordinary B2 refusal of any role currently assigned to the
actor, including inactive-role assignments for this guard, and all direct
self-override operations. An Instructor+Super Admin needs an independently
authorized non-Instructor executor for an ordinary Instructor-template change.

All Super Admins share Admin and governance, so a second Super Admin is not
automatically independent of changes to those templates. **UNRESOLVED:** approve
a narrow protected exception with institutional review that is independent of
the benefiting role holders, a distinct authenticated executor where required,
and durable exact-delta evidence. Until then these edits remain blocked.

No routine API may pass `allow_self`, disable Deny precedence, relabel governance
permissions as ordinary modules, temporarily remove a role, change a Service to
evade checks or assign the same authority through another role. Direct and indirect
effects on the actor's effective authority are part of the protected impact review.

### 6.4 Review evidence, concurrency and rollback

**PROPOSED review record:** bind operation, target, canonical code/role delta,
requester, real approver identity/evidence, authorized executor, manifest/policy
revision, exact relevant before-state digest, expiry and single-use/replay state.
An approval is invalidated by changed reviewed state or authority; a browser impact
preview/confirmation is not independent review. Inspect identifiers/counts rather
than unrelated student records in the impact preview.

**UNRESOLVED storage:** choose reviewed database change/approval records or a
durable verifiable external approval system with equivalent replay/availability
guarantees. Existing audit reason codes and JSON snapshots cannot represent this
contract. Proposed database record sets would be `governance_change_requests`
(delta, state/revision digest, requester, executor, expiry, status) and
`governance_change_approvals` (request, verified approver, decision/time/evidence).
These are schema design candidates, not new tables or approved migrations.

Every real mutation must own one durable default-MySQL transaction, reread
authorization and review state, mutate, consume its approval and append supported
audit events atomically. Audit failure rolls back everything. B2 durable entry
points cannot be nested in an ordinary outer atomic block; refactor shared safe
primitives explicitly before composing workflows.

Adopt one lock protocol across permission, role-assignment, account-status,
governance and session-version writers: calculate the complete dependency set;
lock Service rows in ascending ID including the existing governance mutex;
then permission definitions, approved-change records if stored locally, Accounts,
assignments, Roles, grants/overrides and target rows in agreed deterministic order.
Respect B2's existing rank/order and parent locks for absent-row races. Do not
introduce a “governance mutex first, then a lower-ID target Service” path alongside
B2's sorted Service locking. Abort/replan if a new dependency would require
acquiring an earlier-ranked lock. Finalize this order with concurrency tests before
enabling any writer; config deployments must use the same policy-revision barrier.

### 6.5 Last effective Super Admin

**PROPOSED minimum core capability set K**, subject to owner review:

- `access_control.catalogue.read`
- `access_control.role_permissions.manage`
- `access_control.account_permissions.manage`
- `access_control.effective_permissions.inspect`
- `access_control.audit.read`
- `access_control.admin_assignments.manage` (new candidate)

An effective operator is a real Approved/active Account with both active Admin
and governance membership, every K code effective after Deny/service gates, and
a usable approved governance workflow/policy. Core-code possession alone does
not establish per-service delegation or authorization to elevate another Super
Admin. The exact necessary review quorum/recovery path must remain available.

Before and after any relevant proposed change, compute this predicate under the
shared serialization protocol. Reject a transition leaving zero effective
operators, except an explicitly approved recovery transition that restores the
invariant atomically. Cover suspension, role/default revocation, direct Deny,
Grant deactivation, role/Service disabling, authority metadata and policy changes.
Count effective people, not rows named Super Admin. Test simultaneous removals
and policy changes; one sequential check per endpoint is insufficient.

**PROPOSED operational target:** at least two independently recoverable human
operators in normal operation. A one-person initial checkpoint requires explicit
approval and independent institutional recovery; it must not manufacture a second
identity. **UNRESOLVED:** exact quorum/independent reviewer eligibility and the
usable-workflow predicate, especially while protected codes remain blocked.

### 6.6 First operator, authentication audit and session invalidation

**PROPOSED first application operator:** a separately approved ceremony verifies
the actual named person, independent institutional authorization, minimal signed
manifest/delta, secure credential handling, first-init lock, checkpoint, replay
prevention and recovery. It does not authorize itself through rows it will create.
A reviewed first-init mechanism must work before the governance Service exists;
the existing mutex cannot serialize creation while absent.

If approved, the ceremony persists that real person's Account/profile and minimal
Admin/governance authority atomically, then records initial events against the
newly persisted human with independent external attestation. This self-attribution
is **not approved** merely because a foreign key can be satisfied. Approve an
initialization event/evidence contract before implementation: B1 currently accepts
IDs, flags and bounded security enums, not full metadata, approval digests or
framework flags. Never fabricate an actor, use a borrowed/null identity, suppress
audit, or seed unrestricted permissions. A Django Superuser flag is not bootstrap
application authority. If these conditions cannot be met, bootstrap stays blocked.

**PROPOSED logging:** keep authorization changes in supported atomic B1 events;
design separate secure authentication/framework event storage and redacted read
projections. Failed anonymous login has no persisted actor and cannot be forced
into B1's required-actor FK. Choose approved external structured storage or new
event schema with retention/access policy. Normal Admin sees eligible school
activity only; governance views exclude credentials, tokens, bodies and unrelated
business data. Denied attempts may be security events, not fake successful mutation
audit entries. Django Admin LogEntry is not equivalent to either contract.

**PROPOSED session policy:** revoke/require reauthentication after suspension,
credential recovery, role addition/removal, effective default/override changes,
governance promotion and framework-flag changes. Recheck permissions on each
protected request even before session expiry. Privilege additions must not silently
upgrade a potentially stolen pre-promotion session; require fresh step-up evidence.

For implementation, prefer a persisted Account `security_version` integer initialized
to zero, copied into a session at login and compared on every protected request.
Increment it inside the owning security transaction for all affected Accounts;
stale sessions fail on their next request. This is a **separate optional schema
proposal**, not part of the current Account model or the minimum two framework flags.
An approved per-account session registry is an alternative. Generic post-commit
cookie deletion or cross-process cache clearing alone is not a complete revocation
guarantee. Bound large role-template changes and lock affected Accounts consistently;
reject an over-limit batch until an atomic maintenance plan is approved. Do not
partially revoke or partially audit a template update. Physical session cleanup
may follow commit; authorization must already reject stale versions. Define
in-flight-request and expiry limits explicitly; revocation cannot undo committed work.

## 7. Catalogue-v2 change proposal

### 7.1 Historical identifiers and compatibility disposition

**CONFIRMED by JSON/static inspection:** C1 v1 has 10 services, 82 unique codes,
96 proposed role bindings, five role definitions, seven delegation families and
readiness counts F=9/P=62/B=11. These are historical planning definitions, not
initialized permissions. No exact final v2 total or final grant count is claimed.

| Existing service / codes | PROPOSED v2 disposition |
| --- | --- |
| `accounts` (9) | Retain all existing identities. Own-profile/registration-review/suspend/activate codes remain valid. Restricted provisioning/recovery remain blocked; do not reinterpret them as ordinary role attachment or Django flag authority. Add narrower school-account listing and auth-event read candidates below. |
| `access_control` (19) | Keep both management constants, catalogue/effective/audit/diagnostic reads and seven exact delegation families. Retire broad `role_assignments.manage` from new grant selections in favor of explicit ordinary/Admin/governance assignment codes; preserve its historical definition as blocked/deferred, with no silent alias or DB deletion. Other protected operations stay blocked. |
| `academic` (8), `clearance` (13), `group_rating` (10), `announcements` (3), `notifications` (2) | Retain all existing identifiers and scoped descriptions. Reconcile role composition/recipient policy, not broader record access. `clearance.messages.send` remains blocked. No implementation is inferred. |
| `finance` (13) | Retain existing codes for their existing finance duties; no Advisor default working-ledger/payment/receipt/write grants. Add two separate monitoring reads. |
| `reports` (5) | Retain Draft/Final/generate identifiers with their original scope. Keep finalization/export blocked. Add the minimized Advisor report-read code. |
| `support` (0) | Keep public-only help scope; no invented protected permission or new support-ticket system. |

“Retain” means stable historical identity, not approved readiness, activation or
grant. Any actual metadata change, service move or retirement must produce a
reviewed delta and CONFLICT/DEFER against existing data. Never silently broaden a
stored code, map old grants to a stronger replacement, or rename numeric IDs.

Specific contract changes requiring review:

- `access_control.role_permissions.manage` and
  `access_control.account_permissions.manage`: identifiers remain exact B2
  constants; revised service entry points require effective Super Admin eligibility
  and the new operation-specific policy. F still identifies existing internal
  contracts, not completed revised workflows or APIs.
- `access_control.role_assignments.manage`: replace its broad grant intent with
  the three new assignment capabilities below; leave old definition blocked and
  ungranted until explicit retirement/migration policy is accepted.
- `access_control.technical_accounts.provision/recover`: clarify application
  governance-operator provisioning/recovery only. They do not authorize Django
  staff/superuser flags. Any metadata wording change must be an explicit v2 diff.
- `access_control.effective_permissions.inspect` and `.audit.read`: retain
  governance scope; new school-limited reads are separate codes, not automatic
  grants of full technical inspection to Normal Admin.
- Seven `access_control.delegate.<service>` codes remain exact and have no
  automatic defaults. Explicit service authority still does not create a scope.
  Do not invent `delegate.accounts` or `delegate.access_control` to bypass
  protected governance classification.

### 7.2 Explicit new-code candidates — PROPOSED, not runtime features

The following table is a candidate delta, not a v2 manifest. `A` = Admin, `G` =
protected governance role, `V` = SSG Advisor. Role defaults below are conditional
recommendations only. `—` means no default; B candidates stay blocked. All new
capabilities are NOT IMPLEMENTED. No new service or database-generated ID is needed.

| Service | Permission code | Permission name | Module | Action | Description | Default | State |
| --- | --- | --- | --- | --- | --- | --- | --- |
| accounts | accounts.school_accounts.read | Read eligible school accounts | school_accounts | read | List approved school-account fields for authorized school duties; exclude credentials, governance operators and unrelated confidential records. | A | P |
| access_control | access_control.school_access.inspect | Inspect school account access | school_access | inspect | Inspect eligible ordinary accounts' roles and permitted capability summaries; exclude protected technical records and secrets. | A | P |
| access_control | access_control.role_assignments.ordinary.manage | Manage ordinary extra roles | ordinary_role_assignments | manage | Attach or remove approved Treasurer/SSG Advisor responsibilities for eligible other accounts; never assign Admin, governance or framework privilege. | A | P |
| access_control | access_control.admin_assignments.manage | Manage school Admin assignments | admin_assignments | manage | Promote or remove another eligible Normal Admin through protected review, actor-impact and last-effective-operator safeguards. | G | P |
| access_control | access_control.governance_assignments.manage | Manage governance assignments | governance_assignments | manage | Reserved independently approved application Super Admin elevation/removal; no self-assignment or ordinary-role shortcut. | — | B |
| access_control | access_control.role_templates.protected.manage | Manage protected role templates | protected_role_templates | manage | Reserved exact-delta changes to protected or actor-assigned templates with independent review and effective-operator checks. | — | B |
| access_control | access_control.policy_settings.manage | Manage reviewed governance policy | policy_settings | manage | Reserved versioned allowlisted access-policy changes; never arbitrary settings files, secret configuration or unreviewed service activation. | — | B |
| accounts | accounts.authentication_events.school.read | Read school authentication events | school_authentication_events | read | Read redacted events for eligible school-account activity under an approved event-source and privacy contract. | A | P |
| accounts | accounts.authentication_events.governance.read | Read governance authentication events | governance_authentication_events | read | Read approved redacted privileged authentication/security events; no credential, token, request-body or business-record access. | G | P |
| access_control | access_control.audit.school.read | Read school access audit | school_audit | read | Read scoped ordinary school-account/assignment security changes; exclude protected governance detail and unrelated personal data. | A | P |
| access_control | access_control.recovery.authorize | Authorize governed access recovery | governed_recovery | authorize | Reserved independently verified in-band recovery approval; unavailable-operator recovery still requires a separate institutional ceremony. | — | B |
| finance | finance.monitoring.overview.read | View financial monitoring overview | financial_monitoring | read_overview | Read approved period aggregates for a valid Advisor appointment without identifying individual payer data or finance write access. | V | P |
| reports | reports.monitoring.financial.read | View monitoring financial reports | financial_monitoring | read_reports | Read a minimized approved Final-report projection for the Advisor appointment; exclude Draft, generation, finalization and export. | V | P |
| finance | finance.monitoring.transactions.read | View monitoring transaction history | financial_monitoring | read_transactions | Read approved redacted transaction-history fields for the Advisor period; exclude identifying detail, raw receipts/images and mutation rights. | V | P |

Governance code placement is intentional: assigning even Normal Admin's narrow
`access_control` capabilities requires a protected reviewed initializer/governance
path. Ordinary B2 cannot grant them merely because their new default is Admin.
Specialized school duties do not confer template-management power.

### 7.3 Default-role matrix changes — PROPOSED

| Role/profile | Starting set | Additions / exclusions for review |
| --- | --- | --- |
| Student | C1 Student defaults | No new administrative/Advisor defaults. Treasurer is a separate assigned responsibility; preserve own-record controls. |
| Instructor | C1 Instructor defaults | No automatic Admin or Advisor role/grants. Teaching/rating/class scope retained. |
| Treasurer | C1 Treasurer defaults | No Advisor/governance/admin writes by implication. Own-finance conflicts apply when also Student. |
| Admin / Normal Admin | C1 Admin school defaults as conditional proposals | Add the five A-marked candidates in §7.2 only after review/readiness. Keep existing permitted finance-summary/Final-report scope, no raw ledger or global template authority. Exemption workflow remains gated by maker/checker policy. |
| Governance role G | C1 governance-role defaults as conditional technical proposals | Add the two G-marked P candidates only after review. Keep own-profile/technical reads and management constants; no business-data defaults or blanket delegation. Protected B codes have no defaults. |
| Composed Super Admin | Union of Admin and G | No separate duplicate role/template. A Deny still defeats either source; protected permissions/operations require the separate approval workflow. |
| SSG Advisor V | New optional role, dependent on eligible Instructor | Exactly the three V-marked financial monitoring reads. Other Instructor abilities come from Instructor, not a duplicated Advisor bundle. |

The C1 X/business coassignment prohibition was a proposed policy, not a schema
constraint. Replace it in v2's compatibility rules with the user-required reviewed
composition and specific conflict rules. Do not preserve that obsolete prohibition
as a reason to split an Instructor administrator into two identities.

**Keep blocked:** both `accounts.school_accounts.provision/recover`; catalogue
initialization authority, service activation, the old broad role-assignment code,
governance grants, technical account provisioning/recovery; clearance message send;
report finalization/export; and the new B candidates. Each may be unblocked only
by an explicit later policy, implemented service and test decision—not just by
changing its readiness letter. None gets a default grant in this proposal.

### 7.4 Delegation and planner compatibility

**CONFIRMED:** B2 uses a per-service Cartesian product of codes and recipient role
names, rejects all reserved-role targets/accounts and actor-assigned-role edits,
and requires all active target roles inside the scope. This is deliberately safe
but too restrictive for some Student+Treasurer and Instructor+Admin overrides.
Widening role names would be too broad: a Student-only target could receive
Treasurer operator codes. A selected-role UI context cannot fix account-wide Grants.

**PROPOSED successor:** explicit rules keyed by operation, service, code and exact
recipient predicate. Treasurer-required with Student allowed as an additional role
must differ from Student-only. Instructor+Admin targets use the protected path,
not a reserved-role exception in B2. Advisor reads/appointments need separate
eligibility; removing Deny and governance authority require distinct review tiers.
Validate each cross-product/predicate and lifecycle rule against named positive
and negative combinations. Keep all legacy scopes OFF until replacement approval.

**Safe source-path correction proposal:** preserve C1 v1 JSON bytes, logical source
path and expected content digest. Add a narrowly reviewed resolver mapping that
logical historical path to the exact relocated original under
`docs/implementation/access-control/`. Verify content bytes against the same pinned
hash before any database access. If both known paths exist, verify both and reject
any digest conflict; if neither exists or content differs, fail closed. No recursive
search, title matching, arbitrary path argument, hash refresh or reconstructed-file
substitution. Record the mapping as provenance, not policy approval.

This fixes location only. V2 requires a distinct version with SRS/decision/source
digests, the reviewed role composition, one Advisor role, explicit code lifecycle/
replacement metadata, exact new default pairs, blocked contracts and finer scope
policy. Do not mutate v1 to pass new counts. The current validator's five roles,
fixed source tables and count matrix cannot validate v2 unchanged. The planner must
understand historical versus revised intent, flag unresolved requirements as DEFER,
preserve unknown/inactive/overridden records, and retain MySQL collation and zero-write
guarantees. Never translate a retired grant to a replacement automatically.

## 8. Django Superuser integration assessment

**CONFIRMED:** Account extends AbstractBaseUser; its manager extends BaseUserManager,
uses `school_id` as USERNAME_FIELD, hashes passwords and creates only Pending/inactive
ordinary accounts. `create_superuser()` deliberately raises before saving. Staff/
superuser are false class attributes, not fields; `last_login=None` is not persisted.
Stock framework permission relations/methods are not supplied by PermissionsMixin.
Settings do not configure a custom auth backend. Mounted Django Admin and empty
application model registrations do not establish working privileged administration.

**PROPOSED preferred integration:**

- Add explicitly approved persisted `is_staff` and `is_superuser` flags, no automatic
  role-to-flag mapping, no second AUTH_USER_MODEL and no automatic application grants.
  Restrict `create_superuser()` to authenticated/attributable technical provisioning
  that validates identity/password/true flags and Approved/active eligibility. It
  must not call public creation with unsupported extras or fake reviewer metadata.
- Keep Account's custom `has_perm()` application-only. Never add an active-superuser
  shortcut or fallback union of Django groups/permissions. Framework evaluation may
  use an explicit isolated Django-compatible adapter within the reviewed maintenance
  site; it is not the permission source for custom APIs. Any future async/bulk
  application methods must preserve the same deny semantics.
- Do not add PermissionsMixin by default. It introduces a superuser field, Account
  group/user-permission join tables and stock privilege shortcuts/caching, without
  supplying the separate staff field. Overriding one synchronous method does not
  prove every inherited permission route safe. Full mixin adoption is an alternative
  requiring a larger explicit migration and backend/method review.
- Use a dedicated restricted AdminSite/form/backend and allowlist of maintenance
  functions. Check Approved/active state and fresh framework flags, technical access
  policy and step-up evidence. Stock active/staff checks alone omit CTU-G review
  status. A framework-only roleless operator can maintain approved framework areas;
  application APIs still require assigned-role and custom permission eligibility.
- Keep generic Account, profile, RBAC, audit and confidential business-model editing
  disabled, including direct URLs, actions, inlines, autocomplete/raw-ID, import,
  export and bulk update/delete paths. Review Django auto-registered auth models.
  ModelAdmin index hiding is insufficient. Any reviewed application action must
  invoke the same trusted application service and atomic audit with the actual
  authenticated actor; Django LogEntry is not a bypass.
- Do not use DRF IsAdminUser (`is_staff`) or stock DjangoModelPermissions as the
  application permission adapter. A Django Admin session on a custom API must pass
  normal permission, session-version and object checks.

Official Django extension behavior, corroborated by AR-2's installed-source
inspection, is documented in [custom users and permissions](https://docs.djangoproject.com/en/6.1/topics/auth/customizing/#custom-users-and-permissions)
and [AdminSite permission checks](https://docs.djangoproject.com/en/6.1/ref/contrib/admin/#django.contrib.admin.AdminSite.has_permission).

**UNRESOLVED:** if the owner requires unrestricted stock Django model administration,
that conflicts with protected-record/audit requirements. Reconcile the requirement
rather than silently weaken the custom boundary. Infrastructure/DB/OS administrators
remain a separate trust boundary; application flags cannot constrain raw DB access.

## 9. Database implications and change classification

Classification keys: **CFG** configuration-only; **CAT** catalogue data; **LOGIC**
application logic; **SERVICE** new trusted service; **SCHEMA** separate ERD/migration
approval; **POLICY** owner security decision. Several changes need multiple classes.

| Change | Classification | Exact impact / approval boundary |
| --- | --- | --- |
| Admin + protected governance composition; optional Advisor | CAT, SERVICE, POLICY | Current roles/membership/default tables suffice. No new profile column/table needed; no role rows initialized here. |
| Required role combinations and refined delegation | LOGIC, SERVICE, POLICY; CFG for reviewed registry | Current tables can represent grants/membership. Predicates and versioned policy are new; no wildcard settings edit or live registry enablement. |
| Narrow monitoring/log-read codes and revised defaults | CAT, LOGIC, SERVICE, POLICY | Existing varchar/FK fields suffice for proposed code definitions. Queries/event source/role matrix need separate implementation. |
| Framework flags | SCHEMA, LOGIC, SERVICE, POLICY | Preferred `accounts.is_staff BOOLEAN NOT NULL DEFAULT FALSE` and `accounts.is_superuser BOOLEAN NOT NULL DEFAULT FALSE`; existing rows remain false, IDs/passwords unchanged. Proposed consistency check: superuser implies staff. New reviewed migration; never edit historical migrations. |
| No PermissionsMixin preferred | LOGIC, POLICY | Custom framework adapter; no Account group/user-permission joins. Full mixin alternative adds those joins plus superuser, with staff separately. |
| Session revocation version | Optional SCHEMA, LOGIC, SERVICE, POLICY | Proposed `accounts.security_version` non-negative 64-bit integer, non-null default zero, plus server-side session comparison/increment. Alternative reviewed session registry; neither exists today. It is additional to the two minimum flags. |
| Independent approval/evidence | POLICY, SERVICE; SCHEMA if DB option selected | Request/approval record sets described in §6.4 require reviewed fields/FKs/retention and new tables; external signed evidence is an alternative with equivalent guarantees. Current audit JSON is insufficient. |
| Authentication/framework event history | POLICY, LOGIC, SERVICE; SCHEMA if new local store | Approve external event pipeline or event schema supporting unknown subjects, known actors, scope/retention. Do not make access_audit_logs actor nullable as a shortcut. |
| Existing atomic security audit | LOGIC, SERVICE, POLICY | Reuse supported B1 snapshots; approve versioned event/field/reason extensions for flags, approvals, initialization and review metadata before emitting them. No new DB column needed merely to add an approved bounded JSON key, but semantics/tests must change deliberately. |
| C1 path provenance resolution | LOGIC; documented CFG/provenance mapping | Exact pinned-location mapping, no catalogue/grant/model/schema changes. |
| Governance policy/config deployment | CFG, SERVICE, POLICY | Immutable reviewed revision + audit/serialization barrier; current settings are not a mutable database settings API. |

Minimum framework migration proposal: preserve all existing Account columns and
primary keys; add only the two reviewed false-default fields and, if approved,
the consistency constraint. Optional security-version/approval/event schemas must
be separately specified and approved, not quietly bundled. `last_login` is not
required for the selected adapter; current Django skips its standard update handler
when the attribute is not a field. No existing migration or ERD is modified now.

Any future schema phase must test generated SQL, existing-row preservation, empty
and populated upgrades, false flags, constraint behavior, migration reversal and
backup/restore on disposable MySQL. Before dropping privilege/session/evidence
columns during rollback, disable dependent interfaces and revoke affected sessions;
preserve audit/evidence. Do not roll back by restoring a stale snapshot that erases
later legitimate security changes. Production execution is a separate authorization.

## 10. Security risks and mitigation plan

| Risk | Required mitigation / approval gate — PROPOSED |
| --- | --- |
| Normal Admin gains default-edit power through direct Grant/second role | Composite eligibility + current effective management code and delegation inside transaction; protected authority issuance. |
| Super Admin title exposes all school/financial data | No custom evaluator bypass; minimal defaults and contextual list/detail/export policies. |
| Shared Admin/governance template causes self-benefit | Ordinary assigned-role denial retained; exact reviewed independent protected exception or deny. |
| Multi-role predicate widens Student-only finance rights | Per-operation/code/composition eligibility and negative tests; no broad legacy role-list widening. |
| Advisor appears read-only but union adds writes | One role, three read grants, explicit coexistence/conflict policy and total-effective-rights display. |
| Treasurer/Advisor role removal leaves powerful direct Grants | Source-aware impact/revocation and continuing appointment checks; preserve unrelated overrides. |
| Last nominal Super Admin has Deny/disabled Service/no usable workflow | Effective K/policy predicate under shared lock; concurrent transition tests and independent recovery. |
| First operator cannot satisfy actor FK legitimately | Real named persisted human plus independent approved initial attribution/evidence; no fabricated actor or silent audit omission. |
| Framework flags or Django Admin bypass custom services | Separate framework adapter/site, denied protected CRUD, normal custom permission checks and actual-actor audit. |
| Revoked or pre-promotion sessions retain authority | Fresh request permission checks, proposed session-version/step-up contract and transactional invalidation. |
| Partial audit/approval/session change commits | One owned transaction, supported bounded audit payload, approval consumption and version bump; failure rollback/no hidden retry. |
| Old C1 or reconstructed report treated as current authority | Preserve exact original digest/history, explicit relocation map and new v2/SRS compatibility validation. |

Future security acceptance must retain legacy tests for Deny, role-name/Django-flag
non-bypass, anonymous registration, self/reserved/assigned-role refusal in ordinary
B2, audit rollback and exact-code/collation behavior. Add positives only on the
new explicitly authorized paths, not by flipping ordinary negative assertions.
Test required role unions, finance self-interest, override lifecycle, profile
misgrants, protected review tamper/expiry/replay, simultaneous last-operator
changes, restricted Admin direct URLs, failed unknown-user auth events and stale
sessions. A framework provisioning success test may replace the current fail-before-
save test only after that provisioning/migration path is authorized; public
registration privilege-field rejection stays unchanged.

## 11. Owner approval decision register

The first row records settled user intent; all implementation decisions below
remain **PROPOSED / UNRESOLVED**. Requesting AR-3A did not approve AR-2's options.

| ID / state | Decision needed / recommended choice | Traceability / blocked work |
| --- | --- | --- |
| REQ / USER-STATED | Two application Admin profiles, separate Django Superuser, required multi-role combinations, one read-only SSG Advisor responsibility, explicit Deny and no title bypass | SRS FR-ACL-01–04/14, FR-DJA-01–07, FR-FIN-03–07; do not reopen these as optional goals. |
| A01 / PROPOSED | Adopt composition and provisionally retain `Technical Super Admin` as governance role name | AR2-01; OD-01; C1 D04/D06; role/name/manifest contracts. |
| A02 / UNRESOLVED | Exact ordinary assignment allowlist/prerequisites; recommended initial Treasurer/Advisor extra-role scope and protected Admin promotion | AR2-02; OD-03/06; C1 D03/D06; assignment services. |
| A03 / UNRESOLVED | Approve three monitoring projections, period/detail/redaction/export limits, Advisor duration and incompatibilities | AR2-03; OD-04/05/06; C1 D12/D16; finance reads/appointments. One responsibility already settled. |
| A04 / UNRESOLVED | Super Admin exclusive default editing, operation-specific overrides, fine recipient predicates; Normal Admin override default remains no | AR2-04; OD-08/11; C1 D05/D07/D08; mutation-v2 contracts. |
| A05 / UNRESOLVED | Independent shared-role/actor-impact exception, reviewers, execution identities, exact delta and replay/expiry binding | AR2-05; OD-02/08; C1 D06–D08; protected templates/elevation. |
| A06 / UNRESOLVED | Approve K, usable-workflow predicate, minimum human quorum, lock protocol and recovery | AR2-06; OD-02/09; C1 D08; last-operator changes. |
| A07 / UNRESOLVED | First real human identity, institutional authorization/attestation, minimal catalogue/activation delta, first-init lock and audit contract | AR2-07; OD-09; C1 D09/D10/D18; bootstrap/metadata writes. |
| A08 / UNRESOLVED | Two-flag schema/constraint versus reviewed alternative, restricted framework surface and technical provisioning/recovery | AR2-08; OD-10; FR-DJA; any model/ERD/migration/framework change. |
| A09 / UNRESOLVED | Durable approval and auth/framework event storage, retention/access, new safe audit event fields | AR2-09; OD-02/07/14; C1 D07/D10; approval/log interfaces and initial audit. |
| A10 / UNRESOLVED | Session-version column versus registry, exact revocation/step-up timing and large-change bounds | AR2-10; OD-13; C1 D11; session implementation. |
| A11 / UNRESOLVED | Approve candidate code/default delta, old-code retirement, revised source/decision metadata and exact v2 version | AR2-11; OD-12; C1 D01/D02/D04/D18; v2 approval/grants. Neutral provenance repair is separately bounded below. |
| A12 / UNRESOLVED | Per-service delegation grants, implementation readiness, settings activation and permitted write environments | AR2-04/11; OD-08/12; C1 D05/D18; no default wildcard or automatic activation. |
| A13 / UNRESOLVED | Business self-interest/signing, ratings, messages, report finalization/export/publication, privacy and operational recovery limits | AR2-12; OD-05/06/14; C1 D12–D17; corresponding business phases. |

C1 D01–D18 are not collectively resolved. Revised composition supersedes the old
proposed X/business coassignment ban as intended behavior, not as permission to
relax B2. Protected own-role exceptions, audit/attribution and all business-policy
blockers remain open until recorded owner decisions identify revision, approver,
date and exact accepted scope.

## 12. Prioritized dependency-aware implementation roadmap

All phases below need a separately authorized bounded task. Every writing test
uses the guarded disposable MySQL settings/runner; never development fixtures.
Live database execution requires additional explicit authorization, before/after
counts/digests, schema/migration fingerprints, backups/checkpoints and ERD hashes.

| Phase / dependency | Bounded deliverable | Required tests and rollback/stop boundary |
| --- | --- | --- |
| P0 — approvals | Record A01–A13 choices by dependency; distinguish settled requirements from accepted implementation | No DB changes. Unresolved items stay blockers; no blanket acceptance inferred. |
| P1 — AR-3B1 provenance repair; independent of privilege choices | Exact C1 relocation resolver, historical validation regression, new implementation note | Catalogue tests including absent/mismatched/dual-location conflict, immutable v1 and zero-write comparison. Revert only the task's source diff if needed; never reset existing work. No v2/model/live writes. |
| P2 — catalogue-v2 specification then read-only implementation; P0 relevant decisions + P1 | Freeze reviewed definitions/roles/pairs/policies; validate exact totals from data, add explicit v1/v2 planning and SRS blockers | Static lengths/canonical/duplicate/matrix/readiness/composition tests; scoped predicate negatives; disposable MySQL collation/no-DML/unknown-state tests. Retain v1 and no apply mode; roll back versioned code/artifact changes, no DB reversal needed. |
| P3 — approved schema/evidence design; A08/A09/A10 | Exact ERD/model/new-migration proposals for chosen flags, review evidence and session/event storage | Disposable upgrade/preservation/reversal and native MySQL checks, backup/restore rehearsal. No historical migration edits or live migration until separate approval. Do not bundle optional schemas without decisions. |
| P4 — trusted security foundations; P2 + approved P3 portions | Implement/test audit-event extensions, protected review/mutation/assignment primitives and effective-last-operator lock protocol | Denial, stale authority, mixed roles, dependency revocation, audit/approval failure, no-op/replay and concurrent lockout tests. Keep routes/mutations gated; reverting code must preserve evidence and never enable legacy shortcuts. |
| P5 — framework compatibility; approved flags/storage + P4 contracts | Restricted Account manager/backend/form/AdminSite integration without application roles or bypass | Framework-only roleless positives; custom API negatives; flags/group/bulk/async paths and Admin direct-URL/action audit tests; session invalidation. No actual Superuser creation. Disable site/provisioning and revoke sessions before any approved schema rollback. |
| P6 — first application operator; P0 + minimal approved catalogue/P4 and evidence/first-init tests | One separately authorized minimal named-human ceremony, minimal governance metadata/profile and implemented authority, checkpoint and recovery | Disposable concurrent/replayed/bootstrap/audit-failure rollback tests first. Live creation is a separate approval. After commit use reviewed compensating governance changes, never destructive reset or evidence deletion. |
| P7 — remaining controlled catalogue; P2/P6 | Idempotent metadata-only import with inactive new Services, followed by separately reviewed exact grants and activation stages | Unknown/inactive/conflict preservation, duplicate/race/audit rollback, repeated no-op and unchanged IDs/timestamps tests. Metadata alone grants nothing. Reverse only approved attributable deltas; no pruning. |
| P8 — school approval/role assignment endpoints; P4/P7 | Connect tested ordinary/protected services, preserve registration, validate appointment/privacy rules | Disposable atomic approval/base-role, protected promotion denial, self/conflict/dependent-override/revocation tests. Gate routes until authentication is ready; API end-to-end depends on P9. Preserve legitimate data/audit on rollback. |
| P9 — session authentication/events/CSRF; chosen P3/P4 contracts | Secure application and framework session eligibility, step-up/version checks, event source and current capabilities | Anonymous login CSRF/origin, throttles, session fixation/logout, stale/promoted/suspended sessions and log redaction tests. Disable entry points/revoke affected sessions on rollback; retain audit/event records. |
| P10 — shared dashboard and admin management UI; P8/P9 | One permission-aware layout; defaults versus per-account exception workflows; reviewed impact confirmations | Forged API calls denied, stale-menu refresh, accessibility, exact mutation/audit integration. UI removal does not replace backend denial. |
| P11 — campus modules; per-module policy/schema/readiness approval | Academic/clearance/finance/rating/announcements/report services and three Advisor projections | Cross-user/class/period, own-finance conflicts, read-only Advisor, safe upload/report/privacy tests. Roll back features/flags through reviewed mechanisms; no record destruction or erased history. |

P4 security services precede actual bootstrap even though the user-facing feature
roadmap lists administrator creation early: initial writes need already tested
authorization, audit and serialization. Framework implementation is an independent
branch, not authority for application bootstrap. Minimal approved core catalogue
creation is part of the explicitly authorized first-operator ceremony; bulk
catalogue initialization follows it, avoiding an unaudited actor/catalogue cycle.
Application and framework provisioning may belong to the same real person only
through separately authorized procedures. No single seed/createsuperuser command
is the proposed development plan.

## 13. Exact next Codex development prompt

**PROPOSED next task: AR-3B1 — C1 provenance repair only.** This neutral correction
does not require silently choosing unresolved privilege policies. Using this prompt
would authorize its stated code/test scope, not adopt the whole AR-3A architecture.

> Continue CTU-G Workspace with Phase AR-3B1: Exact C1 Source Provenance Repair.
> Read `docs/architecture/AR-3A-administrator-architecture-finalization.md` §7.4
> and the existing catalogue validator/tests. Preserve all tracked, untracked and
> deleted work; do not repeat a full audit.
>
> Implement only a narrow source resolver for the C1 v1 validator. Keep the
> existing `c1_v1.json` bytes, logical original source path, original C1 content,
> source SHA-256 and 10-service/82-code/96-binding semantics unchanged. Permit
> only the historical source path and the exact known relocated original:
> `docs/implementation/access-control/phase1h-c1-permission-catalogue-governance-proposal.md`.
> Require the pinned digest
> `02EB308DB5AFF1491EA2D024F5F7F1074125E3A7B9BB02DBD1409F6A6170A99E`.
> If both known files exist verify both and reject any mismatch; reject missing,
> differing or reconstructed replacement content before database access. No
> recursive discovery, arbitrary source arguments, weaker hashes or policy repair.
>
> Limit edits to the catalogue validation/resolution code, focused catalogue
> tests, and one new implementation report under `docs/implementation/access-control/`.
> Add tests for relocated original, missing source, changed digest, conflicting
> dual locations, identical accepted copies and unchanged immutable baseline.
> Preserve existing manifest/source/digest, roles, delegation configuration,
> readiness and default matrices. Do not add v2 or change planner classifications.
>
> Run Django checks and the relevant catalogue tests using the existing guarded
> disposable MySQL infrastructure with `--settings=config.test_settings`; never
> create development fixtures. Do not run the entire backend suite unless a new
> failure or changed dependency warrants it. Verify the real read-only planner
> with before/after local row/schema/migration/ERD evidence using the existing
> verifier, without any development writes. Confirm disposable schemas are removed.
>
> Do not edit models, ERDs, migrations, settings, frontend or existing documents;
> do not apply/seed/activate permissions, enable live mutations, provision any
> administrator, invoke createsuperuser, commit or push. Report exact changed
> files, tests, read-only results and preservation evidence, then stop. State that
> C1 remains historical and AR-3A/v2 security decisions remain unapproved.

### AR-3A verification and stop record

Only this new architecture document is created. Static preservation comparison
covers all 212 pre-existing paths, including recorded deletions. Both ERDs retain
their approved SHA-256 values and table/reference counts:

- Full: `E9235A87555FFCD50ECB6AB6C1A45F9C7C54E344FF8F269ECC890579F633E4B2`,
  42 tables / 80 references.
- Auth: `F050F7B910038532CA8E73B283F16A57DEDD6B738FDC74D293E64D539A4AFAC4`,
  9 tables / 17 references.

The new-code table is statically checked for canonical/global-unique identifiers,
existing service relationships, model field lengths, valid P/B states, no B
defaults and no collisions with C1 v1. This validates candidate syntax only, not
owner approval, scope safety, implemented endpoints or a final v2 catalogue total.
No backend/frontend tests, live database observations or security policy decisions
are presented as newly executed or approved in AR-3A.
