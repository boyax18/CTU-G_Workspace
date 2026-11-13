# AR-3B2A — Permission Catalogue v2 Reconciliation Proposal

Date: 7 November 2026, Asia/Manila.
**Status: PROPOSED candidate v2.0-review-1 — owner approval required.**

Every catalogue change, retirement, metadata revision, role definition, scope and
default grant in this document is **PROPOSED**. User-stated architecture requirements
are preserved, but preparing this document does not approve any privilege or write.
Only this new document is created. No runtime manifest, source, model, migration,
ERD, database record, frontend or existing document is changed.

## 1. Executive summary

The exact candidate is **95 permission definitions across the existing 10 services**,
**six role definitions** and **106 explicit proposed role-permission bindings**.
The change ledger contains one additional retired historical identifier, retained
as a tombstone rather than a selectable v2 permission definition. These numbers
were derived and statically validated before publication:

`82 C1 definitions − 1 retired definition + 14 new definitions = 95`

The 81 carried definitions comprise 79 metadata-identical retentions and two
explicit metadata revisions. The 96 existing proposed binding pairs are preserved;
10 new proposed pairs are added: five Admin, two governance-role and three Advisor.
No default pair uses the retired code, a blocked permission or a delegation code.

Normal Admin remains `Admin`. Application Super Admin is the composition of Admin
and a protected governance role, provisionally named `Technical Super Admin`.
Django Superuser remains independent and supplies no custom application bypass.
Student+Treasurer, Instructor+Admin and Instructor+SSG Advisor retain one identity
and combine eligible rights, with individual Deny overriding every positive source.
SSG Advisor and Finance Monitor are one responsibility, not two roles.

The candidate retains all 14 AR-3A additions as distinct, narrowly specified
capabilities; §2.4 records their requirement basis, overlaps and unresolved design
choices. This is an exact review candidate, not a claim that all additions are
mandatory or approved. If an owner decision merges/removes a candidate or changes
defaults, revise and revalidate this document's totals before manifest approval.

### Evidence and provenance

| Source | Actual inspected reference / SHA-256 |
| --- | --- |
| SRS v0.3 | [docs/SRS/CTU-G_Workspace_SRS_v1.md](../SRS/CTU-G_Workspace_SRS_v1.md); content identifies v0.3. `AF4EAD4F88BDB0877AB6C3B8965BEC5CAF0F058D74AB0D878EC690379210346F`. Requested v0.3 Markdown filename is absent; no rename is performed. |
| AR-2 | [Administrator architecture](AR-2-revised-administrator-access-control.md); `B36C0DAC6D18BADC435CCE242725D2D6424DB9D7E12D6D4943F20C7EAAF8CE36`. |
| AR-3A | [Finalization plan](AR-3A-administrator-architecture-finalization.md); `464C0FEC172EF5BA887DBC22EC5B09C3396CA1BE53087D999BBF763966EDDED1`. |
| C1 original | [Restored proposal](../implementation/access-control/phase1h-c1-permission-catalogue-governance-proposal.md); `02EB308DB5AFF1491EA2D024F5F7F1074125E3A7B9BB02DBD1409F6A6170A99E`. |
| C1 v1 JSON after AR-3B1 | [c1_v1.json](../../backend/apps/access_control/catalogue/c1_v1.json); complete file SHA-256 `86D72D82295CB358244145C6D24EBE8BA948F5211DE298EBF897B5D3D83ED447`. Its source digest remains the C1 digest above. |

AR-3B1's canonical source path is present in both manifest and validator and the
source bytes match the pinned digest. The old path defect is repaired; it is not
an open blocker here. No reconstructed report replaces the original C1 source.
The SRS's adjacent DOCX is not treated as independently verified identical content.
Historical 61 catalogue tests / earlier 286 backend tests and live database counts
are prior evidence only; no Django tests, database connections or framework setup
were run during this documentation/static-validation phase.

## 2. Exact C1-to-v2 permission delta

### 2.1 Deterministic construction and interpretation

For a future separately approved v2 manifest:

1. Copy the 10 service definitions and five existing C1 role definitions verbatim
   from the pinned C1 JSON. Add only the optional Advisor role in §3.
2. For every C1 permission, apply the explicit disposition in §2.2. KEEP copies
   service, code, name, module, action, description and F/P/B state unchanged.
   REVISE changes only the exact name/description fields in §2.3. RETIRE excludes
   the permission from v2 selectable definitions and adds the retirement tombstone.
3. Add exactly the 14 complete definitions in §2.4, copied from AR-3A's table.
4. The per-code role-key cells in §2.2 and §2.4 define all 106 default pairs.
   A dash means no grant, not a Deny. There is no wildcard, inheritance or Django
   group grant. §3's count matrix is a cross-check, not an additional grant source.
5. Scope/protection, lifecycle, eligibility, policy references and readiness remain
   manifest metadata. They are not new Permission/Role database fields and do not
   implement object checks or activation.

Keys: S=Student, I=Instructor, T=Treasurer, A=Admin, G=Technical Super Admin
(protected governance role), V=SSG Advisor. Every role-key cell is **PROPOSED**.
Protection `GOV` means ordinary B2 cannot change this permission's grants; it does
not mean only a governance user can use it. `ORD` means not namespace-protected
by current B2, but management and object policies still apply.

F references an existing internal contract/family, not a working v2 governance API;
P is planned; B is blocked with no default grants. RET is the retired tombstone,
outside the 95 candidate definitions. Scope identifiers are defined in §4.3.

### 2.2 Complete C1 inventory and dispositions — PROPOSED

