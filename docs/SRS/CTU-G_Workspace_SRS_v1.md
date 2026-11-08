# CTU-G Workspace
## Software Requirements Specification (SRS)

**Document ID:** CTUG-SRS-001  
**Version:** 0.3 — Revised Access-Control Architecture and SSG Advisor Clarification Draft  
**Date:** 7 November 2026  
**Project:** CTU-G Workspace — Cebu Technological University, Ginatilan Campus  
**Status:** **PROPOSED FOR REVIEW — NOT IMPLEMENTATION OR DATABASE-WRITE APPROVAL**  
**Maintainer:** CTU-G Workspace Project Team  
**Repository destination:** `docs/requirements/CTUG_Workspace_SRS_v0.3.md`

> **Change-control notice.** This specification captures the project owner's updated use cases: two Admin permission profiles; Admin-controlled default role permissions; multi-role Student/Instructor accounts; and a separate Django framework Superuser. It supersedes conflicting *proposed administrator policies* in Phase 1H-C1, but does **not** overwrite the approved DBML, migrations, previously implemented safeguards, or existing code. No role creation, data migration, permission activation, or live privilege grant is authorized by this document.

---

## Document control

| Field | Record |
|---|---|
| Revision | v0.3, 2026-11-07 — formal typography revision and consolidated SSG Advisor / Finance Monitor terminology; not formally signed off |
| Supersedes | v0.2 SRS draft; no changes to the database or previously approved implementation |
| Previous design reference | `docs/phase1h-c1-permission-catalogue-governance-proposal.md` (C1 v1; now requires reconciliation) |
| Database reference | `docs/database/full_schema.dbml`; `docs/database/schema.dbml` — read-only contracts |
| Related implementation | Phase 1H-A evaluator; 1H-B1 audit; 1H-B2 guarded mutation services; 1H-C2A read-only catalogue planner |
| Current evidence | Previous Codex report stated 286 backend tests passed and C2A made no live database writes; this SRS does not independently re-run those tests |
| Approval authority | Project owner and appointed academic/security reviewers (to be recorded) |
| Classification | Internal project requirements; no student data or secrets |

## 1. Introduction

### 1.1 Purpose

This SRS specifies user-facing behavior, roles, authorization, data boundaries, security controls, operational constraints and acceptance criteria for CTU-G Workspace. It is intended to guide architecture, implementation, verification, stakeholder review, and scope control.

### 1.2 Product scope

CTU-G Workspace is a **single-campus web-based university operations platform** integrating account registration and approval, profiles, academic administration, SSG finance, clearance, group rating, announcements/read tracking, reports, and controlled role/permission management. The browser experience uses a shared permission-aware dashboard. A future Flutter mobile application and AI features are outside this SRS release baseline unless later approved.

### 1.3 Stakeholders

Students; instructors; SSG Treasurer; SSG Advisor (also called Finance Monitor); campus administrators; designated access-governance administrators; technical/Django operators; authorized university reviewers and auditors; system maintainers.

### 1.4 Terminology

| Term | Definition |
|---|---|
| Application role | A named entry in custom `roles` that can be assigned to an account through `account_roles`. |
| Role default | Active grants in `role_permissions`; changing a default affects every eligible holder of the role. |
| Account override | A direct `Grant` or `Deny` in `account_permissions` for one account; active Deny takes precedence. |
| Normal Admin | School administrator profile with the base `Admin` role and only approved school-management permissions. |
| Super Admin (application) | Admin profile that combines school administration with protected permission-governance authority; **not** automatically a Django Superuser. |
| Django Superuser | Framework-level privileged account/flag configured for Django administrative maintenance; separate from application role grants. |
| SSG Advisor (Finance Monitor) | **One and the same responsibility profile**, not two separate roles. An eligible Instructor may receive approved, read-only SSG finance-monitoring responsibilities. The recommended canonical additional role name is `SSG Advisor`; "Finance Monitor" is its descriptive label. Approved narrow account overrides may provide equivalent abilities without establishing a second Finance Monitor role. |
| Effective permissions | Active grants from all assigned active roles plus active direct Grants, excluding permissions covered by an active Deny, subject to account/service eligibility and record-scope checks. |
| Approved account | Account explicitly reviewed and activated under the account-approval workflow; a requested role never conveys authority. |

### 1.5 Source hierarchy

The user's current clarified administrator and multi-role use cases control **intended behavior**. Existing ERD/model structures control what can currently be represented. Existing code and test evidence control what is **implemented**. Earlier C1 role defaults and catalogue counts remain proposals for reconciliation, not approved runtime configuration. Conflicts must be recorded and resolved through change control, not silently edited.

## 2. Product context and system boundaries

### 2.1 Logical architecture

1. **Presentation:** React, TypeScript, Vite and Tailwind CSS; shared public, authentication, and dashboard layouts.
2. **Application:** Django REST Framework modular monolith; service-layer workflows; session-based browser authentication and CSRF protection.
3. **Authorization:** Custom Hybrid Dynamic Access Control with roles, role defaults, per-account overrides, least privilege, server-side record-scope checks and audit trails.
4. **Persistence:** Existing MySQL application database; schema evolution requires separate reviewed migrations.
5. **Restricted framework administration:** Django Admin and Django Superuser integration, not automatically interchangeable with application authority.

