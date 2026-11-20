# Phase 1H-C1 — Permission Catalogue and Governance Policy Proposal

**Status: PROPOSED — PROJECT-OWNER APPROVAL REQUIRED.** Version: C1 proposal v1,
2026-11-06. Nothing in this document authorizes initialization, creates grants,
enables delegation, or declares a working feature/API. Approval record: not yet
provided. Explicit decisions, reviewer identity, date and accepted revision must
be recorded before a later implementation/apply phase.

## 1. Evidence, terminology and scope

Inspected the existing delegation.py, mutations.py, services.py, audit.py,
access-control/account models, URL configuration, Phase 1H-B2 report, both DBML
files, business-app model/view scaffolds, and relevant public frontend content.
The branch remains ronald at 8e1ead5 with valuable existing tracked/untracked/
deleted changes. No existing file is to be edited in this policy phase.

The last verified live baseline was MySQL 8.4.13, 16 tables, 22 migrations, four
active roles, and no accounts/catalogue/grants. That database baseline and the
228 passing backend tests are prior-run evidence, not newly executed checks in
this documentation-only phase. No database connection or test fixture is needed
to validate this proposal's field/code contracts.

The approved ERD contains 42 application tables and 80 references; the auth ERD
contains nine tables and 17 references. Both are read-only. Their SHA-256 values:

| File | SHA-256 |
| --- | --- |
| docs/database/full_schema.dbml | E9235A87555FFCD50ECB6AB6C1A45F9C7C54E344FF8F269ECC890579F633E4B2 |
| docs/database/schema.dbml | F050F7B910038532CA8E73B283F16A57DEDD6B738FDC74D293E64D539A4AFAC4 |

Service means a proposed services-table record, not a deployed microservice.
The backend remains one modular Django monolith. All service/permission IDs
remain database-generated; no numeric catalogue IDs are proposed.

Role keys: S = Student, I = Instructor, T = Treasurer, A = existing role_name
Admin (displayed as School Admin), X = proposed Technical Super Admin. Do not
rename the existing Admin record to School Admin. X is not initialized.

Readiness is documentation metadata, never a new model column:

- F: the exact contract or contract family is referenced by implemented internal
  security code, but no catalogue row, live authority or public endpoint exists.
- P: planned capability supported by the ERD or an explicitly proposed technical
  read; business authorization, models/handlers and tests still need implementation.
- B: reserved proposal blocked by a listed policy/representation dependency;
  no default role grant is proposed until that dependency is resolved.

Every default-role entry below is a **future least-privilege recommendation**,
conditional on owner approval, feature readiness, object-scope enforcement and
explicit grant review. It is not an instruction to grant all listed permissions
now. A dash means no default role, not an explicit Deny override.

Public registration, CSRF bootstrap, landing/help content and eventual session
login/logout have their own eligibility/security contracts. Do not require an
application permission merely to register or log in: Pending/inactive registrants
cannot hold effective application permissions. Public routes still require their
existing validation, CSRF/origin, throttling and privacy protections.

## 2. Proposed service catalogue

The name and description columns are proposed database metadata. Other columns
are documentation only. No Service record is inserted or activated here.

| Service code | Service name | Description | Current evidence / planned responsibility |
| --- | --- | --- | --- |
| accounts | Accounts and Profiles | Account identity, personal profiles and controlled school-account administration. | Account/UserProfile models and registration/CSRF APIs exist; approval, provisioning and profile APIs are future work. |
| access_control | Access Control and Governance | Custom permission evaluation, delegated management, technical governance and security audit access. | Seven access-control models, evaluator, audit writer and dormant trusted mutations exist; no governance UI/API. |
| academic | Academic Administration | Courses, school years, periods, sections, academic profiles and class advisers. | App is a scaffold; six corresponding ERD tables are planned. |
| finance | SSG Finance | Organization fee schedules, payments, receipts, funds, expenses and exemptions. | App is a scaffold; finance-table capabilities are planned. |
| clearance | School Clearance | Subject assignments, signatories, clearance requests, signatures and student clearance communication. | App is a scaffold; clearance-related ERD capabilities are planned. |
| group_rating | Group Rating | Assigned rating sheets, criteria, leader invitations, groups, submissions and scores. | App is a scaffold; seven ERD tables are planned. |
| announcements | Campus Announcements | Official campus announcements with controlled authorship. | Public landing has presentation content; the database-backed app/API is a scaffold. |
| notifications | Announcement Read Tracking | Per-user announcement read state without a new generic notification store. | App is a scaffold; user_notification_reads is the relevant planned table. |
| reports | Financial Reports | Draft generation and controlled access to period-based financial reports. | App is a scaffold; reports/report_items are planned, with unresolved finalization controls. |
| support | Public Help and Contact | Existing public help/contact content without a support-ticket or impersonation system. | Public help exists; backend app is a scaffold and no support table exists in the ERD. No protected permission is proposed for public help. |

Provisional boundaries follow the ERD groupings: academic owns its six foundations;
clearance covers subjects/units/subject_teachers; reports owns reports/report_items.
Signature operations are functionally authorized under clearance, although the ERD
lists signatures in the finance section. This avoids giving signatories finance
record access. Confirm module ownership before implementation; do not duplicate
tables or silently change the ERD to settle ownership.

The landing ServiceCards.tsx currently advertises COM Lab Inventory and attendance.
Inventory is excluded from the approved main scope, and the ERD has no attendance
tables. Those marketing entries are not evidence of implemented/approved backend
capabilities. No inventory or attendance service/permission is included here.
Any copy correction or scope expansion is a separate approved task. AI, Flutter,
JWT browser authentication, support tickets and impersonation are also excluded.

## 3. Proposed permission catalogue and exact default bindings

Codes are immutable business identifiers after approval: lowercase dotted codes,
globally unique, maximum 150 characters. Renaming requires explicit conflict and
grant review, not a silent alias. Permission names/modules/actions/descriptions
fit the existing 100/100/50/255-character fields. Descriptions below propose the
minimum future backend scope; a code alone does not enforce that scope.