| Service | C1 permission code | Disposition | v2 state | Proposed defaults | Protection | Scope |
| --- | --- | --- | --- | --- | --- | --- |
| accounts | accounts.profile.self.read | KEEP | P | S,I,T,A,G | GOV | OWN |
| accounts | accounts.profile.self.update | KEEP | P | S,I,T,A,G | GOV | OWN |
| accounts | accounts.registration_requests.read | KEEP | P | A | GOV | SCHOOL |
| accounts | accounts.registration_requests.approve | KEEP | P | A | GOV | SCHOOL |
| accounts | accounts.registration_requests.reject | KEEP | P | A | GOV | SCHOOL |
| accounts | accounts.school_accounts.suspend | KEEP | P | A | GOV | SCHOOL |
| accounts | accounts.school_accounts.activate | KEEP | P | A | GOV | SCHOOL |
| accounts | accounts.school_accounts.provision | KEEP | B | - | GOV | SCHOOL |
| accounts | accounts.school_accounts.recover | KEEP | B | - | GOV | SCHOOL |
| access_control | access_control.catalogue.read | KEEP | P | G | GOV | GOV |
| access_control | access_control.role_permissions.manage | KEEP | F | G | GOV | GOV |
| access_control | access_control.account_permissions.manage | KEEP | F | G | GOV | GOV |
| access_control | access_control.effective_permissions.inspect | KEEP | P | G | GOV | GOV |
| access_control | access_control.audit.read | KEEP | P | G | GOV | GOV |
| access_control | access_control.diagnostics.read | KEEP | P | G | GOV | GOV |
| access_control | access_control.catalogue.initialize | KEEP | B | - | GOV | GOV |
| access_control | access_control.services.activation.manage | KEEP | B | - | GOV | GOV |
| access_control | access_control.role_assignments.manage | RETIRE | RET | - | GOV | GOV |
| access_control | access_control.governance_grants.manage | KEEP | B | - | GOV | GOV |
| access_control | access_control.technical_accounts.provision | REVISE | B | - | GOV | GOV |
| access_control | access_control.technical_accounts.recover | REVISE | B | - | GOV | GOV |
| access_control | access_control.delegate.academic | KEEP | F | - | GOV | GOV |
| access_control | access_control.delegate.finance | KEEP | F | - | GOV | GOV |
| access_control | access_control.delegate.clearance | KEEP | F | - | GOV | GOV |
| access_control | access_control.delegate.group_rating | KEEP | F | - | GOV | GOV |
| access_control | access_control.delegate.announcements | KEEP | F | - | GOV | GOV |
| access_control | access_control.delegate.notifications | KEEP | F | - | GOV | GOV |
| access_control | access_control.delegate.reports | KEEP | F | - | GOV | GOV |
| academic | academic.catalogue.read | KEEP | P | S,I,T,A | ORD | CATALOG |
| academic | academic.profile.self.read | KEEP | P | S | ORD | OWN |
| academic | academic.advisees.read | KEEP | P | I | ORD | ASSIGNED |
| academic | academic.courses.manage | KEEP | P | A | ORD | SCHOOL |
| academic | academic.periods.manage | KEEP | P | A | ORD | SCHOOL |
| academic | academic.sections.manage | KEEP | P | A | ORD | SCHOOL |
| academic | academic.profiles.manage | KEEP | P | A | ORD | SCHOOL |
| academic | academic.advisers.manage | KEEP | P | A | ORD | SCHOOL |
| finance | finance.fee_schedule.read | KEEP | P | S,T,A | ORD | CATALOG |
| finance | finance.fee_schedule.manage | KEEP | P | T | ORD | FINANCE |
| finance | finance.payments.self.read | KEEP | P | S | ORD | OWN |
| finance | finance.payments.read | KEEP | P | T | ORD | FINANCE |
| finance | finance.payments.record | KEEP | P | T | ORD | FINANCE |
| finance | finance.receipts.self.read | KEEP | P | S | ORD | OWN |
| finance | finance.receipts.issue | KEEP | P | T | ORD | FINANCE |
| finance | finance.funds.record | KEEP | P | T | ORD | FINANCE |
| finance | finance.expenses.record | KEEP | P | T | ORD | FINANCE |
| finance | finance.expense_images.attach | KEEP | P | T | ORD | FINANCE |
| finance | finance.ledger.read | KEEP | P | T | ORD | FINANCE |
| finance | finance.summary.read | KEEP | P | T,A | ORD | AGG |
| finance | finance.exemptions.manage | KEEP | P | A | ORD | FINANCE |
| clearance | clearance.subjects.manage | KEEP | P | A | ORD | SCHOOL |
| clearance | clearance.teaching_assignments.manage | KEEP | P | A | ORD | SCHOOL |
| clearance | clearance.signatories.manage | KEEP | P | A | ORD | SCHOOL |
| clearance | clearance.assignments.self.read | KEEP | P | I,T,A | ORD | ASSIGNED |
| clearance | clearance.requests.self.read | KEEP | P | S | ORD | OWN |
| clearance | clearance.requests.self.submit | KEEP | P | S | ORD | OWN |
| clearance | clearance.requests.assigned.read | KEEP | P | I,T,A | ORD | ASSIGNED |
| clearance | clearance.subject_requests.sign | KEEP | P | I | ORD | SIGN |
| clearance | clearance.organization_requests.sign | KEEP | P | I,T,A | ORD | SIGN |
| clearance | clearance.signatures.self.manage | KEEP | P | I,T,A | ORD | SIGN |
| clearance | clearance.messages.self.read | KEEP | P | S | ORD | OWN |
| clearance | clearance.messages.send | KEEP | B | - | ORD | ROUTED |
| clearance | clearance.progress.read | KEEP | P | A | ORD | SCHOOL |
| group_rating | group_rating.sheets.assigned.read | KEEP | P | I | ORD | CLASS |
| group_rating | group_rating.sheets.manage | KEEP | P | I | ORD | CLASS |
| group_rating | group_rating.criteria.manage | KEEP | P | I | ORD | CLASS |
| group_rating | group_rating.invitations.manage | KEEP | P | I | ORD | CLASS |
| group_rating | group_rating.invitations.self.respond | KEEP | P | S | ORD | OWN |
| group_rating | group_rating.groups.manage | KEEP | P | S | ORD | GROUP |
| group_rating | group_rating.members.manage | KEEP | P | S | ORD | GROUP |
| group_rating | group_rating.submissions.self.manage | KEEP | P | S | ORD | GROUP |
| group_rating | group_rating.results.self.read | KEEP | P | S | ORD | OWN |
| group_rating | group_rating.results.assigned.read | KEEP | P | I | ORD | CLASS |
| announcements | announcements.read | KEEP | P | S,I,T,A | ORD | ANNOUNCE |
| announcements | announcements.create | KEEP | P | A | ORD | ANNOUNCE |
| announcements | announcements.update | KEEP | P | A | ORD | ANNOUNCE |
| notifications | notifications.read_state.self.read | KEEP | P | S,I,T,A | ORD | OWN |
| notifications | notifications.read_state.self.mark | KEEP | P | S,I,T,A | ORD | OWN |
| reports | reports.financial.drafts.read | KEEP | P | T | ORD | FINANCE |
| reports | reports.financial.final.read | KEEP | P | T,A | ORD | AGG |
| reports | reports.financial.generate | KEEP | P | T | ORD | FINANCE |
| reports | reports.financial.finalize | KEEP | B | - | ORD | FINANCE |
| reports | reports.financial.export | KEEP | B | - | ORD | FINANCE |