### 2.2 Out-of-scope assumptions

Multi-campus tenancy, inventory, student attendance, a general help-ticket database, impersonation, automated gradebook, browser JWT storage, Flutter deployment and autonomous AI permission changes are **not** authorized by this SRS. Public help/contact content may remain outside protected permissions. Future features require their own approved requirements and schema compatibility review.

### 2.3 Delivery status (as reported)

| Area | Current reported status |
|---|---|
| Public Student/Instructor registration and CSRF | Implemented and previously tested; Pending/inactive accounts only |
| Account approval and role assignment | Not implemented end to end |
| Login/logout/sessions | Not implemented end to end |
| Permission evaluator and transactional access audit | Implemented and previously tested |
| Permission mutation services | Implemented, but live changes intentionally gated |
| Catalogue | C1 proposal of 10 services, 82 codes and 96 bindings; C2A planner implemented; no live seed |
| Admin profiles / Django Superuser integration | New/changed requirements; implementation pending |
| Campus business modules / dashboard | Primarily planned/scaffolded; not production-ready |

## 3. Roles, administrator profiles and authority boundaries

### 3.1 Application roles and composable profiles

The application SHALL support multiple active roles on one account. The current initialized roles are `Student`, `Instructor`, `Treasurer`, and `Admin`. Additional responsibility roles are **proposed**, not yet initialized. The precise name of the protected technical-governance role must be resolved against earlier `Technical Super Admin` contracts.

| User profile | Proposed role composition | Intended rights |
|---|---|---|
| Student | Student | Own student-facing data and services only |
| Instructor | Instructor | Assigned classes, teaching, clearance and rating services |
| Student Treasurer | Student + Treasurer | Own student tools plus approved SSG Treasurer operations; conflict-of-interest controls required |
| Instructor SSG Advisor (Finance Monitor) | Instructor + SSG Advisor (proposed), or equivalent separately approved narrow overrides | Instructor rights plus **one** financial-monitoring responsibility: scoped View Financial Overview, View Financial Reports, and View Transaction History; no Treasurer write powers |
| Normal Admin | Admin | School management, registration review, eligible ordinary role assignment; redacted school audit monitoring if approved |
| Super Admin | Admin + protected governance role (provisionally `Technical Super Admin`) | Normal Admin rights **plus** protected role-default and override governance |
| Instructor + Normal Admin | Instructor + Admin | Both job duties, subject to separation-of-duties rules |
| Instructor + Super Admin | Instructor + Admin + protected governance role | Combined duties only if independently approved; higher-risk conflict controls apply |

**Interpretation:** “Normal Admin” and “Super Admin” are **two default administrative permission profiles**, not merely two independent individual permission codes. Their implementation is proposed as role composition to reuse the existing schema; the protected role name and compatibility rules remain an approval decision. Having an Admin role does not confer automatic global permission-management powers.

### 3.2 Division of responsibility

| Activity | Normal Admin | Super Admin (application) | Django Superuser |
|---|---|---|---|
| Review ordinary registration | Allowed by approved school permission | Inherits school rights | No automatic application authority |
| Assign ordinary roles to eligible users | Within explicit grantable-role allowlist | Within explicit allowlist | No automatic application authority |
| Promote user to Normal Admin | Not by default | Authorized protected workflow, with approval rules | Not by default |
| Promote user to Super Admin | No | Only separate elevated-governance workflow, never unrestricted self/service promotion | Not by default |
| Change **default permissions of any application role** | **No** | **Exclusive protected authority**, subject to policy, audit and governance limits | No automatic application authority |
| Add/revoke direct account permissions | Only if explicitly delegated for narrow use cases; default No | Protected authority with target/service restrictions | No automatic application authority |
| View school authentication/security activity | Limited redacted, school-scoped view when implemented and granted | Redacted governance/audit view | Technical logging access per controlled Django operations |
| Manage academic settings, announcements | School-authorized | Inherits School Admin | Not automatically |
| Manage Django framework/admin site | No | No by default | Yes if Django Admin properly configured and restricted |
| View every student's payments/ratings | No blanket access | No blanket access | No automatic custom API access |

### 3.3 Provisioning and separation principles

- The **first application Super Admin** must be established through a separately approved, attributable initial-operator process. Once operational, this Super Admin may create or promote other **Normal Admins** under an approved workflow and audit trail.
- Promoting or provisioning another **Super Admin** requires a stronger governance process (independent approval/recovery policy to be finalized) and cannot be a one-click unlimited escalation.
- School Admins may attach approved ordinary roles (including eligible Treasurer and the single SSG Advisor (Finance Monitor) responsibility) to Student/Instructor accounts. They must not self-assign protected governance authority or modify role templates.
- No user may approve their own account request, assign protected roles to themselves, grant permissions to themselves, remove their own Deny override, or change a role template whose modification would bypass an approved privilege-escalation control.
- Students and instructors retain their original roles when assigned an additional approved role unless a separate authorized removal occurs.
- The last effective application Super Admin must not be silently deactivated, demoted, or stripped of necessary governance permissions; recovery must remain possible.
- Combining Student and Treasurer is permitted as a target use case, but self-benefiting payments, refunds, exemptions and conflicting sign-off actions must be prohibited or independently approved.

