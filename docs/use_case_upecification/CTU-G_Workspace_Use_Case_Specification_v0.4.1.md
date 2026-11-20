# CTU-G Workspace
## Use Case Specification — All Application User Types

**Document ID:** CTUG-UCS-001  
**Version:** 0.4.1 + 18 November 2026 administrator-authority alignment (review draft; existing use-case IDs preserved)  
**Date:** 17 November 2026  
**Project:** CTU-G Workspace — Cebu Technological University, Ginatilan Campus  
**Status:** **PROPOSED / NOT APPROVED FOR IMPLEMENTATION**  
**Repository location (proposed):** `docs/use_cases/CTU-G_Workspace_Use_Case_Specification_v0.4.1.md`

> **Document-control warning:** This document expresses intended, proposed use cases; it does not certify that all functions exist. **Version 0.4.1 preserves the v0.4 use cases and corrects workflow-category references to the owner-supplied 17 November 2026 category map: Group Rating is WF-08 (Group B), not WF-13; Reporting & Document Generation is WF-13 (Group C). Group-rating design decisions remain proposals, not implementation authorization.** The previously supplied v0.3.2 Workflow Catalogue reported Student/Instructor OTP registration development-implemented, while most other subworkflows were Draft / Not yet inspected. The newer category table supplied here does not itself verify implementation status. Do not treat an actor–use-case association as a live authorization grant, alter the official ERD, or assign new workflow IDs without owner approval.

## 1. Purpose, scope, and source hierarchy

This specification presents the actions that five primary application user types should be able to perform in CTU-G Workspace: **Technical Super Admin (application Super Admin)**, **School Admin (normal Admin)**, **Instructor**, **Treasurer**, and **Student**. It also documents common authenticated functions and public applicant flows. The v0.4 revision retains **one-time Account Registration** for secure identity and **Student Semester Onboarding** for academic information that may change each semester. Every new Active semester requires eligible Students to complete the proposed **Semester Academic Information Setup** process before their normal Student Dashboard; organizational-fee liability is determined independently through verified enrollment and approved period-specific policy, even if an eligible Student has not yet logged in. Each case traces to the **WF-01 through WF-13** category map where appropriate, identifies constraints, and suggests acceptance checks.

**Source documents used:**

