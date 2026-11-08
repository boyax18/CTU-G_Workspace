# AR-2 — Revised Administrator and Hybrid Dynamic Access Control Architecture

**Status: PROPOSED — architecture review only; project-owner approval pending.**
Date: 7 November 2026 (Asia/Manila).

Every recommendation, permission profile, integration option and implementation
sequence below is **PROPOSED**, not an approved policy or implementation task.
Statements labelled **Observed** describe inspected files. No live database was
queried, no code or existing document was changed, and no tests, migrations,
initialization, provisioning or permission mutations were executed for AR-2.

## 1. Executive summary

**PROPOSED:** represent Normal Admin as the existing `Admin` application role,
and application Super Admin as `Admin` plus a separately protected governance
role. Retain `Technical Super Admin` provisionally as that role's persisted name
for compatibility; display the combined profile as **Super Admin**. The governance
role is an additive responsibility, not an alternative school administrator,
blanket business-data privilege or Django Superuser. Its final name requires
approval. Nothing initializes either a governance role or a privileged account.

The central evaluator already supports multiple roles, role defaults, individual
Grant/Deny overrides and fresh evaluation. Keep its authorization equation and
explicit Deny precedence. The main work lies in trusted role-assignment,
protected-governance, finer recipient policies, object scopes and audit workflows.
Do not remove B2's reserved-role or actor-assigned-role prohibitions to make the
new profiles appear to work.

**PROPOSED:** use one optional `SSG Advisor` role for the single SSG Advisor /
Finance Monitor responsibility. An eligible Instructor retains Instructor rights
and receives three scoped financial reads. No second Finance Monitor role and no
Treasurer write powers are implied. A safe transaction-history capability is not
equivalent to the existing broad working-ledger proposal.

**PROPOSED:** support Django framework Superuser independently, through a narrowly
reviewed integration with two persisted Account flags, `is_staff` and
`is_superuser`, defaulting to false. This preferred option **requires a separately
approved ERD/model/migration change**. Do not add `PermissionsMixin` by default;
keep the application evaluator authoritative and restrict framework administration
through a dedicated AdminSite and explicit maintenance allowlist. Without schema
approval, leave framework provisioning unavailable rather than simulate it through
an application role or temporary Python attributes.

Security blockers remain: real first-operator attribution, independent governance
approval, effective-last-Super-Admin protection, reviewed initialization/audit
contracts, authentication-event storage, session revocation and exact finance
monitoring scopes. The historical C1 catalogue is not an approved SRS v0.3 seed.

## 2. SRS v0.3 mapping and inspected evidence

### 2.1 Actual requirements location and source hierarchy

**Observed:** the requested `CTUG_Workspace_SRS_v0.3.md` filename is absent under
both `docs/requirements/` and `docs/SRS/`. The Markdown file
[CTU-G_Workspace_SRS_v1.md](../SRS/CTU-G_Workspace_SRS_v1.md) identifies itself as
**v0.3**, dated 7 November 2026, with the exact revised administrator and SSG Advisor
requirements. AR-2 uses that file's content as the latest requirements baseline,
without renaming it. Its SHA-256 is:

`AF4EAD4F88BDB0877AB6C3B8965BEC5CAF0F058D74AB0D878EC690379210346F`

An adjacent `CTUG_Workspace_SRS_v0.3.docx` exists; this review uses the inspected
Markdown, not an asserted byte/content equivalence with the Word document. The
SRS's stated repository destination and several older report paths are stale.
Its status remains “PROPOSED FOR REVIEW,” not sign-off or write authorization.

Current SRS/use cases determine intended behavior. Existing DBML/model structures
determine representability. Source code determines implemented behavior. Older
catalogue proposals are comparison material, not authority to initialize privileges.

### 2.2 Requirement-to-architecture mapping

| SRS references | Target requirement | Observed support / PROPOSED resolution |
| --- | --- | --- |
| §§3.1–3.3; FR-ACL-04/08/14; OD-01/08 | Two default Admin profiles; only Super Admin governs role defaults | Compose `Admin` + protected governance role; permission checks and governance context remain necessary. Existing B2 alone does not implement the complete profile policy. |
| FR-REG-01–08; UC-01–03; AT-01/02 | Public registration stays ordinary; attributable atomic approval | Preserve implemented Pending/inactive account/profile registration with anonymous CSRF and no roles. Add separate approval/assignment service later; do not copy default grants per registrant. |
| FR-AUTH-01–07; FR-UI-01–06 | Sessions, fresh permissions and shared navigation | Session, current-user capability, revocation and dashboard APIs remain future work. Use fresh evaluator results plus server-side object policy; never a role-name menu as authorization. |
| FR-ACL-01–03/06/11; AT-11/15/16 | Union, Deny precedence, propagation, atomic audit and object scopes | Evaluator and existing audit patterns reusable. Business scopes, new mutation workflows and their tests remain necessary. |
| FR-ACL-05/07–10/12; FR-ADM-01–07 | Impact previews, explicit delegation, role assignment, protected changes | Separate ordinary assignment, default editing and protected elevation. Introduce reviewed finer recipient/operation rules and independently approved sensitive deltas. |
| FR-ADM-08; FR-FIN-06; AT-05 | Student + Treasurer | Keep both roles; enforce own-finance/conflicting-signature checks in business services. B2 account-override scopes currently reject some such targets. |
| FR-ADM-09; FR-FIN-03–05/07; AT-03/04 | Instructor + one SSG Advisor / Finance Monitor responsibility | Prefer optional `SSG Advisor` role, three read-only views, reviewed scope/appointment lifecycle. No extra Finance Monitor role. |
| FR-ACL-14; §3.1; OD-06 | Instructor + Admin, optionally governance | Permit reviewed composition; preserve Instructor role. No authority to edit one's assigned Instructor/Admin/governance templates through ordinary B2. |
| FR-AUD-01–05; FR-ADM-05/07; AT-12 | Attributable mutations versus redacted authentication monitoring | Preserve B1 for supported state snapshots; design separate auth-event contract/storage and school-view scope. Existing permission-change logs are not login history. |
| FR-DJA-01–07; UC-20; AT-13 | Separate Django Superuser without application bypass | Preferred minimal flag migration and restricted framework adapter; custom evaluator remains unchanged. Full compatibility is not present today. |
| FR-ACL-13; AT-14; OD-12 | Reconcile C1/C2A before initialization | Retain historical v1; propose a new version and explicit SRS compatibility metadata. Repair stale source references only in a separately authorized task. |
| FR-FIN-08; FR-CLR-02–05; FR-RAT-03/04; FR-COM-03/04 | Confidentiality, contextual duties and blocked operations | No Super Admin exemption from ownership/period/signatory/rating scope. Preserve blocked messaging, finalization/export and disclosure dependencies. |