### 3.4 Application authorization equation

For an approved active account with at least one assigned active role and an active service:

`Effective = (union of active role grants + active account Grants) - active account Denies`

Every protected action also requires record-level scope checks (self, assigned class, period, specific signatory responsibility, approved reporting scope) and contextual business validation. No role name, requested role, frontend visibility, Django staff status, or Django Superuser flag is itself a bypass of the custom evaluator.

## 4. Primary use cases

| ID | Actor(s) | Use case and expected outcome |
|---|---|---|
| UC-01 | Student/Instructor | Submit registration; create Pending inactive account and linked profile; no roles assigned |
| UC-02 | Normal/Super Admin | Approve eligible application; atomically activate and attach requested base role defaults |
| UC-03 | Normal/Super Admin | Reject request with bounded justification and reviewer attribution |
| UC-04 | Approved account | Sign in/out using secure browser session and CSRF controls; fetch effective capabilities |
| UC-05 | Normal Admin | Assign/remove an eligible ordinary extra role from a Student or Instructor with reason and audit |
| UC-06 | Super Admin | Change a role's default permissions in protected interface; see impact and audit before commit |
| UC-07 | Super Admin | Add/revoke permitted direct user overrides without overriding protected constraints |
| UC-08 | Super Admin | Authorize creation/promotion of a Normal Admin, preserving a valid governance operator |
| UC-09 | Privileged governance operators | Provision/recover another Super Admin only through independently controlled privileged workflow |
| UC-10 | Normal/Super Admin | Review redacted, scope-limited authentication/security activity after dedicated event logging is implemented |
| UC-11 | Instructor | Receive the SSG Advisor (Finance Monitor) responsibility without losing Instructor access |
| UC-12 | Instructor serving as SSG Advisor (Finance Monitor) | View authorized read-only financial overview, reports and transaction history under the **same** responsibility profile |
| UC-13 | Student/Treasurer | Gain Treasurer duties while retaining Student self-service, with financial self-interest restrictions |
| UC-14 | School Admin | Maintain courses, school periods, sections, adviser assignments and valid academic records |
| UC-15 | Treasurer | Record fees/funds/expenses, issue receipts and reconcile allowed ledger views |
| UC-16 | Student/authorized signatory | Request and sign clearance only against actual assignment and active period |
| UC-17 | Instructor/Student | Create rating sheets/invitations, participate in groups and submit/inspect scoped ratings |
| UC-18 | Authorized campus users | Create/read announcements and track their own read state |
| UC-19 | Treasurer/School Admin | Generate and review reports at permitted detail level; separate finalization controls |
| UC-20 | Django Superuser | Perform restricted Django framework maintenance without automatically bypassing custom application security |

## 5. Functional requirements

**Notation:** `SHALL` denotes required behavior for the target release. These are requirements, **not implementation-complete claims**. `P0` is foundational/security-critical; `P1` is core operations; `P2` is deferred/optional pending approval.

### 5.1 Registration, identities and approval

| ID | Priority | Requirement |
|---|---|---|
| FR-REG-01 | P0 | The public registration API SHALL accept only Student or Instructor requests and SHALL reject attempts to request restricted roles or privilege fields. |
| FR-REG-02 | P0 | Registration SHALL atomically create an `accounts` record and linked `users` record with Pending status, inactive flag and no `account_roles`. |
| FR-REG-03 | P0 | Passwords SHALL be hashed; responses/logs SHALL never disclose plaintext passwords, hashes, tokens or whether a school ID is registered beyond the approved anti-enumeration policy. |
| FR-REG-04 | P0 | Only authorized school administrators SHALL list, approve or reject eligible requests; the reviewer SHALL not review themselves. |
| FR-REG-05 | P0 | Approval SHALL verify requested role eligibility, set approval/reviewer metadata, activate the account and assign the appropriate base Student or Instructor role **within one transaction**. |
| FR-REG-06 | P0 | After approval, the account SHALL receive current active base-role defaults by evaluation; individual permission records SHALL NOT be manually generated for each standard registrant. |
| FR-REG-07 | P0 | Rejected requests SHALL remain unauthorized and preserve justified reviewer attribution without exposing private review notes to unauthorized users. |
| FR-REG-08 | P1 | Only an authorized account-provisioning path SHALL create restricted school operators or elevate Admin governance; public registration SHALL never do so. |

### 5.2 Browser authentication, sessions and lifecycle

