# CTU-G Workspace
## Software Requirements Specification (SRS)

**Document ID:** CTUG-SRS-001  
**Version:** 0.4 — Academic Period, Student Semester Onboarding, SSG Fee and WF-08 Group Rating Reconciliation Draft  
**Date:** 17 November 2026  
**Project:** CTU-G Workspace — Cebu Technological University, Ginatilan Campus  
**Status:** **PROPOSED FOR REVIEW — NOT IMPLEMENTATION OR DATABASE-WRITE APPROVAL**  
**Maintainer:** CTU-G Workspace Project Team  
**Repository destination (proposed):** `docs/requirements/CTUG_Workspace_SRS_v0.4.md`

> **Change-control notice.** This v0.4 draft preserves the v0.3 access-control architecture and adds owner-selected design requirements for academic-period activation, Student Semester Onboarding, verified semester organizational fees, clearance preparation, and **WF-08 Group Rating**. It reconciles the updated 13-category Workflow map and Use Case Specification v0.4.1. All new business workflows and scoring rules are **proposed, not approved for implementation**. This document does **not** modify the official ERD, migrations, source code, deployed services, permissions, or live database. Historical test reports are not new verification evidence.

---

## Document control

| Field | Record |
|---|---|
| Revision | v0.4 draft (17 Nov 2026) + owner-directed administrator-authority alignment (18 Nov 2026); **review draft**, not an implementation/release authorization |
| Supersedes | v0.3 SRS draft for documentation review only; no changes to databases, permissions, existing software or approval status |
| Previous design reference | `docs/phase1h-c1-permission-catalogue-governance-proposal.md` (C1 v1; now requires reconciliation) |
| Database reference | `docs/database/full_schema.dbml`; `docs/database/schema.dbml` — read-only contracts |
| Related implementation | Phase 1H-A evaluator; 1H-B1 audit; 1H-B2 guarded mutation services; 1H-C2A read-only catalogue planner |
| Current evidence | v0.3 quoted an older 286-test report; latest implementation status must be re-inspected against current code and Workflow Catalogue. No tests were run to create this SRS. |
| Approval authority | Project owner and appointed academic/security reviewers (to be recorded) |
| Classification | Internal project requirements; no student data or secrets |
| Finance companion | `docs/SRS/CTU-G_Workspace_SRS_v0.4_COMPANION_PROPOSALS.md` — **FR-FIN-09–14 reserved historical candidate IDs, preserved as proposed text** |
| Use-case reference | `docs/use_cases/CTU-G_Workspace_Use_Case_Specification_v0.4.1.md` — proposed, not approved |
| Workflow reference | Owner-supplied category map, 17 November 2026; **WF-08 = Group Rating**, WF-08 subflow IDs unassigned |

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
| Technical Super Admin | Canonical name for the **single application-level Super Admin tier**, inheriting School Admin operations plus separately protected governance authority; distinct from Django Superuser. |
| Academic Period | Campus-scoped School Year + Semester combination with a designated lifecycle; exactly one Active period is the proposed operating rule. |
| Student Semester Onboarding | Proposed period-specific confirmation of Student academic details through the student-facing **Semester Academic Information Setup** page; not an enrollment-management authority. |
| Verified academic eligibility | Enrollment/subjects verified using CTU's main system or an expressly authorized verification procedure; self-report alone is not proof. |
| Organizational fee obligation | A fee assessment tied to a verified eligible Student, academic period and fee type under an approved rate/exemption policy, independent of login timing. |
| Hybrid Group Management | WF-08 formation: Instructor selects leaders, accepted leaders invite classmates, and Instructor resolves placement and finalizes the roster. |
| Exact category point distribution | Per-rater allocation of **exactly** the Instructor-set point budget for each category across eligible groupmates; self is excluded and deliberate zero allocations are allowed. |

### 1.5 Source hierarchy

The user's current clarified administrator, multi-role and Group Rating design selections control **intended behavior** (pending approval). Existing ERD/model structures control what can currently be represented. Existing code and test evidence control what is **implemented**. Earlier C1 role defaults and catalogue counts remain proposals for reconciliation, not approved runtime configuration. Conflicts must be recorded and resolved through change control, not silently edited.

### 1.6 Workflow Category map — owner-supplied 17 November 2026

| ID | Category | Group | Subflows |
|---|---|---|---|
| WF-01 | Registration & Authentication | Group A | 6 |
| WF-02 | Account Management | Group A | 6 |
| WF-03 | Access Control Management | Group A | 6 |
| WF-04 | Profile Management | Group A | 5 |
| WF-05 | Academic Information | Group B | 4 |
| WF-06 | Clearance Management | Group B | 5 |
| WF-07 | SSG Financial Management | Group B | 8 |
| **WF-08** | **Group Rating** | **Group B** | **To be defined** |
| WF-09 | Announcements & Notifications | Group B | 5 |
| WF-10 | Account Concerns & Support | Group B | 4 |
| WF-11 | System Administration & Configuration | Group C | 4 |
| WF-12 | Audit, Security & Monitoring | Group C | 5 |
| WF-13 | Reporting & Document Generation | Group C | 4 |

**Traceability rule:** Existing SRS `UC-01`–`UC-20` and `FR-*` identifiers remain unchanged. `UC-17` is a **use-case ID**, not the workflow number. Group Rating belongs to **WF-08**, with **no approved WF-08.xx IDs**. New requirements below extend existing SRS categories; do not add catalogue subflows without owner approval. References to later-category suffixes must be confirmed against the current full Workflow Catalogue before use in an implementation ticket.

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
| Account approval and role assignment | Historical draft status; current implementation and release gates require inspection. Do not infer WF-02 completion from this SRS. |
| Login/logout/sessions | Prior draft status is stale: WF-01.06 session-expiry/security work has reported tests and owner approval; confirm current code and complete authentication release status before claiming end-to-end readiness. |
| Permission evaluator and transactional access audit | Implemented and previously tested |
| Permission mutation services | Implemented, but live changes intentionally gated |
| Catalogue | C1 proposal of 10 services, 82 codes and 96 bindings; C2A planner implemented; no live seed |
| Admin profiles / Django Superuser integration | New/changed requirements; implementation pending |
| Campus business modules / dashboard | WF-05–08 proposed business rules and integrations; production/implementation status not confirmed by this SRS. |

## 3. Roles, administrator profiles and authority boundaries

### 3.1 Application roles and composable profiles