The Default roles column is the authoritative proposed per-permission grant
matrix. Omitted roles receive no grant. There are no wildcard or inherited role
grants, and X never receives all permissions merely by its role name.

### 3.1 Accounts

| Service | Permission code | Permission name | Module name | Action name | Description / enforced scope | Default roles | Readiness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| accounts | accounts.profile.self.read | Read own profile | profiles | read_self | Read only the actor's identity/profile fields; never password hashes, reset tokens or sessions. | S,I,T,A,X | P |
| accounts | accounts.profile.self.update | Update own personal names | profiles | update_self | Update own first, middle, last and suffix names; exclude school ID, roles, account status and credential changes. | S,I,T,A,X | P |
| accounts | accounts.registration_requests.read | Review registration requests | registration_requests | read | Read Student/Instructor requests needed for school review; exclude privileged provisioning and secrets. | A | P |
| accounts | accounts.registration_requests.approve | Approve school registration | registration_requests | approve | Approve another eligible Student/Instructor request through a future atomic approval/assignment service. | A | P |
| accounts | accounts.registration_requests.reject | Reject school registration | registration_requests | reject | Reject another pending Student/Instructor request with bounded, appropriate review attribution. | A | P |
| accounts | accounts.school_accounts.suspend | Suspend ordinary school account | school_accounts | suspend | Suspend another Student/Instructor account; exclude reserved administrators and restricted provisioning. | A | P |
| accounts | accounts.school_accounts.activate | Reactivate approved school account | school_accounts | activate | Reactivate another already Approved Student/Instructor account; never approve a Pending request implicitly. | A | P |
| accounts | accounts.school_accounts.provision | Provision restricted school operator | school_accounts | provision | Reserved restricted Treasurer/School Admin provisioning; requires separate governance and attribution policy. | - | B |
| accounts | accounts.school_accounts.recover | Recover school account access | school_accounts | recover | Reserved identity-verified recovery; no credential/token disclosure or bypass of privileged recovery. | - | B |

### 3.2 Technical governance and explicit delegation

All rows in this section belong to the canonical access_control Service. Ordinary
Phase 1H-B2 functions cannot grant, revoke or override these governance permissions.

| Service | Permission code | Permission name | Module name | Action name | Description / enforced scope | Default roles | Readiness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| access_control | access_control.catalogue.read | Read permission catalogue | catalogue | read | Read service/permission definitions and readiness metadata without exposing business records or secrets. | X | P |
| access_control | access_control.role_permissions.manage | Manage ordinary role permissions | role_permissions | manage | Invoke trusted role-grant/revoke services only with separate approved service delegation and eligible targets. | X | F |
| access_control | access_control.account_permissions.manage | Manage ordinary account overrides | account_permissions | manage | Invoke trusted Grant/Deny/deactivation services only with separate approved service delegation and eligible targets. | X | F |
| access_control | access_control.effective_permissions.inspect | Inspect effective permissions | effective_permissions | inspect | Inspect attributable account/role/permission identifiers and outcomes; exclude profile, finance and assessment bodies. | X | P |
| access_control | access_control.audit.read | Read access-control audit | audit | read | Read security-change attribution and allowlisted snapshots; do not treat this as business-ledger or credential access. | X | P |
| access_control | access_control.diagnostics.read | Read redacted technical diagnostics | diagnostics | read | Future read-only health/configuration checks with no passwords, tokens, request bodies or business-record dumps. | X | P |
| access_control | access_control.catalogue.initialize | Initialize reviewed catalogue | catalogue | initialize | Reserved future command authority; separate initial attribution and exact approved manifest are prerequisites. | - | B |
| access_control | access_control.services.activation.manage | Control service activation | service_activation | manage | Reserved activation/deactivation with outage and grant-impact review; ordinary permission mutation does not change Services. | - | B |
| access_control | access_control.role_assignments.manage | Manage controlled role assignments | role_assignments | manage | Reserved trusted assignment/revocation with self-escalation, incompatible-role and last-operator safeguards. | - | B |
| access_control | access_control.governance_grants.manage | Change protected governance grants | governance_grants | manage | Reserved independently approved governance changes; never route through ordinary delegation services. | - | B |
| access_control | access_control.technical_accounts.provision | Provision technical operator | technical_accounts | provision | Reserved named-human Technical Super Admin provisioning through a separate reviewed bootstrap/provisioning path. | - | B |
| access_control | access_control.technical_accounts.recover | Recover technical operator | technical_accounts | recover | Reserved independently verified technical recovery; no self-recovery or Django superuser shortcut. | - | B |
| access_control | access_control.delegate.academic | Delegate approved academic scope | delegation | delegate | Separately approved academic permission/recipient allowlist; no blanket access or automatic grant to X. | - | F |
| access_control | access_control.delegate.finance | Delegate approved finance scope | delegation | delegate | Separately approved finance permission/recipient allowlist; no financial-record read authority. | - | F |
| access_control | access_control.delegate.clearance | Delegate approved clearance scope | delegation | delegate | Reserved service delegation; mixed signatory/student recipient policy is not representable as a broad current scope. | - | F |
| access_control | access_control.delegate.group_rating | Delegate approved rating scope | delegation | delegate | Separately approved teaching-only subset; no automatic assessment or student-leader authority. | - | F |
| access_control | access_control.delegate.announcements | Delegate approved announcement scope | delegation | delegate | Separately approved scope only; public-reader versus School Admin author roles must not be conflated. | - | F |
| access_control | access_control.delegate.notifications | Delegate approved read-state scope | delegation | delegate | Separately approved own-read-state scope; does not authorize viewing another user's read state. | - | F |
| access_control | access_control.delegate.reports | Delegate approved report scope | delegation | delegate | Separately approved Treasurer draft-report subset; no finalization or unrestricted financial disclosure. | - | F |

No delegate.accounts or delegate.access_control contract is proposed: those target
services are hard-protected from ordinary mutations. Support has no protected
capability in this version, so it has no delegation authority code. No delegation
code is a default grant, including for X; service-owner approval and a separate
governance grant path must precede its use.

### 3.3 Academic administration