This table exhaustively covers all 82 C1 identifiers exactly once. KEEP is a
metadata claim, not a claim that the feature is implemented or policy approved.
Existing management-code semantics acquire the additional composite-profile and
operation/target gates in §4; their current stored metadata need not be widened.

### 2.3 Two exact metadata revisions and one retirement — PROPOSED

For both revised definitions, retain their original service, permission code,
`module_name=technical_accounts`, action (`provision` or `recover`), B state and
empty default set. Replace only these fields:

| Permission code | New permission_name | New description |
| --- | --- | --- |
| access_control.technical_accounts.provision | Provision application governance operator | Reserved creation of a real named application governance operator through independently approved provisioning; never assign Django staff or superuser flags. |
| access_control.technical_accounts.recover | Recover application governance operator | Reserved independently verified recovery of an application governance operator under the protected recovery contract; never recover Django framework privileges. |

These changes clarify application governance-operator identity creation/recovery;
neither code authorizes Django staff/superuser flags. Historical C1 metadata is not
edited. Future existing-row metadata differences are CONFLICT, not an automatic
overwrite; an approved explicit metadata transition is required to reconcile them.

Retirement tombstone:

- Identifier: `access_control.role_assignments.manage`.
- Disposition: `RETIRED_FOR_V2_SELECTION`; original service/definition retained in
  C1 history, never renamed, aliased to stronger rights or deleted from existing data.
- Replacements: `access_control.role_assignments.ordinary.manage`,
  `access_control.admin_assignments.manage`,
  `access_control.governance_assignments.manage`.
- Default pairs removed: **zero**; C1 already proposed no grants for this B code.
- Existing stored row or Grant/Deny: preserve and report for explicit review;
  active authority is a security conflict, not permission to copy it to replacements.
  No current generic assignment API is thereby enabled.

The candidate has 95 selectable definition entries plus this one tombstone, or
96 identifier-ledger entries. A future database could retain an older retired row;
that does not turn this into a 96-permission selectable v2 catalogue. The evaluator
has no retirement/readiness column: handlers must not accept retired codes and new
mutation policy must reject them. A tombstone alone does not revoke existing rights.

### 2.4 Fourteen complete new definitions — PROPOSED

Names/modules/actions/descriptions are exact AR-3A candidate metadata. All 14 are
NOT IMPLEMENTED as complete capabilities. None is a new service or numeric ID.

| Service | Permission code | Permission name | Module | Action | Description | Proposed defaults | State | Scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| accounts | accounts.school_accounts.read | Read eligible school accounts | school_accounts | read | List approved school-account fields for authorized school duties; exclude credentials, governance operators and unrelated confidential records. | A | P | SCHOOL |
| access_control | access_control.school_access.inspect | Inspect school account access | school_access | inspect | Inspect eligible ordinary accounts' roles and permitted capability summaries; exclude protected technical records and secrets. | A | P | SCHOOL |
| access_control | access_control.role_assignments.ordinary.manage | Manage ordinary extra roles | ordinary_role_assignments | manage | Attach or remove approved Treasurer/SSG Advisor responsibilities for eligible other accounts; never assign Admin, governance or framework privilege. | A | P | SCHOOL |
| access_control | access_control.admin_assignments.manage | Manage school Admin assignments | admin_assignments | manage | Promote or remove another eligible Normal Admin through protected review, actor-impact and last-effective-operator safeguards. | G | P | GOV |
| access_control | access_control.governance_assignments.manage | Manage governance assignments | governance_assignments | manage | Reserved independently approved application Super Admin elevation/removal; no self-assignment or ordinary-role shortcut. | - | B | GOV |
| access_control | access_control.role_templates.protected.manage | Manage protected role templates | protected_role_templates | manage | Reserved exact-delta changes to protected or actor-assigned templates with independent review and effective-operator checks. | - | B | GOV |
| access_control | access_control.policy_settings.manage | Manage reviewed governance policy | policy_settings | manage | Reserved versioned allowlisted access-policy changes; never arbitrary settings files, secret configuration or unreviewed service activation. | - | B | GOV |
| accounts | accounts.authentication_events.school.read | Read school authentication events | school_authentication_events | read | Read redacted events for eligible school-account activity under an approved event-source and privacy contract. | A | P | EVENT_SCHOOL |
| accounts | accounts.authentication_events.governance.read | Read governance authentication events | governance_authentication_events | read | Read approved redacted privileged authentication/security events; no credential, token, request-body or business-record access. | G | P | EVENT_GOV |
| access_control | access_control.audit.school.read | Read school access audit | school_audit | read | Read scoped ordinary school-account/assignment security changes; exclude protected governance detail and unrelated personal data. | A | P | SCHOOL_AUDIT |
| access_control | access_control.recovery.authorize | Authorize governed access recovery | governed_recovery | authorize | Reserved independently verified in-band recovery approval; unavailable-operator recovery still requires a separate institutional ceremony. | - | B | GOV |
| finance | finance.monitoring.overview.read | View financial monitoring overview | financial_monitoring | read_overview | Read approved period aggregates for a valid Advisor appointment without identifying individual payer data or finance write access. | V | P | MONITOR |
| reports | reports.monitoring.financial.read | View monitoring financial reports | financial_monitoring | read_reports | Read a minimized approved Final-report projection for the Advisor appointment; exclude Draft, generation, finalization and export. | V | P | MONITOR |
| finance | finance.monitoring.transactions.read | View monitoring transaction history | financial_monitoring | read_transactions | Read approved redacted transaction-history fields for the Advisor period; exclude identifying detail, raw receipts/images and mutation rights. | V | P | MONITOR |

All 14 codes are canonical, unique and absent from C1. Potential semantic overlaps
are real review concerns even though their identifiers are distinct:

| New candidate | Requirement basis | Overlap/incompatibility analysis and proposed boundary |
| --- | --- | --- |
| `accounts.school_accounts.read` | FR-ADM-01/06; normal school administration | Existing registration-request read covers pending requests, not all eligible ordinary school accounts. Exclude protected operators, credentials and unrelated private records. |
| `access_control.school_access.inspect` | FR-ADM-06; FR-ACL-12 | Narrow school projection differs from governance `effective_permissions.inspect`. Do not expose protected operator authority/technical details to Normal Admin. |
| `access_control.role_assignments.ordinary.manage` | FR-ADM-01/03; FR-ACL-14 | One replacement for broad retired code. Only approved ordinary additions/removals; cannot promote Admin/governance or change framework flags. |
| `access_control.admin_assignments.manage` | FR-ADM-02; UC-08 | Existing-account Admin membership differs from `accounts.school_accounts.provision` (restricted identity creation). Creating a new identity and promoting it needs both approved workflows, not a shortcut. |
| `access_control.governance_assignments.manage` | FR-ADM-04; FR-ACL-08 | Existing named identity elevation/removal differs from `technical_accounts.provision` (new governance identity). A new Super Admin may require both plus Admin assignment. Remains B with independent review. |
| `access_control.role_templates.protected.manage` | FR-ACL-09; OD-08 | Covers protected/actor-assigned role-template changes. Existing `governance_grants.manage` protects governance permission distribution, including account overrides. A protected template granting governance needs both relevant authorities/review; neither subsumes the other. |
| `access_control.policy_settings.manage` | Approved access settings requirement; FR-ACL-07/08 | Versioned allowlisted delegation/eligibility policy only. Existing service-activation authority remains separate. No general settings file, secrets or deployment-write privilege. Storage/deployment/audit path unresolved; B. |
| `accounts.authentication_events.school.read` | FR-ADM-07; FR-AUD-02/03 | Authentication source, school projection; not B1 permission-mutation history. Known and unknown-subject privacy requires an approved event contract. |
| `accounts.authentication_events.governance.read` | FR-AUD-04; FR-DJA-07 | Broader redacted privileged authentication projection; not `access_control.audit.read` and not a business/credential dump. |
| `access_control.audit.school.read` | Normal Admin permitted security monitoring; FR-AUD-01/03 | School-scoped authorization-change projection; distinct from authentication events and full governance audit. Exact visibility rules unresolved. |
| `access_control.recovery.authorize` | FR-ADM-04; FR-DJA-05 separation; OD-09 | Approval of an in-band application recovery request, not execution of `technical_accounts.recover` and not Django recovery. This is a proposed design refinement; retain separately as B pending reviewer policy. If owner merges it with execution, revise candidate/counts first. No in-band permission solves an absent-operator emergency. |
| `finance.monitoring.overview.read` | FR-FIN-03/04/07 | Narrow Advisor appointment projection; `finance.summary.read` belongs to existing finance/admin scope. If datasets prove identical later, owner may choose reuse; this candidate deliberately does not assume equivalence. |
| `reports.monitoring.financial.read` | FR-FIN-03/05/08 | Minimized Final-report projection; no Draft/generate/finalize/export rights. Existing `reports.financial.final.read` is not automatically the same projection. |
| `finance.monitoring.transactions.read` | FR-FIN-03/05/06 | Scoped, minimized history, not raw `finance.ledger.read`/`finance.payments.read`. The missing safe read model makes this an important distinct capability. |

Result: **no identifier duplicates** and no forced semantic equivalence. Recovery,
protected-template and monitoring reuse choices remain explicit owner decisions.
The fourteen additions are a design candidate, not fourteen approved SRS mandates.

## 3. Proposed role definitions and exact default matrix

### 3.1 Definitions and composition — PROPOSED

| Key | Role name | Exact proposed description | Definition status | Eligibility |
| --- | --- | --- | --- | --- |
| S | Student | System role for student accounts. | Carried C1 definition; historically initialized | Approved Student base role; registration approval assigns membership. |
| I | Instructor | System role for instructor accounts. | Carried C1 definition; historically initialized | Approved Instructor base role; registration approval assigns membership. |
| T | Treasurer | Restricted system role for treasury accounts. | Carried C1 definition; historically initialized | Eligible Student plus reviewed Treasurer appointment; retain Student. |
| A | Admin | Restricted system role for administrator accounts. | Carried C1 definition; historically initialized | Approved school-admin promotion; retain eligible pre-existing Instructor membership. |
| G | Technical Super Admin | Proposed technical governance operator; no automatic academic or financial access. | Carried C1 proposal; not initialized by this task | Protected governance assignment; complete Super Admin profile also requires Admin. |
| V | SSG Advisor | Optional Instructor responsibility for scoped read-only financial overview, approved reports and transaction history; Finance Monitor is the same responsibility. | New optional proposal | Eligible active Instructor plus valid independently appointed monitoring responsibility. |

Four roles are historically initialized. G was already a proposed fifth C1 role,
not an initialized operator. V is the only additional role definition relative to
C1. There is no persisted `Normal Admin`, composed `Super Admin`, `Finance Monitor`
or `Django Superuser` application role. Naming G otherwise requires a reviewed
identifier/reserved-classification transition; this exact candidate retains its name.

Normal Admin=A. Application Super Admin=A+G; Instructor may retain I with either
profile through explicitly authorized assignment. Student retains S when receiving
T. Advisor requires I+V, including continuing appointment eligibility. The same
account/session remains the subject of Deny and object checks.

### 3.2 Full per-service default counts — PROPOSED

The exact pair set is the union of default-key cells in §§2.2/2.4; this matrix
must match those cells. Every number is a proposed review count, not a live grant.

| Service | v2 definitions | S | I | T | A | G | V | Binding total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| accounts | 12 | 2 | 2 | 2 | 9 | 3 | 0 | 18 |
| access_control | 26 | 0 | 0 | 0 | 3 | 7 | 0 | 10 |
| academic | 8 | 2 | 2 | 1 | 6 | 0 | 0 | 11 |
| finance | 15 | 3 | 0 | 10 | 3 | 0 | 2 | 18 |
| clearance | 13 | 3 | 5 | 4 | 8 | 0 | 0 | 20 |
| group_rating | 10 | 5 | 5 | 0 | 0 | 0 | 0 | 10 |
| announcements | 3 | 1 | 1 | 1 | 3 | 0 | 0 | 6 |
| notifications | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 8 |
| reports | 6 | 0 | 0 | 3 | 1 | 0 | 1 | 5 |
| support | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| TOTAL | 95 | 18 | 17 | 23 | 35 | 10 | 3 | 106 |

New pair delta, with no other default changes:

- A: `accounts.school_accounts.read`, `access_control.school_access.inspect`,
  `access_control.role_assignments.ordinary.manage`,
  `accounts.authentication_events.school.read`, `access_control.audit.school.read`.