The application SHALL support multiple active roles on one account. The current initialized roles are `Student`, `Instructor`, `Treasurer`, and `Admin`. Additional responsibility roles are **proposed**, not yet initialized. Use **Technical Super Admin** as the canonical application-tier name; the exact stored role, provisioning and protected grant contracts still require reconciliation.

| User profile | Proposed role composition | Intended rights |
|---|---|---|
| Student | Student | Own student-facing data and services only |
| Instructor | Instructor | Assigned classes, teaching, clearance and rating services |
| Student Treasurer | Student + Treasurer | Own student tools plus approved SSG Treasurer operations; conflict-of-interest controls required |
| Instructor SSG Advisor (Finance Monitor) | Instructor + SSG Advisor (proposed), or equivalent separately approved narrow overrides | Instructor rights plus **one** financial-monitoring responsibility: scoped View Financial Overview, View Financial Reports, and View Transaction History; no Treasurer write powers |
| Normal Admin | Instructor + Admin (promotion of an approved Instructor) | Instructor permissions plus School Admin school operations; **no Access Control Management or role assignment** |
| Technical Super Admin | Instructor + Admin + Technical Super Admin (privileged role assignment by Django Superuser only) | Inherits School Admin operational permissions through Admin plus separately authorized access-control governance; cannot assign/revoke the Technical Super Admin role |
| Instructor + Normal Admin | Instructor + Admin | Both job duties, subject to separation-of-duties rules |
| Instructor + Super Admin | Instructor + Admin + Technical Super Admin | Intended multi-role composition; must be installed via an audited Django-Superuser-only protected configuration action, subject to verified eligibility and last-operator rules |

**Interpretation:** “School Admin” and “Technical Super Admin” are **two application administrative tiers**, not merely two independent individual permission codes. Their implementation is proposed as role composition to reuse the existing schema; the protected role name and compatibility rules remain an approval decision. Having an Admin role does not confer automatic global permission-management powers.

### 3.2 Division of responsibility

| Activity | Normal Admin | Super Admin (application) | Django Superuser |
|---|---|---|---|
| Review ordinary registration | Allowed by approved school permission | Inherits school rights | No automatic application authority |
| Assign ordinary roles to eligible users | No | With exact effective permission and eligible target | Authorized Django administrative configuration procedure |
| Promote approved Instructor to School Admin | No | Yes, through approved protected role assignment | Yes, through protected audited Django configuration |
| Promote approved Instructor to Technical Super Admin | No | **No**, including self and other accounts | **Exclusive Django Superuser authority**, via an approved protected and audited procedure |
| Change **default permissions of any application role** | No | Governed permission-management workflow and effective-permission checks | Protected audited configuration authority; no implicit ordinary Workspace API bypass |
| Add/revoke direct account permissions | No | Governed permission-management workflow, eligible target and deny precedence | Protected audited configuration authority; no implicit ordinary Workspace API bypass |
| View school authentication/security activity | Limited redacted, school-scoped view when implemented and granted | Redacted governance/audit view | Technical logging access per controlled Django operations |
| Manage academic settings, announcements | Authorized school operation | Inherits via Admin assignment | Protected administrative configuration authority; record-scope and audit safeguards apply |
| Manage Django framework/admin site | No | No by default | Yes if Django Admin properly configured and restricted |
| View every student's payments/ratings | No blanket access | No blanket access | No automatic custom API access |

### 3.3 Provisioning and separation principles

- **Administrator onboarding:** an eligible person registers through the ordinary Instructor workflow (WF-01.02), obtains independent approval under WF-02.03, and keeps the Instructor role. Technical Super Admin may then grant/revoke the School Admin (`Admin`) role through WF-03.01; the Django Superuser may do so through a protected audited configuration action. There is no separate public registration path for either administrative tier.
- **Exclusive elevation:** only an authenticated Django framework Superuser may grant or revoke the Technical Super Admin role for an existing eligible approved Instructor through a reviewed, attributable, protected configuration procedure. The target also needs `Admin` membership and explicit governance permissions; the original Instructor role is retained. An application Technical Super Admin cannot elevate themselves or anyone else to Technical Super Admin.
- School Admin cannot assign/revoke *any* account role, including ordinary Treasurer/SSG Advisor roles, or manage default/direct permissions. Technical Super Admin may handle eligible ordinary roles and School Admin role assignments under approved governance; Django Superuser has protected full configuration authority over role records. Eligibility, separation-of-duties and audit checks still apply.
- No user may approve their own account request, assign protected roles to themselves, grant permissions to themselves, remove their own Deny override, or change a role template whose modification would bypass an approved privilege-escalation control.
- Students and instructors retain their original roles when assigned an additional approved role unless a separate authorized removal occurs.
- The last effective application Super Admin must not be silently deactivated, demoted, or stripped of necessary governance permissions; recovery must remain possible.
- Combining Student and Treasurer is permitted as a target use case, but self-benefiting payments, refunds, exemptions and conflicting sign-off actions must be prohibited or independently approved.

### 3.4 Application authorization equation

For an approved active account with at least one assigned active role and an active service:

`Effective = (union of active role grants + active account Grants) - active account Denies`

Every protected action also requires record-level scope checks (self, assigned class, period, specific signatory responsibility, approved reporting scope) and contextual business validation. No role name, requested role, frontend visibility, Django staff status, or Django Superuser flag is itself a bypass of the custom evaluator.

### 3.5 Owner-directed Django Superuser and administrator-role policy (18 November 2026; proposed implementation)

**Requirement authority:** The project owner specified this target role model on 18 November 2026. It governs the **revised documentation proposal**, not the currently deployed application's behavior. Do not imply current Django Admin supports these writes: the inspected Django Admin is read-only and the existing protected executor still requires another Admin account and independent signatures.