### 2.3 Focused source evidence and limits

Inspected:

- [Account model/manager](../../backend/apps/accounts/models.py), registration
  services/views/serializers/URLs, account tests and empty application admin files.
- [Evaluator](../../backend/apps/access_control/services.py),
  [delegation contracts](../../backend/apps/access_control/delegation.py),
  [mutation services](../../backend/apps/access_control/mutations.py),
  [audit writer](../../backend/apps/access_control/audit.py), access-control models,
  catalogue manifest/validator, relevant test assertions, and configured auth/admin
  settings and URLs.
- [Registration report](../implementation/authentication/phase2-registration.md),
  [A evaluator report](../implementation/access-control/phase1h-a-permission-evaluator.md),
  [B1 audit report](../implementation/access-control/phase1h-b1-transactional-audit.md),
  [B2 management report](../implementation/access-control/phase1h-b2-trusted-permission-management.md),
  [C1 original proposal](../implementation/access-control/phase1h-c1-permission-catalogue-governance-proposal.md),
  [C2A reconstructed report](../implementation/access-control/phase1h-c2a-catalogue-validator-readonly-planner.md),
  and both approved DBML files.
- Installed Django auth/admin implementation and DRF permission adapters for the
  framework compatibility findings in §4. The installed Django version tuple is
  6.1.2, matching `backend/requirements.txt`.

The relocated A/B1/B2/C2A reports explicitly label themselves reconstructed
historical records. Source inspection takes precedence over their summaries.
The 286 passing tests and live MySQL 8.4.13 / 16-table / 22-migration / four-role
baseline are **historical evidence**, not newly verified database/test results.
No full-suite run or database connection was needed for this static review.

**Observed blocker:** C1 now exists under `docs/implementation/access-control/`,
with unchanged SHA-256
`02EB308DB5AFF1491EA2D024F5F7F1074125E3A7B9BB02DBD1409F6A6170A99E`.
Both the manifest and `validation.py` still require
`docs/phase1h-c1-permission-catalogue-governance-proposal.md`, which is absent.
Source inspection therefore predicts source-unavailable validation before database
comparison. The historical 286-pass result cannot be presented as a current result.
Even after an authorized path repair, the validator checks C1 fidelity, not SRS v0.3
compatibility; it currently cannot establish AT-14's requirements reconciliation.

## 3. Recommended administrator representation — PROPOSED

### 3.1 Options comparison

| Option | Security | Existing-schema compatibility | Scaling and management | Assessment — PROPOSED |
| --- | --- | --- | --- | --- |
| `Admin` + protected governance role | Clear assignment boundary; each permission and contextual restriction still checked. Governance-role defaults are a sensitive shared template. | Current `roles`, `account_roles`, `role_permissions`; no profile column required. B2 requires a separate privileged path. | Shared templates, clear promotion/removal audit, natural Instructor composition; need durable approval and last-operator controls. | **Preferred.** Matches SRS §3.1 while preserving separate school and technical responsibilities. |
| `Admin` + protected individual Grant profile | Grants can be narrowly tailored, but profile identity drifts across accounts; any partial/remnant grant may leave governance authority. | Current `account_permissions` supports Grant/Deny but no profile version, expiry or atomic multi-code profile membership. | Per-person maintenance, complex provisioning/revocation, difficult effective-operator inventory; direct Deny must still win. | Suitable only for exceptional bounded overrides, not the default Super Admin profile. |
| Separate flat `Normal Admin` and `Super Admin` roles | Simple labels but duplicated school defaults and ambiguous legacy `Admin`; role names still cannot authorize by themselves. | Rows can fit current tables; conflicts with four-role baseline and legacy reserved-name contracts require migration-of-policy/data review. | Duplicated templates drift, unnecessary replacement of existing role membership. | Less suitable than composition. |
| New persisted Admin-profile table/flag | Can encode versioned profile state, but creates another privilege source and consistency problem. | Requires new schema and integration; not necessary to express the two presets. | Potential approval/lifecycle benefits only if separately justified; not a substitute for dynamic effective permission evaluation. | Do not introduce merely to represent the two presets. |

### 3.2 Profile and authority rules

**PROPOSED:** `Admin` alone identifies the Normal Admin default profile.
`Admin` plus the active protected governance role identifies the Super Admin
profile. Keep `Technical Super Admin` provisionally; its role name alone grants
nothing and its proposed defaults remain technical. An Instructor can additionally
hold either profile only through explicitly authorized assignment.

Shared `Admin` defaults supply approved school duties to both profiles. Governance
defaults add only approved catalogue/permission-management/security reads. Role
composition does not authorize unrestricted payments, assessment bodies, signatures,
exports, technical impersonation, or every future permission.

For role-default governance, require **both** approved composite-profile eligibility
and the exact current management/delegation permission plus operation/target policy.
This prevents a misplaced direct Grant to a Normal Admin or ordinary role from
turning that account into a template administrator. Conversely, composite role
membership without effective authority, or with an overriding Deny, cannot mutate.
The gate belongs inside the locked mutation authorization boundary, not just the UI.

Do not infer profile authority from requested roles, user-supplied flags, cached
labels, Django flags, account creation origin or having the target business code.
An application Super Admin need not be framework staff or a Django Superuser.

### 3.3 C1/C2A reconciliation

| Historical proposal/contract | Revised treatment — PROPOSED |
| --- | --- |
| C1 separates School Admin and X; discourages X/business-role coassignment | Superseded as a target policy by reviewed `Admin` + governance and Instructor + Admin + governance composition. It was not an evaluator/database prohibition. Retain business conflict controls. |
| C1 X has eight defaults and no business defaults | May remain an additive governance starting point; not the complete Super Admin profile or a final grant list. Add approved Admin school duties by composition, not automatic access to every finance/student record. |
| C1 X has no delegation or protected provisioning defaults | Retain separate explicit approvals. Ordinary management codes do not establish authority for protected elevation or own-template edits. |
| C1 10 services / 82 codes / 96 bindings | Preserve historical manifest. Revised profiles, ordinary assignment, monitoring reads and scoped inspection need an approved new revision; final counts are undetermined. |
| B2 forbids reserved-role targets and governance-code changes | Keep this prohibition in the ordinary path. Add separately reviewed privileged services; no wildcard recipient or namespace exceptions. |
| B2 all-active-role recipient subset | Retain fail-closed legacy behavior until an exact per-permission/operation/role-combination successor is approved and tested. |
| C2A C1-only source and matrix checks | Preserve historical fidelity. Future planner needs reviewed location/provenance handling and explicit SRS revision/compatibility blockers; path repair is not requirements approval. |