- G: `access_control.admin_assignments.manage`,
  `accounts.authentication_events.governance.read`.
- V: `finance.monitoring.overview.read`, `reports.monitoring.financial.read`,
  `finance.monitoring.transactions.read`.

S/I/T defaults remain exact C1 pairs. Admin's C1 finance-summary, fee-schedule,
Final-report and exemption proposals do not imply raw ledger/assessment rights;
exemptions remain gated on maker/checker/self-interest policy and implementation.
G retains only own-profile and technical/security responsibilities, not academic,
finance, clearance, rating or report default grants. A+G's school abilities come
from A; no automatic all-permissions grant or evaluator bypass is introduced.

All seven delegation-family defaults remain empty. Even if future default grants
are approved, management codes alone do not authorize operations until distinct
per-service authority, policy, target eligibility and implementation exist.
No blocked/retired code receives a default, and no default Deny rows are invented.

## 4. Normal Admin and Super Admin governance boundaries

### 4.1 Authority use versus authority distribution

The 38 candidate definitions in `accounts` and `access_control` are protected
under current B2 namespace/module classification. Their grant maintenance requires
a protected initializer/governance path even when use belongs to Student own-profile
or Normal Admin school duties. The remaining 57 definitions are not namespace-
protected by B2, but still require authorized management and business scope.

Normal Admin uses approved school roles/registration/academic/clearance/announcement
rights. It can manage only an explicit additional-role allowlist; the proposed
initial cases are Student→Treasurer and Instructor→SSG Advisor, preserving base
membership. Base Student/Instructor assignment belongs to atomic request approval.
No ordinary action assigns Admin, G, protected grants or framework flags.

Super Admin must have the active composite profile plus the exact effective
management code, approved service/permission/operation/recipient scope and current
review where needed. A Normal Admin with a misplaced direct management Grant still
fails the profile gate. A+G without effective authority or with Deny also fails.
Current B2 checks permissions but does not itself implement that composite gate;
it must be inside the future locked authorization boundary.

### 4.2 Self-escalation, last operator, audit and bootstrap

Preserve ordinary B2 refusals for self-Grant/Deny/deactivation, every actor-assigned
role (including inactive assignments for this guard), reserved targets/accounts
and governance codes. A separate protected workflow needs authenticated distinct
review/execution, exact reviewed delta and state/policy binding, expiry/replay
protection and same-transaction audit. No `allow_self` flag, role detachment,
renaming, namespace disguise, temporary account or alternate-role UI workaround.
Every Super Admin shares A/G, so another Super Admin alone is not necessarily
independent of changing those defaults. Shared-role exceptions remain blocked
until institutional independence/benefit controls and durable evidence are approved.

Approve the minimum effective governance bundle and usable-workflow predicate,
not merely a role count. AR-3A's six-code K is a proposal; it includes the new
Admin-assignment code. After each relevant mutation there must remain an eligible
Approved/active person with A/G, K effective after Deny/Service gates, and usable
approved governance/recovery arrangements. One shared deterministic lock protocol
must cover role/account/service/default/override/policy changes and simultaneous
revocations. Current B2 is not a complete last-effective-operator implementation.

B1 remains a real-persisted-actor atomic audit primitive, not authorization or
independent approval. The first operator needs an explicitly approved real-human
ceremony, external institutional authorization/attestation, minimal exact delta,
first-init serialization before the Service mutex exists, checkpoint and recovery.
Do not fabricate actors, null the audit FK, silently omit audit, authenticate by
CLI actor ID, or use a Django flag to authorize application bootstrap. Existing
bounded audit snapshots cannot encode full catalogue/review/initialization metadata.

No Django Superuser shortcut is added to `Account.has_perm()` or evaluator code.
Framework provisioning/admin surface, authentication eligibility, session invalidation
and logs need their own reviewed integration. Generic Django Admin edits cannot
bypass application services or audit, and staff-only DRF checks are not custom RBAC.

### 4.3 Mandatory resource-scope legend

Every protected action needs current global permission **and** its scope policy.
These identifiers in the delta inventory classify future server checks, not new
database columns or a generic implemented object-policy engine.

| Scope | Mandatory authorization beyond the code |
| --- | --- |
| OWN | Resolve actual Account→UserProfile owner; own profile/payment/receipt/request/read-state/result only. Exclude credentials, tokens, other-user identity and unapproved detail. Notification checks also require accessible announcement. |
| SCHOOL | Eligible ordinary school request/account/student/section/appointment only; actor/target/self-interest, period and data minimization rules. No implied protected-operator view or self-approval/appointment. |
| CATALOG | Approved campus/period definitions without student rosters or private finance records. Historical definition consistency still required. |
| ASSIGNED | Current actual adviser/teaching/signatory assignment and matching student/section/period; role label is insufficient. |
| SIGN | Actor-owned signature and resolved signing eligibility; request/appointment/student/period consistency, historical evidence and ambiguous Treasurer denial. No raw signature access for other people. |
| FINANCE | Authorized period/working-record relationship, financial invariants and attribution; Student+Treasurer cannot collect/receipt/exempt/sign their own conflicting records. Expense-beneficiary/checker fields are not invented; unsupported conflicts remain blocked. |
| AGG | Approved aggregate/Final-report content and disclosure scope; no raw payer ledger, receipt or signature images. |
| CLASS | Actual owned/assigned teaching sheet, class/period and permitted rating lifecycle/privacy. Instructor is not all-student access. |
| GROUP | Accepted own leader invitation or real group-member participation in same sheet/period; unique membership, no self-rating, criteria/submission consistency. rater_id references group_members, not directly users. |
| ANNOUNCE | Approved authorship/history and audience/publication rules; no audience/published columns are implied. Current target policy remains unresolved. |
| ROUTED | Clearance message recipient/thread/period privacy; representation is unresolved, so sending stays B. |
| GOV | Redacted catalogue/security/config or exact security-change target/authority/review state. Never a business-data, password or token authorization. |
| SCHOOL_AUDIT | Approved ordinary school-account/assignment audit projection; exclude protected governance detail and unrelated records. |
| EVENT_SCHOOL | Approved school authentication event source, actor/subject/redaction/retention rules; unknown-login identity is not a fake persisted actor. |
| EVENT_GOV | Approved privileged authentication event projection, with redacted technical/security scope and no secret/body dumps. |
| MONITOR | Valid Instructor+Advisor appointment/period and the specific minimized financial projection in §5. |