| ID | Priority | Requirement |
|---|---|---|
| FR-AUTH-01 | P0 | The web app SHALL use Django-backed server sessions and HttpOnly cookies; login, logout and other state changes SHALL enforce CSRF and trusted-origin checks. |
| FR-AUTH-02 | P0 | Authentication SHALL validate password, approved/active status and required account eligibility before issuing a usable application session. |
| FR-AUTH-03 | P0 | Pending, rejected, suspended or otherwise inactive accounts SHALL not gain protected access. |
| FR-AUTH-04 | P0 | Logout SHALL invalidate the authenticated session. Session expiry and session invalidation after security-critical role/account changes SHALL be explicitly defined and tested. |
| FR-AUTH-05 | P0 | Protected APIs SHALL authorize every request on the backend using effective permissions and resource-scope checks; the frontend SHALL never be the sole enforcement point. |
| FR-AUTH-06 | P1 | The system SHALL provide a current-user/permissions endpoint for rendering correct shared dashboard navigation without returning secrets. |
| FR-AUTH-07 | P1 | Invalid login and authentication events SHALL be safely rate-limited and logged after an approved authentication-event contract is implemented. |

### 5.3 Hybrid dynamic access control and role templates

| ID | Priority | Requirement |
|---|---|---|
| FR-ACL-01 | P0 | The system SHALL resolve eligible permissions from the union of active role grants, direct Grants and overriding direct Denies, with deny-by-default behavior. |
| FR-ACL-02 | P0 | A single account SHALL support multiple assigned roles; removing a role SHALL remove its contribution but preserve other valid role/direct grants unless an active Deny blocks access. |
| FR-ACL-03 | P0 | The system SHALL maintain role defaults centrally in `role_permissions`; an authorized template change SHALL affect future permission evaluations for all holders, without creating per-account duplicate grants. |
| FR-ACL-04 | P0 | Only application Super Admin governance authority SHALL be able to **create, enable, disable or revoke role-default permission grants**, through a protected workflow. Normal Admin SHALL NOT modify role defaults. |
| FR-ACL-05 | P0 | All role-template changes SHALL show affected role, exact permission-code changes, potential affected accounts and active override interactions before confirmation. |
| FR-ACL-06 | P0 | Role default changes and individual overrides SHALL be atomic with attributable audit entries; audit failure SHALL roll back the mutation. |
| FR-ACL-07 | P0 | The system SHALL enforce an explicit service/permission/recipient allowlist; permission-management authority alone SHALL NOT imply unrestricted delegation. |
| FR-ACL-08 | P0 | Protected governance codes, Admin elevation, Super Admin creation/recovery and last-operator actions SHALL use a separate approved privileged workflow, not ordinary permission mutations. |
| FR-ACL-09 | P0 | The system SHALL prevent self-approval, direct self-grants, removal of self-Denies and unauthorized edits to roles assigned to the acting administrator. Any narrowly necessary exception SHALL require independently reviewed governance design. |
| FR-ACL-10 | P0 | The system SHALL detect incompatible simultaneous roles or duties and prohibit a role addition that causes an unapproved conflict. |
| FR-ACL-11 | P0 | All list/detail/export APIs SHALL enforce ownership/assignment/period scopes; no global permission code SHALL authorize access to every record by itself. |
| FR-ACL-12 | P1 | Role defaults, account overrides and effective access SHALL be inspectable through a permission-aware dashboard with audit/change history, subject to viewer scope. |
| FR-ACL-13 | P0 | Existing role/permission catalogue and C2A planner outputs SHALL remain non-authoritative for live grants until a revised versioned manifest is reviewed and initialized separately. |
| FR-ACL-14 | P1 | The application SHALL be able to express Student+Treasurer, Instructor+SSG Advisor (Finance Monitor), Instructor+Admin and Admin+governance profiles without inventing duplicate user identities or splitting SSG Advisor and Finance Monitor into separate roles. |

### 5.4 Account role assignment and admin delegation

| ID | Priority | Requirement |
|---|---|---|
| FR-ADM-01 | P0 | An appropriately authorized Normal Admin SHALL be able to assign/revoke **ordinary approved** roles to eligible Students and Instructors, subject to recipient-role and conflict rules. |
| FR-ADM-02 | P0 | A Super Admin SHALL be able to establish additional Normal Admins under an explicitly protected and auditable promotion/provisioning process. |
| FR-ADM-03 | P0 | No ordinary Admin SHALL be able to assign or grant application Super Admin authority to themselves or another account via the ordinary assignment service. |
| FR-ADM-04 | P0 | Super Admin promotion, removal, last-operator recovery and governance privilege changes SHALL require a separate protected, independently reviewable authorization process. |
| FR-ADM-05 | P0 | Role changes SHALL record acting account, target account, role, before/after state, reason and event time within approved audit contracts. |
| FR-ADM-06 | P1 | Normal Admin SHALL be able to inspect eligible accounts' assigned roles and effective abilities, but SHALL not access sensitive technical secrets or unrestricted governance change interfaces. |
| FR-ADM-07 | P1 | Normal Admin MAY receive an explicit read-only school-scoped security/authentication-log permission. This SHALL not confer role-template editing or full technical system configuration. |
| FR-ADM-08 | P0 | Users with both Student and Treasurer roles SHALL be prevented from recording, approving or exempting their own obligations where a conflict exists. |
| FR-ADM-09 | P1 | Assignment to the single SSG Advisor (Finance Monitor) responsibility SHALL require explicit eligibility, documented duration/revocation rules and a reviewed least-privilege read-only grant set. |