## 4. Normal Admin, application Super Admin and Django Superuser

### 4.1 Responsibility boundaries — PROPOSED

| Responsibility | Normal Admin | Application Super Admin | Django Superuser |
| --- | --- | --- | --- |
| Registration review, school/academic/clearance administration, announcements | Exact school permissions + object/eligibility controls | Same approved school defaults through `Admin` | No automatic application authority |
| Assign approved ordinary extra roles | Explicit assignment permission and role/recipient allowlist | Same, with approved protected promotion path where needed | No automatic application authority |
| Edit global role defaults | No, including forged API calls/direct code grants without Super Admin profile | Exact governance permission, target scope and review; own/protected templates use separate controls | No automatic application authority |
| Direct overrides | Default no; only separately approved narrow delegation if adopted | Approved operation/code/recipient rules; never self-targeted ordinary writes | No automatic application authority |
| Authentication/security monitoring | Redacted school event view if explicitly granted and implemented | Approved governance/event scope; no secret/business-body dumps | Restricted technical event access only |
| Promote another Normal/Super Admin | No default Admin promotion; no Super Admin promotion | Separate protected, attributable workflows | Framework flag alone is insufficient |
| Django Admin maintenance | No by default | No by default | Only explicit reviewed framework allowlist; custom application evaluator remains binding |

### 4.2 Existing framework compatibility — Observed

`Account` extends `AbstractBaseUser`, maps `password` to `password_hash`, uses
`school_id` as `USERNAME_FIELD`, and has `REQUIRED_FIELDS=[]`. Its manager hashes
passwords and deliberately creates only Pending/inactive ordinary registrants.
`create_superuser()` raises `NotImplementedError` before saving anything.

`is_staff=False` and `is_superuser=False` are class attributes, not persisted
fields. `last_login=None` deliberately shadows the abstract field; the approved
ERD has none of these columns. Setting an attribute on an instance cannot provide
persistent framework provisioning. `Account.has_perm()` always delegates to the
custom evaluator for global checks and returns false for `obj`; module permission
checks return false. No `PermissionsMixin`, group/user-permission relations or
full stock permission-method surface is provided.

Settings enable Django auth/admin/session middleware and mount `/admin/`, but
application `admin.py` files have no model registrations. No custom
`AUTHENTICATION_BACKENDS` is configured; the framework default is ModelBackend.
Password authentication and request-status eligibility are not identical:
ModelBackend checks activity, not CTU-G's Approved status or assigned-role policy.
The registered route is not proof of working privileged administration.