All 57 non-protected business-service definitions require their applicable scope,
including catalogue/aggregate/content checks. Account and governance definitions
also require target/event/review scopes; “protected namespace” is not an object
authorization implementation. `has_perm(code, obj)` currently denies for obj;
future query/services must enforce positive object policy explicitly.

## 5. SSG Advisor read-only permission contract

One optional V role supplies exactly three financial reads, while I supplies
ordinary Instructor duties. Each view is separately authorized and gated by a valid
appointment and approved period. The recommended initial projection is aggregates
for Overview, minimized approved Final content for Reports, and dates/types/amounts/
status plus non-sensitive references for History. Exclude payer names/School IDs
by default, raw receipts/signatures/images, Draft working data and unapproved exports.
These projection details require owner acceptance; they are not existing endpoints.

No payment recording, receipt issuance, expenses/funds mutation, exemption, role
management, generation/finalization/export or unrestricted ledger code is added
to V. Do not automatically install Denies: another independently assigned role may
add rights and a direct Deny overrides every source. Propose no same-scope V/T
coappointment unless a reviewed conflict exception exists; otherwise an account
could have write authority despite the “read-only Advisor” label.

Student+Treasurer retains S/T rights but business services must refuse contextual
self-payment/receipt/exemption/signing conflicts or route work to an independent
authorized actor. Removing T does not automatically remove an account-wide Grant
while S remains. Review dependent sources and revoke only approved dependencies
atomically, or enforce continuing appointment eligibility at the action boundary.
Instructor removal similarly must not leave ineligible Advisor rights active.
Current assignment rows have no expiry/period; approve manual revocation controls
or a separately designed enforceable appointment store before claiming duration.

## 6. Delegation and multi-role compatibility

| Configuration/use case | Current contract result | Proposed safe treatment |
| --- | --- | --- |
| Student+Treasurer override under finance recipient set {Treasurer} | Refused because all active target roles must be in scope | Require Treasurer and explicitly permit Student as additional role under exact code/operation policy; Student-only still denied. No broad Cartesian widening. |
| Instructor+SSG Advisor under role set {SSG Advisor} | Mixed-role target refused; adding Instructor could admit Instructor-only | New predicate requires actual Advisor+Instructor eligibility/appointment; role-default grants and account overrides have separate recipient rules. |
| Instructor+Admin or A+G account override | Reserved assignment protects target, even inactive; ordinary path cannot be widened to Admin | Separate protected workflow with independent review/actor impact; preserve ordinary refusal. |
| Admin/G default edit; any actor-assigned role | Reserved/assigned-role guard refuses | Protected exact-delta service, last-operator checks and approved shared-role exception; no direct B2 mutation. |
| Granting new school-use codes under accounts/access_control | Governance permission classifier refuses ordinary mutation | Protected initializer/governance distribution with exact approved A/S/etc defaults; usage authority does not imply grant-management authority. |
| Combined Student reads and Treasurer operator codes in one scope | Cartesian product can authorize operator codes to Student-only | Unsupported/unsafe. Use separate per-code/per-operation recipient predicates; do not split identity or change selected UI role. |
| Clearance mixed student/teacher/Treasurer/Admin signing codes | C1 disabled scope; broad registry cannot encode distinct duties safely | Remain OFF pending finer signatory/recipient/period policy and business checks. |
| Per-change independent review, expiry, approval ticket, object-limited grant | Not represented by ApprovedDelegationScope or grant rows | Reviewed durable workflow/evidence and contextual services, with schema review if needed. Reason/action strings are not substitutes. |

Keep all seven delegation families and legacy candidate scopes OFF. Do not add
delegate.accounts/access_control, wildcard codes or reserved recipients to bypass
the existing contracts. Academic teaching, finance operator, rating teacher,
announcement-reader, own-read-state and report subsets remain useful historical
scope candidates, not approved mixed-role policies. V2 must enumerate reviewed
operation/code/recipient combinations and test every allowed and denied named case.

## 7. Blocked permissions and unresolved security decisions

### 7.1 Exhaustive B inventory — PROPOSED no defaults

| Blocked candidate code | State | Proposed defaults | Required decisions |
| --- | --- | --- | --- |
| accounts.school_accounts.provision | B | - | V2-02/07/08: restricted identity provisioning, attribution and approval. |
| accounts.school_accounts.recover | B | - | V2-07/08: verified identity recovery and session/evidence contract. |
| access_control.catalogue.initialize | B | - | V2-01/07/10: approved manifest, real actor, audit/serialization and write environment. |
| access_control.services.activation.manage | B | - | V2-06/10: feature readiness, grant impact, effective-operator and activation review. |
| access_control.governance_grants.manage | B | - | V2-04/05/06/08: protected grants, independence, bound evidence and last operator. |
| access_control.technical_accounts.provision | B | - | V2-02/07/08: named application governance identity provisioning, not Django flags. |
| access_control.technical_accounts.recover | B | - | V2-06/07/08: verified application governance recovery, not Django recovery. |
| clearance.messages.send | B | - | V2-10: recipient/thread/period privacy not safely represented. |
| reports.financial.finalize | B | - | V2-10: attributable finalizer/checker, immutable source and retention. |
| reports.financial.export | B | - | V2-03/10: approved content/disclosure/export and retention. |
| access_control.governance_assignments.manage | B | - | V2-02/04/05/06: protected elevation, independent review and last operator. |
| access_control.role_templates.protected.manage | B | - | V2-04/05/06/08: assigned/protected template exception and evidence. |
| access_control.policy_settings.manage | B | - | V2-05/06/10: allowlisted versioned settings and shared deployment barrier. |
| access_control.recovery.authorize | B | - | V2-04/06/07/08: independent approval role and recoverable ceremony. |

The retired legacy assignment code is an additional tombstone, not a fifteenth B
definition. All delegation codes also have no defaults despite F, and every P/F
capability still needs approved implementation/readiness, grant and activation gates.
A Permission row has no is_active/readiness column: a letter in this document is
not a live feature gate. Future services must refuse blocked/retired operations;
unimplemented endpoints stay unavailable and unsupported grants must not be enabled.

### 7.2 Decision register — all OPEN / PROPOSED