### 5.5 Academic services

| ID | Priority | Requirement |
|---|---|---|
| FR-ACA-01 | P1 | Authorized school staff SHALL maintain courses, school years, school periods, year/section definitions and valid academic profiles. |
| FR-ACA-02 | P1 | Instructors SHALL see only students and teaching assignments linked to their active adviser/subject appointments and relevant periods. |
| FR-ACA-03 | P1 | Students SHALL see only their own academic profile and permitted public academic catalogue. |
| FR-ACA-04 | P1 | Modifying historical academic definitions SHALL preserve consistency with existing records and avoid silent reassignment of students. |

### 5.6 Finance and the SSG Advisor (Finance Monitor) responsibility

| ID | Priority | Requirement |
|---|---|---|
| FR-FIN-01 | P1 | Authorized Treasurers SHALL manage applicable organization fee schedules and attributable payment, receipt, fund and expense records. |
| FR-FIN-02 | P1 | Students SHALL view only their own permitted payment records and receipts. |
| FR-FIN-03 | P1 | The SSG Advisor (Finance Monitor) responsibility SHALL expose **View Financial Overview**, **View Financial Reports** and **View Transaction History** as three distinct, scoped, read-only approved abilities under the same responsibility profile. |
| FR-FIN-04 | P0 | SSG Advisor (Finance Monitor) abilities SHALL never grant payment recording, receipt issuance, ledger modification, expense editing, refund, exemption or role-management powers. |
| FR-FIN-05 | P0 | Transaction History SHALL have an approved scope, redaction rules and export limits; a generic raw ledger permission SHALL not automatically be treated as safe financial monitoring. |
| FR-FIN-06 | P0 | A Treasurer who is also a Student SHALL not be able to act on their own fee/payment/exemption records without independent safeguards. |
| FR-FIN-07 | P1 | SSG Advisor and Finance Monitor SHALL refer to the **same** approved monitoring responsibility; appointment SHALL NOT imply Treasurer write access or a second independent role. Any advisory actions beyond the three named financial views require separate future approval. |
| FR-FIN-08 | P1 | Financial report generation SHALL validate period and source data; finalization/export SHALL remain blocked until maker/checker, immutability, retention and disclosure rules are approved. |

### 5.7 Clearance

| ID | Priority | Requirement |
|---|---|---|
| FR-CLR-01 | P1 | Students SHALL submit and track eligible subject/organization clearance requests for valid periods. |
| FR-CLR-02 | P0 | An Instructor or authorized signatory SHALL only sign requests matching an actual current teaching, adviser, Treasurer or fixed-signatory appointment. |
| FR-CLR-03 | P1 | School Admins SHALL maintain subject/teaching assignments and signatory appointments, subject to separation-of-duties controls. |
| FR-CLR-04 | P0 | Signature access and reuse SHALL be bound to the owner and historical evidence; no raw signature image SHALL be disclosed through broad admin permissions. |
| FR-CLR-05 | P2 | Clearance message sending SHALL remain unavailable until recipient/thread/period privacy semantics are approved for the existing schema. |

### 5.8 Group rating

| ID | Priority | Requirement |
|---|---|---|
| FR-RAT-01 | P1 | Instructors SHALL create and manage rating sheets only for their assigned classes and teaching periods. |
| FR-RAT-02 | P1 | Eligible Students SHALL respond to their own leader invitations and manage groups through verified accepted invitations. |
| FR-RAT-03 | P0 | Ratings SHALL enforce group/sheet/criteria consistency and prevent self-rating and duplicate submissions. |
| FR-RAT-04 | P0 | Rating results SHALL be disclosed only to the student or authorized instructor within approved privacy and aggregation rules. |

### 5.9 Announcements, read tracking and reports

| ID | Priority | Requirement |
|---|---|---|
| FR-COM-01 | P1 | Authorized School Admins SHALL create and update attributable campus announcements. |
| FR-COM-02 | P1 | Authorized users SHALL read eligible announcements and track only their own read state. |
| FR-COM-03 | P0 | Public publication/audience policy SHALL be defined before exposing all stored announcements publicly; the ERD does not supply general audience/status fields. |
| FR-COM-04 | P1 | Treasurer/School Admin report access SHALL distinguish draft/final reports, aggregates, transaction-level data and export rights. |

### 5.10 Authentication event monitoring, authorization auditing and Django Superuser