1. Owner-supplied **updated workflow category mapping**, 17 November 2026, supersedes older category numbering for WF-08 through WF-13. The corresponding newly numbered catalogue file was not provided in this revision; verify it against the repository before implementing. The older supplied `docs/workflows/CTU-G_Workspace_System_Workflow_Catalogue.md` draft **v0.3.2** (16 November 2026) is a historical reference only where its numbering conflicts.
2. `docs/SRS/CTU-G_Workspace_SRS_v1.md` (the file's internal header identifies it as a **v0.3 revised draft dated 7 November 2026**); specifically existing SRS use cases UC-01–UC-20 and FR/NFR references.
3. `docs/SRS/CTU-G_Workspace_SRS_v0.4_COMPANION_PROPOSALS.md`, 11 November 2026 — **proposals only** on academic-period organization-fee eligibility.
4. Stakeholder discussion, 16–17 November 2026 — proposed semester activation, Student Semester Onboarding, verified subjects, normal Student Dashboard gating, clearance preparation and organization-fee obligations.
5. Stakeholder terminology decision, 17 November 2026 — prefer **Student Semester Onboarding** for the feature/workflow and **Semester Academic Information Setup** for the student-facing page. Course/program, year level, section and enrolled subjects are semester-dependent information, not mandatory initial registration fields. These are requirements proposals until formally reconciled with SRS, WF and code.
6. Stakeholder Group Rating design discussion, 17 November 2026 — Hybrid group formation; Instructor-nominated leaders, Student-accepted invitations, group-size exceptions, unassigned-student remedies, Student-requested/Instructor-approved transfers, Instructor-designated successors, departure handling, and **exact distribution of Instructor-set points per category**. Design selections are proposed; no WF-08.xx IDs are approved.

**Updated workflow-category map (owner-supplied 17 November 2026):**

| ID | Category | Group | Subflows |
|---|---|---|---|
| WF-01 | Registration & Authentication | Group A | 6 |
| WF-02 | Account Management | Group A | 6 |
| WF-03 | Access Control Management | Group A | 6 |
| WF-04 | Profile Management | Group A | 5 |
| WF-05 | Academic Information | Group B | 4 |
| WF-06 | Clearance Management | Group B | 5 |
| WF-07 | SSG Financial Management | Group B | 8 |
| WF-08 | Group Rating | Group B | To be defined |
| WF-09 | Announcements & Notifications | Group B | 5 |
| WF-10 | Account Concerns & Support | Group B | 4 |
| WF-11 | System Administration & Configuration | Group C | 4 |
| WF-12 | Audit, Security & Monitoring | Group C | 5 |
| WF-13 | Reporting & Document Generation | Group C | 4 |

**WF-08 subworkflow boundary:** Group Rating remains one category with **no approved WF-08.xx subflow IDs**. Mapping later category references (e.g., WF-09.02 or WF-13.01) is a provisional traceability crosswalk, not confirmation that individual subflow titles or suffixes are unchanged. The use-case details and candidate acceptance tests below do not create such IDs. This correction does not approve any implementation or modify the official Workflow Catalogue.

**Reconciliation precedence:** The owner-supplied 17 November category table governs the current category numbers. Earlier catalogue specifications inform proposed detailed behavior only where not superseded, and the SRS is a reference for broader use cases. The newly numbered catalogue with individual subflow titles has not been inspected here; mapped suffixes for WF-09–WF-13 must be verified before implementation. Any disagreement is tracked as an open reconciliation item. Workflow-category numbers in this draft are corrected, not approved as new subworkflows. References such as **UC-01** refer to pre-existing SRS use cases; local IDs like **ACT-ST-01** are documentation entry identifiers, **not new SRS-approved use-case identifiers**.

## 2. Actors and system boundary

| Actor | Description and authority boundary |
|---|---|
| Technical Super Admin | **Application-level Super Admin**, built from normal School Admin authority plus separately protected access-governance permissions. It is **not** a separate third admin tier and not automatically a Django Superuser. No blanket right to view every business record. |
| School Admin | Existing approved Instructor with an additional Admin role; handles authorized school operations. Cannot assign/revoke any account role or edit role defaults, overrides or protected governance. |
| Instructor | Views assigned teaching information; prepares class-scoped group formation and Instructor-defined point-allocation sheets, reviews transfer/exception requests, and performs assigned clearance actions. Can additionally act as **SSG Advisor (Finance Monitor)** with separately approved, read-only finance capabilities. |
| Treasurer | Handles permitted SSG fee assessments after verified period enrollment eligibility, payments, receipts, expenses, and reports. A Student may also have Treasurer duties; self-benefiting transactions must be blocked or independently controlled. |
| Student | Completes proposed semester-specific onboarding and uses own academic, clearance, finance, group invitation and peer point-allocation, announcement and account services. Cannot access other students' records. |
| Student/Instructor Applicant | Public, pre-approval actor who can start email-OTP registration; no dashboard or assigned application role from registration alone. |
| CTU Main System / authorized verifier | **External authoritative source** for enrollment/reenrollment and verified academic status; CTU-G Workspace must not create a competing authoritative enrollment module. |
| Django Superuser / technical operator | Separate framework-level highest configuration authority over system data and all account roles, **including exclusive grant/revoke of Technical Super Admin** via reviewed, audited, protected Django administration. No implicit ordinary Workspace API permission bypass. |

### 2.1 Authorization principles

- One account may hold multiple **approved active roles**; the shared dashboard displays features derived from effective permission checks, not from role-name checks alone.
- Effective permissions derive from the union of active assigned-role grants and active direct Grants, less active Denies; active account/service eligibility and record/period ownership checks also apply.
- **School Admin vs Technical Super Admin:** school operations are inherited by the higher application tier through explicit permission assignment. Only the protected tier governs role defaults and broad user-specific overrides.
- Public requested roles do not grant authority. On successful OTP registration, the new account remains **Pending** and **inactive** with no assigned application role or authenticated session.
- SSG Advisor and Finance Monitor name **one** responsibility, not two separate roles; it permits scoped financial overview, reports, and transaction history **read-only**, never Treasurer writes.
- A permission grant does not create a missing feature. Every protected API must enforce actual permission and row-level business scope.
- No user may review or privilege-escalate themselves; preserve last-effective-Super-Admin recovery and independent review of protected promotions.
- **Proposed Student Dashboard prerequisite:** for an active academic period, a Student must complete **Student Semester Onboarding** using the **Semester Academic Information Setup** page and meet verified-subject checks before the normal Student Dashboard becomes available. This is a workflow eligibility rule, **not** a new authentication role, and must be enforced server-side.
- **One-time versus semester-dependent data:** account registration collects durable identity/login fields (School ID, name, email, password and approved optional identity fields). Semester Onboarding collects or confirms course/program, year level, section and enrolled subjects for the current Active period; School Year and Semester are read-only, system-selected period attributes, not Student-entered identity credentials. The academic record must not overwrite the original registration identity.
- **Essential-access exception:** a Student awaiting onboarding or verification must retain safe, restricted access to Logout, support, their onboarding status/correction path and permitted previous-clearance resolution. A Student who also has an independent authorized Treasurer role must not lose unrelated Treasurer access solely because Student onboarding is incomplete.
- **Organization-fee boundary:** activation or self-submitted subject lists alone do not create a debt. Verified eligibility for a distinct active academic period plus an approved fee policy must trigger exactly one assessment per student, period and fee type, even if onboarding is completed late or verified upstream before login.
- **WF-08 group-scoped authority (proposal):** a Group Leader is a responsibility within one verified subject/activity, not a new application role. Instructor group management is limited to assigned classes. Each Student may have only one confirmed group in the same activity and cannot score themselves or view other raters' private point allocations.
- **WF-08 exact point distribution (proposal):** for each published category, a Student must allocate **exactly** the Instructor-set number of points across eligible *other* members of the same activity group; zero is a valid intentional allocation, but an unanswered cell is not zero. Row totals sum that groupmate's categories; category totals must match the Instructor's budget before final submission.

### 2.2 Administrator promotion authority — owner-directed alignment, 18 November 2026

These are **target requirements, not implemented access paths**. An Instructor applies using WF-01.02 and is approved through WF-02.03. School Admin is the resulting Instructor + Admin composition. Technical Super Admin is Instructor + Admin + Technical Super Admin; its governance permissions must also be explicitly provisioned and enabled. Both retain Instructor. Technical Super Admin may assign/revoke Admin for another eligible approved Instructor, but **only Django Superuser** may add/remove the Technical Super Admin role. Django Superuser also has reviewed configuration authority over other system data and account roles. Direct unrestricted model editing is not approved; the current `/admin/` is read-only. A special audited, authenticated, protected Django configuration action must be reconciled against the existing bootstrap ceremony, ledger/writer safeguards and effective-permission architecture before use.

**Negative flows:** School Admin role editing denied; Technical Super Admin grants/revokes Technical Super Admin denied; Django staff-only actor denied; `is_superuser` flag does not bypass unrelated Workspace API permissions; self-promotion by an application administrator denied; invalid Instructor eligibility denied; missing audit or P3B/protected writer precondition rolls back; last-operator removal refused until recovery policy exists. Preserve separate requirements for account eligibility, role collision, Deny precedence and session invalidation.

## 3. Common use cases (approved active accounts unless stated)

| Entry | Use case | Actor(s) | WF reference | Intended result |
|---|---|---|---|---|
| ACT-CM-01 | Sign in and establish secure browser session | All approved active users | WF-01.03, WF-01.06; SRS UC-04 | Authenticated session; Students without current-period onboarding receive a restricted onboarding route rather than the normal Student Dashboard; other authorized roles remain independently scoped. |
| ACT-CM-02 | Log out / terminate session | All signed-in users | WF-01.04; SRS UC-04 | Session invalidated; protected resources inaccessible. |
| ACT-CM-03 | Request password reset | Eligible account owner | WF-01.05 | Secure, bounded recovery without account enumeration. |
| ACT-CM-04 | View/edit own profile and credentials | All eligible users | WF-04.01–05 | Only authorized personal fields updated, with reauthentication where needed. |
| ACT-CM-05 | Read announcements and notifications | All authorized users | WF-09.02–05; SRS UC-18 | Audience-appropriate messages and personal read states only. |
| ACT-CM-06 | Submit/track account concerns | All eligible users | WF-10.01, WF-10.04 | Own issue submitted and tracked through permitted support channel. |

**Status:** The previously supplied v0.3.2 catalogue described WF-01.03–06, WF-04 and the corresponding announcements/support functions as Draft/Not yet inspected; confirm their status in the latest catalogue. These entries describe target behavior, **not verified functionality**.

## 4. Actor-specific use-case catalogue

### 4.1 Technical Super Admin (application Super Admin)

| Entry | Use case | WF reference | Condition / expected outcome |
|---|---|---|---|
| ACT-TS-01 | Perform authorized School Admin operations | WF-02, WF-11 | Inherit normal school-operation permissions through explicit approved grants; school record scope still applies. |
| ACT-TS-02 | Review/change role-default permissions | WF-03.02; SRS UC-06 | Impact preview, protected authorization, atomic update, and audit; no self-escalation. |
| ACT-TS-03 | Grant/deny/revoke user-specific permissions | WF-03.03–04; SRS UC-07 | Target/service restrictions, Deny precedence, audit, and conflict checks. |
| ACT-TS-04 | Inspect effective user access | WF-03.05 | Explain combined role grants, direct overrides, service state and record-scope limits without exposing secrets. |
| ACT-TS-05 | Review role/permission audit events | WF-03.06, WF-12.02 | Redacted, scoped and attributable access-governance history. |
| ACT-TS-06 | Configure protected service permissions | WF-11.03, WF-03 | Only approved governance configuration; review impact on active users. |
| ACT-TS-07 | Provision/promote eligible ordinary School Admin | WF-03.01; SRS UC-08 | Independently authorized change with role allowlist, actor identity and audit trail. |
| ACT-TS-08 | Await first Technical Super Admin provisioning by Django Superuser | WF-03.01; SRS UC-09 | Only Django Superuser may grant/revoke Technical Super Admin to an approved Instructor; existing two-Admin/three-signer bootstrap and protected executor require reconciled replacement authorization. Technical Super Admin cannot perform elevation. |
| ACT-TS-09 | Review authorized security/system events | WF-12.01–04 | Access redacted diagnostics as granted; no blanket read of financial or rating records. |
| ACT-TS-10 | Review backup/retention controls | WF-12.05 | Only when assigned separate operational powers; procedures and evidence require approval. |

| ACT-TS-11 | Assign/revoke authorized ordinary account roles | WF-03.01; SRS UC-05 / FR-ADM-01 | With exact permission, approved eligible target, no self-promotion, atomic audit, deny precedence and session revocation; may assign/remove Admin to eligible approved Instructors, never Technical Super Admin. |

### 4.2 School Admin (normal Admin)

| Entry | Use case | WF reference | Condition / expected outcome |
|---|---|---|---|
| ACT-SA-01 | View pending registration applications | WF-02.01 | School-scoped Pending applicants only; sensitive credential material hidden. |
| ACT-SA-02 | Review applicant identity and eligibility | WF-02.02 | Validate email proof and Student/Instructor eligibility using approved evidence; OTP alone does not prove enrollment/employment. |
| ACT-SA-03 | Approve an eligible applicant | WF-02.03; SRS UC-02 | Approved/active account with correct first role and reviewer attribution in one authorized transaction. |
| ACT-SA-04 | Reject applicant and notify by email | WF-02.04; SRS UC-03 | Notify and delete rejected registration account/data under approved failure, privacy and audit policy; allow normal fresh registration. |
| ACT-SA-05 | Activate/deactivate eligible existing account | WF-02.05–06 | Authorized state change without breaking protected governance or audit invariants. |
| ACT-SA-06 | Attempt to assign/revoke roles (denial case; historical ID retained) | WF-03.01; SRS UC-05 | School Admin has no account-role or Access Control Management mutation authority. All attempts must be refused and audited where policy requires; no role change. Ordinary role management belongs to ACT-TS-11. |
| ACT-SA-07 | Manage authorized academic-period settings | WF-05.04, WF-11.01; SRS UC-14 | Create/edit Draft and Scheduled school-year/semester settings and validated dates; CTU main system remains enrollment authority. |
| ACT-SA-08 | Maintain clearance signatory assignments | WF-06.02–03 | Only valid periods, subjects and appointees; assignment changes are attributable. |
| ACT-SA-09 | Publish eligible announcements | WF-09.01; SRS UC-18 | Audience and publication policy enforced. |
| ACT-SA-10 | Review/respond to account concerns | WF-10.02–03 | Assigned concerns handled without disclosing unrelated users' information. |
| ACT-SA-11 | Review permitted operational reports/activity | WF-12.02, WF-13.01 | Scoped business reports and optionally redacted school auth events, only if explicitly granted. |
| ACT-SA-12 | Activate or close the campus academic period (proposed) | WF-05.04, WF-11.01 (existing categories; no new ID) | Preflight, confirm, audit and atomically transition exactly one campus-scoped Active semester while preserving prior records; no blanket charging or auto-clearance. |

**Explicit denial:** School Admin cannot assign or revoke **any role**, edit role-default permission templates, manage account overrides, edit protected governance catalogue, or grant Super Admin authority. Any narrowly delegated read-only inspection is not permission editing.

### 4.3 Instructor

| Entry | Use case | WF reference | Condition / expected outcome |
|---|---|---|---|
| ACT-IN-01 | Register Instructor account (public) | WF-01.02; SRS UC-01 | Verify email OTP before creation; pending/inactive account, no role or login. |
| ACT-IN-02 | View assigned subjects | WF-05.02 | Class/period-scoped list from authorized academic assignment data. |
| ACT-IN-03 | View enrolled students for assigned classes | WF-05.03 | View officially verified, period-appropriate class rosters; self-reported subjects must not independently grant a Student association or clearance authority. |
| ACT-IN-04 | Create/manage group-rating activities, sheets and criteria (proposed) | WF-08 (IDs unassigned); SRS UC-17 | For assigned classes/periods, configure custom categories with Instructor-set point budgets, preview/publish and freeze scoring definitions at the first accepted submission. |
| ACT-IN-05 | Review/decide assigned clearance items | WF-06.03; SRS UC-16 | Only currently authorized signatory actions; record owner and date. |
| ACT-IN-06 | View SSG finance as SSG Advisor (Finance Monitor) | WF-07.06–07; SRS UC-11–12 | Only when specifically assigned: overview, reports and transaction history **read-only**; no payment/expense writes. |
| ACT-IN-07 | Use common profile, announcement and support functions | WF-04, WF-09, WF-10 | Subject to shared-account and data-scope policies. |
| ACT-IN-08 | Manage hybrid group formation and finalization (proposed) | WF-08 category only | Nominate leaders; monitor invitations, group capacity and unassigned Students; extend deadlines, request invitations, directly place eligible Students with reason, authorize controlled exceptions and finalize a verified roster. |
| ACT-IN-09 | Review Student transfer requests and correct roster/leader changes (proposed) | WF-08 category only | Decide Student-initiated transfers; directly designate an eligible successor when a leader moves; preserve audit and roster revisions, apply stricter controls after finalization. |

### 4.4 Treasurer

| Entry | Use case | WF reference | Condition / expected outcome |
|---|---|---|---|
| ACT-TR-01 | Verify academic-period fee eligibility | WF-07.01, WF-05.04 | Use CTU main system status or authorized manual verification for each active period; Student-submitted subjects alone do not establish liability. |
| ACT-TR-02 | Assess semester-specific organization fee | WF-07.02 | After verified enrolled eligibility, apply the **approved period-specific fee schedule**, at most once per Student + Period + Fee Type; assessment is not triggered by login or unchecked subject entry. |
| ACT-TR-03 | Record and validate payment | WF-07.03; SRS UC-15 | Authorized attributable transaction; no self-payment approval or unsupported reversals. |
| ACT-TR-04 | Issue/view authorized receipt | WF-07.04 | Receipt linked to validated payment and correct owner; no duplicate issuance. |
| ACT-TR-05 | Record/category SSG expenses | WF-07.05 | Only authorized expense category and financial period; audit changes. |
| ACT-TR-06 | View financial overview, balances and history | WF-07.06 | Sensitive student ledger access limited to approved duties. |
| ACT-TR-07 | Prepare financial reports | WF-07.07, WF-13.01–04; SRS UC-19 | Period/source correctness, scoped output and protected finalization/export. |
| ACT-TR-08 | Process newcomers, transferees and returning students | WF-07.08 | Reassess each period using verified official enrollment; no automatic fees for periods not enrolled. |
| ACT-TR-09 | Decide assigned fee-related clearance items | WF-06.03 | Only correct-period verified obligation/payment status and valid Treasurer appointment; own-case conflicts blocked; past balances stay separate. |
| ACT-TR-10 | Reconcile automated period assessment and exceptions (proposed) | WF-07.01–02, WF-07.08 (existing categories) | Review held, conflicting or corrected eligibility; apply authorized exemption/reversal rules without duplicating, hiding or backdating charges improperly. |

**Boundary:** The accompanying finance scenarios (FR-FIN-09–14, AT-25–31), plus the v0.2 automatic-on-verification assessment rule, are **candidate amendments**, not approved policies. Actual semester fee dates, recurring rules, exemptions, proration, and reversals require owner approval.

### 4.5 Student

| Entry | Use case | WF reference | Condition / expected outcome |
|---|---|---|---|
| ACT-ST-01 | Register Student account (public) | WF-01.01; SRS UC-01 | Collect School ID, name, email and secure credentials (plus approved optional identity details); email OTP precedes creation of one Pending/inactive account. **Course/program, year level, section and subjects are not mandatory registration fields** under the proposed split. |
| ACT-ST-02 | View own academic information | WF-05.01; SRS UC-14 | View verified current-period subjects and prior-period history; subject submission is distinguished from official verification. |
| ACT-ST-03 | Request an eligible semester clearance | WF-06.01; SRS UC-16 | Only after relevant current-period subjects/instructors are verified and the approved previous-semester eligibility checks pass. |
| ACT-ST-04 | Track clearance progress/decisions | WF-06.04 | See only personal requirement status and legitimate feedback. |
| ACT-ST-05 | Generate/download authorized clearance PDF | WF-06.05 | Only issued when period/signatory requirements and access checks pass. |
| ACT-ST-06 | View own organizational fee and balance | WF-07.06 | Show independently assessed new-period fees, approved amount/effective date, and distinct older unpaid balances; no duplicate fees. |
| ACT-ST-07 | View own payments and receipts | WF-07.04, WF-07.06 | No cross-student or privileged transaction data. |
| ACT-ST-08 | Participate in group formation and exact-point peer rating (proposed) | WF-08 (IDs unassigned); SRS UC-17 | Respond to eligible invitations and leader nominations; rate **only other eligible groupmates** by distributing each Instructor-set category budget exactly; no self row or duplicate final allocations. |
| ACT-ST-09 | Manage own profile and password/email | WF-04.01–05 | Protected personal updates with appropriate verification. |
| ACT-ST-10 | Read announcements/notifications | WF-09.02–05 | See relevant messages and own read states only. |
| ACT-ST-11 | Submit/track account concerns | WF-10.01, WF-10.04 | Own support case and permitted responses only. |
| ACT-ST-12 | Complete Student Semester Onboarding (proposed) | WF-05.01, WF-05.04 (existing categories; no new ID) | At first approved login and every subsequent new Active semester, open **Semester Academic Information Setup**; review read-only School Year/Semester and enter or confirm course/program, year level, section and enrolled subjects for verification before normal Student Dashboard access. |
| ACT-ST-13 | Correct and track semester onboarding (proposed) | WF-05.01 (existing category) | Save/revise drafts; correct semester course/program, year level, section and subject data; track Submitted/Needs Correction/Verified or officially Not Enrolled status. Student edits do not establish authoritative academic status. |
| ACT-ST-14 | Request own group transfer or report membership mistake (proposed) | WF-08 category only | Request transfer from current group to eligible destination and state a reason; existing membership stays active until Instructor decision. Request correction of mistaken member/leader placement through a distinct review path. |
| ACT-ST-15 | Distribute Instructor-defined category points to groupmates (proposed) | WF-08 category only | See other groupmates as rows, categories and budgets as columns, automatic row totals and category-total verification; submit only when each category sum equals the full budget. |

**Student enrollment boundary:** At first approved Student login and each newly Active semester, the Student is proposed to confirm **course/program, year level, section and enrolled subjects** for clearance preparation. CTU-G Workspace must not treat self-entered academic information as authoritative enrollment evidence, nor implement its own enrollment-management authority. The **School Year and Semester are derived from the Active period and displayed read-only**; existing verified data may be prefilled for student confirmation, not treated as newly verified merely because a student clicks Continue. Previous-semester-clearance prerequisites remain separate from new onboarding and fees; the exact gate, exception and verification contracts require owner approval.

## 5. Summary access matrix

**Legend:** **G** = protected governance; **M** = intended operational management; **A** = assigned/scoped action; **O** = own-record access; **R** = read-only/scoped; **—** = no standing permission. These are **design intents**, not live role grants; effective permissions and record scopes decide runtime access.

| Workflow category | Technical Super Admin | School Admin | Instructor | Treasurer | Student |
|---|---|---|---|---|---|
| WF-01 Authentication | O | O | O | O | O |
| WF-02 Account Management | M | M | — | — | — |
| WF-03 Access Control Management | G (subject to exact permissions) | — (may view own/eligible roles in school account detail, not manage access control) | — | — | — |
| WF-04 Profile Management | O | O | O | O | O |
| WF-05 Academic Information / Semester Onboarding | A | M (period activation) | A/R (assigned) | R (if assigned) | O (submit/verify status) |
| WF-06 Clearance Management | A | M | A | A | O |
| WF-07 SSG Financial Management | R (if granted) | R (if granted) | R (Advisor only) | M (verified assessment) | O (period fees) |
| WF-08 Group Rating (draft) | — | A (if granted) | A | O (if Student) | A/O |
| WF-09 Announcements & Notifications | M | M | R | R | R |
| WF-10 Account Concerns & Support | M | M | O | O | O |
| WF-11 System Administration & Configuration | G | M (school settings) | — | — | — |
| WF-12 Audit, Security & Monitoring | G | R (if granted) | — | — | — |
| WF-13 Reporting & Document Generation | A | M | R (if granted) | A | O (own PDFs) |

**Caution:** This matrix should not be converted into permission seeds or a default role catalogue without independent review. The Technical Super Admin cannot freely access all financial and educational records merely because of governance status.

## 6. Detailed representative use-case specifications

The detailed cases below are **design descriptions**. For cases whose workflow in the catalogue says “Not yet inspected,” the main/alternative steps are proposed for later reconciliation, not claims about existing APIs or implemented behavior.

### UC-D01 — Student email-OTP registration

**SRS link:** UC-01. **Workflow:** WF-01.01. **Actor:** Public Student Applicant. **Status:** Development-implemented and locally verified in catalogue; Human Approval/policy decisions pending.

- **Trigger:** Applicant selects Student and chooses **Proceed Email Verification**.
- **Preconditions:** Registration, approved temporary writer, CSRF protection and email OTP delivery available.
- **Main success flow:** (1) Enter School ID, verified recipient email, first/last name, password/confirmation and permitted optional stable identity information. **Do not require semester-dependent course/program, year level, section or enrolled subjects during public account registration.** (2) Validate inputs and Student requested role; check conflicts. (3) Hash password and securely stage registration without creating an account. (4) Send OTP, show code screen, and verify code within configured limits. (5) In one transaction, recheck uniqueness, create linked account/profile with Pending/inactive status and email-verification proof, then consume stage. (6) Inform applicant that School Admin review follows.
- **Alternatives/failures:** Invalid form, generic duplicate conflict, staging/email outage, OTP resend/expiry/attempt exhaustion, original-browser stage continuation, uncertain network response and transaction rollback. No automatic retry or unauthorized reuse of another browser's stage.
- **Postconditions:** Exactly one account/profile after successful verification; zero assigned application roles; no login session. No permanent account for unsuccessful/unverified attempts.
- **Acceptance evidence required:** Validity, duplicate and concurrency tests; safe OTP handling; rollback; CSRF; frontend/accessibility and actual inbox acceptance before production.

### UC-D02 — Instructor email-OTP registration

**SRS link:** UC-01. **Workflow:** WF-01.02. **Actor:** Public Instructor Applicant. **Status:** Development-implemented/verified per catalogue, but earlier source audit identified discrepancies; reconcile against current files and seek Human Approval.

- **Trigger:** Applicant selects Instructor and **Proceed Email Verification**.
- **Preconditions:** Instructor role enabled for registration, approved staging/OTP writer and email delivery available.
- **Main success flow:** (1) Enter **Staff ID of 1–7 ASCII digits**, email, first/last name, password/confirmation, optional middle/suffix. (2) Reject Student-only school-information fields; use existing `accounts.school_id` for Staff ID with leading zeroes preserved. (3) Validate uniqueness, hash password and stage immutable Instructor identity. (4) Send and verify code within configured restrictions. (5) Atomically create email-verified Pending/inactive Instructor account/profile and consume stage. (6) Refer applicant to School Admin eligibility review.
- **Alternatives/failures:** Generic Staff ID/email 409 before/after OTP; original-browser-only continuation; conditional forgot-password action; configured support contact/fallback; honest delivery errors, expiry, rate limits, invalid OTP and uncertain-result status check.
- **Postconditions:** Pending/inactive verified applicant, no assigned role or authenticated session; OTP does **not** establish employment eligibility.
- **Acceptance evidence required:** Instructor-specific UX/wording tests and manual review of the prior contradictory audit; protected-writer, browser and delivery acceptance.

### UC-D03 — School Admin approves an applicant

**SRS link:** UC-02. **Workflow:** WF-02.01–03. **Actor:** Authorized School Admin (or inheriting Technical Super Admin). **Status:** Draft/not yet inspected in catalogue.

- **Trigger:** Reviewer opens a Pending application and selects Approve.
- **Preconditions:** Reviewer has approval permission, is not applicant, requested role is eligible and required verification evidence is available.
- **Proposed main flow:** (1) Review submitted identity, email proof and academic/instructor eligibility. (2) Confirm the decision and correct initial Student/Instructor role. (3) Under a guarded transaction, record reviewer attribution, set Approved/active and assign only approved first role. (4) Notify applicant of the decision through allowed channels.
- **Alternatives:** Unverified legacy Pending account, ineligible applicant, expired evidence, conflicting reviewer, duplicate action or database/notification error: refuse, rollback or preserve a recoverable state without false success.
- **Postconditions:** Eligible approved account with assigned base role; requested role alone never authorizes access.
- **Required decisions:** D-09 legacy email-proof eligibility, verified academic/employment source and notification guarantees.

### UC-D04 — School Admin rejects an applicant

**SRS link:** UC-03. **Workflow:** WF-02.04. **Actor:** Authorized School Admin. **Status:** Draft; a preserved sample in catalogue is not approved.

- **Trigger:** Reviewer selects Reject on a Pending application.
- **Preconditions:** Authorized non-self review; eligible Pending application; notification/deletion recovery policy defined.
- **Proposed main flow:** (1) Review applicant and required reason. (2) Confirm rejection and send a truthful rejection notification by email. (3) Delete rejected registration account/data under the approved privacy/audit policy. (4) Present a reliable result to reviewer. (5) Permit a **new standard registration**, including reuse of same School ID/email when no longer reserved.
- **Alternatives:** Email delivery or deletion failure, repeated request, concurrent approval, privacy/audit retention conflict. Do not claim the request completed if one required effect did not occur; use approved compensation/retry mechanism.
- **Important conflict:** Older SRS FR-REG-07 describes retaining rejected request history. The **newer catalogue and project-owner decision** require notification and deletion of rejected registration data; exact audit-minimization and failure sequencing need explicit reconciliation.

### UC-D05 — Technical Super Admin assigns an ordinary additional role

**SRS link:** UC-05, UC-11, UC-13. **Workflow:** WF-03.01. **Actor:** Authorized Technical Super Admin (ACT-TS-11); Django Superuser may use its separate protected configuration procedure. **Status:** Owner-directed requirement alignment; implementation and bootstrap blocked.

- **Preconditions:** Approved active target; authorized Technical Super Admin holds the Admin + Technical Super Admin roles and the exact effective role-assignment permission, or Django Superuser uses the separately protected audited administrator channel; role is on approved allowlist; duties are eligible. School Admin is not an actor.
- **Proposed main flow:** (1) View target roles. (2) Select an ordinary additional role (e.g., eligible Student+Treasurer or Instructor+SSG Advisor). (3) Review scope and separation-of-duties warnings. (4) Confirm an audited role assignment. (5) Re-evaluate effective permissions for next authorized request.
- **Alternatives:** School Admin attempts any assignment; Technical Super Admin attempts Technical Super Admin promotion; untrusted superuser flag in normal API; self-change, ineligible or protected target, financial self-interest, duplicate role, last-operator violation, missing audit or stale session — deny without partial change.
- **Postconditions:** Original role preserved unless separately revoked; protected governance unchanged.

### UC-D06 — Technical Super Admin changes role-default permission

**SRS link:** UC-06–07. **Workflow:** WF-03.02–05. **Actor:** Application Technical Super Admin. **Status:** Protected design proposal; live governance activation requires separate approval.

- **Preconditions:** Protected authority granted through approved governance composition; service active; independent audit/actor invariant satisfied.
- **Proposed main flow:** (1) Select a role and service permission. (2) Preview affected account populations and potential self/other escalation. (3) Obtain required governance approvals. (4) Atomically modify role default and write audit record. (5) Confirm affected effective-permission behavior with Deny precedence.
- **Alternatives:** Normal Admin attempts change, protected target, last-operator risk, missing audit actor, audit insertion failure or direct privilege bypass — deny/rollback.
- **Postconditions:** Only approved grants take effect, audit remains attributable, and no privileged bypass arises from role names.

### UC-D07 — Treasurer assesses organization fee for a period

**SRS link:** UC-15 and candidate finance requirements. **Workflow:** WF-07.01–02, WF-07.08. **Actor:** Authorized Treasurer. **Status:** Draft and policy-dependent.

- **Preconditions:** Official period/fee policy is defined; CTU-main-system enrollment is verified or approved manual verification exists; actor has scope permission.
- **Proposed main flow:** (1) Receive official enrollment/eligibility verification for the Active period, either during Student Semester Onboarding verification or through an authorized upstream/verified batch process. (2) Confirm the applicable Student, Active Period and approved Fee Type/rate/exemptions. (3) Determine the approved obligation effective date independently of the login/onboarding date. (4) Atomically check and create-or-return the unique Student + Period + Fee Type obligation, recording the policy/version and verification evidence reference. (5) Show the result in the current-period finance view without mixing prior debt; issue a separate clearance requirement if policy calls for it.
- **Alternatives:** No valid Active period, not enrolled, awaiting verification, newly transferred, returning after a gap, duplicate onboarding/import, late official verification, overlapping workers, expired/changed fee schedule, policy exemption, corrected or revoked eligibility, already-paid/reversed obligations, disputed fee and own Student+Treasurer account. No charge for confirmed not-enrolled periods; keep unknown status on hold. An authorized correction/reversal must preserve an audit trail, not silently delete history.
- **Postconditions:** A correct, auditable, deduplicated period-specific obligation **only if official eligibility and approved policy permit**, even if the student has not logged in yet. No authoritative enrollment updates in CTU-G Workspace. A transaction failure must not create a partial fee or duplicate side effect.

### UC-D08 — Student requests and tracks clearance

**SRS link:** UC-16. **Workflow:** WF-06.01–05. **Actors:** Student, assigned Instructor/Treasurer signatory, School Admin for configuration. **Status:** Draft and dependent on academic-period rules.

- **Preconditions:** Authenticated approved Student; valid Active academic period; current-period onboarding/verified enrolled subjects and assigned signatories established as policy requires. Historical clearance records are preserved.
- **Proposed main flow:** (1) System takes the current eligible Active period from School Admin configuration. (2) It validates verified current subjects and corresponding Instructor assignments; self-reported, unverified subjects cannot create real signatory duties. (3) It applies the separately approved previous-semester-clearance prerequisite and exemptions. (4) It generates one set of scoped academic and SSG fee-related clearance requirements for that period. (5) Assigned signatories decide only their items, preserving evidence. (6) Student tracks progress. (7) A PDF is issued only when every applicable requirement is satisfied.
- **Alternatives:** First semester/no prior clearance, returning after gap, irregular student with individually verified subject roster, missing official assignment, onboarding still Submitted or Needs Correction, signatory conflict, new-period unpaid fee, old outstanding obligation, duplicate clearance request and unavailable data. Previous-period debt/clearance is not erased or silently rolled into the new-period record. These cases require approved policy, not implicit acceptance.
- **Postconditions:** Period-scoped decision/status; no fabricated sign-off or unrestricted signature access.

### UC-D09 — Instructor and Student use Group Rating (WF-08 umbrella)

**SRS link:** UC-17 / FR-RAT-01–04. **Workflow:** WF-08 **category only; no approved subflow IDs**. **Actors:** Assigned Instructor and eligible Student (including Group Leader). **Status:** Draft — stakeholder-selected design proposals added in v0.4.

- **Proposed scope:** (1) Assigned Instructor opens a class/semester-specific activity and configures group formation. (2) Instructor nominates leaders; accepted leaders invite classmates and Students accept/decline. (3) Instructor resolves unassigned Students, transfers and roster corrections, then finalizes eligible groups. (4) Instructor defines any practical number of named categories and a positive point budget for each category. (5) Each Student allocates each category's full budget **only to other eligible groupmates**, never themselves. (6) System validates category totals and saves attributable, nonduplicated submissions. (7) Calculation, disclosure and publication of results remain separately undecided.
- **Alternatives:** Invalid class or academic-period eligibility; declined/expired invitation; inadequate or oversized group; incomplete formation; direct Instructor assignment; contested roster; leader successor; post-finalization amendment; missing rater/recipient; departed member; wrong/excess/short category total; duplicate submission; concurrent edits; category change after submissions start.
- **Non-assumption:** No point budget, category weighting, rating scale, results-visibility rule, group-size minimum/maximum or WF-08.xx sub-ID is approved by this use-case document. The chosen method is *exact category-budget distribution*, replacing the earlier proposed independent 0–5 / 0–10 / 0–100 score-per-student approach.
- **Detailed proposed cases:** See UC-D14 (formation), UC-D15 (transfers and corrections), and UC-D16 (peer point allocation) plus Section 6.3.

### UC-D10 — Multi-role shared dashboard with no permission bypass

**SRS link:** UC-04, UC-11–13. **Workflow:** WF-01.03, WF-03.05, WF-04, WF-07. **Actors:** Any approved multi-role account. **Status:** Proposed functional behavior.

- **Proposed main flow:** (1) Authenticate in one browser session. (2) Server evaluates active account, approved roles, direct overrides, Denies and service availability. (3) For the Student context only, verify period-specific onboarding eligibility; redirect incomplete Students to restricted semester setup/status rather than normal Student Dashboard. (4) Render accessible navigation for other independently permitted roles. (5) Recheck effective permission, onboarding eligibility where relevant, and record/period scope at every protected API.
- **Alternatives:** Role just revoked, account disabled, service disabled, direct Deny, expired session, new period activated mid-session, onboarding Submitted/Needs Correction, Student+Treasurer dual-role account, own-finance conflict. Essential support/logout/allowed prior-clearance access must remain available; no UI-only bypass of server enforcement.
- **Postconditions:** A single user/profile; no duplicated account, no separate role-login, and no information leakage to unentitled records.


### UC-D11 — School Admin creates and activates a new semester (proposed)

**SRS link:** UC-14 (conceptual). **Workflow:** WF-05.04 and WF-11.01 **existing category references only**; no approved new subworkflow ID. **Actors:** School Admin, inheriting Technical Super Admin. **Status:** New v0.2 proposal; not implemented or approved.

- **Trigger:** Authorized School Admin prepares a new School Year/Semester or selects an eligible Scheduled period for activation.
- **Preconditions:** Calendar configuration is authorized; institutional academic calendar is consulted; the proposed period belongs to the correct campus scope; existing state and dependencies are available.
- **Proposed main flow:** (1) Create a school year and its semester periods as Draft, with unique identity and valid dates. (2) Review and optionally move a period to Scheduled. (3) Display a preflight summary of current Active period, potential impact on Student onboarding, Clearance and Finance, pending reconciliations, and date conflicts. (4) Require authorized human confirmation. (5) Atomically close the previous period and activate **exactly one** new semester for the campus scope; record actor, timestamp and reason. (6) Invalidate or update active-period caches as needed and show the new period as read-only metadata to users. (7) Establish eligibility for new per-period onboarding; do **not** automatically create Student enrollments, fee debt, paid status or clearance sign-offs.
- **Alternatives/failures:** Duplicate term, missing school year, invalid/overlapping calendar, stale confirmation, simultaneous activation, missing policy, pending settlement, permission denied, database write/audit failure, expired session and rollback. Do not force the previous period closed if the new one cannot be activated. Changes to a Closed period or re-opening require a separately approved exceptional procedure.
- **Postconditions:** One current Active semester, earlier period records preserved, auditable transition and correct default period for academic, clearance and finance services. No blanket fees are created from activation alone.
- **Required approvals:** Scope of one-active-period uniqueness, School Admin authority, Approved vs Scheduled transitions, activation timing, exceptional re-open/rollback policy, and period change notices.

### UC-D12 — Student Semester Onboarding: Semester Academic Information Setup (proposed)

**SRS link:** UC-14, UC-16 (candidate expansions; not approved new SRS cases). **Workflow:** WF-05.01, WF-05.04, WF-06 and WF-07 **existing categories only**. **Actors:** Student, CTU main system/authorized verifier, authorized Reviewer where manual verification is permitted. **Status:** New v0.2 proposal; not implemented or approved.

- **Trigger:** An approved Student first enters Student services after account approval, or a later semester becomes Active, and no **Verified** Student Semester Onboarding record exists for that academic period.
- **Preconditions:** Student account Approved/active; there is one authorized Active period; a verified academic-data source or approved manual verification process exists.
- **Proposed main flow:** (1) Authenticate normally, then detect the missing/current-period onboarding state. (2) Route the Student to the restricted **Semester Academic Information Setup** page before normal Student Dashboard access; show **School Year and Semester as read-only Active-period metadata**, never editable text. (3) Prepopulate trusted academic information when available, otherwise request provisional **Course/Program, Year Level, Section and Enrolled Subjects**; for each subject, capture the minimum approved subject identity and class/section details needed for verification and clearance. Provide an irregular-student path for mixed-year or different-section subjects. (4) Validate required fields, legitimate programme/year/section choices, subject identity, duplicate subject entries and approved size limits; allow Draft and explicit Submit. (5) Save a period-specific **Submitted** request with integrity protections and actor attribution, without asserting official enrollment. (6) Verify enrollment, course/year/section, enrolled subjects and subject–Instructor assignments using CTU's main system or an approved independent verifier; label all unverified entries as provisional. (7) Mark **Verified** or **Needs Correction** with actionable feedback; do not equate student confirmation with verification. (8) Ensure approved organization-fee assessment occurs at most once per eligible Student/Period/Fee Type when official eligibility is verified, **whether verification occurred during onboarding or earlier through authorized synchronization**. Prepare clearance requirements from verified academic and financial evidence only. (9) Permit normal Student Dashboard access after the approved Verified gate, with current-period academic information, fee status and clearance status.
- **Proposed statuses:** Not Started → Draft → Submitted → Verified; Submitted → Needs Correction → resubmission; a **Not Eligible / Not Enrolled** outcome must be based on official evidence and have a documented correction path. These are *conceptual states*, not approved database enums.
- **Alternatives/failures:** First approved login, new semester transition, course/program change, year-level progression, section transfer, first enrollment, transferee, irregular or cross-section subject load, return after inactive semester/year, late registration, approved Student with no eligible classes, upstream CTU outage, unverified or contradictory roster, incorrect entry, repeated submit, browser refresh, concurrent editing, period activation mid-session, submission after close, duplicate onboarding, role-switching, old uncleared semester and unassigned Instructor. Unverified Student stays in restricted onboarding/support/status access; they cannot circumvent the server-side Student dashboard/clearance gate. Other independently authorized roles must remain usable, subject to their own permissions.
- **Postconditions:** At most one authoritative onboarding status per Student/period; verified current-period academic facts are usable for clearance. An unverified Student creates **no new fee debt solely by submitting subjects**. Prior subjects, clearance, receipts and fees remain in their original periods.
- **Required approvals:** Source-of-truth data exchange, whether verification must finish before Dashboard access, limited-access exceptions, course/program/year-level/section and subject field contracts, irregular subject handling, correction ownership, timeouts, retention, and handling for officially non-enrolled students. The initial registration field split must be reconciled with the current WF-01.01 contract and existing frontend/backend validation before any code change.

### UC-D13 — New semester onboarding connects fee obligation and clearance (proposed)

**SRS link:** UC-14–16 and candidate finance amendments. **Workflow:** WF-05, WF-06, WF-07 existing categories; **no new workflow ID assigned**. **Actors:** Student, authorized academic verifier, Treasurer, assigned Instructor, background assessment process as designed. **Status:** New v0.2 cross-module proposal.

- **Trigger:** A Student's current semester enrollment eligibility is officially verified during onboarding **or through authorized verified synchronization before login**.
- **Proposed main flow:** (1) Confirm verified enrollment in the exact Active academic period and read the approved fee policy. (2) If the Student is liable, perform transactional/idempotent **Student + Period + Fee Type** assessment with approved amount, effective date, evidence reference and audit trail. (3) Repeated onboarding, retries and late login return the existing obligation rather than create a duplicate. (4) Prepare the current-period academic and Treasurer clearance requirements only when corresponding source records and assignments are verified. (5) Show current obligation/status separately from historical debts and previous semester clearance. (6) Follow independent payment, clearance decision and PDF issue workflows.
- **Alternatives:** Not enrolled, already assessed, verified late, assessed upstream earlier, schedule not approved, exempted Student, returning after gap, fee policy amended after assessment, reversal/correction, unavailable upstream verification, unpaid past fee, missing Instructor or a Student–Treasurer conflict. A Student who is not enrolled in a period receives no new charge for that period solely due to account status or activation.
- **Temporal rule:** Actual obligation effective date follows the **approved fee policy and verified enrollment**, not the Student's first login, self-entered subjects, or the activation event by itself. Verified synchronization may precede onboarding and must produce the same single obligation if eligible.
- **Postconditions:** At most one valid obligation per Student/Period/Fee Type under policy; period-scoped clearance requirements and historical debts remain distinct; audit and reversal procedures preserve financial integrity.
- **Dependencies:** Specific policy amounts/exemptions, source-of-truth integration, unique constraint design consistent with official ERD, clearance signatory assignments, notification policy and exception review.

### 6.1 Cross-module academic-period transition contract (v0.2 proposal)

| Event / state | Student access | Current-period organization fee | Clearance |
|---|---|---|---|
| Draft/Scheduled semester | Current Active period remains in effect | No charges solely because next term is drafted/scheduled | Current and historical records remain unchanged |
| New semester becomes Active | **Student Semester Onboarding** becomes required; **Semester Academic Information Setup** opens with read-only period information | No blanket charge at period activation | New period eligible for preparation, no automatic approval |
| Student submits semester course/year/section/subjects; verification Pending | Restricted Student onboarding/status/support (and permitted past-clearance access) | No charge based only on self-submitted data | No official Instructor signatory obligations from unverified subjects |
| Enrollment verified as eligible | Normal Student Dashboard allowed once onboarding is Verified | Create/confirm one applicable obligation per Student/Period/Fee Type under approved policy | Prepare verified subjects, Instructor signatories and period fee requirement |
| Official status Not Enrolled | Student receives documented correction/support route | Do not assess an un-enrolled period | Do not fabricate a clearance for that period |
| Student returns after a gap | New relevant Active period onboarding/verification needed | Eligible new period only; old liabilities remain separate | Prior-period records preserved; approved returner exceptions apply |
| New period follows unpaid prior semester | Student onboarding/verified enrollment proceeds independently | New valid obligation separate from old unpaid balance | Prior-semester clearance gate handled by its own approved eligibility policy |

**Consistency guarantees:** The campus period scope must have a reliable one-Active rule; Student onboarding must be scoped by account/academic period; official enrollment evidence must be attributable; financial assessments must be idempotent and transactional; older academic, clearance and payment history must not be overwritten. No new columns, tables, enums, migrations, role grants or workflow IDs are authorized by this document.

### 6.2 Student Semester Onboarding — page and data contract (v0.3 proposal)

**Official feature/workflow name:** **Student Semester Onboarding**. **Student-facing page title:** **Semester Academic Information Setup**. This page is displayed after authenticated login when the Student lacks a Verified onboarding outcome for the Active academic period. It is **not** a new account-registration form and does **not** ask the Student to reset their School ID, email or password.

| Field / information | One-time public Student Registration (WF-01.01) | Semester Academic Information Setup (proposed WF-05 scope) | Verification / authority |
|---|---|---|---|
| School ID, first/last name, email, password | Required as currently approved by the registration contract | Not re-entered; existing account identity used | Registration/approval workflow; sensitive changes belong in secured profile/account workflows |
| Course / Program | Not a required registration field under proposed split | Review, select or correct for each Active period | CTU main system or authorized academic verifier |
| Year Level | Not a required registration field under proposed split | Review, select or correct for each Active period | CTU main system or authorized academic verifier |
| Section | Not a required registration field under proposed split | Review, select or correct for each Active period; allow authorized exceptions for irregular/no-single-section enrolment | CTU main system or authorized academic verifier |
| School Year and Semester | Not collected from applicant for period onboarding | Display **read-only** from the one Active academic period | School Admin period configuration aligned with CTU calendar |
| Enrolled Subjects / Class Sections | Not collected as mandatory registration fields | Confirm prefilled verified data or provisionally provide each subject/class needed for current-period clearance | Official CTU enrolment, timetable/assignment data or authorized verification; typed entries are unverified until confirmed |
| Assigned Instructors | Not entered in registration | Display verified assignment; unresolved assignment goes to review | Trusted academic assignment source; a Student cannot assign their own Instructor |
| SSG Organizational Fee | Never entered or selected by applicant | Read-only applicable assessed amount/status when available | Separate idempotent SSG Finance assessment using verified eligibility and approved fee policy, potentially before onboarding/login |

**Page-level behavior and guards:**

1. Clearly state **“Semester Academic Information Setup”**, and display the current **School Year** and **Semester** as immutable system metadata. Explain that the process is required for the new Active term, not a second account registration.
2. Show validated Course/Program, Year Level and Section inputs; show an accessible add/edit/remove list of current subjects. Prefer CTU-verified picklists and prefilled values; allow provisional manual entry only when policy allows. Irregular Students must be able to submit legitimate mixed-section subjects without falsifying an overall Section.
3. Support **Save Draft**, **Submit for Verification**, **View Status** and **Correct and Resubmit** as permitted. Use conceptual statuses **Not Started, Draft, Submitted, Needs Correction, Verified** and the independently verified **Not Eligible / Not Enrolled** outcome. Do not silently advance an unverified submission to Verified.
4. The server enforces the normal Student Dashboard gate for the Active period; while pending or unverified, keep eligible account support, Logout, correction, onboarding status and permitted historical clearance/payment access. Preserve independently authorized non-Student roles on the same account.
5. Preserve prior semesters' verified academic/clearance/fee records; do not overwrite the Student's stable account identity or create an authoritative enrollment record inside CTU-G Workspace.
6. Fee eligibility may be verified independently of this page. The Student can view a correctly assessed current-period fee but **cannot choose, create, remove, waive or approve their own organization-fee obligation**. The obligation is never created solely because the Student opens or submits this form.

**Implementation boundary:** This is an approved terminology direction and a **proposed business/data contract**, not authorization to change the existing WF-01.01 frontend fields, official ERD, workflow sub-IDs, database models, permissions, or live finance rules. Follow Inspect → Reconcile → Approve → Implement → Test → Commit for any implementation.

### UC-D14 — Form and finalize groups under Hybrid Group Management (proposed)

**SRS link:** UC-17 / FR-RAT-01–02. **Workflow:** WF-08 category only; no new workflow ID. **Actors:** Assigned Instructor, nominated Group Leader, eligible Students. **Status:** Proposed design selection; not implemented/approved.

- **Trigger and preconditions:** Instructor with a verified assigned class creates a group activity for a specific subject, class and academic period; CTU-verified roster or authorized verification evidence is available. Student Semester Onboarding alone does not prove class membership.
- **Main success flow:** (1) Instructor selects activity and proposed minimum/maximum group size, formation deadline and invited roster. (2) Instructor nominates eligible Group Leaders; initial nominees confirm/decline their leadership appointment. (3) Accepted Group Leaders invite eligible classmates. (4) Students accept or decline their own invitations; confirmed membership is recorded only after server-side eligibility and capacity rechecks. (5) Instructor reviews groups and unassigned Students. (6) Instructor may extend a deadline, request further invitations, or directly assign an eligible Student with a reason and a correction path. (7) Instructor validates complete accounting of eligible Students, authorizes any size exception within an approved hard cap, and finalizes the roster; ordinary invitation/membership edits then close.
- **Alternatives/errors:** Declined nomination; leader inactive; invitation expired/cancelled; concurrent acceptance of last slot; multiple pending invitations; ineligible or irregular Student; full or undersized group; class roster changes; outstanding unassigned Students; lost Instructor assignment; duplicate group membership; repeated finalization; notification failure.
- **Postconditions:** For one activity, a Student belongs to no more than one confirmed group. A finalized roster has attributable membership and leader history. Direct Instructor assignments are identified as such—not misrepresented as accepted invitations. Unresolved Students require documented assignment or approved exception rather than silent omission.

### UC-D15 — Request group transfer and correct membership/leadership (proposed)

**SRS link:** UC-17 / FR-RAT-02–03. **Workflow:** WF-08 category only; no new workflow ID. **Actors:** Student requesting their own transfer; assigned Instructor approving or correcting; affected Group Leaders receiving notifications. **Status:** Proposed.

- **Trigger/preconditions:** Student belongs to a valid group in a verified activity and requests a new eligible group, providing a reason. The current membership stays in force while Pending.
- **Main success flow:** (1) Student selects eligible destination and requests transfer. (2) System prevents duplicate unresolved requests and validates same-activity eligibility. (3) Instructor reviews the source and destination groups, minimum/maximum capacity effects, current leader and roster version. (4) Instructor approves or rejects with a documented decision. (5) When the departing Student is the current Group Leader, Instructor directly designates an eligible existing source-group member as successor **without a separate acceptance step**; the system notifies successor and permits an assignment-concern/correction request. (6) Approval atomically applies transfer, successor if needed, roster revision and required audit; rejected requests leave membership unchanged. (7) Affected parties receive truthful notices through a failure-tolerant notification mechanism.
- **Membership correction:** A Student may report a mistaken group or leadership record separately. Instructor verifies and corrects it with attributable history; this is **not** an Instructor-initiated ordinary transfer or fabricated Student consent.
- **Before/after finalization:** Ordinary moves are permitted only during formation and after all checks; finalized groups require a controlled roster-amendment review. If rating submissions already exist, ordinary transfer/leader replacement must be blocked pending a separately approved rating-integrity policy.
- **Departure policy:** No automatic replacement member is required when an ordinary Student leaves. If a departed member remains in an eligible evaluation roster, peer raters may deliberately allocate zero points to that member in each applicable category; **do not generate zero ratings automatically**. Whether officially authorized transfers/withdrawals retain evaluation eligibility is still a policy decision.
- **Failure/edge cases:** Student withdrawal of Pending request, former leader has no eligible successor, successor disputes designation, class/section change, source group falling below minimum, destination full, duplicate/competing approvals, Instructor reassignment, activity closure, offline retry, and audit failure. All protected writes must revalidate and fail atomically.

### UC-D16 — Submit exact Instructor-defined peer point allocations (proposed)

**SRS link:** UC-17 / FR-RAT-01, FR-RAT-03–04. **Workflow:** WF-08 category only; no new workflow ID. **Actors:** Eligible group member, including Group Leader; assigned Instructor as sheet/configuration owner. **Status:** Proposed.

- **Preconditions:** Verified group roster, eligible subject/activity and assigned Instructor; published sheet with at least one valid category, each having an Instructor-configured positive points budget; a Student has at least one *other* eligible groupmate to rate. Category and roster snapshots/revisions are available to establish consistent submissions.
- **Main success flow:** (1) Instructor adds and describes a flexible number of categories and defines a **point budget per category**; reviews and publishes the sheet. (2) Student opens the activity and sees a **table with other eligible groupmates as rows (self is absent), Instructor-created categories with budgets as columns, and Total as the final column**. (3) Student enters nonnegative point allocations (including 0) to each groupmate for every applicable category. (4) UI calculates each **row Total** (sum across categories) and **category Distributed** total (sum down groupmates). (5) Student may submit only when, for **every category**, the Distributed total equals **exactly** the Instructor-set points budget; backend independently verifies category sums, eligibility, version, ownership, valid values and one final allocation per rater/activity/sheet as defined by approval. (6) The system atomically records the submission without fabricated ratings or unauthorized disclosure.
- **Examples:** For a category budget of 10: `4 + 3 + 3 = 10` valid; `5 + 3 + 1 = 9` invalid; `5 + 4 + 2 = 11` invalid; `10 + 0 + 0 = 10` valid. If the Instructor configures 10, 10 and 20 across three categories, **each rater** must distribute 40 points in total but must satisfy each category independently; this is not a shared budget among all group members.
- **Alternatives/errors:** Rater attempts self-insertion, other group/class/period member, empty/unrated cell mistaken for explicit 0, negative/nonfinite/fractional values (precision policy pending), sum below/above budget, duplicated submit, concurrent change, no eligible recipients (one-person group), departed member roster eligibility, changed Instructor assignment, changed category definitions after rating begins, and unavailable service. Keep an incomplete sheet as Draft; never silently round or rebalance allocations to force a valid total.
- **Scoring boundary:** **How each recipient's points from multiple raters are aggregated, how group sizes affect comparisons, whether categories carry weights, corrections after submission and who sees published outcomes are NOT decided here.** Ordinary category/point-budget edits must freeze once first submissions are accepted; any later adjustment requires a separately reviewed revision and historic traceability.

### 6.3 WF-08 Group Rating — proposed UI/data contract (carried forward from v0.4)

**Student-facing grid:** the logged-in Student is *excluded* entirely from recipient rows. The first column contains **Groupmate**, the middle columns contain the Instructor-created **rating categories with per-category budgets**, and the final column contains **Total**. A final summary row labeled **Total Distributed** validates each category against its exact budget. The table contains only that logged-in rater's editable allocation and must not expose the other raters' private allocations.

**Illustrative Student A example (not a configured production scale):**

| Groupmate | Participation (10 pts) | Cooperation (10 pts) | Contribution (20 pts) | Total |
|---|---:|---:|---:|---:|
| Student B | 4 | 3 | 8 | 15 |
| Student C | 3 | 2 | 7 | 12 |
| Student D | 3 | 5 | 5 | 13 |
| **Total Distributed** | **10/10** | **10/10** | **20/20** | **40/40** |

**Submission rules:**

1. The Instructor can define category names/descriptions and a point budget **separately for every category**. Category count is flexible; implementation may apply justified performance, input-size and validation safeguards instead of an arbitrary small fixed number.
2. A rater and Group Leader use the **same** eligible-recipient and exact-budget rules. The rater is not rendered among recipient rows and cannot inject themselves through the API.
3. Zero is a deliberate numerical allocation; an empty/unanswered input is **not** zero. Exact category totals are required even if some groupmates receive zero.
4. Only the owning Student's draft allocations appear in their form. Group Leaders cannot edit another Student's allocations. The server performs authoritative eligibility, group, assignment, budget, roster-version and duplicate checks.
5. A one-person group cannot submit peer allocation because it has no eligible recipient; it requires an Instructor resolution. Departed-member eligibility depends on a preserved roster/evaluation policy, and absent/departed status itself never manufactures zero scores.
6. Disallow ordinary changes to published scoring definitions once submissions begin, preserve earlier submission snapshots, and record approved corrections with attribution. Results aggregation, result disclosure, weighting and publication stay unresolved.
7. Distinguish a Student's **total allocated to recipients** from the **score a Student receives from other raters**. This document does not prescribe a final grade or grading formula.

**Design scope:** The Instructor may set 10 points per category, or different amounts such as 10/10/20. The full budget is required **per rater, per category**. This replaces earlier option-based 0–5/0–10/0–100 independent scoring examples and the proposal to leave part of the budget unused.

## 7. Traceability and representative acceptance scenarios

| Test scenario | Related entries | Acceptance condition |
|---|---|---|
| AT-01 Registration | ACT-ST-01, ACT-IN-01 | Email verification precedes Pending/inactive creation; no role/session; duplicate attacks denied. |
| AT-02 Approval | ACT-SA-03 | Correct authorized reviewer; one approval and base-role assignment with attribution; no self-approval. |
| AT-03/04 Advisor | ACT-IN-06, ACT-TS-11, ACT-SA-06 (denied) | Eligible responsibility assignment only through Technical Super Admin or protected Django Superuser procedure; School Admin must be denied; Instructor monitoring remains read-only. |
| AT-05 Student+Treasurer | ACT-TR-03, ACT-ST-06 | Both allowed interfaces appear; own-finance conflicting mutation denied. |
| AT-06/07 Protected defaults | ACT-TS-02 | Super Admin can change approved defaults; School Admin denied even with forged API request. |
| AT-08/09 Admin promotion | ACT-TS-07, ACT-TS-08, ACT-TS-11, ACT-SA-06 (denied) | Approved Instructor retains Instructor while Technical Super Admin or Django Superuser assigns Admin; only Django Superuser can assign/revoke Technical Super Admin via protected audited configuration. |
| AT-10 Last operator | ACT-TS-08 | No self-grant or last-governance-operator removal outside recovery. |
| AT-11 Deny override | ACT-TS-03, ACT-TS-04 | Active Deny wins over any assigned role Grant on next request. |
| AT-12/13 Logs/framework | ACT-TS-09, ACT-SA-11, Django Superuser protected config | School Admin receives only granted redacted views; Django Superuser controls reviewed administrative configurations but never obtains an implicit ordinary Workspace API bypass. |
| AT-15 Audit rollback | ACT-TS-02, ACT-TS-11, protected Django Superuser configuration | Required audit failure rolls back protected role mutation; there is no unreviewed raw Django Admin role editing. |
| AT-16 Row scope | ACT-IN-03, ACT-ST-07 | Assigned-class and own-payment constraints enforced server-side. |
| Proposed fee tests AT-25–31 | ACT-TR-01–08 | Only after finance policy approval; verified official status, no gap charges, dedupe, actor trace and conflict controls. |
| Candidate SAP-01 Active period uniqueness | ACT-SA-07, ACT-SA-12 | Cannot activate duplicate/concurrent campus periods; previous period and audit roll back together on failure. |
| Candidate SAP-02 New-period onboarding gate | ACT-ST-12, ACT-CM-01 | Approved Student at first Student access or in a new Active period without Verified onboarding receives **Semester Academic Information Setup**, not normal Student Dashboard; backend APIs enforce the rule. |
| Candidate SAP-03 Verified academic-information source | ACT-ST-12–13, ACT-IN-03 | Student-entered course/program, year level, section and subjects cannot grant Instructor clearance access or officially establish enrollment; corrections and irregular rosters supported. |
| Candidate SAP-04 Fee assessment at verification | ACT-TR-01–02, ACT-ST-06, ACT-ST-12 | Eligible verified active-period student receives one policy-correct obligation; unverified submission/activation creates none. |
| Candidate SAP-05 Idempotence and late login | ACT-TR-02, ACT-TR-10 | Repeat submit, retry, concurrent workers and verified upstream import cannot double-charge; effective date does not depend on login. |
| Candidate SAP-06 Ineligible/absent/returning | ACT-TR-08, ACT-ST-12–13 | No fee for confirmed inactive/non-enrolled periods; returning Student assessed only for verified eligible period; old records retained. |
| Candidate SAP-07 Finance and clearance independence | ACT-ST-03, ACT-ST-06, ACT-TR-09 | Prior unpaid balance is not silently copied/erased; new clearance uses correct period and separately approved prior-clearance rule. |
| Candidate SAP-08 Multi-role/account recovery | ACT-ST-12, ACT-CM-02, ACT-TR-03 | Restricted Student onboarding does not block Logout/support/allowed old-clearance access or independently entitled Treasurer duties. |
| Candidate SAP-09 Failure recovery/accessibility | ACT-ST-12–13, ACT-SA-12 | Upstream outage, period switch, keyboard/mobile form, safe retries and transparent statuses are validated; no false success. |

| Candidate SAP-10 Registration/onboarding separation | ACT-ST-01, ACT-ST-12 | Registration accepts approved identity credentials without requiring semester-varying course/year/section/subjects; the first Student access after approval uses Semester Academic Information Setup for these fields. Existing public API validation is reconciled before a change. |
| Candidate SAP-11 Academic form and fee authority | ACT-ST-12–13, ACT-TR-02 | Read-only School Year/Semester; validated course/year/section; irregular subject rosters, safe correction, trusted Instructor assignment and read-only organization-fee display; no duplicate or self-created fees. |
| Candidate GRT-01 Activity and verified roster | ACT-IN-04, ACT-IN-08, ACT-ST-08 | Only assigned Instructor creates activity; only officially verified eligible classmates are leaders, invitees and members; no self-reported roster bypass. |
| Candidate GRT-02 Hybrid formation | ACT-IN-08, ACT-ST-08 | Leader nomination and initial acceptance; individual invitations and acceptance/decline; one confirmed group per Student/activity. |
| Candidate GRT-03 Unassigned and size exceptions | ACT-IN-08 | Instructor may extend formation, request further invitations or directly place Students with reason; size exceptions obey approved hard bounds and history; no silent omission. |
| Candidate GRT-04 Transfer and successor | ACT-IN-09, ACT-ST-14 | Only Student requests ordinary transfer; Instructor approves; when leader moves, Instructor designates successor with notice/correction path; movement and succession atomic. |
| Candidate GRT-05 Finalized roster corrections | ACT-IN-09, ACT-ST-14 | Finalized roster changes use versioned amendments; existing rating submissions block ordinary changes pending approved integrity policy. |
| Candidate GRT-06 Peer rating table / self exclusion | ACT-ST-15 | Logged-in rater absent from all editable rows; other verified groupmates are rows, Instructor categories columns, Total last column. |
| Candidate GRT-07 Exact category budgets | ACT-ST-15, ACT-IN-04 | Per category, recipient scores sum **exactly** to Instructor budget; short/over allocations refused; 0 is valid, blank is not 0. |
| Candidate GRT-08 Different budgets / totals | ACT-ST-15 | Category budgets 10/10/20 yield exactly 10/10/20 in Distributed row; per-groupmate row totals and 40/40 grand total computed correctly. |
| Candidate GRT-09 Security and concurrency | ACT-ST-15, ACT-IN-09 | API denies self/cross-group injection, unauthorized ratings or leader edits; duplicates, stale roster and concurrent submissions fail safely without partial writes. |
| Candidate GRT-10 Departure and no-peer cases | ACT-ST-15, ACT-IN-08 | No mandatory replacement when ordinary member leaves; zero must be explicit; one-person group blocked; eligibility of transferred/withdrawn recipients follows a separately approved snapshot policy. |
| Candidate GRT-11 Sheet revision and results boundary | ACT-IN-04, ACT-ST-15 | Published categories freeze at first accepted submission; ratings stay attributable/versioned; final aggregation, release and privacy remain blocked pending owner policy. |

**Verification classification:** SAP-01–11 and GRT-01–11 are **candidate local test labels**, not approved workflow IDs or confirmed automated tests. These and the other scenarios are proposed tests to implement or reconcile, **not claimed passing test runs**. Run applicable unit, integration, browser, accessibility, recovery, security and race-condition tests in disposable environments; record command, result and approval evidence.

## 8. Nonfunctional acceptance checklist (11 system qualities)

| Quality | Use-case acceptance focus |
|---|---|
| Security | Deny by default; secure sessions/CSRF, hashing, OTP protections, least privilege, row scope; server-side Student onboarding gate, verified-source integrity and no multi-role bypass. |
| Reliability | Transactional period activation and fee assessment, idempotence, honest email outcomes, safe recovery after interruption. |
| Performance | Measure onboarding/verification throughput, academic-period switch propagation, concurrent OTP load and API latency against approved benchmark; do not invent metrics. |
| Usability | Current School Year/Semester shown read-only; regular/irregular subject inputs, transparent Pending/Needs Correction/Verified feedback and recoverable restricted access. |
| Scalability | Shared throttling, bounded processing and supported growth in users and academic periods. |
| Maintainability | Modular code, stable WF/UC traceability, testable services and change history. |
| Availability | Document behavior for email, database, upstream CTU and hosting outages. |
| Data Integrity | One Active period per scope, period-scoped verified subjects, unique fees per Student/Period/Fee Type, no duplicate clearance and non-destructive history. |
| Flexibility | Configurable approved period, fee, clearance and role policies without insecure role-name hardcoding or duplicate CTU enrollment administration. |
| Accessibility | Keyboard and screen-reader form access, visible focus and WCAG 2.2 AA target. |
| Compatibility | Responsive Windows/mobile browser acceptance; separate future Flutter integration policy. |

## 9. Document governance and AI Agent Guidelines Checklist

All numbered workflows must follow **Inspect → Reconcile → Approve → Implement → Test → Commit**. The AI agent does not approve its own work; evidence is required at each stage. Final **Human Approval** remains separate. This document **does not alter workflow checklist status**.

| Stage | Document-use requirement |
|---|---|
| Inspect | Review latest catalogue, SRS, protected ERD, code, actual APIs, tests and environment. |
| Reconcile | Match actor/use case with permission code, exact fields, main/alternative/error steps, data schema and acceptance test. |
| Approve | Record explicit owner authorization for scope/policy changes; do not infer it from a proposal. |
| Implement | Update only authorized code/data; preserve schema and role-governance gates. |
| Test | Record real passing and failing checks, including security, accessibility and business alternatives. |
| Commit | Obtain repo permission as required, review for secrets, commit intended files, record SHA. |

**This use-case document:** Draft — Owner approval: ☐  Reviewer: __________  Date: __________

## 10. Open issues and decisions before full sign-off

| ID | Decision / reconciliation required | Impact |
|---|---|---|
| O-01 | WF-01 D-01–D-09 defaults, production OTP writer, delivery consistency, real inbox and Human Approval. | Student/Instructor registration release. |
| O-02 | Instructor support address and latest conflict/recovery UI versus source/tests (prior audit discrepancy). | WF-01.02 experience and acceptance. |
| O-03 | WF-02 eligibility proof, legacy Pending accounts and precise review/deletion-email recovery/audit rules. | Approval, rejection and privacy. |
| O-04 | Older SRS historical rejected-account retention versus later deletion-after-email requirement. | Requirements reconciliation. |
| O-05 | Protected governance-role name, first operator bootstrap, Super Admin promotion and last-operator policy. | Technical Super Admin activation. |
| O-06 | Exact ordinary-role assignment allowlist, Treasurer and SSG Advisor (Finance Monitor) appointment, scope and revocation. School Admin cannot assign roles; Technical Super Admin governs eligible ordinary grants, Django Superuser uses protected configuration. | Technical Super Admin / security owner. |
| O-07 | Approve official enrollment and subject/Instructor verification contract, fee effective dates, new-semester liability trigger, schedule, exemptions, transfers, gaps, corrections and authorized upstream pre-login assessment. | Treasurer, onboarding and Student finance. |
| O-08 | Set previous-semester clearance prerequisite and exceptions separately from onboarding and fees; require verified subjects/authorized signatories. | Clearance and Student onboarding. |
| O-09 | Allocate WF-08 subflow IDs only after review; reconcile proposed Hybrid group formation, Instructor-selected leaders, Student invitation acceptance, hybrid size/unassigned-student remedies, student-requested transfers, Instructor-designated successors and corrected/finalized roster behavior. | Instructor / Student group formation and changes. |
| O-10 | Official reporting access, announcement audience, auth event logging, retention, data recovery and performance targets. | Cross-cutting deployment. |
| O-11 | Approve School Admin period Create/Draft/Scheduled/Active/Closed transitions, activation dates, single-Active campus scope, exceptional reopen/rollback and period-switch notification policy. | Academic period management and all per-semester modules. |
| O-12 | Approve mandatory **Student Semester Onboarding**, student-facing **Semester Academic Information Setup**, normal dashboard gate, verifier, read-only active period fields, course/program/year level/section/subject data rules, limited-access exceptions, and irregular/returning Student handling. | Student dashboard, Academic Information and Clearance. |
| O-13 | Approve automatic obligation assessment timing, verified upstream pre-login import, Student+Period+Fee Type deduplication, idempotent worker behavior, approved fee schedule, adjustments/reversals, reminders and no-charge exceptions. | SSG Finance, verification and period history. |
| O-14 | Approve removal of mandatory semester-varying School Information from Student registration, including current WF-01.01 field validation/API compatibility, existing applicant data, and first-login transition to Semester Academic Information Setup. | WF-01.01 registration, Student Semester Onboarding and migration-free compatibility planning. |
| O-15 | Approve WF-08 exact category-point-allocation contract: flexible Instructor-created categories, configurable positive point budgets, per-rater self-exclusion, exact sums, zero-versus-blank validation, permitted numeric precision and submission/correction lifecycle. | Group Rating sheet, Student form, validation and rating persistence. |
| O-16 | Decide how recipient allocations from multiple raters are aggregated; group-size normalization, optional category weighting, results privacy/publication, and whether transferred/withdrawn members remain eligible in a frozen evaluation roster. | WF-08 grading, fairness, audit and disclosure; **not decided by v0.4**. |
| O-17 | Approve WF-08 implementation limits and process details: group capacity floor/hard limit, leader/successor disputes, missing-groupmate or one-person groups, deadline extensions, roster snapshot and exceptional post-rating amendments. | Group formation, transfers and rating eligibility. |

## 11. Change control and next action

**Required next action:** Owner reviews this actor/use-case catalogue (including O-11–O-17), reconciles the new academic-period/onboarding/fee proposals with the latest Workflow Catalogue, SRS, protected ERD, API/data model and actual implementation, and either approves or amends the proposed behaviors. Only then create precise workflow-level contracts (inputs, permission codes, endpoints, field validation, data entities, tests) in the official workflow specs. No code, ERD, migration, access grant or policy setting has been changed by creating this document.

**Revision log:**

- **v0.1 — 16 November 2026:** Initial all-actor use-case documentation and traceability, based on supplied Catalogue v0.3.2 and SRS drafts; pending owner review.
- **v0.2 — 17 November 2026:** Added School Admin academic-period activation, mandatory current-semester Student onboarding/verified subjects, normal Student Dashboard gate, new organization-fee assessment linked to verified eligibility (with earlier verified-sync support), semester-clearance integration, exception scenarios, candidate acceptance tests SAP-01–09 and open decisions O-11–O-13. Proposal only; no approved workflow IDs, source changes or grants.
- **v0.3 — 17 November 2026:** Standardized **Student Semester Onboarding** and **Semester Academic Information Setup** names; separated account registration identity fields from semester-specific course/program, year level, section and subjects; clarified first approved login, academic verification, multi-role access, upstream fee assessment, form controls, SAP-10–11, and open decision O-14. Proposal only; original v0.2 retained and no code, ERD or workflow catalogue changed.
- **v0.4 — 17 November 2026 (historical numbering corrected in v0.4.1):** Expanded the Group Rating umbrella and proposed UC-D14–D16 for Hybrid Group Management, Student-requested Instructor-approved transfers and direct Instructor-designated leadership successors; documented configurable category point budgets with exact distribution, self-excluding Student table, calculated totals, zero versus blank, illustrative 10/10/20 example, proposed acceptance labels GRT-01–11 and open decisions O-15–O-17. Draft only; no new approved WF-08 IDs, code/ERD/permissions or workflow approvals.

- **v0.4.1 — 17 November 2026:** Administrative category reconciliation using the owner-supplied 13-category map: Group Rating WF-08 (Group B); Announcements WF-09; Account Concerns WF-10; System Administration WF-11; Audit/Security WF-12; Reporting & Document Generation WF-13 (Group C). Remapped all affected use-case, traceability, status, scope and open-decision references; preserved proposed Group Rating behaviors and left WF-08 subflow IDs undefined. No ERD, code, permission or workflow approval changes.

> **Implementation status (18 Nov 2026, WF-03.01 staged, local development only):** ACT-TS-11 is implemented for School Admin assignment/revocation only (ordinary Treasurer/SSG Advisor assignment is not implemented; the Permission Catalogue v2.1 overlay that binds ordinary-role management to the Technical Super Admin was validated on 19 Nov 2026 (D-89) but is not provisioned, and eligibility decisions D-100 remain open); under the Permission Catalogue v2.2 overlay (D-103, 19 Nov 2026) School Admin holds no access_control default, supporting ACT-SA-06 (validated specification, not provisioned); ACT-TS-08 and UC-09 are implemented as the Django-Superuser-exclusive protected command, verified only in the disposable test database; ACT-SA-06 (denial) is enforced and tested. No real administrator was provisioned. Owner direction (19 November 2026, D-104): Permission Catalogue v2.2 is the current target specification; v2.1 is maintained only as its verified dependency, not a separate operational target. The v2.1 validator was corrected under D-101 F-1 (commit 9e259e7; effective catalogue digests unchanged). Operational adoption still requires the independent D-101 sign-offs (v2.1, then v2.2), D-102 and separate consumer-switch and provisioning authorization; nothing is provisioned.

> **Governance note (18 Nov 2026):** This revision leaves earlier historical design status and test evidence unchanged. ACT-SA-06 is retained as a negative/legacy traceability identifier; ACT-TS-11 identifies the new positive ordinary-role operation. The framework-superuser configuration contract and protected bootstrap remain pending.