- **Django Superuser:** framework-level highest **administrative configuration authority** over system data and account roles. Can add or remove Student, Instructor, Treasurer, School Admin (`Admin`), and Technical Super Admin roles, subject to reviewed, authenticated, auditable, safe configuration operations; only Django Superuser can grant/revoke Technical Super Admin. No automatic right to bypass the existing Workspace API evaluator through `is_superuser`.
- **Technical Super Admin (Super Administrator):** no independent public registration; a previously approved Instructor retains Instructor and additionally holds Admin + Technical Super Admin. Authorized for Access Control Management through precise permission grants, and may grant/revoke School Admin for other eligible approved Instructors. Cannot grant/revoke Technical Super Admin.
- **School Admin (Normal Administrator):** no independent public registration; an approved Instructor retains Instructor and receives Admin from an authorized Technical Super Admin or Django Superuser. Performs school operations; cannot manage role assignments, role-default permissions or account overrides.
- **Identity/eligibility separation:** Instructor registration (WF-01.02) and approval (WF-02.03) remain the normal path to eligible administrator accounts. Student and Instructor base-role changes by a Django Superuser need explicit integrity checks; they are not a public re-registration bypass. The first School Admin/first Technical Super Admin bootstrap remains a distinct unresolved security transition.
- **Pending engineering decisions:** whether trusted Django Admin actions or a superuser-authenticated command are the reviewed configuration surface; how the existing protected two-Admin/three-signer bootstrap, executor storage, P3B/P4 compatibility, signed receipts, operator recovery and last-operator protection adapt. No direct SQL, unbounded model editor, automatic role grant, schema installation or release change is authorized by this SRS amendment.

Related decision register: D-79, D-80, D-81, D-82, D-85, D-88, D-89, D-90, and proposed D-91/D-92 in WF-03.01. **Implementation status (18 Nov 2026, WF-03.01 staged, local development only):** the Technical Super Admin School Admin assignment/revocation, the Django-Superuser-exclusive Technical Super Admin grant/revoke command (disposable test database only), and the role-change session epoch are implemented and tested; ordinary roles, general superuser data administration, development-database use (D-93/D-95; the D-85 P3B prerequisite is implemented for local development), executor parity and production remain not implemented. Permission Catalogue v2.1 (D-89, 19 Nov 2026) is a validated specification overlay binding ordinary-role management to the Technical Super Admin instead of the School Admin, and Permission Catalogue v2.2 (D-103) moves School Admin's two read-only access_control defaults to the Technical Super Admin, so School Admin holds no Access Control Management default; neither is provisioned. See WF-03.01 in the System Workflow Catalogue. Historical integrity-pinned documents are preserved; update their versioned manifests and hashes only with a separately reviewed contract migration.

## 4. Primary use cases

| ID | Actor(s) | Use case and expected outcome |
|---|---|---|
| UC-01 | Student/Instructor | Validate and stage identity credentials, verify recipient email via OTP, then atomically create exactly one **Pending/inactive** account and profile without a role/session; School Information is not mandatory on the proposed Student registration form. |
| UC-02 | Normal/Super Admin | Approve eligible application; atomically activate and attach requested base role defaults |
| UC-03 | School/Technical Super Admin | Reject an eligible application, notify the recipient by approved email flow and delete rejected registration account/data under an approved audit/privacy/error-recovery contract so they may register afresh; no previous-credentials or rejected-account-reuse design. |
| UC-04 | Approved account | Sign in/out using secure browser session and CSRF controls; fetch effective capabilities |
| UC-05 | Technical Super Admin or Django Superuser through its protected administration procedure | Assign/remove an eligible ordinary additional role with review, evidence, atomic audit and session protection; School Admin denied |
| UC-06 | Super Admin | Change a role's default permissions in protected interface; see impact and audit before commit |
| UC-07 | Super Admin | Add/revoke permitted direct user overrides without overriding protected constraints |
| UC-08 | Technical Super Admin or Django Superuser (separate protected procedure) | Grant/revoke School Admin (`Admin`) only to an authorized approved Instructor while retaining Instructor, with atomic audit and session safety |
| UC-09 | Django Superuser only | Grant/revoke Technical Super Admin to an eligible approved Instructor through a separately approved protected configuration procedure; retains Instructor+Admin and explicit governance permissions |
| UC-10 | Normal/Super Admin | Review redacted, scope-limited authentication/security activity after dedicated event logging is implemented |
| UC-11 | Instructor | Receive the SSG Advisor (Finance Monitor) responsibility without losing Instructor access |
| UC-12 | Instructor serving as SSG Advisor (Finance Monitor) | View authorized read-only financial overview, reports and transaction history under the **same** responsibility profile |
| UC-13 | Student/Treasurer | Gain Treasurer duties while retaining Student self-service, with financial self-interest restrictions |
| UC-14 | School Admin / inheriting Technical Super Admin; Student | Create/activate academic periods; run Student Semester Onboarding on each Active semester with verified current subjects; do not create authoritative enrollments in CTU-G Workspace. |
| UC-15 | Authorized Treasurer / Student recipient | Assess deduplicated period-specific organizational fees only after verified official eligibility and approved fee policy; post payments/receipts and preserve prior-period balances. |
| UC-16 | Student/authorized signatory | Prepare valid current-period clearance based on verified subjects, assigned Instructors, relevant organizational fees and approved prior-semester clearance prerequisites. |
| UC-17 | Instructor / Student (Group Leader or member) | WF-08 Hybrid Group Management: form verified groups, manage invitations/transfer and successor corrections, publish Instructor-defined categories and distribute **exact budget points per category** to other eligible groupmates only; scoring results/privacy to be approved separately. |
| UC-18 | Authorized campus users | Create/read announcements and track their own read state |
| UC-19 | Treasurer/School Admin | Generate and review reports at permitted detail level; separate finalization controls |
| UC-20 | Django Superuser | Configure and maintain CTU-G Workspace system data and any role, including exclusively granting/revoking Technical Super Admin via protected audited Django administration, without an ordinary Workspace API bypass |

## 5. Functional requirements

**Notation:** `SHALL` denotes required behavior for the target release. These are requirements, **not implementation-complete claims**. `P0` is foundational/security-critical; `P1` is core operations; `P2` is deferred/optional pending approval.

### 5.1 Registration, identities and approval