| ID | Priority | Requirement |
|---|---|---|
| FR-AUD-01 | P0 | Role, template and override changes SHALL be attributable and audited atomically, using the approved access-audit contract. |
| FR-AUD-02 | P0 | Authentication events (e.g., successful/failed login, logout, account lock or session revocation) SHALL have a defined, secure event source and retention policy; they SHALL NOT be mislabeled as existing permission-mutation audit records. |
| FR-AUD-03 | P1 | Normal Admin's authentication-log view SHALL be read-only, redacted and limited to eligible school account activity; full technical diagnostics remain separately controlled. |
| FR-AUD-04 | P1 | Super Admin SHALL inspect authorized governance changes and security events without obtaining unrestricted business data or secrets. |
| FR-AUD-05 | P0 | Audit access SHALL avoid password hashes, reset tokens, session secrets, full request bodies and sensitive unapproved business content. |
| FR-DJA-01 | P0 | The project SHALL provide a supported, reviewed Django Superuser provisioning method compatible with the custom `Account` model and authentication backend. |
| FR-DJA-02 | P0 | Django Superuser SHALL be a **separate framework privilege**, not an implicit `account_roles` entry and not an automatic custom permission bypass. |
| FR-DJA-03 | P0 | If current custom Account model lacks required Django framework fields/methods/admin integration, the team SHALL first document the exact compatibility gap and seek approval for any migration or code adaptation. |
| FR-DJA-04 | P0 | Django Admin SHALL allow only explicitly registered, reviewed maintenance functions; direct edits to protected role, permission and audit records SHALL be disabled or routed through trusted audited services. |
| FR-DJA-05 | P0 | Django Superuser creation/recovery SHALL use an independent, authenticated and attributable technical procedure with emergency access and secrets-handling safeguards. |
| FR-DJA-06 | P0 | The initial application Super Admin bootstrap SHALL not assume a Django Superuser automatically satisfies the custom first-operator audit actor requirement. |
| FR-DJA-07 | P1 | Technical framework actions and changes to application authority SHALL have clearly separated policies, logs and recovery procedures. |

### 5.11 Shared dashboard and interfaces

| ID | Priority | Requirement |
|---|---|---|
| FR-UI-01 | P1 | The application SHALL use one shared `DashboardLayout` with context-sensitive navigation based on effective permissions. |
| FR-UI-02 | P1 | Normal Admin SHALL see school-management, approval, eligible role assignment and limited monitoring screens. |
| FR-UI-03 | P1 | Super Admin SHALL additionally see role-default templates, service permissions, per-user overrides, effective-access inspection and security audit interfaces. |
| FR-UI-04 | P1 | A user with multiple roles SHALL use one account/session and see the union of authorized features, without separate logins or duplicate profiles. |
| FR-UI-05 | P0 | Screens SHALL clearly distinguish **Change Role Default** (affects all role holders) from **Change This User's Permissions** (one account). |
| FR-UI-06 | P1 | All privileged changes SHALL show a confirmation summary, privilege impact and meaningful denial/error messages; UI controls SHALL never substitute for server enforcement. |

## 6. Data requirements and ERD compatibility

### 6.1 Reuse of existing schema

| Existing table | Requirement support |
|---|---|
| `accounts`, `users` | Identity, registration status, review attribution, account eligibility |
| `roles` | Base roles and future approved responsibility/governance roles |
| `account_roles` | Multiple simultaneous roles; assigned-by attribution; unique account/role pair |
| `services`, `permissions` | Explicit service/action catalogue |
| `role_permissions` | Editable default permissions for each role, without account duplication |
| `account_permissions` | Individual Grant/Deny exceptions |
| `access_audit_logs` | Existing access-governance mutation auditing, within its approved payload limitations |

### 6.2 Representation gaps — no silent schema changes

1. **Django Superuser compatibility:** the custom Account model's existing framework fields and permission methods need focused inspection; do not assume `createsuperuser`/Django Admin work solely because `create_superuser` exists in a manager.
2. **Authentication event logs:** existing `access_audit_logs` primarily represent authorization mutations, not comprehensive login/session events; define storage, redaction, retention and access before exposing a log viewer.
3. **Role/profile semantics:** Normal Admin/Super Admin are proposed composites; actual governance-role naming and two-profile selection must be reconciled with the earlier C1 manifest.
4. **Additional responsibility:** SSG Advisor (Finance Monitor) is **one** proposed role/profile, not two. Review its exact read-only permissions, eligibility and whether to assign the proposed `SSG Advisor` role or equivalent narrow account overrides; a new role may use `roles` without a new table if approved.
5. **Delegation policy:** existing B2 per-service recipient cross-product is too coarse for some mixed-role recipients, especially Student+Treasurer and Instructor+Admin; no widening of scopes to bypass current refusal is permitted.
6. **Two-party approval / grant expiry:** not directly represented by the current schema; needs a reviewed implementable workflow, possibly schema changes only after authorization.
7. **Default role changes:** editing a role affects all holders and could elevate the actor via another assigned role; protected governance mutation rules must explicitly address that risk.
8. **Object scopes:** evaluator has global permission semantics; record ownership, class, period, and financial conflicts must be checked in each business service.

### 6.3 ERD protection rule

The 42-table main DBML and auth DBML SHALL remain read-only until any schema revision is explicitly approved. No migration, Django `PermissionsMixin`, new Superuser field, account status flag, login event table, or delegation approval table may be added by interpreting this SRS alone as approval. Model changes, migration SQL, data impacts and rollback plans require separate review.