| Decision | Required owner choice / current recommendation | Prior references |
| --- | --- | --- |
| V2-01 Exact candidate adoption | Accept/revise 95 definitions, one tombstone, two metadata revisions, six role definitions and 106 pairs. Any change requires recomputation, not silent seed edits. | AR-3A A01/A11; OD-01/12; C1 D01/D04/D18 |
| V2-02 Role/promotion eligibility | Exact ordinary extra-role allowlist, A/G naming and protected promotion/removal. One Advisor responsibility is settled; optional role implementation and duration still need approval. | A01/A02/A03; OD-01/03/04/06; D03/D06 |
| V2-03 Monitoring projection/reuse | Approve three minimized views and scope; retain dedicated codes or explicitly revise to reuse proven-equivalent old views. Decide V/T coexistence. | A03; OD-05/06; D12/D16 |
| V2-04 Overlapping governance intents | Accept exact separation of identity creation, membership elevation, protected template change, governance-grant change and recovery approval/execution. Recovery approval remains B unless this distinction is adopted. | A04/A05/A09; OD-02/08/11; D07/D08 |
| V2-05 Actor/shared-role safeguards | Independent reviewers/executors, exact reviewed state, approval binding/expiry/replay, source-of-authority and self-benefit rules. Ordinary self/assigned-role refusals retained. | A04/A05; OD-08/11; D05–D08 |
| V2-06 Effective operator and recovery | Approve K/usable-workflow/quorum, common lock order and independent recovery, including simultaneous revocations. A role count is insufficient. | A06; OD-02/09; D08 |
| V2-07 Bootstrap attribution | First real human, independent institutional evidence, initial metadata/authority/activation delta, first-init serialization and supported audit event contract. | A07/A09; OD-09; D09/D10/D18 |
| V2-08 Events, sessions and evidence | Choose auth/framework/review event sources, retention/access, failed unknown-subject handling and session revocation/step-up storage. | A09/A10; OD-07/13/14; D07/D10/D11 |
| V2-09 Framework integration | Explicit staff/superuser flags or reviewed alternative, restricted AdminSite/backend/manager and recovery; no custom bypass. Any schema changes separate. | A08; OD-10; FR-DJA-01–07 |
| V2-10 Activation and business scopes | Resolve finance/signature/rating/message/report/audience/privacy rules and settings deployment; readiness and service activation remain separate from catalogue approval. | A12/A13; OD-05/06/12/14; D02/D05/D12–D18 |

No decision is marked approved merely by this request. Existing C1 D01–D18 are
carried as relevant policy dependencies, not all resolved by SRS v0.3. The old
proposed ban on G/business-role coassignment is superseded as intended behavior
by the required composition; new self-interest protections replace that blanket
proposal, not the evaluator or ordinary B2 safeguards.

## 8. Schema, implementation and independently versioned manifest impact

| Area | Current support | Required change / limitation — PROPOSED |
| --- | --- | --- |
| Six roles/defaults/Grant-Deny | Existing roles/account_roles/role_permissions/account_permissions and FK/unique constraints can represent them | No profile schema or second user identity needed. New data requires later approval; defaults do not enforce eligibility/lifecycle by themselves. |
| Global evaluation | Existing union, direct Deny, account/role/Service gates, exact codes and fresh reads | Reuse unchanged; object scope, composite mutation gate and blocked/retired action control belong in trusted operation contracts. No Django bypass. |
| Finer mutation policy | B2 explicit scope/authority, locks, durable commit/audit patterns | Add per-operation/code/composition rules and separate protected services; do not nest durable B2 entry calls in arbitrary outer transactions or rely on unlocked façade checks. |
| Last effective operator | Current rows provide relevant authority state | Shared serialization and complete predicate across every writer/config transition are not implemented. Reuse reviewed lock order, including sorted Service dependencies; no missing-row mutex assumption during bootstrap. |
| Audit/review | B1 supports bounded ID/flag/effect/status snapshots with real actor in same atomic transaction | Full metadata, initialization, framework flags, approval IDs/digests and anonymous events need explicit contracts. Durable review/expiry may require new schema or verified external storage; no fabricated actor. |
| Advisor/financial object policy | ERD has payment user links, receipt/payment link, some operator/period references | Actual projections, membership/appointment/ownership/conflicts are future logic; expense beneficiary and complete checker/finalizer history are not supplied. Automatic assignment expiry is absent. |
| Django Superuser | Account has no persisted staff/superuser fields; manager raises | AR-3A's false-default two-flag proposal and restricted framework adapter need independent ERD/model/migration approval. PermissionsMixin would add a separate permission system/joins and shortcuts; not automatically adopted. |
| Sessions/events | No complete implemented login/revocation or auth-event store | Security-version/registry and event pipeline/schema choices require separate review. Fresh permission evaluation is not itself physical session revocation. |

### 8.1 Proposed v2 manifest contract, after owner approval only

Create a **new independently versioned artifact**, for example `catalogue-v2.0`,
with no change to `c1_v1.json`, its version, canonical source path or pinned source
digest. Record the v1 file digest above as derivation provenance; freeze accepted
v2 definitions, exact pairs, role eligibility/composition, readiness, protected
operation tiers, scope policies, tombstone/replacement metadata and unresolved
decision gates. Record the SRS digest and owner decision-record references too.

Use a separate SHA-256 of the accepted v2 source snapshot. This document cannot
embed its own stable content hash recursively; compute the frozen snapshot digest
after accepted edits and record approval/digest externally in the decision record
and future manifest. No v2 manifest or source digest is installed by this phase.
Original C1 identities remain historical; no numeric database IDs are hardcoded.

### 8.2 Read-only planner changes required later

The current validator loads one fixed C1 file/version, validates five roles and
the C1 tables/count matrix. It cannot validate v2 by substituting new counts. A
separate version-aware validator must check exact source/decision provenance,
six roles, all 95 definitions/106 pairs, metadata revisions, lifecycle, scope
predicates and unsupported policies. Preserve the old v1 test expectations.

The planner needs explicit old/new version selection with no apply mode; clearly
label proposed/unapproved sources and SRS blockers. Compare service/role/code exact
metadata and actual MySQL collation. Report the two revised definitions as metadata
CONFLICT if an existing row has old values; report missing metadata as CREATE only
as a proposal. Retired existing rows/overrides remain preserved and surfaced for
review; active retired grants require conflict review, not rename/remap/deletion.
Unknown/inactive records must never be silently pruned or reactivated.