| ID | Priority | Requirement |
|---|---|---|
| FR-REG-01 | P0 | The public registration API SHALL accept only Student or Instructor requests and SHALL reject attempts to request restricted roles or privilege fields. |
| FR-REG-02 | P0 | Student/Instructor public registration SHALL securely stage eligible data and send email OTP **without creating a permanent account**. After OTP verification, the service SHALL atomically create one linked `accounts`/`users` pair as Pending/inactive, persist authorized verification evidence, consume the temporary stage and create no `account_roles` or authenticated session. |
| FR-REG-03 | P0 | Passwords SHALL be hashed; responses/logs SHALL never disclose plaintext passwords, hashes, tokens or whether a school ID is registered beyond the approved anti-enumeration policy. |
| FR-REG-04 | P0 | Only authorized school administrators SHALL list, approve or reject eligible requests; the reviewer SHALL not review themselves. |
| FR-REG-05 | P0 | Approval SHALL verify requested role eligibility, set approval/reviewer metadata, activate the account and assign the appropriate base Student or Instructor role **within one transaction**. |
| FR-REG-06 | P0 | After approval, the account SHALL receive current active base-role defaults by evaluation; individual permission records SHALL NOT be manually generated for each standard registrant. |
| FR-REG-07 | P0 | For an eligible rejection, the approved workflow SHALL send a truthful rejection email and delete the rejected registration account/data under an explicitly approved privacy, minimal-audit and delivery/deletion failure-recovery policy; the applicant SHALL be able to use ordinary fresh registration, including the same ID/email when unreserved. Prior SRS retained-rejected-account wording is superseded **as design intent**, not as automatic database-cleanup authorization. |
| FR-REG-08 | P1 | Only an authorized account-provisioning path SHALL create restricted school operators or elevate Admin governance; public registration SHALL never do so. |
| FR-REG-09 | P0 | Student registration SHALL collect required identity/login details only; course/program, year level, section, enrolled subjects and current semester SHALL be captured/confirmed during proposed **Student Semester Onboarding**, not treated as mandatory registration fields. Instructor Staff ID/field rules remain separately defined in WF-01.02. |
| FR-REG-10 | P0 | OTP resend/attempt limits, original-browser continuation, email delivery consistency, temporary stage expiry/cleanup, anti-enumeration, test evidence and production writer/security gates SHALL follow separately approved WF-01.01/WF-01.02 contracts. School Admin approval remains a distinct WF-02 action. |

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
| FR-AUTH-08 | P1 | On Student-context entry and upon an Active-semester change during an existing session, the backend SHALL check current-period onboarding eligibility and route Students lacking **Verified** onboarding to a restricted **Semester Academic Information Setup** / verification status view, not the ordinary Student Dashboard. Permitted logout, account support, accessible correction and historical-obligation/clearance recovery remain available. |
| FR-AUTH-09 | P0 | Semester Onboarding restrictions SHALL be enforced by protected Student-service APIs, not by frontend navigation alone. Multi-role accounts SHALL retain independently permitted non-Student functions without bypassing Student-context gates or financial self-interest restrictions. |

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
| FR-ADM-01 | P0 | School Admin SHALL NOT grant, remove or modify any account role or access-control permission. Only authorized Technical Super Admin may perform governed ordinary role assignments, subject to eligible accounts, exact effective permissions and audit; the Django Superuser MAY configure all account roles through an independently protected, authenticated, audited administration channel. |
| FR-ADM-02 | P0 | An approved Instructor SHALL retain their Instructor role when assigned School Admin (`Admin`) by an authorized Technical Super Admin or Django Superuser through protected, audited administration. No separate public School Admin registration is permitted. |
| FR-ADM-03 | P0 | Only the authenticated Django Superuser SHALL be able to assign or revoke Technical Super Admin membership; neither School Admin nor Technical Super Admin may grant/revoke that role for anyone, including themselves. The protected procedure must validate eligibility and prevent unauthorized privilege elevation. |
| FR-ADM-04 | P0 | Django Superuser authority over all application data and account roles SHALL be exposed only through reviewed administrative configuration operations, with authenticated execution, scoped write contracts, atomic audit, last-operator safeguards, transaction rollback and appropriate recovery. It SHALL NOT implicitly bypass ordinary CTU-G Workspace API effective-permission checks. Existing independent-signature/bootstrap machinery requires a separately approved reconciliation before replacement. |
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
| FR-ACA-05 | P1 | School Admin (and Technical Super Admin through inherited School Admin authority) SHALL be able to prepare campus-scoped School Year/Semester periods in Draft/Scheduled states and activate the next eligible semester after preflight, explicit confirmation, authorization and audit. Exactly one campus-scoped semester SHALL be Active; transition and previous-period close SHALL be atomic or fully rolled back. |
| FR-ACA-06 | P0 | Period activation SHALL preserve all historical academic, clearance, group and finance records; it SHALL NOT itself imply that every existing Student is enrolled, charged, cleared or ready for a new rating activity. Closed-period reopening/correction requires separate approval. |
| FR-ACA-07 | P1 | Each approved active Student SHALL complete or confirm **Student Semester Onboarding** for each newly Active period via the **Semester Academic Information Setup** page. The server SHALL provide School Year and Semester as read-only current-period values; Student SHALL supply/confirm course/program, year level, section and current enrolled subjects as applicable. |
| FR-ACA-08 | P0 | Self-reported academic information SHALL be Provisional/Draft/Submitted/Needs Correction until verified against CTU's main system or an authorized manual-verification process. The Workspace SHALL NOT become the authoritative enrollment or reenrollment system, nor treat Student input as proof of eligibility. |
| FR-ACA-09 | P1 | Onboarding SHALL be distinct for each Student and academic period, preserve previous-period submissions, accept controlled corrections/reverification, and show a clear status (Not Started, Draft, Submitted, Needs Correction, Verified). If official verification is unavailable, it SHALL support a recoverable pending state without falsely declaring eligibility. |
| FR-ACA-10 | P0 | Verified subject-to-class/Instructor assignments for clearance or group-rating eligibility SHALL originate from official CTU information or authorized verification, not merely from a typed subject name. Irregular, transferee, newcomer, absent and returning Student cases SHALL be assessed for the selected period without retroactively fabricating enrollment. |

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
| FR-FIN-09 | P0 | For each fee-bearing academic period, Finance SHALL base eligibility on a verifiable CTU-main-system enrollment state or on recorded, authorized manual verification when integration is unavailable. An unknown/unverified state SHALL NOT be silently treated as actively enrolled. |
| FR-FIN-10 | P1 | A newly enrolled first-year student, transferee or other newcomer SHALL be considered for an organization-fee obligation only in applicable periods in which official enrollment and campus fee policy are verified. |
| FR-FIN-11 | P0 | A student verified **not enrolled** in a period SHALL not incur a **new** fee solely because a previous period carried a balance. Existing legitimate unpaid obligations SHALL remain distinguishable from new charges. |
| FR-FIN-12 | P1 | For a returning student after one or more un-enrolled periods, Finance SHALL reassess eligibility for the **return period** using verified official enrollment and then-current applicable fee policy; gap periods SHALL not automatically generate new fee assessments. |
| FR-FIN-13 | P0 | Re-running assessment for the same student, period and fee type SHALL avoid duplicate active obligations. Conflicting upstream/verification evidence SHALL be held for authorized reconciliation rather than automatically billing or deleting charges. |
| FR-FIN-14 | P1 | Every posted eligibility decision SHALL be explainable by academic period, fee rule/version, verification evidence/source, verification date, responsible actor or trusted integration, assessment date, and any later correction reason, subject to privacy/retention approval. |
| FR-FIN-15 | P1 | The approved organization fee SHALL be assessed for each **verified eligible Student + academic period + fee type**, under the active approved policy/rate; application retries, repeated onboarding, re-verification and batch processing SHALL not duplicate an obligation. |
| FR-FIN-16 | P0 | New semester activation, unverified subject entry and login timing SHALL NOT alone create an obligation. Official eligibility may arrive during Student Onboarding verification or authorized upstream verification; the obligation effective date SHALL follow approved policy, independent of first login. |
| FR-FIN-17 | P0 | Prior-period unpaid balances and completed transactions SHALL remain period-identifiable. Approved corrections, exemptions and reversals SHALL preserve attributable history and never silently delete or overwrite a posted financial record. |
| FR-FIN-18 | P1 | Student and Treasurer views SHALL distinguish current-semester obligations and statuses from historical debt, and Student+Treasurer dual-role self-benefiting operations SHALL remain denied or independently reviewed. |