| Service | Permission code | Permission name | Module name | Action name | Description / enforced scope | Default roles | Readiness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| academic | academic.catalogue.read | Read academic catalogue | catalogue | read | Read courses, school years, periods and section definitions without student rosters. | S,I,T,A | P |
| academic | academic.profile.self.read | Read own academic profile | academic_profiles | read_self | Read only the actor's user-linked academic_profile and its course/year/section/period context. | S | P |
| academic | academic.advisees.read | Read assigned advisees | class_advisers | read_assigned | Read minimal student academic data only for sections currently assigned to the actor as class adviser. | I | P |
| academic | academic.courses.manage | Manage course definitions | courses | manage | Maintain approved course definitions; preserve referenced historical records. | A | P |
| academic | academic.periods.manage | Manage school years and periods | school_periods | manage | Maintain school-year/semester dates and activation with consistency and historical-data checks. | A | P |
| academic | academic.sections.manage | Manage year and section definitions | year_and_sections | manage | Maintain course/year/section definitions without silently moving historical students or assignments. | A | P |
| academic | academic.profiles.manage | Manage student academic profiles | academic_profiles | manage | Maintain approved student academic status and section/year references; no role or credential changes. | A | P |
| academic | academic.advisers.manage | Assign class advisers | class_advisers | manage | Assign eligible approved instructors to sections; validate the unique section/adviser relationship. | A | P |

### 3.4 SSG finance

| Service | Permission code | Permission name | Module name | Action name | Description / enforced scope | Default roles | Readiness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| finance | finance.fee_schedule.read | Read organization fee schedule | fee_schedules | read | Read applicable period fee amounts without access to other students' payment records. | S,T,A | P |
| finance | finance.fee_schedule.manage | Manage organization fee schedule | fee_schedules | manage | Maintain period fee amounts under approved rules; do not rewrite amounts used by historical payments. | T | P |
| finance | finance.payments.self.read | Read own payments | payments | read_self | Read only org_fee_payments linked to the actor's user_id and applicable receipt details. | S | P |
| finance | finance.payments.read | Read payment ledger | payments | read | Read school organization-fee payments needed for Treasurer duties; exclude credentials and unrelated personal data. | T | P |
| finance | finance.payments.record | Record organization payment | payments | record | Record attributable valid payments with amount/status/period invariants; no silent edit, void or deletion. | T | P |
| finance | finance.receipts.self.read | Read own receipts | receipts | read_self | Read receipts only through payments belonging to the actor's user_id. | S | P |
| finance | finance.receipts.issue | Issue payment receipt | receipts | issue | Issue a unique receipt for a valid payment with issuer attribution and duplicate-issuance policy. | T | P |
| finance | finance.funds.record | Record other funds | other_funds | record | Record attributable non-fee funds for an approved period; preserve financial history. | T | P |
| finance | finance.expenses.record | Record expense | expenses | record | Record attributable expenses for an approved period under financial validation and retention rules. | T | P |
| finance | finance.expense_images.attach | Attach expense evidence | expense_images | attach | Attach authorized evidence to an expense; require reviewed upload/storage/content controls. | T | P |
| finance | finance.ledger.read | Read finance working ledger | ledger | read | Read Treasurer payment/fund/expense detail needed for reconciliation, without granting mutation authority. | T | P |
| finance | finance.summary.read | Read financial summary | summaries | read | Read approved period aggregates; do not expose student payment rows or raw receipt/signature images. | T,A | P |
| finance | finance.exemptions.manage | Manage approved fee exemptions | student_fee_exemptions | manage | Manage justified exemptions for other eligible students with explicit school approval and no self-benefit. | A | P |

No refund, reversal, void, destructive correction or expense deletion code is
proposed: the current ERD does not define their accounting/history workflow.

### 3.5 School clearance

| Service | Permission code | Permission name | Module name | Action name | Description / enforced scope | Default roles | Readiness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| clearance | clearance.subjects.manage | Manage subject catalogue | subjects | manage | Maintain subjects and lecture/lab units; preserve referenced assignments and clearance history. | A | P |
| clearance | clearance.teaching_assignments.manage | Manage teaching assignments | subject_teachers | manage | Assign eligible instructors to subject/period/section combinations using the approved unique key. | A | P |
| clearance | clearance.signatories.manage | Manage signatory appointments | authorized_signatories | manage | Maintain fixed/adviser appointments under the ERD's position rules; do not assign Treasurer roles implicitly. | A | P |
| clearance | clearance.assignments.self.read | Read own signatory assignments | assignments | read_self | Read only teaching, adviser and fixed/dynamic signatory assignments resolved to the actor. | I,T,A | P |
| clearance | clearance.requests.self.read | Read own clearance requests | clearance_requests | read_self | Read only organization/subject requests belonging to the actor's user_id. | S | P |
| clearance | clearance.requests.self.submit | Submit own clearance requests | clearance_requests | submit_self | Submit own eligible subject/signatory requests for a consistent active period; no duplicate or cross-section requests. | S | P |
| clearance | clearance.requests.assigned.read | Read assigned clearance requests | clearance_requests | read_assigned | Read only students/requests for the actor's resolved current teaching or authorized signatory responsibility. | I,T,A | P |
| clearance | clearance.subject_requests.sign | Sign assigned subject clearance | subject_requests | sign | Sign only requests whose subject_teachers resolves to the actor and matches the student's section/period. | I | P |
| clearance | clearance.organization_requests.sign | Sign authorized organization clearance | organization_requests | sign | Sign only for the actor's resolved fixed/adviser/Treasurer responsibility; deny vacant or ambiguous assignments. | I,T,A | P |
| clearance | clearance.signatures.self.manage | Manage own signing signature | signatures | manage_self | Manage only the actor's active signature after signatory eligibility is established; never expose others' signature_data. | I,T,A | P |
| clearance | clearance.messages.self.read | Read own clearance messages | clearance_messages | read_self | Read only messages for the actor's user_id; no inferred instructor-wide thread access. | S | P |
| clearance | clearance.messages.send | Send routed clearance message | clearance_messages | send | Reserved until recipient/thread/period privacy semantics can be enforced with the approved schema. | - | B |
| clearance | clearance.progress.read | Read school clearance progress | progress | read | Read school operational clearance status summaries without signing, bypassing signatories or exposing signature images. | A | P |