Do not assume today's 92/4/0/97 v1 output is a v2 baseline. Future comparisons
must use then-current database state and dependencies. Keep READ ONLY transaction,
SELECT guard, no audit writes, no timestamp updates, no mutation-service calls,
stable replay output and aggregate non-PII reporting. Default approval is distinct
from metadata creation and service/feature/delegation activation; permission rows
have no readiness flag to enforce those stages automatically.

## 9. Static validation results

**PASS for this fixed PROPOSED review candidate.** Validation read local source/
Markdown/JSON/DBML files only; no Django setup, application tests or database reads.

| Check | Statically verified result |
| --- | --- |
| C1 disposition coverage | 79 KEEP + 2 REVISE + 1 RETIRE = 82; no missing/duplicate C1 code. |
| Additions | 14 exact AR-3A metadata rows; 0 identifier collisions with C1. |
| Candidate arithmetic | 82 - 1 + 14 = 95 selectable definitions; 1 separate retired tombstone; 96 identifier-ledger entries. |
| Services | 10 preserved service definitions; per-service totals sum to 95. |
| Role definitions | 6: four historical initialized roles, carried proposed governance role and new optional Advisor. |
| Proposed bindings | 106 = 96 carried pairs + 10 new pairs; no duplicate or dangling references. |
| Role totals | S 18; I 17; T 23; A 35; G 10; V 3. |
| Readiness | F 9; P 72; B 14. Metadata only, not activation. |
| Protected classification | 38 candidate definitions protected by B2 service/module/namespace; 57 other business definitions with scope policy. |
| B / RET / delegation defaults | 0 / 0 / 0. Seven exact delegation-family definitions retained. |
| Governance business defaults | 0 academic/finance/clearance/group_rating/reports pairs for G. |
| Advisor defaults | Exactly three named monitoring reads, no writes/export. |
| Identifier/field validation | PASS against current code regexes, exact model text limits and referenced services/roles. |
| C1 source/file provenance | Pinned source digest and complete repaired-v1 JSON digest match the recorded originals. |
| Safety meaning | Static candidate checks only; owner decisions, implementation and live initialization remain gated. |

Checks include: exact AR-3A 14-code coverage and metadata equality; no new-code
collision with C1; complete mutually exclusive 79/2/1 C1 disposition coverage;
exact two-field revisions only; unchanged identities/service placement; canonical
globally unique codes; referenced services/roles; existing model field lengths;
unique binding pairs and exact count-matrix equality; no B/retired/delegation
defaults; exact three Advisor read defaults; no G business defaults; stable B2
management constants and seven delegation-family identities; source/ERD hashes,
document links and preservation of every pre-existing file.

These checks verify syntax, arithmetic, traceability and declared restrictions.
They do not implement or prove object authorization, workflow independence,
runtime concurrency, event privacy, last-operator safety, feature readiness or
owner acceptance. Those remain the reviewed implementation/security-test gates.

## 10. Owner approval checklist

- [ ] Record named owner/reviewers, date and accepted v2 source snapshot/digest.
- [ ] Accept/revise each KEEP/REVISE/RETIRE/ADD entry and the retirement handling;
  no alias, automatic old-grant conversion or deletion.
- [ ] Accept/revise all 106 explicit proposed pairs, A/G composition/name and
  the one optional V role; no unrestricted business or framework authority.
- [ ] Decide the recovery/protected-governance overlap boundaries and independently
  approved shared-role/actor-impact exceptions; otherwise keep them blocked.
- [ ] Approve exact monitoring projections, appointment/lifecycle and financial
  self-interest rules; confirm no Advisor write/export defaults.
- [ ] Approve per-operation/code/recipient predicates, effective-operator K/quorum,
  lock/recovery contract and precise delegation authorities; legacy scopes stay OFF.
- [ ] Resolve initial actor/audit/evidence/session/event decisions and any separate
  schema changes. Django Superuser never substitutes for application authority.
- [ ] Authorize only the next bounded artifact/validator/planner task. Metadata
  initialization, exact grants, activation and administrator provisioning each
  need later explicit authorization and disposable-MySQL security verification.

None of these checkboxes is prechecked by preparing this proposal.

## 11. Next implementation handoff

**PROPOSED next phase AR-3B2B:** after the owner accepts an exact revision/digest
and records any revised decisions, create an independently versioned v2 planning
manifest/validator and extend only the read-only planner. Unresolved security
policies remain explicit blockers, not invented defaults or approval records.
If owner edits alter this candidate, recompute counts before implementation.

Suggested bounded prompt, to be used only with the actual decision record:

> Continue CTU-G Workspace with AR-3B2B: independently versioned catalogue-v2
> manifest validation and read-only planning. Read the accepted revision/digest
> of `docs/architecture/AR-3B2A-permission-catalogue-v2-proposal.md` and the actual
> owner decision record. Do not infer adoption from the file's existence. Preserve
> C1 v1 bytes/source hash, its repaired canonical path and all existing work.
>
> Implement the accepted version's exact service/role/permission/default data,
> independently pinned source/SRS/decision provenance, protected/blocked/lifecycle
> metadata and retirement tombstone. Validate all identifiers/field lengths,
> exact old/new deltas, pair matrix, three Advisor reads, Deny/non-bypass contracts
> and finer recipient policies. Keep unapproved choices explicitly blocked.
> Add version-aware read-only planning with CREATE/MATCH/CONFLICT/DEFER, including
> metadata revisions, preserved unknown/inactive/overridden records and active
> retired-grant conflicts; do not remap old grants or force historical totals.
>
> Run focused static/catalogue tests and guarded disposable-MySQL planner tests,
> retaining v1 regressions, MySQL collation and zero-DML/DDL/audit guarantees.
> Reverify live planner reads only if authorized, with before/after integrity
> evidence. Do not modify models/ERDs/migrations, seed/activate any catalogue,
> enable live mutations, provision administrators/Django Superuser, implement
> login/UI, or reset/discard/commit/push existing work. Report exact tests, counts,
> preserved v1, remaining policy blockers and stop.

### Preservation and stop record

Only this proposal document is new. The 214 pre-existing paths, including tracked/
untracked changes and recorded deletions, remain unchanged. Both ERDs retain:

- Full: `E9235A87555FFCD50ECB6AB6C1A45F9C7C54E344FF8F269ECC890579F633E4B2`
  (42 tables, 80 references).
- Auth: `F050F7B910038532CA8E73B283F16A57DEDD6B738FDC74D293E64D539A4AFAC4`
  (9 tables, 17 references).

This completes documentation/static validation only. No code, grants, schema,
database, frontend or approval state is changed.