### 5.7 Clearance

| ID | Priority | Requirement |
|---|---|---|
| FR-CLR-01 | P1 | Students SHALL submit and track eligible subject/organization clearance requests for valid periods. |
| FR-CLR-02 | P0 | An Instructor or authorized signatory SHALL only sign requests matching an actual current teaching, adviser, Treasurer or fixed-signatory appointment. |
| FR-CLR-03 | P1 | School Admins SHALL maintain subject/teaching assignments and signatory appointments, subject to separation-of-duties controls. |
| FR-CLR-04 | P0 | Signature access and reuse SHALL be bound to the owner and historical evidence; no raw signature image SHALL be disclosed through broad admin permissions. |
| FR-CLR-05 | P2 | Clearance message sending SHALL remain unavailable until recipient/thread/period privacy semantics are approved for the existing schema. |
| FR-CLR-06 | P1 | Current-period clearance SHALL be based on verified enrolled subjects, effective Instructor/signatory assignments and applicable SSG fee obligations; provisional subjects SHALL NOT create official Instructor sign-off duties or clearance approvals. |
| FR-CLR-07 | P1 | The prerequisite for clearance from a previous semester, along with first-year, returning, transferee and irregular-student exceptions, SHALL be applied only after a separately approved policy; activation of a new campus semester SHALL NOT wait for every Student to complete past clearance. |
| FR-CLR-08 | P0 | Clearance records, signatures, fees and statuses SHALL remain separately tied to the original academic period; no new-term reset may erase, auto-approve or merge previous requirements. A current-period request/PDF SHALL not be issued as complete until all approved current-period requirements are satisfied. |

### 5.8 WF-08 Group Rating — Hybrid groups and exact peer point allocation (proposed)

**Workflow mapping:** Group Rating is **WF-08, Group B**. Its subflow IDs remain **To be defined**. The following requirements are stakeholder-selected **draft designs** and do not approve runtime configuration, new schema, final grading or result-publication rules.

| ID | Priority | Requirement |
|---|---|---|
| FR-RAT-01 | P1 | Only the officially assigned Instructor SHALL create/manage an activity and rating sheet for their verified subject/class/academic period; the sheet SHALL be bound to the correct eligible roster and current academic context. |
| FR-RAT-02 | P1 | Group formation SHALL be Hybrid: Instructor nominates group leaders; initial nominees accept leadership; accepted leaders invite eligible classmates; invitees accept/decline their own invitations. Valid acceptance SHALL atomically establish membership. |
| FR-RAT-03 | P0 | Group membership, invitation, transfer and rating submissions SHALL enforce class/activity/period eligibility, record ownership, single confirmed group per Student per activity, no self-rating, no duplicate final allocations and no forged membership acceptance. |
| FR-RAT-04 | P0 | Rating allocations and calculated results SHALL be disclosed only to approved recipients under a separately approved privacy/aggregation/publication policy; a Group Leader SHALL never read/edit another member's private allocation just by being leader. |
| FR-RAT-05 | P1 | Instructor SHALL configure a practical, flexible number of named category definitions (optionally with descriptions) and a **positive point budget for each category**. This replaces independent per-member 0–5/0–10/0–100 scoring as the working design. |
| FR-RAT-06 | P1 | The Student rating form SHALL show **only other eligible groupmates as rows**, **Instructor-defined categories and their point budgets as columns**, and **Total as the last column**, with a **Total Distributed** row. The logged-in Student SHALL not appear as a recipient, including when the Student is the Group Leader. |
| FR-RAT-07 | P0 | For **each category independently**, each Student SHALL allocate **exactly** the Instructor-assigned number of points among eligible *other* groupmates. Every cell SHALL be an explicitly entered nonnegative permitted number; deliberate **0 is valid** and missing input is **not 0**. Under/over-budget submissions SHALL be rejected by both UI and backend. |
| FR-RAT-08 | P1 | Each rater SHALL independently allocate the full per-category budget; groupmates SHALL not share one collective budget. The row total sums category allocations for a recipient; the Distributed total sums each category down recipient rows. A grand total does not replace per-category validation. |
| FR-RAT-09 | P1 | Instructor SHALL configure a minimum/maximum group size and may approve a documented exception within an independently approved hard capacity limit. Standard invitation acceptance and concurrent joins SHALL never exceed the authorized capacity. |
| FR-RAT-10 | P1 | If Students remain unassigned, Instructor MAY extend a bounded formation deadline, request Group Leaders to issue further invitations, or directly assign verified eligible Students, recording the reason and notifying affected people. Direct placement SHALL NOT be mislabeled as Student acceptance. |
| FR-RAT-11 | P1 | Only the Student SHALL initiate an ordinary request to transfer groups; an authorized assigned Instructor SHALL review and approve/reject, rechecking both groups, student eligibility, leadership and roster version. Pending/rejected requests SHALL leave existing membership unchanged. |
| FR-RAT-12 | P1 | When an outgoing Group Leader's transfer is approved, Instructor SHALL directly designate an eligible successor from the original group, without a separate acceptance step, and SHALL notify the successor and enable an assignment-correction request. Leadership replacement and transfer SHALL be atomic with required audit. |
| FR-RAT-13 | P0 | After roster finalization, ordinary invitations/transfers SHALL be closed; exceptional membership or leadership corrections SHALL require an authorized auditable roster revision. Where rating submissions already exist, ordinary roster changes SHALL be blocked pending approved rating-integrity rules. |
| FR-RAT-14 | P1 | A departing ordinary member SHALL NOT automatically require a replacement. An eligible departed member MAY receive manually entered zero allocations from peers in applicable categories; the system SHALL NOT fabricate or auto-fill zero ratings. Whether officially authorized withdrawals/transfers remain ratable requires separate policy. |
| FR-RAT-15 | P0 | Published category names, point budgets and eligible recipient-roster revisions SHALL be locked once submissions are accepted. Approved corrections SHALL preserve the original definitions, historic data, acting identity, reason and revision sequence. |
| FR-RAT-16 | P0 | Final submission SHALL be disabled/denied if a rater has no eligible recipient (e.g., one-member group), if category sums mismatch, self/foreign recipients are injected, a field is missing, versions have changed, or another final allocation already exists. Incomplete work may remain a recoverable draft only. |
| FR-RAT-17 | P1 | The final aggregation formula across raters, group-size normalization, category weighting, edit-after-submit policy, score publication and result audience SHALL remain **open decisions**. The system SHALL NOT invent a grade or publish results until these are approved. |