### 3.6 Group rating

| Service | Permission code | Permission name | Module name | Action name | Description / enforced scope | Default roles | Readiness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| group_rating | group_rating.sheets.assigned.read | Read assigned rating sheets | rating_sheets | read_assigned | Read sheets only for the actor's actual subject_teachers assignments and permitted periods. | I | P |
| group_rating | group_rating.sheets.manage | Manage assigned rating sheets | rating_sheets | manage | Create/change sheet Draft/Open/Closed state only for the actor's teaching assignment; enforce submission immutability. | I | P |
| group_rating | group_rating.criteria.manage | Manage owned sheet criteria | rating_criteria | manage | Maintain criteria only for an owned eligible sheet, with stable ordering and scoring consistency. | I | P |
| group_rating | group_rating.invitations.manage | Manage leader invitations | leader_invitations | manage | Invite eligible students only to an owned sheet's class/period; enforce unique invitation and response rules. | I | P |
| group_rating | group_rating.invitations.self.respond | Respond to own leader invitation | leader_invitations | respond_self | Read/respond only to invitations addressed to the actor's user_id; do not create an assignment by choosing a role label. | S | P |
| group_rating | group_rating.groups.manage | Manage own accepted leader group | groups | manage_owned | Manage a group only through the actor's accepted leader invitation for the same sheet. | S | P |
| group_rating | group_rating.members.manage | Manage own group members | group_members | manage_owned | Manage only an authorized leader's group roster; enforce same-sheet eligibility, unique membership and leader invariants. | S | P |
| group_rating | group_rating.submissions.self.manage | Manage own rating submission | rating_submissions | manage_self | Draft/submit only as the actor's group_member rater; enforce group/sheet/criteria alignment, deadlines and no self-rating. | S | P |
| group_rating | group_rating.results.self.read | Read own rating result | results | read_self | Read the actor's approved own-result aggregate without disclosing co-rater identities or other students' results. | S | P |
| group_rating | group_rating.results.assigned.read | Read assigned class rating results | results | read_assigned | Read assessment results only for sheets owned through the actor's teaching assignment and approved assessment privacy rules. | I | P |

### 3.7 Announcements, read tracking and reports

| Service | Permission code | Permission name | Module name | Action name | Description / enforced scope | Default roles | Readiness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| announcements | announcements.read | Read campus announcements | announcements | read | Read authorized official announcements; public publication is a separate explicit policy, not inferred from this grant. | S,I,T,A | P |
| announcements | announcements.create | Create official announcement | announcements | create | Create an attributable official school announcement; no invented Draft/audience/approval fields. | A | P |
| announcements | announcements.update | Update official announcement | announcements | update | Correct official content under an approved authorship/history policy; preserve poster attribution. | A | P |
| notifications | notifications.read_state.self.read | Read own announcement read state | announcement_reads | read_self | Read only announcement-read rows for the actor's user_id and announcements the actor may access. | S,I,T,A | P |
| notifications | notifications.read_state.self.mark | Mark own announcement read | announcement_reads | mark_self | Mark only the actor's own accessible announcement read, preserving the composite user/announcement primary key. | S,I,T,A | P |
| reports | reports.financial.drafts.read | Read finance draft reports | financial_reports | read_drafts | Read working Draft reports for Treasurer reconciliation without granting finalization. | T | P |
| reports | reports.financial.final.read | Read finalized financial reports | financial_reports | read_final | Read approved Final report aggregates and authorized report content; no raw student payment or signature-image access. | T,A | P |
| reports | reports.financial.generate | Generate finance draft report | financial_reports | generate | Generate attributable Draft reports with validated period totals and Expense/Fund references. | T | P |
| reports | reports.financial.finalize | Finalize financial report | financial_reports | finalize | Reserved until maker/checker, attributable finalization, immutable source snapshot and retention rules are approved. | - | B |
| reports | reports.financial.export | Export approved financial report | financial_reports | export | Reserved until report-content minimization, disclosure, export and retention policies are approved. | - | B |

Support deliberately has no permission rows in this version: existing public help
and contact content do not require effective permissions. Technical diagnostics
are explicitly protected under access_control, not delegated as ordinary support.

## 4. Default role-permission matrix and separation of duties

This count matrix summarizes the exact bindings in section 3; a count is not a
wildcard grant. The proposed full future matrix has 96 explicit role/permission
pairs: S 18, I 17, T 23, A 30, X 8. None is applied now.

| Service | Student | Instructor | Treasurer | School Admin | Technical Super Admin |
| --- | --- | --- | --- | --- | --- |
| accounts | 2 | 2 | 2 | 7 | 2 |
| access_control | 0 | 0 | 0 | 0 | 6 |
| academic | 2 | 2 | 1 | 6 | 0 |
| finance | 3 | 0 | 10 | 3 | 0 |
| clearance | 3 | 5 | 4 | 8 | 0 |
| group_rating | 5 | 5 | 0 | 0 | 0 |
| announcements | 1 | 1 | 1 | 3 | 0 |
| notifications | 2 | 2 | 2 | 2 | 0 |
| reports | 0 | 0 | 3 | 1 | 0 |
| support | 0 | 0 | 0 | 0 | 0 |

Student: own academic/payment/receipt/clearance information and own eligible
rating participation. A group leader is a relationship established by an accepted
invitation and group membership, not an additional global role or a Student's
self-selected privilege.

Instructor: only actual teaching/adviser/signatory assignments and owned rating
sheets/results. The Instructor role never implies access to every student.

Treasurer: finance recording/reconciliation and the actual Treasurer signatory
responsibility. No registration approval, exemption approval, technical governance,
or unrelated academic assessment rights are proposed.

School Admin: school registration review, academic organization, appointments,
clearance oversight, official announcements, exemptions and financial summaries/
Final reports. No default payment recording, raw working ledger, individual rating
results, technical provisioning or permission-management authority is proposed.