Installed Django source shows AdminSite's default gate checks active/staff;
ModelAdmin uses model permission methods. PermissionsMixin adds a superuser field,
two many-to-many relations and unconditional active-superuser permission shortcuts.
ModelBackend's permission routines also use Django group/user permission relations
or its superuser permission set. These behaviors cannot be adopted as the custom
application authorization layer. Official documentation confirms the extension
points and optional mixin:
[custom authentication](https://docs.djangoproject.com/en/6.1/topics/auth/customizing/#custom-users-and-permissions),
[AdminSite permission gate](https://docs.djangoproject.com/en/6.1/ref/contrib/admin/#django.contrib.admin.AdminSite.has_permission).

### 4.3 Integration alternatives — PROPOSED, not implemented

| Integration | Schema impact | Security/compatibility assessment |
| --- | --- | --- |
| Explicit two-flag Account extension, no PermissionsMixin; restricted framework adapter | Add `is_staff` and `is_superuser`, both non-null false by default; reviewed new migration and ERD revision required | **Preferred.** Persistent framework privilege is independent of custom roles; application checks remain centralized. Requires custom AdminSite, reviewed ModelAdmin hooks and provisioning/authentication tests. |
| Full PermissionsMixin and conventional Django permissions | Superuser column plus user/group permission join tables; staff column separately; larger schema/integration change | Adds a second RBAC system and built-in bypass behavior. Would require explicit method/backend isolation and more regression coverage; not justified by a small restricted maintenance surface. |
| Derive flags from application roles/account Grants | Can avoid columns but changes meaning of application governance permissions | Couples framework privilege to school role/default edits and weakens separation. Not recommended. |
| External identity backend with independently authenticated framework claims | Could avoid Account flag columns, but introduces external identity, claim lifetime, mapping and recovery dependencies | A possible separately reviewed alternative if schema extension is rejected; no such infrastructure is evidenced. Do not claim it exists. |

**PROPOSED integration contract:**

1. Preserve `AUTH_USER_MODEL`, Account primary keys, password column and public
   registration semantics. Never swap to a second Django User model mid-project.
   Existing accounts receive false flags; no automatic flag backfill from Admin
   or governance roles. A `last_login` column is not essential to the selected
   integration; current Django signal registration skips a non-field attribute.
2. Implement restricted `create_superuser()` separately from ordinary registration
   only after approval: validate School ID/password, enforce true framework flags,
   create a verified Approved/active named operator and required identity/profile
   records under the technical provisioning contract. Do not call ordinary
   `create_user()` with forbidden extras, fabricate review attribution, assign
   application roles/grants, or pretend the manager authenticates an invoking CLI
   human. Command access, initial authorization and audit are separate controls.
3. Keep `Account.has_perm()` and `get_effective_permissions()` application-only.
   Do not add an `is_superuser` branch, fallback to permissive backends, Django
   group union, or cached stock `_perm_cache` to custom decisions. Any added sync,
   async or bulk application permission helpers must preserve the same semantics.
4. Use a dedicated restricted AdminSite and explicit framework authorization helper
   in reviewed ModelAdmin/view hooks. Its gate rereads framework flags and account
   eligibility and enforces technical access policy/step-up controls. A flagged,
   Approved, active operator may be roleless for framework maintenance; custom
   application evaluation still denies a roleless operator.
5. Keep the model allowlist empty until each maintenance function is reviewed;
   begin, if approved, with redacted technical read-only functions. Do not expose
   Account, profiles, roles, assignments, services, permissions, overrides, audit,
   finance or other confidential business models through generic CRUD, inline,
   autocomplete, history, raw-ID, export, bulk action or password-reset paths.
   Review Django's own auto-registered auth models too. Index hiding alone is
   insufficient: deny direct URLs and every add/change/delete/view/action hook.
6. Any future application security action exposed from a technical interface must
   call the same trusted service using the actual authenticated Account and the
   same application authorization/audit checks. Django ModelAdmin `save_model`,
   bulk update/delete and Django `LogEntry` are not replacements for B1/B2 audit.
   Technical flag changes require their own approved audit/recovery contract.
7. Customize eligibility checks for Approved/active state. Application login
   additionally requires its assigned-role eligibility; framework login requires
   framework eligibility. A Django Admin session reaching an application URL
   still passes through ordinary application permission/object checks. Do not use
   DRF `IsAdminUser` (installed implementation checks `is_staff`) or stock
   `DjangoModelPermissions` as the custom application authorization adapter.
8. Audit both framework provisioning/access and application governance under their
   separate contracts. No flags, plaintext credentials, reset/session tokens or
   privileged identity selectors may be accepted by public registration. Restrict
   credential recovery and revoke both relevant session surfaces when appropriate.

These adaptations deliberately constrain Django framework administration. If the
owner expects unrestricted stock Django model administration, that conflicts with
FR-DJA-02/04 and requires a requirements/security decision, not a silent bypass.
Deployment/DB/OS administrators remain a separate infrastructure trust boundary;
an application flag cannot technically constrain a person with raw database access.

## 5. Multi-role authorization design — PROPOSED

### 5.1 Existing calculation to retain

For a persisted default-database Account that is Approved/active, has at least one
active assigned role, and requests a permission in an active Service:

`Effective = (union(active role grants) ∪ active direct Grants) − active direct Denies`

`account_roles` has a unique account/role pair and can contain several different
roles. Requested role is not membership. The evaluator does not restrict roles
to Student/Instructor or impose the old X/business coassignment proposal.
Business actions still require object/assignment/period eligibility in addition
to an effective permission. An object-specific `Account.has_perm(code, obj)` call
currently fails closed; it is not an implemented object policy.

After commit, subsequent fresh evaluations see the changed defaults under the
normal READ COMMITTED workflow. Existing in-flight work/older snapshots are not
retroactively undone. Trusted writes must lock and recheck current authority;
future UI capability refresh and session invalidation are separate requirements.

### 5.2 Required combinations

| Composition | PROPOSED allowed responsibility | Mandatory contextual safeguards |
| --- | --- | --- |
| Student + Treasurer | Retain Student self-service and approved Treasurer operations | Resolve own records through Account → UserProfile → payment/exemption ownership. Deny conflicting own-payment receipt/collection, exemption and sign-off actions, or use an independently approved alternative actor. No duplicate identity or self-selected active-role switch. |
| Instructor + Admin | Teaching/assigned academic rights plus school administration | Do not approve oneself, appoint oneself to gain access, or change own assigned Instructor/Admin templates via ordinary mutations. Avoid arbitrary access to unrelated classes, assessment results or student finance detail. |
| Instructor + Admin + governance | Reviewed Super Admin composite with teaching duties | Same school/teaching limits plus protected governance controls. Holding three roles does not authorize self-grants, own-template editing, unrestricted data or Django flags. |
| Instructor + SSG Advisor | One monitoring responsibility in addition to teaching | Three read-only approved views, permitted period/data/redaction scope, appointment eligibility and independent revocation; no implied Treasurer, signatory, exemption, export or governance authority. |

Finance ERD ownership supports checks on `org_fee_payments.user_id` and linked
receipts; `received_by`, `issued_by` and `recorded_by` support operator attribution.
They do not prove independent approval. The expense schema does not encode every
beneficiary/conflict, and there is no approved refund/void workflow to expose.
Keep unrepresentable conflicts blocked or design a separately reviewed workflow.
Clearance signing must still resolve the actual appointment and deny ambiguous
Treasurer responsibility; multiple role holders are not a signing policy.

### 5.3 One SSG Advisor / Finance Monitor responsibility

**PROPOSED:** prefer `Instructor` + optional `SSG Advisor` because it makes
appointment, shared least-privilege defaults and revocation explicit. `Finance
Monitor` is a descriptive alias in documentation/UI, not a second persisted role.
Do not add either role in AR-2. Narrow individual overrides are a possible
exception after approval, but have weaker lifecycle clarity and no profile/expiry
binding in the current schema.

| Required ability | Existing C1 proposal | Reconciliation — PROPOSED |
| --- | --- | --- |
| View Financial Overview | `finance.summary.read` | Candidate only if its aggregate filters/redaction exactly meet the approved advisor scope. |
| View Financial Reports | `reports.financial.final.read` | Candidate for approved Final reports only; Draft detail, generation, finalization and export are not implied. Decide report maturity/content scope explicitly. |
| View Transaction History | `finance.ledger.read` / `finance.payments.read` are broader working/detail reads | Do not grant these by inference. Define a minimized history dataset and separately reviewed read permission/endpoint, including identifiers, periods, sensitive fields and export limits. |

The three views must be distinct authorizations under the same responsibility.
No automatic blanket Deny rows are needed for other users; least-privilege missing
grants suffice. If an Advisor independently also holds Treasurer, union can add
writes: “read-only Advisor role” does not make the entire account read-only. The
recommended default is no Advisor/Treasurer coappointment for the same monitoring
scope unless an approved conflict policy explicitly permits it. Direct Deny still
overrides grants from every role; role-context switching cannot evade it.

### 5.4 Finer recipient and lifecycle policy

B2's `permission_codes × role_names` scope is too coarse. For example, a finance
Treasurer-only scope rejects a Student+Treasurer account override; adding Student
would also make a Student-only target eligible for Treasurer codes. A reserved
Admin assignment blocks all ordinary account-override operations even if inactive.

**PROPOSED successor:** explicit rules per operation, service, permission and target
role/role-combination, with independent rules for role defaults and account
overrides. A finance operator override might require actual Treasurer eligibility,
allow Student as an additional role, reject Student-only, and route any reserved
administrator target to a protected workflow. Do not solve this by widening the
legacy list or ignoring an inconvenient target role. Recheck inside the owning
transaction and enforce business object scopes after global authorization.

Direct Grants are account-wide, not attached to the role that justified them.
Removing Treasurer can leave a finance Grant effective while Student remains.
Assignment/revocation must therefore review and revoke dependent overrides or
apply a separately approved continuing-eligibility check; never promise that role
removal removes every source. Instructor eligibility and Advisor appointment
removal need the same dependent-role/override analysis. No expiry or period-scoped
assignment columns exist: use a reviewed explicit revocation process initially,
or separately approve durable appointment/expiry storage.

## 6. Permission defaults, overrides and administrative governance — PROPOSED

### 6.1 Three distinct service boundaries

1. **School account/ordinary-role service:** Normal Admin with explicit authority
   may review another eligible registrant and assign/remove approved Student,
   Instructor, Treasurer or SSG Advisor roles only under approved recipient and
   prerequisite rules. The exact list is an owner decision, not every Role row.
   Never assign Admin/governance/framework flags through this path.
2. **Super Admin permission-management service:** effective composite-profile
   eligibility plus exact management/delegation authority permits approved
   ordinary role defaults and per-person exceptions. Normal Admin has no default
   override authority and can never use this service to edit global defaults.
3. **Protected governance service:** Admin promotion/removal, governance role/grant
   changes, protected templates, bootstrap/recovery and authorized own-role
   exceptions require independently approved workflows and last-operator checks.
   Existing B2 is deliberately not this service.

Existing B2 durable transactions cannot simply be nested in a new outer atomic
workflow. A future refactor must share safe locking/validation primitives while
giving each complete operation one owned transaction and in-transaction profile/
approval checks. An unlocked façade check before calling B2 creates a TOCTOU gap.

### 6.2 Assignment/provisioning decision rules

| Operation | Authorized path — PROPOSED | Required checks / audit |
| --- | --- | --- |
| First application Super Admin | Restricted owner-authorized bootstrap ceremony | Real named human, independent attribution/attestation, minimal approved catalogue/profile, first-init serialization and recovery plan; see §9. |
| Another Super Admin | Separate protected elevation | Effective authorized Super Admin requester plus independent approval; exact target and minimal profile delta; no self-promotion or ordinary assignment shortcut. |
| Normal Admin assignment/removal | Super Admin protected promotion/revocation | Eligible identity, no self-targeting, approved Admin duties, no implicit governance role; assess loss of effective Super Admin if target also holds governance. |
| Student → Student + Treasurer | Authorized school assignment within explicit allowlist | Preserve Student membership, validate finance appointment/conflicts, deny self-assignment, audit new assignment and attribution. |
| Instructor → Instructor + Admin | Super Admin protected promotion | Preserve Instructor role; assess self-interest and role/default edit restrictions. Normal Admin cannot freely create more Normal Admins. |
| Instructor → Instructor + SSG Advisor | Authorized school assignment if approved | Same one responsibility; approved read-only defaults/period/expiry policy; no Treasurer write bundle. |
| Default permission change | Super Admin ordinary or protected template path | Exact role/code delta, effect preview, code/recipient scope, actor-assigned-role check, last-operator invariant, same-transaction audit. |
| Individual Grant/Deny/deactivation | Approved operation-specific override path | Target eligibility, protected/admin routing, actual actor, no self-targeting, code scope; removing Deny is privilege-increasing. |
| Unavailable administrator recovery | Separate independently authorized recovery | Verify identity and evidence; bound access, restore effective governance without disabling Deny globally or removing audit; rotate/revoke relevant sessions. |

### 6.3 Role-default impact and self-interest

Role-default changes update `role_permissions`, not one copied override per role
holder. Preview exact enable/disable changes, affected eligible account counts,
other assigned-role grants, direct Grant/Deny interactions and service states.
Commit only the reviewed delta after rereading those authorization dependencies.
Removing a role grant does not guarantee effective denial when another role or
direct Grant contributes it. Removing Deny may expose several existing sources.

**PROPOSED:** preserve B2's prohibition on editing *any* role assigned to the
acting administrator, including inactive assignments for this guard. Do not
detach/rename/reassign roles, select another UI role, or use a second School ID
to bypass it. An Instructor+Super Admin cannot routinely edit Instructor defaults;
an independently authorized administrator without that role can do an otherwise
approved ordinary change.

Every proposed Super Admin holds Admin and governance, so a second Super Admin
does **not** by itself resolve shared-role self-benefit for those templates.
Changes to these shared assigned/protected roles remain blocked until the owner
approves a separate independent-review exception: exact immutable delta, current
state binding, distinct requester/approver/executor identities where required,
institutional review for shared-benefit changes, expiry/replay protection and
transactional evidence. Additional human approval without durable evidence or
same-state execution is not an implemented safeguard. This may require a new
approval-event/storage contract (§7); no general `allow_self=True` switch is proposed.

### 6.4 Effective-last-Super-Admin invariant

**PROPOSED:** define a reviewed minimum governance capability set and compute
eligible operators from Approved/active Accounts, both active composite roles,
active Services, effective grants after Deny and the required action/target
policies. A role name or count of governance assignments is insufficient.

Every change that can remove the final effective operator must share a common
serialization protocol and deny unless an approved recovery transition preserves
governance. This includes account suspension/rejection, assignment deletion, role
deactivation, default revocation, direct Deny, override deactivation, permission/
service changes and relevant policy/configuration changes. Test simultaneous
demotions/revocations, not just sequential role removal. An incomplete governance
bundle, disabled Service, or active Deny cannot count as an effective operator.

Reuse a reviewed common governance lock only once its row exists; bootstrap
cannot lock a nonexistent Service as though the B2 mutex were installed. The
definition and lock order are approval dependencies, not current guarantees.
Availability of an actual human/credential is an operational concern too: keep
independent recovery, not just a database count of nominal operators.

## 7. Database compatibility assessment

| Requirement | Current representation | Implementation / schema consequence — PROPOSED |
| --- | --- | --- |
| Two Admin defaults and multi-role combinations | `roles`, `account_roles`, `role_permissions` | No schema change required for composition; new role data requires separately approved initialization. |
| Shared defaults / individual Grant and Deny | `role_permissions` active flag; unique account/permission override with effect/active flag | No schema change to preserve union/Deny semantics; new management policy/services needed. Only one current override per account/code, not several concurrent exception records. |
| Role assignment/removal | Unique account/role, assigned_by/time | Supports current membership and attribution. No assignment active flag: authorized removal deletes the link, with before/after audit in the same transaction; reappointment is separately audited. No existing service implements it. |
| Scoped delegation and conflict predicates | Server policy plus existing records | Finer predicates can be implemented without new columns, but exact rules require approval/tests. No per-grant object scope or operation metadata exists. |
| Bounded assignment/grant mutation audit | `access_audit_logs`, required actor FK, approved B1 state allowlist | Existing ID/flag/effect snapshots reusable. Audit does not authenticate/authorize the actor or itself implement review. |
| Independent approvals, immutable reviewed deltas, expiry/replay | Not encoded in seven access-control tables | Approve a durable workflow/evidence store with verification/retention, or separately reviewed new tables/fields. Free text in reason/action is not a substitute. |
| Named first operator and full initialization metadata | Accounts/profile + required audit actor; no first-init workflow | Real identity can use existing tables, but first authorization, serialization and metadata audit/attestation contracts are missing. No invented actor or FK nullability bypass. |
| Django framework privilege | No persisted staff/superuser fields | Preferred two-column Account change requires separate ERD/migration authorization. Existing primary keys and custom RBAC tables need not change. |
| PermissionsMixin alternative | No Account groups/user_permissions relations | Adds join tables and superuser field, plus staff separately. Existing Django auth tables are not Account-to-group/permission joins; their existence does not make the mixin schema-free. |
| Login/session event history | B1 authorization-mutation logs only | No approved comprehensive event store/retention source. Failed anonymous login cannot supply a required Account actor. Approve separate storage/schema or external event pipeline. |
| Advisor/role appointment duration | No assignment expiry or period fields | Manual independently audited revocation is representable; enforceable automatic duration needs additional approved workflow/storage. |
| Per-permission readiness/activation | Permission has no active/readiness field; Service has broad flag | Metadata tags do not gate a live feature. Keep unimplemented endpoints unavailable and activation separate. |
| Object ownership and financial self-interest | Some payment/profile/appointment references exist | Business validators needed; no generic row-policy engine, expense beneficiary or report-finalizer history is implied by the schema. |

Neither approved ERD is changed. The main ERD's 42 application tables are broader
than the historically instantiated 16 database tables; planned tables are not
implemented capabilities. No migration list/database snapshot was refreshed here.

## 8. Existing implementation impact and test plan

### 8.1 Reuse versus modification

| Component | Reuse unchanged | Necessary future work — PROPOSED |
| --- | --- | --- |
| `access_control/services.py` | Fresh fail-closed union/Deny evaluator, strict code matching, role/service/account eligibility | Keep unchanged for global application evaluation; add contextual business authorization around it. No framework bypass. |
| `Account.has_perm()` | Application evaluator delegation and object-deny default | Preserve semantics through any framework integration; do not inherit active-superuser shortcuts. |
| Public registration service/views/serializers | Anonymous CSRF, strict Student/Instructor inputs, atomic Pending/inactive profile creation, no grants | No privilege-field expansion. Add separate approval/provisioning/login modules, not a registration backdoor. |
| Existing RBAC models/constraints | Multiple memberships, unique grants/overrides, native timestamps, protected references | Current schema supports most application composition. Framework flags/approval/event stores are separate change requests. |
| `audit.py` | Current bounded snapshots, real persisted actor check, rollback semantics | New role-assignment actions can use approved ID snapshots after review. Framework flags, initialization metadata, approval evidence and anonymous authentication events need explicit contracts; do not pass unsupported JSON keys. |
| `delegation.py` / `mutations.py` | Deny-by-default principles, reserved/self protections, locked rereads, durable commit/audit patterns | Need reviewed Super Admin-only authority gate, finer recipient/operation policy and separate protected workflows. Not complete unchanged SRS v0.3 services. Never remove protections wholesale or nest durable calls incorrectly. |
| `init_system_roles` | Existing four-role preservation and strict naming behavior | Do not extend/invoke it as a bootstrap shortcut. Additional roles require reviewed manifest and provisioning approval. |
| Catalogue manifest/validator/planner | Historical C1 fidelity, read-only comparison and collation checks | Resolve stale path by approved provenance change; retain v1, design a reviewed new manifest and SRS compatibility blockers. No implicit grant application. |
| Settings, URLs, empty application admin registrations | Keep current state during review | Later custom backend/form/AdminSite and reviewed framework allowlist; production security/session configuration in its own phase. |

### 8.2 Existing tests to retain or revise deliberately

- Keep evaluator tests for role union, Deny overriding multiple sources, no Admin
  or Technical Super Admin name bypass, roleless/direct-Grant denial, immediate
  reevaluation, strict codes, failure handling and object/module denial. Add
  required named combinations rather than replacing negative cases.
- Keep B2 tests `test_any_role_currently_assigned_to_actor_is_protected`,
  `test_reserved_administrative_roles_cannot_be_mutated`,
  `test_accounts_with_reserved_roles_are_protected_even_if_that_role_is_inactive`,
  governance-code protection and self-override denial **for the ordinary API**.
  New protected services need different explicitly approved positive tests; do
  not flip these tests to permit ordinary reserved mutations.
- `test_unreviewed_extra_active_target_role_blocks_override` remains correct for
  legacy B2. A successor policy needs exact reviewed-combination positives plus
  unexpected-role/Student-only negatives. Generic positive manager fixtures need
  revision if the corresponding entry service adds composite-profile eligibility;
  non-Super-Admin managers must not retain accidental default-edit authority.
- `test_superuser_provisioning_fails_without_saving` remains correct until the
  framework design, migrations and provisioning contract are separately approved.
  Only then replace it with controlled successful provisioning plus unauthorized/
  wrong-flags/audit-failure negatives. Ordinary `create_user()` restriction tests
  and public registration privilege-injection tests remain unchanged.
- C1 catalogue tests remain historical-version tests. Under authorized path work,
  update provenance references explicitly and add new-version tests; do not remove
  source digest or matrix checks to make failures disappear. The old “Technical
  role has no business defaults” test can still hold for the additive governance
  role; it is not a ban on the approved composite profile's school permissions.

### 8.3 Required new security coverage — PROPOSED

1. All required role unions and Deny combinations; role/default removal with other
   contributing grants; post-commit checks on the same Account object; no copied
   per-user defaults; snapshot/session/menu refresh boundaries.
2. Normal Admin forged role-template API denial, even with an incorrectly supplied
   direct management Grant; composite Super Admin without effective code/scope
   denied; revoked authority and changed approval state rechecked under locks.
3. Ordinary assignment eligibility and preserved base roles; no self-appointment,
   Admin/governance promotion through ordinary paths, temporary role-detachment
   workaround, or restricted public registration. Audit failure rolls back every
   approval/assignment/state change.
4. Student+Treasurer own collection/receipt/exemption/signature conflicts, other
   eligible records positive cases, and dependent override leakage after Treasurer
   removal. Teacher appointments and Advisor revocation need equivalent lifecycle
   tests; no fake active-role switch may bypass ownership or Deny.
5. One Advisor responsibility with exactly three approved reads; history field/
   period filtering, cross-user/minimization tests, writes/exports denied, and
   Advisor/Treasurer overlap handled by the approved conflict policy.
6. Own/assigned/protected template changes, distinct bound approvals, tampered/
   expired/replayed review, independent shared-role review and safe idempotency.
   Concurrent last-operator demotions, Denies, default revocations, role/service
   deactivation and account suspension must not all succeed.
7. Framework flags persisted only through the authorized path; flags and Django
   groups confer no custom authority; a roleless framework Superuser remains
   denied by application APIs. Add sync/async/bulk-check negatives where used.
8. Restricted Admin direct URLs, hidden models, relation widgets, actions, imports,
   bulk writes, password/flag edits and audit tampering refused. Any permitted
   application operation uses actual actor/service audit; Django LogEntry alone
   does not satisfy the test. Stock staff-only DRF authorization is disallowed.
9. Approved/active checks on both login surfaces; revoked flags/roles/overrides and
   stale sessions; rate limits, CSRF and authentication-log privacy, including
   failures with no known Account and no fake actor.
10. Read-only planners, revised manifest compatibility, missing source/digests,
    MySQL collation, unknown/inactive records, conflict preservation and no DML/DDL.

Use the existing guarded disposable MySQL runner for future writing tests. None
of these tests was generated or run as part of this documentation-only review.

## 9. Security risks, safeguards and bootstrap blockers — PROPOSED

### 9.1 First real application operator

The historically empty catalogue/accounts state means there is no authenticated
application Super Admin, no established governance mutex and no prior actor for
the first security mutation. B1 requires a real persisted Account actor and
validates attribution, not bootstrap authority. Django Superuser creation does
not itself solve this problem or confer application authority.

**PROPOSED:** a separately approved one-time institutional ceremony identifies the
actual named human, verifies credentials/identity and independent approval,
records a signed minimal manifest/delta and recovery/checkpoint plan, and uses
an explicitly designed first-init serialization mechanism. The exact selected
mechanism must work before the Service mutex exists and prevent concurrent or
replayed ceremonies. Do not authorize the ceremony using permissions it would
grant to itself.

If the chosen approved ceremony persists the actual operator and minimal authority
in one transaction, subsequent audit FKs may reference that newly persisted human.
Self-attribution of initial events is valid only under the separately approved
external authorization/independent attestation and event contract, not merely
because the FK can be satisfied. No fake system account, borrowed ID, null actor,
CLI `--actor-id` as authentication, hidden audit omission or default-all-permissions
seed is acceptable. Full metadata/approval evidence cannot be squeezed into B1's
current allowed snapshots or reason strings. Approve durable evidence first.

Initial Django framework provisioning is its own technical ceremony and log/
recovery contract. The same verified person could participate in both only with
explicitly separate authority and attribution decisions; there is no automatic
promotion between the two privilege systems.

### 9.2 Core risk register

| Risk | Safeguard / remaining blocker — PROPOSED |
| --- | --- |
| Normal Admin becomes global template editor through another grant | Composite-profile eligibility plus effective permission and exact delegation inside trusted transaction; protected governance grant control. |
| Super Admin gains private school/finance records by title | No evaluator bypass; least-privilege defaults; ownership, class, period, signatory and disclosure checks on every backend path. |
| Role-default self-escalation or shared-Admin self-benefit | Preserve ordinary assigned-role prohibition; independently approved exact-delta protected exception or remain blocked. |
| Scope widening admits Student-only finance operators | Per-permission/operation/composite recipient predicates; do not broaden Cartesian products. |
| Advisor becomes a writer through another role/direct Grant | Explicit coexistence policy and lifecycle checks; display total effective rights, not a misleading read-only profile label. |
| Last nominal operator is ineffective or concurrent revocations win | Evaluate full effective governance bundle after proposed delta under shared serialization across all contributing state changes; independently tested recovery. |
| Django Admin bypasses business audit/authorization | Independent framework boundary, no generic protected-model CRUD, trusted service calls with real application authorization, separate framework event audit. |
| Authentication logs expose secrets or fabricate actors | Dedicated reviewed event contract/storage; unknown failed-login subjects remain non-actor events; redact sensitive identity/request content and define retention. |
| Audit FK/JSON constraints bypassed during bootstrap | Real human, independent external authorization, approved first-init event contract; no schema/payload hacks. |
| Stale C1 or renamed documentation treated as current policy | Preserve source hashes, explicit revision/path handling, SRS compatibility gate, no implicit apply mode. |

## 10. Decisions requiring project-owner approval

All decisions in this table are **PROPOSED / OPEN**, unless the row explicitly
identifies terminology already clarified by the user. No implementation approval
is recorded by AR-2.

| AR-2 decision | SRS decisions / C1 reconciliation | Approval needed |
| --- | --- | --- |
| AR2-01 Composition and naming | OD-01/12; C1 D04/D06 | Adopt Admin + governance; retain or explicitly rename `Technical Super Admin`; permit reviewed Instructor composition. |
| AR2-02 School responsibilities | OD-03/06; C1 D03/D06 | Exact ordinary role allowlist, Admin promotion boundary, appointment eligibility and conflicts. |
| AR2-03 One Advisor responsibility | OD-04/05; C1 D01/D12/D16 | **One responsibility is clarified**, not open for splitting. Approve optional `SSG Advisor` role versus narrow exceptions, three view datasets and appointment duration; approve no additional duties by implication. |
| AR2-04 Default/override governance | OD-08/11; C1 D05/D07/D08 | Exclusive Super Admin template authority, fine recipient/operation rules, optional narrow Normal Admin overrides, protected-target boundaries. |
| AR2-05 Assigned-role exceptions | OD-02/08; C1 D06/D07/D08 | Independent review for shared Admin/governance template changes, who can approve/execute and how exact deltas/evidence are bound. Ordinary prohibition remains. |
| AR2-06 Effective last operator | OD-02/09; C1 D08 | Minimum effective capability bundle, common lock protocol, concurrent-change coverage and independent recovery. |
| AR2-07 First human/initialization attribution | OD-09; C1 D09/D10/D18 | Real identity, external authority, attestation, first-init serialization, audit payload and checkpoint/replay/recovery procedure. |
| AR2-08 Django integration and schema | OD-10; C1 D08/D10 | Preferred two-field extension versus alternative, reviewed ERD/migration/rollback plan, restricted AdminSite surface and flag provisioning/recovery. |
| AR2-09 Approval/event storage | OD-02/07/09/14; C1 D07/D10 | Durable approval evidence and auth/framework event storage, retention and access; any required schema changes. |
| AR2-10 Session lifecycle | OD-13; C1 D11 | Application/framework session invalidation timing, privileged step-up and behavior for security-critical updates. |
| AR2-11 Revised manifest and references | OD-12; C1 D01/D02/D04/D18 | Canonical requirements/report locations, preserved v1 provenance, new catalogue/profile revision, future metadata/grant/activation gates. |
| AR2-12 Business/privacy/operations | OD-05/06/14; C1 D12–D17 | Financial self-interest, signature resolution, rating/message/report/publication policy, monitoring disclosure and operational recovery targets. |

C1 D01–D18 are not collectively resolved by the new SRS: D04/D06 need deliberate
administrator-policy revision, while attribution, audit, session and business
decisions continue to gate their corresponding features. The two-profile and
multi-role intended use cases are requirements; their concrete grant sets,
exceptions, schema and execution mechanisms remain proposed designs.

## 11. Recommended implementation sequence — PROPOSED

1. **AR-3A: focused read-only contract specification.** Obtain owner decisions on
   composition/name, assignment tiers, default/override boundaries, shared-role
   approval and effective-last-operator semantics. Specify exact service contracts,
   lock order, delta/approval evidence and acceptance tests; no bootstrap or writes.
2. **AR-3B: separately approved provenance/catalogue reconciliation.** Resolve
   requirements/report source paths without weakening hashes; preserve C1 v1 as
   historical. Prepare a reviewed new manifest with one Advisor profile, actual
   monitoring/assignment/governance intents and SRS compatibility markers. Extend
   only read-only validation/planning/tests first, in an explicitly authorized task.
3. **AR-3C: dedicated framework schema/integration design.** Review exact two-flag
   Account migration or chosen alternative, all false existing-account backfill,
   restricted AdminSite/backend/form/provisioning/audit changes, rollback and
   negatives. Authorize model/ERD/migration work separately before executing any.
4. **AR-4: implement trusted application governance/assignment services in isolation.**
   Add fine recipient policy, protected promotions, exact approved-template changes,
   approval evidence, effective-last-operator locking, audit and lifecycle cleanup.
   Retain legacy B2 negative guarantees. Test only in fresh disposable MySQL; keep
   live mutations and initialization gated.
5. **AR-5: separately approved initial operator and minimal catalogue ceremony.**
   Requires accepted identity/attribution/audit/serialization/recovery contracts
   and reviewed manifest. Metadata, explicit grants, service activation and Django
   framework privilege provisioning remain separate gated operations.
6. **AR-6: approval, authentication/events and permission-aware interfaces.**
   Add atomic school approval, secure sessions, event monitoring and revocation,
   current-user capabilities, then shared dashboard/admin interfaces. Implement
   business views only with their object/privacy/conflict tests and approved scope.

Do not combine these stages into “createsuperuser and seed everything.” Each
implementation prompt must state its exact authorization and stop boundary.

## 12. Exact handoff for the next Codex prompt

**PROPOSED next phase: AR-3A, documentation-only governance contract definition.**
The following prompt is ready to use after the owner reviews AR-2. It does not
record owner approval of an option merely by being present in this document.

> Continue CTU-G Workspace with Phase AR-3A: Protected Administrator Governance
> Contract Specification. Read `docs/architecture/AR-2-revised-administrator-access-control.md`
> and the v0.3 content at `docs/SRS/CTU-G_Workspace_SRS_v1.md`. Obtain the actual
> recorded owner decisions for AR2-01 through AR2-12; any missing decision stays
> explicitly PROPOSED/OPEN rather than being inferred. Inspect only relevant
> accounts/access-control/config sources and approved DBML. Preserve all existing
> tracked/untracked/deleted work.
>
> Create one new document at
> `docs/architecture/AR-3A-protected-administrator-governance-contracts.md`.
> Specify Normal Admin and composed Super Admin eligibility; ordinary role-assignment
> versus protected Admin/governance promotion contracts; per-operation/per-permission
> recipient-combination rules; self/assigned-role restrictions and independently
> approved shared-role exceptions; the exact effective-last-operator predicate and
> shared lock/commit protocol; durable review-delta binding, expiry/replay and audit
> evidence requirements; Student+Treasurer and Instructor+SSG Advisor lifecycle/
> object-scope constraints; and the first real human bootstrap/attribution decision
> gates. State exactly which parts current tables/B1/B2 can represent and which
> require separate approval storage/schema/contracts. Include precise API/service
> input/output/denial/no-op semantics and disposable-MySQL acceptance scenarios,
> without claiming any code is implemented.
>
> Reconcile the known relocated C1 source and historical manifest as a documented
> follow-up blocker only; do not repair paths or alter v1. Keep Django Superuser's
> proposed flag migration and restricted AdminSite integration in a separate
> explicit change request. Do not modify code, frontend, models, migrations, ERDs,
> existing documents, settings or database records; do not initialize roles,
> catalogue or grants, provision any administrator, enable live mutations, invoke
> createsuperuser, run the full suite, commit or push. Save the new contract
> document, report open decisions and the next bounded implementation handoff,
> then stop.

### Review verification and preservation

AR-2 created only this document. Static file comparisons cover the 211
pre-existing tracked/untracked paths and recorded deletions. Both read-only ERDs
retain their approved SHA-256 values:

- `full_schema.dbml`:
  `E9235A87555FFCD50ECB6AB6C1A45F9C7C54E344FF8F269ECC890579F633E4B2`.
- `schema.dbml`:
  `F050F7B910038532CA8E73B283F16A57DEDD6B738FDC74D293E64D539A4AFAC4`.

The SRS and original C1 content hashes above are recorded for traceability. Live
database state, test success, approval decisions and schema changes are not
asserted as newly verified or authorized by this architecture review.