**Required form example** (illustrative, not a production rating scale). Student A is the rater, so Student A is absent from rows:

| Groupmate | Participation (10 pts) | Cooperation (10 pts) | Contribution (20 pts) | Total |
|---|---:|---:|---:|---:|
| Student B | 4 | 3 | 8 | 15 |
| Student C | 3 | 2 | 7 | 12 |
| Student D | 3 | 5 | 5 | 13 |
| **Total Distributed** | **10/10** | **10/10** | **20/20** | **40/40** |

**Per-category validation:** For a 10-point budget, `4+3+3=10` and `10+0+0=10` are valid; `5+3+1=9` and `5+4+2=11` are invalid. A blank cell cannot be treated as an explicit zero. Every eligible Student, including Group Leaders, receives the **same budget per category for their own allocation**.

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
| FR-DJA-04 | P0 | Django Superuser SHALL have the highest controlled configuration authority over CTU-G Workspace system data, including adding/removing any account role, via explicitly registered, reviewed, authenticated and audited Django administrative procedures. Protected role, permission and audit edits SHALL not be exposed as unrestricted raw model editing; approved business, integrity and recovery safeguards continue to apply. |
| FR-DJA-05 | P0 | Django Superuser creation/recovery SHALL use an independent, authenticated and attributable technical procedure with emergency access and secrets-handling safeguards. |
| FR-DJA-06 | P0 | Only a Django Superuser may authorize Technical Super Admin elevation/revocation via the protected administrator configuration path. Reconcile this owner-directed design with the existing two-Admin/three-signer first-operator bootstrap, audit attribution, release gates and P3B/P4 invariants before implementing or activating the replacement; framework `is_superuser` alone is not a normal Workspace API grant. |
| FR-DJA-07 | P1 | Technical framework actions and changes to application authority SHALL have clearly separated policies, logs and recovery procedures. |

### 5.11 Shared dashboard and interfaces

| ID | Priority | Requirement |
|---|---|---|
| FR-UI-01 | P1 | The application SHALL use one shared `DashboardLayout` with context-sensitive navigation based on effective permissions. |
| FR-UI-02 | P1 | School Admin SHALL see authorized school-management, applicant approval and limited monitoring screens, but no Access Control Management role editor, permission overrides or technical governance navigation. |
| FR-UI-03 | P1 | Super Admin SHALL additionally see role-default templates, service permissions, per-user overrides, effective-access inspection and security audit interfaces. |
| FR-UI-04 | P1 | A user with multiple roles SHALL use one account/session and see the union of authorized features, without separate logins or duplicate profiles. |
| FR-UI-05 | P0 | Screens SHALL clearly distinguish **Change Role Default** (affects all role holders) from **Change This User's Permissions** (one account). |
| FR-UI-06 | P1 | All privileged changes SHALL show a confirmation summary, privilege impact and meaningful denial/error messages; UI controls SHALL never substitute for server enforcement. |
| FR-UI-07 | P1 | Student-facing Semester Academic Information Setup SHALL clearly distinguish prefilled/verified data from editable proposed corrections and indicate verification status, required actions and safe support/recovery links. |
| FR-UI-08 | P1 | The WF-08 Student rating grid SHALL use accessible names, understandable category budgets, totals, error feedback, responsive horizontal overflow and keyboard/screen-reader compatible input controls; the Group Leader receives no privileged scoring interface. |

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

### 6.2.1 New module representation gaps and reconciliation gates