## 7. Nonfunctional requirements

| ID | Category | Requirement / proposed acceptance target |
|---|---|---|
| NFR-SEC-01 | Authorization | Every protected API path is deny-by-default with server-side permission and row-scope tests, including cross-user, role-combination and stale-session cases. |
| NFR-SEC-02 | Authentication | HTTPS in production; secure HttpOnly SameSite cookies, CSRF, rate limiting, safe password hashing and no browser localStorage credential tokens. |
| NFR-SEC-03 | Privileged safety | No unauthorized escalation, no public privileged role registration, no Django Superuser bypass of custom application permission checks. |
| NFR-AUD-01 | Accountability | Security mutations are atomic with bounded audit events; audit write failure rolls back the security mutation. |
| NFR-PRV-01 | Privacy | Collect only necessary personal/financial information; redaction, access scoping, retention and disclosure reviewed before deployment. |
| NFR-REL-01 | Reliability | System shall fail closed on permission policy errors; idempotent operations must not create duplicate role assignments or audit records. |
| NFR-PER-01 | Performance | Proposed target: 95% of ordinary dashboard/API reads respond within 2 seconds under an agreed realistic campus load; benchmark before acceptance. |
| NFR-USA-01 | Accessibility | Aim for WCAG 2.2 AA for essential web flows; keyboard use, meaningful labels, clear errors and responsive layouts. |
| NFR-OPS-01 | Recovery | Define backup/restore cadence, tested recovery, audit retention, administrator recovery and incident response before production go-live. |
| NFR-MNT-01 | Maintainability | Keep modular Django services, reusable React components, versioned permission catalogue, unit/integration tests and change documentation. |
| NFR-TEST-01 | Verification | All role-combination and privilege-escalation flows have positive and negative automated tests, using disposable databases for data-writing suites. |

*Numeric performance and operational targets are proposals pending campus deployment sizing; they are not measured current performance.*

## 8. End-to-end acceptance scenarios

| Test ID | Scenario | Pass condition |
|---|---|---|
| AT-01 | Register Student/Instructor | Pending inactive account + profile; no role assignment; duplicate/privilege attack denied |
| AT-02 | Admin approves registration | Single committed approval/activation/base-role assignment and reviewer attribution; default access available after login |
| AT-03 | Instructor gains SSG Advisor (Finance Monitor) responsibility | Teacher role preserved; only approved read-only financial-monitoring rights added; revocation retracts those rights |
| AT-04 | Instructor uses SSG Advisor (Finance Monitor) views | Through the **same** assigned responsibility, financial overview/reports/scoped history remain read-only; payment/expense write API denied |
| AT-05 | Student gains Treasurer role | Student and Treasurer menus visible where authorized; own-finance conflicting actions refused |
| AT-06 | Super Admin changes Instructor role default | Impact preview; change committed with audit; every applicable Instructor holder's effective permission changes; protected grant rules enforced |
| AT-07 | Normal Admin attempts role-default edit | Denied even if UI request is forged; no state change or fake success audit |
| AT-08 | Super Admin creates a Normal Admin | Protected promotion with attribution; new account gets school Admin rights but no governance role |
| AT-09 | Normal Admin attempts Super Admin promotion | Denied; no governance authority granted |
| AT-10 | Super Admin attempts self-grant/last-admin removal | Denied or routed through separately approved governance recovery, never silently executed |
| AT-11 | Multi-role account with Deny override | Direct Deny wins even if a second role grants same code; authorization checked again on next request |
| AT-12 | Normal Admin monitors auth activity | Only redacted, authorized campus-scoped events shown, no passwords/tokens or unrestricted security diagnostics |
| AT-13 | Django Superuser logs into Django Admin | Only reviewed maintenance functions available; no automatic CTU-G role grants/custom bypass |
| AT-14 | Catalogue planner after SRS change | Reports previous C1 manifest incompatibilities as unresolved; does not apply existing 82-code/96-binding baseline automatically |
| AT-15 | Audit insertion fails during role change | Security transaction rolled back; role/override state unchanged |
| AT-16 | Instructor accesses other class / Student other payment | Server returns denied/filtered result regardless of role membership or hidden buttons |

## 9. Project architecture implications and delivery sequence

| Stage | Deliverable | Entry gate |
|---|---|---|
| R1 — Requirements adoption | Review/approve Admin presets, exact role composition, finance monitoring, role assignment rights, Django Superuser separation | Explicit owner sign-off; no code or DB writes |
| R2 — Architecture reconciliation | Compare SRS against C1 82 codes/96 bindings, B2 restrictive role policies and C2A manifest; publish precise changes | R1 decisions |
| R3 — Governance/bootstrap design | First real application Super Admin identity, independent attribution, governance changes, last-operator invariant, Django Superuser integration analysis | Security approval |
| R4 — Controlled catalogue readiness | Revised versioned manifest; read-only planner; independent metadata apply and grant approval stages | Reviewed manifest/actor/audit contract |
| R5 — Trusted role assignment/approval and login | Normal Admin account approvals, role assignment, session login/logout, CSRF, session revocation, event logging | Protected role workflows and secure service tests |
| R6 — Shared dashboard | Role-aware navigation; Normal Admin and Super Admin consoles; permission templates and individual override UI | End-to-end authorization APIs |
| R7 — Campus modules | Academic, finance, clearance, group rating, announcements, reports, with object policy tests | Module-by-module schema/workflow approval |
| R8 — Release validation | Security, privacy, performance, user acceptance, backups, deployment and documentation | Successful integration and acceptance tests |