Technical Super Admin: explicit catalogue/effective-permission/audit/diagnostic
reads, the two dormant ordinary permission-management contracts, and own identity
profile only. No academic, finance, clearance, rating or report permission is a
default grant. Delegation authorities, governance-grant modification, catalogue
initialization, service activation and technical provisioning/recovery have no
default grant even for X. Each needs separate reviewed governance attribution.

All eligible assigned active roles still combine by union in the existing
evaluator; active direct Deny takes precedence. This document proposes no broad
default Deny rows, since they could unintentionally defeat a separately reviewed
second role. Missing grants are sufficient to deny by default.

Proposed separation rules for future assignment services: no default X/business
role coassignment and no default A/T combination for maker/checker duties.
These are NOT enforced by today's evaluator/schema/B2 functions. Approve exact
exceptions and identity handling before implementing role assignments. Do not
invent a second School ID or duplicate identity to bypass accounts.school_id
uniqueness. Multiple ordinary roles such as S/I remain possible, subject to
object scope and the approved incompatible-role policy.

## 5. Mandatory object/data-scope rules for future capabilities

Permission possession is necessary, never sufficient for a record operation.
The current evaluator checks global codes and returns False for has_perm with a
non-None obj; there is no generic implemented object-policy engine. Future views
and business services must enforce these scopes server-side, including list
queries and exports, and test negative cross-user/class/period cases.

| Scope | Required future enforcement / ERD evidence |
| --- | --- |
| Own identity/student records | Resolve Account to users through users.account_id. Enforce actor ownership of user_id; reject submitted actor/owner IDs and any password/hash/token field. |
| School account administration | Limit review to another canonical Student/Instructor request; requested_role is input to review, never authority. Approve status, activation, trusted role assignment and audit atomically. Exclude reserved operators. |
| Academic adviser | class_advisers.user_id must resolve to the actor; limit student academic_profile rows to the assigned section. Define historical period retention before permitting old-cohort reads. |
| Teacher responsibilities | subject_teachers.user_id must resolve to the actor with correct period/section and active assignment. Instructor role or creator IDs alone are insufficient. |
| Own finance/receipts | org_fee_payments.user_id must be the actor's user. Resolve receipts through payment_id, not a submitted receipt owner. Amount, period, receipt uniqueness and exemptions require business validation. |
| Organization signing | Resolve fixed positions from authorized_signatories.account_id, Class Adviser from class_advisers, and Treasurer from actual account_roles. Require active eligible actor and consistent student/period responsibility. Deny vacant or ambiguous resolution. |
| Signatures | Signature owner must equal the signing actor. Preserve referenced historical signature data; prefer a new signature row plus deactivation rather than overwriting a signature already used. No other-role raw signature access. |
| Rating leader/member | Verify accepted invitation, same sheet/group/period, actual leader responsibility and unique sheet membership. rater_id references group_members.group_member_id, not users.user_id. Prevent self-rating and cross-sheet criteria/member references. |
| Rating results | Default Student reads own approved aggregate only; Instructor reads own sheets. Approve anonymity, scoring bounds, deadlines and submitted-state immutability before implementation; no official gradebook is implied. |
| Announcement reads | No audience, Draft or published-status column exists. Public publication/role-specific audience rules need an explicit implementable decision; do not expose all DB rows publicly by inference. |
| Notification read state | Resolve only the actor's accessible announcement/read pair. Keep the ERD composite primary key; do not silently add an id or permit other-user read-receipt inspection. |
| Reports | Validate period/date sources and polymorphic report_items.item_type/item_ref_id against permitted Expense/Fund records. Final report disclosure must respect the approved content scope. status alone does not prove checker/finalizer attribution. |

Single-campus deployment is the current scope. The ERD has no tenant/campus
partition key; this proposal does not claim multi-campus row isolation.

Proposed future self-interest rule: an operator must not appoint themselves to a
teaching/adviser/fixed-signatory responsibility or approve their own exemption to
expand access. Another independently authorized actor is required. These business
assignment guards are not implemented by B2 and require D06/D12 approval and tests;
do not infer their enforcement from the global permission check. Payment ownership
can be checked through user_id, but expense beneficiary/conflict detection is not
fully represented by the current expense fields and must not be invented.

## 6. Delegation and governance policy mapped to Phase 1H-B2

### 6.1 Candidate service scopes — all remain OFF

No ACCESS_CONTROL_DELEGATION_POLICY setting is written by this phase. These are
review candidates only, activated in no environment by this document. Every
candidate also requires its distinct access_control.delegate.<service> grant;
the matrix grants none by default.

| Target service | Exact candidate delegable codes | Eligible recipient role names | Compatibility / restriction |
| --- | --- | --- | --- |
| academic | academic.catalogue.read, academic.advisees.read | Instructor | Current shape can represent this teaching-only subset after object-policy implementation; no Student or School Admin write permission in this scope. |
| finance | finance.fee_schedule.read, finance.fee_schedule.manage, finance.payments.read, finance.payments.record, finance.receipts.issue, finance.funds.record, finance.expenses.record, finance.expense_images.attach, finance.ledger.read, finance.summary.read | Treasurer | Current shape can represent this Treasurer-only subset. Exclude Student own-read and School Admin exemption rights. Mixed-role account targets may still be refused. |
| clearance | None proposed for activation under the current coarse scope | None | Student, teacher, Treasurer and School Admin duties differ; keep ordinary delegation disabled pending a reviewed finer recipient/action policy. |
| group_rating | group_rating.sheets.assigned.read, group_rating.sheets.manage, group_rating.criteria.manage, group_rating.invitations.manage, group_rating.results.assigned.read | Instructor | Teacher-only subset; exclude all Student leader/participant permissions and any School Admin override. |
| announcements | announcements.read | Student, Instructor, Treasurer | Equivalent reader permission for each listed role. Exclude School Admin create/update; Admin is a reserved ordinary target. |
| notifications | notifications.read_state.self.read, notifications.read_state.self.mark | Student, Instructor, Treasurer | Same own-record scope for all recipients; object checks must exist first. Exclude reserved operators. |
| reports | reports.financial.drafts.read, reports.financial.final.read, reports.financial.generate | Treasurer | Treasurer-only subset; exclude finalization/export and reserved School Admin targets. |
| accounts | None | None | Hard-protected target service; ordinary B2 mutation cannot delegate these permissions. |
| access_control | None | None | Hard-protected governance service; no self-grant or ordinary delegation of authority itself. |
| support | None | None | No protected capability or delegation contract proposed in this version. |