- **Academic periods:** Determine whether the official DBML already supports Draft/Scheduled/Active/Closed semesters, campus-scoped one-active-period enforcement, activation history and serialized transitions. No new field/table is authorized by this document.
- **Onboarding:** Reconcile Student+period academic confirmation state, per-subject verification evidence, correction history and external CTU enrollment/assignment identifiers against the existing ERD.
- **SSG fees:** Reconcile unique Student+Period+Fee Type assessments, policy/version, verification source, effective date, exemptions, refund/reversal and idempotent batch updates with existing finance tables.
- **Clearance:** Reconcile current/previous period prerequisites, period-specific signatory assignments, Student verification and PDF issuance requirements with actual clearance models.
- **WF-08 groups:** Reconcile activity, membership, invitation, leader designation, transfer request, roster version, custom category budget, per-rater-per-recipient allocations and audit provenance with the official ERD. No new workflow subflow IDs or database tables may be inferred solely from this SRS.
- **Data ownership:** CTU-G Workspace may store *verified references and operational snapshots* from CTU's authoritative academic source, but SHALL NOT become the primary owner of enrollment/reenrollment.

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
| NFR-SCL-01 | Scalability | Registration, onboarding, semester verification and finance batch processing shall use safe bounded/concurrent operations sized through measured campus load; no student fees created from an unverified bulk enrollment list. |
| NFR-AVL-01 | Availability | Semester onboarding and financial/clearance history shall degrade safely during CTU upstream or SMTP outages, with clear pending states and essential recovery/support routes. |
| NFR-DAT-01 | Data integrity | One active campus semester; idempotent period fee assessments; immutable/auditable historical records; unique group membership and exact category budgets enforced on the server. |
| NFR-FLX-01 | Flexibility | Instructors may configure reasonable category counts and per-category budgets; academic-period/fee policy adapts through approved configuration, without silent live privilege or grading changes. |
| NFR-CMP-01 | Compatibility | Onboarding and rating forms should be tested across supported modern browsers, keyboard/screen-reader interaction and varying mobile viewport sizes. |

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
| AT-08 | Authorized Technical Super Admin promotes an approved Instructor to School Admin | Protected assignment adds Admin while preserving Instructor; no Technical Super Admin grant; audit and session handling verified |
| AT-09 | School Admin or Technical Super Admin attempts unauthorized Technical Super Admin elevation | Denied for both; only Django Superuser can use the protected role elevation/revocation procedure; no write on failure |
| AT-10 | Super Admin attempts self-grant/last-admin removal | Denied or routed through separately approved governance recovery, never silently executed |
| AT-11 | Multi-role account with Deny override | Direct Deny wins even if a second role grants same code; authorization checked again on next request |
| AT-12 | Normal Admin monitors auth activity | Only redacted, authorized campus-scoped events shown, no passwords/tokens or unrestricted security diagnostics |
| AT-13 | Django Superuser operates reviewed Django Admin configuration | Only protected audited administrative operations, including role management and exclusive Technical Super Admin role grant/revoke, can mutate data; no automatic ordinary Workspace API bypass |
| AT-14 | Catalogue planner after SRS change | Reports previous C1 manifest incompatibilities as unresolved; does not apply existing 82-code/96-binding baseline automatically |
| AT-15 | Audit insertion fails during role change | Security transaction rolled back; role/override state unchanged |
| AT-16 | Instructor accesses other class / Student other payment | Server returns denied/filtered result regardless of role membership or hidden buttons |

### 8.1 Proposed acceptance scenarios for academic periods and WF-08

The following **AT-V04-01–AT-V04-25** are **provisional v0.4 test scenarios**, not new official AT identifiers or evidence of passed tests. The provisional prefix avoids collisions with earlier companion-proposal AT-V04-09–31. Treat the examples as design candidates pending owner sign-off.

| Test ID | Scenario | Expected acceptance outcome |
|---|---|---|
| AT-V04-01 | Student OTP registration | No permanent account before verified OTP; after verification exactly one Pending/inactive account and profile, no role/session. |
| AT-V04-02 | Rejected applicant | Authorized email/deletion lifecycle with recoverable failure handling; fresh registration possible when identity no longer reserved. |
| AT-V04-03 | Register Student without semester-specific School Information | Identity fields can complete registration; onboarding collects course/year/section/subjects after approval for Active period. |
| AT-V04-04 | School Admin activates semester | Preflight and confirmation; exactly one Active semester; previous period preserved; transactional rollback on failure. |
| AT-V04-05 | New semester triggers onboarding | Student is routed to Semester Academic Information Setup; non-Student approved features remain independently authorized. |
| AT-V04-06 | Provisional subjects or unavailable CTU verifier | Status remains Submitted/Needs Correction; no fake verified enrollment, no official instructor clearance or automatic fee. |
| AT-V04-07 | Verified irregular/returning Student | Only validated current subjects/period recorded; no false charges for inactive periods. |
| AT-V04-08 | Fee idempotence and effective date | One eligible Student+Period+Fee Type assessment despite retries/concurrent jobs, independent of login. |
| AT-V04-09 | New period with outstanding prior fee/clearance | Historical debt/clearance preserved and separately visible; no blanket waiver or reset. |
| AT-V04-10 | Clearance prerequisites and official signatories | Verify previous-period policy/exceptions and current assignments before requests/approval/PDF. |
| AT-V04-11 | WF-08 Instructor assignment | Unassigned Instructor cannot create or finalize another class's group activity. |
| AT-V04-12 | Hybrid leader invitation and group formation | Initial leader accepts nomination; only eligible classmate accepts own invitation; one active membership per activity. |
| AT-V04-13 | Concurrent group acceptance | Group capacity and uniqueness maintained atomically. |
| AT-V04-14 | Hybrid unassigned Student handling | Instructor can extend, request invitations or directly place with reason; no forged acceptance event. |
| AT-V04-15 | Student-requested transfer | Only Student initiates ordinary transfer; Instructor approves/rejects; original membership stays until successful commit. |
| AT-V04-16 | Leader successor designation | Assigned Instructor directly designates eligible source-group successor, records reason/notifications/correction, with atomic transfer. |
| AT-V04-17 | Post-finalization roster | Ordinary edits blocked; auditable revision required; prior accepted ratings preserved and stricter change gate enforced. |
| AT-V04-18 | Instructor category builder | Multiple custom categories with separate positive budgets can be published; no arbitrary small fixed category cap. |
| AT-V04-19 | Self excluded from rating form | Student A sees only eligible B/C/D rows; API rejects self ID even if forged. |
| AT-V04-20 | Correct grid layout | Groupmates as rows, custom categories as columns, rightmost Total, bottom Total Distributed. |
| AT-V04-21 | Exact budget per category | Both 10/10/20 examples and all custom budgets require exact sums for **each** category; 9/10 and 11/10 rejected. |
| AT-V04-22 | Explicit zero and missing input | Deliberate `0` accepted, blank remains incomplete, and absent rating never auto-filled as zero. |
| AT-V04-23 | Group Leader and departed members | Same peer-rating rules as others; no mandatory replacement for departed ordinary member; eligibility/policy checked. |
| AT-V04-24 | One-person group / duplicate submit | No recipient means cannot submit; repeated final submission cannot create duplicate allocations. |
| AT-V04-25 | Published sheet changed after submissions | Ordinary category/point/roster mutation blocked, or approved versioned correction with original history retained. |

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
| OD-03 | Define the exact ordinary role allowlist, target eligibility, and approved Treasurer / SSG Advisor appointment evidence **for Technical Super Admin** (or separately protected Django Superuser administration); School Admin receives no role assignment authority. |
| OD-04 | **Terminology resolved:** SSG Advisor and Finance Monitor are the same responsibility, not separate roles. Confirm the recommended canonical `SSG Advisor` role or equivalent narrow account overrides, and approve any additional advisor duties separately. |
| OD-05 | Approve the three SSG Advisor (Finance Monitor) views, dataset filters, redactions, report maturity, transaction history scope and retention/export rules. |
| OD-06 | Define Student+Treasurer conflict rules (self-payments, exemption, receiving/issuing receipt) and Instructor+Admin conflict rules. |
| OD-07 | Decide which redacted authentication events a Normal Admin may see, and approve event storage/retention without overloading access-control mutation audit. |
| OD-08 | Set exact Super Admin limits for editing any role default, including their own Admin/governance role and safeguards for globally disruptive changes. |
| OD-09 | Define first application Super Admin identity/bootstrap attribution, governance approval evidence and recovery. |
| OD-10 | Decide Django Superuser integration path after inspecting the custom Account model; any migrations require separate authorization. |
| OD-11 | Set Technical Super Admin direct Grant/Deny override governance; School Admin may not manage account-specific permissions. Django Superuser protected configuration remains separately reviewed and audited. |
| OD-12 | Reconcile all affected C1 D01-D18 policy proposals and freeze a new approved catalogue/grant manifest; keep all activation and database writes blocked until then. |
| OD-13 | Determine session revocation timing after role/default/override changes and account suspensions. |
| OD-14 | Approve performance, privacy, audit-retention, operational recovery and deployment acceptance targets. |
| OD-15 | Approve semester status transitions, one-active-period scope, calendar dates, activation authority, exception/reopen and audit rules. |
| OD-16 | Approve official enrollment/subject verification channel, authorized manual fallback, onboarded status model and Student Dashboard restriction/recovery policy. |
| OD-17 | Approve semester-specific organization fee policies (amount, effective date, exemptions, late verification, transfers/returns, reversals, billing notice and audit). |
| OD-18 | Approve previous-semester clearance prerequisite and exceptions for first-year, irregular, returning or transfer Students. |
| OD-19 | Define WF-08 subflow IDs in official Catalogue; approve eligibility snapshots, group capacity range/hard cap, nominations, invitation windows and unassigned Student resolution. |
| OD-20 | Approve WF-08 transfer/leadership/withdrawal and post-finalization roster amendments, especially after rating submission. |
| OD-21 | Approve category point precision (integers vs decimals), practical category/input limits, draft/final submission and correction/reopen policy. Exact per-category budget distribution and self-exclusion are the **selected design**, subject to formal approval. |
| OD-22 | Decide how incoming points from multiple raters are aggregated, whether group-size normalization/weighting applies, and the permitted result audience/release timing; these are **not yet specified**. |
| OD-23 | Reconcile original v0.3 registration/rejection wording against latest OTP-before-account and rejection-email/deletion contracts and real code/tests; resolve privacy-safe notifications and legacy data handling before release. |