**Do not merge R3/R4 into a blanket “createsuperuser and seed every permission” command.** Django Superuser provisioning and initial custom Super Admin authority are distinct problems and require deliberate reconciliation.

## 10. Open decisions requiring explicit approval

| Decision | Question / suggested direction |
|---|---|
| OD-01 | Confirm that **Normal Admin = Admin**, **Super Admin = Admin + protected governance role**, and exact persisted role name (keep `Technical Super Admin` or rename through approved process). |
| OD-02 | Define if a Super Admin can elevate another Super Admin alone; recommendation: independent approval and last-operator safeguards. |
| OD-03 | Define the precise list of assignable ordinary roles for Normal Admin; include eligible Treasurer and the **single** SSG Advisor (Finance Monitor) role, with conflict checks. |
| OD-04 | **Terminology resolved:** SSG Advisor and Finance Monitor are the same responsibility, not separate roles. Confirm the recommended canonical `SSG Advisor` role or equivalent narrow account overrides, and approve any additional advisor duties separately. |
| OD-05 | Approve the three SSG Advisor (Finance Monitor) views, dataset filters, redactions, report maturity, transaction history scope and retention/export rules. |
| OD-06 | Define Student+Treasurer conflict rules (self-payments, exemption, receiving/issuing receipt) and Instructor+Admin conflict rules. |
| OD-07 | Decide which redacted authentication events a Normal Admin may see, and approve event storage/retention without overloading access-control mutation audit. |
| OD-08 | Set exact Super Admin limits for editing any role default, including their own Admin/governance role and safeguards for globally disruptive changes. |
| OD-09 | Define first application Super Admin identity/bootstrap attribution, governance approval evidence and recovery. |
| OD-10 | Decide Django Superuser integration path after inspecting the custom Account model; any migrations require separate authorization. |
| OD-11 | Set direct Grant/Deny override governance and whether Normal Admin receives any narrowly delegated override authority. |
| OD-12 | Reconcile all affected C1 D01-D18 policy proposals and freeze a new approved catalogue/grant manifest; keep all activation and database writes blocked until then. |
| OD-13 | Determine session revocation timing after role/default/override changes and account suspensions. |
| OD-14 | Approve performance, privacy, audit-retention, operational recovery and deployment acceptance targets. |

## 11. Requirement-to-source traceability and change impact

| Requirement group | Primary basis | Existing implementation dependency |
|---|---|---|
| Admin profiles, role defaults, multi-role assignment | Owner's 7 Nov 2026 clarified use cases | `roles`, `account_roles`, `role_permissions`, `account_permissions`; B2 restrictions must be reconciled |
| Registration and approval | Existing project workflow and ERD | Current registration API; future atomic approval/assignment services |
| Django Superuser separation | Owner requirement and Django custom-Account integration need | Custom user manager/model, Django Admin and security-reviewed framework permissions |
| SSG Advisor (Finance Monitor) read-only finance oversight | Owner's clarification that SSG Advisor = Finance Monitor, plus the three named financial views and finance/report ERD | C1 finance/reports permissions; new safe transaction-history scope may be required |
| Audit and integrity | Existing Phase 1H-B1/B2 security architecture | `access_audit_logs` and safe audit payload contracts; auth-event logging not implemented |
| Campus modules | Main ERD and C1 catalogue proposal | Module-specific model/view/services and object authorization, largely future work |

**Explicit change impact on C1/C2A:** The 10-service/82-code/96-binding manifest remains a valuable **historical planning baseline**, not the approved implementation target. It must be revisited to add/adjust Admin profiles, the **single SSG Advisor (Finance Monitor)** responsibility, finance-monitoring permissions and school authentication-log viewing. The old C1 assumption that `Admin` and `Technical Super Admin` must not be co-assigned is intentionally superseded by this **proposed** composite Super Admin profile, but code changes require tests and specific approval. B2's restrictions on reserved roles and assigned-role edits must never be relaxed as a quick fix.

## 12. Acceptance and sign-off

This SRS is suitable for stakeholder review, not authorized deployment. Recording an approved version requires a named project owner, review date, accepted revision/digest, decisions OD-01 through OD-14 as applicable, and a mapping to approved implementation tasks. Any change affecting authorization, account provisioning, finance, ERD or Django framework administration requires impact analysis and fresh regression/security tests.

| Reviewer | Decision | Date / evidence |
|---|---|---|
| Project owner | Pending | — |
| Security/architecture reviewer | Pending | — |
| University operations stakeholder | Pending | — |

---

**End of SRS v0.3 — Draft for review.**