The current registry describes a Cartesian product: every permission_codes entry
is eligible for every role_names entry. **Do not combine finance's Student reader
and Treasurer operator scopes into one broad role list.** That would permit
delegating operator permissions to Students. Similar widening is forbidden for
clearance, ratings and announcements. Role-based defaults and exceptions outside
these narrow candidates require a separate approved initialization/governance
path or a reviewed future policy-shape extension, never an ad-hoc workaround.

### 6.2 Rule-to-code compatibility matrix

| Policy rule | Existing contract / function | Representation and limitation |
| --- | --- | --- |
| Approved, active, persisted actor with active assigned role | services.has_permission and mutations._management_context | Implemented; current database state is read after locking. Requested role and caller-edited flags do not authorize. |
| Separate management and delegation authority | delegation.ROLE_PERMISSION_MANAGE / ACCOUNT_PERMISSION_MANAGE; require_governance_authority; require_delegation | Implemented; both authority definitions must belong to active canonical access_control. Possession of the target code is not delegation authority. |
| Explicit service/code/recipient approval | approved_scope and ApprovedDelegationScope | Implemented with strict keys and no wildcard. Coarse per-service recipient cross-product cannot represent per-permission recipient or per-operation scopes. |
| No self-escalation | _management_context target_id check | All own-account mutations are refused, including adding Deny and removing Deny. No ordinary self-repair/recovery exception. |
| Actor-assigned role restrictions | actor_role_ids comparison in _management_context | Every currently assigned role is protected, even if it contributes no active grant. An actor cannot edit a second role merely by using a different selected UI role. |
| Reserved administrators | is_reserved_role and target-role/account checks | Admin/Super Admin/Technical Super Admin variants are blocked. A target account holding any reserved role is blocked even when that role is inactive. |
| Protected governance permissions | is_governance_permission | Service, module or code namespace can trigger protection: access_control, accounts, auth/authentication/authorization, security, governance, admin. No ordinary change even with a matching registry entry. |
| Approved ordinary role grant/revoke | grant_role_permission / revoke_role_permission | Implemented; only active eligible independent role targets. Disabling a role grant removes its contribution, not other-role/direct grants. |
| Direct Grant/Deny/deactivation | grant_account_permission / deny_account_permission / deactivate_account_override | Implemented; target must be Approved/active with all active roles in scope and no reserved assignment. Removing Deny or replacing it with Grant requires full authority. |
| No inactive-record privilege | active target Service/Role/Account checks plus evaluator gates | Implemented conservatively for every operation. Cleanup of inactive targets is refused; no cleanup bypass is proposed. |
| Effective-access refresh | services._effective_codes and Account.has_perm delegation | Implemented, no cross-request permission cache. Subsequent evaluations see committed changes under transaction isolation. Revoking one source does not imply all effective access is gone. |
| Atomic attributable mutation | durable atomic block, governance Service mutex, record_access_audit | Implemented; deterministic locks and same-transaction audit. Actual changes audit; authorized no-ops do not. Do not nest these services inside an ordinary caller transaction. |
| Role assignment/approval/bootstrap | Not provided by B2 | Planned separate trusted services; do not misuse role-permission functions to assign roles or approve accounts. |

### 6.3 Compatibility gaps that must stay visible

- G1: The proposed A and X defaults, and all accounts/access_control codes even
  for ordinary roles, cannot be maintained through B2 services: reserved roles
  and governance permissions are deliberately blocked. A separately approved
  attributable initializer/governance path is required.
- G2: Permission has no is_active/readiness field. Service activation gates the
  entire service, not individual proposed features. Do not invent a permission
  activation flag or equate a catalogue row with a shipped/authorized API.
- G3: A per-service recipient list cannot encode different roles for each code,
  separate Grant/Deny-removal approval, or different role-grant/account-override
  scopes. Existing management codes distinguish operation families globally only.
- G4: A T+S account fails a Treasurer-only account-override scope because all
  active roles must be in scope. Widening the scope to S is unsafe for operator
  permissions. Any finer target rule needs reviewed code/tests, not role removal
  or a second account invented to pass validation.
- G5: Two-party approval, delegation expiry and per-grant object constraints are
  not represented in the current schema/service contract. An audit reason code
  is not a reviewer approval, expiry, approval ticket or object-policy substitute.
- G6: Business object scopes and incompatible role combinations are not enforced
  by the global evaluator. Do not claim they are solved by this catalogue.
- G7: B1 audit snapshots allow specific security IDs/flags/enums only. Catalogue
  definitions, free-text justifications, report/announcement identifiers and other
  business history need a reviewed audit event contract; do not encode them into
  action strings or abuse another field's meaning.
- G8: No reserved-role provisioning/recovery, service activation, last-operator
  safeguard or session-revocation workflow exists. All remain gated future work.

## 7. Technical Super Admin versus School Admin

School Admin handles routine school operations: Student/Instructor review,
academic organization, appointments, clearance progress and official notices.
Finance defaults are aggregate/Final-report oversight plus controlled exemption
approval, not Treasurer transaction entry. School Admin is not a technical
permission administrator or a Django superuser.

Technical Super Admin handles technical catalogue/authorization inspection,
security audits and redacted diagnostics. The proposed two ordinary mutation
authorities remain unusable until a separately approved service delegation is
explicitly assigned. Neither authority grants business records, another person's
signature, student assessment results, financial exports or actor impersonation.

Governance grants, reserved-role changes, provisioning, initial bootstrap and
recovery must use a separate reviewed path with attributable operator identity,
independent approval where required, and last-operator/concurrency safeguards.
No unconditional X bypass, temporary is_superuser flag, default Django group,
requested role, or fabricated system identity is permitted.

Changing a technical role's own grants through ordinary services is intentionally
impossible. Recovery is not achieved by deactivating a Deny on oneself or renaming
a protected role. The current unique School ID and identity model must be honored.