## 11. Requirement-to-source traceability and change impact

| Requirement group | Primary basis | Existing implementation dependency |
|---|---|---|
| Admin profiles, role defaults, multi-role assignment | Owner's 7 Nov 2026 clarified use cases | `roles`, `account_roles`, `role_permissions`, `account_permissions`; B2 restrictions must be reconciled |
| Registration and approval | Existing project workflow and ERD | Current registration API; future atomic approval/assignment services |
| Django Superuser separation | Owner requirement and Django custom-Account integration need | Custom user manager/model, Django Admin and security-reviewed framework permissions |
| SSG Advisor (Finance Monitor) read-only finance oversight | Owner's clarification that SSG Advisor = Finance Monitor, plus the three named financial views and finance/report ERD | C1 finance/reports permissions; new safe transaction-history scope may be required |
| Audit and integrity | Existing Phase 1H-B1/B2 security architecture | `access_audit_logs` and safe audit payload contracts; auth-event logging not implemented |
| Campus modules | Main ERD and C1 catalogue proposal | Module-specific model/view/services and object authorization, largely future work |
| Academic-period activation / onboarding | Use Case Specification v0.4.1 UC-D11–D12; owner decisions, Nov 2026 | WF-05 and WF-11 category review; CTU-authoritative eligibility; official schema and period status verification |
| Semester fee and clearance | Use Case Specification v0.4.1 UC-D13, UC-D07–D08 | WF-06/WF-07; approved fee policy, previous clearance gates, idempotent period-specific obligations |
| **WF-08 Group Rating** | Owner-selected group and exact point distribution designs; UC-D09 and UC-D14–D16 | Hybrid group lifecycle, verified rosters, custom categories with exact budgets, proposed tests; no approved subflow IDs or final formula |

**Explicit change impact on C1/C2A:** The 10-service/82-code/96-binding manifest remains a valuable **historical planning baseline**, not the approved implementation target. It must be revisited to add/adjust Admin profiles, the **single SSG Advisor (Finance Monitor)** responsibility, finance-monitoring permissions and school authentication-log viewing. The old C1 assumption that `Admin` and `Technical Super Admin` must not be co-assigned is intentionally superseded by this **proposed** composite Super Admin profile, but code changes require tests and specific approval. B2's restrictions on reserved roles and assigned-role edits must never be relaxed as a quick fix.

### 11.1 AI Agent Guidelines Checklist for future approved implementation

Use the existing Workflow Catalogue's exact workflow-entry template and separate Human Approval field. Each applicable subworkflow follows **Inspect → Reconcile → Approve → Implement → Test → Commit**. This SRS is a requirement draft, not an instruction to mark any checklist item complete, grant permissions, modify the ERD, perform a migration or create a Git commit. No WF-08.xx subflow ID may be invented while the official Catalogue says "To be defined".

## 12. Acceptance and sign-off

This SRS v0.4 is suitable for stakeholder review, not authorized deployment. The proposed additions do not certify code, schema or WF-08 readiness. Recording an approved version requires a named project owner, review date, accepted revision/digest, decisions OD-01 through OD-14 as applicable, and a mapping to approved implementation tasks. Any change affecting authorization, account provisioning, finance, ERD or Django framework administration requires impact analysis and fresh regression/security tests.

| Reviewer | Decision | Date / evidence |
|---|---|---|
| Project owner | Pending | — |
| Security/architecture reviewer | Pending | — |
| University operations stakeholder | Pending | — |

---

**End of SRS v0.4 — Draft for review.**

> **Administrative-role alignment note (18 Nov 2026):** Historical R3/R4, OD-01/03/08/09/10/11, and older FR-ADM-01/UC-05 descriptions elsewhere in archived or integrity-pinned sources may refer to School Admin role delegation or a two-Admin bootstrap. The policy in §3.5 and revised FR-ADM requirements above is the owner-directed proposed revision. Resolve all protected contracts and catalogue pins before implementation; no ERD or database change was performed by this document edit.