## 8. Proposed future initialization command — plan only

No command, manifest executable, seed migration, service activation or SQL is
implemented/executed in C1. The future command must separate metadata planning,
metadata application, reviewed default grants and activation; none implies another.

### 8.1 Default dry-run and comparison

1. Require local-development target verification for any future write mode;
   refuse production/shared/unknown targets unless a separate deployment policy
   expressly authorizes them. Verify schema/migration fingerprint and checkpoint.
2. Load an immutable, owner-approved, versioned catalogue/grant manifest with a
   recorded digest. Validate exact codes, field lengths, service relationships,
   role names, governance classification and readiness. No numeric IDs in source.
3. Dry-run must issue reads only: no get_or_create, audit insertion, timestamp
   update, command lock-table record, seeding or grant reactivation. Do not expose
   passwords, reset/session tokens or complete sensitive rows in output.
4. Print CREATE/MATCH/CONFLICT/DEFER summaries with row counts, service/code
   identities and proposed grant deltas. Example format, not actual live output:

```text
MODE DRY-RUN — NO WRITES
SERVICE academic: CREATE, initially inactive
PERMISSION academic.catalogue.read: CREATE, no automatic grant
ROLE Technical Super Admin: DEFER to approved Phase 1I provisioning
GRANT Admin -> academic.courses.manage: PROPOSED, review/path required
ACTIVATION: NONE
APPLY: BLOCKED if actor attribution or required approvals are unresolved
```

5. Compare exact Python identifiers AND MySQL uniqueness behavior. Case/accent/
   trailing-space equivalents, duplicate names/codes, a code under the wrong
   service, metadata drift and code/role normalization conflicts are hard stops,
   not silent rename/update opportunities. Cosmetic differences still require
   explicit review before modifying an existing record.
6. Preserve unknown existing services/permissions/grants and all data; list them
   separately. Never prune, overwrite a description, reset a name/PK, reactivate
   a disabled Service/Role/grant, replace a Deny, or remove an override by default.

### 8.2 Explicit apply/grant/activation gates

7. An eventual apply mode must require explicit owner approval of the manifest
   revision/digest and a trusted authenticated named operator. --actor-account-id
   is an identity locator, not authentication or authority. Never use a fake ID,
   null actor, borrowed actor or CLI password flag/logging to bypass attribution.
8. Metadata-only application, if approved, creates missing exact records only;
   planned services start inactive and no role/account grants or delegation registry
   are enabled. Public registration does not consult Service activation today;
   this plan does not invent a public-route maintenance switch.
9. Any future grant application requires a separate exact per-role/per-code delta
   review. The 96-pair proposed target matrix is not a bulk apply instruction.
   B rows have no defaults; X is not created by the ordinary initializer. Existing
   inactive grants, overrides and unknown grants are preserved and flagged.
10. School Admin/X bindings and protected governance codes cannot be applied by
    calling B2 functions or widening role_names. Use only the separately approved
    initializer/governance contract, with the same or stronger authorization,
    attribution, locking and self-escalation safeguards.
11. Activation is another explicit reviewed operation. Require implemented backend
    object scopes, code-to-endpoint mapping, negative tests and disclosure controls
    before enabling a service or granting its planned capabilities. A P/F/B label
    in this document is not an implemented feature gate.
12. Within one owned transaction, lock and recheck current records and authority,
    execute only approved deltas, and append safe attributable initialization/audit
    events. Success output/side effects occur only after commit. Audit failure
    rolls back all associated changes; no partial batch success or hidden retry.
13. After commit, reread counts, exact bindings, untouched overrides, service flags,
    schema/migrations and ERD hashes. A repeated identical approved apply is a
    no-op with no duplicate grants/audits or refreshed attribution/timestamps.

### 8.3 First initialization and audit attribution blocker

There is no initial operator or catalogue, and the B2 mutex Service does not yet
exist. A normal command cannot authorize itself through a permission it has not
initialized, create its own unrestricted delegation, or audit with a nonexistent
actor. B1's current payload allowlist also does not describe full catalogue
metadata diffs. These are real preconditions, not errors to auto-repair.

Preferred option **for owner consideration only**: a separate restricted Phase 1I
ceremony establishes an actual named human technical operator, approved minimal
governance catalogue/authority and first-init serialization in one reviewed plan.
Self-attribution to that real newly persisted operator would require explicit
owner approval plus an independent external attestation; it is not automatically
valid because the FK can be satisfied. Thereafter the ordinary attributable
catalogue command can require an existing authorized actor/mutex.

An alternative external-attestation-only first metadata import would require an
explicit exception and retention policy; it must not silently omit required
application audit. Neither option is approved here. Do not invent a placeholder
system account, modify actor_account_id nullability or encode approval evidence
in an unrelated JSON/reason field. Define first-init locking separately because
locking a missing Service row is not the existing B2 mutex protocol.

### 8.4 Future initialization regression/verification requirements

- Dry-run emits its plan with zero DDL/DML/audit writes; missing approval/actor
  denies apply before any insertion.
- Exact replay is idempotent. Collation-equivalent codes/names, wrong service,
  conflicting metadata, partial manifests, reserved-role absence and concurrent
  commands fail safely without silent overwrite.
- Existing active/inactive records, assignments, overrides and unrelated rows
  survive unchanged. No implicit grant reactivation or Technical Super creation.
- Reviewed grants only, inactive-service defaults, actor authority, bootstrap-only
  boundaries, last-operator rules and incompatible-role rules have negative tests.
- Audit failure/mid-batch failure rolls back the complete batch; successful events
  and data become visible together only after commit. Concurrent replay creates
  one exact set of rows and attributable events.
- Use disposable MySQL with the guarded runner and read-only before/after live
  verification. Run the existing 228-test backend suite plus new catalogue,
  scope-compatibility and command tests when implementation is authorized.

## 9. Security decisions requiring explicit project-owner approval

All decisions below are OPEN. Approval of this document's title or permission
names alone must not be interpreted as approval to seed, assign, activate or deploy.

| Decision | Proposed recommendation / explicit question |
| --- | --- |
| D01 Catalogue and readiness | Approve or revise the 10 services, 82 codes, default binding matrix and feature activation prerequisites. Which P capabilities are actually required first? |
| D02 Module boundaries and scope mismatch | Confirm subject/teaching ownership under clearance and signature authorization there; keep support public-only. Inventory/attendance stay excluded; authorize any landing-copy correction separately. |
| D03 Default School Admin boundary | Confirm Student/Instructor review, academic maintenance, exemptions and financial aggregate/Final-report oversight; approve any additional raw finance or assessment access explicitly. |
| D04 Technical boundary | Confirm X's eight proposed defaults, no automatic service delegation/business access, and exact diagnostics/audit privacy scope. Who may approve each later service delegation? |
| D05 Recipient granularity | Accept only the narrow compatible candidate scopes, or authorize a separately tested per-permission/operation recipient policy extension. Never approve a broad cross-product by accident. |
| D06 Incompatible roles and self-interest | Define X/business and A/T incompatibilities, legitimate multi-role exceptions, own-account decisions and shared identity constraints before role assignment/provisioning. |
| D07 Override and two-party policy | Who may create Deny, remove Deny or grant exceptions? Is independent per-change approval required? Current B2 has no reviewer/expiry/ticket model; do not claim it enforces one. |
| D08 Governance and last operator | Define separate protected-grant/role operations, effective-authority-based last-operator invariants, recovery, emergency access and shared lock order. Role count alone is insufficient. |
| D09 Bootstrap attribution | Choose and approve the first human actor/attestation, initial minimal authority, first-init lock/checkpoint and recovery procedure before any write mode or Phase 1I bootstrap. |
| D10 Audit contract and retention | Approve initialization metadata events, bounded reason taxonomy, access/retention and any stronger immutability controls. B1 security snapshots are not a financial or document-history ledger. |
| D11 Session revocation | Define when account/role/grant changes invalidate sessions and how future session APIs enforce eligibility. The evaluator refreshes permissions, but no session-revocation service exists. |
| D12 Finance integrity | Approve fee-schedule immutability, payment/receipt invariants, exemption maker/checker rules and financial correction history before transaction handlers. No refund/void/delete workflow is assumed. |
| D13 Clearance/signature resolution | Decide multiple Treasurer holders, historical period responsibility, signing conflict rules and signature retention. The ERD has no period-scoped Treasurer-role assignment; ambiguous signing must deny. |
| D14 Clearance-message privacy | Define recipients/threads/period routing and is_read meaning. Current messages lack recipient/thread/period references; the reserved send capability remains blocked. |
| D15 Rating privacy and scoring | Approve leader/member constraints, rater anonymity/result visibility, deadlines and score bounds without inventing per-criterion weight/maximum columns. |
| D16 Reports | Define auditable finalizer attribution, maker/checker and immutable source/report behavior, plus export content/retention. reports.status alone cannot prove those controls. |
| D17 Announcements/read tracking | Decide public publication and audience semantics without invented status/audience columns; preserve per-user read state and the composite key. |
| D18 Initialization approval boundaries | Approve metadata-only versus grant versus activation stages, exact conflict policy and permitted write environments. Existing record preservation remains the default. |

## 10. Exact next steps — Phase 1H-C2

1. Obtain an explicit owner decision record for the selected revision and relevant
   D01-D18 answers. Until then, every entry remains a proposal and live delegation
   stays disabled. Do not treat this task as that confirmation.
2. Freeze the accepted subset as a versioned immutable catalogue/grant manifest,
   with the precise target/recipient/object scopes and known blocked capabilities.
   Do not silently turn all 82 proposals into seed data or all 96 bindings into grants.
3. Authorize C2 as **manifest validation and read-only initialization planning**:
   implement a validator plus a dry-run-only management command with no apply,
   activation, seeding, bootstrap, live grant or frontend path. Validate exact
   current-schema compatibility and classify CREATE/MATCH/CONFLICT/DEFER.
4. Test that planner entirely in disposable MySQL, including collation conflicts,
   unrelated-record preservation, zero-write dry-run, missing actor/bootstrap
   dependencies and coarse-scope rejection. Run existing backend regressions.
5. Review the concrete dry-run plan and resolve attribution/audit/governance gaps
   before separately authorizing any metadata apply mode, protected grant changes,
   scope activation, role assignment or Phase 1I provisioning. None is implicit C2 work.

Suggested bounded C2 prompt, usable only after the owner accepts a concrete revision:

> Using owner-approved C1 revision <revision/digest> and its recorded decisions,
> implement only the immutable catalogue manifest validator and a read-only
> plan_permission_catalogue management command. Compare existing records and
> reviewed grant intentions; emit CREATE/MATCH/CONFLICT/DEFER and blocker summaries
> with zero database/audit writes. Test in guarded disposable MySQL and run backend
> regressions. Do not implement apply/seed/activation, bootstrap, role assignment,
> management endpoints, dashboards or schema changes. Preserve all existing work.

## 11. Validation and stop boundary

C1 validates proposal identifiers/metadata lengths/uniqueness, model field
compatibility, default-role bindings, B2 management/delegation names and recipient
scope constraints against source. The role counts and matrix must agree with
section 3; reserved B capabilities and all delegation authorities have no defaults.
X must have no academic/finance/clearance/rating/report default grants.

No backend/frontend tests, database reads/writes, command implementation, setting
change, schema change, provisioning or feature activation is performed in C1.
The prior 228-test result is historical evidence only. Only this new documentation
file is created, and both protected ERD hashes and existing source hashes are
checked for preservation. Stop after preparing and validating this proposal.

Validation result: PASS for 10 unique service definitions, 82 unique/canonical
permission codes and their actual model field lengths, 96 proposed explicit role
bindings, all 10 service/role count-matrix rows, both implemented management-code
constants, seven correctly placed delegation-family definitions, and six narrow
candidate recipient cross-products. Readiness totals are F 9, P 62, B 11; every B
row and every delegation code has zero default bindings. Both ERD hashes/counts
match their approved inputs. Source-hash comparison found no existing file changes;
the only new file is this proposal. These static checks do not approve policy,
test future business handlers or claim a new 228-test run.
