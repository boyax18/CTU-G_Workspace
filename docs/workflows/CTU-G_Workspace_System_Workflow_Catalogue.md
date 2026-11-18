SYSTEM DOCUMENTATION  /  WORKFLOW CLASSIFICATION

# CTU-G Workspace
System Workflow Catalogue

Draft version 0.3.1  |  15 November 2026  |  For stakeholder review

## 1. Purpose and scope

This catalogue organizes the proposed CTU-G Workspace processes into 13 functional workflow categories. It is intended to support the Software Requirements Specification (SRS), use-case descriptions, acceptance criteria, and test-case planning.

These entries are proposed workflow definitions, not a statement that each function is implemented or approved. Detailed steps, business rules, permission codes, exception handling, and integration contracts must be reconciled with the approved SRS and actual system design.

## 2. Workflow classification

| ID | Category | Group | Subflows |
| --- | --- | --- | --- |
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

## 3. Workflow register

Index only. Actor and status are documented here; detailed specifications are in Section 4. The original workflow IDs and titles are retained except the user-supplied cleaned WF-01.01 title.

### Group A - Core System Workflows

#### WF-01  Registration & Authentication

| Workflow ID | Proposed workflow | Actor | Status |
| --- | --- | --- | --- |
| WF-01.01 | Register Student Account | Student Applicant (public) | Implemented and locally verified; Human Approval recorded |
| WF-01.02 | Register Instructor Account | Instructor Applicant (public) | Instructor OTP implemented and development-verified; Human Approval recorded |
| WF-01.03 | Login and session establishment | Approved Workspace account holder (public endpoint) | Owner-approved; P-01 to P-05 implemented and tested; Human Approval recorded |
| WF-01.04 | Logout and session termination | Any account holder with a valid Workspace session | Owner-approved; P-01 to P-05 implemented and tested; Human Approval recorded |
| WF-01.05 | Forgot-password request and reset | Approved account holder who cannot sign in (public, gated) | CR-01 (email + OTP) approved, implemented and tested; replaces the link flow; gate off; Human Approval recorded |
| WF-01.06 | Session expiry and CSRF handling | System-enforced for all browser visitors | Owner-approved; P-01 to P-07 implemented and tested; committed (9a56fd9); Human Approval recorded |

#### WF-02  Account Management

| Workflow ID | Proposed workflow | Actor | Status |
| --- | --- | --- | --- |
| WF-02.01 | View pending applications | School Admin with accounts.registration_requests.read (Technical Super Admin through effective permissions) | Owner-approved; P-01 to P-08 implemented and tested; committed (bbbc8db); list switch off by default; Human Approval recorded |
| WF-02.02 | Verify and review applicant information | School Admin with accounts.registration_requests.read (Technical Super Admin through effective permissions) | Owner-approved; P-01 to P-08 implemented and tested; committed (5e7a2c6); read switch off by default; Human Approval recorded |
| WF-02.03 | Approve applicant account | School Admin with accounts.registration_requests.approve (Technical Super Admin through effective permissions) | Owner-approved (P-01 to P-09, D-44 to D-53); implemented, tested and committed locally; reachable only in local review mode and the sandbox; Human Approval recorded by the owner (Ronald C. Arias, November 18, 2026) |
| WF-02.04 | Reject applicant, notify by email, and delete rejected registration data | School Admin with accounts.registration_requests.reject (Technical Super Admin through effective permissions) | Owner-approved (stages 1 and 2, D-54 to D-62); implemented, tested and committed locally; local review mode and sandbox only (in-memory mail); production blocked; Human Approval recorded by the owner for local development (Ronald C. Arias, November 18, 2026) |
| WF-02.05 | Activate or deactivate an existing account | School Admin with accounts.school_accounts.suspend / .activate and .read (Technical Super Admin through effective permissions) | Completed for local development only: stages 1–3C owner-authorized 18 Nov 2026; implemented, tested and committed locally (f476294; documentation ce784e8 and 53f0616; test 85212e4; not pushed); governed permissions provisioned and verified in ctug_workspace; production blocked; Human Approval recorded by the owner (Ronald C. Arias, November 18, 2026) for local development only |
| WF-02.06 | View account status and permitted history | School Admin with accounts.school_accounts.read (Technical Super Admin through an actual Admin assignment; D-72) | D-72 to D-78 owner-approved 18 Nov 2026; implemented and tested in the disposable test database and over real data read-only; local review and sandbox only; production blocked; Human Approval pending |

#### WF-03  Access Control Management

| Workflow ID | Proposed workflow | Actor | Status |
| --- | --- | --- | --- |
| WF-03.01 | Assign or revoke account roles | Not yet inspected | Draft |
| WF-03.02 | Manage role-based permission assignments | Not yet inspected | Draft |
| WF-03.03 | Grant account-specific permission | Not yet inspected | Draft |
| WF-03.04 | Deny or revoke account-specific permission | Not yet inspected | Draft |
| WF-03.05 | Evaluate effective permissions and service state | Not yet inspected | Draft |
| WF-03.06 | Record and review access-control changes | Not yet inspected | Draft |

#### WF-04  Profile Management

| Workflow ID | Proposed workflow | Actor | Status |
| --- | --- | --- | --- |
| WF-04.01 | View own profile | Not yet inspected | Draft |
| WF-04.02 | Request or update profile information | Not yet inspected | Draft |
| WF-04.03 | Change account password | Not yet inspected | Draft |
| WF-04.04 | Update email address | Not yet inspected | Draft |
| WF-04.05 | Upload or replace profile picture | Not yet inspected | Draft |

### Group B - Campus Service Workflows

#### WF-05  Academic Information

| Workflow ID | Proposed workflow | Actor | Status |
| --- | --- | --- | --- |
| WF-05.01 | View authorized academic information | Not yet inspected | Draft |
| WF-05.02 | View assigned subjects (instructor) | Not yet inspected | Draft |
| WF-05.03 | View enrolled students where authorized | Not yet inspected | Draft |
| WF-05.04 | Obtain or verify academic status from CTU main system | Not yet inspected | Draft |

#### WF-06  Clearance Management

| Workflow ID | Proposed workflow | Actor | Status |
| --- | --- | --- | --- |
| WF-06.01 | Request clearance | Not yet inspected | Draft |
| WF-06.02 | Verify clearance eligibility and requirements | Not yet inspected | Draft |
| WF-06.03 | Review and decide assigned clearance items | Not yet inspected | Draft |
| WF-06.04 | Track clearance progress and decisions | Not yet inspected | Draft |
| WF-06.05 | Generate an authorized clearance PDF | Not yet inspected | Draft |

#### WF-07  SSG Financial Management

| Workflow ID | Proposed workflow | Actor | Status |
| --- | --- | --- | --- |
| WF-07.01 | Verify academic-period fee eligibility | Not yet inspected | Draft |
| WF-07.02 | Assess organizational fee obligation | Not yet inspected | Draft |
| WF-07.03 | Record and validate payments | Not yet inspected | Draft |
| WF-07.04 | Generate and view authorized receipts | Not yet inspected | Draft |
| WF-07.05 | Record and categorize expenses | Not yet inspected | Draft |
| WF-07.06 | View balances, payment status, and history | Not yet inspected | Draft |
| WF-07.07 | Prepare authorized financial reports | Not yet inspected | Draft |
| WF-07.08 | Process returning, transferee, and newcomer scenarios | Not yet inspected | Draft |

#### WF-08  Group Rating

| Workflow ID | Proposed workflow | Actor | Status |
| --- | --- | --- | --- |
| Not assigned | Group Rating subflows — owner review required | Student / Instructor (SRS scope only) | Draft — not yet inspected |

No WF-08.xx IDs or detailed workflow behaviors assigned. Group Rating is included as a draft campus-service category only; the project owner will approve its workflow breakdown before specifications are written.

#### WF-09  Announcements & Notifications

| Workflow ID | Proposed workflow | Actor | Status |
| --- | --- | --- | --- |
| WF-09.01 | Create and publish announcements | Not yet inspected | Draft |
| WF-09.02 | View announcements | Not yet inspected | Draft |
| WF-09.03 | Generate event-based in-app notifications | Not yet inspected | Draft |
| WF-09.04 | Send eligible email notifications | Not yet inspected | Draft |
| WF-09.05 | View notification history and delivery status | Not yet inspected | Draft |

#### WF-10  Account Concerns & Support

| Workflow ID | Proposed workflow | Actor | Status |
| --- | --- | --- | --- |
| WF-10.01 | Submit account concern | Not yet inspected | Draft |
| WF-10.02 | Assign or review concern | Not yet inspected | Draft |
| WF-10.03 | Respond to concern | Not yet inspected | Draft |
| WF-10.04 | Track concern status and resolution | Not yet inspected | Draft |

### Group C - System Operations & Maintenance

#### WF-11  System Administration & Configuration

| Workflow ID | Proposed workflow | Actor | Status |
| --- | --- | --- | --- |
| WF-11.01 | Manage authorized academic-period settings | Not yet inspected | Draft |
| WF-11.02 | Manage system operational settings | Not yet inspected | Draft |
| WF-11.03 | Configure services within authorized boundaries | Not yet inspected | Draft |
| WF-11.04 | Review operational configuration changes | Not yet inspected | Draft |

#### WF-12  Audit, Security & Monitoring

| Workflow ID | Proposed workflow | Actor | Status |
| --- | --- | --- | --- |
| WF-12.01 | Record security-relevant events | Not yet inspected | Draft |
| WF-12.02 | Review authorized audit records | Not yet inspected | Draft |
| WF-12.03 | Detect and respond to unauthorized attempts | Not yet inspected | Draft |
| WF-12.04 | Monitor system health and error conditions | Not yet inspected | Draft |
| WF-12.05 | Apply data retention, backup, and recovery controls | Not yet inspected | Draft |

#### WF-13  Reporting & Document Generation

| Workflow ID | Proposed workflow | Actor | Status |
| --- | --- | --- | --- |
| WF-13.01 | Generate authorized operational reports | Not yet inspected | Draft |
| WF-13.02 | Export permitted records | Not yet inspected | Draft |
| WF-13.03 | Generate official system documents | Not yet inspected | Draft |
| WF-13.04 | Check report accuracy and access scope | Not yet inspected | Draft |

## 4. Detailed workflow specifications

Each flow has a consistent header, main flow, alternative flow, errors, links and approval checklist. Uninspected flows are placeholders only: no behavior has been invented.

### 4.0 Reusable workflow template (moved from former Section 6)

| Template element | What to record |
| --- | --- |
| Workflow ID and title | Stable ID and title (unchanged until approved) |
| Header table | Actor and required permission; Trigger; Preconditions; Result; Status |
| Main flow | Numbered actions; Not yet inspected until reconciled |
| Alternative flows | Numbered alternatives; Not yet inspected until reconciled |
| Errors | Step \| Problem \| What happens |
| Links | Depends on; Feeds |
| Checklist footer | Guidelines; AI Agent Checklist; Blocked by; Evidence level; Human Approval; Next flow |
| Evidence and approval | Record verification level; do not tick Approved without the project owner |

Original reusable-template intent retained: purpose/scope, actors/permissions, trigger/preconditions, postconditions, requirement/data traceability, acceptance/testing, approval and version must be confirmed during each flow’s inspection.

### Group A - Core System Workflows

### WF-01  Registration & Authentication

#### WF-01.01 — Register Student Account

| Field | Definition |
| --- | --- |
| Actor | Student Applicant (public registration, no permission needed) |
| Trigger | Applicant submits the Student registration form |
| Preconditions | Registration is available and the OTP email service is working |
| Result | A verified Pending/inactive account is created and waits for School Admin review (WF-02) |
| Status | Implemented in the development system and verified by automated checks; 16 November 2026 UI wording update complete. OTP precedes account/profile creation. Defaults are configurable; policy decisions and Human Approval remain unapproved. |

**Implementation basis:** The user's subsequent instruction authorized making WF-01.01 follow its main flow and then completing the AI checklist. Student registration now stages encrypted data, sends/verifies an OTP and only then creates the Pending/inactive account/profile with durable email proof. WF-01.02 later reused this mechanism for Instructor (see WF-01.02). The owner-approved 16 November 2026 audit corrections (mail sent only after the staging write commits, per-identity limits for both roles, status rate limits, resumed-attempt notice and code-lifetime/spam-folder guidance) are recorded in the [WF-01 audit corrections record](group_a/WF-01_Audit_Corrections_2026-11-16.md); Student conflict wording and main flow are unchanged. See the [current implementation and verification record](group_a/WF-01.01_Student_Registration_Implementation.md); the [earlier inspection record](group_a/WF-01.01_Student_Registration_Review.md) preserves pre-implementation findings. No policy decision or Human Approval was approved by the agent. Per the 16 November instruction, the Student form button reads “Proceed Email Verification” and has no separate resume verification control.

#### Main flow

1. Applicant opens the public registration page and chooses Student.

2. Applicant completes the form: School ID, email, first name, last name, password, confirm password, and optional profile info.

3. Applicant submits the form to request email verification.

4. System validates the request and fields, and confirms that Student is an available requested base role. Academic eligibility is reviewed by the School Admin under WF-02; email verification alone does not establish enrollment or eligibility.

5. System checks that the School ID and email are not already used. (email rule: D-06)

6. System securely stages the information. The password is hashed first. (D-04)

7. System creates an OTP and emails it to the applicant.

8. System shows the OTP entry screen.

9. Applicant enters the OTP.

10. System checks the attempt limit (D-03), then validates the OTP (D-01).

11. System marks the temporary registration as email-verified.

12. System runs one all-or-nothing transaction. It rechecks School ID and email, creates the Pending/inactive account, creates the linked profile, saves the email-verification proof, and commits.

13. System shows a confirmation, and the Pending account becomes visible to the School Admin (WF-02.01).

Rule: Before step 12, no account or profile exists, and no role is assigned. A role is assigned only on School Admin approval (WF-02.03).

#### Alternative A – Resend OTP (D-02)

1. Applicant requests a new code.

2. System checks the resend interval and limit.

3. System cancels the old OTP, creates a new one, and emails it.

4. System shows a generic "code sent" message.

#### Alternative B – Applicant already has a staged registration (D-04b)

1. Applicant submits again with the same School ID or email.

2. System does not overwrite the first attempt and shows the generic message.

3. The original browser's scoped HttpOnly cookie proves possession and continues the earlier verification attempt without overwriting its details. The applicant can cancel from the OTP screen. Another browser knowing only School ID/email cannot resume or cancel. There is no separate resume verification button/link. [D-04b: implemented mechanism; policy sign-off OPEN.]

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Step 4 | Invalid form or request | Reject and show what to fix |
| Steps 5, 12 | School ID or email conflict | Stop; show the same generic message: "We could not complete this registration. Please check your information or contact support." Student initial/final conflict checks now return HTTP 409 with this message (D-07). |
| Step 6 | Staging fails | Stop; show "registration unavailable" |
| Step 7 | OTP email fails | Return a delivery failure, invalidate the uncertain code and retain encrypted staging for bounded resend within the original deadline. No account/profile is created and no delivery success is claimed. [D-08: implemented recovery default; policy sign-off OPEN.] |
| Step 10 | OTP expired, wrong, or too many attempts | Show the matching message (D-01, D-03) |
| Steps 6–11 | Applicant abandons registration | Staged data purged (D-05) |
| Step 12 | Transaction fails | Roll back; show "registration not completed" |

#### Links

Depends on: WF-01.06 (session and CSRF) and the OTP email service. WF-09.04 is related, not a proven dependency.

Public support cross-reference: Official support contact – needs owner input. See Appendix A/B and WF-01.02 D-13 for the configured support/fallback decision. This adds the owner's requested open-item reference; WF-01.01's approved error wording and behavior are unchanged.

Feeds: WF-02.01, WF-02.02, WF-02.03, and WF-02.04 if the applicant is rejected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☒ Inspected   ☒ Reconciled   ☐ Tested   ☒ Cleaned   ☒ Verified

Checklist scope: Completed for this local implementation: source/DB inspection, reconciliation to the main flow, cleanup of staged secrets/data and automated verification. Verified means 122 focused backend checks (23 OTP tests), 75 related backend regressions, 34 frontend checks, successful frontend build, schema installation and safe HTTP/SMTP smoke checks. It does not assert actual recipient inbox delivery, full interactive browser testing, production readiness or human approval.

Blocked by: No remaining implementation blocker for the main flow in the current local configuration. Human sign-off and policy review D-01–D-09 remain OPEN; official support details, actual inbox/full browser acceptance and a supervised production cleanup/executor deployment require separate completion. Protected executor mode deliberately refuses Student OTP until its writer/credential/trigger contract is reviewed. Do not start WF-01.02.

Evidence level: Code-verified and automated-test verified for the Student OTP sequence; DB-verified for installed development staging/proof schema and accounts migration ledger through 0005. Existing account/profile values preserved. SMTP connection/authentication succeeded without sending a real test message. React component initial server rendering/build and live route/proxy responses verified; actual inbox/full interactive browser acceptance unverified. This is not production verification.

Human Approval: ☒ Approved by: Ronald Arias  Date: 11/16/2026

Next flow: WF-01.02. Do not start until Approved is ticked.

#### WF-01.02 — Register Instructor Account

| Field | Definition |
| --- | --- |
| Actor | Instructor Applicant (public registration; no permission needed) |
| Trigger | Applicant submits the Instructor registration form |
| Preconditions | Registration and OTP email service are available; requested Instructor role is active; existing CSRF, rate and permitted-writer checks pass |
| Result | After OTP, one email-verified Pending/inactive Instructor account and linked profile await School Admin review; no role or authenticated session is created |
| Status | Implemented and verified in development against the owner-stated OTP target on 16 November 2026, with the owner's later instruction to adopt Student error feedback/response ([consistency report](group_a/WF-01.02_Feedback_Consistency.md)) and the owner-approved audit corrections ([WF-01 audit corrections record](group_a/WF-01_Audit_Corrections_2026-11-16.md)). Human Approval recorded by the owner on 17 November 2026. |

**Owner-stated basis:** Ronald Arias authorized reuse of WF-01.01 staging/OTP/proof for Instructor in development and confirmed Staff ID (1–7 digits), School Admin review only, the conflict sentence below, configured public support with neutral fallback, and the existing password-reset feature gate. These requirements supersede the historical direct-to-Pending/neutral-202 Instructor baseline. D-01–D-09 remain OPEN; owner statements are recorded without agent policy approval. See the [current implementation/acceptance report](group_a/WF-01.02_Instructor_OTP_Implementation.md), [reconciliation table and owner answers](group_a/WF-01.02_Instructor_OTP_Reconciliation.md), and [historical direct-registration record](group_a/WF-01.02_Instructor_Registration_Implementation.md).

#### Main flow

1. Applicant opens /register and selects Instructor.
2. Applicant supplies Staff ID, email, first name, last name, password and confirmation; middle name and suffix are optional.
3. Applicant activates Proceed Email Verification.
4. System validates the allowlisted input and active Instructor requested role, with existing CSRF/Origin, JSON and request-limit protections.
5. System checks the Staff ID and normalized email against existing accounts and active staged reservations.
6. System creates the protected temporary registration with a password hash and immutable Instructor role inside the encrypted payload.
7. System generates a six-digit OTP and sends it through the existing email mechanism.
8. System displays the shared OTP screen for the original browser: the configured code lifetime and a spam/junk-folder hint (OD-3, owner-approved 16 November 2026). The recipient address is not displayed.
9. Applicant enters the OTP.
10. System checks cumulative attempts and code/stage expiry, then validates the OTP.
11. System marks the temporary registration email-verified inside the completion transaction.
12. System atomically rechecks uniqueness and the active Instructor role, creates the Pending/inactive account and linked profile, saves durable email proof, and consumes the stage.
13. System displays confirmation that School Admin review is next.

Rules:
- Before step 12, no account/profile exists. No AccountRole, privilege, approval or login is created by registration.
- Staff ID is the Instructor label for existing accounts.school_id; it accepts 1–7 ASCII digits, preserving leading zeroes. No employee entity/column or migration was introduced (D-11, owner-stated).
- Instructor has no School Information section and no course/year-level/section fields. Submitted Student-only fields are rejected with a clear safe error and are not staged/stored.
- OTP proves email access, not employment. Eligibility is checked by School Admin review only, as owner-stated (D-12). Existing review authorization, role assignment and activation gates are unchanged.
- Hashing, encryption, cookie ownership, code generation, attempt/resend limits, fixed expiry and atomic proof use the same mechanism as WF-01.01 (D-01–D-09). Legacy Student stages retain Student interpretation; a role is never changed by resubmitting or by a query parameter.
- Step 5 reservation checks are backed by unique keyed Staff ID/email digests in the existing staging table; a competing insert is refused before an OTP is generated/sent. Permanent identity uniqueness is also backed by the existing account indexes.
- Same-browser resume continues the original immutable attempt, with its original role/recipient, and sends no new OTP. It is not a conflict and does not show the conflict message.
- No automatic retry of registration or OTP mutations. Passwords clear on conflict/security/delivery/uncertain outcomes; OTP input clears after failed verification. Safe form values remain available for correction.

#### Alternative A — Resend OTP (D-02, D-08; same mechanism as WF-01.01)

1. Applicant requests Resend code or Send a new code after code expiry.
2. System enforces the countdown, resend limit, cumulative attempts and original stage deadline.
3. System invalidates the old code before issuing/sending a different code.
4. System reports success only when the mail backend accepts the message; uncertain failure invalidates the new code and retains encrypted staging for bounded resend.

#### Alternative B — Existing attempt / original-browser resume (D-04b)

1. Original scoped HttpOnly cookie proves possession of the earlier staged attempt.
2. System returns existing_verification without overwriting its details or sending a new code.
3. Applicant continues the original attempt or uses Cancel registration to invalidate it before starting over. When a resubmission resumes the saved attempt, the OTP screen states that the newly entered details were not used and that a wrong email address requires Cancel registration (R-05).
4. Another browser knowing only Staff ID/email receives generic HTTP 409 and cannot resume or cancel; missing/expired ownership returns HTTP 410.

#### Alternative C — Uncertain result

1. System clears sensitive inputs and states that completion could not be confirmed.
2. Applicant explicitly checks the cookie-bound registration status using GET.
3. System never interprets a missing session alone as proof that the earlier write failed or succeeded.
4. An explicit restart performs no automatic registration write.

#### Errors

| Step | Problem | What the user sees / recovery |
| --- | --- | --- |
| 4 | Invalid fields/password/request | HTTP 400 with safe correction errors; Staff ID is labelled correctly. Student-only fields: "Student-only school information is not accepted for Instructor registration." |
| 4, 9–10 | CSRF/Origin, JSON/method/media or request limits | Existing 403/400/405/415/406/429 semantics and safe request reference; explicit security refresh or wait/countdown. No automatic POST retry. |
| 5, 12 | Existing account or another staged reservation | HTTP 409 and the shared generic message below (identical to WF-01.01); keep safe form values, clear passwords and send no verification code for this blocked request. |
| 6 | Staging/writer unavailable | Safe HTTP 503 registration_unavailable; no permanent record and no writer-boundary bypass. |
| 7 | OTP email delivery fails | Honest HTTP 503 delivery_failed; original cookie retains encrypted staging, uncertain code is invalidated, and bounded resend stays within the original deadline (D-08). |
| 10 | Wrong OTP | HTTP 400 otp_invalid; code clears, remaining attempts are displayed and correction is accessible. |
| 10 | OTP expired | HTTP 400 otp_expired; Send a new code remains on the same screen, subject to resend countdown/limit. |
| 10 | Attempts exhausted | HTTP 400 attempts_exhausted; verification/resend are refused. Explain remaining stage-expiry time and that explicit cancellation permits a fresh start. Resends do not reset attempts. |
| 6–11 | Stage missing/expired/abandoned | HTTP 410 for missing/expired ownership; offer a new registration. Existing cleanup deletes only expired stages under D-05. |
| 12 | Profile/database/unrelated integrity failure | Roll back account/profile/proof together; genuine safe HTTP 503. An unrelated profile duplicate-key failure is not mislabeled as an identity conflict for Instructor. |
| 3–12 | Network/gateway/invalid success body/unexpected server result | Accessible safe uncertainty/error message; clear secrets and explicitly read status before another write. HTTP 200 error envelopes are not accepted as success. |

Conflict message (shared with WF-01.01; identical before and after OTP):
"We could not complete this registration. Please check your information or contact support."

Per the owner's 16 November 2026 instruction ("make it consistent, adopt the student error feedback/response"), confirmed as OD-1(a) during the 16 November audit, Instructor uses the Student conflict feedback: the same accessible notice and request reference, "Check both your Staff ID and email" guidance, wait-for-review guidance and a Sign in link to /. The earlier Instructor-only sentence and the Log in / Reset your password / Continue your registration / Contact support action panel are superseded and not implemented. Password recovery is neither enabled nor bypassed by registration.

Accepted abuse controls/risks: existing registration IP limits 5/minute and 30/day; Instructor OTP/status IP limits 30/minute and 200/day. Admission and owned OTP/status operations for both roles also enforce those respective budgets per keyed ID and normalized email, shared across roles, using existing DRF/cache infrastructure; no raw identities are cache keys (Student coverage added by owner-approved audit item R-03). The status endpoint is IP-throttled for both roles before any database work (R-04). Verification mail is sent only after the staging write commits; a failed send invalidates only that same code (R-02). Unique stage constraints cap concurrent attempts at one per ID and one per email across roles. Inherited fixed 30-minute staging expiry (D-05), 10-minute OTP, five cumulative wrong codes, 60-second resend interval and three resends remain configurable inherited defaults, not agent-approved policy. Resends do not extend expiry. A local 60-second cleanup worker is running; immediate expiry refusal does not depend on it. Cache throttles are best effort within the configured cache backend; distributed/shared-cache enforcement and supervised production cleanup remain deployment work. Temporary first-claim blocking until cancellation/expiry is an accepted risk; no cross-browser bypass is provided (D-14).

#### Links

Depends on: WF-01.06/session/CSRF; existing /register and OTP routes; active Instructor requested role; shared staging/proof/mail and permitted writer.
Feeds: Existing School Admin listing/detail/review in WF-02.01–WF-02.03, and WF-02.04 if rejected. No review route/permission/activation gate was enabled by this task.
Traceability: Owner-stated Instructor OTP target; existing SRS UC-01 / FR-REG-01–03 validation/security/atomicity (direct-creation sequence is superseded for Instructor); accounts, users, roles and existing student_registration_staging. Existing exact accounts.registration_requests.read/approve/reject permissions remain separate from public registration.
Official support contact – needs owner input. Registration feedback uses the shared generic "contact support" wording; the earlier configured support action was retired by the consistency decision. WORKSPACE_REGISTRATION_SUPPORT_CONTACT is currently unused by the application and is kept only pending the owner's official contact decision. Not a local implementation blocker.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☒ Inspected   ☒ Reconciled   ☐ Tested   ☒ Cleaned   ☒ Verified

Checklist scope: Owner decisions reconciled; spec/implementation follow the Instructor OTP target; legacy direct creation removed; Instructor fields/actions/errors and shared secure completion verified. All eleven requested verification checklist items are recorded with evidence in the implementation report. Human Approval is not included in agent verification.

Blocked by: No remaining development implementation blocker. Official support contact – needs owner input; the accepted neutral fallback is active. Human Approval and policy sign-off remain separate; D-01–D-09 stay OPEN. Actual recipient inbox delivery, full human/browser acceptance and protected-production deployment are unverified. Do not start WF-01.03.

Evidence level: Code-verified, DB-verified (read-only SHOW CREATE TABLE accounts/staging, zero duplicate groups and ledger through 0005), automated-test verified. Final 164 focused backend checks (including 30 unchanged Student OTP and 20 Instructor OTP cases), 93 related backend regressions, 51 focused frontend checks, 29 browser checks, one real browser/CSRF/staging/OTP/MySQL/permission-protected Pending-read scenario, build and scoped lint passed. Full frontend: 139/140 passed, with one known unrelated dashboard/mock-isolation failure. Disposable test databases were destroyed. No new migration, ERD change, production operation, real development applicant or real OTP email send was performed. Development backend/frontend and cleanup worker are running; cookie-less Instructor status returned the expected 410 with matching request references through the real proxy.

Human Approval: ☒ Approved by: Ronald C. Arias  Date: 11/17/2026

Next flow: WF-01.03. Do not start until Approved is ticked.

#### WF-01.03 — Login and session establishment

| Field | Definition |
| --- | --- |
| Actor / required permission | Approved Workspace account holder: Student, Instructor, or any account with at least one active assigned role. The login endpoint is public, so no permission code is needed to attempt it. Django framework staff and superuser accounts are refused here and use /admin/ only (ADR-001). |
| Trigger | The user submits School ID (Staff ID for Instructors, the same field; D-11) and password on the home-page sign-in card (/#login), which sends POST /api/v1/auth/login/. |
| Preconditions | The account exists with request_status Approved and is_active true, and holds at least one AccountRole whose role is active. It is not is_staff or is_superuser. The browser has a CSRF token from GET /api/v1/auth/csrf/ and the request comes from a trusted origin. The per-IP login throttle has not been exceeded. |
| Result | Django creates a server-side session (HttpOnly session cookie) for the account. The response returns school_id, the sorted active role names and the current effective permission codes as UI hints only. The browser opens /dashboard, which reads GET /api/v1/auth/session/ again. Login creates no role, permission or approval, and stores no grants in the session. |
| Status | Inspected and reconciled 16 November 2026, then approved by the owner the same day ("I approve the wf-01.03"). P-01 to P-05 are implemented and verified by automated backend, frontend and browser tests. P-06 (authentication events, D-17) stays blocked pending an approved contract. D-18 is deferred to WF-01.06 and D-19 is recorded without code change. Human Approval recorded by the owner on 17 November 2026. |

**Inspection basis:** On 16 November 2026 the owner instructed: continue WF-01 with WF-01.03, read-only inspection and reconciliation first, then stop for approval. Inspected: backend/apps/accounts/session_auth.py (LoginView, SessionView, LogoutView and the shared WorkspaceSessionAPI), accounts/urls.py, accounts/views.py (CSRFView and the JSON parser), the Account model, access_control.services.get_effective_permissions, the executor client, config/settings.py, frontend/src/features/auth/session.ts, api/client.ts, home/components/HomeLoginForm.tsx, HeroSection.tsx, layouts/DashboardLayout.tsx, and the existing session tests. Also inspected: SRS v0.3 (UC-04, FR-AUTH-01 to 07, FR-AUD-02, NFR-SEC-02, OD-13; read from git HEAD because the working-tree copy is deleted and was not restored), docs/api/AUTH_ENDPOINT_INVENTORY.md and the ERD (read-only). WF-01.01 and WF-01.02 share the CSRF bootstrap, the JSON parser and the error envelope with this flow; their pending approvals and policy decisions are unchanged.

**Implementation basis:** Owner approval on 16 November 2026 covered the reconciled WF-01.03 specification, including the proposed label "School ID or Staff ID" and the approval hint. Changed: backend/apps/accounts/session_auth.py (per-identity login budget before authentication; X-Request-ID on every WorkspaceSessionAPI response, which includes the registration review API); frontend/src/features/auth/loginFeedback.ts (new failure-to-feedback mapping); frontend/src/features/home/components/HomeLoginForm.tsx (feedback, countdown, security refresh, session confirmation, signed-in view, label and maxLength). Tests added: backend/apps/accounts/test_session_auth.py (4 cases), frontend/tests/login-feedback.test.mjs (6) and frontend/tests/browser/login-errors.test.mjs (7). No ERD, migration, permission, role, feature-gate or settings change.

**Reconciliation findings and proposals (P-01 to P-05 implemented 16 Nov 2026; P-06 not implemented):**
- P-01 Login feedback (D-15) — IMPLEMENTED. Before this change, the frontend replaced every failure with "Sign-in could not be completed. Please try again." (role=status, amber notice). That covered 401 invalid credentials, 403 CSRF, 429 throttle and 503/network errors alike. The password was not cleared, no wait time was shown, there was no recovery action and no request reference. Approved and implemented: reuse the WF-01.01 feedback patterns (ApiErrorNotice: role=alert, focus, request reference). Show the server's own messages: 401 "Unable to sign in with these credentials." plus a non-revealing hint shown on every 401, "If you registered recently, your account may still be awaiting School Admin approval."; 429 with a Retry-After countdown; 403 with a "Refresh security check" action; 503 or network failure as "Sign-in could not be confirmed", followed by a GET session re-read before claiming failure. Clear the password after any failed attempt.
- P-02 Identifier label (D-15) — IMPLEMENTED. The login field was labelled "School ID" for everyone, but Instructors register with a Staff ID stored in the same school_id field (D-11). Implemented: label, placeholder and empty-field error now say "School ID or Staff ID"; maxLength 50/256 matches the backend serializer. The other Title Case copy on the card is unchanged.
- P-03 Existing session — IMPLEMENTED. The home page did not check the current session, so a signed-in user saw the sign-in form again. Signing in with other credentials replaces the session (Django flushes the earlier one). Implemented: the card reads GET /api/v1/auth/session/ on load and, when authenticated, shows "You’re signed in as {school_id}." with Continue to Dashboard and Sign Out (existing CSRF-protected logout). A failed check keeps the form.
- P-04 Request reference — IMPLEMENTED. WorkspaceSessionAPI responses carried no X-Request-ID (registration responses did). Implemented: reuse api_errors.request_id so authentication errors show a safe "Request reference".
- P-05 Abuse controls (D-16) — IMPLEMENTED in code; deployment items open. Throttling was per REMOTE_ADDR only (8/minute, 40/hour) in Django's default per-process LocMem cache. Behind a reverse proxy, every user would share the proxy's address, and there is no per-identity budget against distributed guessing. Implemented: a per-identity budget (8/minute and 40/hour, code defaults equal to the IP budgets) keyed by an HMAC digest of the trimmed, lower-cased school_id (the D-14 mechanism), checked before any password hashing or executor call, with no account lockout. Still open deployment work: a shared cache and trusted-proxy configuration. The values remain a policy decision.
- P-06 Authentication events (D-17). No login success or failure event is recorded. Account has no last_login field (removed by design, so Django does not update it). FR-AUTH-07 and FR-AUD-02 require an approved event contract, and the SRS forbids using access_audit_logs for login events or adding a login-event table without separate ERD approval. Proposal: owner decides the contract. Meanwhile no storage is added.
- Dependencies recorded for WF-01.06, not fixed here (D-18). config/settings.py sets no session or CSRF cookie options: Django defaults apply (14-day persistent session cookie, no idle timeout, Secure off, SameSite Lax, HttpOnly session cookie). DEBUG is hard-coded to True. Only the protected executor runtime settings enable Secure cookies and the HTTPS redirect.
- Session revocation (D-19). Implemented: every session read and protected review request rechecks account, approval and role eligibility from the database, so a revoked role, revoked approval or deactivation takes effect at the next request. Existing session rows are not deleted, and there is no limit on concurrent sessions per account (SRS OD-13).

#### Main flow

1. User opens / and reaches the sign-in card (HomeLoginForm, anchor #login), either directly, through the header Sign In button, or through "Return to sign-in" on /dashboard (/#login focuses the form).
2. User enters "School ID or Staff ID" and password. Instructors enter their Staff ID in the same field (P-02). If the browser already holds a valid session, the card instead shows "You’re signed in as {school_id}." with Continue to Dashboard and Sign Out (P-03).
3. User activates Sign In.
4. Frontend checks that both fields are filled (School ID trimmed), shows inline errors otherwise, and blocks a second submit while one is in flight.
5. Frontend gets a fresh CSRF token (GET /api/v1/auth/csrf/) and sends POST JSON {school_id, password} with X-CSRFToken: same-origin cookies, 15-second timeout, no automatic retry.
6. Backend enforces CSRF and the trusted origin before parsing anything, even for anonymous requests. It then applies the per-IP throttles (8/minute, 40/hour) and accepts only a JSON object (16 KiB or less, duplicate keys refused, no extra fields), with school_id up to 50 characters (trimmed) and password up to 256 characters (not trimmed). It then applies the per-identity budget (8/minute, 40/hour per normalized school_id digest; P-05) before any password hashing.
7. Backend authenticates with Django ModelBackend, which hashes the password even for unknown IDs and refuses inactive accounts. When protected executor mode is enabled, the verified-writer executor (authenticate_actor) authenticates instead and its proof is stored in the session.
8. Backend rechecks Workspace eligibility against the database: the account is not framework staff or superuser, is active and Approved, and has at least one active assigned role.
9. Backend builds the response (school_id, active role names, effective permission codes) before creating the session, so a database failure never leaves an orphaned signed-in session.
10. Backend calls Django login(): the session key and CSRF token are rotated, the HttpOnly session cookie is set, and the response is Cache-Control: no-store with an X-Request-ID reference (P-04).
11. Frontend validates the response shape and navigates to /dashboard.
12. The dashboard reads GET /api/v1/auth/session/, which rechecks eligibility on every call, and renders the shared shell. Navigation follows exact permission codes.

Rules:
- Login never approves, activates or assigns roles. Permission codes are point-in-time UI hints, never stored in the session. Every protected API re-authorizes on the backend (FR-AUTH-05/06).
- Unknown ID, wrong password, Pending, Rejected (rejected accounts are deleted), inactive, no active role, inactive role, and framework staff or superuser all return the same HTTP 401 invalid_credentials. No session is created and no account state is revealed (FR-AUTH-02/03).
- One account has one session with the union of its roles. There are no separate per-role logins (FR-UI-04).

#### Alternative flows

Alternative A — Invalid credentials or ineligible account (implemented): 1. The backend returns HTTP 401 "Unable to sign in with these credentials." 2. No session is created. 3. The form shows that message in an alert with "If you registered recently, your account may still be awaiting School Admin approval." and the request reference, clears the password and keeps the ID (P-01).

Alternative B — Already signed in (implemented, P-03): 1. The card reads the session on load. 2. When authenticated, it shows "You’re signed in as {school_id}." with Continue to Dashboard. 3. Sign Out ends the session through the existing logout and returns to the form, focused on the ID field. A different account can then sign in.

Alternative C — Eligibility lost after login (implemented): 1. An administrator removes a role, revokes approval or deactivates the account. 2. The next session read returns authenticated: false, or ModelBackend refuses an inactive user. 3. The dashboard shows "Sign in required" with Return to sign-in, and protected review APIs deny the request.

Alternative D — Rate limited (implemented): 1. The backend returns 429 too_many_attempts with Retry-After, per IP or per identity (P-05). 2. The form shows "Too many attempts. Please try again later." and "Try again in N seconds.", and disables Sign In until the countdown ends (P-01). Nothing is retried automatically.

Alternative E — Security check failed (implemented): 1. A missing or invalid CSRF token, or an untrusted Origin, returns 403 csrf_failed before credentials are read. 2. The form offers "Refresh security check", which only fetches a new token (no POST), then asks the user to enter the password and sign in again (P-01).

Alternative G — Unknown outcome (implemented, P-01): 1. A network failure, timeout, 5xx or malformed response follows the login POST. 2. The form reads GET /api/v1/auth/session/ before claiming failure. 3. If a session exists it opens /dashboard; otherwise it shows "Sign-in did not complete. Check your connection and try again." (or the safe 503 message). If the session read also fails, it says sign-in could not be confirmed and suggests reloading.

Alternative F — Forgot password: 1. The form links to /forgot-password. 2. That behavior belongs to WF-01.05 and is gated by WORKSPACE_PASSWORD_RESET_ENABLED (off by default).

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| 4 | School ID or password empty | Inline errors "Please enter your School ID." / "Please enter your password."; no request sent |
| 5–6 | CSRF missing or invalid, or untrusted Origin | HTTP 403 csrf_failed before parsing or throttling; no session. Form: alert with "Refresh security check" (no automatic POST) |
| 6 | Throttle exceeded (8/minute or 40/hour per IP, or per normalized identity) | HTTP 429 too_many_attempts + Retry-After, before any password hashing. Form: alert + "Try again in N seconds."; Sign In disabled until it ends |
| 6 | Non-object JSON, extra or duplicate fields, oversized body, wrong method or media type | HTTP 400 invalid_request / 405 / 406 / 415; no session |
| 7–8 | Wrong credentials or ineligible account | HTTP 401 invalid_credentials (same for every cause). Form: shared message + approval hint + request reference; password cleared, ID kept |
| 7 | Executor refuses or is unavailable (protected mode only) | HTTP 401 invalid_credentials, or HTTP 503 auth_unavailable; no session |
| 9 | Database error while computing roles or permissions | HTTP 503 auth_unavailable; no session, because the payload is built before login() |
| 11 | Malformed or negative success body | Frontend treats it as failure (invalid_session); test-verified |
| 5–11 | Network failure, timeout or 5xx after the POST | Form reads the session (GET) first: opens /dashboard if a session exists, otherwise "Sign-in did not complete. Check your connection and try again." (or the safe 503 message) |
| 12 | Session read fails or returns anonymous | Dashboard shows "Session unavailable" with Try again, or "Sign in required" with Return to sign-in |

#### Links

Depends on: WF-02.03, the only path that makes an account Approved, active and role-assigned. WF-03.05, effective permissions and role state. WF-01.06, CSRF bootstrap and session cookie/expiry configuration (D-18). ADR-001, framework-administrator separation.

Feeds: WF-01.04 (logout), the shared dashboard (FR-UI-01 to 08) and every protected module. WF-12.01 (authentication events, once D-17 is approved). The form links to WF-01.05.

Traceability: SRS v0.3 UC-04. FR-AUTH-01/02/03/05/06 are met in code and tests. FR-AUTH-04 belongs to WF-01.04 and WF-01.06. FR-AUTH-07 and FR-AUD-02 are not met (no approved event contract). NFR-SEC-02 is partially met (HTTPS and Secure cookies only in the executor runtime settings). See docs/api/AUTH_ENDPOINT_INVENTORY.md.

Guidelines: Inspect → Reconcile → Approve → Implement → Test → Commit

AI Agent Checklist: ☒ Inspected   ☒ Reconciled   ☒ Approved   ☒ Implemented   ☒ Tested   ☒ Committed

Checklist scope: Approved records the owner's 16 November 2026 approval of the reconciled specification; it is not Human Approval of the finished flow. Implemented covers P-01 to P-05. Tested covers the automated evidence below. Committed: 66c1301 on branch ronald (7 files: the 4 source/test changes listed under Implementation basis, 2 new frontend test files and this catalogue); unrelated uncommitted work was left unstaged. P-06 and D-17 are not implemented; D-18 belongs to WF-01.06; D-19 is unchanged.

Blocked by: No remaining development implementation blocker for P-01 to P-05. Open: D-17 authentication-event contract (P-06; plus ERD review if storage is required); production cookie, HTTPS and DEBUG settings (D-18, WF-01.06); shared cache and trusted-proxy deployment for the throttles (D-16); session deletion and limits (D-19); policy sign-off of the D-16 values. Human Approval recorded by the owner on 17 November 2026 for WF-01.01 to WF-01.06.03 by explicit instruction and approval on 16 November 2026. Actual interactive sign-in against a real development account is unverified.

Evidence level: Code-verified and automated-test verified, 16 November 2026 (Django 6.1.2). Inspection baseline: 14/14 backend session tests and 9/9 frontend session tests. After implementation: `manage.py test apps.accounts.test_session_auth --settings=config.test_settings` 18/18 passed (14 existing + 4 new: identity budget across IPs and normalized IDs, budget checked before authentication, no raw ID in cache keys, distinct request reference on every auth response). All 23 accounts test modules: 380 tests, 377 passed; the 3 failures are in test_registration_review_notifications and fail identically with the original session_auth.py, so they belong to pre-existing uncommitted outbox work, not this flow. Frontend `npm test`: 154 tests, 153 passed; the 1 failure is the known unrelated dashboard/mock-isolation test. `npm run test:registration-ui`: 43/43 passed, including 7 new real-browser login scenarios on the actual home page with mocked APIs (wrong credentials, rate limit, CSRF refresh, unknown outcome with and without a session, existing session and sign-out, success). `npm run build` passed. `npm run lint`: the new and changed files are clean; 1 pre-existing error (ThemeToggle.tsx) and 1 pre-existing warning (RegistrationReviewLivePanel.tsx) in untouched files. Disposable test databases were created and destroyed. Not verified: interactive sign-in with a real development account, production configuration and HTTPS deployment. access_control suites were not re-run (no access_control code changed).

Human Approval: ☒ Approved by: Ronald C. Arias  Date: 11/17/2026

Next flow: WF-01.04. Do not start until Approved is ticked.

#### WF-01.04 — Logout and session termination

| Field | Definition |
| --- | --- |
| Actor / required permission | Any account holder with a valid Workspace session, whatever its active assigned roles. Signing out needs no feature-permission grant: the endpoint requires only a CSRF-verified browser request. Django framework staff and superusers never hold a Workspace session (WF-01.03), so they sign out of /admin/ separately. |
| Trigger | The user selects **Sign out** in the dashboard sidebar (DashboardShell), or **Sign Out** on the home-page signed-in card (WF-01.03 P-03). Both call POST /api/v1/auth/logout/. |
| Preconditions | The browser can obtain a CSRF token (GET /api/v1/auth/csrf/) and the request comes from a trusted origin. A session normally exists; an expired or already-terminated session is handled the same way (see Alternatives A and B). |
| Result | Django deletes the current server-side session row and expires the session cookie. The response is {"authenticated": false} with no-store caching and a request reference. The browser loads the public page /, which discards all in-memory account state. Any later request carrying the old session cookie is anonymous. Other devices' sessions are unaffected. |
| Status | Inspected and reconciled 16 November 2026 from the owner-supplied draft, then approved by the owner the same day with five safeguards (S-1 to S-5 below). P-01 to P-05 are implemented and verified by automated backend, unit and browser tests. The server-side logout needed no code change; its behavior is now covered by tests. D-17 and D-19 stay open. Human Approval recorded by the owner on 17 November 2026. |

**Inspection basis:** On 16 November 2026 the owner instructed "proceed with wf-01.04" and supplied a draft specification; it was reconciled against the code, and its unverified items were replaced with findings. Inspected: backend/apps/accounts/session_auth.py (LogoutView and WorkspaceSessionAPI, as committed in 66c1301), Django 6.1.2 django.contrib.auth.logout, SessionBase.flush and SessionMiddleware cookie deletion, registration_review_api.py (require_actor), frontend/src/features/auth/session.ts (logoutWorkspace), layouts/DashboardLayout.tsx, components/dashboard/DashboardShell.tsx, features/home/components/HomeLoginForm.tsx, features/admin/RegistrationReviewLivePanel.tsx, and the existing session and review tests. Draft corrections: the draft named roles (Treasurer, School Admin, Super Admin) that are not verified Workspace role names, so the actor is defined by session validity instead. The draft linked security events to WF-11.01; after the 0.3.3 renumbering that flow is WF-12.01. WF-01.03 Human Approval is still unchecked; this inspection started on the owner's explicit instruction.

**Implementation basis:** On 16 November 2026 the owner approved P-01 to P-05 and added safeguards. S-1: a failed session check is never treated as confirmed logout; the outcome stays uncertain with an explicit retry. S-2: location.replace() alone does not keep cached pages away, so the restored-page check stays. S-3: tabs also recheck when they become visible, including where BroadcastChannel is unsupported. S-4: 401 (not signed in) is distinguished from 403 (permission denied); a 403 never signs anyone out. S-5: tests cover old-cookie replay, anonymous logout, session-store failure, other tabs and dashboard restoration. Changed: frontend/src/utils/sessionSignals.ts (new: BroadcastChannel notice, visibility, pageshow and 401 signals), hooks/useSessionRevalidation.ts (new), features/auth/signOut.ts (new: confirmed sign-out outcome), api/client.ts and features/admin/registrationReviewApi.ts (401 authentication_required signal only), layouts/DashboardLayout.tsx (session recheck on signals; sign-out via signOutWorkspace and location.replace), features/home/components/HomeLoginForm.tsx (same sign-out confirmation; card rechecks). Tests added: backend/apps/accounts/test_session_auth.py (4 logout cases), frontend/tests/sign-out.test.mjs (5) and frontend/tests/browser/logout-errors.test.mjs (8). No backend application code, ERD, migration, permission, role, gate or settings change.

**Reconciliation findings and proposals (P-01 to P-05 implemented 16 Nov 2026 with safeguards S-1 to S-5):**
- Implemented and verified by code: LogoutView accepts POST only (GET returns 405), enforces CSRF and the trusted origin before anything else, and calls Django logout() for every request, authenticated or not. logout() flushes the session: it clears the data, deletes the session row and drops the key, which also removes any executor proof stored by WF-01.03. SessionMiddleware then expires the session cookie because the session is empty. The response is {"authenticated": false}, Cache-Control: no-store, plus X-Request-ID. It reveals no account data. Logout does not change the account, its roles or its permissions. The CSRF cookie is not rotated at logout; that is acceptable because login rotates it (WF-01.03). The frontend stores no session or account data in the browser (only the theme preference), and the full-page navigation to / discards React state. logoutWorkspace() fails closed: it reports success only when the server returns authenticated: false.
- P-01 Uncertain result — IMPLEMENTED (S-1). Before this change, a 403, 503, network failure or timeout leaves the dashboard showing "Sign-out could not be confirmed. Please try again." without checking whether the session still exists; the home signed-in card behaved the same way. Implemented: after any failed or uncertain logout, read GET /api/v1/auth/session/ (never repeat the POST automatically). If the session is anonymous, continue to / as signed out. If it is still authenticated, show "Sign-out did not complete. Please try again." and keep Sign out enabled. If the read fails too, show "Sign-out could not be confirmed. Check your connection and try again."
- P-02 Browser history — IMPLEMENTED (S-2). Sign-out used window.location.assign('/'), so /dashboard stays in history, and Back may restore a cached dashboard (back/forward cache) that still shows account details until it reloads. Implemented: the dashboard signs out with window.location.replace('/'), and still re-reads the session on pageshow when a page is restored from the back/forward cache.
- P-03 Other tabs — IMPLEMENTED (S-3). The dashboard read the session only on load, so another open tab keeps showing the shell, school_id, roles and permission hints after sign-out until it reloads; its protected API calls are denied server-side. Implemented: after a confirmed sign-out, post a data-free "signed-out" message on BroadcastChannel('ctug-session') (no storage). Dashboard tabs re-read the session on that message and whenever the tab becomes visible again, and switch to the existing "Sign in required" panel when the session is anonymous. The visibility recheck also covers browsers without BroadcastChannel. The home signed-in card rechecks the same way. A message never changes state by itself; only the server's session answer does.
- P-04 Protected-API 401 — IMPLEMENTED (S-4). When a module call returned 401 authentication_required (for example, the registration review list), the panel showed its own error and the shell still showed the account. Implemented: a 401 authentication_required from the shared client or the review API GET triggers a session re-read, and the dashboard switches to "Sign in required" only if the session is anonymous. 403 access_denied and the login's own 401 invalid_credentials never trigger it.
- P-05 Missing tests — IMPLEMENTED (S-5). No test replayed the old session cookie after logout, signs out an already-anonymous session, or simulates a session-store failure during logout, and no browser test covered dashboard sign-out. Added backend tests: the old cookie is anonymous for /session/ and is refused by the review API; anonymous logout with CSRF returns 200 {"authenticated": false} without creating a session; the logout response expires the session cookie; a session-store failure returns 503 auth_unavailable and the session is still reported as authenticated (logout is never claimed). Browser tests: dashboard sign-out success, uncertain result then anonymous, uncertain result still signed in, other-tab notification, and Back after sign-out.
- Recorded without change: there is no "Sign out from all devices" (the draft's Alternative E; D-19 stays open). Logout events are not recorded; Django's user_logged_out signal has no receivers (D-17).

#### Main flow

1. User is on /dashboard (or on / with the signed-in card from WF-01.03 P-03).
2. User selects Sign out (sidebar; on small screens inside the opened navigation drawer) or Sign Out (home card). The button shows "Signing out…" and blocks a second click.
3. Frontend gets a fresh CSRF token (GET /api/v1/auth/csrf/) and sends POST /api/v1/auth/logout/ with {} and X-CSRFToken: same-origin cookies, 15-second timeout, no automatic retry.
4. Backend enforces the method (POST only), CSRF and trusted origin before any other work.
5. Backend uses only the server-side session from the request cookie; the frontend sends no account identifier, role or permission.
6. Backend calls Django logout(): the session data is cleared, its database row deleted and its key dropped (this also discards any executor proof).
7. SessionMiddleware expires the session cookie because the session is now empty; the response is Cache-Control: no-store.
8. Backend returns {"authenticated": false} with an X-Request-ID reference and no account data.
9. Frontend accepts the result only if authenticated is false. Otherwise it reads GET /api/v1/auth/session/ once (never repeating the POST): anonymous counts as signed out; an active session or a failed read keeps the user on the page with an explicit retry (P-01).
10. Frontend tells other tabs through a data-free BroadcastChannel notice and replaces the history entry with / (location.replace). The full page load discards in-memory account state; nothing else is stored in the browser (P-02, P-03).
11. Opening /dashboard again reads GET /api/v1/auth/session/, which returns authenticated: false.
12. The dashboard shows "Sign in required" with Return to sign-in, and protected APIs refuse the old session (401). Any open dashboard tab rechecks on the notice, on becoming visible, on a back/forward-cache restore or on a protected 401, and shows the same panel (P-02 to P-04).

Rules:
- Logout ends only the current session. It never deactivates the account, removes roles or changes permissions.
- Logout is enforced server-side; clearing frontend state alone is never treated as signed out.
- No feature permission is needed; GET never signs out; CSRF and trusted-origin checks stay enforced.
- Other devices' sessions are not ended. A "sign out from all devices" feature needs separate approval (D-19).
- No session identifier, credential, CSRF secret or account detail appears in the response.
- A network failure is never treated as a confirmed sign-out, and the POST is never repeated automatically.

#### Alternative flows

Alternative A — Session already expired (implemented): 1. The user selects Sign out after the session has expired. 2. The request is anonymous; CSRF still applies. 3. logout() flushes the empty session and returns {"authenticated": false}; no session is created or restored. 4. The frontend continues to /.

Alternative B — Already signed out (implemented): 1. A second sign-out (for example, from another tab) sends the same request. 2. The response is the same {"authenticated": false}; account state does not change. 3. The frontend stays public.

Alternative C — Other tabs in the same browser (implemented, P-03): 1. The user signs out in one tab, which ends the shared session. 2. Other tabs' protected requests are refused. 3. Other tabs re-read the session on the BroadcastChannel notice or when they become visible (also without BroadcastChannel), and show "Sign in required".

Alternative D — Uncertain result (implemented, P-01): 1. The logout POST fails, times out or returns an unexpected body. 2. The frontend reads the session once. 3. Anonymous: continue to / as signed out. Still active: "Sign-out did not complete. Please try again." Read failed: "Sign-out could not be confirmed. Check your connection and try again." In both of the last two cases Sign out stays enabled for an explicit retry.

Alternative E — Other devices (implemented by design): 1. Signing out ends only this browser's session. 2. Sessions on other devices continue under the existing session policy (D-18, D-19).

Alternative F — Back button after sign-out (implemented, P-02): 1. The dashboard history entry was replaced, so Back does not return to it. 2. If a cached dashboard is still restored, it re-reads the session on pageshow and shows "Sign in required"; the backend refuses its requests.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| 3 | CSRF bootstrap or POST cannot be sent (network) | No sign-out is claimed. One session read follows: anonymous continues to /; otherwise "Sign-out did not complete. Please try again." or "Sign-out could not be confirmed. Check your connection and try again.", and Sign out stays enabled |
| 4 | CSRF missing or invalid, or untrusted Origin | HTTP 403 csrf_failed; the session is unchanged. The session read reports it still active, so "Sign-out did not complete. Please try again."; a retry fetches a new token |
| 4 | GET or another method | HTTP 405; nothing changes (test-verified) |
| 5 | Session missing, expired or already ended | HTTP 200 {"authenticated": false}; no session is created (Alternatives A and B; test-verified) |
| 6 | Session-store (database) failure during flush | HTTP 503 auth_unavailable; Django does not save sessions on 5xx, so the session stays active and logout is not claimed (test-verified). The session read then shows "Sign-out did not complete. Please try again." |
| 7–8 | Response lost or malformed | Treated as uncertain: one session read decides, as in step 3 |
| 10–11 | Back restores a cached dashboard | History entry replaced; a restored page rechecks on pageshow and shows "Sign in required" (P-02) |
| 12 | Protected API called with the old session | HTTP 401 authentication_required; the dashboard rechecks and shows "Sign in required". A 403 access_denied leaves the user signed in |
| 3–12 | Another tab still open | It rechecks on the BroadcastChannel notice or when shown again, then shows "Sign in required"; its protected requests are refused meanwhile |

#### Links

Depends on: WF-01.03 (session establishment and the shared WorkspaceSessionAPI). WF-01.06 (CSRF bootstrap, cookie and session configuration; D-18). Django session authentication. The shared dashboard and GET /api/v1/auth/session/. WF-03.05 (effective permissions checked on every later protected request).

Feeds: WF-01.03 (signing in again). WF-01.06 (session expiry and revocation behavior; D-19). WF-12.01 (logout events, once D-17 is approved; the draft's WF-11.01 is the pre-renumbering ID).

Traceability: SRS v0.3 UC-04 and FR-AUTH-01 are met for logout (server session, HttpOnly cookie, CSRF and trusted origin). FR-AUTH-04 is met for "logout SHALL invalidate the authenticated session"; its expiry and revocation part belongs to WF-01.06 and D-19. FR-AUTH-05 is met (protected APIs re-authorize every request). FR-AUD-02 and FR-AUTH-07 logout events are not met (D-17). docs/api/AUTH_ENDPOINT_INVENTORY.md lists the endpoint as "CSRF protected; server confirmation required", which matches.

Guidelines: Inspect → Reconcile → Approve → Implement → Test → Commit

AI Agent Checklist: ☒ Inspected   ☒ Reconciled   ☒ Approved   ☒ Implemented   ☒ Tested   ☒ Committed

Checklist scope: Approved records the owner's 16 November 2026 approval of P-01 to P-05 with safeguards S-1 to S-5; it is not Human Approval of the finished flow. Implemented and Tested cover P-01 to P-05 as described above. Committed: f5eaace on branch ronald (11 files: the source and test changes listed under Implementation basis and this catalogue); unrelated uncommitted work was left unstaged. D-17 and D-19 are unchanged.

Blocked by: No remaining development implementation blocker for P-01 to P-05. Open: D-17 (logout events), D-19 (session deletion, limits and sign-out from all devices), and cookie and session lifetime settings (D-18, WF-01.06). Human Approval recorded by the owner on 17 November 2026 for WF-01.01 to WF-01.06.04 by explicit instruction and approval on 16 November 2026. A real back/forward-cache restore and sign-out with a real development account are unverified.

Evidence level: Code-verified and automated-test verified, 16 November 2026. Backend: `manage.py test apps.accounts.test_session_auth --settings=config.test_settings` 22/22 passed (18 existing + 4 new: the replayed old cookie is anonymous for /session/ and refused with 401 by the review API, and its session row is deleted; the logout response expires the session cookie with no-store and no account data; anonymous and repeated logout return 200 {"authenticated": false} and create no session; a session-store failure returns 503 auth_unavailable and the session honestly stays active). All 23 accounts test modules: 384 tests, 381 passed; the same 3 test_registration_review_notifications failures as in WF-01.03, which belong to pre-existing uncommitted outbox work. Frontend: tests/sign-out.test.mjs 5/5 (confirmed sign-out; uncertain then anonymous; still active; failed status read stays unconfirmed; only 401 authentication_required signals, not 403 or login 401), with the POST sent exactly once in every case. `npm test`: 159 tests, 158 passed; the 1 failure is the known unrelated dashboard/mock-isolation test. `npm run test:registration-ui`: 51/51 passed, including 8 new real-browser scenarios on the actual dashboard with mocked APIs (sign-out then Back stays on /; uncertain then anonymous; still active; failed status read; other tab via BroadcastChannel; other tab without BroadcastChannel on visibility; restored-page recheck via a simulated persisted pageshow; protected 401 versus 403). `npm run build` passed; `npm run lint` is clean for changed files, with the same 2 pre-existing problems in untouched files. Not verified: a genuine browser back/forward-cache restore (simulated with a persisted pageshow event), sign-out with a real development account, and production configuration.

Human Approval: ☒ Approved by: Ronald C. Arias  Date: 11/17/2026

Next flow: WF-01.05. Do not start until Approved is ticked.

#### WF-01.05 — Forgot-password request and reset

| Field | Definition |
| --- | --- |
| Actor / required permission | Holder of an approved Workspace account who cannot sign in. It is a public flow: no session and no feature permission are needed. Eligibility: active, Approved, not framework staff or superuser, at least one active role, and verification proof for the account's current email (D-21). Framework administrators recover through /admin/ only. |
| Trigger | The user selects **Forgot Password?** on the home sign-in card, opens /forgot-password and submits a registered email (D-25). |
| Preconditions | WORKSPACE_PASSWORD_RESET_ENABLED is on; it defaults to off and activation needs separate owner approval (D-24). Protected executor mode is off, because recovery is refused there. The mail backend is configured (SMTP only when WORKSPACE_EMAIL_SMTP_ENABLED; otherwise the console backend). STUDENT_REGISTRATION_STAGING_KEY is at least 32 characters (shared OTP key). CSRF and trusted-origin checks pass. |
| Result | The account that uses that email receives a 6-digit code valid for 10 minutes. A correct code is exchanged for a 10-minute single-use reset ticket. A new password that meets the validators replaces the password hash, the recovery record is cleared, and every existing session of that account stops working on its next request. No session is created, and approval, activation, roles and permissions are unchanged. The user then signs in through WF-01.03. |
| Status | Change request CR-01 (email + OTP) is approved (D-25, D-26 and D-28 on 16 November 2026; D-27 with the HttpOnly-cookie ticket on 17 November 2026) and is implemented and verified by automated backend, unit and browser tests. It replaces the link-based flow (P-01 to P-07, commit 8a96162, receipt 2c0f30a) under D-28. WORKSPACE_PASSWORD_RESET_ENABLED remains off, and protected executor mode refuses recovery. Human Approval recorded by the owner on 17 November 2026. |

**Change request CR-01 (D-25, D-26 and D-28 approved 16 November 2026; D-27 approved 17 November 2026 with the HttpOnly-cookie ticket; implemented):** The owner asked for "Forgot Password → Enter Email → Receive OTP → Verify Code → Change Password → Sign In". During a development test the owner found that no reset email arrived; read-only counts showed 0 accounts eligible under D-21 (the only approved account has no verification proof, and the only account with proof is still Pending). The owner then approved D-25 (email-only recovery on /forgot-password with neutral responses), D-26 (6-digit OTP, 10-minute validity, 5 cumulative wrong attempts, 60-second resend interval, the per-email request limits, and resending never resets the attempt count) and D-28 (replace reset links with OTP recovery), and asked for D-27 to be reconciled before implementation. Superseded by CR-01 (now implemented): the School ID plus email request, the reset-link email, the URL-fragment token, Django's token generator (D-23) and the /reset-password link page. Kept from the link-based design: D-20, D-21, D-22, D-24, P-01 to P-03 feedback and limits, the protected-mode refusal and session invalidation.

**D-27 reconciliation (read-only, 16 November 2026):**
- Email uniqueness and ambiguity: accounts.email has the unique index accounts_email_200aa879_uniq under utf8mb4_unicode_ci (case-insensitive), and there are 0 normalized duplicate groups. Proposed lookup: normalize with normalize_account_email (trim, lower-case), match case-insensitively, and require exactly one row; more than one is treated as no match and logged only as "ambiguous".
- Existing storage: password_reset_token varchar(255) and password_reset_token_expires timestamp are installed, nullable, set on 0 rows and hidden from the Django admin. reapplication.py already clears both on reapplication. No new table, column or migration is needed.
- Reusable WF-01.01 utilities: 6-digit codes from secrets.randbelow; the keyed _digest (HMAC-SHA256 with STUDENT_REGISTRATION_STAGING_KEY, which fails closed if the key is under 32 characters) with new purpose names; policy() defaults (600 s code, 60 s resend, 5 attempts, 1800 s window); the pattern of counting wrong attempts on the locked row and committing before replying; after-commit delivery; and the HttpOnly, SameSite=Strict, path-scoped cookie used for registration ownership.
- Protected executor: the fencing DDL refuses credential-state updates on Approved accounts without the protected lease, and the executor's before_hash includes password_reset_token in protected-state evidence. Writing a code there would be refused and would also perturb that evidence. Recovery therefore stays explicitly refused in protected mode until a reviewed executor operation exists.
- Session invalidation: unchanged and already test-verified. set_password changes the session-auth hash, so Django flushes every other session on its next request. Clearing the recovery columns does not affect sessions.

**D-27 implementation (approved 17 November 2026 with the HttpOnly-cookie ticket; implemented as specified):**
- Record format in password_reset_token (ASCII, at most 160 characters, compared in Python with hmac.compare_digest, never in SQL): `rv1:otp:{attempts}:{window_start}:{issued_at}:{digest}` while a code is live; `rv1:ticket:{attempts}:{window_start}:{issued_at}:{digest}` after a correct code; `rv1:locked:{attempts}:{window_start}:0:` after the 5th wrong code. Times are UTC epoch seconds. password_reset_token_expires holds the live code's or ticket's expiry; the window end is window_start + 1800.
- Digests: code = _digest("password-recovery-otp", f"{account_id}:{window_start}:{issued_at}:{password_hash}:{email}:{code}"); ticket = _digest("password-recovery-ticket", f"{account_id}:{issued_at}:{password_hash}:{email}:{ticket}"). Binding to the password hash and email means a password or email change invalidates a live code or ticket.
- Request (POST /api/v1/auth/forgot-password/ {email}): inside one transaction, lock the eligible account. If there is no record or the window has ended, start a new window with attempts 0. If locked, or a code was issued less than 60 s ago, send nothing. Otherwise issue a new code, replacing the old one and keeping attempts and window, valid until min(issued + 600, window end). Commit, then queue the mail via transaction.on_commit to the D-20 sender. Always return the same 202 body.
- Verify (new POST /api/v1/auth/forgot-password/verify/ {email, code}): per-IP limits (4/minute, 20/day, own scope) plus a per-email verify budget (10/hour). Lock the row. Wrong or expired code: attempts + 1 (lock at 5), committed before the 400 is returned. Correct live code: replace the record with a ticket state (secrets.token_urlsafe(32), expiry now + 600), then set the ticket as an HttpOnly, SameSite=Strict, Secure-per-settings cookie scoped to /api/v1/auth/reset-password/ (max-age 600) and return 200. Every failure returns the identical 400 recovery_code_invalid; an unknown email still computes one HMAC so the work is similar.
- Reset (POST /api/v1/auth/reset-password/ {email, password, password_confirmation} + ticket cookie): own counters as today. Lock the row and require a live ticket state whose digest matches the cookie, plus eligibility. Validator failure: 400 with allowlisted fields, ticket kept until it expires. Success: set_password, set both recovery columns to NULL, save, queue the notice on commit and delete the cookie. Missing, expired, used or mismatched ticket: 400 reset_session_invalid.
- Concurrency: every step locks the account row, so wrong guesses are counted exactly, at most one ticket is issued per code, and one ticket gives exactly one password change.
- Guess bound: at most 5 wrong codes per window, windows bounded by 6 requests per day per email, so at most 30 guesses per day (a chance of about 3 in 100,000 per day for a 6-digit code).
- Residual timing: an eligible request performs one row update and commit (milliseconds) and other requests do not; mail is never sent in the request. This is an accepted residual and is smaller than the D-20 timing it replaces.
- Owner choice inside D-27: the HttpOnly cookie (approved 17 November 2026). Page scripts can never read the ticket; the verify response body is only {"status": "verified"}.
- Implementation notes: verification failures use the error code recovery_code_invalid (distinct from registration's otp_invalid so recovery keeps its own message), and an expired or missing ticket uses reset_session_invalid. Testing found and fixed a latent serializer bug: a request with unsupported fields raised a string error, which crashed DRF's error rendering into a 503; it now returns a 400. Changed files: backend/apps/accounts/password_reset.py (rewritten for the three steps), urls.py (forgot-password/verify/), test_password_reset.py (rewritten); frontend/src/api/client.ts (recovery_code_invalid and reset_session_invalid messages), features/auth/passwordReset.ts, ForgotPasswordPage.tsx (three steps), ResetPasswordPage.tsx (pointer for old links), tests/password-reset.test.mjs, tests/password-reset-feedback.test.mjs and tests/browser/password-reset-errors.test.mjs (rewritten). recovery_mail.py is reused unchanged. No ERD, migration, model or settings change; the gate default is unchanged (off).

**History of the link-based design (P-01 to P-07, committed in 8a96162; its reset-link behavior is superseded by CR-01 under D-28):**

**Inspection basis:** On 16 November 2026 the owner supplied a WF-01.05 draft, continuing the WF-01 sequence; it was reconciled against the code and its unverified items were replaced with findings. Inspected: backend/apps/accounts/password_reset.py (PasswordResetRequestView, PasswordResetConfirmView, throttles, eligibility), accounts/urls.py, config/settings.py (gate, PASSWORD_RESET_TIMEOUT 1800, AUTH_PASSWORD_VALIDATORS, mail backend, WORKSPACE_PUBLIC_BASE_URL), the Account model (the unused password_reset_token and password_reset_token_expires columns, and the email-verification proof fields), Django 6.1.2 PasswordResetTokenGenerator and get_user session-hash verification, frontend/src/features/auth/passwordReset.ts, ForgotPasswordPage.tsx, ResetPasswordPage.tsx, api/client.ts, and the existing tests. Draft corrections: the recovery identifier is School ID plus registered email, both required. The draft's "Continue" is the existing "Send reset link" button. The email-notification link is WF-09.04 (the draft's WF-08.04 is the pre-renumbering ID), and security events are WF-12.01. Existing-session invalidation does not depend on D-19, because Django already invalidates sessions when the password hash changes. WF-01.03 and WF-01.04 Human Approval are still unchecked; drafting and inspecting this flow does not waive them.

**Second reconciliation (16 November 2026):** The owner asked to reconcile P-01 to P-07 and D-20 to D-24 further before implementation, without code changes, and to keep WF-01.03, WF-01.04 and WF-01.05 Human Approval unchecked. Additionally inspected: the registration notification outbox (outbox_models.py, outbox_worker.py, process_registration_outbox, ERD table registration_notification_outbox), the executor fencing DDL (access_control/executor/schema.py) and its operations (engine.py), the read-only Django admin (accounts/admin.py), and read-only counts from the development database (no identities read). A temporary probe test was run on an isolated MySQL test database and then deleted; it is not part of the codebase.

**Implementation basis:** On 16 November 2026 the owner approved P-01 to P-07 and decided D-20 (option a, a controlled background sender, development only; production blocked until reliable delivery, failure handling and security are verified), D-21 (option A: verified email ownership required; legacy accounts without proof wait for a future authorized assisted-recovery procedure; no recovery through unverified addresses), D-22 (notice only after the update commits), D-23 (keep Django's token) and D-24 (keep recovery disabled; activation needs separate approval after production security and protected-executor compatibility). Changed: backend/apps/accounts/password_reset.py (verified-email eligibility at request and reset; per-identity request budget 3/hour and 6/day; separate reset counters; allowlisted field errors and the reset_link_invalid code; background delivery; post-commit notice; explicit fail-closed refusal in protected executor mode), backend/apps/accounts/recovery_mail.py (new: bounded in-memory background sender, 50-message queue, one daemon thread; logs only the message kind and exception type), frontend/src/api/client.ts (recovery_unavailable and reset_link_invalid messages), frontend/src/features/auth/passwordReset.ts (feedback mapping and copy), ForgotPasswordPage.tsx and ResetPasswordPage.tsx (ApiErrorNotice feedback, countdown, security refresh, uncertain-outcome message, field errors, password requirements, the "School ID or Staff ID" label, a "Request a new reset link" link, passwords cleared after every attempt, and the always-shown assisted-recovery hint "If no email arrives, your account may need assisted recovery. Contact support."). Tests: backend/apps/accounts/test_password_reset.py (fixture now carries verification proof; 15 new cases), frontend/tests/password-reset-feedback.test.mjs (4) and frontend/tests/browser/password-reset-errors.test.mjs (7). No ERD, migration, model, permission, role or settings change; the gate default is unchanged (off).

**Reconciliation findings and proposals (P-01 to P-07 implemented 16 Nov 2026 under D-20 to D-24):**
- Implemented and verified by code: both endpoints are POST-only, behind the gate (HTTP 503 recovery_disabled when off) and behind CSRF and trusted-origin checks. The request view returns the same HTTP 202 and the same message whether or not the account matches. Matching is exact on school_id (trimmed) and case-insensitive on email, against eligible accounts only. Ineligible means Pending, inactive, staff, superuser, no active role or no email; rejected registrations are deleted. Any internal error, including mail failure, is logged by exception type only and still returns the neutral 202. The token is Django's default_token_generator: an HMAC of the account ID, password hash, email and timestamp. Nothing is stored, it expires after PASSWORD_RESET_TIMEOUT (1800 s), and it becomes invalid once the password (or email) changes, so it is single-use. A newer request does not extend an earlier link. The link carries uid and token in the URL fragment, which is never sent to the server or in Referer headers. The reset page reads the fragment, removes it from browser history, and only an explicit POST uses it; opening the link changes nothing. Confirmation locks the account row (select_for_update), rechecks eligibility and the token under the lock, runs the Django password validators, and saves only the new hash, all in one transaction. A second use of the same token fails. Changing the password changes the session-auth hash, so Django's get_user flushes every other session of the account on its next request, including sessions that hold an executor proof. Reset never signs the user in. The unused password_reset_token and password_reset_token_expires columns need no change. Verified by the second-reconciliation probe: after a reset, another browser's signed-in session (also one holding a workspace_executor_proof value) reads as anonymous and its session row is deleted, so the proof is gone; the resetting browser gets no session cookie; a token older than 30 minutes is refused; two links sent minutes apart are both valid until one is used, after which the other is refused; Pending and no-email accounts get the neutral 202 and no mail; a mail failure returns the same 202 and logs only "could not be completed (OSError)", with no ID, email or token. Protected executor mode: the fencing DDL refuses credential updates on Approved accounts unless the protected writer holds a lease, and the executor has no password-reset operation, so a reset there fails closed (HTTP 503 recovery_unavailable). The real executor server was not run.
- P-01 Feedback and field errors (D-15 consistency) — IMPLEMENTED. (a) WorkspaceSessionAPI.handle_exception replaces every 400 body with the generic "Check the submitted data.", so the confirm view's "This reset link is invalid or expired." and the password-validator messages never reach the browser. (b) The frontend shows one message for every failure: "Password recovery is unavailable. Please try again later." on the request page, and "Unable to reset password. Your link may be invalid or expired." on the reset page, even for password-rule failures, 429, 403 or network errors. (c) recovery_unavailable is missing from API_MESSAGES, so a 503 shows the registration text "Registration is temporarily unavailable." (d) The request form says "School ID". Proposal: return an allowlisted 400 field error on confirm (token: the fixed invalid-or-expired text; password and password_confirmation: the existing safe frontend texts), and show the password requirements as helper text, as registration does. Use ApiErrorNotice with specific messages: 429 countdown, 403 "Refresh security check", recovery_disabled, recovery_unavailable and request reference. Clear the password fields after a failure, and label the field "School ID or Staff ID". Other copy is unchanged. Probe evidence: an expired token and a weak password both returned only {"error": {"code": "invalid_request", "message": "Check the submitted data."}}. With the gate off, the Forgot Password? link is still shown and the page currently says "Password recovery is unavailable. Please try again later."; P-01 would show the specific recovery_disabled text instead.
- P-02 Uncertain reset result (draft Alternative H) — IMPLEMENTED. A network failure, timeout or 5xx after the reset POST is reported as "link may be invalid or expired", although the password may have changed. Proposal: say "We could not confirm whether your password was changed. Try signing in with your new password. If that does not work, request a new reset link." Never repeat the POST automatically; an explicit retry is allowed, and a used token then fails safely.
- P-03 Abuse limits (D-16) — IMPLEMENTED. The only limits are per IP (4/minute, 20/day), and request and confirm share the same counters. Anyone who knows a School ID and email can send reset mail to that inbox from many IPs. Proposal: a per-identity request budget keyed by an HMAC digest of the normalized school_id (the D-14 and WF-01.03 mechanism), with proposed defaults of 3/hour and 6/day, checked before any lookup or mail; and separate throttle scopes for confirm so a burst of requests cannot block a confirmation. Probe evidence: two requests, one refused expired link and one successful reset used up the shared 4/minute budget, and the next reset attempt got HTTP 429.
- P-04 Timing (D-20) — IMPLEMENTED. Mail is sent synchronously inside the request (EMAIL_TIMEOUT 10 s), so a valid, eligible ID and email pair responds measurably slower than a wrong one. That reveals which pairs are registered, although the response text is identical. Proposal (owner choice in D-20): send the reset mail outside the request through a small bounded background dispatcher, so every response returns after the same work. The trade-off is that a mail lost on process restart is not retried, and the user can request again. D-20 evaluation: the only existing asynchronous mail mechanism is the registration notification outbox and its worker. It cannot be reused without an ERD change: decision_audit_log_id is NOT NULL, unique and tied to a review audit event; template_code is allowlisted to registration.approved and registration.rejected; and the table is fenced for the executor. A reset link must also never be stored, even encrypted. No other queue, thread pool or task runner exists. Options that need no ERD change and no new service: (a) a bounded in-process background sender, one daemon thread with a small queue, best effort, lost on restart, with a full queue logged and dropped; (b) keep sending synchronously and accept the timing exposure, documented; (c) pad every response to a fixed minimum time, which costs up to EMAIL_TIMEOUT (10 s) on every request and still leaks if SMTP is slower. Recommended: (a), with (b) as the fallback if the owner prefers no background thread.
- P-05 Verified email (draft Alternative G, D-21) — IMPLEMENTED. Eligibility does not check email-verification proof, so legacy accounts with an unverified address (email_verified_at NULL) still receive reset links. Proposal (owner choice in D-21): require email_verified_at to be set and email_verified_address to match the current email (case-insensitive) before sending. Accounts without proof get the same neutral response and need the support path, whose official contact is still pending owner input. D-21 evaluation: the development database has 1 approved, active, non-staff account, and it has an email but no proof (counts only; no identities read). Every account created before WF-01.01 OTP is in that state. No assisted recovery exists today: the Django admin for accounts is read-only, there is no support module (WF-10 not inspected or built), no School Admin operation can reset a password or correct an email, and the protected executor has no such operation. So a strict proof requirement would currently leave legacy accounts with no reachable recovery. Options: (A) require proof now, leaving legacy accounts with no self-service recovery until an approved assisted procedure exists (an attributable School Admin identity check plus a protected executor or WF-02/WF-10 operation, and the official support contact); (B) keep sending to the on-file email of legacy accounts, treating the requester's knowledge of School ID plus exact email and control of that mailbox as the proof, with D-22 notices and the accepted risk that a mistyped legacy address could let its mailbox owner take over the account; recording proof after a successful legacy reset is excluded, because it would change D-09 semantics; (C) apply A to accounts created with OTP proof and B to legacy accounts until a set date or until the assisted procedure exists. Recommended: C, which behaves as B for today's data, with the support dependency recorded.
- P-06 Password-changed notice (D-22) — IMPLEMENTED. No email is sent after a successful reset. Proposal: send "Your CTU-G Workspace password was changed" to the account email after the transaction commits. It contains no link or token, and its failure never changes the reset result. D-22 reconciliation: queue the notice with transaction.on_commit inside the existing atomic block, so it is sent only after the password update commits; a rollback (invalid token, validator failure, database error) sends nothing. Send it through the same mechanism chosen in D-20. Its recipient is the account's current email.
- P-07 Missing tests — IMPLEMENTED. Proposal backend tests: an existing session becomes anonymous after a reset; an expired token is refused; two links are both valid until one is used, then both fail; concurrent confirmations with the same token give exactly one success (MySQL TransactionTestCase); Pending, no-email and (if D-21) unverified accounts get the neutral 202 with no mail; a mail failure returns the same 202 and logs no ID, email or token; reset creates no session; confirm is gated; field errors are allowlisted; the per-identity budget. Frontend unit and browser tests: specific feedback, countdown, uncertain reset, the label, and that the fragment is removed from history.
- D-23 reconciliation: keep the Django token mechanism. No security or functional gap was found that needs a change: the token is HMAC-bound to the password hash and email, expires after 30 minutes, is refused after use, and every outstanding link dies on the first successful reset (probe-verified). Accounts have no last_login, so signing in does not invalidate a link; the first successful reset still does. Rotating SECRET_KEY invalidates all links. The existing password_reset_token columns stay unused. Several valid links at once is accepted behavior.
- D-24 reconciliation: WORKSPACE_PASSWORD_RESET_ENABLED stays off. Activation is a separate approval after P-01 to P-07, D-20 and D-21, and production HTTPS (D-18). In protected executor mode, a reviewed executor operation would also be needed. Until then the Forgot Password? link leads to the disabled message (P-01).
- Recorded without change: WORKSPACE_PUBLIC_BASE_URL accepts http, and production must use https (D-18, WF-01.06). Recovery events are not recorded (D-17).

#### Main flow

Email-OTP sequence (CR-01, owner-approved 16 and 17 November 2026; implemented and test-verified).

1. User opens / and selects Forgot Password? on the sign-in card.
2. /forgot-password step 1 shows "Forgot Password" with a single "Registered email" field.
3. User enters the email and selects Send code.
4. Frontend checks the field is filled, blocks a second submit, gets a CSRF token and sends POST /api/v1/auth/forgot-password/ with exactly {email}; no automatic retry.
5. Backend refuses with 503 recovery_disabled while the gate is off, and 503 recovery_unavailable in protected executor mode, before reading the body. It then enforces POST only, CSRF, trusted origin, the per-IP request limits (4/minute, 20/day) and the per-email budget (3/hour, 6/day per HMAC digest of the normalized email).
6. Backend normalizes the email (normalize_account_email: trimmed, lower-cased) and, inside one transaction, locks the eligible account that uses it (select_for_update). Eligible means active, Approved, not staff or superuser, an active role, and verification proof for this exact email (D-21). The unique, case-insensitive email index allows at most one match; if more than one row ever matched, the request is treated as no match and only "ambiguous" is logged.
7. For an eligible account, backend applies the D-26 rules to the recovery record in password_reset_token (D-27): a 30-minute window starts with the first code; a new code is issued only if no code was sent in the last 60 seconds and the window is not locked; wrong-attempt counts carry over across resends.
8. Backend generates a 6-digit code with secrets.randbelow, stores only its HMAC (bound to the account, the window, this issue time, the current password hash and email) plus the expiry, and commits.
9. After the commit, the code email is handed to the background sender (D-20): "Your CTU-G Workspace password reset code is 123456. It expires in 10 minutes. If you did not request this, ignore this email." It contains no link.
10. Backend returns HTTP 202 with the same neutral body in every case: "If an eligible account uses this email, we sent a 6-digit code. It expires in 10 minutes." plus resend_after 60 and code_valid_seconds 600.
11. The page moves to step 2, "Enter the 6-digit code", with a numeric, paste-friendly code field, Resend code after a 60-second countdown, and Start over.
12. User enters the code. The frontend sends POST /api/v1/auth/forgot-password/verify/ with {email, code} (new endpoint).
13. Backend applies the gate, executor refusal, CSRF, per-IP verify limits and a per-email verify budget, then locks the account row. A live code that matches is consumed at once and replaced by a reset ticket: 256 random bits, HMAC-stored, valid 10 minutes, sent only as an HttpOnly, SameSite=Strict cookie scoped to /api/v1/auth/reset-password/ (D-27 choice). A wrong code increments the attempt count and commits; the 5th wrong entry locks the window.
14. Any failure (unknown email, no code, expired, used, locked or wrong) returns the same HTTP 400 recovery_code_invalid "The code is incorrect or has expired." with no attempt count.
15. The page moves to step 3: New password and Confirm new password, with the password requirements shown.
16. User submits. The frontend sends POST /api/v1/auth/reset-password/ with {email, password, password_confirmation}; the browser adds the ticket cookie.
17. Backend applies the gate, executor refusal, CSRF and its reset limits, locks the account row, checks the ticket and eligibility, runs AUTH_PASSWORD_VALIDATORS, saves the new hash, clears both recovery columns and deletes the cookie, all in one transaction.
18. The new hash ends every existing session of the account on its next request. After the commit, the password-changed notice is queued (D-22).
19. Backend returns "Password changed. You can now sign in." without creating a session. The page shows it with Back to login, and the user signs in through WF-01.03.

Superseded by CR-01 (D-28): the link-based sequence committed in 8a96162, in which the user entered School ID plus email, received a 30-minute link carrying a Django token in the URL fragment, and set the password on /reset-password. It has been replaced; /reset-password now only points to Forgot Password, and its earlier verified behavior is recorded under Evidence level.

Rules:
- Recovery never approves, activates, deactivates or assigns roles, and never recreates a rejected or deleted registration.
- Public responses never reveal whether an email is registered or eligible: request responses are identical, and verification errors are identical.
- Codes, tickets and passwords never appear in logs, responses or browser storage; only HMACs and the password hash are stored. The ticket lives only in an HttpOnly cookie.
- Resending never resets the attempt count or extends the 30-minute window.
- A code or ticket is single-use and is invalidated by a password or email change.
- Reset never signs the user in. Password recovery stays separate from the authenticated password change in WF-04.03.
- The gate stays off until activation is separately approved (D-24). CSRF and trusted-origin checks are never relaxed for recovery.

#### Alternative flows

Alternative A — Email not registered or account not eligible (implemented): 1. No eligible account uses the email. 2. No code is created or sent. 3. The same 202 is returned and the page still moves to the code step; any code entered fails with the same recovery_code_invalid message.

Alternative B — Resend (implemented, D-26): 1. The user selects Resend code after the 60-second countdown, which sends the same request. 2. Within the window and budget, a new code replaces the earlier one, which stops working. 3. The attempt count and window end are unchanged. 4. Inside 60 seconds, while locked, or over budget, no code is sent and the response is still neutral (429 only when the per-IP or per-email limit is exceeded).

Alternative C — Code expired (implemented): 1. The code is older than 10 minutes, or the 30-minute window has ended. 2. Verification returns recovery_code_invalid. 3. The user selects Resend code; after the window ends, a new request starts a fresh window.

Alternative D — Wrong code (implemented): 1. A wrong code increments the cumulative count and commits. 2. The 5th wrong entry locks the window: no further code is accepted or sent until it ends. 3. The response is always the same recovery_code_invalid; the page clears the code field and offers Resend code and Start over.

Alternative E — Mail delivery fails (implemented, D-20): 1. The background sender fails or its queue is full. 2. Only the message kind and exception type are logged. 3. The request had already returned the neutral 202, so no delivery is claimed. 4. The stored code simply expires; the user can resend after 60 seconds within the budget.

Alternative F — New password rejected (implemented): 1. A password that fails the validators, or a mismatched confirmation, returns allowlisted field errors. 2. The password is unchanged and the ticket stays valid until it expires, so the user can correct it without a new code. 3. Both password fields are cleared.

Alternative G — Account without verified email (D-21 option A, unchanged): 1. A legacy account without proof, or whose proof is for another address, never receives a code. 2. The responses are the same as Alternative A, plus the assisted-recovery hint. 3. These users depend on a future authorized assisted-recovery procedure and the official support contact, which is still pending owner input.

Alternative H — Interrupted request or uncertain result (implemented): 1. The send, verify or reset POST times out or its response is lost. 2. The page never repeats the POST automatically. 3. After an uncertain send, the user can select Resend code. After an uncertain verify, entering the code again either succeeds or fails safely. After an uncertain reset, the page says "We could not confirm whether your password was changed. Try signing in with your new password. If that does not work, start again."

Alternative I — Ticket expired or missing (implemented): 1. More than 10 minutes pass after verification, or the cookie is missing. 2. Reset returns 400 reset_session_invalid "Your verification has expired. Request a new code." 3. The page returns to step 1.

Alternative J — Sessions after a reset (implemented mechanism, unchanged): 1. The password hash changes. 2. Django's get_user flushes every other session of the account on its next request, including sessions that hold an executor proof (test-verified in the link-based implementation).

Alternative K — Protected executor mode (implemented, unchanged): 1. All three endpoints refuse with 503 recovery_unavailable before any read, write or mail. 2. The fencing DDL would also refuse writes to an Approved account's recovery columns, and password_reset_token is part of the executor's protected-state hash, so recovery needs a reviewed executor operation before it can run there.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| 4–5, 12–13, 16–17 | Gate off, or protected executor mode | HTTP 503 recovery_disabled or recovery_unavailable before any read, write or mail |
| 4 | Email empty, or invalid format | Empty: inline message, no request. Invalid format: HTTP 400 invalid_request; nothing reveals whether an account exists |
| 4–5, 12–13, 16–17 | CSRF missing or invalid, or untrusted Origin | HTTP 403 csrf_failed before parsing; "Refresh security check" (no automatic POST) |
| 5, 13, 17 | Per-IP or per-email limit exceeded | HTTP 429 too_many_attempts + Retry-After; countdown with the button disabled |
| 6–8 | No eligible match, legacy account, locked window, resend within 60 seconds | Neutral HTTP 202; no code sent |
| 6 | More than one account matches the email (should be impossible) | Treated as no match; neutral 202; "ambiguous" logged without the email |
| 8–9, 13, 17 | Database error, or a staging key under 32 characters | Request: rolled back, neutral 202, error type logged, no code sent. Verify and reset: database errors return 503 recovery_unavailable; a short key fails closed with 503 auth_unavailable |
| 9 | Mail failure or full queue | Kind and exception type logged; nothing claimed (Alternative E) |
| 13–14 | Unknown email, no code, expired, used, locked or wrong code | HTTP 400 recovery_code_invalid "The code is incorrect or has expired."; wrong codes count toward the lock |
| 13 | Two verifications at once | The row lock serializes them; at most one ticket is issued, and each wrong code is counted |
| 17 | Ticket missing, expired, used or for another account | HTTP 400 reset_session_invalid; password unchanged; back to step 1 |
| 17 | Password fails a validator, or confirmation differs | HTTP 400 with allowlisted fields; password unchanged; ticket kept until it expires |
| 17 | Two resets with the same ticket | The row lock serializes them; exactly one succeeds and exactly one notice is sent |
| 17 | Database error | Rolled back; HTTP 503 recovery_unavailable; no notice |
| 4–19 | Network failure or timeout | No automatic repeat; the Alternative H message for the step |

#### Links

Depends on: WF-01.01 and WF-01.02 (registered email and verification proof; shared OTP utilities and the staging key). WF-01.03 (the sign-in card link; signing in afterwards). WF-01.06 (CSRF, cookies, HTTPS; D-18). WF-02.03 and WF-02.05 (approval and activation decide eligibility). The configured mail backend and the D-20 background sender.

Feeds: WF-01.03 (sign-in with the new password). WF-01.06 (sessions ended by the password change; the scoped ticket cookie). WF-04.03 (separate authenticated password change). WF-04.04 (an email change invalidates a live code or ticket). WF-09.04 (password-changed notice). WF-12.01 (recovery events, once D-17 is approved).

Traceability: SRS v0.3 (git HEAD) has no account-holder password-recovery requirement; FR-REC-01 and FR-REC-02 are cited only by docs/testing/MASTER_TEST_UAT_PLAN_DRAFT.md TC-010 (AT-17), probably from a later SRS version. TC-010's criteria (enumeration resistance, no secret disclosure, replay and expiry refusal, wrong CSRF) apply to the OTP flow. FR-AUD-05 (no reset secrets in logs or responses), FR-AUTH-01 and FR-AUTH-03 apply. Existing accounts columns only: password_reset_token and password_reset_token_expires, plus the email-verification proof fields. No new ERD entity, column or migration. One new endpoint (POST /api/v1/auth/forgot-password/verify/) and changed request bodies for the two existing endpoints.

Guidelines: Inspect → Reconcile → Approve → Implement → Test → Commit

AI Agent Checklist: ☒ Inspected   ☒ Reconciled   ☒ Approved   ☒ Implemented   ☒ Tested   ☒ Committed

Checklist scope: This checklist tracks CR-01 (the email-OTP specification above). Approved records the owner's approval of D-25, D-26 and D-28 (16 November 2026) and D-27 with the HttpOnly cookie (17 November 2026); it is not Human Approval of the finished flow. Implemented and Tested cover CR-01 as described under D-27 implementation and Evidence level. Committed: da9e480 on branch ronald (11 files: the CR-01 source and test changes and this catalogue); unrelated uncommitted work was left unstaged. The earlier link-based scope (P-01 to P-07) was approved, implemented, tested and committed in 8a96162 (receipt 2c0f30a); that history is recorded above and under Evidence level.

Blocked by: No remaining development implementation blocker for CR-01. Protected executor mode: recovery stays refused, because the fencing DDL blocks credential-state writes on Approved accounts and password_reset_token is part of the executor's protected-state hash; a reviewed executor operation is required first. Production blockers (recovery stays disabled, D-24): reliable delivery for the background sender (D-20 is development only), production HTTPS and Secure cookies (D-18; the ticket cookie follows SESSION_COOKIE_SECURE), the assisted-recovery procedure and official support contact for legacy accounts (D-21), policy sign-off of the D-16 and D-26 values, a shared cache for the rate limits in multi-process deployments, and the authentication-event contract (D-17). Separate activation approval is required (D-24). Human Approval recorded by the owner on 17 November 2026 for WF-01.01 to WF-01.06.04 has only its box ticked, with no name or date. Development account 7241423 is now eligible (owner-authorized direct approval, 17 November 2026). Turn WORKSPACE_PASSWORD_RESET_ENABLED off again after local testing.

Evidence level: CR-01 code-verified and automated-test verified, 17 November 2026. Backend: `manage.py test apps.accounts.test_password_reset --settings=config.test_settings` 26/26 passed: the full flow changes the password once and clears the record, and a replayed ticket is refused; only digests are stored; email normalization; unknown, legacy, mismatched-proof and inactive emails get identical responses and no code; framework staff get no code; a code expires after 10 minutes; a resend needs 60 seconds and replaces the code; 5 cumulative wrong codes lock the window, resends do not reset the count, and a new window starts after 30 minutes; a password change invalidates a live code; a ticket expires after 10 minutes and is required; a ticket cannot reset another account; field errors keep the ticket; other sessions (including one holding an executor proof) end and reset creates none; the notice is sent only after a committed change; the response does not wait for delivery; mail failure is neutral and logs no identity or code; a full queue is dropped; per-email request and verify budgets apply across IPs; a request burst does not block verify or reset; protected executor mode and the gate refuse every step; CSRF and exact fields are required; and two-thread tests show that simultaneous correct codes issue one ticket, simultaneous wrong codes are each counted, and simultaneous resets with one ticket succeed exactly once with one notice. All 23 accounts test modules: 404 tests, 401 passed; the same 3 test_registration_review_notifications failures as in WF-01.03 to WF-01.05, which belong to pre-existing uncommitted outbox work. Frontend: tests/password-reset.test.mjs 4/4 and tests/password-reset-feedback.test.mjs 4/4. `npm test`: 164 tests, 163 passed; the 1 failure is the known unrelated dashboard/mock-isolation test. `npm run test:registration-ui`: 59/59 passed on a clean run, including 8 rewritten recovery scenarios (full three-step flow with no ticket visible to page scripts; wrong code; resend countdown and Start over; expired verification; rejected password; uncertain reset without a repeated POST; disabled recovery and rate limit; old reset links redirected to Forgot Password). One earlier run under heavy CPU load from the concurrent backend suite timed out one registration scenario, which then passed 17/17 twice on its own. `npm run build` passed; `npm run lint` is clean for changed files, with the same 2 pre-existing problems in untouched files. Owner manual acceptance, 17 November 2026: on the development system (recovery temporarily enabled through WORKSPACE_PASSWORD_RESET_ENABLED=1 in backend/.env, real Gmail SMTP on), the owner requested a code for the registered email of account 7241423, received the real code email, verified it, changed the password, and reported "passed". To make that account eligible, the agent, with the owner's explicit authorization, set it to Approved and active and added its requested Student role in one transaction; its email-verification proof was genuine (from WF-01.01 registration) and was not altered. That change wrote no review or audit record and left assigned_by empty, so it does not appear in review history. Not verified: the real executor server and production configuration. Earlier D-27 reconciliation evidence (read-only, 16 November 2026): accounts.email has the unique index accounts_email_200aa879_uniq under utf8mb4_unicode_ci (case-insensitive), with 0 normalized duplicate groups. password_reset_token is varchar(255) utf8mb4_unicode_ci and password_reset_token_expires is a timestamp; both are installed and set on 0 rows. The only code that touches them is reapplication.py, which clears both, and the executor's before_hash, which includes password_reset_token in protected-state evidence. The Django admin omits both. Reusable WF-01.01 utilities were confirmed: secrets.randbelow 6-digit generation, the keyed _digest (fails closed if the staging key is under 32 characters), policy() defaults (600, 60, 5, 1800), the cumulative attempt counting that resends do not reset, the after-commit delivery, the HttpOnly SameSite=Strict scoped cookie, and normalize_account_email. Existing verified behavior (link-based implementation, 8a96162): 21/21 backend password-reset tests including two-thread concurrency, 7/7 unit, 58/58 browser tests, session invalidation including executor-proof sessions, the post-commit notice, background delivery, verified-email eligibility and the protected-mode refusal. Those mechanisms carry over to CR-01, but the OTP code paths themselves are unverified until implemented. Not verified: real SMTP, the real executor server, production configuration.

Human Approval: ☒ Approved by: Ronald C. Arias  Date: 11/17/2026

Next flow: WF-01.06. Do not start until Approved is ticked.

#### WF-01.06 — Session expiry and CSRF handling

| Field | Definition |
| --- | --- |
| Actor / required permission | System-enforced for every browser visitor: anonymous visitors on public forms (registration, OTP, recovery, sign-in) and signed-in Workspace account holders. No permission code is involved. Django framework administrators use /admin/, which keeps Django's own CSRF form handling and is outside the Workspace session (ADR-001). |
| Trigger | (a) Any state-changing browser request (POST) to /api/v1/auth/ endpoints; (b) any request carrying a session cookie; (c) a session reaching its expiry; (d) a dashboard tab re-reading the session after a WF-01.04 signal. |
| Preconditions | The browser can reach GET /api/v1/auth/csrf/ on the same origin (directly, or through the Vite proxy, which keeps Host and Origin), the host is in WORKSPACE_ALLOWED_HOSTS, and cookies are enabled. |
| Result | Every POST is accepted only with a matching CSRF token from a trusted origin; otherwise it is refused with HTTP 403 csrf_failed before any parsing or write, and the page offers an explicit "Refresh security check". A signed-in session ends on the server after 30 minutes without activity or 8 hours after sign-in, whichever comes first, or earlier if the account loses eligibility. Afterwards every request is anonymous, protected APIs return 401, and a dashboard that was in use shows "Your session has ended. Sign in again to continue." |
| Status | Owner-approved on 17 November 2026 (P-01 to P-07; D-18: 30-minute idle and 8-hour absolute limits, HTTPS and Secure cookies mandatory in production, DEBUG off by default; D-29: HttpOnly CSRF cookie; D-30: daily clearsessions; no background polling). P-01 to P-07 are implemented and verified by automated backend, frontend and browser tests. Production host, proxy, HTTPS forwarding and HSTS values still need verification before activation. Not committed (separate authorization); Human Approval recorded by the owner on 17 November 2026. |

**Inspection basis:** On 17 November 2026 the owner asked for a full Inspect and Reconcile of WF-01.06 (no implementation, no invented timeout values, Approve to Commit left unchecked). Branch ronald, clean at 64f1853 and level with origin/ronald, except the owner's uncommitted backend/.env.example, which was preserved. Inspected read-only:
- Settings: config/settings.py (middleware order, DEBUG hard-coded True, ALLOWED_HOSTS from WORKSPACE_ALLOWED_HOSTS, and no session, CSRF, HTTPS or CORS settings), config/test_settings.py, config/executor_runtime_settings.py (the protected profile sets SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE, SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS=3600 and DEBUG False), and the Django 6.1.2 global defaults.
- Backend: accounts/views.py (CSRFView, PublicJSONView), session_auth.py (WorkspaceSessionAPI CSRF check, LoginView, LogoutView, SessionView, _workspace_account), password_reset.py and student_registration_api.py (app cookies), registration_review_api.py (require_actor), and access_control/services.py (effective permissions).
- Frontend: api/client.ts (initializeCSRF, postJSON, readResponse), features/auth/session.ts, signOut.ts, layouts/DashboardLayout.tsx, utils/sessionSignals.ts and HomeLoginForm.tsx.
- Records: SRS v0.3 (FR-AUTH-01 to 07, NFR-SEC-02, OD-13; read from git history), docs/decisions/DOCUMENTATION_DECISION_REGISTER_DRAFT.md (OD-13 open; no recorded session-expiry values), a read-only count of django_session rows, and the existing tests.

WF-01.05 Human Approval is still unchecked; this inspection started on the owner's explicit instruction.

**Implementation basis:** On 17 November 2026 the owner approved P-01 to P-07 with these decisions. D-18: 30-minute idle and 8-hour absolute limits, both enforced on the server; activity never extends the absolute lifetime; HTTPS and Secure cookies mandatory in production; local HTTP development keeps working; DEBUG off unless explicitly configured; no assumed production domain or proxy. D-29: HttpOnly CSRF cookie once the bootstrap and client are verified compatible. D-30: daily clearsessions, documented, independent of enforcement. P-06: no background polling. Before implementing, the inspection evidence was re-verified against the working tree (branch ronald at 64f1853; only the owner's backend/.env.example and this uncommitted WF-01.06 inspection were modified). Changes:
- backend/config/security_settings.py (new). A pure, validated builder for DEBUG, cookie flags, HTTPS redirect, HSTS, the proxy SSL header, trusted origins, CORS and the session limits. The "local" profile (default) allows HTTP; the "production" profile refuses to start without WORKSPACE_HTTPS=1, with DJANGO_DEBUG on, or with a * host. Proxy trust and HSTS require HTTPS. Trusted origins must be exact scheme://host[:port] values with no wildcards, https-only under HTTPS. The CSRF and session cookies are HttpOnly and SameSite=Lax; CORS has no origins, no wildcard and no credentials. Errors name the variable, never its value.
- backend/config/settings.py. DEBUG and the security settings now come from build_security_settings(os.environ), replacing DEBUG = True; SessionTimeoutMiddleware is added immediately after AuthenticationMiddleware.
- backend/apps/accounts/session_timeout.py (new). A user_logged_in receiver stamps every login (the Workspace LoginView and Django admin) with _workspace_auth_at and _workspace_seen_at and sets the session expiry to 8 hours. The middleware flushes a session that is idle for at least 1800 s, at least 28800 s past sign-in, missing its timestamps (legacy fail-safe transition) or carrying a future timestamp. It records activity at most once per 60 s and keeps the cookie and database expiry at the absolute deadline. A session-store error returns 503 auth_unavailable JSON for /api/ paths (plain text otherwise, no-store).
- backend/apps/accounts/apps.py. ready() registers the login receiver.
- frontend/src/layouts/DashboardLayout.tsx. A tab that was showing a valid session and then finds it gone shows "Your session has ended. Sign in again to continue." (role="status") with Return to sign-in. A first visit keeps "Sign in using an approved, active Workspace account.". A 403 never triggers it, and no timer polls.
- docs/operations/LOCAL_SETUP_RELEASE_RUNBOOK_DRAFT.md. Section 5A documents every security variable (names only) and that local dev tools needing DEBUG require DJANGO_DEBUG=1 in the local .env; section 5B documents the daily clearsessions schedule with Windows Task Scheduler, cron and systemd templates; the release checklist gains both items. No scheduler was installed.
- Tests: backend/apps/accounts/test_session_security.py (new, 22 tests) and frontend/tests/browser/session-expiry-errors.test.mjs (new, 4 scenarios).
Not changed: ERD, migrations, models, endpoints, permissions, backend/.env, backend/.env.example (owner's uncommitted edits preserved), JWT (not introduced) and CSRF exemptions (none added).

**Reconciliation of the required cases (inspection findings; corrections P-01 to P-07 now implemented as described above):**
- Case 1, valid session continues. Expected: each request works while the session is valid and the account eligible. Actual: implemented. The DB-backed session is loaded each request, Django verifies the session-auth hash against the current password hash, and _workspace_account rechecks approval, activity, framework flags and at least one active assigned role. Tests: test_session_auth (login, session read). Gap: none.
- Case 2, idle expiry. Expected: an inactive session ends after a server-defined idle period. Actual: not implemented. SESSION_SAVE_EVERY_REQUEST is False and there is no idle logic, so inactivity never ends a session. Tests: none. Risk: a session left open on a shared campus computer stays usable. Correction: P-01. Decision: idle period value (D-18).
- Case 3, absolute expiry. Expected: a defined maximum session lifetime. Actual: implicit only. SESSION_COOKIE_AGE defaults to 14 days and, because sessions are rarely re-saved, it behaves as an absolute 14-day lifetime with a persistent cookie. It is not a defined policy (FR-AUTH-04 requires it to be defined and tested). Tests: none. Correction: P-01. Decision: absolute lifetime value (D-18).
- Case 4, protected page after expiry. Expected: no protected content; "Sign in required". Actual: implemented. DashboardLayout reads GET /api/v1/auth/session/ on load and shows "Sign in required" when anonymous. Tests: tests/session.test.mjs and the WF-01.04 browser tests. Gap: the message does not say the session ended (P-05).
- Case 5, protected API after expiry. Expected: refused. Actual: implemented. Protected APIs return 401 authentication_required, and the dashboard rechecks and shows "Sign in required"; a 403 never signs out. Tests: test_registration_review_api session-required and p3c boundary tests; browser test "protected 401 vs 403".
- Case 6, missing, invalid or stale CSRF token. Expected: refused before any effect; explicit recovery. Actual: implemented. CSRFCheck runs in initial() for every Workspace API POST, including anonymous ones; 403 csrf_failed; the frontend fetches a fresh token before every POST and offers "Refresh security check" without repeating the POST. Tests: test_session_auth (anonymous login, logout), test_registration and the OTP and recovery suites, and the browser CSRF-refresh scenarios.
- Case 7, untrusted origin. Expected: refused. Actual: implemented. Origin must match the request host (CSRF_TRUSTED_ORIGINS is empty), and no CORS access is granted (django-cors-headers has no settings). Tests: test_untrusted_origin_rejected (login). Gap: no Origin test on other POST endpoints (P-07).
- Case 8, account deactivated during a session. Expected: refused at the next request. Actual: implemented. Inactive or unapproved accounts read as anonymous, and ModelBackend.get_user refuses inactive users. The session row itself is not deleted (D-19). Tests: test_session_reflects_revoked_approval, test_pending_rejected_and_inactive_accounts_cannot_login, test_permissions inactive and rejected cases.
- Case 9, role or permission revoked during a session. Expected: effective at the next request. Actual: implemented. Permissions are recomputed per request and never stored in the session; the session payload holds only UI hints. Tests: test_session_reflects_removed_role_without_cached_grants, test_revoked_permission_detected_after_session_created, p3c role and read-grant revocation tests, and test_role_grant_revocation_takes_effect_on_the_same_account_instance.
- Case 10, account Deny or disabled service. Expected: Deny wins; a disabled service grants nothing; no administrative name bypass. Actual: implemented in access_control.services. An active Deny excludes the permission despite any grant; Permission.service.is_active must be true; role names, including Admin and Super Admin, confer nothing; evaluation errors return an empty set (fail closed). The review API additionally requires both services active (503 review_unavailable). Tests: test_permissions (Deny override, Grant-to-Deny, inactive service, admin-name and technical-super-admin no-bypass, requested_role manipulation). Gap: no test that the session endpoint's permission hints drop a denied or service-disabled code (P-07).
- Case 11, password change or reset. Expected: other sessions end. Actual: implemented for recovery (WF-01.05). Django flushes sessions whose auth hash no longer matches, including sessions holding an executor proof. Tests: WF-01.05 session-invalidation test. Authenticated password change belongs to WF-04.03 (not built).
- Case 12, several tabs after logout or expiry. Expected: every tab stops showing account data. Actual: implemented (WF-01.04). BroadcastChannel notice plus visibility, pageshow and 401 rechecks. Tests: WF-01.04 browser tests (with and without BroadcastChannel). Expiry with no signal is caught at the next visibility change or request.
- Case 13, Back or cached dashboard. Expected: no restored authenticated data. Actual: implemented. Sign-out replaces history; pageshow (persisted) rechecks; all auth and API responses are Cache-Control: no-store. Tests: WF-01.04 Back and restored-page browser tests. Note: HTML caching headers of a production static host are a deployment item (P-02).
- Case 14, network errors or session-store outage. Expected: fail closed, with no false sign-in or sign-out. Actual: implemented. A failed session read shows "Session unavailable" with Try again, never the shell; network failures are never treated as anonymous; a session-store failure on logout returns 503 and keeps the session (WF-01.04); SessionView turns unexpected errors into 503 auth_unavailable. Tests: frontend "network failures must not be interpreted as anonymous sessions", "malformed session response fails closed"; backend logout store-failure test. Gap: no backend test for a session-store failure on GET /session/ (P-07).
- Case 15, public registration and OTP. Expected: CSRF-protected without creating an authenticated session. Actual: implemented. All public POSTs run CSRFCheck; registration and OTP use their own HttpOnly, SameSite=Strict, path-scoped stage cookie, and recovery uses its ticket cookie; none logs anyone in. Tests: test_registration (no session cookie after registration), the OTP suites, and the recovery test "reset creates no session".
- Case 16, login rotation. Expected: a new session key and CSRF token at login. Actual: implemented (Django login() cycles the key and rotates the token; the previous session is flushed when another account signs in). Tests: test_login_rotates_anonymous_session_key_and_csrf_token.

**Proposals (owner-approved and implemented 17 November 2026; text below is the approved specification):**
- P-01 Defined session expiry (D-18; values are owner decisions; none are recorded in the SRS or decision register). New backend/apps/accounts/session_timeout.py with WorkspaceSessionTimeoutMiddleware, placed after AuthenticationMiddleware in config/settings.py. LoginView stores the sign-in time (epoch seconds) in the session after login(). For a session that has it, the middleware compares now with the sign-in time (absolute limit) and with the last-activity time (idle limit); on either breach it flushes the session, which reads as anonymous (401 on protected APIs). The last-activity value is refreshed at most once per 60 seconds, to limit database writes. New settings WORKSPACE_SESSION_IDLE_SECONDS and WORKSPACE_SESSION_ABSOLUTE_SECONDS are read from the environment and validated as positive integers, with idle not above absolute; SESSION_COOKIE_AGE is set to the absolute value. No new endpoint, response shape, table or migration; the session-row format is unchanged apart from two keys.
- P-02 Deployment security settings (D-18). config/settings.py reads DEBUG, SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE, SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS, SECURE_PROXY_SSL_HEADER and CSRF_TRUSTED_ORIGINS from the environment, so local HTTP development keeps working through backend/.env and HTTPS deployments set them explicitly. The protected profile keeps its own overrides. Owner decisions: the default when DEBUG is not set, and the production host and proxy details.
- P-03 CSRF cookie HttpOnly (D-29). Set CSRF_COOKIE_HTTPONLY = True. Verified safe: the frontend takes the token only from the /csrf/ JSON body and never reads document.cookie; Django admin forms use a hidden field. No request or response contract changes.
- P-04 Expired-session cleanup (D-30). Document and schedule `python manage.py clearsessions` (for example daily) in docs/operations/LOCAL_SETUP_RELEASE_RUNBOOK_DRAFT.md and the deployment, alongside the registration staging purge. No code or schema change. Today there are 4 rows and none expired; without cleanup, expired rows accumulate.
- P-05 Session-ended feedback. In DashboardLayout, when a tab that held a valid session finds it anonymous, show "Your session has ended. Sign in again to continue." with Return to sign-in, announced with role="status"; a first visit keeps "Sign in required". The server discloses no reason.
- P-06 Expiry signal. Treat the existing 401 recheck as the expiry signal; no polling timer is added, to avoid background traffic and battery use.
- P-07 Tests to add. Backend:
  - idle expiry and absolute expiry flush the session, and activity within the idle window keeps it
  - the last-activity write is throttled to once per minute
  - settings validation rejects bad values
  - cookie flags under secure settings
  - the CSRF cookie is HttpOnly and the /csrf/ body still carries the token
  - an untrusted Origin is refused on logout, registration, OTP and recovery POSTs
  - a session-store failure on GET /session/ returns 503, not anonymous
  - the session endpoint's permission hints drop a code after an account Deny and after its service is disabled
  - clearsessions removes only expired rows

  Frontend unit and browser tests:
  - the session-ended message
  - CSRF refresh still works with an HttpOnly CSRF cookie
  - expiry during dashboard use, triggered by a protected 401
- Quality considerations: Security (shorter exposure on shared devices; script-inaccessible CSRF secret; Secure and HTTPS in deployment; fail-closed paths unchanged). Reliability and availability (no new dependency; expiry uses the existing session store; cleanup is offline). Performance and scalability (at most one session write per user per minute; clearsessions keeps django_session bounded; database-backed sessions need a shared database across workers, which already holds). Data integrity (no account or permission data is touched by expiry). Usability and accessibility (clear, announced session-ended message; no silent loss of typed data beyond the expired session). Maintainability and flexibility (all values from the environment; one middleware). Compatibility (LAN HTTP development unchanged; no JWT; no change to the registration, OTP or recovery contracts).
- Recorded without change: deletion of other session rows on deactivation or role change, and limits on concurrent sessions, stay open (D-19, OD-13); authentication-event logging stays open (D-17).

#### Main flow

1. A visitor opens any Workspace page; reading public pages needs no session or CSRF state.
2. Before every state-changing request, the frontend calls GET /api/v1/auth/csrf/; the backend returns the token in the JSON body (Cache-Control: no-store) and sets the csrftoken cookie (HttpOnly, SameSite=Lax; Secure under HTTPS).
3. The frontend sends the POST with X-CSRFToken, same-origin cookies, a JSON body and a 15-second timeout; it never retries automatically.
4. The view runs CSRFCheck before parsing, throttling or writing: the token must match the cookie, and the Origin must match the request host (CSRF_TRUSTED_ORIGINS is empty).
5. On success the request proceeds. Login also cycles the session key and rotates the CSRF token (WF-01.03); public registration, OTP and recovery steps create no authenticated session.
6. While signed in, each request carries the HttpOnly session cookie. The backend loads the server-side session, verifies the session-auth hash against the current password hash, and rechecks approval, activity, framework flags and an active assigned role.
7. Protected operations evaluate exact effective permissions per request: role grants and direct Grants, with active Deny precedence and active services only, and no bypass by role name.
8. SessionTimeoutMiddleware (P-01) runs after authentication on every request: it records activity at most once a minute and flushes the session after 30 minutes without recorded activity or 8 hours after sign-in, and flushes legacy sessions without timestamps. A concurrent request cannot save an expired session back (Django refuses to update the deleted row). A session-store error fails closed with 503.
9. Once the session is expired, flushed or ineligible, the next session read is anonymous and protected APIs return 401 authentication_required.
10. Open dashboards recheck on a protected 401, on becoming visible, on another tab's sign-out notice and on a back/forward-cache restore (no polling), then show "Sign in required" with "Your session has ended. Sign in again to continue." when the tab had a session.
11. The user signs in again through WF-01.03.
12. A daily clearsessions run (documented in the runbook, section 5B; installation needs deployment approval) removes expired session rows. Enforcement never depends on it.

Rules:
- Every unsafe request is CSRF-checked server-side, including anonymous ones; GET never changes state.
- No state-changing request is repeated automatically after a CSRF, network or uncertain failure.
- The CSRF token comes only from the /csrf/ response body; scripts never need the cookie.
- Session identifiers and credentials never go into localStorage or sessionStorage; only the theme preference is stored there.
- Authorization never trusts frontend role labels, permission hints or requested_role; every protected request re-evaluates the account on the server.
- Session expiry never changes the account, its roles or its permissions.
- Authenticated responses are not cacheable (Cache-Control: no-store).
- Verification failures fail closed: no shell, no grant, no claimed sign-out.
- Web sessions stay Django server-side sessions; no JWT.

#### Alternative flows

Alternative A — CSRF token missing, stale or mismatched (implemented): 1. The POST fails CSRFCheck. 2. HTTP 403 csrf_failed with a request reference; nothing is parsed or written. 3. "Refresh security check" fetches a new token without repeating the POST, and the user resubmits.

Alternative B — Untrusted origin (implemented): 1. The Origin header does not match the host. 2. HTTP 403 csrf_failed; nothing changes.

Alternative C — Idle or absolute expiry (implemented, P-01 and P-05): 1. The session reaches 30 minutes without recorded activity or 8 hours after sign-in. 2. The middleware flushes it on the next request (the row is deleted, and replaying its cookie is anonymous). 3. Protected APIs return 401; the dashboard shows "Your session has ended. Sign in again to continue." with Return to sign-in.

Alternative D — Eligibility lost during a session (implemented): 1. The account is deactivated, unapproved or loses its last active role, or a permission is revoked, denied or its service disabled. 2. The next request re-evaluates: an ineligible account is anonymous (401); a missing permission is refused (403) while the user stays signed in.

Alternative E — Password changed or reset (implemented for recovery, WF-01.05): 1. The password hash changes. 2. Every other session is flushed at its next request.

Alternative F — Several tabs or restored pages (implemented, WF-01.04): 1. Logout or expiry happens in one tab. 2. Other tabs recheck on the notice, on visibility or pageshow, or on a 401, and show "Sign in required".

Alternative G — Session store or network unavailable (implemented): 1. The session read or a request fails. 2. The dashboard shows "Session unavailable" with Try again; a failed logout is never claimed; nothing is treated as a valid session.

Alternative H — Public form POSTs (implemented): 1. Registration, OTP and recovery POSTs pass CSRFCheck. 2. They use their own scoped HttpOnly cookies and never create an authenticated session.

Alternative I — Cookies blocked (implemented): 1. The CSRF cookie is missing. 2. Every POST fails with 403 csrf_failed and security-refresh guidance; no session is created.

Alternative J — Session created before this change (implemented fail-safe transition): 1. An authenticated session has no sign-in timestamp. 2. The middleware flushes it on its next request. 3. The user signs in once more; every new login is stamped.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| 2 | /csrf/ unreachable (network) | No POST is sent; "We could not refresh the security check. Check your connection and try again." |
| 4 | Token missing or mismatched | HTTP 403 csrf_failed before parsing or writes; "Refresh security check"; no automatic retry (test-verified) |
| 4 | Untrusted Origin, or (HTTPS without Origin) a cross-site Referer | HTTP 403 csrf_failed; no state change (test-verified on all 11 auth POST endpoints and the HTTPS Referer check) |
| 4 | Host not in ALLOWED_HOSTS (for example a new LAN address) | Django refuses the request with HTTP 400; add the host to WORKSPACE_ALLOWED_HOSTS |
| startup | Invalid or inconsistent security setting (for example production without HTTPS, proxy trust without HTTPS, a wildcard trusted origin, idle above absolute) | Django refuses to start with ImproperlyConfigured naming the variable, never its value (test-verified) |
| 6 | Session-auth hash no longer matches (password changed) | Session flushed; request anonymous (test-verified) |
| 6 | Account inactive, unapproved or without an active role | Request anonymous; protected APIs 401; dashboard "Sign in required" (test-verified) |
| 7 | Permission revoked or denied, or service disabled | Exact check refuses (403 or 503 review_unavailable); user stays signed in; hints recomputed (test-verified, including the session hints after a Deny and a disabled service) |
| 7 | Permission evaluation fails | Empty permission set (fail closed) and an error logged without identifiers (test-verified) |
| 8 | Idle (≥ 1800 s) or absolute (≥ 28800 s) limit reached, legacy or tampered timestamps | Session flushed; next request anonymous; the dashboard shows the session-ended message (test-verified) |
| 9 | Session store unavailable | Middleware returns 503 auth_unavailable (no-store) before any view; the dashboard shows "Session unavailable" with Try again; nothing is lost when the store returns (test-verified) |
| 10 | Protected API without a valid session | HTTP 401 authentication_required; dashboard rechecks and shows "Sign in required" (test-verified) |
| 12 | Expired rows not yet removed | The daily clearsessions run removes them (runbook 5B); expired rows are never accepted meanwhile (clearsessions test-verified) |

#### Links

Depends on: WF-01.03 (session creation; key and token rotation). WF-01.04 (logout; cross-tab, restored-page and 401 rechecks). WF-01.05 (password change flushes sessions; recovery ticket cookie). WF-03.05 (effective permissions, Deny precedence and service state). Django sessions and CsrfViewMiddleware; config/settings.py and the deployment runtime profile.

Feeds: Every authenticated workflow and every public form POST (WF-01.01 to WF-01.05, the WF-02 review actions and later modules). WF-12.01 (session events, once D-17 is approved). WF-12.05 (session-row retention and cleanup).

Traceability:
- SRS v0.3 FR-AUTH-01 (server sessions, HttpOnly cookies, CSRF and trusted-origin checks on state changes): met.
- FR-AUTH-02, FR-AUTH-03 and FR-AUTH-05 (eligibility and per-request authorization): met.
- FR-AUTH-04 ("session expiry ... SHALL be explicitly defined and tested"): not met. Expiry is an implicit default (P-01, D-18).
- NFR-SEC-02 (HTTPS; secure HttpOnly SameSite cookies; CSRF; no localStorage tokens): met except HTTPS and Secure flags outside the protected profile (P-02).
- OD-13 and D-19 (revocation timing): per-request revalidation is implemented; deleting session rows stays open.
- No ERD entity, column or migration is required. django_session is Django's framework table.

Guidelines: Inspect → Reconcile → Approve → Implement → Test → Commit

AI Agent Checklist: ☒ Inspected   ☒ Reconciled   ☒ Approved   ☒ Implemented   ☒ Tested   ☒ Committed

Checklist scope: Inspected and Reconciled cover the read-only inspection and the 16-case reconciliation above, re-verified against the working tree on 17 November 2026 before implementation. Approved records the owner's 17 November 2026 authorization of P-01 to P-07 with D-18, D-29, D-30 and the no-polling rule; it is not Human Approval. Implemented and Tested cover P-01 to P-07 as described under Implementation basis and Evidence level: all WF-01.06 tests and the 15-check interactive run pass. After the authorized repository and test corrections, every backend, frontend and browser suite listed under Evidence level passes; only the 2 pre-existing lint findings in untouched files remain. Committed: owner-authorized local commits on branch ronald, not pushed: 23f9b8e (repository repair), f32a526 (test-only corrections) and 9a56fd9 (WF-01.06 implementation, tests and documentation). backend/.env.example was left unstaged.

Blocked by:
- No remaining development implementation blocker for P-01 to P-07.
- Commit: done locally (23f9b8e, f32a526, 9a56fd9); pushing to GitHub has not been authorized.
- Production activation: verification of the production host, reverse proxy, HTTPS forwarding (WORKSPACE_TRUST_PROXY_SSL_HEADER only if the proxy sets and strips X-Forwarded-Proto), trusted origins and HSTS value; then WORKSPACE_DEPLOYMENT_PROFILE=production. Installation of the daily clearsessions scheduler needs verified deployment access and approval.
- Local development: tools that require DEBUG (config.review_local_settings and the *_local_dev commands) need DJANGO_DEBUG=1 in the local backend/.env, which the agent did not edit.
- Repository corrections completed (owner-authorized 17 November 2026; none changes WF-01.06 behavior):
  - Pinned catalogue sources restored byte-exact from 9594a02 in commit 23f9b8e: phase1h-c1-permission-catalogue-governance-proposal.md (02eb308d…), AR-3B2A-permission-catalogue-v2-proposal.md (56ccd699…), AR-2-revised-administrator-access-control.md (b36c0dac…) and AR-3A-administrator-architecture-finalization.md (464c0fec…) as LF, and docs/SRS/CTU-G_Workspace_SRS_v1.md (af4ead4f…) as CRLF, the form its pin requires. A new .gitattributes marks exactly these five paths -text, so core.autocrlf can no longer change their bytes; nothing repository-wide changed. A full audit shows all six pinned sources in c1_v1.json and v2_0.json match.
  - Test-only corrections in commit f32a526: test_registration_review_notifications.py now pins WORKSPACE_PUBLIC_BASE_URL=http://localhost:5173, an empty WORKSPACE_EMAIL_PUBLIC_HOSTS and WORKSPACE_REGISTRATION_OUTBOX_ENABLED=False, so a developer's .env cannot change the result (production email rules unchanged). registration-review-api-contract.test.mjs now allows the dashboard's intentional AR-6C7E.1 import of registrationReviewApiGate, and only that review module, while still rejecting direct imports of the review API client or contract; the preview check is unchanged.
- Remaining, outside this flow: full frontend lint still reports 1 error (ThemeToggle.tsx no-useless-assignment) and 1 warning (RegistrationReviewLivePanel.tsx exhaustive-deps) in untouched files, pre-existing since before WF-01.
- D-17 and D-19 (OD-13) remain open.
- Human Approval recorded by the owner on 17 November 2026 for WF-01.01 to WF-01.06. WF-02.01 is not started.

Evidence level: Code-verified and automated-test verified, 17 November 2026 (branch ronald, base 64f1853, uncommitted).
- New backend tests: `manage.py test apps.accounts.test_session_security --settings=config.test_settings` ran 22 tests, all passed. They cover: a valid session inside the idle window; idle expiry exactly at 1800 s with the row deleted; activity every 1700 s extending idle but not past 28800 s (valid at 28799, ended at 28800); activity written at most once per 60 s, with the cookie max-age and database expiry following the absolute deadline; login stamping a fresh session and rotating CSRF; legacy sessions without timestamps ended; future timestamps ended; Django admin logins stamped; expired-cookie replay rejected; a concurrent stale request unable to save an expired session (UpdateError); deactivation; role revocation, account Deny and a disabled service dropping session hints without signing out; a session-store outage returning 503 (API JSON and the admin page) and recovering; the HttpOnly CSRF cookie with the body token still working; missing and invalid tokens refused; an untrusted Origin refused on all 11 auth POST endpoints (reapplication with its gate on); the HTTPS Referer check; clearsessions removing only expired rows; local and production settings profiles; rejection of unsafe or inconsistent values; and the active middleware order and policy.
- Backend regression: all 24 accounts test modules ran 426 tests, 423 passed; the 3 failures are the known test_registration_review_notifications cases (outbox work). access_control: the 36 modules other than test_catalogue ran 1020 tests, 916 passed; all 104 failures are in test_catalogue_v2 and test_catalogue_planner_v2 and all are caused by the deleted pinned v2 proposal (FileNotFoundError). test_catalogue (61 tests) fails for the same reason with the deleted c1 proposal. Neither is related to WF-01.06. `manage.py check`: no issues. Earlier in the same session, after the middleware was added: test_session_auth, test_password_reset and test_registration_review_api ran 68 tests, all passed.
- Frontend: `node --test tests/browser/session-expiry-errors.test.mjs` 4/4 (an expiry found by a protected 401 shows the session-ended message and drops account data; expiry noticed on visibility with no background polling; a first visit keeps the ordinary text; a 403 never shows the message). `npm run test:registration-ui` 63/63 on a clean run; the first run timed out the first test of three files on the cold Vite compile, and those passed on re-run. `npm test` 164 tests, 163 passed (the known dashboard/mock-isolation test). `npm run build` passed. `npm run lint` is clean for changed files, with the same 2 pre-existing problems in untouched files.
- Final verification, 17 November 2026, after the repository corrections:
  - `manage.py check`: no issues.
  - Catalogue suites (test_catalogue, test_catalogue_v2, test_catalogue_planner_v2): 119/119.
  - All 37 access_control modules: 1081/1081, so the 103 missing-SRS failures are resolved.
  - All 24 accounts modules: 426/426, including the 3 decision-email tests and the 22 WF-01.06 tests.
  - `npm test`: 164/164, including the corrected dashboard assertion.
  - `npm run test:registration-ui`: 63/63, including the 4 WF-01.06 browser scenarios.
  - `npm run build` passed; eslint is clean on every changed frontend file.
  - Pre-WF-01.06 baseline (worktree at 64f1853), used to diagnose the decision-email failures: 4/7 before the correction.
- Interactive local verification, 17 November 2026: 15/15 checks passed. The stack was a real Edge browser, the real Vite dev server and real Django (full middleware stack, WSGI) on a disposable isolated MySQL test database created and dropped by the run (0 leftover test databases). Only session_timeout._now was offset to reach the boundaries. Checks:
  - Login through the real form opened the dashboard.
  - The session cookie is HttpOnly and SameSite=Lax; the CSRF cookie is HttpOnly and unreadable by page scripts.
  - A POST without the token returned 403 and the session survived; the token is available from the /csrf/ body.
  - Idle 29:59 kept the session; activity restarted the idle window; idle exactly 30:00 ended it on the server, and the dashboard showed "Your session has ended. Sign in again to continue." with account data dropped.
  - Return to sign-in recovered with a fresh login.
  - Continuous activity kept the session for 7h 56m; absolute 7:59:59 kept it; absolute exactly 8:00:00 ended it although the last activity was 26:40 earlier.
  - Replaying the expired cookie stayed anonymous.
  The run's scripts were scratch files and are not part of the repository.
- Inspection evidence (kept): Django 6.1.2 defaults read directly; the frontend never reads the CSRF cookie; 4 django_session rows, 0 expired (read-only count).
- Not verified: production HTTPS, proxy and HSTS behavior, a real installed clearsessions schedule, and an interactive run against the real backend with the new middleware (the owner's development server reloads the code; existing signed-in sessions end once).

Human Approval: ☒ Approved by: Ronald C. Arias  Date: 11/17/2026

Next flow: WF-02.01. Do not start until Approved is ticked.

### WF-02  Account Management

#### WF-02.01 — View pending applications

| Field | Definition |
| --- | --- |
| Actor / required permission | School Admin (Normal Administrator): an approved, active account holding an active Admin role assignment and the exact effective permission accounts.registration_requests.read (Admin role grant, not overridden by an account Deny, on the active accounts service). Technical Super Admin (Super Administrator) inherits it only through effective permissions: the v2 contract requires such accounts to hold both Admin and Technical Super Admin, and the Technical Super Admin role itself has no registration binding. Role names, requested roles, Django is_staff/is_superuser and UI hints never authorize. |
| Trigger | An authorized reviewer opens Dashboard → Registration review (/dashboard?view=registration-review), changes page, search, filter or sort, or selects Refresh list. |
| Preconditions | Valid Workspace session (WF-01.03, WF-01.06); accounts and access_control services active; the read-only list route mounted and its gate on (D-31; today the route is unmounted and requires both the review API gate and the approval gate). |
| Result | A read-only, paginated list of eligible Pending Student and Instructor applications showing only permitted fields (D-32), with the email-proof state of each (D-34). Nothing is changed, decided or sent. Unauthorized, expired, invalid and failed requests reveal no applicant data and no record counts. |
| Status | Owner-approved 17 November 2026 (P-01 to P-08; D-31 to D-36, D-34 and D-35 with clarifications). Implemented and tested: GET /api/v1/admin/registration-requests/ is the only review route in config.urls, read-only, behind WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED (backend) and VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED (frontend), both off by default. Approve and reject stay unmounted. Committed (bbbc8db), since pushed by the owner. Human Approval recorded by the owner (Ronald C. Arias, November 17,2026). |

**Inspection basis:** On 17 November 2026 the owner requested Inspect and Reconcile of WF-02.01 only (no implementation, no WF-02.02 to WF-02.04). Branch ronald at 51217b1, level with origin/ronald; working tree clean except the owner's untracked docs/SRS/CTU-G_Workspace_SRS_v0.4_UPDATED.md and docs/use_case_upecification/, which were preserved. WF-01.06 completion was verified from git, not catalogue text: commits 23f9b8e, f32a526 and 9a56fd9 are on origin/ronald, and 51217b1 (owner) contains the WF-01 Human Approval entries. Inspected read-only:
- Backend: accounts/models.py (Account, UserProfile), registration_staging.py (account creation after OTP), registration_review.py (decision service), registration_review_api.py (PendingRegistrationRequestsView, require_actor, ReviewBurstThrottle), registration_review_urls.py, session_auth.py (WorkspaceSessionAPI, SessionView), access_control/services.py (has_permission), catalogue c1_v1.json and v2_0.json (bindings, normal_admin and application_super_admin contracts), config/urls.py, config/review_local_urls.py, config/review_sandbox_urls.py and the review gate settings.
- Frontend: features/dashboard/navigation.ts and SessionDashboardPage.tsx; features/admin RegistrationReviewLivePanel.tsx, registrationReviewApi.ts, registrationReviewApiContract.ts, registrationReviewLiveViewModel.ts and the gate/config modules; docs/design PATTERNS.md §5–7 and frontend/AGENTS.md.
- Schema: docs/database/full_schema.dbml (accounts, users, roles, account_roles, role_permissions, account_permissions), accounts migrations 0001–0005 and access_control 0001–0003 (all applied), SHOW INDEX FROM accounts.
- Records: SRS v1 (UC-02, FR-REG-02, FR-AUTH-03, FR-ADM-06), Use Case Specification v0.4.1 (ACT-SA-01, UC-D03), D-09 and D-12.
- Read-only development database counts (no identities read): roles Student, Instructor, Treasurer and Admin (no Technical Super Admin role); services accounts and access_control active; the three accounts.registration_requests codes exist and are granted to Admin only; 0 account overrides on them; 3 Approved active accounts, 1 Rejected inactive account and 0 Pending accounts.
- Baseline tests: test_registration_review_api, _routing, test_registration_review, _p4_http_contract and _p3c_authenticated_boundary 74/74; frontend tests/registration-review-*.test.mjs 64/64.

**Reconciliation (requirement → evidence → finding):**
- R-01 Permission. Required: accounts.registration_requests.read. Actual: PendingRegistrationRequestsView calls require_actor(READ_CODE): session account, active Admin assignment, both services active, then has_permission (exact code, Deny wins, fails closed). Confirmed by code and tests (no assignment, Admin name without grant, account Deny, inactive service, revoked permission). No contract difference.
- R-02 Super Admin inheritance. Required: through effective permissions. Actual: consistent with the v2 application_super_admin contract (required roles Admin + Technical Super Admin); a Technical Super Admin account without the Admin role is refused. Confirmed by catalogue contract; not exercised end to end because no Technical Super Admin role exists (provisioning is WF-03.01). Test proposed with a test-only role.
- R-03 Pending only. Actual: request_status Pending, is_active false, not staff or superuser, requested role Student or Instructor and active, reviewed_by and reviewed_at null, no account_roles row, and not the reviewer. Confirmed by code; only status=Pending is accepted. Gap: Pending rows that fail these conditions are silently invisible (D-35).
- R-04 Fields. Actual: account_id, school_id, requested_role, created_at only; no email, hashes, tokens or session data. Gap: no applicant name, email-proof state or status label (D-32, D-34).
- R-05 Search, filter, sort. Actual: none on the server (unknown query fields return 400); the live panel filters School ID and role on the current page only. Gap: server-side search, filter and allowlisted sort (D-33).
- R-06 Pagination. Actual: fixed 20 per page, page 1–10000, order account_id; no total and no next-page indicator, so Next is enabled whenever a page has exactly 20 rows. Gap: has_next (D-33).
- R-07 Legacy without email proof. Actual: the list does not distinguish them; registration_review.py does not check proof (Appendix B finding). Development DB has 0 Pending rows, so impact today is nil. Gap: flag in the list (D-34); approval eligibility stays with WF-02.03 (D-09).
- R-08 Route and gates. Actual: registration_review_urls.py is included only by config/review_local_urls.py and review_sandbox_urls.py; config/urls.py does not mount it (test_registration_review_routing asserts this). The read view requires WORKSPACE_REGISTRATION_REVIEW_API_ENABLED and WORKSPACE_REGISTRATION_APPROVAL_ENABLED, so a read-only listing is tied to the decision gate. Frontend REGISTRATION_REVIEW_LIVE_API_ENABLED is false and REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT is null. Gap: a read-only mount and gate (D-31).
- R-09 Read-only boundary. Actual: RegistrationReviewLivePanel combines the list with Approve/Reject buttons and a confirmation dialog (WF-02.03/02.04). Gap: WF-02.01 needs a list without decision controls (P-05).
- R-10 Frontend authorization hints. Actual: mayShowReviewPanel requires roles.includes('Admin') as well as the read code. This conflicts with the frontend rule "show modules by exact permission code, never by role name" (AGENTS.md, PATTERNS §7). The backend role prerequisite remains (R-01). Correction in P-05.
- R-11 Unauthorized, expired session. Actual: 401 authentication_required triggers notifyAuthenticationRequired and the WF-01.06 "Your session has ended" view; 403 access_denied never signs out. Confirmed by code and WF-01.06 browser tests.
- R-12 Query validation. Actual: 400 invalid_request for unknown fields, non-decimal or out-of-range page and status other than Pending. Confirmed by test_minimal_pending_list_and_pagination_validation.
- R-13 Database failure. Actual: a DatabaseError inside the list falls through to WorkspaceSessionAPI's generic handler and returns 503 auth_unavailable, a code the review contract does not know (the UI shows its generic fallback). A failure during permission evaluation fails closed as 403 access_denied. Correction: map database errors to 503 review_unavailable (P-02).
- R-14 Throttle. Actual: ReviewBurstThrottle 20/min per REMOTE_ADDR, shared by list and decisions. Server-side search could exhaust it (D-36).
- R-15 Caching and headers. Actual: Cache-Control no-store and JSON-only renderer inherited from WorkspaceSessionAPI. Confirmed by test.
- R-16 Schema. The ERD and applied migrations already hold every needed column (accounts, users, roles, account_roles). accounts has indexes on PK, school_id (unique), email (unique), requested_role_id and reviewed_by, none on request_status or created_at. At a single-campus Pending queue size this needs no migration; a composite index would be a separate, separately approved ERD change only if measured volume requires it. No migration proposed.
- R-17 UI design. The panel follows PATTERNS §6 (table, muted dates, labelled filters, overflow-x-auto) and §5 states. Gaps: loading and empty states lack the aria-live pattern of §5.1; the decision dialog is out of scope; no name column.

**Implementation basis:** On 17 November 2026 the owner approved P-01 to P-08 and decided D-31 (mount only the read-only list behind an independent switch, off by default), D-32 (applicant name and email-verification state; no email address or sensitive registration data), D-33 (server-side search, filters and sort; 20 per page; stable oldest-first default; accurate next-page flag), D-34 (list eligible legacy Pending applications marked "No email proof on record"; missing proof is never verified or approval-eligible), D-35 (keep excluding anomalous rows, document the limitation and track count-only visibility as a follow-up; never hide valid Pending applications) and D-36 (separate 60-per-minute per-account listing limit). Additional owner conditions: reuse the existing services, evaluator, API patterns and components; no parallel access control; navigation follows the backend's effective-permission result, never role names; read-only; no tables, migrations or ERD changes; registration, authentication, session and CSRF behavior preserved; isolated test data only. Files changed:
- backend/apps/accounts/registration_review_api.py. PendingRegistrationRequestsView: own review_gate_open() (list gate, or the existing decision-gate pair used by the isolated review URLconfs); strict single-valued page, status, q, role, proof and sort; up to 5 search terms, each matching School ID prefix or any name part (ORM lookups, wildcards literal); proof annotation (email, email_verified_at and email_verified_address present and the address equal to the current email, case-insensitive); allowlisted sorts with account_id tie-breaker; 21-row look-ahead for has_next; select_related requested_role and profile (constant query count). New ReviewListThrottle (60/min keyed by the session account; address only for anonymous callers). RegistrationReviewAPI: gate check moved to review_gate_open(); DatabaseError now returns 503 review_unavailable for every review view (status code unchanged, error code corrected). Eligibility filter unchanged.
- backend/config/urls.py. Adds only path('api/v1/admin/registration-requests/', PendingRegistrationRequestsView.as_view()).
- backend/config/settings.py. WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED from the environment, "1" only; default off.
- frontend/src/features/admin/PendingApplicationsPanel.tsx (new). Read-only queue: search, role, email-proof and sort controls applied on submit or Enter (no request per keystroke), Refresh list, Previous/Next driven by has_next, table at 768px and wider, stacked cards below, fixed loading, empty, filtered-empty and error states, polite result announcement, footnote that missing proof is not eligibility. No decision controls.
- frontend/src/features/admin/pendingApplicationsConfig.ts (new). Frontend switch and the route root.
- frontend/src/features/admin/registrationReviewApiContract.ts. Query builder with validated q, role, proof and sort; parser requires has_next (true only with a full page), email_verified (boolean) and full_name (string or null) and still refuses every other field.
- frontend/src/features/admin/registrationReviewApi.ts. listPendingApplications(): refuses before any request while the list switch is off; GET only.
- frontend/src/features/admin/registrationReviewLiveViewModel.ts and RegistrationReviewLivePanel.tsx. mayShowReviewPanel now uses only the exact read permission and the gate (role argument removed); the unmounted decision panel uses has_next.
- frontend/src/features/dashboard/SessionDashboardPage.tsx and navigation.ts. The registration-review view renders the panel when the list switch is on; the navigation item stays permission-driven and loses its "Soon" label only then.
- Tests: backend/apps/accounts/test_wf0201_pending_list.py (new, 26 tests); backend/apps/access_control/test_wf0201_release_safeguard.py (new, 14 tests); test_registration_review_routing.py (+2); envelope assertions updated in test_registration_review_api.py and test_registration_review_p4_http_contract.py; frontend tests/registration-review-api-contract.test.mjs (+6), registration-review-live-ready.test.mjs and registration-review-p4-integration-contract.test.mjs (intentional contract updates); tests/browser/pending-applications-errors.test.mjs (new, 10 scenarios).
Protected-file correction (owner-authorized 17 November 2026, Option A): the first full regression after implementation had 134 failures (133 errors, 1 failure), all with one cause. The review release tooling treated any reversible route named registration-review-pending as "Registration Review already mounted" and refused P1 metadata initialization (init_registration_review_metadata_local_dev.py) and the P3C operational report (report_registration_review_operational_gate_p3c.py); test_review_sandbox_boundary.py asserted the name was unresolvable. The owner chose to narrow the safeguard rather than rename the route (which would silently sidestep it) or leave the list unmounted. The regression after that correction surfaced 2 further failures that had been hidden behind the setup errors (the recovery tests asserted no review route at all); the owner separately authorized correcting exactly those assertions. Changes, limited to the four authorized files plus a new test module:
- init_registration_review_metadata_local_dev.py: new unexpected_review_routes() walks every pattern of the active URLconf (including includes) and identifies registration-review routes by view class (any RegistrationReviewAPI subclass), view module, route name prefix or the registration-requests path marker. Exactly one entry is tolerated: route api/v1/admin/registration-requests/, name registration-review-pending, view class exactly PendingRegistrationRequestsView, http_method_names exactly get/head/options, no write handlers and no as_view() overrides. Approve, reject, bulk, a moved, renamed, unnamed, overridden or subclassed list, a second list mount, any unknown review route and an unreadable URLconf are all reported and refused. New refuse_unless_only_read_only_list() also refuses while WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED is on, so no review data can be read before the release, as before. P1's _target() calls it in place of the old reverse() check, keeping the original refusal message.
- report_registration_review_operational_gate_p3c.py: the same shared guard replaces its reverse() check (P3C already inherits P1's checks through P3A and P2; this remains a second layer). All other P1/P2/P3 gates, flags, catalogue, audit, scope and database checks are unchanged.
- test_review_sandbox_boundary.py: now asserts that config.urls mounts only the GET-only list, approve, reject and bulk names do not reverse, the guard accepts config.urls and refuses the sandbox URLconf, and the sandbox still mounts the full set.
- test_registration_review_activation_recovery_test_only.py: the three assertions that reverse("registration-review-pending") raises NoReverseMatch (after the activation exercise, after compensation, and in the no-activation-route test) now assert the narrowed contract: unexpected_review_routes() is empty and registration-review-approve, registration-review-reject and bulk-registration-review do not resolve. Activation and recovery behavior and all other assertions are unchanged.
- backend/apps/access_control/test_wf0201_release_safeguard.py (new, 14 tests): unit cases for allowed, decision, bulk, isolated, altered, duplicate, unknown and uninspectable URLconfs and the shared guard with both error classes; real P1, P2 and P3C commands on the disposable database passing with config.urls and refusing (no writes, no active service) for review_local or sandbox URLconfs, a reject route, unknown review routes and the list switch.
Deviations from the proposal text, all within the approved decisions: (1) the list also opens under the existing decision-gate pair so config.review_local_settings and the sandbox keep working; neither variable is read by config/settings.py, so in the regular application only the list switch opens it; (2) the throttle is keyed per account, as D-36 was approved, not per account and address; (3) the frontend switch is a Vite build variable rather than a hard-coded constant; (4) the search error uses existing dashboard tokens with a visible "!" marker, because --db-error is still Proposed in docs/design/TOKENS.md (gap reported, no token added).
Not changed: ERD, migrations, models, permissions and role grants, the eligibility filter, decision views and their gates, every other release-tooling command and governance check, registration, login, session and CSRF code, backend/.env and backend/.env.example, docs/design.

**Proposals (owner-approved and implemented 17 November 2026; text below is the approved specification):**
- P-01 Read-only route. Add to config/urls.py only path("api/v1/admin/registration-requests/", PendingRegistrationRequestsView.as_view(), name="registration-review-pending") — not include(registration_review_urls), so the approve and reject routes stay unmounted. Gate it with a new WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED setting (default False, read in config/settings.py from the environment as "1"); the list view checks this gate, and the decision views keep requiring the existing two gates (D-31).
- P-02 Backend view changes (backend/apps/accounts/registration_review_api.py). Split RegistrationReviewAPI.initial so the list checks the list gate and the decision views check the current pair. Accept only page, q, role, proof and sort (D-33); validate each strictly (ASCII-printable q of 1–50 characters after trim, role Student or Instructor, proof verified or legacy, sort submitted, -submitted, school_id or -school_id; duplicates and any other field return 400). Search: q matches school_id by case-insensitive prefix, and, if D-32 includes names, users.first_name or last_name by case-insensitive containment (ORM parameters only). Order: the chosen sort with account_id as a stable tie-breaker; default submitted, oldest first. Fetch 21 rows to return has_next without a total. Join users through select_related("profile") and requested_role in one query. Map DatabaseError and its subclasses to 503 review_unavailable. Keep the eligibility filter of R-03 unchanged.
- P-03 Response shape. Each item: account_id, school_id, requested_role, created_at, email_verified (boolean, D-34) and, if D-32 is approved, full_name (first, middle, last and suffix joined; null if absent). Envelope: results, page, page_size, has_next. No email address, password_hash, password_reset_token or its expiry, rejection_reason, reviewer fields, staff flags or session data.
- P-04 Throttle (D-36). Add a read scope workspace_review_read at 60/min keyed by account id and REMOTE_ADDR for the list; keep ReviewBurstThrottle at 20/min for decisions.
- P-05 Frontend read-only list. New features/admin/PendingApplicationsPanel.tsx for WF-02.01, reusing registrationReviewApi.listPendingRegistrationRequests, the contract parser and safeReviewError; no Approve, Reject or dialog. Server-side search box, role and email-proof filters and sort select submitted with an Apply button (Enter submits; no request per keystroke); Previous/Next using has_next; Refresh list. Columns: School ID, Name (if D-32), Requested role, Submitted (en-PH date with the full timestamp in a title or time element), Email proof (Verified, or "No email proof" as a muted badge) and Status ("Pending review"). States per PATTERNS §5: loading with role="status", empty ("No pending applications." / "No applications match these filters."), error with role="alert" and Try again, and the existing unavailable panel. Responsive: overflow-x-auto table at ≥768px; stacked definition cards at 360px. Works in Light, System-dark and Dark. Change mayShowReviewPanel to check only the read permission code and the gate (R-10). Contract (registrationReviewApiContract.ts): extend buildPendingReviewRequest with validated q, role, proof and sort, and parsePendingRegistrationPage with has_next, email_verified and optional full_name while still rejecting every other field. New gate constant REGISTRATION_REVIEW_LIST_ENABLED (false until release) and route root "/api/v1/admin/registration-requests/" in registrationReviewLiveConfig.ts; SessionDashboardPage renders PendingApplicationsPanel for view=registration-review when that gate is on; navigation item integration becomes 'shell'. RegistrationReviewLivePanel stays unmounted for WF-02.03/02.04.
- P-06 Backend tests (new backend/apps/accounts/test_wf0201_pending_list.py, config.test_settings): authorized Admin lists; Technical Super Admin with Admin listed, without Admin refused (test-only role); Student, Instructor, Treasurer, no-role, Pending, inactive, Rejected and Django-superuser actors refused; account Deny, inactive role, inactive service and revoked grant refused; anonymous 401; list gate off 503 while decision gates do not open the list and the list gate does not open decisions; only eligible Pending Student/Instructor rows (Approved, Rejected, active, staff, superuser, reviewed, role-assigned, inactive-requested-role and self rows excluded); requested-role filter; proof flag for verified, NULL proof, mismatched address and NULL email; search by School ID prefix and name, with % and _ treated literally; each sort and the tie-breaker; has_next at 0, 20 and 21 rows and page beyond the end; malformed inputs (unknown, duplicate, empty or 51-character q, non-ASCII, bad role, proof or sort, page 0, 10001, "1e3", "+1", " 1") all 400 with no data; exact response keys (no email, hashes, tokens, reviewer or session fields) and no-store; DatabaseError → 503 review_unavailable; throttle 429; HEAD and OPTIONS safe, POST 405; query count bounded (no N+1); routing: only the list path is mounted in config.urls, approve and reject remain unresolvable.
- P-07 Frontend tests: contract unit tests for the new query builder and parser (extra fields rejected, has_next required, bad q rejected); a view-model test that role names alone never show the panel; browser tests (tests/browser/pending-applications.test.mjs, mocked API) for authorized list, empty list, filtered empty list, search, filters and sort sending the right query, pagination with has_next, legacy badge, 401 → session-ended view, 403 → no sign-out and no data, 400 and 503 messages, no Approve/Reject controls, keyboard operation and focus order, 360/768/1024/1440 widths and the three themes.
- P-08 Regression before commit: all accounts and access_control test modules, npm test, npm run test:registration-ui, npm run build, npm run lint (changed files clean) and manage.py check; update test_registration_review_routing, registration-review-api-contract.test.mjs and registration-review-live-ready.test.mjs only where the approved contract intentionally changes them.
- Not proposed: migrations, ERD changes, new permissions or role grants, enabling the decision gates, email display, Approve/Reject/delete behavior, Django admin changes.

#### Main flow

1. The reviewer signs in (WF-01.03). The dashboard reads GET /api/v1/auth/session/ and shows Applicant reviews in navigation, under the Account operations group of the shared Dashboard Shell (docs/design Dashboard Shell v0.1), only if session.permissions (the backend's effective-permission result) contains accounts.registration_requests.read; role names are never consulted. With the frontend switch on, the item has no "Soon" label.
2. The reviewer opens Applicant reviews from the sidebar, or Open applicant reviews on the dashboard's Pending applications card (a link card without a count, D-33); /dashboard?view=registration-review loads with the breadcrumb Dashboard / Account operations / Applicant reviews and the page title Applicant reviews.
3. The frontend sends GET /api/v1/admin/registration-requests/?page=1&status=Pending (same-origin cookies, Accept JSON, no-store, 15-second timeout). It never sends a write and never retries automatically.
4. Django checks, in order: the list switch, the per-account rate limit (60/min), the Workspace session account, the active Admin assignment, both active services and the exact effective read permission (Deny wins); then validates every query field.
5. Django selects eligible Pending Student and Instructor accounts (R-03), applies the search, role and proof filters, orders by the chosen sort with account_id as tie-breaker (default oldest submission first), reads 21 rows and returns at most 20 with has_next. Each row has only account_id, school_id, full_name, requested_role, created_at and email_verified.
6. The frontend validates the response shape strictly (any extra field is refused) and shows School ID, name ("Not recorded" if none), requested role, submission date (full timestamp on hover), email-proof badge ("Email verified" or "No email proof on record") and status "Pending review": a table at 768px and wider, stacked cards below.
7. The reviewer enters a School ID (prefix) or name search, chooses role, email-proof filter or sort, and selects Apply filters or presses Enter; steps 3–6 repeat from page 1. Typing alone sends nothing.
8. The reviewer moves between pages with Previous and Next (Next only when has_next), selects Refresh list, or Clear filters. Nothing is changed by any step.

#### Alternative flows

- A1 No pending applications: "No pending applications." with a one-line explanation. With filters: "No applications match these filters." with Clear filters. A page beyond the end after paging: "No more applications."
- A2 Legacy application without email proof (no proof, proof for a different address, or no email): listed and marked "No email proof on record"; the footnote states this is not proof of eligibility (D-34). Approval eligibility is decided in WF-02.03 under D-09.
- A3 Technical Super Admin: listed the same way when the account holds Admin and the effective read permission; the Technical Super Admin role alone, or with a direct Grant, is refused 403.
- A4 Records change while viewing: a record approved or rejected elsewhere disappears on the next request; the list never claims to be live.
- A5 Anomalous Pending rows (missing or inactive requested role, staff or superuser flags, reviewer fields, an assigned role, or active): excluded by the eligibility filter and not shown; count-only visibility is follow-up FU-02.01-A (D-35).
- A6 Frontend switch off: the shared "This module is not available yet" state and the "Soon" navigation label; no request is sent. Backend switch off while the frontend switch is on: 503, see Errors.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| 3–4 | Not signed in, session expired (WF-01.06), or the session is not a Workspace identity (no active role, Pending or inactive account, Django staff or superuser) | 401 authentication_required; the dashboard shows "Your session has ended. Sign in again to continue." and drops applicant data |
| 4 | No Admin assignment, missing, inactive or denied permission, Technical Super Admin role alone | 403 access_denied; "You do not have permission to view applications." with no records, no Try again and no sign-out; nothing reveals whether applications exist |
| 4 | List switch off, or the accounts or access_control service inactive | 503 review_unavailable; "Pending applications are not available right now." with Try again |
| 4 | Unknown, repeated or malformed query value | 400 invalid_request; "The search or filters could not be used."; no data. Search text the server would refuse (over 50 characters, non-ASCII, more than 5 words) is refused in the browser first, with the message shown at the field and focus returned to it |
| 4–5 | Database failure | 503 review_unavailable without detail; same message as above; no partial list. A failure during permission evaluation fails closed as 403 |
| 4 | More than 60 list requests a minute from one account | 429 rate_limited; "Too many requests." with Try again |
| 3, 6 | Network failure, timeout or unexpected response shape (extra fields, leaked email, inconsistent has_next) | No data shown; "Applications could not be loaded." with Try again; never retried automatically |
| 3 | POST or another write method | 405 method_not_allowed (403 csrf_failed without a CSRF token); the view has no write handler |

#### Links

Depends on: WF-01.01 and WF-01.02 (create Pending accounts, profiles and email proof). WF-01.03 and WF-01.06 (session, expiry, CSRF bootstrap). WF-03 and the access_control evaluator (effective permissions, Deny precedence, service state). WF-03.01 (Technical Super Admin provisioning, for A3). The AR-6C registration-review release tooling (P1 to P3), whose route safeguard now tolerates only this read-only list (Option A). D-09, D-12, D-31 to D-36.

Feeds: WF-02.02 (open one application for review), WF-02.03 (approve), WF-02.04 (reject); each remains unmounted and separately gated. WF-12 (read events, if D-17 later requires them). FU-02.01-A (count-only anomaly visibility).

Traceability: SRS v1 UC-02 (precondition: reviewer sees eligible Pending applications), FR-REG-02, FR-AUTH-03, FR-ADM-06; Use Case Specification v0.4.1 ACT-SA-01 and UC-D03; ERD tables accounts, users, roles, account_roles, role_permissions, account_permissions (no change).

Guidelines: Inspect → Reconcile → Approve → Implement → Test → Commit

AI Agent Checklist: ☒ Inspected   ☒ Reconciled   ☒ Approved   ☒ Implemented   ☒ Tested   ☒ Committed

Checklist scope: Inspected and Reconciled cover the read-only inspection and R-01 to R-17 above. Approved records the owner's 17 November 2026 authorization of P-01 to P-08 with D-31 to D-36; it is not Human Approval. Implemented and Tested cover the files and results under Implementation basis and Evidence level. Committed: one owner-authorized local commit on ronald containing this entry, not pushed; only WF-02.01 files and this catalogue were staged.

Blocked by:
- No development implementation blocker for P-01 to P-08.
- Tracked follow-up FU-02.01-A (D-35): authorized, count-only visibility of Pending rows that fail the eligibility filter (missing or inactive requested role, staff or superuser flags, reviewer fields set, an assigned role, or is_active true). Until it exists such rows are not shown anywhere in the Workspace UI; the development database has 0. Valid Pending applications are never excluded.
- D-09 (whether legacy applications without email proof may be approved) stays OPEN and belongs to WF-02.03; WF-02.01 only displays the state.
- Activation: set WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=1 for Django and VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=1 for the Vite build. Production also needs the WF-01.06 production items (HTTPS, proxy, trusted origins) and governance approval of the Admin read grant in the target database.
- Design-system gap: the dashboard has no error-text token yet (--db-error is Proposed, AUDIT A-02); the search error therefore uses heading colour plus a "!" marker.
- Remaining, outside this flow: full frontend lint still reports the 2 pre-existing findings (ThemeToggle.tsx error, RegistrationReviewLivePanel.tsx exhaustive-deps warning, now at line 74).
- Observed outside this flow, not changed: the development database holds 1 Rejected inactive account although current rejection deletes the row (WF-02.04 retention review); the WF-01.06 entry still says its commits were not pushed, but origin/ronald contains them.
- Human Approval recorded by the owner (Ronald C. Arias, November 17,2026). WF-02.02 has since been implemented separately (D-37 adds a second, GET-only review route for the detail).

Evidence level: Code-verified and automated-test verified, 17 November 2026 (branch ronald, base 51217b1).
- New backend tests: test_wf0201_pending_list (26, real config.urls route, isolated MySQL test database): Admin lists with the exact envelope and no-store; Technical Super Admin lists only with Admin, and is refused with the Technical Super Admin role alone or with a direct Grant; Student (even with a direct Grant), Instructor and Treasurer refused 403; role-less, Pending Admin and Django superuser sessions refused 401; anonymous 401; account Deny, inactive grant and inactive service; expired session 401; list switch off 503; list switch never opens approve or reject; the existing decision pair still opens the list for the isolated configs; POST 405 (403 without CSRF), HEAD empty, OPTIONS without records; only eligible Pending Student/Instructor rows (approved, rejected, active, staff, superuser, reviewed_by, reviewed_at, role-assigned, null, Treasurer and inactive requested roles excluded); role filter; proof flag for matching, mixed-case, missing, mismatched and no-email cases and both proof filters; null name without a profile; School ID prefix and name-term search with literal % and _; all four sorts with the tie-breaker; has_next at 0, 20 and 21 rows and beyond the end; 23 malformed queries 400 with no data; 3 valid boundaries; no email, token, reason, hash or reviewer data in the body; DatabaseError 503 review_unavailable without detail; constant query count for 1 and 16 rows; per-account 429.
- Backend regression: all 65 accounts and access_control test modules 1587/1587 after the corrections (manage.py test, config.test_settings). History: the first full run after implementation had 134 failures from one cause (the release safeguard, see Protected-file correction); the run after narrowing it had 2 further failures in previously masked recovery assertions; after the authorized assertion update every module passes.
- Release-safeguard correction: test_wf0201_release_safeguard 14/14 and test_review_sandbox_boundary 6/6 after the change; the 134 earlier failures were re-run, not assumed fixed (see the regression line above).
- `manage.py check`: no issues. `makemigrations --check --dry-run`: no changes detected.
- Frontend (re-run after the safeguard correction): `npm test` 169/169 (6 new WF-02.01 contract and client tests). `npm run test:registration-ui` 73/73, including tests/browser/pending-applications-errors.test.mjs 10/10: read-only list content and no decision buttons; search, filters and sort sent only on Apply or Enter; non-ASCII search refused without a request and focused; empty and filtered-empty states with Clear filters; Previous/Next following has_next; 401 shows the WF-01.06 session-ended view and drops data; 403 shows no records and keeps the session; 400, 429, 503 and malformed responses (extra total, leaked email) show fixed messages, with Try again re-requesting once where offered; keyboard order and operation; 360, 768, 1024 and 1440px in Light, System-dark and Dark with no horizontal page scroll, table or cards as designed and every badge and muted or heading text at least 4.5:1. `npm run build` passed. `npm run lint`: changed files clean; the same 2 findings exist when linting the committed 51217b1 versions of those files, so none is new.
- Dev-server note: React StrictMode runs the first load twice in development (the first response is discarded); production sends one request.
- Not verified: an interactive run against a real Django server and real data (the development database has 0 Pending rows and real records were deliberately not created), Technical Super Admin with a provisioned role outside tests, production HTTPS and proxy behavior, and performance at volume.

Human Approval: ☒ Approved by: Ronald C. Arias  Date: November 17,2026

Next flow: WF-02.02. Do not start until Approved is ticked.

#### WF-02.02 — Verify and review applicant information

| Field | Definition |
| --- | --- |
| Actor / required permission | School Admin (Normal Administrator): an approved, active account with an active Admin role assignment and the exact effective permission accounts.registration_requests.read (catalogue: "Read Student/Instructor requests needed for school review; exclude privileged provisioning and secrets"). Technical Super Admin (Super Administrator) only through effective permissions: the v2 contract requires Admin + Technical Super Admin, and the Technical Super Admin role has no registration binding of its own. No role-name bypass; Django is_staff/is_superuser confer nothing. |
| Trigger | From Applicant reviews (WF-02.01) the reviewer selects one pending application; or opens its direct link. |
| Preconditions | Valid Workspace session (WF-01.03, WF-01.06); accounts and access_control services active; the read-only review switch on (D-37); the application still meets the WF-02.01 eligibility filter (Pending, inactive, unreviewed, not staff or superuser, Student or Instructor requested role active, no assigned role). |
| Result | A read-only view of one application: registered name, School ID (Student) or Staff ID (Instructor), email address (D-38), requested role, submission time, request status and the email-verification evidence, with a clear statement that enrollment (Student) or employment (Instructor) is not verified by Workspace. Nothing is changed, decided, sent or recorded (D-39, D-40). |
| Status | Owner-approved 17 November 2026 (P-01 to P-08; D-37 to D-43, including the protected-file authorization for D-41). Implemented and tested: GET /api/v1/admin/registration-requests/{id}/ (read-only, same read switch as WF-02.01, off by default) and the applicant-detail page inside Applicant reviews. Approve and reject stay unmounted. Committed locally on ronald (5e7a2c6). Human Approval recorded by the owner (Ronald C. Arias, November 17, 2026) after reviewing the finished implementation. |

**Inspection basis:** On 17 November 2026 the owner requested Inspect and Reconcile of WF-02.02 only (no implementation, no WF-02.03). Branch ronald at 94cc3b2 (bbbc8db WF-02.01, 8798e47 shell, 18ce71e and 94cc3b2 visual refinements), 4 commits ahead of origin/ronald. Working tree: the owner's uncommitted WF-02.01 Human Approval line in this catalogue, and untracked owner documents, all preserved. Inspected read-only:
- Backend: accounts/models.py (Account, UserProfile), registration_staging.py (fields persisted after OTP), serializers.py (RegistrationSerializer), registration_review.py (decision service), registration_review_api.py (WF-02.01 list view, require_actor, ReviewListThrottle), registration_review_urls.py, config/urls.py, access_control/services.py, the release safeguard in init_registration_review_metadata_local_dev.py, catalogue v2_0.json.
- Frontend: PendingApplicationsPanel.tsx, registrationReviewApi.ts, registrationReviewApiContract.ts, pendingApplicationsConfig.ts, the shared Dashboard Shell (navigation registry, PageHeader breadcrumbs, DashboardStates), RegisterPage.tsx (School ID / Staff ID labels).
- Schema: docs/database/full_schema.dbml (accounts, users, academic_profile), applied migrations accounts 0001–0005 and access_control 0001–0003.
- Records: SRS v1 and the owner's untracked SRS v0.4 draft (definitions of approved account and verified academic eligibility), Use Case Specification v0.4.1 (ACT-SA-02, UC-D03), D-09, D-12, D-17, D-31 to D-36.
- Read-only development database counts (no identities): 0 Pending accounts; 3 Approved active; 1 Rejected inactive; Admin holds the three registration codes.

**Reconciliation (requirement → evidence → finding):**
- R-01 Existing detail capability. No applicant-detail endpoint, view or component exists. The only registration-review route mounted in config.urls is the WF-02.01 GET list. The isolated registration_review_urls.py has the list plus POST approve and reject; no detail route. Verified.
- R-02 Data actually captured. RegistrationSerializer accepts only school_id (1–7 ASCII digits for both roles; the UI labels it Staff ID for Instructors), email, first_name, middle_name (optional), last_name, suffix (optional), requested_role, password and confirmation; Student-only fields such as course, year_level and section are refused. After OTP, registration_staging.py creates the account (school_id, email, password hash, requested_role, Pending, inactive, email_verified_at, email_verified_address) and the users profile (names). Nothing else about an applicant exists; academic_profile is a post-approval design table and not migrated. Verified.
- R-03 Fields WF-02.02 can show. Names (first, middle, last, suffix), School ID or Staff ID, email address (D-38), requested role, created_at, request_status, email_verified_at and whether email_verified_address equals the current email. Must never show: password_hash, password_reset_token and expiry, staging digests or OTP state, rejection_reason, reviewed_by/at, is_staff/is_superuser, session data. Verified against the model.
- R-04 Email-verification evidence. Four states are derivable without new data: verified (proof time present and the recorded address equals the current email, case-insensitive), no proof on record (legacy, email_verified_at NULL), proof for a different address (address changed after proof), and no email. Only the first is evidence of mailbox control; none is evidence of enrollment or employment. Verified (the WF-02.01 list already computes the first rule).
- R-05 Enrollment and employment. Not verifiable in Workspace: enrollment is CTU's main system (SRS definition "Verified academic eligibility"); instructor eligibility is School Admin review only (D-12). WF-02.02 must say so and must not show a general "Verified" status. Finding.
- R-06 Eligibility states. The decision service (registration_review.py) requires Pending, inactive, not staff or superuser, reviewed_by and reviewed_at NULL, requested role active Student or Instructor, no assigned role, and the reviewer is not the target; rejection also refuses a target with account-level permission history. The WF-02.01 list applies the same filter except the permission-history check. Applicants outside the filter (no longer Pending, role assigned, anomalous) are not reviewable and must answer 404 request_unavailable, identical to "does not exist" (non-enumerating). D-09 (approval eligibility of legacy applicants) stays OPEN for WF-02.03. Verified.
- R-07 Review recording side effects. Approve and reject set request_status, is_active, reviewed_by, reviewed_at and rejection_reason (approve also creates an account_roles row; reject deletes the account and profile). The WF-02.01 list excludes any account with reviewed_by or reviewed_at set, so populating those fields during WF-02.02 would make the applicant vanish from the queue while still Pending. WF-02.02 must not write any of them (D-39). Verified.
- R-08 Dependency on WF-02.03/02.04. The read path depends only on require_actor (session, Admin assignment, both services, exact read permission) and the eligibility filter; it does not call _decide, the writer boundary, the executor or the approval gate. A separately enabled, read-only WF-02.02 is possible. Verified.
- R-09 Access control. require_actor + has_permission give: session required, per-request effective permission, account Deny precedence, inactive role/account/service fail closed, no role-name bypass. Applicants themselves cannot sign in while Pending (WF-01.03), so applicant-to-applicant access is impossible. Verified by the WF-02.01 tests (26) and the evaluator suite.
- R-10 Transport and caching. WorkspaceSessionAPI responses are JSON with Cache-Control no-store; review errors use fixed codes; DatabaseError returns 503 review_unavailable (WF-02.01). Reusable. Verified.
- R-11 Rate limiting. ReviewListThrottle (60/min per account, D-36) is suitable for detail reads; sharing its bucket with the list keeps one read budget per reviewer. Recommendation.
- R-12 Release safeguard. The P1/P3C safeguard (owner-authorized Option A) tolerates exactly one review route: the GET list. A detail route under api/v1/admin/registration-requests/ would be refused as an unexpected review route, so mounting it requires a protected-file change to allow the exact GET-only detail route (D-41). Verified by reading unexpected_review_routes().
- R-13 UI. WF-02.01 rows have no selection control. The shell's breadcrumbs and h1 come from the navigation registry (view = registration-review), so a detail needs either an in-view sub-state or a shell extension for a fourth crumb. No modal component exists (AUDIT A-06), which argues against a modal or drawer. Verified.
- R-14 Audit of reads. The WF-02.01 list writes no read audit; authentication-event logging is D-17 (OPEN). Recording detail reads in access_audit_logs is possible without a migration but is a policy choice (D-40). Finding.

**Implementation basis:** On 17 November 2026 the owner approved P-01 to P-08 and D-37 to D-43: D-37 same read switch; D-38 full email in the authorized detail only; D-39 strictly read-only (never reviewed_by, reviewed_at, request_status, is_active, roles or registration data; opening a detail never removes an application from the queue); D-40 no application-level read audit until D-17; D-41 explicit authorization to modify the protected init_registration_review_metadata_local_dev.py and its associated safeguard tests so the safeguard recognizes exactly the two read routes; D-42 in-view detail page with breadcrumb and Back that preserves filters, sort and page; D-43 the four email-evidence wordings, never a bare "Verified", enrollment and employment stated as not verified by Workspace, D-09 preserved. Implementation started from 5ca1062 (owner commit after the inspection). Files changed:
- backend/apps/accounts/registration_review_api.py. New _read_gate_open() and _reviewable_pending(actor) shared by the list and the detail (the list's filter, results and behaviour are unchanged; its existing tests pass). New PendingRegistrationDetailView: GET/HEAD/OPTIONS only, ReviewListThrottle (one 60/min per-account budget with the list), require_actor(accounts.registration_requests.read), any query field 400, identifier 1–2147483647 else 404, the shared eligibility filter excluding the reviewer, select_related requested_role and profile; response keys account_id, school_id, id_label (School ID / Staff ID), name {first, middle, last, suffix}, full_name, email, requested_role, request_status "Pending", created_at, email_evidence {state, verified_at}, institutional_check {subject enrollment|employment, verified_by_workspace false}, data_notes. Unknown, ineligible and no-longer-Pending identifiers share one 404 request_unavailable. No database write and no logging of applicant data.
- backend/config/urls.py. Adds only path('api/v1/admin/registration-requests/<int:account_id>/', PendingRegistrationDetailView.as_view(), name='registration-review-detail').
- backend/apps/access_control/management/commands/init_registration_review_metadata_local_dev.py (protected; D-41). unexpected_review_routes() now tolerates exactly two read routes, each at most once, by exact path, name, view class, GET/HEAD/OPTIONS, no write handler and no as_view() overrides; the detail only alongside the list. Approve, reject, bulk, moved, renamed, re-typed (for example <str:account_id>), subclassed or swapped routes, duplicates, unknown review routes and unreadable URLconfs still refuse; the list-switch refusal and every other P1/P2/P3 check are unchanged. report_registration_review_operational_gate_p3c.py was not modified (it reuses the same helper).
- backend/apps/access_control/test_wf0201_release_safeguard.py (associated safeguard tests; 5 new, 19 total) and backend/apps/accounts/test_wf0202_applicant_detail.py (new, 19 tests).
- frontend/src/contexts/DashboardContext.ts, layouts/DashboardLayout.tsx, components/dashboard/DashboardShell.tsx, components/dashboard/PageHeader.tsx. Small shell extension: the context exposes the query string, openSubpage() (adds parameters to the current, already-permitted view) and an optional sub-page (fourth breadcrumb and description); leaving the view clears it.
- frontend/src/features/admin/registrationReviewApiContract.ts and registrationReviewApi.ts. parseApplicantId (digits only, 1–2147483647), buildApplicantDetailRequest, a strict parseApplicantDetail (exact keys, consistent role/label/subject and evidence/email pairs, any extra field refused) and getPendingApplication behind the same frontend read switch.
- frontend/src/features/admin/ApplicantDetailPanel.tsx (new) and PendingApplicationsPanel.tsx. A "Review application" link per row and card; ?applicant={id} renders the read-only detail in the same view, so filters, sort, page and loaded rows stay in memory; Back pops history when reached from the list (Forward keeps working) and returns focus to the opened link; three panels (Applicant information, Email verification evidence, Institutional eligibility); no decision or edit controls.
- Tests: frontend/tests/registration-review-api-contract.test.mjs (4 new), registration-review-p4-integration-contract.test.mjs (route lock updated from one to the two approved review paths, D-37), tests/browser/applicant-detail-errors.test.mjs (new, 8 scenarios).
Not changed: ERD, migrations, models, permissions and grants, the eligibility rules, the WF-02.01 list response (still no email), decision views and their gates, the P3C command, registration, login, session and CSRF code, approved copy, docs/design.

**Proposals (owner-approved and implemented 17 November 2026; text below is the approved specification):**
- P-01 Backend detail view. In backend/apps/accounts/registration_review_api.py add PendingRegistrationDetailView(RegistrationReviewAPI): GET/HEAD/OPTIONS only; review_gate_open() = the read switch (D-37); throttle ReviewListThrottle; require_actor(READ_CODE); reject any query string (400); account_id from the path (1–2147483647, else 404); fetch with the same eligibility filter as the list, extracted into one shared helper used by both views (no behaviour change for the list), excluding the actor; select_related requested_role and profile; not found or ineligible → 404 request_unavailable.
- P-02 Response (exact keys): account_id, school_id, id_label ("School ID" for Student, "Staff ID" for Instructor), name {first, middle, last, suffix} (strings or null), full_name, email (D-38), requested_role, request_status ("Pending"), created_at, email_evidence {state: verified | no_proof | address_changed | no_email, verified_at (only when verified)}, checks {enrollment: "not_verified_by_workspace" for Students, employment: "not_verified_by_workspace" for Instructors}, data_notes [codes such as missing_profile, missing_first_name, missing_last_name]. No other field.
- P-03 Route. backend/config/urls.py: path('api/v1/admin/registration-requests/<int:account_id>/', PendingRegistrationDetailView.as_view(), name='registration-review-detail'), GET-only; approve, reject and bulk stay unmounted.
- P-04 Release safeguard (protected, D-41). Extend unexpected_review_routes() in init_registration_review_metadata_local_dev.py so it tolerates exactly the detail route above (path, name, exact class, GET/HEAD/OPTIONS, no write handlers, no as_view overrides) in addition to the list, and still refuses everything else; update test_wf0201_release_safeguard.py, test_review_sandbox_boundary.py and the recovery-test assertions only where the allowlist contract changes.
- P-05 Frontend contract and client. registrationReviewApiContract.ts: buildApplicantDetailRequest(id) and a strict parseApplicantDetail (exact keys, enumerated evidence states, rejects any extra field such as password or token). registrationReviewApi.ts: getPendingApplication(id) behind the same frontend switch, GET only.
- P-06 Frontend UI (D-42). In PendingApplicationsPanel, each row and card gains a "Review application" link (keyboard reachable, accessible name includes the School ID or Staff ID) to /dashboard?view=registration-review&applicant={id}. A new ApplicantDetailPanel renders in the same view: "Back to pending applications" (restores the previous filters, sort and page from memory), a fourth breadcrumb with the applicant's ID (small shell extension), and three nearly solid panels: Applicant (names, ID with its role-specific label, requested role, submitted, status "Pending review"), Evidence ("Email ownership: verified by one-time code on {date}" or "No email proof on record" / "Email changed after verification" / "No email on file" — never a bare "Verified"), and What Workspace cannot verify ("Enrollment must be confirmed with CTU's main system" or "Employment must be confirmed through authorized institutional records"). No approve, reject or edit controls. States: loading, 404 "This application is no longer pending. It may have been processed.", 401 session ended, 403, 400, 429, 503, network. Responsive and keyboard accessible in the three themes.
- P-07 Tests (see Required tests in Evidence level).
- P-08 Regression before commit: all accounts and access_control modules, npm test, npm run test:registration-ui, build, lint, manage.py check, makemigrations --check.
- Not proposed: migrations, ERD changes, new permissions, writes of any kind, reviewed_by/reviewed_at changes, approve/reject/edit, enrollment management.

#### Main flow

1. The reviewer opens Applicant reviews (WF-02.01) and selects Review application on one row.
2. The frontend shows the application view (/dashboard?view=registration-review&applicant={id}) and sends GET /api/v1/admin/registration-requests/{id}/ (same-origin cookies, no-store, 15-second timeout).
3. Django checks the read switch, the per-account rate limit, the Workspace session, the Admin assignment, both active services and the exact effective read permission; validates the identifier.
4. Django loads the application only if it still meets the review eligibility filter and returns the permitted fields with the email-evidence state and the enrollment or employment notice.
5. The frontend validates the response strictly and shows the applicant, evidence and limits panels. No field is editable and no decision control exists.
6. The reviewer returns to Pending applications with the same filters, sort and page. Nothing has been recorded or changed.

#### Alternative flows

- A1 Legacy application without email proof: the evidence panel shows "No email proof on record" and states that this is not a verification; the application stays in the queue (D-34); approval eligibility is decided in WF-02.03 under D-09.
- A2 Email changed after verification, or no email on file: shown as such, never as verified.
- A3 Instructor applicant: the identifier is labelled Staff ID; the limits panel states that employment is not verified by Workspace (D-12).
- A4 Incomplete profile (missing name parts or profile row): shown as "Not recorded" with a data note; nothing is inferred.
- A5 Application processed or changed elsewhere (approved, rejected, deleted, role assigned): 404 request_unavailable; "This application is no longer pending." with Back to pending applications.
- A6 Technical Super Admin: same view, only through Admin and the effective read permission.
- A7 Read switch off: the module shows "Soon" and the not-available state; no request is sent.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| 2–3 | Not signed in, session expired, or not a Workspace identity | 401 authentication_required; the WF-01.06 session-ended screen; applicant data dropped |
| 3 | No Admin assignment, missing, inactive or denied permission | 403 access_denied; no data; no sign-out; nothing reveals whether the application exists |
| 3 | Read switch off, or a required service inactive | 503 review_unavailable; "Applications are not available right now." |
| 2–3 | Malformed identifier or any query field | The browser refuses a malformed applicant value without any request ("This application is no longer pending."); the server answers 404 for an out-of-range or non-numeric path and 400 invalid_request for query fields; no data |
| 4 | Not found, no longer Pending, or outside the eligibility filter | 404 request_unavailable (indistinguishable); "This application is no longer pending." |
| 3–4 | Database failure | 503 review_unavailable without detail; permission-evaluation failure fails closed as 403 |
| 3 | More than 60 review reads a minute from one account | 429 rate_limited; "Too many requests." |
| 2, 5 | Network failure or unexpected response shape | No data shown; "The application could not be loaded." with Try again; never retried automatically |
| 2 | POST or another write method | 405 (403 csrf_failed without a token); no write handler exists |

#### Links

Depends on: WF-01.01 and WF-01.02 (the captured fields and email proof), WF-01.03 and WF-01.06 (session, expiry, CSRF), WF-02.01 (queue, eligibility filter, read switch, throttle, shell entry point), WF-03 and the access_control evaluator, the AR-6C release safeguard (D-41), D-09, D-12, D-17.

Feeds: WF-02.03 (approve) and WF-02.04 (reject) — both stay unmounted and separately gated; WF-02.02 provides the information a reviewer needs before them but records nothing for them.

Traceability: Use Case Specification v0.4.1 ACT-SA-02 ("Validate email proof and Student/Instructor eligibility using approved evidence; OTP alone does not prove enrollment/employment") and UC-D03 step 1; SRS v1 UC-02 and FR-ADM-06; SRS v0.4 draft definitions of "Approved account" and "Verified academic eligibility"; ERD tables accounts, users, roles, account_roles (read only; no change).

Guidelines: Inspect → Reconcile → Approve → Implement → Test → Commit

AI Agent Checklist: ☒ Inspected   ☒ Reconciled   ☒ Approved   ☒ Implemented   ☒ Tested   ☒ Committed

Checklist scope: Inspected and Reconciled cover the read-only inspection and R-01 to R-14 above. Approved records the owner's 17 November 2026 authorization of P-01 to P-08 with D-37 to D-43 (including the D-41 protected-file authorization); it is not Human Approval. Implemented and Tested cover the files and results under Implementation basis and Evidence level. Committed: one owner-authorized local commit on ronald containing this entry, not pushed. Human Approval was recorded by the owner on November 17, 2026 after reviewing the finished implementation.

Blocked by:
- No development implementation blocker for P-01 to P-08.
- Human Approval recorded by the owner (Ronald C. Arias, November 17, 2026).
- D-09 (approval eligibility of legacy applicants) and D-12 (instructor eligibility source) stay OPEN for WF-02.03; WF-02.02 only displays evidence.
- Activation: the same switches as WF-02.01 (WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=1 for Django, VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=1 for the Vite build); production also needs the WF-01.06 production items and governance approval of the Admin read grant in the target database.
- Remaining, outside this flow: full frontend lint still reports the 2 pre-existing findings (ThemeToggle.tsx:17 error, RegistrationReviewLivePanel.tsx:74 warning). The development database holds 1 Rejected inactive account (WF-02.04 retention review). WF-02.03 is not started.

Evidence level: Code-verified and automated-test verified, 17 November 2026 (branch ronald, base 5ca1062).
- New backend tests: test_wf0202_applicant_detail (19, real config.urls routes, isolated MySQL test database): Student detail with exact keys and no-store; Instructor with Staff ID, employment and an empty middle name; all four evidence states plus a mixed-case match, and a null email; missing profile and blank name parts reported as data notes; Technical Super Admin allowed only with Admin (refused alone or with a direct Grant); Student (even with a direct Grant), Instructor and Treasurer 403; role-less and Django-superuser sessions and anonymous 401; account Deny, inactive grant, inactive Admin role and inactive service; expired session 401; switch off 503 while approve stays 503 and the detail's approve/reject sub-paths do not exist; POST 405 (403 without CSRF); 0, 999999, 2147483648 and 10^12 → the same 404 and non-numeric paths 404; the reviewer's own account 404; ten ineligible targets byte-identical to a missing one; approved and then deleted between list and detail → 404; query fields 400; three detail reads and HEADs make no INSERT/UPDATE/DELETE on accounts, users, account_roles, account_permissions or access_audit_logs, leave the row unchanged and keep the application in the WF-02.01 list; no token, reason, hash, session, reviewer or flag data in the body and still no email in the list; DatabaseError → 503 review_unavailable with the email in neither the body nor the logs; constant query count; the detail shares the per-account 60/min budget with the list (429, another account unaffected); the route resolves to the GET-only detail view.
- Release safeguard: test_wf0201_release_safeguard 19/19 (5 new: list + detail allowed, also through an include; detail without the list refused; moved, re-typed, renamed, unnamed, method-overridden, writable-subclass and swapped list/detail views refused; a second detail refused; approve, reject and bulk refused next to list and detail), plus the existing real P1/P2/P3C command tests passing with config.urls (now list + detail) and refusing otherwise. Sandbox, recovery and routing suites unchanged and passing.
- Backend regression: all 66 accounts and access_control test modules 1611/1611. `manage.py check`: no issues. `makemigrations --check --dry-run`: no changes detected.
- Frontend: `npm test` 176/176 (4 new WF-02.02 contract and client tests; the route-lock test updated to the two approved paths). `npm run test:registration-ui` 92/92, including tests/browser/applicant-detail-errors.test.mjs 8/8: opening from a row with the four-crumb breadcrumb, focus on the applicant heading, three panels and exact wording, never a bare "Verified", no approve/reject/activate/edit/delete/save controls and no write requests; Back restoring sort and page without refetching and returning focus to the opened link, browser Back/Forward and the breadcrumb link; each evidence state, the Staff ID label, employment notice and missing-name notes; 404, 403 (no sign-out), 503, 429 and a malformed response with a leaked field; 401 session-ended screen; malformed applicant values refused without a request; keyboard Enter on the Review link and Shift+Tab to Back; 360/768/1024/1440 px in Light, System-dark and Dark with no overflow and composited AA contrast for every text element. `npm run build` passed. `npm run lint`: the same 2 pre-existing findings, nothing new.
- Dev-server note: React StrictMode runs the first detail read twice in development (the first response is discarded); production sends one request.
- Not verified: an interactive run against real data (the development database has 0 Pending rows and real records were deliberately not created), Technical Super Admin with a provisioned role outside tests, and production deployment.

Human Approval: ☒ Approved by: Ronald C. Arias  Date: November 17, 2026

Next flow: WF-02.03. Do not start until Approved is ticked.

#### WF-02.03 — Approve applicant account

| Field | Definition |
| --- | --- |
| Actor / required permission | School Admin (Normal Administrator): an approved, active, non-staff, non-superuser account with an active Admin role assignment and the exact effective permission accounts.registration_requests.approve (catalogue v2: SCHOOL scope, bound to Admin only). Technical Super Admin (Super Administrator) only through effective permissions, that is while also holding Admin (v2 contract Admin + Technical Super Admin); the Technical Super Admin role has no registration binding of its own. No role-name bypass; Django is_staff/is_superuser confer nothing; requested_role never authorizes. |
| Trigger | From the WF-02.02 applicant detail, a reviewer who has completed the required checks selects Approve application and confirms. |
| Preconditions | Valid Workspace session and CSRF token (WF-01.03, WF-01.06); accounts and access_control services active and the Admin approve grant active; approval reachable only in an approved release mode (D-46); the application still eligible (Pending, inactive, not staff or superuser, reviewed_by and reviewed_at empty, requested role active Student or Instructor, no assigned role, not the reviewer); email ownership verified (D-44); institutional eligibility confirmed by the reviewer (D-45). |
| Result | In one transaction: request_status Approved, is_active true, reviewed_by and reviewed_at set, rejection_reason cleared, exactly one account_roles row for the requested base role (assigned_by the reviewer), and one access_audit_logs record (account.registration.approve) with before/after state and the reviewer's eligibility attestation (D-45). The application leaves the WF-02.01 queue and its WF-02.02 page reports it as no longer pending. Any notification is sent only after commit and never decides the approval (D-49). |
| Status | Owner-approved 17 November 2026 (P-01 to P-09; D-44 to D-51; the narrow audit-contract authorization D-52; the bulk decision D-53). Implemented and tested 18 November 2026: verified email (D-44) and the reviewer's attestation (D-45) are enforced in the locked transaction and recorded in the existing approval audit; the approve body is the attestation only; policy refusals are 409; the WF-02.02 detail has an approval section with an accessible confirmation dialog behind its own build switch (off by default). Approval stays reachable only in the loopback local review mode and the sandbox (D-46); config.urls, the release safeguard, P1–P4, the executor and the writer boundary are unchanged. Committed locally on ronald (b974087), not pushed. Human Approval recorded by the owner (Ronald C. Arias, November 18, 2026) after reviewing the finished implementation, with the ninth bulk-test change and the WF-02.03-only baseline lint exception accepted. |

**Inspection basis:** On 17 November 2026 the owner requested Inspect and Reconcile of WF-02.03 only (no implementation, no WF-02.04). Branch ronald at fa525a1 (5e7a2c6 WF-02.02, fa525a1 its Human Approval), 2 commits ahead of origin/ronald, working tree clean. Prerequisites verified: WF-02.01 and WF-02.02 Human Approvals recorded (Ronald C. Arias, November 17, 2026). Inspected read-only:
- Backend: accounts/registration_review.py (_decide, approve_registration), registration_review_api.py (ApproveRegistrationRequestView, require_actor, ReviewBurstThrottle, error mapping), registration_review_urls.py, config/urls.py, config/review_local_settings.py and review_local_urls.py, config/review_sandbox_*.py, registration_notifications.py, registration_outbox.py, outbox_models.py, outbox_worker.py and process_registration_outbox, access_control/services.py, audit.py, writer_boundary.py, executor/client.py, engine.py and protocol.py, and every registration-review release command (P1 metadata, P2 inactive bindings, P3A readiness, P3B recovery test-only, P3C operational gate, P3D transition candidate, P3E release gates, P4 local release).
- Frontend: ApplicantDetailPanel.tsx, PendingApplicationsPanel.tsx, RegistrationReviewLivePanel.tsx, registrationReviewApi.ts (approveRegistrationRequest), registrationReviewApiGate.ts, registrationReviewLiveConfig.ts, components/common/Modal.tsx (empty), the Dashboard Shell.
- Schema: docs/database/full_schema.dbml (accounts, account_roles, role_permissions, access_audit_logs, registration_notification_outbox); applied migrations accounts 0001–0005, access_control 0001–0003.
- Records: SRS v1 and v0.4 draft (UC-02, AT-02, FR-ADM), Use Case Specification v0.4.1 (UC-D03, ACT-SA-03), D-09, D-12, D-17, D-19, D-34, D-37 to D-43; catalogue v2 bindings.
- Read-only development database counts (no identities): 0 Pending accounts; services accounts and access_control active; Admin holds 3 active registration grants; Student and Instructor roles hold 0 active grants; audit receipts show P1 (2 service + 3 permission creates), P2 (3 binding stages), the P4 local activation (2 service + 3 binding activates), 1 bootstrap and 1 past rejection.

**Reconciliation (requirement → evidence → finding):**
- R-01 Existing approval. approve_registration() → _decide(approve=True) is implemented and tested (test_registration_review 17, test_registration_review_api 20, p4 HTTP contract 12, notifications 7, protected executor 29). ApproveRegistrationRequestView (POST, empty JSON body, CSRF, require_actor(approve), 20/min per-address throttle, 404 request_unavailable for stale or ineligible, 503 review_unavailable) is mounted only by registration_review_urls.py, which config.urls never includes; it is reachable only through config.review_local_settings (loopback-only, CTUG_REVIEW_LOCAL_ACK, local ctug_workspace, both gates on, email off) and the synthetic sandbox. Verified: deliberately unmounted, not missing.
- R-02 Gates. The service requires WORKSPACE_REGISTRATION_APPROVAL_ENABLED; the API also requires WORKSPACE_REGISTRATION_REVIEW_API_ENABLED. Neither is read from the environment in config/settings.py (default off); only the isolated settings set them. Verified.
- R-03 Protected writer and executor. With WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER on, _decide forwards registration.approve over mTLS to the separately authenticated executor (restricted grants and writer-lease triggers); with it off (development) the legacy local path writes. writer_boundary.RELEASE_STATUS is BLOCKED: no production path is released. Verified.
- R-04 Transaction and locking. One writer_atomic transaction on primary MySQL READ COMMITTED locks, in ID order: the access_control and accounts service rows, the exact permission row, the reviewer and target accounts, both accounts' account_roles, the roles, the reviewer's role_permissions and account_permissions; then re-evaluates has_permission inside the lock. A concurrent approve, reject, deactivation, role change or permission revocation therefore serializes and the loser is refused. Verified by code; no two-connection concurrency test exists for review decisions (gap).
- R-05 Eligibility enforced today. Reviewer: active, Approved, not staff or superuser, Admin assignment active, exact effective approve permission, not the target. Target: Pending, inactive, not staff or superuser, reviewed_by and reviewed_at empty, requested role active Student or Instructor, no assigned role. Verified.
- R-06 Not enforced today. No email-proof check (D-09 gap; Appendix B "School Admin review lacks OTP-proof check") and no institutional-eligibility check or record (D-12). Verified.
- R-07 State written. request_status Approved, is_active true, reviewed_by, reviewed_at, rejection_reason None; account_roles row for the requested role with assigned_by; audit account.registration.approve with old {account_id, Pending, inactive} and new {account_id, Approved, active, role_id}, reason account_status_change. Verified.
- R-08 Duplicate and retry. A second approval of the same application is refused (reviewed fields set) and answers 404 request_unavailable, not success; the existing live panel already treats an ambiguous POST as "refresh to confirm" and never retries. Verified.
- R-09 Effective access after approval. The approved user can sign in (an active role assignment exists), but Student and Instructor roles hold no active grants in the development database, so no module appears. SRS AT-02 "default access available after login" therefore depends on base-role defaults (WF-03 / catalogue v2), outside WF-02.03 (D-50). Verified.
- R-10 Student eligibility. Captured: School ID (1–7 digits), names, email and proof, requested role. Enrollment is not in Workspace (CTU's main system is authoritative; academic_profile is a post-approval design table). No enrollment integration exists; only authorized manual confirmation by the reviewer is possible. Finding.
- R-11 Instructor eligibility. Captured: Staff ID (same 1–7 digit rule), names, email and proof. D-12: School Admin review only; OTP proves mailbox control, not employment. No HR source exists and none may be invented. Opening the WF-02.02 page is not a verification. Finding.
- R-12 Notifications. Two existing paths, both after commit and both unable to undo an approval: best-effort email (WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED, not read from the environment) and the durable encrypted outbox (WORKSPACE_REGISTRATION_OUTBOX_ENABLED, one row per decision audit, at-least-once worker with leases and retry state, delivery_status auditable). The SRS requires notification for rejection (UC-03) but not for approval; UC-D03 lists it as a proposed step. config.review_local_settings forces all email off. Verified.
- R-13 Release safeguard. The P1/P3C safeguard (D-41) refuses any approve route; P3A/P3C/P3E/P4 inspect activation state; P3D keeps a hard-coded local write barrier. Mounting approve in config.urls would make the pre-release tooling refuse by design. Verified.
- R-14 Frontend. RegistrationReviewLivePanel has approve/reject buttons and an inline role="dialog" section without focus trap, Escape or scrim (AUDIT A-06), behind REGISTRATION_REVIEW_LIVE_API_ENABLED (false) with a null route root; components/common/Modal.tsx is empty. The WF-02.02 detail has no decision controls. Verified.
- R-15 Configuration note. config.review_local_settings sets CSRF_COOKIE_HTTPONLY = False, which differs from WF-01.06 D-29 (HttpOnly CSRF cookie) in local review mode only; the frontend reads the token from the /csrf/ body either way. Finding, not changed.
- R-16 Catalogue numbering. Announcements & Notifications is WF-09 and Audit, Security & Monitoring is WF-12 in this catalogue (the request referred to WF-08 and WF-11). Finding.

**Implementation basis:** On 17 November 2026 the owner authorized P-01 to P-09 and D-44 to D-51 (Implement → Test → Commit) with these conditions: verified email for the current address, enforced in the backend transaction (D-44); a reviewer attestation with the fixed source for the role, recorded in the existing approval audit JSON, never claiming that Workspace verified enrollment or employment, and with no personal data, documents or free text (D-45); approval only in the local review mode and the sandbox, never mounted in config.urls, production disabled (D-46); 409 for policy refusals, 404 for stale targets (D-47); an accessible dialog with focus management, Escape, focus return and no duplicate submit, never auto-replaying an uncertain result (D-48); the outbox only when enabled, after commit, without duplicates and with no production email (D-49); Student and Instructor permission seeding deferred to WF-03, with SRS AT-02 recorded as UNMET (D-50); approval refused while the protected writer is enabled (D-51). During implementation the owner also authorized a narrow change to the protected audit writer for the approval event only (D-52) and decided that bulk approval must follow D-44/D-45, fail closed and stay unmounted, with its tests adjusted as proposed (D-53). Implementation started from fa525a1. Files changed:
- backend/apps/accounts/registration_review.py (governance-sensitive). ELIGIBILITY_SOURCES (Student: ctu_main_system_records; Instructor: institutional_employment_records) and ELIGIBILITY_SUBJECTS; RegistrationApprovalNotAllowed(reason) with reasons email_unverified and eligibility_unconfirmed, a subclass of RegistrationReviewDenied so callers that only know denials (the bulk service, the executor engine) fail closed; email_ownership_verified() (email present, email_verified_at present, proof address equal to the email case-insensitively, the WF-02.01/02.02 rule). approve_registration(actor, target_id, attestation) requires exactly {"confirmed": True, "source": <str>}. Before any transaction: D-51 refuses approval with WriterBoundaryUnavailable while the protected writer is enabled (the executor protocol cannot carry the attestation; rejection unchanged). Inside the locked transaction, after the existing reviewer, permission and target checks: unverified email → email_unverified, a source other than the one for the requested role → eligibility_unconfirmed; nothing is written before these checks. The approval audit new_value adds four flat, server-derived fields: email_evidence "verified", eligibility_confirmed true, eligibility_subject (enrollment or employment) and eligibility_source. The reviewer is the audit actor, the applicant its target and created_at the attestation time; no email, ID, name or free text is recorded.
- backend/apps/accounts/registration_review_api.py. ApproveRegistrationRequestView checks the session, Admin assignment and exact approve permission first, then accepts exactly {"eligibility_confirmed": <bool>, "eligibility_source": <one of the two sources>} (anything else 400) and passes it to the service. handle_exception maps RegistrationApprovalNotAllowed to 409 {"error": {"code": "approval_not_allowed", "reason": <fixed>, "message": "Approval is not allowed for this application."}} before the generic 404 mapping.
- backend/apps/access_control/audit.py (protected; D-52, owner-authorized narrow change). Only the account.registration.approve event's new_value may, and must, carry the four attestation fields, with fixed values, the consistent pairs enrollment ↔ ctu_main_system_records and employment ↔ institutional_employment_records, and an applicant target; they are rejected in every other event and in any old_value. No other field, event or validation rule changed; append-only and fail-closed behaviour (rollback-only on any failure) are unchanged.
- Tests adjusted to the new policy without loosening assertions: test_registration_review, test_registration_review_api, test_registration_review_notifications, test_registration_outbox, test_registration_review_p3c_authenticated_boundary and test_registration_review_p4_http_contract (approval fixtures now have verified email proof and pass the role's attestation; three tests whose purpose is the missing or invalid recipient path now reach it through a rejection, which needs no email proof); test_registration_bulk (D-53: one new test that bulk approval approves nothing, even for verified applicants, and accepts no attestation fields; the seven other approval-dependent tests switched to rejection with equivalent assertions); test_task1_reapplication (its bulk-approval v2-template test now asserts that bulk approval is refused with no outbox row, and checks the v2 approval template through the single attested approval; the same D-53 pattern, applied to a ninth test found in the full regression; accepted by the owner on 18 November 2026 after inspection confirmed the owner's conditions: bulk approval without the D-45 attestation is refused (0 Approved, 2 Skipped, no outbox row, which the approval writes in the same transaction as its audit), the service refuses before any transaction so no activation, role or approval audit can result (asserted directly by test_registration_bulk), the v2 approval template is still tested through two valid single approvals and is now also required to produce exactly 2 messages, only the reversed bulk-success count was removed, and no other test in the file changed). registration_bulk.py is unchanged.
- New backend tests: backend/apps/access_control/test_audit_approval_attestation.py (9) and backend/apps/accounts/test_wf0203_approval.py (32).
- frontend/src/components/common/Modal.tsx (was empty; COMPONENTS §6, D-48): native dialog opened with showModal() (inert background, top layer), Escape and Cancel close unless a request is in flight, focus to the first control (Cancel) and back to the trigger, scrim from --db-scrim, 200 ms enter with a reduced-motion fade.
- frontend/src/css/dashboard.css: the documented success, error and warning feedback tokens (TOKENS §1.4) and blocks, and .dashboard-dialog. docs/design/TOKENS.md, COMPONENTS.md and AUDIT.md (A-06 partly fixed) updated as the frontend rules require.
- frontend/src/features/admin/pendingApplicationsConfig.ts: APPLICANT_APPROVAL_ENABLED (VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED=1; default off). registrationReviewApiContract.ts: ELIGIBILITY_SOURCE_FOR_ROLE, labels, buildApprovalRequest (attestation only, never a role) and parseApprovalRefusal. registrationReviewApi.ts: approveApplication(), switch checked first, one CSRF-protected POST, never retried; definite refusals keep their codes; no response after sending, other 5xx or a reply that is not exactly {account_id, status: "Approved"} become outcome_unknown.
- frontend/src/features/admin/ApplicantApprovalPanel.tsx (new) inside ApplicantDetailPanel.tsx, shown only with the switch and the exact approve permission: a "Before you approve" checklist (email evidence; eligibility confirmed by the reviewer, not by Workspace); when the email is not verified, a statement that the application cannot be approved and no form; otherwise the requested role read-only, a required source select offering only the role's fixed source, a required confirmation checkbox, validation on submit with focus on the first problem, the Confirm approval? dialog, an "Application approved" result view (focused) that says access depends on the role's permissions, fixed messages for 409, 404 (the detail's no-longer-pending state), 401, 403, 429, 503 and invalid requests, and an uncertain-result state that pauses approval until the application is reloaded. No reject control. PendingApplicationsPanel.tsx reloads the list (GET) after a decision.
- New frontend tests: tests/registration-review-approval.test.mjs (11) and tests/browser/applicant-approval-errors.test.mjs (8).
Not changed: config.urls, the release safeguard and P1–P4 commands, writer_boundary.py, the executor client, protocol and engine, registration_bulk.py, models, migrations, the ERD, permissions and grants, base-role defaults, rejection behaviour (WF-02.04), real applicant data, approved WF-01/WF-02.01/02.02 copy.

**Proposals (owner-approved 17 November 2026 and implemented; text below is the approved specification):**
- P-01 Approval policy in the service (backend/apps/accounts/registration_review.py, governance-sensitive). Inside the existing locked transaction, after the current target checks: refuse unless the email-evidence state is verified (D-44, same rule as WF-02.01/02.02: email present, email_verified_at present, email_verified_address equal to the email case-insensitively); require an eligibility attestation argument {confirmed: true, source: one fixed enum value valid for the requested role} (D-45) and record it in the existing audit new_value; raise a new RegistrationApprovalNotAllowed(reason_code) for policy refusals. No schema change.
- P-02 API (backend/apps/accounts/registration_review_api.py). ApproveRegistrationRequestView accepts exactly {"eligibility_confirmed": true, "eligibility_source": "<enum>"}; policy refusals return 409 approval_not_allowed with a fixed reason (email_unverified, eligibility_unconfirmed); stale or ineligible stays 404 request_unavailable; everything else unchanged (CSRF, require_actor(approve), throttle, gates).
- P-03 Reachability (D-46). Keep the approve route out of config.urls and keep the release safeguard unchanged; approval is usable only in the existing loopback local review mode and the sandbox; production stays the separate protected executor release.
- P-04 Executor parity (D-51). The executor protocol carries actor_id, target_id and rejection_code only; while the attestation is not part of it, refuse approval when the protected writer is enabled rather than approve without the attestation. A protocol/engine change is a separate protected-file decision.
- P-05 Frontend contract and client. approveRegistrationRequest(id, attestation) with the new body; parse 200, 404, 409 reasons and errors strictly; a separate build switch VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED (default off) and the existing route root; never retried.
- P-06 Frontend UI (D-48). An Approval panel on the WF-02.02 detail, shown only with the approve permission hint and the switch: readiness checklist (email evidence must be "Email ownership verified"; institutional confirmation with a role-specific source select and a required confirmation checkbox; the role that will be assigned, read-only), missing requirements listed, Approve application disabled with the reason until ready; an accessible confirmation dialog stating that the account is activated, the requested role assigned and the action audited; on success a result view ("Application approved") with Return to pending applications; stale (404) "This application was already processed or changed. Return to the list to see its current state."; 409 reasons; 401/403/429/503; network uncertainty "The result could not be confirmed. Check the pending list before trying again." No reject, edit or activate controls.
- P-07 Notification (D-49). Reuse the durable outbox only when it is enabled and configured; otherwise no approval email; an approval stays valid if delivery fails; no new service; no live email in tests.
- P-08 Tests (see Evidence level) and P-09 regression.
- Not proposed: migrations, ERD changes, new permission codes, changes to base-role defaults (D-50), rejection behaviour (WF-02.04), enrollment management, an HR integration, mounting decision routes in config.urls, or relaxing any release safeguard.

#### Main flow

1. The reviewer opens an application in WF-02.02 and reads the applicant, email evidence and institutional eligibility panels.
2. In the Approval panel the reviewer confirms institutional eligibility through an authorized source (Student: CTU's main system records; Instructor: institutional employment or appointment records) and selects that source; the panel shows the role that will be assigned.
3. With the email evidence verified and the confirmation complete, the reviewer selects Approve application; an accessible dialog states the consequences and the reviewer confirms.
4. The frontend fetches a fresh CSRF token and sends one POST /api/v1/admin/registration-requests/{id}/approve/ with the attestation; it never retries.
5. Django checks the gates, the session, CSRF, the Admin assignment, both services and the exact approve permission; validates the body; then, in one locked transaction, re-checks the reviewer and the target, the email evidence and the attestation.
6. Django sets Approved and active, records the reviewer and time, assigns exactly the requested base role, writes the audit record with the attestation, and commits; any notification is queued after commit.
7. The frontend shows "Application approved" only after the 200 response and returns the reviewer to Pending applications, where the application no longer appears.

#### Alternative flows

- A1 Email not verified (no proof, address changed, no email): the approval section states that the application cannot be approved and shows no form; a forged request is refused 409 email_unverified (D-44). The application stays Pending.
- A2 Institutional eligibility not confirmed: Approve application shows the missing source or confirmation and focuses it, and no dialog opens; a forged request with a false or wrong-role attestation is refused 409 eligibility_unconfirmed, and a malformed or missing one 400.
- A3 Processed or changed elsewhere (approved, rejected, deactivated, role assigned): 404 request_unavailable; the reviewer is told to return to the list.
- A4 Two reviewers approve at the same time: the row locks serialize them; one succeeds, the other receives 404.
- A5 Reviewer loses the approve permission (Deny, revoked grant, inactive role or service): before the request 403 (or 503 for an inactive service); during the request the locked re-check refuses with 404; nothing changes.
- A6 Notification delivery fails: the approval stands; the outbox records the failure and retries if enabled (D-49).
- A7 Approval not released in this mode (normal config.urls) or the frontend switch off: no Approve control; the read-only WF-02.02 page is unchanged.
- A8 Protected writer enabled without attestation support in the executor: refused 503 review_unavailable (D-51).

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| 4–5 | Session expired or not a Workspace identity | 401 authentication_required; WF-01.06 session-ended screen; nothing changed |
| 4–5 | Missing or invalid CSRF token, or untrusted Origin | 403 csrf_failed before any parsing; nothing changed; "Refresh security check" |
| 5 | No Admin assignment, missing, inactive or denied approve permission (pre-check) | 403 access_denied; nothing changed |
| 5 | Self-approval, or the reviewer loses eligibility or the permission between the pre-check and the locked re-check | Refused inside the transaction; the existing mapping answers 404 request_unavailable; nothing changed |
| 5 | Gates off, services inactive, writer boundary or executor unavailable | 503 review_unavailable; nothing changed |
| 5 | Body not exactly the attestation object, unknown source | 400 invalid_request; nothing changed |
| 5 | Email evidence not verified, attestation missing or not allowed for the role | 409 approval_not_allowed with a fixed reason; nothing changed |
| 5 | Application not found, no longer Pending or otherwise ineligible | 404 request_unavailable (non-enumerating); nothing changed |
| 6 | Audit, role assignment or outbox insert fails | Whole transaction rolls back; 503 review_unavailable; nothing changed |
| 4, 7 | Network failure or timeout after sending, another 5xx, or an unexpected reply | "We could not confirm whether the application was approved. Do not approve it again yet. Reload the application to check its current status first."; approval pauses until the application is reloaded; never retried automatically |
| 5 | More than 20 decisions a minute from one address | 429 rate_limited |

#### Links

Depends on: WF-01.01 and WF-01.02 (captured fields and email proof), WF-01.03 and WF-01.06 (session, CSRF), WF-02.01 (queue), WF-02.02 (applicant detail and evidence wording), WF-03 (effective permissions; base-role defaults for AT-02, D-50), the protected writer/executor and the AR-6C release sequence (P1–P4), D-09, D-12, D-17, D-19.

Feeds: WF-01.03 (the approved account can sign in), WF-04 (profile of the approved user), WF-09 (approval notification, if D-49 enables it), WF-12 (audit review of account.registration.approve).

Traceability: SRS v1 and v0.4 UC-02 and AT-02; FR-AUTH-03; Use Case Specification v0.4.1 ACT-SA-03 and UC-D03 (including "Unverified legacy Pending account … refuse"); ERD tables accounts, account_roles, access_audit_logs, registration_notification_outbox (no change).

Guidelines: Inspect → Reconcile → Approve → Implement → Test → Commit

AI Agent Checklist: ☒ Inspected   ☒ Reconciled   ☒ Approved   ☒ Implemented   ☒ Tested   ☒ Committed

Checklist scope: Inspected and Reconciled cover the read-only inspection and R-01 to R-16 above. Approved records the owner's 17 November 2026 authorization of P-01 to P-09 with D-44 to D-51, the D-52 audit-writer authorization and the D-53 bulk decision; it is not Human Approval. Implemented and Tested cover the files and results under Implementation basis and Evidence level. Committed: one local commit on ronald containing only the WF-02.03 work and this entry, not pushed. Human Approval was recorded by the owner (Ronald C. Arias) on November 18, 2026 after reviewing the finished implementation; the owner confirmed making that entry.

Blocked by:
- Human Approval recorded by the owner (Ronald C. Arias, November 18, 2026). It does not release production approval or close D-50.
- Production approval: still blocked. config.urls has no approve route (D-46), writer_boundary RELEASE_STATUS stays BLOCKED, and D-51 refuses approval whenever the protected writer is enabled because the executor protocol (actor_id, target_id, rejection_code) cannot carry the attestation. Production approval needs a separately authorized executor protocol and engine change.
- SRS AT-02 "default access available after login": UNMET, not passed (D-50). An approved Student or Instructor can sign in with the requested role, but those roles hold no active grants, so no module appears until WF-03 seeds base-role permissions.
- Bulk approval: a separate future workflow (D-53). The unmounted test-only bulk service refuses every approval item until it can carry a per-applicant attestation.
- Known effects of the policy (recorded, not fixed here): backend/apps/access_control/tests_support/executor_actual_schema.py, a standalone executor harness that the suite does not run, approves without an attestation and is now refused by design (update it with the executor change); the gated-off legacy RegistrationReviewLivePanel still sends an empty approval body, which the server now refuses with 400 (it stays behind REGISTRATION_REVIEW_LIVE_API_ENABLED = false).
- Activation for local review only: config.review_local_settings (unchanged; loopback, acknowledgement, both decision gates, email off) with the Vite build switches VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=1 and VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED=1.
- Lint: `npm run lint` FAILS (exit 1) because of the pre-existing baseline error ThemeToggle.tsx:17 (no-useless-assignment), with the pre-existing warning RegistrationReviewLivePanel.tsx:74 (react-hooks/exhaustive-deps). Both findings are identical at fa525a1 and b974087, neither file was changed by WF-02.03, and the WF-02.03 files lint clean. Documented baseline exception approved by the owner on 18 November 2026 for WF-02.03 only: it covers exactly these two unchanged pre-existing findings, it does not mean lint passed, and it is not a general exception for future workflows (any new finding, or a change to either finding, still fails acceptance). Correcting the ThemeToggle.tsx:17 error remains a separate task.
- Remaining, outside this flow: D-09 and D-12 stay open beyond approval (legacy transition and an authoritative HR source). WF-02.04 is not started.

Evidence level: Code-verified and automated-test verified, 18 November 2026 (branch ronald, base fa525a1). Isolated MySQL test database only; no real applicant data was created or changed and no email was sent.
- New backend tests, test_wf0203_approval (32): Student approval sets Approved, active, reviewed_by, reviewed_at, no rejection reason and exactly one Student account_roles row (assigned_by the reviewer), with an audit row whose actor, target, role, old and new values are exact and contain no email or ID; Instructor needs the employment source; a case-only proof difference is accepted; no email, a blank email, no proof time, no proof address and a changed address are each refused (email_unverified) with nothing written; 14 missing, false, malformed, forged or wrong-role attestations refused (eligibility_unconfirmed), and an omitted one; authorization is checked before policy (no permission plus unverified email gives the generic denial, never the policy reason); account Deny over a role grant; self-approval, Django superuser and an already approved target denied without a second audit; only the requested base role, no direct grants, and empty effective permissions (D-50); audit failure rolls back everything; D-51 refuses with the writer enabled before any executor call; the approval gate off refuses. Outbox (D-49): one encrypted row linked to the approval audit and no email sent inside the decision; none when the outbox is disabled; none after a refusal; an outbox failure rolls back the approval; a delivery failure (retry) leaves the approval intact; a repeated approval never duplicates it; the legacy email path runs only on commit. HTTP through config.review_local_urls: exact 200 body with no-store; 409 email_unverified and eligibility_unconfirmed with the fixed body and no applicant data; 11 malformed bodies 400 (role or status fields cannot be supplied); stale and unknown targets the same 404; missing CSRF 403, anonymous 401, no permission 403 (checked before the body), approval gate off 503, protected writer on 503; 21st request in a minute 429; after approval the application leaves the WF-02.01 list, its WF-02.02 detail is 404, and the applicant signs in with roles ["Student"] and permissions []. Route: the approve and reject paths do not resolve in config.urls and resolve only in config.review_local_urls. Two real MySQL connections: two concurrent approvals approve once (the second, blocked on the first one's row locks, is denied, one audit, one role); approve racing reject gives one decision (Approved); a permission revoked by a concurrent transaction is honoured by the waiting approval (denied, still Pending, no audit).
- Audit contract, test_audit_approval_attestation (9): Student and Instructor attestations recorded with the reviewer as actor, the applicant as target and created_at set; missing attestation, each single missing field and a missing target rejected; 13 malformed or forged values (false, 1, "true", null, other evidence states, wrong case, unknown sources, lists, objects) rejected; mismatched subject and source rejected; unrelated, nested, free-text and personal fields rejected; the fields rejected on every other event and in old_value; other events keep their original contract. test_audit 42/42 unchanged.
- Bulk (D-53): test_registration_bulk 23/23 and test_task1_reapplication pass with the changes listed above.
- Backend regression: all 77 accounts and access_control test modules 1652/1652 (41 new). `manage.py check`: no issues. `makemigrations --check --dry-run`: no changes detected.
- Frontend: tests/registration-review-approval.test.mjs 11/11 (switch off by default and separate; one fixed source per role; the plan carries only the attestation; only the two refusal reasons recognised; switched off, no CSRF request or POST; one CSRF-protected POST and the exact decision required; 10 definite refusals keep their codes and are not retried; 9 possibly-applied outcomes become outcome_unknown and are sent once; a failed security check sends nothing; the legacy plan unchanged; no role, postJSON or reject control in the approval code). tests/browser/applicant-approval-errors.test.mjs 8/8: attestation errors with focus on the first one, only the role's source offered, the dialog with focus on Cancel, Escape and Cancel returning focus with nothing sent, one POST with CSRF and the exact body, the focused "Application approved" view and a list reload; no section without the approve permission, and no form when the email is not verified; the Instructor source; 409 (both reasons), 403 (no sign-out), 429 and 503 messages, focused, each sent once, and the confirmation cleared after eligibility_unconfirmed; 404 shows no longer pending; an aborted request pauses approval until the application is reloaded and is never replayed; while in flight both dialog buttons are disabled, Escape is ignored and only one POST is sent; 360/768/1024/1440 px in Light, System-dark and Dark with no overflow, the dialog inside the viewport and composited AA contrast for the page, field errors and dialog text. `npm test` 187/187. `npm run test:registration-ui` 100/100 (the WF-02.02 detail tests still find no decision controls with the approval switch off). `npm run build` passed. `npm run lint`: FAILED (1 error, 1 warning), both pre-existing and identical at the fa525a1 baseline (ThemeToggle.tsx:17 error, RegistrationReviewLivePanel.tsx:74 warning); nothing new, and no WF-02.03 file has a finding. Accepted only as the owner-approved, WF-02.03-specific baseline exception (see Blocked by); lint did not pass.
- Not verified: an interactive run against real data (the development database has 0 Pending accounts and none were created), a Technical Super Admin with a provisioned role outside tests, the protected executor path (approval is refused there by design, D-51), and production deployment.

Human Approval: ☒ Approved by: Ronald C. Arias  Date: November 18, 2026

Next flow: WF-02.04. Do not start until Approved is ticked.

#### WF-02.04 — Reject applicant, notify by email, and delete rejected registration data

| Field | Definition |
| --- | --- |
| Actor / required permission | School Admin (Normal Administrator): an approved, active, non-staff, non-superuser account with an active Admin role assignment and the exact effective permission accounts.registration_requests.reject (catalogue v2: "Reject school registration", SCHOOL scope, GOV grant protection, default binding Admin only). Technical Super Admin (Super Administrator) only through effective permissions while also holding Admin; that role has no registration binding of its own. Account-level Deny wins over role grants; no role-name bypass; Django is_staff/is_superuser confer nothing. |
| Trigger | From the WF-02.02 applicant detail, a reviewer selects Reject application, chooses one fixed rejection reason and confirms. |
| Preconditions | Valid Workspace session and CSRF token (WF-01.03, WF-01.06); accounts and access_control services active and the Admin reject grant active; rejection reachable only in an approved release mode (D-62); the application eligible (Pending, inactive, not staff or superuser, reviewed_by and reviewed_at empty, requested role active Student or Instructor, no assigned role, no direct permission rows, no other audit or framework history referencing it, not the reviewer); the durable notification outbox available (D-54). Email-ownership proof and the D-45 attestation are approval requirements and are NOT rejection preconditions (D-55). |
| Result | In one transaction: an append-only access_audit_logs record (account.registration.reject) with no applicant identity beyond the internal account_id (old {account_id, Pending, inactive}; new {account_id, Rejected, inactive, rejection_code, account_deleted: true}; target NULL; the reviewer as actor), one encrypted notification outbox row bound to that audit record, and the deletion of the applicant's users (profile) and accounts rows (credentials, email, email proof and reset fields with them). After commit the outbox worker delivers the rejection email using the audit snapshot (D-54). The School ID and email become free for an ordinary new registration (WF-01.01/01.02) that starts again as a new Pending application. No account reuse (D-61). |
| Status | Inspected and reconciled 18 November 2026; stage 1 and stage 2 owner-authorized the same day. Implemented and tested 18 November 2026 (uncommitted work committed locally on ronald, not pushed): the durable outbox and v2 template are mandatory (D-54); a verified, deliverable recipient is required, so no-email rejection is refused (D-55 revised); conflicts are fixed 409s and stale targets 404 (D-58); success reports the email as queued; the rejection section is behind its own switch (off); the encrypted recipient is erased in the same lease-fenced update that makes a notification Delivered or Dead (D-57); legacy reapplication is disabled in the executor settings (D-61, partial); local review mode and the sandbox enable the outbox with in-memory mail only (D-62). Rejection stays out of config.urls; production stays blocked. Committed locally as fac37a9. Human Approval recorded by the owner (Ronald C. Arias, November 18, 2026) for completed local development after reviewing the finished implementation, the reported test results and the WF-02.04-only baseline lint exception; it does not authorize production release. |

**Inspection basis:** On 18 November 2026 the owner requested Inspect and Reconcile of WF-02.04 only (no implementation, no WF-02.05). Branch ronald at 1615d8e (b974087 WF-02.03, 1615d8e its Human Approval), 4 commits ahead of origin/ronald, not pushed. Prerequisites verified: WF-02.01, WF-02.02 and WF-02.03 Human Approvals recorded (Ronald C. Arias, November 17, 17 and 18, 2026). Working tree: only this catalogue modified, holding another editor's uncommitted drafts (header text, WF-05 to WF-11.01, the 0.3.8 change-log row and the standardized WF-02.04 footer lines), all preserved. Inspected read-only:
- Backend: accounts/registration_review.py (_decide reject path, _delete_rejected_registration, REJECTION_CODES), registration_review_api.py (RejectRegistrationRequestView), registration_review_urls.py, config/urls.py, review_local_settings/urls, review_sandbox_*, registration_outbox.py, outbox_models.py, outbox_crypto.py, outbox_worker.py, registration_email_templates.py, registration_notifications.py, registration_staging.py, reapplication.py and reapplication_api.py, registration_bulk.py, access_control/audit.py, executor client, protocol, engine and schema.py (writer triggers), catalogue v2_0.json.
- Schema: docs/database/full_schema.dbml, the Django models and the live MySQL foreign keys (information_schema).
- Requirements: SRS v0.4 UC-03, FR-REG-07, AT-V04-02 and OD-23; SRS v1 UC-03 and FR-REG-07; Use Case Specification v0.4.1 ACT-SA-04, UC-D04, O-03 and O-04.
- Frontend: ApplicantDetailPanel.tsx, PendingApplicationsPanel.tsx, the shared Modal.tsx, RegistrationReviewLivePanel.tsx (legacy, gated off).
- Read-only development database checks (no identities, no writes, transaction rolled back): 0 Pending, 3 Approved, 1 Rejected; 0 outbox rows; 0 registration staging rows.
- Existing tests run unchanged: 134 tests in 9 rejection-related modules passed (rejection retention, outbox, outbox worker, review service and API, reapplication, bulk, release safeguard, routing).

**Reconciliation (requirement → evidence → finding):**
- R-01 Existing rejection. reject_registration() → _decide(approve=False) is implemented and tested; RejectRegistrationRequestView (POST, CSRF, require_actor(reject) first, body exactly {"rejection_code": <one of 4>}, 20/min per-address throttle shared with approve, 404 request_unavailable, 503 review_unavailable) is mounted only by registration_review_urls.py, i.e. config.review_local_urls and the sandbox. config.urls has no reject route; the P1/P3C release safeguard refuses one. Verified: deliberately unmounted, not missing.
- R-02 Authorization and locking. Identical to approval: Admin assignment pre-check, both services active, then one writer_atomic READ COMMITTED transaction locking services, the exact reject permission, reviewer and target accounts, both accounts' role rows, roles, the reviewer's role and account permissions, and a has_permission re-check inside the lock (Deny precedence). Self-rejection, Django staff/superuser and inactive reviewers are refused. Verified.
- R-03 Eligibility. Same target checks as approval, plus: a target with direct account_permissions is refused, and the delete fails closed (MySQL 1451) when any other row references the account (an earlier audit, a framework log entry), which is mapped to a refusal. D-44 (email proof) and D-45 (attestation) are not applied to rejection; legacy unverified Pending applicants, who cannot be approved (D-44), can therefore still be rejected. Verified.
- R-04 Reason. Mandatory, one of four fixed codes (incomplete_submission, ineligible_registration, identity_mismatch, duplicate_request); no free text; stored in the audit snapshot (and accounts.rejection_reason until the row is deleted). The v2 template shows a fixed public label per code; the v1 template (the default while WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED is off) states no reason. Verified.
- R-05 Deletion. _delete_rejected_registration issues exactly two fixed deletes (users, then accounts with a Rejected/inactive/non-staff guard) after the audit and outbox rows exist; any failure rolls back the audit, outbox and status change (tests). Every foreign key to accounts and access_audit_logs is NO ACTION (no cascade); the outbox references only the audit record, which has target NULL for rejection, so the notification survives the deletion. Password-reset data are columns of accounts and go with it; registration staging rows have no FK and are deleted on completion (0 rows). Verified (models, ERD and live information_schema agree).
- R-06 Notification. With WORKSPACE_REGISTRATION_OUTBOX_ENABLED the encrypted recipient (AES-GCM bound to the audit id and template) is written in the same transaction; the at-least-once worker (leases, retry, Dead) renders the v2 email from the immutable audit snapshot, so delivery works after the account is gone; a missing key or outbox error rolls the whole rejection back. A missing or invalid address produces a Dead row ("recipient_unavailable") and the rejection still deletes the account. Without the outbox, the legacy best-effort path sends once after commit and is lost on failure; with both off, nothing is sent. Verified.
- R-07 Critical gap: the only modes where rejection is reachable (config.review_local_settings and the sandbox) force the outbox and email off, so a rejection there deletes the applicant's data and creates no notification, and the address is then gone. This violates FR-REG-07 ("SHALL send a truthful rejection email") and must be resolved before WF-02.04 is usable (D-54).
- R-08 Retention gap: outbox rows keep the encrypted recipient indefinitely after Delivered or Dead; recipient_erased_at exists but nothing sets it, and the executor trigger makes the recipient columns immutable for the notifications principal. The audit row keeps no direct identity (account_id integer, reason code, reviewer FK, time). No retention period is defined anywhere (D-57).
- R-09 Re-registration. Ordinary registration refuses only when an accounts row has the same School ID or email (registration_staging._identity_conflicts); after deletion both are free, and test_rejected_applicant_can_register_again_with_same_credentials proves a new Pending account with a new ID. No blacklist exists. Verified.
- R-10 Conflicting existing mechanism. reapplication.py / reapplication_api.py implement a signed-link "reapplication of REJECTED accounts" that revives the same account row (Rejected → Pending). Routes are in apps/accounts/urls.py (mounted under /api/v1/auth/) but fail closed (503) unless WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED; off by default and in local review mode, but set True in config/executor_settings.py and executor_isolated_settings.py; no frontend caller. Because current rejection deletes the account, it can apply only to legacy Rejected rows. It contradicts SRS v0.4 UC-03 ("no previous-credentials or rejected-account-reuse design") (D-61).
- R-11 Legacy data. The development database's single Rejected account predates deletion: inactive Student request, reason code set, reviewer set, email present without proof, profile present, no roles or direct grants, one reject audit that targets the row (no account_deleted snapshot), no outbox row. It keeps its School ID and email reserved, is eligible for the R-10 mechanism, and cannot be deleted while its append-only audit references it (NO ACTION FK). Separate cleanup authorization required (D-60); not modified.
- R-12 Executor and release. The executor protocol already carries rejection_code and the engine dispatches reject_registration; the executor schema allows users/accounts deletes only through wex_rejected_registration (verified reject request, matching audit, no roles or grants). Rejection, unlike approval (D-51), therefore has executor parity. writer_boundary RELEASE_STATUS stays BLOCKED, so no production path exists. Verified.
- R-13 Refusal reporting. Every refusal (stale, protected history, direct grants) answers 404 request_unavailable, so a reviewer who can read a protected-history application cannot tell why it was refused (D-58).
- R-14 Concurrency. Covered by the shared lock order: a concurrent approval, rejection, deactivation or permission change serializes; a waiting decision re-reads committed state and is refused (a deleted target is "no longer exists"). Two-connection evidence exists only for approve-then-reject (WF-02.03); reject-first, reject/reject and revocation-during-rejection are untested (P-09).
- R-15 Bulk. The unmounted, test-only bulk service supports rejection with the same fixed codes and is unchanged; no bulk rejection UI is proposed.
- R-16 Frontend. The WF-02.02 detail and WF-02.01 list have no reject control; the legacy RegistrationReviewLivePanel has a reject flow behind REGISTRATION_REVIEW_LIVE_API_ENABLED = false; the shared Modal (WF-02.03) and dashboard feedback tokens exist. The API reply ({account_id, status}) does not say whether an email was queued, so the UI cannot truthfully report notification state today (D-54).
- R-17 Requirements conflict. SRS v1 FR-REG-07 (retain rejected requests) is superseded as design intent by SRS v0.4 FR-REG-07 and UC-D04 (notify, delete, fresh registration), which also say this is not automatic cleanup authorization for existing data (D-60).

**Implementation basis (stage 1, 18 November 2026; uncommitted):** The owner authorized the first implementation stage with D-54 APPROVED (durable outbox mandatory for a completed rejection), D-55 REVISED (no-email rejection is not authorized; a valid verified recipient is required until an alternative policy is separately approved), D-56 APPROVED (four fixed reasons), D-57 APPROVED IN PRINCIPLE (minimal audit and recipient erasure; protected details gated), D-58 APPROVED WITH CLARIFICATION (privacy-safe 404 kept, fixed 409 policy conflicts), D-59 APPROVED (rejection UI), D-60 APPROVED (legacy Rejected records untouched), D-61 APPROVED IN PRINCIPLE (retire reapplication through a separate protected authorization) and D-62 APPROVED (local review and sandbox only; production blocked). The existing reject_registration() service was reused. Files changed:
- backend/apps/accounts/registration_review.py (governance-sensitive). New RegistrationRejectionNotAllowed(reason) with reasons recipient_unverified, direct_permissions and protected_history (a RegistrationReviewDenied subclass, so bulk and executor callers fail closed) and rejection_notification_ready() (outbox AND v2 template). In the local write path, after the writer-boundary check and before any database read or write, a rejection without the ready outbox raises RegistrationReviewUnavailable (D-54; never the best-effort email path). Inside the locked transaction, after the existing reviewer, permission and target checks and before any write: direct account permissions → direct_permissions; no verified current address (the D-44 rule) or an address the outbox cannot deliver to → recipient_unverified (D-55 revised). After the encrypted outbox insert, the rejection completes only if that row is Pending; the delete-protection failure (MySQL 1451) now raises protected_history. Audit snapshot, lock order, permission re-check and the two-table deletion are unchanged; approval is unchanged.
- backend/apps/accounts/registration_review_api.py. RegistrationRejectionNotAllowed → 409 {"error": {"code": "rejection_not_allowed", "reason": <fixed>, "message": "Rejection is not allowed for this application."}} before the 404 mapping; success now returns {"account_id", "status": "Rejected", "notification": "queued"} (queued, never delivered). The request body is unchanged: exactly {"rejection_code": <one of four>}.
- New backend tests: backend/apps/accounts/test_wf0204_rejection.py (31).
- frontend/src/features/admin/pendingApplicationsConfig.ts: APPLICANT_REJECTION_ENABLED (VITE_WORKSPACE_REGISTRATION_REJECTION_ENABLED=1; default off). registrationReviewApiContract.ts: REJECTION_PUBLIC_LABELS (identical to the backend email labels), buildRejectionRequest (one fixed code only), parseRejectionDecision (requires notification "queued") and parseRejectionRefusal. registrationReviewApi.ts: rejectApplication(), switch checked first, one CSRF-protected POST, never retried, outcome_unknown for anything possibly applied. The WF-02.03 approval client is unchanged.
- frontend/src/features/admin/ApplicantRejectionPanel.tsx (new) inside ApplicantDetailPanel.tsx, shown only with the switch and the exact reject permission: the four reasons with the exact public wording, no free text; for a no_proof, address_changed or no_email application a statement that it cannot be rejected and no form (D-55 revised); the shared Modal "Confirm rejection?" naming the applicant, ID, reason and recipient, with Cancel first and focused and the COMPONENTS §2 destructive confirm; busy state that ignores Escape and blocks double submission; a focused "Application rejected" view that says the email "has been queued for delivery" and that delivery is not confirmed here; fixed messages for the three conflicts, 404 (no longer pending), 401, 403, 429, 503 and invalid requests; an uncertain result that pauses rejection until reload. The approval section and its behaviour are unchanged; both sections can appear together. docs/design/COMPONENTS.md marks the destructive style Current.
- New frontend tests: tests/registration-review-rejection.test.mjs (11) and tests/browser/applicant-rejection-errors.test.mjs (9).
Not changed: config.urls, config/review_local_settings.py, config/review_sandbox_settings.py, the release safeguard and P1–P4, writer_boundary.py, the executor client, protocol, engine, schema and settings, outbox_worker.py, registration_outbox.py, reapplication.py and its routes, registration_bulk.py, models, migrations, the ERD, permissions, real applicant data and the legacy Rejected account.

**Implementation basis (stage 2, 18 November 2026):** The owner approved the 30 existing-test corrections (25 setup or contract changes, 5 behavioural rewrites with safeguards) and authorized these protected changes: config/review_local_settings.py and config/review_sandbox_settings.py (outbox and v2 template for isolated local review and sandbox, in-memory mail, no SMTP, no key in source control, guards unchanged); apps/accounts/outbox_worker.py and apps/access_control/executor/schema.py (D-57 recipient erasure only, after confirming no recovery path needs a Dead row's address); config/executor_settings.py and config/executor_isolated_settings.py (disable reapplication only). Files changed:
- config/review_local_settings.py, config/review_sandbox_settings.py: WORKSPACE_REGISTRATION_OUTBOX_ENABLED and WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED True, best-effort notifications False, SMTP False, the locmem backend, a loopback WORKSPACE_PUBLIC_BASE_URL. The key is never in source: a test-only WORKSPACE_OUTBOX_KEK_V1_B64 must be set in the local environment, otherwise every rejection rolls back; the worker still needs WORKSPACE_OUTBOX_WORKER_ENABLED=1. Acknowledgement, DEBUG, local-database and loopback guards, cookie names, URLconfs and the reapplication-off lines are unchanged.
- apps/accounts/outbox_worker.py (protected; D-57): RECIPIENT_FIELDS and one erasure step in the existing lease-fenced terminal updates: _finish for Delivered and for Dead (permanent failure, or the final attempt), and _claim_next's attempts-exhausted Dead path. The four encrypted fields become NULL and recipient_erased_at is set in that same UPDATE; status, attempt count, failure code, delivered_at and timestamps are kept. Pending, Retry and Leased rows are never erased, and a stale worker whose lease expired erases nothing. Inspection found no path that re-queues or recovers a Dead row (the due filter excludes Dead and the management command only previews or delivers due rows), so no recovery operation needs the address.
- apps/access_control/executor/schema.py (protected; D-57): for the notifications principal the outbox UPDATE trigger keeps outbox_id, decision_audit_log_id, template_code, template_version and created_at immutable; the recipient envelope may change only as a complete erasure (all four fields NULL and recipient_erased_at newly set) in one update from Leased to Delivered or Dead; an erased row can never return to a non-terminal state. Its column grant adds exactly those five columns. Every other trigger, grant and the append-only audit rules are unchanged; no general outbox mutation privilege was added.
- config/executor_settings.py, config/executor_isolated_settings.py (D-61, partial): WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED = False. reapplication.py, reapplication_api.py, the routes and the executor protocol handler are kept (fail closed).
- Test corrections (30, owner-approved): test_registration_rejection_retention 8 and test_registration_bulk 8 (outbox, v2 template and a per-test random key; the applicants used for successful rejection get verified proof; assertions unchanged); test_registration_outbox 3 setup (v2 template) and 2 rewrites (missing email and invalid historical email: rejection refused recipient_unverified with no deletion, role, audit or outbox row, and the writer's safe Dead disposition without ciphertext still covered directly); test_registration_review_notifications 2 rewrites (the best-effort test now proves rejection is refused without the outbox even with the best-effort gate on, then queues exactly one encrypted row bound to its audit with no callback or email; the missing-email test proves refusal with no deletion, role, audit, row or email); test_registration_review 2, test_registration_review_api 1, test_registration_review_p3c_authenticated_boundary 1, test_registration_review_p4_http_contract 1 (outbox prerequisites; the HTTP tests now also require "notification": "queued"); test_task1_reapplication 1 (its bulk-rejection applicants get verified proof); test_wf0203_approval 1 (the approve/reject race enables the outbox so the losing rejection reaches the locks). No test was removed and no proof was added where proof is the point. New test-only helper: apps/accounts/rejection_test_support.py.
- New tests: apps/accounts/test_wf0204_outbox_erasure.py (14) and apps/accounts/test_wf0204_release_settings.py (11).

**Proposals (decided by the owner 18 November 2026 as recorded above; P-02's no-email acknowledgement was not authorized under the revised D-55; P-05 and P-06 protected parts remain gated):**
- P-01 Notification required (D-54). In _decide (registration_review.py, governance-sensitive), refuse rejection with 503 review_unavailable before any write unless the durable outbox is enabled and the v2 template is on; never use the best-effort path for rejection. The API reply adds "notification": "queued" | "not_sent" derived from the outbox row's status in the same transaction.
- P-02 Recipient policy (D-55). Queue the email only for a verified current address (the D-44 rule); otherwise create the Dead row ("recipient_unverified" or "recipient_unavailable"), and require the reviewer's explicit acknowledgement field "no_email_acknowledged": true in the request; without it 409 rejection_not_allowed (reason notification_unavailable).
- P-03 Reason contract (D-56). Keep the four fixed codes and their public v2 labels; no free text or reviewer notes; no change to the codes or the audit snapshot.
- P-04 Refusal reporting (D-58). 409 rejection_not_allowed with fixed reasons (protected_history, direct_permissions, notification_unavailable) for an application the reviewer can read; stale or unknown stays 404.
- P-05 Release mode (D-62). Keep reject out of config.urls and the release safeguard unchanged; usable only in local review mode and the sandbox. Enabling the outbox there (locmem backend, test key, no SMTP) is a change to release-tooling configuration that needs separate authorization; until then P-01 makes rejection refuse in those modes rather than delete without notice.
- P-06 Retention (D-57). Keep the minimal append-only rejection audit record; erase the encrypted recipient after Delivered or Dead (worker change plus an executor-schema trigger change, both protected); no retention period, blacklist or identity digest invented.
- P-07 Frontend switch and client. VITE_WORKSPACE_REGISTRATION_REJECTION_ENABLED (default off); rejectApplication(id, code, ack) with its own CSRF POST, never retried, strict parsing of 200, 404, 409 reasons and errors, outcome_unknown for anything possibly applied.
- P-08 Frontend UI (D-62 scope). A Reject application section in the WF-02.02 detail, shown only with the switch and the exact reject permission: the applicant summary; a required reason select (fixed codes, each with the public wording the applicant will see); a notification line that says whether an email can be queued; Reject application → the shared Modal "Confirm rejection?" naming the applicant, ID and reason, stating that the account and personal data will be deleted, that it is audited and cannot be undone, and (when applicable) that no email can be sent, with a required acknowledgement checkbox; Cancel first and focused; the destructive confirm style (COMPONENTS §2); busy state that blocks Escape and double submit; on success a focused "Application rejected" view that says "A rejection email has been queued" or "No email will be sent", never "sent"; 409, 404 (no longer pending), 401, 403, 429, 503 and an uncertain result that pauses until reload and is never replayed; the list reloads after a decision. No bulk rejection UI. Approval (WF-02.03) unchanged.
- P-09 Tests (see Evidence level) and P-10 regression.
- Not proposed: migrations or ERD changes, new permission codes, free-text reasons, reviewer-visible delivery tracking, account reuse, deletion of existing legacy data, mounting decision routes in config.urls, relaxing release safeguards, or changes to WF-02.03.

#### Main flow

1. The reviewer opens a pending application in WF-02.02 and reads the applicant, email evidence and institutional panels.
2. In the Reject section the reviewer chooses one fixed reason; the page shows the public wording the applicant will receive and whether an email can be queued.
3. The reviewer selects Reject application; an accessible dialog names the application, reason and verified recipient and states that the account and registration data will be deleted, a rejection email will be queued, and the action is audited and cannot be undone; the reviewer confirms.
4. The frontend fetches a fresh CSRF token and sends one POST /api/v1/admin/registration-requests/{id}/reject/; it never retries.
5. Django checks the gates, session, CSRF, Admin assignment, both services and the exact reject permission; validates the body; then, in one locked transaction, re-checks reviewer and target and requires the outbox (D-54).
6. Django writes the rejection audit and the encrypted Pending outbox row, deletes users and accounts, and commits; anything else rolls everything back.
7. The frontend shows "Application rejected" (email queued for delivery, delivery not confirmed) only after the 200 response, and the list reloads without the application.
8. After commit the outbox worker delivers the v2 rejection email (reason label and "Register Again"); delivery failures retry and finally become Dead; the rejection stands.
9. The applicant may register again through WF-01.01/01.02 with the same School ID or email; a new Pending application is reviewed normally.

#### Alternative flows

- A1 No verified address (no proof, changed address, no email): rejection is not authorized (D-55 revised); the section states that the application cannot be rejected and shows no form; a forged request is refused 409 rejection_not_allowed (recipient_unverified); the application stays Pending until an alternative policy is separately approved.
- A2 Outbox disabled or unavailable (key missing, insert fails): refused 503 with nothing changed; never delete without the notification record (D-54).
- A3 Processed or changed elsewhere (approved, rejected, deleted, role assigned): 404 request_unavailable; the page reports the application is no longer pending.
- A4 Two reviewers decide at once (reject/reject or reject/approve): row locks serialize them; the second is refused.
- A5 Reviewer loses the reject permission (Deny, revoked grant, inactive role or service): 403/503 before the request, refused inside the lock during it; nothing changes.
- A6 Protected history or direct grants on the applicant: 409 rejection_not_allowed (protected_history / direct_permissions) and nothing changes (D-58); separate review required.
- A7 Email delivery fails: the worker retries with backoff and finally marks Dead; the rejection and deletion stand; no false delivery claim anywhere.
- A8 Rejection not released in this mode or the frontend switch off: no Reject control; the read-only WF-02.02 page is unchanged.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| 4–5 | Session expired or not a Workspace identity | 401 authentication_required; WF-01.06 session-ended screen; nothing changed |
| 4–5 | Missing or invalid CSRF token, or untrusted Origin | 403 before any parsing; nothing changed |
| 5 | No Admin assignment, missing, inactive or denied reject permission | 403 access_denied; nothing changed |
| 5 | Self-rejection, or reviewer loses eligibility or permission before the locked re-check | Refused inside the transaction (404 request_unavailable); nothing changed |
| 5 | Body not exactly the allowed fields, unknown reason code | 400 invalid_request; nothing changed |
| 5 | Gates off, services inactive, writer boundary or executor unavailable, outbox disabled or key missing | 503 review_unavailable; nothing changed |
| 5 | No verified deliverable address, direct grants, or protected history | 409 rejection_not_allowed (recipient_unverified, direct_permissions, protected_history); nothing changed |
| 5 | Application not found, no longer Pending or otherwise ineligible | 404 request_unavailable (non-enumerating); nothing changed |
| 6 | Audit, outbox insert or deletion fails | Whole transaction rolls back: application still Pending, no audit, no outbox row |
| 4, 7 | Network failure or timeout after sending, other 5xx, unexpected reply | "We could not confirm whether the application was rejected." Rejection pauses until the application is reloaded; never retried automatically |
| 8 | SMTP or worker failure after commit | Retry, then Dead with a fixed failure code; the decision stands; no applicant data in logs |
| 5 | More than 20 decisions a minute from one address | 429 rate_limited |

#### Links

Depends on: WF-01.01 and WF-01.02 (registration, email proof, identity-conflict rules for fresh registration), WF-01.03 and WF-01.06 (session, CSRF), WF-02.01 (queue), WF-02.02 (applicant detail and evidence wording), WF-02.03 (shared review service, lock order, Modal, approval policy D-44/D-45 which does not apply here), WF-03 (effective permissions), WF-09 (notification delivery: outbox worker and email templates), WF-12 (audit review and retention), the protected writer/executor and the AR-6C release sequence (P1–P4), D-09, D-12, D-17.

Feeds: WF-01.01/01.02 (fresh registration with the same School ID or email), WF-09 (rejection email delivery), WF-12 (account.registration.reject audit review).

Traceability: SRS v0.4 UC-03, FR-REG-04, FR-REG-07, FR-AUTH-03, AT-V04-02 and OD-23 (superseding SRS v1 FR-REG-07 retention wording as design intent); Use Case Specification v0.4.1 ACT-SA-04 and UC-D04, open items O-03 and O-04; ERD tables accounts, users, account_roles, account_permissions, access_audit_logs, registration_notification_outbox (no change).

#### Pending detail — preserved from v0.1 sample (reconciled 18 November 2026; superseded by the entry above, kept for traceability)

The following content is retained verbatim from the original sample use case for later reconciliation. It is not a validated WF-02.04 specification.

| Original sample field | Original sample wording |
| --- | --- |
| Primary actor | School Admin with approved account-review permission |
| Trigger | School Admin selects Reject for a pending applicant |
| Preconditions | Application is pending; actor is authenticated and authorized |
| Main flow | 1. Display applicant and validation details.<br>2. Collect an authorized rejection decision and reason as required.<br>3. Validate the decision and process the rejection safely.<br>4. Trigger a rejection email notification to the applicant.<br>5. Delete rejected registration account/data from application records under the approved retention policy.<br>6. Return a clear outcome to the School Admin. |
| Alternative / exception flows | If authorization fails, reject without changing the record. If notification or deletion fails, follow a documented recovery path without reporting unsupported completion. |
| Postcondition | Rejected applicant cannot use the rejected registration; normal fresh registration is possible, including reuse of the School ID/email when permitted by the approved deletion workflow. |
| Verification | Tests cover authorized rejection, denial to unauthorized actors, notification behavior, deletion, and fresh registration; privacy/audit handling requires explicit approval. |

Guidelines: Inspect → Reconcile → Approve → Implement → Test → Commit

AI Agent Guidelines Checklist: ☒ Inspect   ☒ Reconcile   ☒ Approve   ☒ Implement   ☒ Test   ☒ Commit

Checklist scope: Inspect and Reconcile cover the read-only inspection and R-01 to R-17 above. Approve records the owner's 18 November 2026 stage-1 and stage-2 authorizations (D-54 to D-62; D-55 revised; D-57 and D-61 in principle, with the protected parts listed under Implementation basis). Implement and Test cover the application-level and authorized protected changes and the results under Evidence level (lint under the WF-02.04-only baseline exception). Commit: one local commit on ronald (fac37a9) containing only the WF-02.04 work and this entry, not pushed. Human Approval was recorded by the owner on November 18, 2026 for completed local development; it is not a production-release authorization.

Blocked by:
- Human Approval recorded by the owner (Ronald C. Arias, November 18, 2026) for completed local development only. It does not release production rejection or close any item below.
- Delivery is not guaranteed: a successful rejection guarantees only that the encrypted email was queued in the same transaction as the decision and the deletion. Delivery happens later in the separately gated outbox worker, is at-least-once (a rare duplicate after a worker crash is possible) and may end Dead after the final attempt. Before production, terminal Dead notifications need a separately approved operational policy (who monitors them, how a reviewer or applicant is informed, and whether any re-notification is allowed, given that the recipient is erased at Dead and the applicant's data are already deleted).
- OPEN — Production rejection stays blocked: no reject route in config.urls (D-62), writer_boundary RELEASE_STATUS BLOCKED, SMTP delivery not approved (WF-09). In local review mode and the sandbox rejection works only with a test-only key in the environment and delivers only to Django's in-memory mailbox.
- OPEN — Retention (D-57): no retention period is set for the rejection audit record or for outbox metadata (status, attempts, failure code, times); that is an owner decision. Recipient erasure applies to rows that reach Delivered or Dead from now on; there is no backfill for rows that became terminal earlier (the development database has 0 outbox rows).
- OPEN — Full reapplication removal (D-61, separate proposal for authorization): remove apps/accounts/reapplication.py, reapplication_api.py, the two /api/v1/auth/reapply/ routes in apps/accounts/urls.py, the registration.reapply operation in executor/protocol.py, client.py and engine.py, the reapplication settings in config/settings.py and the review/executor overlays, and their tests (test_task1_reapplication's reapplication cases, test_session_security's reapplication case, executor-harness steps in tests_support/executor_actual_schema.py). Dependencies: none in the frontend; the executor protocol changes are protected. Legacy-account policy: under D-60 legacy Rejected rows stay untouched and keep their School ID and email reserved; after removal they have no path back, so any cleanup (for example anonymizing in place, since the NO ACTION audit reference blocks deletion) needs its own decision.
- Known effects: the gated-off legacy RegistrationReviewLivePanel expects the old reject reply and would report an uncertain result; the executor maps remote refusals to the generic denial, so the 409 reasons are not carried over the executor; the standalone executor harness (tests_support/executor_actual_schema.py, not part of the suite) still contains reapplication steps that the executor now refuses by design.
- Lint: `npm run lint` FAILS (1 error, 1 warning). Both findings are the pre-existing baseline, identical at 1615d8e and now (ThemeToggle.tsx:17 no-useless-assignment error, RegistrationReviewLivePanel.tsx:74 react-hooks/exhaustive-deps warning); neither file changed and no WF-02.04 file has a finding. The owner authorized a documented WF-02.04-only baseline exception for exactly these two findings on 18 November 2026; it is not a lint pass and not a general exception. Correcting ThemeToggle.tsx:17 remains a separate task.
- OPEN — Legacy-account cleanup: the development database's one Rejected account stays untouched (D-60) and needs a separate decision; D-09 and D-12 stay open beyond approval and rejection.

Evidence level: Code-verified and automated-test verified, 18 November 2026 (branch ronald, base 1615d8e). Isolated MySQL test database, locmem email and synthetic applicants only; no real data changed, no live or SMTP email.
- test_wf0204_rejection 31/31 (unchanged from stage 1; listed in the stage-1 implementation basis): minimal audit, one Pending encrypted row, exactly two deletes; four fixed reasons; every unverified email state refused; outbox or v2 off refused before any query; key, outbox, delete and audit failures roll back; non-Pending row never completes; 409 conflicts; authorization before policy; stale and repeat denied; fresh registration with the same School ID and email as a new Pending account; delivery after deletion and retry; bulk skips an unverified applicant; HTTP contract including 200 queued, 409, 400, 404, 401, 403, 429, 503, Technical Super Admin only with Admin; two-connection races reject/reject, reject→approve, approve→reject and revocation.
- test_wf0204_outbox_erasure 14/14: delivery erases the four encrypted fields and sets recipient_erased_at while keeping status, attempts, delivered_at, template and the audit row unchanged, and the row is never sent again; Pending, Leased and Retry keep the recipient; five failures keep it until the final attempt makes the row Dead and erased (attempts 5, failure code kept); a permanent SMTP refusal is Dead and erased; an exhausted expired lease is Dead and erased; a stale worker erases nothing; no reopening path; two real workers deliver and erase exactly once; the generated executor trigger, installed for real in the test database with the test user as the notifications principal, allows status-only updates and complete erasure from Leased to Delivered or Dead, and refuses erasure from Pending, while staying Leased or going to Retry, partial erasure, erasure without recipient_erased_at, forged ciphertext or key version, immutable evidence changes and reopening an erased row; the real worker delivers and erases under that trigger; the notifications grant adds exactly the five erasure columns and no insert, delete or other column.
- test_wf0204_release_settings 11/11: local review and sandbox enable the outbox and v2 with locmem, SMTP off, best-effort off, a loopback public URL, loopback middleware first, unchanged URLconfs and no key or mail credential in source; their acknowledgement and local-database guards still refuse; production defaults unchanged; with these settings the worker refuses SMTP and console backends; a sandbox-settings rejection is delivered only to the in-memory mailbox with external SMTP patched to fail; both executor settings disable reapplication; a validly signed token cannot revive a legacy Rejected account, no link is sent, and both legacy routes answer 503 even with a valid token and CSRF, all with the legacy row, profile and audit untouched; the legacy row still reserves its identity (D-60).
- The 30 corrected tests: the 10 affected modules 159/159.
- Backend regression: all 80 accounts and access_control test modules 1708/1708 (56 new across the three WF-02.04 modules: 31 + 14 + 11). `manage.py check`: no issues. `makemigrations --check --dry-run`: no changes detected. Development database read-only check afterwards: 0 Pending, 3 Approved, 1 Rejected, 0 outbox rows, legacy row intact.
- Frontend: tests/registration-review-rejection.test.mjs 11/11 and tests/browser/applicant-rejection-errors.test.mjs 9/9 (stage 1, unchanged); `npm test` 198/198; `npm run test:registration-ui` 109/109 (four widths, three themes); `npm run build` passed; `npm run lint` failed only on the two baseline findings (WF-02.04-only exception above).
- Not verified: an interactive run in local review mode or the sandbox against a running server (covered by settings and service tests), the second-server executor harness, and production deployment.

Human Approval: ☒ Approved by: Ronald C. Arias  Date: November 18, 2026

Next flow: WF-02.05. Do not start until Approved is ticked.

#### WF-02.05 — Activate or deactivate an existing account

| Field | Definition |
| --- | --- |
| Actor / required permission | School Admin (Normal Administrator): an approved, active, non-staff, non-superuser account with an active Admin role assignment and the exact effective permission accounts.school_accounts.suspend (deactivate) or accounts.school_accounts.activate (reactivate), plus accounts.school_accounts.read to find and view the account. All three are catalogue v2 codes (SCHOOL scope, GOV grant protection, readiness P "implementation required", default binding Admin only). Technical Super Admin (Super Administrator) only through effective permissions while also holding Admin; that role has no school-account binding of its own. Account-level Deny wins; no role-name bypass; Django is_staff/is_superuser confer nothing. This workflow grants no Access Control Management authority: no role assignment, permission editing or escalation. |
| Trigger | From the account directory (catalogue view account-directory, today "planned"), a reviewer opens an eligible account and selects Deactivate account or Reactivate account, then confirms. |
| Preconditions | Valid Workspace session and CSRF token (WF-01.03, WF-01.06); accounts and access_control services active; the actor's grant active; the operation reachable only in an approved release mode (D-69); the target eligible under the state matrix (D-63, D-65); the target's current active state equals the state the reviewer confirmed (D-68). |
| Result | Deactivate: accounts.is_active true → false and nothing else (request_status, review fields, roles, direct permissions, identity, credentials, profile and history untouched); one append-only audit record; access ends on the next request on every device, and every session signed in before the deactivation stays invalid forever, including after a reactivation (D-66). Reactivate: is_active false → true for an Approved, non-protected account that still holds an active role, with one audit record; the user must sign in again. Workspace account status is separate from academic enrollment, which CTU's main system manages. |
| Status | Completed for local development only: Human Approval recorded by the owner (Ronald C. Arias, November 18, 2026); implementation f476294, documentation ce784e8 and 53f0616, final test 85212e4 (local, not pushed). Production account activation and deactivation stay blocked. Stage 3C (18 November 2026): the three school-account permissions, their Admin bindings (active) and nine receipts provisioned in ctug_workspace through the governed command after a verified backup; final verify VERIFIED; P4 compensation preview available and not executed; security checks passed. Stage 3B: committed locally as f476294 (not pushed); read-only verification of ctug_workspace before provisioning. Stage 3A (owner Option A): the P3B snapshot tolerates exactly the governed school-account rows with their receipts and preserves them through P4 compensation. Inspected and reconciled 18 November 2026; stages 1, 2 and 3 owner-authorized the same day. Implemented and tested (uncommitted): service, session epoch, API (mounted only in local review and sandbox), account directory and status controls, the governed companion provisioning command for the three accounts.school_accounts.* codes and the release-safeguard amendment. Stage 3 stopped at an unexpected protected dependency: the registration-review P3B snapshot used by P4 activate/compensate requires exactly the three registration permissions and bindings, so provisioning the school-account rows in ctug_workspace would make the P4 compensation (rollback) path refuse permanently. The command was therefore NOT run against ctug_workspace and nothing was committed. Production stays blocked. |

**Inspection basis:** On 18 November 2026 the owner requested Inspect and Reconcile of WF-02.05 only (no implementation, no WF-02.06). Branch ronald at 4804e7a (fac37a9 WF-02.04, 4804e7a its Human Approval), 6 commits ahead of origin/ronald, not pushed. Prerequisites verified: WF-02.01 to WF-02.04 implemented with Human Approval (Ronald C. Arias, November 17, 17, 18 and 18, 2026; WF-02.04 for local development only). The docs/workflows/group_a documents reported deleted after WF-02.04 were restored from Git and match HEAD. Working tree: only this catalogue modified, holding another editor's uncommitted drafts (header text, WF-05 to WF-11.01, the 0.3.8 change-log row), all preserved. Inspected read-only:
- Backend: accounts/models.py, admin.py and framework_admin_readonly.py, session_auth.py (_workspace_account, LoginView, LogoutView, SessionView), session_timeout.py, registration_review.py (_decide lock order), registration_review_api.py (require_actor), access_control/services.py (has_permission), audit.py, mutations.py, writer_boundary.py, executor protocol.py, engine.py, client.py and schema.py (grants and triggers), the P1/P3C release safeguard (unexpected_review_routes), config/settings.py and security_settings.py, catalogue v2_0.json (permissions, bindings, scope definitions, policy blockers V2-01 to V2-10, operational gates).
- Frontend: features/dashboard/navigation.ts (account-directory entry), the WF-02.01 to WF-02.04 review views, the shared Modal.
- Requirements: SRS v0.4 and v1 (FR-AUTH-03, FR-ADM-01 to FR-ADM-09, the last-effective Super Admin rule, the read-only-DBML rule forbidding a new account-status flag), Use Case Specification v0.4.1 ACT-SA-05.
- Schema: docs/database/full_schema.dbml and the Django models (accounts.is_active is the only status column).
- Read-only development database checks (no identities, transaction rolled back): services accounts and access_control active; only the three registration permissions exist (none of the accounts.school_accounts.* rows); roles Student, Instructor, Treasurer and Admin active, no Technical Super Admin role; 3 Approved accounts, all active (role memberships: 1 Student, 1 Admin; one framework superuser); 0 account permissions; 4 session rows.
- Existing tests run unchanged: test_session_security, test_session_auth, test_permissions and test_framework_admin_readonly, 92 tests passed.

**Reconciliation (requirement → evidence → finding):**
- R-01 Nothing exists yet. No service, API view, URL, executor operation, management command or frontend control activates or deactivates an account. Django Admin exposes accounts strictly read-only (framework superuser inspection, no write). The dashboard registry lists an "Account directory" view (requiredAny accounts.school_accounts.read, integration planned), which opens the ModuleUnavailable state. Verified.
- R-02 Permission codes exist in the catalogue only. catalogue v2 defines accounts.school_accounts.suspend ("Suspend another Student/Instructor account; exclude reserved administrators and restricted provisioning"), accounts.school_accounts.activate ("Reactivate another already Approved Student/Instructor account; never approve a Pending request implicitly") and accounts.school_accounts.read, all readiness P and bound to Admin only. The development database has none of these rows; creating them is a governed metadata change through the protected release tooling (P1/P2/P4 create only the three registration permissions). Verified.
- R-03 Login and every protected request already fail closed on inactive accounts. Django's ModelBackend refuses inactive users at login and when loading the session user; _workspace_account and require_actor additionally require account is_active, request_status Approved and an active role; _authorized_permissions requires the same, active services and no Deny. test_session_security test_deactivation_ends_access_on_the_next_request proves access ends on the next request. Verified.
- R-04 Sessions survive deactivation and can be revived. The session row and cookie are not removed, and SessionTimeoutMiddleware records activity before any view runs, so an open tab that keeps polling keeps the session alive up to the 8-hour absolute limit (D-18). Reactivating the account inside that window would make the old cookie valid again, including on other devices. Django's session hash depends on the password, not on is_active. catalogue operational gate session_revocation is BLOCKED and policy blocker V2-08 (session revocation storage) is OPEN (D-66).
- R-05 Eligibility and protected accounts. The catalogue scope excludes reserved administrators; FR-ADM-02 to FR-ADM-04 and the SRS last-effective Super Admin rule put Admin and Technical Super Admin changes in a separate protected governance process; V2-06 (last-effective operator, lock order) is OPEN and the effective_last_operator gate BLOCKED. Excluding Admin, Technical Super Admin, staff and superuser targets keeps School Admin from disabling administrators, including themselves (D-63, D-71).
- R-06 State model. accounts holds request_status (Pending, Approved, Rejected) and is_active; SRS v0.4 forbids adding an account-status flag without schema approval. Approved accounts are created active by WF-02.03; Pending and Rejected are inactive. Deactivation is therefore only is_active on an Approved account; reactivation is only is_active on an Approved account that still holds an active Student or Instructor base role (otherwise it could not sign in anyway). Verified (D-65).
- R-07 Audit. The existing writer accepts {account_id, is_active, request_status} snapshots with reason account_status_change and a target foreign key; actor, target and server created_at are recorded; no new audit contract is needed for a reason-free event. A reviewer-chosen reason would need a narrow protected audit-allowlist change (as D-52) (D-67). Refusals are not audited (consistent with WF-02.03/02.04).
- R-08 Concurrency. The WF-02.03/02.04 lock order (services, exact permission, actor and target accounts, both accounts' role rows, roles, the actor's role and account permissions, then has_permission inside the lock) applies unchanged and serializes deactivation, reactivation, role changes and permission revocation. A login racing a deactivation can finish just before the commit; the next request fails closed and session revocation removes the session (D-66).
- R-09 Executor and writer boundary. writer_boundary.COVERED_OPERATIONS and the executor protocol contain no account-status operation; the executor accounts UPDATE trigger refuses ordinary-principal updates of any account whose OLD.request_status is Approved; the ordinary executor principal has only SELECT on django_session. A production path therefore needs protected protocol, engine, client, trigger and grant changes; until then the operation must refuse when the protected writer is enabled, as D-51 does for approval (D-69). writer_boundary RELEASE_STATUS stays BLOCKED.
- R-10 Release safeguard gap. The P1/P3C safeguard recognises only registration-review modules, route names and the registration-requests path. A new account-status view in its own module and path would not be refused if mounted in config.urls (D-69).
- R-11 Directory dependency. Finding an approved account needs a minimized read view; WF-02.06 (View account status and permitted history) is not inspected and FR-ADM-06 is P1 (D-70).
- R-12 Workflow relationships. WF-01.03/01.04/01.06 are implemented and approved (login, logout, expiry); WF-02.03 creates the active Approved state; WF-02.04 deletes rejected data (no Rejected rows from it remain); WF-03.01 to WF-03.06 and WF-02.06 are not inspected; WF-09 delivery is gated; WF-12 audit review is not implemented. Account Management (this workflow) stays separate from Access Control Management (WF-03): no role or permission change here.

**Implementation basis (stage 1, 18 November 2026; uncommitted):** The owner reconciled the decisions: D-63 REVISED (deactivate any Approved, non-protected account even without an active role; reactivate only into existing login eligibility with an active operational role; Treasurer-only accounts included where supported; never grant a role to make an account eligible; Pending and Rejected ineligible; administrative and protected accounts excluded); D-64 APPROVED IN PRINCIPLE (the three catalogue codes; rows and bindings only through governed tooling); D-65 APPROVED (only is_active); D-66 SECURITY REQUIREMENT APPROVED (deactivation must end effective access; reactivation must never revive sessions from before the deactivation; deleting session rows not assumed sufficient); D-67 LIMITED APPROVAL (the fixed account_status_change reason; no free text); D-68 APPROVED; D-69 APPROVED WITH PROTECTED GATES; D-70 APPROVED; D-71 APPROVED. Files changed (application level only):
- backend/apps/accounts/account_status.py (new, governance-sensitive): suspend_account and activate_account in one writer_atomic READ COMMITTED transaction with the WF-02.03/02.04 lock order (services, exact permission row, actor and target accounts, both accounts' role rows, roles, the actor's role and account permissions) and has_permission re-checked inside the lock; the actor must be an active, Approved, non-framework account with an active Admin role. Target rules (D-63 revised, D-71): not Approved → the shared denial (404); framework staff/superuser, any Admin or Technical Super Admin assignment (the executor's reserved-role normalization) or the actor → protected_account; a different current state from the confirmed expected_active → state_changed (no change, no audit); reactivation without any active role → no_operational_role. Only is_active is updated (guarded UPDATE) and one audit event account.status.suspend or account.status.activate is written (actor, target, old/new {account_id, request_status Approved, is_active}, reason account_status_change, database created_at). Default-off WORKSPACE_ACCOUNT_STATUS_ENABLED; refused before any read or write while the protected writer is enabled (D-69).
- backend/apps/accounts/models.py (Account._get_session_auth_hash, D-66): Django re-checks the session hash on every request and flushes a mismatching session. The hash is unchanged for accounts never suspended; after a suspension it also binds the primary key of the latest committed account.status.suspend audit row (status_epoch). That row is written in the same transaction as is_active, is append-only and never reused, so every session signed in before the suspension fails the check on its next use, on every device, whether or not its row still exists, including after any later reactivation. No schema change and no session-store privilege.
- backend/apps/accounts/session_auth.py (LoginView, D-66): after login() binds the session to the current epoch, eligibility is re-read from the database; a suspension committed before the epoch was read is seen there (sign-out, 401), and one committed after it changes the epoch, so no interleaving leaves a session that survives reactivation.
- backend/apps/accounts/account_status_api.py and account_status_urls.py (new): GET list (accounts.school_accounts.read; page, q, status; minimized fields account_id, school_id, id_label, full_name, active role names, is_active; no email, credentials, review or session data), GET detail (adds name parts, request_status, created_at and a can_reactivate hint), POST {id}/suspend/ and {id}/activate/ with exactly {"expected_active": bool}; 200 {account_id, is_active}; 409 account_status_conflict with state_changed, protected_account or no_operational_role; 404 request_unavailable for unknown or ineligible accounts. The views subclass RegistrationReviewAPI, so they reuse CSRF, no-store, the Admin pre-check, throttles and error mapping, and the existing P1/P3C release safeguard refuses them if mounted anywhere it inspects. account_status_urls.py is NOT included by config.urls, review_local_urls or review_sandbox_urls.
- frontend/src/features/admin/accountStatusConfig.ts, accountStatusContract.ts, accountStatusApi.ts (new): VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED (default off), strict parsers, confirmed-state plans, one CSRF POST never retried, outcome_unknown for anything possibly applied. AccountDirectoryPanel.tsx, AccountDetailPanel.tsx and AccountStatusBadge.tsx (new): searchable, permission-filtered directory with Active/Inactive in words, read-only detail and roles, Deactivate (destructive confirm) or Reactivate (primary confirm) only with the exact permission, session-termination wording, busy and duplicate-submit guards, a pause after an uncertain result, stale-state reload. features/dashboard/navigation.ts and SessionDashboardPage.tsx: the account-directory view is live only when the switch is on.
- Tests: backend/apps/accounts/test_wf0205_account_status.py (23); frontend/tests/account-status.test.mjs (8) and tests/browser/account-directory-errors.test.mjs (8).
Not changed: config.urls, review_local_urls.py, review_sandbox_urls.py, review_local_settings.py, review_sandbox_settings.py, config/settings.py, the release safeguard and P1–P4, writer_boundary.py, the executor client, protocol, engine and schema, audit.py, migrations, the ERD, permission rows or bindings in any database, real accounts.

**Implementation basis (stage 2, 18 November 2026; uncommitted):** The owner authorized local-development-only stage 2: config/review_local_urls.py, config/review_sandbox_urls.py, config/review_local_settings.py and config/review_sandbox_settings.py to mount the isolated account-status URLconf and enable its switch there only; governed provisioning of exactly accounts.school_accounts.read, .suspend and .activate bound to Admin through P1/P2/P4, or a STOP if the tooling cannot do it; D-66 verification over real HTTP; release-safeguard verification, with a STOP and an exact amendment if it does not reliably detect an unauthorized endpoint; a WF-02.05-only lint baseline exception if the findings are unchanged. Done:
- config/review_local_urls.py and config/review_sandbox_urls.py (protected, authorized): path("api/v1/admin/school-accounts/", include("apps.accounts.account_status_urls")) after the existing review routes. config.urls unchanged.
- config/review_local_settings.py and config/review_sandbox_settings.py (protected, authorized): WORKSPACE_ACCOUNT_STATUS_ENABLED = True; acknowledgement, DEBUG, local-database and loopback guards, cookies, URLconfs, email and outbox settings unchanged. config/settings.py still has no such setting (the switch is absent, therefore off, and not environment-controlled); the protected writer still refuses.
- New tests: backend/apps/accounts/test_wf0205_stage2.py (21).
STOP 1, governed provisioning (required protected change): the P1 command (init_registration_review_metadata_local_dev) creates exactly its frozen PERMISSION_CODES (the three registration_requests codes) once, and refuses when any other catalogue row, any existing grant or override, or earlier P1 audit events exist; the development database has all three. P2 (inactive bindings) and P4 (local activation) are bound to P1's PERMISSION_CODES. The tooling therefore cannot provision the school_accounts codes, and nothing was seeded or bypassed. Proposed protected change: a governed companion sequence for exactly these three codes (for example init_school_accounts_metadata_local_dev, init_school_accounts_inactive_bindings_local_dev and release_school_accounts_local_dev, or the same phases added to P1/P2/P4 behind a separate code set and confirmation phrase): definitions taken from catalogue v2 and verified against it, ctug_workspace and loopback only, a named Approved Admin actor, preconditions that the P1/P2/P4 registration receipts exist, one audit receipt per created row, binding and activation, an exact verify mode, refusal of any other code, role or grant change, and tests mirroring the existing P1/P2/P4 suites.
STOP 2, release-safeguard gap (required protected amendment): unexpected_review_routes detects these views only through their RegistrationReviewAPI base class. It refuses every class-based mount (an include anywhere, a renamed path or name, a csrf_exempt wrapper, a subclass; tested), but an opaque function wrapper around the view is not detected, because no module prefix, route name prefix or path marker covers account-status routes (registration-review routes have the registration-requests path marker as a second layer). Proposed amendment in apps/access_control/management/commands/init_registration_review_metadata_local_dev.py: add "school-accounts" to _REVIEW_NAME_PREFIXES; add "apps.accounts.account_status" to _REVIEW_MODULE_PREFIXES; replace _REVIEW_ROUTE_MARKER with _REVIEW_ROUTE_MARKERS = ("registration-requests", "school-accounts") and test `any(marker in route for marker in _REVIEW_ROUTE_MARKERS)`; plus test_wf0201_release_safeguard cases for an opaque wrapper on a school-accounts path, a function view in an account_status module and a school-accounts route name. A wrapper on an unrelated path, from an unrelated module, stays statically undetectable for every review route; the default-off service gate is the second layer (tested: such a mount answers 503 and writes nothing under production defaults).

**Implementation basis (stage 3, 18 November 2026; uncommitted):** The owner approved a governed companion process for exactly accounts.school_accounts.read, .suspend and .activate (Admin only, as catalogue v2 defines them; P1/P2/P4 principles; ctug_workspace on loopback; a named Approved Admin and valid governance receipts; inactive bindings first; append-only evidence for every phase; no duplicate, conflicting or unauthorized grant; Deny precedence preserved), and a narrow amendment of the release safeguard. Files changed:
- backend/apps/access_control/management/commands/provision_school_accounts_local_dev.py (new, protected governance tooling): phases metadata, bindings and activate (each needs --apply and its exact confirmation: ctug_workspace:WF-02.05:S3:METADATA, …:BINDINGS, …:ACTIVATE; the disposable test database uses WF-02.05:DISPOSABLE-TEST:S3:<PHASE>) and a read-only verify. Each phase: the definitions and Admin-only default bindings are read from the pinned, validated catalogue v2 (validate_manifest) and re-checked before commit; the target is P1's own strict check (one alias, local MySQL, ctug_workspace in DEBUG config.settings or the disposable test DB, READ COMMITTED, registration-review flags off, no unexpected review or account-status route) plus the account-status switch off; the shared governance lock (P1's GET_LOCK) and one durable transaction; the Admin role and the actor locked (P1's actor rule: active, Approved, non-framework Workspace Admin) who must be the attributed registration-review operator; the registration-review release must be complete (2 active services, the 3 registration permissions, P1 5, P2 3 and P4 2+3 receipts, no compensation). Creates exactly 3 permission rows (receipts workspace.school_accounts.permission.create), then 3 inactive Admin bindings granted_by the actor (workspace.school_accounts.role_binding.stage), then activates exactly those (workspace.school_accounts.role_binding.activate, old/new is_active); re-runs only verify; partial, foreign, differing, orphaned or partially active state is refused without repair; account-level Grants for these codes are refused (Denies are allowed and keep precedence); a snapshot of every service, role, other permission, other binding, role assignment and override must be unchanged before commit. Never creates services, roles, role assignments or overrides.
- backend/apps/access_control/management/commands/init_registration_review_metadata_local_dev.py (protected, authorized amendment): _REVIEW_NAME_PREFIXES adds "school-accounts"; _REVIEW_MODULE_PREFIXES adds "apps.accounts.account_status"; the single path marker became _REVIEW_ROUTE_MARKERS = ("registration-requests", "school-accounts"). Nothing is newly tolerated; the registration-review checks are unchanged.
- Tests: backend/apps/access_control/test_wf0205_school_accounts_provisioning.py (7) and 4 new cases in backend/apps/access_control/test_wf0201_release_safeguard.py.
STOP 3, unexpected protected dependency (separate approval required before applying provisioning in ctug_workspace): exercise_registration_review_activation_recovery_test_only._snapshot (P3B), which P4 uses for activate and compensate, requires exactly 3 permission rows and 3 bindings. After the school-account rows exist, P4 compensate refuses ("Unexpected or missing catalogue rows"; tested), and the rows cannot be removed (append-only audit references). Options for the owner: (a) authorize a narrow P3B change that scopes its snapshot to the registration-review codes and treats exactly the governed school-account rows as known; (b) accept that the registration-review P4 compensation path is permanently unavailable once provisioning runs; (c) keep provisioning unapplied. No option was taken.

**Implementation basis (stage 3A, 18 November 2026; uncommitted):** The owner selected Option A conditionally (a narrowly scoped protected P3B compatibility change, only if the original P4 compensation and security guarantees stay intact; otherwise Option C; Option B not authorized). Inspection findings: P3B's exact-count check (2 services, 3 permissions, 3 bindings, no account-level overrides) is the whole-catalogue integrity check for P4 activate and compensate (pre- and post-checks) and for the P3D compensation preview and transition; P4 compensate deactivates only the 3 registration bindings and then the 2 shared services (accounts, access_control) with 3 + 2 receipts, and P4 cannot activate again after a compensation; the companion's 9 receipts (3 per phase) are recorded after the P4 activation and reference the rows, so they cannot be removed; because the accounts service is shared, a compensation also makes the school-account authority ineffective (a fail-closed side effect), and because compensation is one-way, an account deactivated through WF-02.05 would be left with no governed way back. Exact change, in one protected file only (backend/apps/access_control/management/commands/exercise_registration_review_activation_recovery_test_only.py, +77/−4; no change to P1, P2, P3C, P3D, P3E, P4, routes, switches, the executor protocol, engine, client, writer or database triggers):
- _snapshot still locks every service, permission and binding and keeps every original check on the registration scope (exactly 2 services, exactly the 3 registration permissions, P1 audit evidence, exactly the 3 registration bindings to Admin, P2 receipts, no account-level override, the expected Admin scope). The only rows tolerated beyond that scope go through the new _governed_school_accounts: they must be exactly the three accounts.school_accounts.* definitions, identical to the pinned catalogue v2 on the accounts service, and either no bindings or exactly three Admin bindings in one state (all inactive or all active). Each phase is proven by the companion's own receipt verifiers (_verify_metadata, _verify_bindings: exact count, actor, target, old/new values). Every WF-02.05 receipt must be newer than the last registration P4 activation receipt, and binding receipts without bindings are refused. Any other extra row (a fourth or differing permission, a binding to another role, a partial or partially active state, a missing, forged or inconsistent receipt, or rows before the release) still refuses with "Unexpected or missing catalogue rows". With no school-account rows, any school-account binding or receipt is refused.
- The snapshot returns only the registration rows, so P4 compensation deactivates exactly the same 3 bindings and 2 services as before and never touches, deletes or modifies a WF-02.05 row or receipt.
- New compensation precondition (_assert_no_stranded_suspensions, checked on the active pre-check only): refuse while any account's latest account.status.* event is a suspension and the account is still inactive.
- _assert_effective_permissions keeps the exact registration check and adds the school-account codes: effective only for the expected Admin scope, only while all three school bindings and the services are active; never otherwise.
Supported: compensation before provisioning (unchanged) and after each governed phase (definitions; inactive bindings; active bindings), including after repeated provisioning, all with the actual results checked. Refused without any write: every tampered or unauthorized state above, an account-level override (original rule, Deny included), a stranded WF-02.05 deactivation, activation with school-account rows present, a concurrent operation while the shared lock is held, provisioning after a compensation, and a second activation after a compensation. Tests: backend/apps/access_control/test_wf0205_p3b_compatibility.py (new, 17); the obsolete stage-3 dependency test in test_wf0205_school_accounts_provisioning.py was removed (now 6), because Option A changes that behavior by design. Live provisioning in ctug_workspace is still pending (not run).

**Commit and read-only verification (stage 3B, 18 November 2026):** The owner approved the stage 3A implementation on its isolated-database evidence and authorized a local commit followed by read-only verification of ctug_workspace; permission provisioning and production deployment are not authorized. Before the commit: branch ronald at 4804e7a; every modified and untracked file reviewed as WF-02.05 stage 1–3A work; `git diff --check` clean; focused registration-review governance, safeguard, session and WF-02.05 suites 367/367; `manage.py check` no issues; `makemigrations --check --dry-run` no changes; no migration, ERD, config.settings, config.urls or production-release change. Local commit f476294 (not pushed): 28 files, the WF-02.05 code and tests and this catalogue staged as the previous HEAD plus only the WF-02.05 lines (other contributors' drafts left unstaged). Read-only verification of ctug_workspace, after the commit, in config.settings with the documented local profile (DJANGO_DEBUG=1 in that process only; .env unchanged), no --apply and no write phase; the inspection's own checks ran in transactions that were rolled back, and every table checksum and row count (services, permissions, roles, role bindings, account roles, account overrides, audit log, accounts) was identical before and after:
- Target: one alias, django.db.backends.mysql, ctug_workspace on 127.0.0.1:3306 (client localhost), MySQL 8.4.13, READ-COMMITTED, profile local, registration-review flags off, account-status switch absent from config.settings, no unexpected route; the companion's own target check passes. A first attempt without DJANGO_DEBUG=1 was refused by that check as designed; it ran in a server-enforced READ ONLY session.
- Registration-review release: services accounts and access_control active; exactly the three registration permissions, bound only to Admin, all active, granted_by account 3; receipts P1 2 + 3, P2 3, P4 activation 2 + 3, all by account 3; no compensation receipt; no account-level override; roles Student, Instructor, Treasurer and Admin (one active Admin role).
- WF-02.05 state: no accounts.school_accounts.* permission, binding, receipt or account Grant; no account.status.* event; no other catalogue row.
- Operator: account 3 is the attributed registration-review operator (Approved, active, not staff or superuser, Admin only) and passes P1's actor rule; the eligible Admin scope is exactly {3}.
- Companion: the metadata-phase preconditions pass (release complete and attributable, nothing to conflict with, the pinned catalogue v2 defines exactly the three Admin-only codes); --phase verify refuses with "Permission definitions are partial or differ from catalogue v2", the expected answer before the metadata phase.
- P4 compensation: the P3D read-only preview over the new P3B snapshot reports it AVAILABLE for the scope {3}; nothing currently blocks it.

**Governed local provisioning (stage 3C, 18 November 2026):** The owner authorized the controlled execution of provision_school_accounts_local_dev against ctug_workspace, limited to the three definitions, three inactive Admin bindings, their activation, the append-only receipts and the final verification; the owner acknowledged the P4 compatibility limitations (compensation also deactivates the shared accounts service; it is refused while a WF-02.05 deactivation is stranded). No other database change, no P4 compensation and no production deployment were authorized. Run by the agent at HEAD ce784e8 (P3B change committed in f476294; backend and frontend identical to HEAD), each process in config.settings with DJANGO_DEBUG=1 set for that process only (.env and settings unchanged):
- Preconditions re-verified immediately before: target ctug_workspace on 127.0.0.1:3306 (client localhost, MySQL 8.4.13, READ-COMMITTED, profile local, one alias); the companion's target check passes; the registration-review release complete and uncompensated (P1 2 + 3, P2 3, P4 2 + 3 receipts, all by account 3; no deactivation receipt); exactly the three registration permissions and their three active Admin bindings; no school-account permission, binding, receipt or account Grant; no account-level override; no other catalogue row; account 3 Approved, active, not staff or superuser, Admin only, passing P1's actor rule; the pinned catalogue v2 defines exactly the three Admin-only codes.
- Backup: a consistent mysqldump (--single-transaction, routines and triggers) of ctug_workspace taken just before, stored outside the repository in a private ctug_workspace_backups folder in the developer's user profile (ctug_workspace-pre-WF-02.05-S3C-20261118-134846.sql, 39,805 bytes, SHA-256 a46c4c9f7f7a899b595988d10475e8c9b0cb9e1678e11474aae1100b1f45bd58). Restore test: loaded into a disposable database, all 18 tables present with identical row counts and CHECKSUM TABLE values (ctug_workspace has no triggers), the disposable database dropped; credentials were passed through a temporary option file that was deleted and were never printed. The file contains real development data and must not be shared or committed.
- A baseline of everything outside the three codes (services, roles, other permissions and bindings, account roles, overrides, account states and every other audit row) was recorded and proven unchanged after every phase.
- Phase metadata (--apply, ctug_workspace:WF-02.05:S3:METADATA): CREATED; permissions 4 accounts.school_accounts.read ("Read eligible school accounts"), 5 .suspend ("Suspend ordinary school account"), 6 .activate ("Reactivate approved school account"), module school_accounts, service accounts; receipts 16–18 (workspace.school_accounts.permission.create, actor 3); verify VERIFIED; no effective change.
- Phase bindings (…:BINDINGS): CREATED; role bindings 4–6, Admin, inactive, granted_by 3; receipts 19–21 (workspace.school_accounts.role_binding.stage); verify VERIFIED; no account gained any effective permission.
- Phase activate (…:ACTIVATE): ACTIVATED; bindings 4–6 active; receipts 22–24 (workspace.school_accounts.role_binding.activate, old/new is_active); only account 3 (Admin) gained read, suspend and activate.
- Phase verify: VERIFIED. Final state: services 2 active; permissions 6 (3 registration, 3 school-account); bindings 6, all Admin, all active, all granted_by 3; WF-02.05 receipts 3 + 3 + 3 = 9; registration-review receipts unchanged (2 + 3, 3, 2 + 3; no compensation); no override; no account.status.* event; every table outside the three codes unchanged.
- P3B/P4: the P3B snapshot accepts the provisioned state and the P3D read-only compensation preview reports it AVAILABLE for the Admin scope {3}. P4 compensation was not executed.
Post-provisioning security checks without changing any state: effective permissions per account (Admin 3: the three school codes and the three registration codes; Student 6, the framework superuser 2, Pending 7 and Rejected 1: none). In config.review_local_settings (its documented local marker set for that process only) the directory was called over the real data with GET only inside rolled-back transactions, with only the session lookup substituted (no sign-in, so no session or last_login write): Admin 3 lists exactly account 6 and reads its detail; Student 6 is refused 403; the framework superuser is refused 401; self, Pending, Rejected and framework targets are 404. config.urls does not route /api/v1/admin/school-accounts/; config.review_local_urls and config.review_sandbox_urls do; WORKSPACE_ACCOUNT_STATUS_ENABLED is absent from config.settings; the protected writer is off locally. Table and django_session checksums were unchanged. ctug_workspace has no Instructor, Treasurer or Technical Super Admin account, so those cases, a School Admin's own Deny and the protected-writer refusal after provisioning were verified in the disposable test database (new test, below). No real account was deactivated or reactivated.

**Proposals (decided by the owner 18 November 2026 as recorded above; P-03's row deletion was replaced by the session epoch; P-05 is mounted locally; P-06 is implemented as the governed companion command and applied to ctug_workspace in stage 3C; the safeguard amendment is applied):**
- P-01 Service (new apps/accounts/account_status.py, governance-sensitive): suspend_account(actor, target_id, expected_active=True) and activate_account(actor, target_id, expected_active=False), one writer_atomic READ COMMITTED transaction reusing the WF-02.03/02.04 lock order and the in-lock has_permission re-check; checks per the state matrix (D-63, D-65); change only accounts.is_active; record one audit event; refuse with fixed reasons. Gated by a new WORKSPACE_ACCOUNT_STATUS_ENABLED (default off) and refused before any write when the protected writer is enabled (D-69).
- P-02 Audit: action account.status.suspend or account.status.activate, actor = reviewer, target = account, old/new {account_id, request_status: Approved, is_active}, reason account_status_change, created_at from the database; no credential, session or profile data (D-67).
- P-03 Sessions (D-66): keep the existing fail-closed checks; after the suspension commits, delete every django_session row that belongs to the target (decoded _auth_user_id), and do the same before the reactivation commits, so no old cookie is ever restored; no schema change.
- P-04 API (new apps/accounts/account_status_api.py): GET list and GET detail of eligible school accounts (accounts.school_accounts.read; minimized fields: account_id, School/Staff ID, name, base role and extra roles as labels, is_active, request_status; no email unless approved) and POST …/{id}/suspend/ and …/{id}/activate/ with body exactly {"expected_active": <bool>}; 200 {account_id, is_active}; 404 for unknown or ineligible (non-enumerating); 409 account_status_conflict with fixed reasons state_changed, protected_account, no_active_base_role (D-68); 400, 401, 403, 429, 503 as in WF-02.03.
- P-05 Routing (D-69): mount only in the local review and sandbox URLconfs; never config.urls; extend the release safeguard to refuse account-status routes (protected; separate authorization).
- P-06 Metadata (protected; separate authorization): create the three accounts.school_accounts.* permission rows and their Admin bindings through the governed release tooling, not by seeding.
- P-07 Frontend: implement the account-directory view behind VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED (default off) and accounts.school_accounts.read: search and status filter, rows with status text ("Active" / "Inactive", never color only), a detail page with identity, roles (read-only) and status, and Deactivate account (destructive confirm) or Reactivate account (primary confirm) shown only with the exact permission; the shared Modal naming the account and the consequence ("They will be signed out and cannot sign in until reactivated"); busy state, no double submit, uncertain result paused until reload, stale 409 state_changed reloads the account; four widths, three themes.
- P-08 Tests (see Evidence level); P-09 regression; P-10 protected executor parity (later, separate); P-11 reason codes if D-67 chooses them; P-12 WF-02.06 history view stays a separate workflow.
- Not proposed: migrations or ERD changes, new permission codes, an account-status flag, changes to request_status, roles or permissions, deactivating Admin or Technical Super Admin accounts, mounting in config.urls, relaxing release safeguards, or changes to WF-02.01 to WF-02.04.

#### Main flow

1. The reviewer opens the account directory, searches and opens an eligible account.
2. The detail shows identity, roles (read-only) and the current status; the Deactivate or Reactivate control appears only with the exact permission and the switch.
3. The reviewer selects the action; an accessible dialog names the account and states the consequence; the reviewer confirms.
4. The frontend fetches a fresh CSRF token and sends one POST with the confirmed expected state; it never retries.
5. Django checks the gates, session, CSRF, Admin assignment, both services and the exact permission; validates the body; then, in one locked transaction, re-checks the actor, the target's eligibility and the expected state.
6. Django changes only is_active, writes the audit record and commits; suspension then revokes the target's sessions (reactivation revokes them before committing).
7. The frontend shows the new status only after the 200 response and reloads the account.

#### Alternative flows

- A1 Target is Pending or Rejected: not listed; a forged request is 404 (WF-02.03/02.04 own those states).
- A2 Target holds Admin or Technical Super Admin, or is a framework staff/superuser account, or is the actor: 409 protected_account (D-63, D-71); no approved administrative-account workflow exists yet (WF-03 not inspected).
- A3 Reactivation of an account without any active role: 409 no_operational_role; no role is granted to make it eligible (D-63 revised). Deactivating such an account is allowed.
- A4 State changed since the reviewer confirmed (another admin acted, duplicate submission): 409 state_changed; the page reloads; no second audit.
- A5 Actor loses the permission (Deny, revoked grant, inactive role or service): 403/503 before the request, refused inside the lock during it.
- A6 The deactivated user is signed in: their next request on any device is refused, and every session signed in before the deactivation fails the session-hash check forever, so reactivation never revives it; they sign in again (D-66).
- A7 Not released in this mode or the switch off: no controls; the directory shows nothing new.
- A8 Protected writer enabled: 503 review_unavailable until executor parity exists (D-69).

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| 4–5 | Session expired or not a Workspace identity | 401 authentication_required; nothing changed |
| 4–5 | Missing or invalid CSRF token, or untrusted Origin | 403 before any parsing; nothing changed |
| 5 | No Admin assignment, missing, inactive or denied permission | 403 access_denied; nothing changed |
| 5 | Body not exactly {"expected_active": bool} | 400 invalid_request; nothing changed |
| 5 | Unknown, Pending, Rejected or otherwise ineligible target | 404 request_unavailable (non-enumerating); nothing changed |
| 5 | Protected target, no active role for reactivation, or state changed | 409 account_status_conflict (protected_account, no_operational_role, state_changed); nothing changed |
| 5 | Gates off, services inactive, writer boundary or executor unavailable | 503; nothing changed |
| 6 | Audit or update failure | Whole transaction rolls back; is_active unchanged |
| 6 | Session-epoch read fails on a later request (database error) | The request fails closed (503 or signed out); no session is accepted without the check |
| 4, 7 | Network failure or timeout after sending | "We could not confirm the change. Reload the account before trying again."; never retried automatically |
| 5 | More than 20 changes a minute from one address | 429 rate_limited |

#### Links

Depends on: WF-01.03 and WF-01.04 (login and logout), WF-01.06 (session expiry and CSRF), WF-02.03 (creates the active Approved state; shared lock order and Modal), WF-02.04 (rejected data are deleted, so no Rejected rows come from it), WF-02.06 (account status and permitted history, D-70), WF-03 (effective permissions; role and permission changes stay there), the protected writer/executor and the AR-6C release tooling (P1–P4), catalogue v2 (V2-06, V2-08, operational gates).

Feeds: WF-01.03 (an inactive account cannot sign in), WF-02.06 (status history), WF-09 (no notification is proposed; any status-change email needs its own decision), WF-12 (audit review of account.status.* events).

Traceability: SRS v0.4/v1 FR-AUTH-03, FR-ADM-02 to FR-ADM-06 and the last-effective Super Admin rule; Use Case Specification v0.4.1 ACT-SA-05; catalogue v2 accounts.school_accounts.read/suspend/activate; ERD tables accounts, account_roles, access_audit_logs and django_session (no change).

Guidelines: Inspect → Reconcile → Approve → Implement → Test → Commit

AI Agent Guidelines Checklist: ☒ Inspect   ☒ Reconcile   ☒ Approve   ☒ Implement   ☒ Test   ☒ Commit

Checklist scope: Inspect and Reconcile cover the read-only inspection and R-01 to R-12 above. Approve records the owner's 18 November 2026 stage-1, stage-2, stage-3, stage-3A, stage-3B and stage-3C authorizations and the reconciled D-63 to D-71; it is not Human Approval. Implement covers the committed implementation and the stage 3C governed provisioning of ctug_workspace (local development only). Test covers the disposable-database suites, the stage 3C focused and security regression and the read-only checks over the real development data; no real account status was changed, so a live status change in ctug_workspace is left to the owner's Human Approval review. Commit records the local implementation commit f476294, the documentation commits ce784e8 and 53f0616, the stage 3C test commit 85212e4 and the Human Approval documentation commit (none pushed). The full Account Management regression is due at WF-02.06.

Blocked by:
- Human Approval recorded by the owner (Ronald C. Arias, November 18, 2026) for completed local development only. It does not release production account activation or deactivation or close any item below.
- No live status change was performed on actual development accounts; the status endpoints were verified over real data with GET only and the changes in the disposable test database.
- Full Account Management regression remains mandatory at WF-02.06.
- Stage 3A limitations: a registration-review compensation also makes the school-account authority ineffective (shared accounts service; fail-closed), and it is one-way; it is refused while any account deactivated through WF-02.05 is still inactive. The P3A readiness, P3C gate and P3E release-gate reports (activation-only) refuse once school-account rows exist; that is fail-closed and needed only before the P4 activation. Account-level overrides of any code still block compensation (original P3B rule).
- Provisioning sequence (DONE in stage 3C, owner-authorized, run by the agent; recorded for reference): in config.settings with DJANGO_DEBUG=1 set in the process environment (the target check refuses otherwise), with the registration-review operator's account ID (account 3), the read-only check, then the three phases in order: manage.py provision_school_accounts_local_dev --phase verify --actor-account-id <id> (expected to refuse until metadata exists), then --phase metadata --apply --confirm ctug_workspace:WF-02.05:S3:METADATA, --phase bindings --apply --confirm ctug_workspace:WF-02.05:S3:BINDINGS, --phase activate --apply --confirm ctug_workspace:WF-02.05:S3:ACTIVATE, then --phase verify.
- Remaining safeguard limit: an opaque function wrapper on an unrelated path, defined outside the recognized modules and without a recognized route name, stays statically undetectable for every review route; the default-off backend switch and the protected-writer refusal fail closed independently (tested).
- Changed approved-workflow code, for owner awareness: Account._get_session_auth_hash and LoginView's post-login re-check (WF-01.03), required by D-66.
- D-67: a fixed status reason-code catalogue stays a separate proposal. Catalogue V2-06 and V2-08 stay OPEN (WF-02.05 does not depend on them).
- Production stays blocked: no route in config.urls, switch absent from config.settings, writer_boundary RELEASE_STATUS BLOCKED, no executor operation; the provisioning command refuses anything but local development and the disposable test database.
- Lint: `npm run lint` FAILS on the two pre-existing findings only, identical to baseline 4804e7a (ThemeToggle.tsx:17, RegistrationReviewLivePanel.tsx:74; both files unchanged); covered only by the owner's WF-02.05-only baseline exception, not a pass.

Evidence level: Code-verified and automated-test verified in the disposable test database; DB-verified in ctug_workspace for the stage 3C governed provisioning and the read-only checks, 18 November 2026 (branch ronald, implementation f476294). Only the three authorized permissions, their three Admin bindings and nine receipts were written to ctug_workspace; no account state, role or override was changed.
- Stage 1 and 2: test_wf0205_account_status 23/23 and test_wf0205_stage2 21/21 (recorded above).
- Stage 3, test_wf0205_school_accounts_provisioning 7/7, built on the real P1, P2 and P4 code paths: the full sequence creates exactly the three catalogue definitions on the accounts service, three Admin bindings granted_by the operator (inactive, granting nothing, then active), and nine attributable receipts; Admin and Admin+Technical Super Admin gain exactly these codes, Technical Super Admin alone and Student gain none, no access_control code is granted; services, roles, assignments, other bindings and overrides are unchanged; re-runs report ALREADY_COMPLETE and verify reports VERIFIED without new rows or receipts; an account Deny keeps precedence and an account-level Grant is refused; no release, no P4 activation, wrong phase order, wrong or cross-phase confirmations, no --apply, a non-Admin actor, an Admin who is not the operator, and the account-status switch on are all refused without writes; forged, foreign, partial and partially active states are refused without repair; the P4 compensation dependency is demonstrated; end to end through the real local-review configuration with ONLY governed rows: Admin lists accounts, Technical Super Admin alone and Student are refused 403, Technical Super Admin with Admin deactivates, both of the user's sessions lose access, reactivation keeps them invalid, a fresh sign-in works and a stale reactivation is refused 409, with exactly two status audits. (In stage 3A, the dependency test was retired; the remaining 6 pass.)
- Stage 3A, test_wf0205_p3b_compatibility 17/17, on the real P1, P2, P4, P3D and companion code paths: the original compensation without school-account rows; compensation after definitions, after inactive bindings and after active bindings (each with the P3D compensation preview), with the actual results checked: the 2 services and 3 registration bindings inactive, exactly 2 + 3 deactivation receipts, all on registration codes, the school-account rows and their 3, 6 or 9 receipts byte-for-byte unchanged, nobody keeping any registration or school-account authority, and the companion refusing after compensation. Refused with every table and the audit count unchanged: a fourth permission, a binding to another role, a modified definition, a forged, missing or inconsistent receipt, partially active bindings, a partial unattributed definition, school-account rows before the release (P4 itself, with a clean fingerprint, and the P3E gate), an account-level Deny, a stranded WF-02.05 deactivation (permitted again after reactivation), a second activation after compensation, and operations while another session holds the shared lock (serialized; provisioning succeeds afterwards). Repeated provisioning is idempotent (9 receipts) and compensation still works. test_wf0205_school_accounts_provisioning 6/6.
- Protected registration-review suites unchanged and passing: P1 metadata, P2 inactive bindings, P3A readiness, P3B recovery, P3C gate, P3D transition, P3E release gates, P4 local release, metadata, inactive grants, protected candidate, the release safeguard, and the WF-02.05 and registration-review HTTP and boundary suites: 323/323.
- Release safeguard: test_wf0201_release_safeguard 23/23 (19 existing unchanged, 4 new): direct, include (at the expected and another path), renamed path and name, subclass, class-based wrapper, csrf_exempt, opaque wrappers on a school-accounts path or with a school-accounts name, a function view in an account_status module and the read-only list are all refused; the approved registration read routes alone are still allowed; config.urls reports nothing; both local URLconfs are reported; the P1/P3C guard refuses a mounted account-status route; the remaining limit is demonstrated.
- Backend regression: all 83 accounts and access_control test modules 1763/1763 (7 provisioning tests and 4 safeguard cases new). `manage.py check`: no issues. `makemigrations --check --dry-run`: no changes detected.
- Frontend: `npm test` 206/206; `npm run build` passed; `npm run lint` failed only on the two baseline findings (WF-02.05-only exception). `npm run test:registration-ui`: 117/117 on the final run. Two earlier full-suite runs were not clean and are reported: 108/117 while the backend regression ran concurrently (nine 30-second timeouts in WF-01/WF-02.02 tests) and 115/117 alone (two timeouts); every failing file then passed on its own (applicant approval 8/8, rejection 9/9, session expiry 4/4), and no frontend file changed between runs. The suite is timing-sensitive under load; it is not a WF-02.05 regression.
- Stage 3A regression: all 84 accounts and access_control test modules 1779/1779 (1763 before, plus 17 compatibility tests, minus 1 retired dependency test). `manage.py check`: no issues. `makemigrations --check --dry-run`: no changes detected. Frontend not affected in stage 3A (no frontend file changed); stage 3 frontend results stand.
- Stage 3B: local commit f476294; before it the focused suites 367/367, `git diff --check` clean, check and migration check clean. Read-only verification of ctug_workspace (recorded above under stage 3B): target, release, receipts, operator and companion preconditions pass; no school-account rows; verify refuses as expected before metadata; P4 compensation preview available; checksums unchanged.
- Stage 3C: governed provisioning of ctug_workspace (recorded above): metadata CREATED, bindings CREATED, activate ACTIVATED, verify VERIFIED after each phase and at the end; 3 permissions, 3 active Admin bindings, 9 receipts; everything outside the three codes unchanged; compensation preview AVAILABLE. New isolated test test_stage3c_role_coverage_school_admin_deny_and_protected_writer (committed as 85212e4 after the owner's review; focused suites 412/412 before that commit): after the real release and all phases, Admin and Admin+Technical Super Admin hold exactly the three codes; Technical Super Admin alone, Student, Instructor, Treasurer and Student+Treasurer hold none (effective set and has_permission); a School Admin's own Deny on read removes only read and not suspend, and does not affect another Admin; with the protected writer enabled a suspension is refused with WriterBoundaryUnavailable, the target stays active and no audit is written. test_wf0205_school_accounts_provisioning 7/7. Security regression (broader run required because protected authorization state changed): all 84 accounts and access_control test modules, including authentication, session security, the protected writer and executor, the registration-review governance (P1–P4) and the release safeguards, 1780/1780 OK (0 failures, 0 errors, 0 skipped, no timeouts; 566.8 s; 1779 before plus the new stage 3C test). `manage.py check`: no issues. `makemigrations --check --dry-run`: no changes detected. Frontend not affected in stage 3C (no frontend file changed); stage 3 frontend results and the lint exception stand.
- Not verified: a live status change, P4 compensation and any destructive rollback against ctug_workspace (deliberately not run), the protected executor path, production.

Human Approval: ☒ Approved by: Ronald C. Arias  Date: November 18, 2026

Next flow: WF-02.06. Do not start until Approved is ticked.

#### WF-02.06 — View account status and permitted history

| Field | Definition |
| --- | --- |
| Actor / required permission | School Admin (Normal Administrator) with accounts.school_accounts.read, the WF-02.05 directory code (D-72 APPROVED); Technical Super Admin only through an actual, active Admin assignment (effective permissions; no role-name bypass); never Student, Instructor or Treasurer; never a Django staff/superuser bypass. No new permission code, binding or provisioning. |
| Trigger | From the existing Account directory (WF-02.05), the reviewer opens an eligible account; the account detail shows its current status and a "Status history" section. No new navigation item (Dashboard Shell §3.4/§3.5). |
| Preconditions | Gates as WF-02.05 (local review or sandbox, WORKSPACE_ACCOUNT_STATUS_ENABLED on, protected writer off); an active, Approved, non-framework actor with an active Admin assignment, both services active and the exact read permission (account-level Deny wins); the target is an eligible WF-02.05 account (Approved, not framework, no Admin/Technical Super Admin role, not the actor). |
| Result | Read-only: the account's current status (from the account row) and a minimized, paginated history of its own registration approval and activation/deactivation events, with dates and a minimized actor label. Nothing is written; no audit, session or account change. |
| Status | Implemented 18 November 2026 under the owner's approval of D-72 to D-78 (local review and sandbox only, behind the existing default-off WORKSPACE_ACCOUNT_STATUS_ENABLED): detail status dates, one read-only history endpoint and the Account status and Status history sections in the account detail. Focused, real-data read-only and full WF-02 category regression results are recorded under Evidence level. Production stays blocked. Human Approval pending. |

**Inspection basis:** On 18 November 2026 the owner requested Inspect and Reconcile of WF-02.06 only (no implementation, commit or push). Branch ronald at 1b03991 (WF-02.05 implementation f476294, documentation ce784e8 and 53f0616, test 85212e4, Human Approval 1b03991), 11 commits ahead of origin/ronald, not pushed. Prerequisites verified in this catalogue: WF-01.01 to WF-01.06 and WF-02.01 to WF-02.05 carry Human Approval (Ronald C. Arias, 16 to 18 November 2026); WF-02.03, WF-02.04 and WF-02.05 are approved for local development only. Working tree: only this catalogue modified, holding another editor's uncommitted drafts (header text, WF-05 to WF-11.01, the 0.3.8 change-log row), all preserved. Read-only database checks of ctug_workspace (no write). Inspected:
- Documents: this catalogue; docs/SRS/CTU-G_Workspace_SRS_v0.4_UPDATED.md (v0.4, 17 Nov 2026, latest) and docs/SRS/CTU-G_Workspace_SRS_v1.md (file name v1, header still "Version 0.3", 7 Nov 2026: a version-label conflict); docs/use_case_upecification/CTU-G_Workspace_Use_Case_Specification_v0.4.1.md (v0.4.1, 17 Nov 2026); docs/design/CTU-G_Workspace_Dashboard_Shell_and_Role-Based_Navigation_Design_v0.1.md (v0.1, 17 Nov 2026); docs/design/TOKENS.md, COMPONENTS.md, PATTERNS.md, AUDIT.md (baseline 16 Nov 2026); docs/architecture/AR-3A-administrator-architecture-finalization.md and AR-3B2A-permission-catalogue-v2-proposal.md; docs/security/ACCESS_CONTROL_GATES.md and SECURITY_PRIVACY_OPERATIONS_GATES_DRAFT.md; docs/database/full_schema.dbml and schema.dbml (official ERD); backend/apps/access_control/catalogue/v2_0.json (pinned catalogue v2, planning_only, "no live grant or security-policy approval"). No Figma or FigJam file is in the repository (docs/README.md only names "Figma/FigJam sources"); the design was reconciled against the repository design documents only.
- Code: apps/accounts/account_status.py, account_status_api.py, account_status_urls.py, models.py (Account), registration_review.py (approval/rejection audit), reapplication.py; apps/access_control/models.py (AccessAuditLog), audit.py (allowlisted snapshots), services.py; frontend/src/features/admin/AccountDirectoryPanel.tsx, AccountDetailPanel.tsx, AccountStatusBadge.tsx, accountStatusApi.ts, accountStatusContract.ts; frontend/src/features/dashboard/navigation.ts.

Documentation traceability:

| Document (path, version) | Requirement or section | Role | Impact on WF-02.06 | Missing or conflicting |
| --- | --- | --- | --- | --- |
| docs/use_case_upecification/…_v0.4.1.md (0.4.1) | ACT-SA-05 "Activate/deactivate eligible existing account", mapped to WF-02.05–06 | School Admin | WF-02.06 is the read side of ACT-SA-05 | No separate history use case; visibility rules not defined |
| docs/SRS/…_v0.4_UPDATED.md (0.4) | FR-ADM-06 (P1): inspect eligible accounts' assigned roles and effective abilities, no governance interfaces | School Admin | Roles are shown (read-only); "effective abilities" is a WF-03 inspection (access_control.school_access.inspect) | Effective-ability view not in WF-02.06 scope |
| same | FR-AUD-01/03/04/05, OD-07; §"Authentication event logs" | School Admin, Super Admin | Audit access must exclude hashes, tokens, session secrets and full bodies; the School Admin auth-log view is redacted and separate | Authentication events have no event source (V2-08 OPEN); not part of WF-02.06 |
| same | FR-ADM-05, NFR-PRV-01, NFR-OPS-01, OD-14; schema rule (no status flag or new table without approval) | All | Data minimization; no schema change; audit retention undefined | Audit retention policy missing |
| docs/design/…Dashboard_Shell…_v0.1.md (0.1, proposed) | §3.4 School Admin: Account operations → Account directory; §3.5 Super Admin: inherited School operations, plus Security & audit → Access audit logs | School Admin, Super Admin | History belongs inside the Account directory detail; Access audit logs stay a separate governance module (WF-12) | Route URLs and audit UI permissions listed as open decisions |
| docs/design/PATTERNS.md, COMPONENTS.md, TOKENS.md, AUDIT.md | Detail `<dl>`, empty state (§5.2), tables, 44px targets, 360/768/1024/1440 widths, three themes, sentence case; StatusBadge text names the state; School Admin never sees Security & audit groups | All dashboard users | Reuse AccountDetailPanel, AccountStatusBadge, Modal-free read view; EmptyState/Skeleton are proposed components | EmptyState and Skeleton do not exist yet |
| docs/architecture/AR-3B2A…v2-proposal.md (v2.0-review-1, proposed) and catalogue/v2_0.json | accounts.school_accounts.read (Admin, SCHOOL, GOV); access_control.audit.school.read (Admin, SCHOOL_AUDIT, GOV: "scoped ordinary school-account/assignment security changes … exact visibility rules unresolved"); access_control.audit.read (Technical Super Admin, GOV) | Admin, Technical Super Admin | Candidate codes for the history (D-72) | SCHOOL_AUDIT visibility rules unresolved; operational gates object_authorization and authentication_events BLOCKED |
| docs/database/full_schema.dbml, schema.dbml (official ERD) | accounts (created_at, reviewed_at, reviewed_by, is_active, request_status); access_audit_logs (actor, target, role, permission, action, old/new JSON, reason, created_at) | — | All data exists; no migration needed | No account-status history table (none may be added) |
| This catalogue: WF-02.03, WF-02.04, WF-02.05, D-45, D-54 to D-71 | Approval attestation in audit; rejection deletes data (audit keeps only the ID); status audit events; directory scope D-70 | School Admin | Defines which events exist and what they contain | — |

Findings:
- R-01 Status already shown. WF-02.05's detail (GET …/school-accounts/{id}/) returns identity, roles, is_active, request_status "Approved" and created_at under accounts.school_accounts.read; the directory filters Active/Inactive. WF-02.06 must not duplicate it; it adds only the status dates and history.
- R-02 Registration versus activation. request_status (Pending/Approved/Rejected) is the registration decision; is_active is the account's ability to sign in; neither is CTU enrollment (CTU's main system stays the authority). Only Approved accounts are eligible, so the directory never shows Pending or Rejected states.
- R-03 Available history events (actual writers): account.registration.approve (WF-02.03; actor reviewer, target applicant, role_id, plus the D-45 attestation fields), account.status.suspend and account.status.activate (WF-02.05; old/new {account_id, request_status, is_active}, reason account_status_change), account.registration.reject (WF-02.04; target NULL, ID only in the snapshot, account and profile deleted), account.registration.reapply (Task 1; Pending stage). Everything else is governance or release evidence (workspace.review.*, workspace.school_accounts.*, workspace.bootstrap.*, technical_admin.*, role/permission changes).
- R-04 Deleted accounts. Rejected accounts are deleted and their audit keeps no target reference; approved accounts cannot be deleted (audit FKs are PROTECT). WF-02.06 therefore has no deleted-account history to show; that record belongs to the protected audit review (WF-12).
- R-05 Legacy gaps (ctug_workspace, read-only): Approved accounts 2, 3 and 6 have no approval or status audit events; reviewed_at is set only for account 3. The UI must say "Not recorded" rather than infer dates, and the current status must come from the account row, never from the history.
- R-06 Permission choice. accounts.school_accounts.read ("List approved school-account fields …; exclude credentials, governance operators and unrelated confidential records") is active for Admin in ctug_workspace. access_control.audit.school.read is the catalogue's school audit projection but its visibility rules are unresolved, it is not provisioned, and provisioning it would add a fourth extra permission that the P3B snapshot refuses (stage 3A tolerates exactly the three school-account codes), so it would need another protected P3B change (D-72).
- R-07 Actor disclosure. Actors of these events are administrators (protected accounts the read code must not expose). Proposed: "You" when the viewer is the actor, otherwise "An administrator"; full attribution stays in the protected audit (D-73).
- R-08 Field minimization. Never return old/new JSON, reason, attestation fields, role or permission IDs, email, session data, or other accounts' identities (FR-AUD-05).
- R-09 Authorization. Same server-side chain as WF-02.05 (session, Admin assignment, both services, exact permission with Deny precedence, active Approved non-framework actor); inactive actors and disabled services refused; Technical Super Admin only through an Admin assignment; School Admin gains no access-control authority.
- R-10 Enumeration. Same eligibility queryset as WF-02.05 and the same non-enumerating 404 for unknown, ineligible, protected or self targets; the same list throttle.
- R-11 Query and indexing. access_audit_logs has a FK index on target_account_id; filtering one target and three actions ordered by access_audit_log_id (newest first) is bounded and index-assisted; no new index or migration. Page size 20, page bounded as in WF-02.05.
- R-12 Retention. No audit retention policy exists (NFR-OPS-01, catalogue D10, V2-08 OPEN); the view shows what is recorded and never deletes or rewrites audit rows.
- R-13 Navigation. No new module or link: the Account directory group stays the entry; School Admin never sees Security & audit (PATTERNS); Super Admin's Access audit logs (access_control.audit.read, "planned") stay WF-12.
- R-14 Release surface. A new GET route under the already-mounted isolated URLconf (api/v1/admin/school-accounts/{id}/history/) or an extended detail response; the release safeguard already recognizes the school-accounts name and module prefixes; config.urls, config.settings and the protected writer stay unchanged (D-76).

**Implementation basis (18 November 2026):** The owner approved implementation with D-72 to D-78: D-72 APPROVED (reuse accounts.school_accounts.read; no new code, binding or provisioning; WF-02.05 authorization and eligibility reused; Deny precedence and the School Admin / Technical Super Admin boundaries preserved; no access-control or security audit exposure); D-73 APPROVED ("You" for the viewer's own actions, otherwise "An administrator", generated server-side from the trusted session; no names, e-mails, School IDs, account IDs or governance detail); D-74 APPROVED (exactly account.registration.approve, account.status.suspend and account.status.activate; only event type, fixed description, time, actor label and, for status changes, the recorded previous/new active state; enforced by the server); D-75 APPROVED WITH CLARIFICATION (current status from accounts.is_active, registration state from accounts.request_status, approval time reconciled from the approval audit and reviewed_at without inventing a date, last status change from the latest allowlisted status event, "Not recorded" otherwise; history never decides the current state); D-76 APPROVED (extend the WF-02.05 detail; exactly one read-only history endpoint in the authorized school-accounts URLconf under the existing switch and gates; 20 per page, deterministic newest first, the existing pagination conventions, no enumeration, no write endpoint; Account status and Status history sections in AccountDetailPanel; no new navigation module); D-77 APPROVED (rejected or deleted applicants, reapplication, protected administrator accounts, governance, role and permission management, authentication and session events and raw audit records stay out; WF-12 keeps them); D-78 APPROVED CONDITIONALLY (lint against the pre-WF-02.06 baseline; a WF-02.06-specific exception only for the same two unchanged findings). No protected file needed changing: the history route sits in the already-authorized isolated URLconf, which the release safeguard already recognizes. Files changed:
- backend/apps/accounts/account_status_api.py: HISTORY_EVENTS allowlist (the three actions with fixed event types and descriptions); _history_rows (one query: target, allowlisted actions, newest first by the append-only access_audit_log_id, only five columns); _actor_label ("You" when actor_account_id equals the session account, otherwise "An administrator"); _history_entry (previous/new active state only when the audit row itself recorded booleans matching the event, otherwise null; never inferred); _approved_at (the latest approval audit created_at, else reviewed_at, else null); detail adds approved_at and last_status_change and takes request_status from the row; new SchoolAccountHistoryView (GET/HEAD/OPTIONS; the WF-02.05 gate, ReviewListThrottle, require_actor(accounts.school_accounts.read), only the page query field, the same eligible_accounts queryset and the same 404; {results, page, page_size 20, has_next}).
- backend/apps/accounts/account_status_urls.py: one route, <int:account_id>/history/ named school-accounts-history (reported by the release safeguard in config.review_local_urls and config.review_sandbox_urls; absent from config.urls).
- frontend/src/features/admin/accountStatusContract.ts: StatusHistoryEntry/StatusHistoryPage types; buildAccountHistoryRequest (page only); parseHistoryEntry (exact keys per event, the fixed description, the two actor labels, consistent states); parseHistoryPage; parseAccountDetail requires approved_at (timestamp or null) and last_status_change (a status event or null).
- frontend/src/features/admin/accountStatusApi.ts: getSchoolAccountHistory (switch first, one GET, never retried).
- frontend/src/features/admin/AccountDetailPanel.tsx: Account information keeps identity, roles and creation date; a new Account status section (status in words, registration, Approved on, Last status change, "Not recorded"); a Status history section (`<section aria-labelledby>`, `<ol aria-label="Status history">` of `<time>` entries with "By you"/"By an administrator" and "Active to Inactive", a polite count, "Show older entries" that loads one page at a time, loading, empty, denied, not-found, unavailable and connection states with Try again where useful, a failed older page that keeps the shown entries); after a confirmed status change the detail and history are re-read from Django; the "Account history is a separate view" line removed. No new navigation item.
- Tests: backend/apps/accounts/test_wf0206_account_history.py (new, 12); test_wf0205_account_status.py (the exact detail key set and the route count 4 → 5 updated to the new contract); test_wf0201_release_safeguard.py (two history mount shapes added to the refusal matrix); frontend/tests/account-status.test.mjs (5 new); frontend/tests/browser/account-directory-errors.test.mjs (the mock serves the new fields and /history/ and remembers confirmed changes; 5 new tests; the 4-width × 3-theme contrast test also covers a full history page).

**Proposals (approved by the owner 18 November 2026 as D-72 to D-78 and implemented as recorded above):**
- P-01 Detail additions (backend/apps/accounts/account_status_api.py, SchoolAccountDetailView): add approved_at (account.reviewed_at, null when not recorded) and last_status_change {changed_at, is_active, actor: "you"|"administrator"} or null, from the latest account.status.* event for the target. Current status stays account.is_active.
- P-02 History endpoint (new SchoolAccountHistoryView in account_status_api.py; one route school-accounts-history in account_status_urls.py): GET …/school-accounts/{id}/history/?page=n under the same gate, throttle and require_actor(accounts.school_accounts.read) (or the D-72 code), the same eligibility and 404; response {results: [{event: "registration_approved"|"account_deactivated"|"account_reactivated", occurred_at, actor: "you"|"administrator"}], page, page_size: 20, has_next}; allowlisted actions only (D-74); newest first by access_audit_log_id; nothing written.
- P-03 Frontend (frontend/src/features/admin/AccountDetailPanel.tsx; accountStatusApi.ts; accountStatusContract.ts): an "Account status" `<dl>` with Active/Inactive (AccountStatusBadge text), "Approved on" and "Last status change" ("Not recorded" when absent), and a "Status history" section: an ordered list of `<time>` entries in sentence case, "Load more" for the next page, a loading state, an empty state ("No status changes have been recorded for this account."), a permission-denied and an unavailable state, the 404 state reusing the WF-02.05 message; no new navigation item; remove the "Account history is a separate view" line. Four widths, three themes, keyboard and screen-reader checks.
- P-04 Tests (Evidence level) and the full WF-02 category regression (below).
- Not proposed: migrations or ERD changes, new permission codes, status-history tables, showing rejected or deleted accounts, governance or authentication events, effective-permission inspection (WF-03), Access audit logs (WF-12), changes to WF-02.01 to WF-02.05 behavior, config.urls or production settings.

#### Main flow

1. The reviewer opens the Account directory and selects an eligible account (WF-02.05).
2. The detail loads; Django checks the gate, session, Admin assignment, services, exact permission and eligibility.
3. The page shows identity, roles (read-only), the current status, "Approved on" and "Last status change".
4. The frontend requests the first history page; Django returns only the allowlisted events for that account, newest first, with minimized actor labels.
5. The reviewer reads the history and may load further pages; nothing is changed or audited.

#### Alternative flows

- A1 No recorded history (legacy or never changed): the empty state; current status still shown from the account.
- A2 Status changed in another tab: the detail and history reload after a WF-02.05 change; a stale page never infers state from history.
- A3 Actor loses the read permission, a Deny is added, the actor is deactivated or a service is disabled: 403 or 503 on the next request; no data is returned.
- A4 Target becomes ineligible (gains an Admin role) or does not exist: 404 request_unavailable, without revealing why.
- A5 Gate off or protected writer on: no controls and no data (503 review_unavailable or the feature hidden).
- A6 Technical Super Admin without an Admin assignment: 403; with one: the same view as School Admin.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| 2, 4 | Session expired or not a Workspace identity | 401 authentication_required; nothing shown |
| 2, 4 | No Admin assignment, missing, inactive or denied permission | 403 access_denied |
| 2, 4 | Unknown, ineligible, protected or self target | 404 request_unavailable (non-enumerating) |
| 4 | Invalid or unsupported query (page out of range, extra fields) | 400 invalid_request |
| 2, 4 | Gate off, services inactive, writer boundary unavailable | 503 review_unavailable |
| 4 | Too many requests | 429 rate_limited |
| 4 | Network failure | "We couldn't load the history. Try again."; the status section stays visible |

#### Links

Depends on: WF-01.03, WF-01.04 and WF-01.06 (session, logout, expiry), WF-02.03 (approval event and reviewed_at), WF-02.04 (rejected accounts deleted; no history to show), WF-02.05 (directory, detail, eligibility, status events, gate and provisioning), WF-03 (roles and effective-permission inspection stay there), catalogue v2 (accounts.school_accounts.read, access_control.audit.school.read, SCHOOL_AUDIT, V2-08).

Feeds: WF-12 (the protected audit review keeps full attribution, deleted-account and governance records), WF-09 (no notification proposed).

Traceability: Use Case Specification v0.4.1 ACT-SA-05; SRS v0.4 FR-ADM-05/06, FR-AUD-01/03/05, NFR-SEC-01/03, NFR-PRV-01, NFR-OPS-01, OD-07/14; Dashboard Shell v0.1 §3.4/§3.5; catalogue v2 accounts.school_accounts.read and access_control.audit.school.read; ERD tables accounts and access_audit_logs (no change).

Full WF-02 category regression plan (mandatory after implementation, before WF-02.06 acceptance; not run in this inspection):
- Focused WF-02.06 (disposable MySQL): detail additions and history for Admin, Admin+Technical Super Admin, Technical Super Admin alone (403), Student, Instructor and Treasurer (403), Deny precedence on the read code, inactive actor, inactive service, gate off, protected writer on, framework superuser (401), self/protected/Pending/Rejected/unknown targets (404), only allowlisted events and fields (no JSON, reason, attestation, IDs or other identities), actor labels, legacy accounts without events, pagination bounds and order, concurrency with a status change (READ COMMITTED), no writes (audit and session counts unchanged), query count bounded, release safeguard for the new route, config.urls not routing it.
- Backend, every module of accounts and access_control and the remaining apps (currently 1780 tests across 84 modules): registration and email verification (WF-01.01/01.02), login, logout and session security (WF-01.03/01.04/01.06), password reset (WF-01.05), pending list and review (WF-02.01/02.02), approval and rejection with the outbox (WF-02.03/02.04), activation and deactivation and the D-66 session epoch (WF-02.05), dynamic authorization and Deny precedence, governance P1–P4, P3B compatibility and the release safeguards; `manage.py check`; `makemigrations --check --dry-run`.
- Frontend: `npm test` (all unit suites), `npm run test:registration-ui` (all browser suites at 360, 768, 1024 and 1440px in light, dark and system themes, including the account-directory suite), `npm run build`, `npm run lint`. Lint baseline exceptions are reported separately; the WF-02.05 exception does not carry over (D-78). Flaky or timed-out browser tests are reported as such.
- Read-only checks over ctug_workspace (GET only, rolled back, checksums unchanged), as in WF-02.05 stage 3C.

Guidelines: Inspect → Reconcile → Approve → Implement → Test → Commit

AI Agent Guidelines Checklist: ☒ Inspect   ☒ Reconcile   ☒ Approve   ☒ Implement   ☒ Test   ☐ Commit

Checklist scope: Inspect and Reconcile cover the read-only inspection, the traceability table and R-01 to R-14 above. Approve records the owner's 18 November 2026 approval of D-72 to D-78 (D-75 with clarification, D-78 conditional); it is not Human Approval. Implement covers the files listed under Implementation basis (local review and sandbox only). Test covers the focused suites, the read-only checks over the real development data and the full WF-02 category regression recorded under Evidence level. Commit is recorded when the local commit exists.

Blocked by:
- Human Approval (owner) for completed local development.
- Production stays blocked as for WF-02.05: no route in config.urls, switch absent from config.settings, protected writer refuses account-status changes (the read-only history writes nothing); WF-02.05 production activation and deactivation also stay blocked.
- access_control.audit.school.read and the SCHOOL_AUDIT projection stay unused (catalogue visibility rules unresolved); full attribution, deleted-account, governance and authentication records remain WF-12 (D-77; V2-08 OPEN).
- Legacy accounts without approval or status audit events show "Not recorded" (ctug_workspace account 6); no date is reconstructed.
- Lint: `npm run lint` FAILS on the two pre-existing findings only, identical to the pre-WF-02.06 baseline 1b03991 (ThemeToggle.tsx:17 error no-useless-assignment, RegistrationReviewLivePanel.tsx:74 warning react-hooks/exhaustive-deps; both files unchanged); covered only by the owner's WF-02.06-specific exception (D-78), not a pass; the WF-02.05 exception was not carried forward.
- Audit retention policy undefined (NFR-OPS-01, V2-08 OPEN).
- No Figma or FigJam reference available in the repository.

Evidence level: Code-verified and automated-test verified in the disposable test database; read-only verified over the ctug_workspace data, 18 November 2026 (branch ronald, base 1b03991). Inspection: documentation and read-only database queries (audit actions present, FK indexes on access_audit_logs, legacy accounts without approval or status events).
- Focused backend, test_wf0206_account_history 12/12: status dates from the approval audit, then reviewed_at, then null, never from history (a row change is not overridden by history); exactly the three allowlisted events for the target, newest first, exact keys, fixed descriptions, "You"/"An administrator" swapped for another administrator, states only when recorded and consistent; reapplication, role-assignment, governance and other accounts' events excluded; no attestation, reason, JSON, IDs, School IDs or e-mail in any response; empty history for legacy accounts; 45 events paginate 20/20/5/0 with has_next and the exact pk order; invalid, repeated or extra query fields 400; anonymous 401; Student, Instructor, Treasurer and Technical Super Admin alone 403; Admin+Technical Super Admin 200; a Deny on read refuses history and detail, a Deny on suspend does not; framework superuser 401; inactive service or gate off 503; inactive reviewer 401; Pending, Rejected, Admin, Technical Super Admin, framework, self, unknown and zero targets share the detail's single 404 body; POST, PUT, PATCH and DELETE 405; no application-table write (only the WF-01.06 session idle-time bookkeeping); query count independent of history length; the 60/min list throttle; the route only in the isolated URLconf and both local URLconfs, reported by the safeguard, never in config.urls; consistent reads while a suspension commits concurrently. With the affected suites (WF-02.05 account status and stage 2, release safeguard, provisioning, P3B compatibility, sandbox boundary, routing, session auth and security): 162/162.
- Read-only over ctug_workspace (config.review_local_settings, GET only inside rolled-back transactions, only the session lookup substituted, table and django_session checksums unchanged): history of Student 6 for Admin 3 is HTTP 200 with no entries, its detail has approved_at null and last_status_change null ("Not recorded"); self, Pending, Rejected and framework targets 404; Student 6 is refused 403.
- Frontend: `npm test` 211/211 (account-status 13/13, 5 new); `npm run build` passed; `npm run lint` failed only on the two baseline findings (WF-02.06-specific exception, D-78). Browser account-directory suite 13/13 (5 new: legacy Not recorded and empty history; dated status and newest-first history with labels only; older entries on request with a kept list after a failed page and keyboard activation; denied, not-found, unavailable and connection states with the status still visible and Try again; detail and history re-read after a confirmed change), and the 360/768/1024/1440px × Light/System-dark/Dark contrast and overflow test including a full history page.
- Full WF-02 category regression (mandatory closing run): every backend test module (85: WF-01 registration, e-mail verification, login, logout, session security and password reset; WF-02.01 to WF-02.06; dynamic permissions and Deny precedence; governance P1–P4, P3B compatibility and the release safeguards; the protected writer and executor) 1792/1792 OK (0 failures, 0 errors, 0 skipped; 873.8 s; 1780 before plus 12 WF-02.06). `manage.py check`: no issues. `makemigrations --check --dry-run`: no changes detected. Frontend `npm test` 211/211, `npm run build` passed, `npm run lint` only the two baseline findings (WF-02.06 exception).
- Full browser regression (`npm run test:registration-ui`, all 12 browser suites, 360/768/1024/1440px in Light, System-dark and Dark where the suites cover them), run alone after the backend: first run 121/122. The one failure was the WF-02.03 applicant-approval contrast check (System-dark, 1024px, dialog title "Approve application" measured 4.27:1 against the 4.5:1 limit); no file it uses changed (Modal, CSS, approval panels, harness and probe identical to HEAD), and that suite then passed 8/8 twice on its own. Full rerun: 122/122 (0 failures, 0 timeouts). Recorded as a timing-sensitive contrast measurement, not a WF-02.06 regression.
- Not verified: production, the protected executor path, a live status change on real accounts.

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-03.01. Do not start until Approved is ticked.

### WF-03  Access Control Management

#### WF-03.01 — Assign or revoke account roles

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-03.02. Do not start until Approved is ticked.

#### WF-03.02 — Manage role-based permission assignments

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-03.03. Do not start until Approved is ticked.

#### WF-03.03 — Grant account-specific permission

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-03.04. Do not start until Approved is ticked.

#### WF-03.04 — Deny or revoke account-specific permission

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-03.05. Do not start until Approved is ticked.

#### WF-03.05 — Evaluate effective permissions and service state

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-03.06. Do not start until Approved is ticked.

#### WF-03.06 — Record and review access-control changes

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-04.01. Do not start until Approved is ticked.

### WF-04  Profile Management

#### WF-04.01 — View own profile

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-04.02. Do not start until Approved is ticked.

#### WF-04.02 — Request or update profile information

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-04.03. Do not start until Approved is ticked.

#### WF-04.03 — Change account password

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-04.04. Do not start until Approved is ticked.

#### WF-04.04 — Update email address

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-04.05. Do not start until Approved is ticked.

#### WF-04.05 — Upload or replace profile picture

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-05.01. Do not start until Approved is ticked.

### Group B - Campus Service Workflows

### WF-05  Academic Information

#### WF-05.01 — View authorized academic information

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-05.02. Do not start until Approved is ticked.

#### WF-05.02 — View assigned subjects (instructor)

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-05.03. Do not start until Approved is ticked.

#### WF-05.03 — View enrolled students where authorized

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-05.04. Do not start until Approved is ticked.

#### WF-05.04 — Obtain or verify academic status from CTU main system

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-06.01. Do not start until Approved is ticked.

### WF-06  Clearance Management

#### WF-06.01 — Request clearance

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-06.02. Do not start until Approved is ticked.

#### WF-06.02 — Verify clearance eligibility and requirements

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-06.03. Do not start until Approved is ticked.

#### WF-06.03 — Review and decide assigned clearance items

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-06.04. Do not start until Approved is ticked.

#### WF-06.04 — Track clearance progress and decisions

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-06.05. Do not start until Approved is ticked.

#### WF-06.05 — Generate an authorized clearance PDF

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-07.01. Do not start until Approved is ticked.

### WF-07  SSG Financial Management

#### WF-07.01 — Verify academic-period fee eligibility

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-07.02. Do not start until Approved is ticked.

#### WF-07.02 — Assess organizational fee obligation

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-07.03. Do not start until Approved is ticked.

#### WF-07.03 — Record and validate payments

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-07.04. Do not start until Approved is ticked.

#### WF-07.04 — Generate and view authorized receipts

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-07.05. Do not start until Approved is ticked.

#### WF-07.05 — Record and categorize expenses

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-07.06. Do not start until Approved is ticked.

#### WF-07.06 — View balances, payment status, and history

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-07.07. Do not start until Approved is ticked.

#### WF-07.07 — Prepare authorized financial reports

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-07.08. Do not start until Approved is ticked.

#### WF-07.08 — Process returning, transferee, and newcomer scenarios

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-09.01. Do not start until Approved is ticked.

### WF-08  Group Rating

Not yet inspected. Scope evidenced in SRS v0.5, FR-RAT-01–FR-RAT-04: assigned-class rating sheets, student group invitations, safeguards for group ratings, and privacy-scoped results. These are requirements for later reconciliation, not implementation claims or approved workflow definitions.

Workflow IDs: Not assigned. Actor(s) and exact permissions: Unknown – needs confirmation. Main flow, alternatives, errors, links, and checklist footer will be added when the project owner defines the individual Group Rating workflows. No WF-08 subflow has been approved.

### WF-09  Announcements & Notifications

#### WF-09.01 — Create and publish announcements

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-09.02. Do not start until Approved is ticked.

#### WF-09.02 — View announcements

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-09.03. Do not start until Approved is ticked.

#### WF-09.03 — Generate event-based in-app notifications

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-09.04. Do not start until Approved is ticked.

#### WF-09.04 — Send eligible email notifications

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-09.05. Do not start until Approved is ticked.

#### WF-09.05 — View notification history and delivery status

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-10.01. Do not start until Approved is ticked.

### WF-10  Account Concerns & Support

#### WF-10.01 — Submit account concern

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-10.02. Do not start until Approved is ticked.

#### WF-10.02 — Assign or review concern

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-10.03. Do not start until Approved is ticked.

#### WF-10.03 — Respond to concern

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-10.04. Do not start until Approved is ticked.

#### WF-10.04 — Track concern status and resolution

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-11.01. Do not start until Approved is ticked.

### Group C - System Operations & Maintenance

### WF-11  System Administration & Configuration

#### WF-11.01 — Manage authorized academic-period settings

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-11.02. Do not start until Approved is ticked.

#### WF-11.02 — Manage system operational settings

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-11.03. Do not start until Approved is ticked.

#### WF-11.03 — Configure services within authorized boundaries

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-11.04. Do not start until Approved is ticked.

#### WF-11.04 — Review operational configuration changes

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-12.01. Do not start until Approved is ticked.

### WF-12  Audit, Security & Monitoring

#### WF-12.01 — Record security-relevant events

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-12.02. Do not start until Approved is ticked.

#### WF-12.02 — Review authorized audit records

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-12.03. Do not start until Approved is ticked.

#### WF-12.03 — Detect and respond to unauthorized attempts

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-12.04. Do not start until Approved is ticked.

#### WF-12.04 — Monitor system health and error conditions

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-12.05. Do not start until Approved is ticked.

#### WF-12.05 — Apply data retention, backup, and recovery controls

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-13.01. Do not start until Approved is ticked.

### WF-13  Reporting & Document Generation

#### WF-13.01 — Generate authorized operational reports

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-13.02. Do not start until Approved is ticked.

#### WF-13.02 — Export permitted records

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-13.03. Do not start until Approved is ticked.

#### WF-13.03 — Generate official system documents

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-13.04. Do not start until Approved is ticked.

#### WF-13.04 — Check report accuracy and access scope

| Field | Definition |
| --- | --- |
| Actor / required permission | Not yet inspected |
| Trigger | Not yet inspected |
| Preconditions | Not yet inspected |
| Result | Not yet inspected |
| Status | Not yet inspected |

#### Main flow

Not yet inspected.

#### Alternative flows

Not yet inspected.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| Not yet inspected | Not yet inspected | Not yet inspected |

#### Links

Depends on: Not yet inspected.

Feeds: Not yet inspected.

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: Final pass / owner approval. Do not start until Approved is ticked.

## 5. Cross-cutting rules

### 5.1 Existing workflow-documentation rules (retained)

- Use functional modules as the primary classification; user roles may participate in multiple modules.
- Give every workflow a stable ID, actor, trigger, preconditions, main flow, alternative/error flows, postconditions, business rules, and acceptance criteria.
- Link each workflow to functional requirement IDs, relevant permission codes, API endpoints, data entities, and test cases only after those are verified.
- Keep School Admin operational account approval separate from Super Admin access-control governance. Do not assume School Admin can assign role permissions.
- Do not create an authoritative enrollment module in CTU-G Workspace. Fee eligibility uses verified enrollment information from the CTU main system or authorized verification.
- Permissions determine which existing features and actions are available. A permission grant does not create a new implemented feature or bypass record-level privacy checks.
- Treat reports, auditing, backups, retention, and security as cross-cutting concerns, not substitutes for module-specific controls.

### 5.2 Additional cross-cutting rules

- Hash passwords before any temporary or permanent storage.
- Use the same generic conflict message before and after OTP so existing IDs/emails are not revealed.
- Account creation is all-or-nothing, backed by database-level concurrency protection.
- Roles and permissions attach to the account ID, never to the email.
- No ERD, migration, or code change is authorized by this document.

## 6. Appendix A – Decision Register

D-01–D-09 remain OPEN. The owner-stated Instructor OTP target and follow-up Staff ID/review/conflict/support/recovery answers are recorded for WF-01.02; implementation and test success do not approve policy or Human Approval. Shared rules now list WF-01.02 as affected; Student's approved main flow, conflict wording and runtime behavior are retained. The historical direct-Instructor baseline is superseded.

| ID | Decision | Suggested | Alternative | Status | Owner | Flows affected |
| --- | --- | --- | --- | --- | --- | --- |
| D-01 | OTP expiry | 10 minutes | 5 minutes | IMPLEMENTED configurable default — Code/test-verified; policy OPEN | Project owner |WF-01.01; WF-01.02 |
| D-02 | Resend interval and limit | 60 s, 3 resends | 120 s, 2 resends | IMPLEMENTED configurable default — Code/test-verified, row-locked counters; counters commit before mail is sent (R-02); policy OPEN | Project owner |WF-01.01; WF-01.02 |
| D-03 | Failed attempts | 5 cumulative per stage, then invalidate/refuse until cancel/expiry; resends do not reset attempts | 3, then cooldown | IMPLEMENTED configurable default — Code/test-verified; policy OPEN | Project owner |WF-01.01; WF-01.02 |
| D-04a | Staging storage | Encrypted DB staging; password hash inside AES-GCM envelope; keyed identity/OTP/token digests | protected Redis staging | IMPLEMENTED mechanism — Code/DB/test-verified; policy OPEN | Project owner |WF-01.01; WF-01.02 |
| D-04b | Duplicate staged attempt | Reject other-browser duplicates; original HttpOnly cookie resumes/cancels the immutable original role/recipient. Student has no separate resume control; Instructor owned resume continues directly without a conflict | Overwrite or cross-browser identity-only resume (not allowed) | IMPLEMENTED shared ownership; Instructor action states in D-13; policy OPEN | Project owner | WF-01.01; WF-01.02 |
| D-05 | Abandoned cleanup | Fixed 30-minute TTL; resends do not extend it; immediate expiry refusal plus local 60-second purge worker | 1 hour | IMPLEMENTED configurable default — Code/DB/test-verified; supervised production scheduling/policy OPEN | Project owner |WF-01.01; WF-01.02 |
| D-06 | Email uniqueness | Unique normalized non-null email across accounts; new Student/Instructor public accounts save durable verified address/time after OTP; legacy proof remains NULL | Original active-account-only wording or shared addresses need a separately reviewed policy change | Code/DB/test-verified; fresh SHOW CREATE TABLE confirms email unique key and ledger through 0005; zero normalized duplicate groups, none merged/deleted; historical exact 0004 reconciliation/0005 release preserved values; policy OPEN | Project owner |WF-01.01; WF-01.05; WF-04.04; WF-02.04; WF-03; WF-01.02 |
| D-07 | Duplicate-registration response | Generic HTTP 409 before/after OTP with the same approved Student wording for both roles (owner consistency instruction, 16 Nov; OD-1(a)) | Historical direct Instructor neutral 202 and the Instructor-only sentence are superseded; no field-specific identity disclosure | IMPLEMENTED shared contract — Code/test-verified; anti-enumeration policy (SRS FR-REG-03) OPEN | Project owner |WF-01.01; WF-01.02 |
| D-08 | OTP delivery failure and recovery | Retain encrypted stage; send only after the staging write commits; invalidate the uncertain code, never a newer one; bounded resend within original deadline; no account or success claim | Purge staging and require a new attempt | IMPLEMENTED mechanism — Code/test-verified with failed/zero-send and concurrent-newer-code cases; policy OPEN | Project owner |WF-01.01; WF-09.04; WF-01.02 |
| D-09 | Review eligibility and existing unverified Pending accounts | New Student/Instructor public registrations save proof atomically after OTP; legacy proof remains NULL | WF-02 eligibility/legacy transition remains separately reviewed; no WF-02 code/gates changed | Registration proof IMPLEMENTED — Code/DB/test-verified; existing shared review gates unchanged. For approval, resolved by D-44 (WF-02.03, 17 Nov 2026): an application without verified proof for its current address cannot be approved, so legacy unverified Pending accounts stay Pending; any legacy approval path would need a new decision. Legacy/cross-flow policy otherwise OPEN | Project owner |WF-01.01; WF-02.01; WF-02.03; WF-01.02 |
| D-10 | Instructor registration sequence | Owner-stated OTP before Pending account/profile, sharing protected staging and proof with Student; role stored in existing encrypted payload | Historical direct-to-Pending/neutral-202 baseline, now superseded by owner instruction | IMPLEMENTED/test-verified in development; owner-stated requirement recorded, no agent approval; Human Approval pending | Project owner | WF-01.02 |
| D-11 | Instructor identity | Owner-stated Staff ID, 1–7 ASCII digits, mapped to unique existing accounts.school_id; leading zeroes retained | Separate employee identity/format would require new owner/schema review | Owner answer recorded; Code/DB/test-verified; no migration or agent policy approval | Project owner | WF-01.02 |
| D-12 | Instructor eligibility verification | Owner-stated School Admin review only; OTP proves email access, not employment | Separate authoritative HR/verification process would require specified source/contract | Owner answer recorded; shared review service/gates retained. For approval, resolved by D-45 (WF-02.03, 17 Nov 2026): the School Admin attests that they checked institutional employment records, and the attestation is recorded in the approval audit; Workspace does not verify employment. An authoritative HR source remains out of scope and OPEN | Project owner | WF-01.02; WF-02.01; WF-02.03 |
| D-13 | Instructor conflict/recovery actions and support | SUPERSEDED by the owner's 16 Nov instruction to adopt Student feedback, confirmed as OD-1(a): shared conflict wording, no Instructor-only action panel or configured support action. Owned resume is not a conflict | Earlier Instructor sentence and four gated actions (historical, not implemented) | SUPERSEDED — shared feedback Code/test-verified; official support contact – needs owner input; no agent policy approval | Project owner | WF-01.02; WF-01.01 (support open-item cross-reference only) |
| D-14 | Registration identity abuse limits / staging cap | Reuse existing IP budgets additionally per keyed ID/email for both roles (Student added by OD-2, 16 Nov), shared across roles: admission 5/min and 30/day, OTP/status 30/min and 200/day; one live stage per unique ID/email; inherited D-05 fixed expiry | Tighter identity budgets or a separately reviewed global-cap/shared-cache deployment | IMPLEMENTED/test-verified local controls; accepted first-claim/cache deployment risks documented; inherited/default policy review OPEN | Project owner | WF-01.01; WF-01.02 |
| D-15 | Login feedback and identifier label | Show server messages (401 credentials, 429 countdown, 403 refresh action, 503 or network then session re-read); non-revealing approval hint on every 401; clear the password; label "School ID or Staff ID" | Keep the current single generic message and the "School ID" label | Owner-approved 16 Nov 2026; IMPLEMENTED and test-verified (WF-01.03 P-01, P-02) | Project owner | WF-01.03 |
| D-16 | Login abuse controls | Keep per-IP 8/minute and 40/hour; add a per-identity budget keyed by a keyed school_id digest; shared cache and trusted-proxy settings in deployment; no account lockout | Account lockout after N failures (lets anyone lock out a known School ID), or IP-only throttling | Per-identity budget owner-approved and IMPLEMENTED, test-verified (8/min, 40/hour code defaults); WF-01.05 recovery request budget 3/hour, 6/day and separate reset counters IMPLEMENTED, test-verified; value policy, shared cache and trusted proxy OPEN | Project owner | WF-01.03; WF-01.05 |
| D-17 | Authentication-event contract | Owner-approved event source, fields (no credentials or secrets), redaction, retention and access (FR-AUTH-07, FR-AUD-02) before any login event is stored | Server log only, or no events | OPEN; nothing recorded today; access_audit_logs must not be used; ERD read-only | Project owner | WF-01.03; WF-01.04; WF-12.01 |
| D-18 | Session lifetime and cookie flags | Explicit production settings: Secure session and CSRF cookies, HTTPS, DEBUG off, an approved absolute and idle session lifetime | Django defaults (14-day persistent cookie, no idle timeout, Secure off) | Owner-APPROVED 17 Nov 2026: 30-minute idle and 8-hour absolute limits enforced server-side; DEBUG off by default; HTTPS and Secure cookies mandatory in production; local HTTP kept. IMPLEMENTED and test-verified (security_settings.py, session_timeout.py). Production host, proxy, HTTPS forwarding and HSTS values to be verified before activation | Project owner | WF-01.03; WF-01.06 |
| D-19 | Session revocation timing and concurrent sessions | Keep the per-request database eligibility recheck; decide whether to delete sessions on deactivation or role change and whether to limit sessions per account (SRS OD-13) | Revoke only at expiry | Recheck IMPLEMENTED and test-verified; deletion and limits OPEN | Project owner | WF-01.03; WF-01.04; WF-01.06; WF-02.05; WF-03.01 |
| D-20 | Recovery mail dispatch and timing | Send the reset mail outside the request through a bounded background dispatcher so matching and non-matching requests take the same time | Keep synchronous sending (reveals valid ID and email pairs by timing) or pad every response | Option (a) owner-approved 16 Nov 2026 for development only; IMPLEMENTED and test-verified (recovery_mail.py: 50-message in-memory queue, one daemon thread, kind-only logging). Production BLOCKED until reliable delivery, failure handling and security are verified (D-24). The registration outbox is not reused (it would need an ERD change) | Project owner | WF-01.05 |
| D-21 | Recovery eligibility: verified email | Require email_verified_at and email_verified_address matching the current email; others get the neutral response and the support path | Keep sending to any email on file, including legacy unverified addresses | Option A owner-approved 16 Nov 2026; IMPLEMENTED and test-verified at request and reset. Legacy accounts without proof (dev DB: 1 of 1 approved accounts) get the neutral response and the assisted-recovery hint. The future authorized assisted-recovery procedure and the official support contact are OPEN | Project owner | WF-01.05; WF-01.01; WF-01.02; WF-02.03; WF-10 |
| D-22 | Password-changed notice | After commit, send a link-free "password was changed" email; failure never changes the result | No notice | Owner-approved 16 Nov 2026; IMPLEMENTED and test-verified: queued with transaction.on_commit only after the update commits (none on rollback; exactly one under concurrency), sent through the D-20 sender, no link or token | Project owner | WF-01.05; WF-09.04 |
| D-23 | Reset token model | Keep Django stateless tokens (single-use through the password hash, 30-minute expiry; several links valid until one is used) and leave password_reset_token columns unused | Store a digest of the latest token in the existing columns so a newer request invalidates older links | Owner-approved 16 Nov 2026: keep Django's stateless token unchanged (IMPLEMENTED and test-verified: expiry, single use, other links refused after use). SUPERSEDED by D-28; CR-01 implemented 17 Nov 2026 and password_reset_token columns now hold the OTP record (D-27) | Project owner | WF-01.05 |
| D-24 | Password-recovery activation | Keep WORKSPACE_PASSWORD_RESET_ENABLED off until P-01 to P-07, D-20, D-21 and production HTTPS (D-18) are done, then approve activation separately | Activate now | Owner decision 16 Nov 2026: keep disabled; gate default off (test-verified). Protected executor mode refuses recovery explicitly (test-verified). Activation needs separate approval after production security, reliable delivery and protected-executor compatibility | Project owner | WF-01.05; WF-01.03 |
| D-25 | Recovery flow and identifier (CR-01) | Email only, then a 6-digit code, then a new password on one page; always continue to the code step with a neutral message; D-21 eligibility unchanged | Keep School ID plus email and the reset link | Owner-APPROVED 16 Nov 2026 (email-only recovery on /forgot-password; neutral responses); IMPLEMENTED and test-verified 17 Nov 2026 | Project owner | WF-01.05 |
| D-26 | Recovery code rules (CR-01) | 6 digits, 10 minutes, 5 cumulative wrong entries per 30-minute window, 60-second resend, resending never resets attempts, 3/hour and 6/day per email; identical error for unknown, expired, used and locked codes | Other lifetimes or limits | Owner-APPROVED 16 Nov 2026; defaults reused from WF-01.01 D-01 to D-03 and D-05 via policy(); IMPLEMENTED and test-verified 17 Nov 2026 (expiry, 60-second resend, 5-attempt lock that resends do not reset, fresh window after 30 minutes, per-email budgets) | Project owner | WF-01.05 |
| D-27 | Recovery code storage (CR-01) | HMAC of the code plus attempt count and expiry in the existing accounts.password_reset_token and password_reset_token_expires columns; a correct code is exchanged for a one-time 10-minute reset ticket; new endpoint POST /api/v1/auth/forgot-password/verify/ | Cache-only storage (lost on restart, per process) or a new table (ERD change) | Owner-APPROVED 17 Nov 2026 with the HttpOnly-cookie ticket; IMPLEMENTED and test-verified: rv1 otp/ticket/locked record in the existing columns (HMAC only), row-locked steps, exactly-once ticket and password change under concurrency, cookie HttpOnly, SameSite=Strict, path-scoped, 10 minutes; protected mode refused. No migration | Project owner | WF-01.05; WF-01.06 |
| D-28 | Retire the reset link (CR-01) | Remove the link email, fragment token and Django token generator; /reset-password only points to Forgot Password; supersedes D-23 | Keep the link alongside the code | Owner-APPROVED 16 Nov 2026; IMPLEMENTED 17 Nov 2026: link email, fragment token and Django token generator removed; /reset-password points to Forgot Password; supersedes D-23 | Project owner | WF-01.05 |
| D-29 | CSRF cookie HttpOnly | Set CSRF_COOKIE_HTTPONLY = True; the frontend takes the token only from the /csrf/ body and never reads the cookie | Keep the script-readable CSRF cookie | Owner-APPROVED 17 Nov 2026; IMPLEMENTED and test-verified (CSRF_COOKIE_HTTPONLY = True; body-token bootstrap and all POST flows pass) | Project owner | WF-01.06; WF-01.01 to WF-01.05 |
| D-30 | Expired-session cleanup | Schedule `python manage.py clearsessions` (for example daily) in the runbook and deployment; no schema change | No cleanup (expired rows accumulate, never accepted) | Owner-APPROVED 17 Nov 2026: daily clearsessions documented (runbook 5B) and test-verified; scheduler installation awaits deployment access and approval; enforcement independent | Project owner | WF-01.06; WF-12.05 |
| D-31 | WF-02.01 route and gate | Mount only the list view at GET /api/v1/admin/registration-requests/ in config/urls.py behind a new WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED (default off); approve/reject stay unmounted and keep the review API + approval gates; frontend REGISTRATION_REVIEW_LIST_ENABLED separate from the decision gate | Keep the list tied to both existing gates (list only when decisions are enabled), or keep it unmounted | Owner-APPROVED 17 Nov 2026; IMPLEMENTED and test-verified (only the list route mounted; backend and frontend switches off by default; the existing decision pair still opens the list in the isolated review configs) | Project owner | WF-02.01; WF-02.03; WF-02.04 |
| D-32 | WF-02.01 listed applicant fields | School ID, full name from users, requested role, submission date, email-proof state, status "Pending review"; no email address (shown only in WF-02.02 detail) | Current minimum (School ID, role, date only), or also show a masked email | Owner-APPROVED 17 Nov 2026; IMPLEMENTED and test-verified (full_name and email_verified added; no email address) | Project owner | WF-02.01; WF-02.02 |
| D-33 | WF-02.01 search, filter, sort, pagination | Server-side q (School ID prefix; name contains if D-32), role, proof and allowlisted sort; fixed 20 per page; default oldest first; has_next instead of a total | Also return a total count, or keep page-only client filtering | Owner-APPROVED 17 Nov 2026; IMPLEMENTED and test-verified (has_next, no total) | Project owner | WF-02.01 |
| D-34 | WF-02.01 legacy Pending without email proof | List them with a "No email proof" flag (email_verified_at or email_verified_address NULL, email NULL, or address not matching the current email case-insensitively); approval eligibility left to WF-02.03 under D-09 | Hide them from the list, or list them without a flag | Owner-APPROVED with clarification 17 Nov 2026: label "No email proof on record"; missing proof never treated as verified or approval-eligible; IMPLEMENTED and test-verified | Project owner | WF-02.01; WF-02.03; D-09 |
| D-35 | WF-02.01 Pending rows outside the review filter | Keep excluding Pending rows with a missing or inactive requested role, staff/superuser flags, reviewer fields set, an assigned role or is_active true; report them only through a later count-only operator check | Show them in the list as "Needs technical review" | Owner-APPROVED conditionally 17 Nov 2026: exclusion kept and documented; count-only visibility tracked as FU-02.01-A (not built); valid Pending rows never hidden | Project owner | WF-02.01; WF-12 |
| D-36 | WF-02.01 read throttle | Separate list scope 60/min per account and address; searches submitted explicitly, never per keystroke; decisions keep 20/min | Keep the shared 20/min per-address bucket | Owner-APPROVED 17 Nov 2026: 60/min per account for the list; decisions keep 20/min; IMPLEMENTED and test-verified | Project owner | WF-02.01; WF-02.03; WF-02.04 |
| D-37 | WF-02.02 route and switch | Mount only GET /api/v1/admin/registration-requests/<id>/ (exact class, GET/HEAD/OPTIONS) behind the existing WF-02.01 read switch (one read surface, one permission); approve/reject stay unmounted | A separate WORKSPACE_REGISTRATION_REVIEW_DETAIL_ENABLED switch, or keep the detail unmounted | Owner-APPROVED 17 Nov 2026; IMPLEMENTED and test-verified (detail mounted GET-only behind the same read switch; approve/reject unmounted) | Project owner | WF-02.02; WF-02.01 |
| D-38 | WF-02.02 email address in the detail | Show the full current email to the authorized reviewer, next to its evidence state, because identity review compares it with the verified address; never in the list (D-32) | Masked email (for example j***@example.edu), or no email at all | Owner-APPROVED 17 Nov 2026; IMPLEMENTED and test-verified (email only in the detail; never in the list, body of errors or logs) | Project owner | WF-02.02; D-32 |
| D-39 | WF-02.02 review-progress recording | None: WF-02.02 is read-only and never writes reviewed_by, reviewed_at, request_status, is_active or roles (writing reviewed_* would hide a Pending applicant from WF-02.01) | A new review-notes table (migration + ERD change, separate approval) | Owner-APPROVED 17 Nov 2026; IMPLEMENTED and test-verified (no writes on any read; the application stays in the queue) | Project owner | WF-02.02; WF-02.01; WF-02.03; WF-02.04 |
| D-40 | WF-02.02 read audit | No read audit until D-17 defines read/security events (the WF-02.01 list writes none either) | An access_audit_logs row per detail read (existing table, no migration; GET would write) | Owner-APPROVED 17 Nov 2026; IMPLEMENTED (no application-level read audit; existing logging unchanged) | Project owner | WF-02.02; WF-12; D-17 |
| D-41 | Release safeguard for the detail route (protected) | Extend unexpected_review_routes() in init_registration_review_metadata_local_dev.py to tolerate exactly the GET-only detail route as well as the list, with its tests; everything else still refuses | Keep the safeguard list-only and leave the detail unmounted | Owner-APPROVED 17 Nov 2026 with explicit protected-file authorization for init_registration_review_metadata_local_dev.py and its associated safeguard tests; IMPLEMENTED and test-verified | Project owner | WF-02.02; AR-6C release tooling |
| D-42 | WF-02.02 UI pattern | In-view detail page (/dashboard?view=registration-review&applicant={id}) with Back to pending applications that restores filters, sort and page, and a fourth breadcrumb (small shell extension) | Drawer or modal (no accessible Modal exists yet, AUDIT A-06), or a separate navigation item | Owner-APPROVED 17 Nov 2026; IMPLEMENTED and test-verified (in-view page, fourth breadcrumb, Back preserving filters, sort and page) | Project owner | WF-02.02; Dashboard Shell v0.1 |
| D-43 | WF-02.02 evidence wording | Email states: verified by one-time code on {date} / No email proof on record / Email changed after verification / No email on file; plus "Enrollment must be confirmed with CTU's main system" (Student) or "Employment must be confirmed through authorized institutional records" (Instructor); never a bare "Verified" | Show only the email state | Owner-APPROVED 17 Nov 2026; IMPLEMENTED and test-verified (four wordings, enrollment/employment notices; D-09 preserved) | Project owner | WF-02.02; D-09; D-12 |
| D-44 | WF-02.03 email evidence for approval (resolves D-09 for approval) | Approval requires the email-evidence state verified (email, proof time and a proof address equal to the email, case-insensitive); no_proof, address_changed and no_email are refused 409 email_unverified and stay Pending | An owner-authorized legacy path with a recorded attestation, or no email requirement (current code) | APPROVED 17 Nov 2026 (owner); implemented and tested 18 Nov 2026 | Project owner | WF-02.03; D-09; D-34; D-43 |
| D-45 | WF-02.03 institutional eligibility (resolves D-12 for approval) | Each approval carries a reviewer attestation {confirmed: true, source: fixed enum} — Student: ctu_main_system_records; Instructor: institutional_employment_records — recorded in the existing access_audit_logs new_value; no documents, IDs or free text stored | A UI-only checkbox (not recorded), or a new verification table (migration and ERD change) | APPROVED 17 Nov 2026 (owner); implemented and tested 18 Nov 2026 | Project owner | WF-02.03; D-12 |
| D-46 | WF-02.03 release mode | Keep the approve route out of config.urls and the release safeguard unchanged; approval usable only in the existing loopback local review mode and the synthetic sandbox; production stays the separate protected executor release | Mount approve in config.urls behind environment gates (needs a protected safeguard change and makes the pre-release tooling refuse) | APPROVED 17 Nov 2026 (owner); implemented and tested 18 Nov 2026 | Project owner | WF-02.03; AR-6C release tooling |
| D-47 | WF-02.03 refusal reporting | Policy refusals 409 approval_not_allowed with fixed reasons (email_unverified, eligibility_unconfirmed), because the reviewer can already read the application; stale or ineligible stays 404 request_unavailable | Keep every refusal as 404 | APPROVED 17 Nov 2026 (owner); implemented and tested 18 Nov 2026 | Project owner | WF-02.03 |
| D-48 | WF-02.03 confirmation dialog | Implement the COMPONENTS §6 Modal (native dialog: focus trap, Escape, focus return) as a shared component and use it for the approval confirmation | An inline confirmation section with managed focus, no modal | APPROVED 17 Nov 2026 (owner); implemented and tested 18 Nov 2026 | Project owner | WF-02.03; AUDIT A-06 |
| D-49 | WF-02.03 approval notification | Use the existing durable outbox only when it is enabled and configured; otherwise no approval email; the approval stands if delivery fails; no live email in tests | Best-effort after-commit email, or no approval email at all | APPROVED 17 Nov 2026 (owner); implemented and tested 18 Nov 2026 | Project owner | WF-02.03; WF-09 |
| D-50 | Base-role defaults after approval | Out of WF-02.03 scope: Student and Instructor roles hold no active grants, so SRS AT-02 "default access after login" depends on a separately approved WF-03 base-role grant change | Seed role defaults as part of WF-02.03 | APPROVED 17 Nov 2026 (owner): deferred to WF-03; SRS AT-02 recorded as UNMET, not passed | Project owner | WF-02.03; WF-03; SRS AT-02 |
| D-51 | WF-02.03 executor parity | While the executor protocol cannot carry the attestation, refuse approval when the protected writer is enabled (503) instead of approving without it; a protocol/engine change is a separate protected-file decision | Change the executor protocol and engine now | APPROVED 17 Nov 2026 (owner); implemented and tested 18 Nov 2026 | Project owner | WF-02.03; protected executor |
| D-52 | WF-02.03 approval audit contract (protected audit.py) | Narrow extension for the account.registration.approve event only: its new_value may and must carry email_evidence "verified", eligibility_confirmed true, eligibility_subject (enrollment or employment) and eligibility_source (ctu_main_system_records or institutional_employment_records) as a consistent pair, with an applicant target; the reviewer is the actor and created_at the time; the fields are rejected in every other event and in old_value; values are derived server-side | Unrestricted JSON, a nested attestation object, or relaxing other event validation | APPROVED 17 Nov 2026 (owner authorization of a narrow protected-file change); implemented and tested 18 Nov 2026 | Project owner | WF-02.03; D-45; WF-12 |
| D-53 | Bulk registration approval | Bulk approval must follow D-44/D-45 and stay unmounted; the test-only bulk service is unchanged and fails closed (every approval item Skipped) because it cannot carry a per-applicant attestation; no fabricated or automatic attestations; bulk approval is a separate future workflow | Approve in bulk without an attestation, or generate attestations automatically | APPROVED 17 Nov 2026 (owner); bulk tests adjusted as approved (1 refusal test, 7 switched to rejection); a ninth, reapplication bulk test adjusted in the same pattern, accepted by the owner 18 Nov 2026 after inspection | Project owner | WF-02.03; future bulk-review workflow |
| D-54 | WF-02.04 rejection notification | Rejection requires the durable encrypted outbox with the v2 template, written in the same transaction as the audit and the deletion; refused 503 before any write when the outbox is disabled or unavailable; never the best-effort path; at-least-once delivery (a rare duplicate after a worker crash is accepted); the API reports notification queued or not_sent, never delivered | Allow rejection without a notification record (current local review mode), or send synchronously before commit | APPROVED 18 Nov 2026 (owner); implemented and tested 18 Nov 2026 | Project owner | WF-02.04; WF-09; FR-REG-07 |
| D-55 | WF-02.04 recipient and eligibility policy | D-44/D-45 do not apply to rejection. The email is queued only for a verified current address; for no_proof, address_changed or no_email the reviewer must acknowledge that no email will be sent, and the outbox records a Dead row with a fixed code | Send to any address on file, or refuse rejection without a verified address (legacy applicants could then never leave Pending) | REVISED by the owner 18 Nov 2026: no-email rejection is NOT authorized; a valid verified recipient is required until an alternative policy is separately approved; implemented and tested 18 Nov 2026 | Project owner | WF-02.04; D-09; D-44 |
| D-56 | WF-02.04 rejection reasons | Keep the four fixed codes; the applicant sees only the approved public v2 label; no free text, reviewer notes or private details in email or audit | Free-text reasons with length limits and moderation | APPROVED 18 Nov 2026 (owner); unchanged codes, enforced and tested | Project owner | WF-02.04; SRS v1 FR-REG-07 |
| D-57 | WF-02.04 audit and notification retention | Keep the minimal append-only rejection audit record (account_id integer, reason code, reviewer, time; no name, email or ID); erase the encrypted recipient after Delivered or Dead (protected worker and executor-trigger change); no retention period, blacklist or identity digest is invented; the owner sets any retention period | Keep the encrypted recipient indefinitely (current), or delete the audit record | APPROVED IN PRINCIPLE 18 Nov 2026 (owner); recipient erasure implemented and tested 18 Nov 2026 under the protected-file authorization (outbox_worker.py, executor schema.py); retention period still unset | Project owner | WF-02.04; WF-12; D-17 |
| D-58 | WF-02.04 refusal reporting | 409 rejection_not_allowed with fixed reasons (protected_history, direct_permissions, notification_unavailable) for an application the reviewer can read; stale or unknown stays 404 request_unavailable | Keep every refusal as 404 (current) | APPROVED WITH CLARIFICATION 18 Nov 2026 (owner): privacy-safe 404 kept, fixed 409 conflicts (recipient_unverified, direct_permissions, protected_history); implemented and tested 18 Nov 2026 | Project owner | WF-02.04; D-47 |
| D-59 | WF-02.04 frontend scope | A Reject section in the WF-02.02 detail behind VITE_WORKSPACE_REGISTRATION_REJECTION_ENABLED (default off) and the exact reject permission; shared Modal with the destructive confirm; truthful notification wording; no bulk UI; WF-02.03 unchanged | Reuse the legacy live panel | APPROVED 18 Nov 2026 (owner); implemented and tested 18 Nov 2026 | Project owner | WF-02.04; D-48 |
| D-60 | Legacy Rejected data | The development database's one Rejected account (rejected before deletion existed; its audit references the row) is left untouched; any cleanup (for example anonymizing it in place, since the NO ACTION audit reference blocks deletion) needs a separate owner authorization; SRS v0.4 FR-REG-07 is not automatic cleanup authorization | Delete or rewrite it as part of WF-02.04 | APPROVED 18 Nov 2026 (owner): legacy Rejected records stay untouched | Project owner | WF-02.04; SRS OD-23; O-03 |
| D-61 | Existing reapplication mechanism | The signed-link reapplication of Rejected accounts (reapplication.py, /api/v1/auth/reapply/*) contradicts SRS v0.4 UC-03 (no rejected-account reuse); keep it disabled and retire it in a separately authorized change (routes, service, executor settings that enable it) | Keep it as an alternative path for legacy Rejected accounts | APPROVED IN PRINCIPLE 18 Nov 2026 (owner); partial retirement done 18 Nov 2026 (disabled in both executor settings); removal needs a separate authorization | Project owner | WF-02.04; WF-01.01; SRS UC-03 |
| D-62 | WF-02.04 release mode | Keep the reject route out of config.urls and the release safeguard unchanged; rejection usable only in local review mode and the sandbox, and only after the outbox is enabled there (locmem, test key, no SMTP) by a separately authorized settings change; production stays the protected executor release plus approved SMTP | Mount reject in config.urls, or allow deletion without notification in local mode | APPROVED 18 Nov 2026 (owner): local review and sandbox only, production blocked; outbox enabled there with in-memory mail 18 Nov 2026 (authorized settings change) | Project owner | WF-02.04; AR-6C release tooling |
| D-63 | WF-02.05 eligible targets | Only Approved accounts whose active roles are Student or Instructor base roles, optionally with ordinary extra roles (Treasurer, SSG Advisor); never Admin, Technical Super Admin, framework staff/superuser, the actor, Pending or Rejected accounts | Include Treasurer only after a separate finance-continuity decision, or include administrators | REVISED by the owner 18 Nov 2026: deactivate any Approved, non-protected account (no active role required); reactivate only with an active operational role and existing login eligibility; Treasurer-only accounts included; never grant roles to make an account eligible; Pending, Rejected and protected accounts excluded; implemented stage 1 (uncommitted) | Project owner | WF-02.05; catalogue scope SCHOOL |
| D-64 | WF-02.05 permission codes | Use catalogue v2 accounts.school_accounts.suspend, .activate and .read (Admin binding; Technical Super Admin through Admin); create their rows and bindings only through the governed release tooling (protected) | New codes, or reuse registration_requests codes | APPROVED IN PRINCIPLE 18 Nov 2026 (owner); stage 3: governed companion provisioning implemented and tested; stage 3A: Option A P3B compatibility implemented and tested (compensation preserves the governed rows); committed f476294; stage 3C: provisioned in ctug_workspace through the governed command (permissions 4–6, Admin bindings 4–6 active, receipts 16–24) and verified | Project owner | WF-02.05; catalogue v2 |
| D-65 | WF-02.05 state change | Change only accounts.is_active; never request_status, reviewed_by/at, roles, direct permissions, identity, credentials or profile; reactivation requires an active Student or Instructor base role | A new status flag or status enum (forbidden without schema approval) | APPROVED 18 Nov 2026 (owner); implemented stage 1 (uncommitted) | Project owner | WF-02.05; SRS schema rule |
| D-66 | WF-02.05 session handling | Keep the fail-closed per-request checks; revoke all of the target's sessions after a suspension commits and before a reactivation commits, by deleting their django_session rows; no schema change; reactivation never restores an old session | Fail-closed only (old sessions can revive on reactivation), or a schema-backed session generation | SECURITY REQUIREMENT APPROVED 18 Nov 2026 (owner); implemented as a schema-free session epoch plus a post-login re-check; verified over real HTTP in local-review and sandbox configurations, including delayed writes and rolled-back deactivation | Project owner | WF-02.05; WF-01.06; V2-08 |
| D-67 | WF-02.05 reason policy | No reviewer-entered reason; the audit uses the existing account_status_change reason code | Fixed reason codes (for example separated, administrative_hold, security_concern) through a narrow protected audit.py change like D-52; never free text | LIMITED APPROVAL 18 Nov 2026 (owner): fixed account_status_change reason only, no free text; a status reason-code catalogue is a separate proposal | Project owner | WF-02.05; WF-12 |
| D-68 | WF-02.05 refusal reporting and stale state | Body {"expected_active": bool}; 409 account_status_conflict with fixed reasons state_changed, protected_account, no_active_base_role; unknown or ineligible targets 404 (non-enumerating); repeated requests never audit twice | Idempotent 200 for a repeated request | APPROVED 18 Nov 2026 (owner); implemented stage 1 (uncommitted) | Project owner | WF-02.05; D-47; D-58 |
| D-69 | WF-02.05 release mode | New WORKSPACE_ACCOUNT_STATUS_ENABLED and VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED (default off); routes only in the local review and sandbox URLconfs; extend the release safeguard to refuse account-status routes (protected); refuse when the protected writer is enabled until executor parity exists (as D-51) | Mount in config.urls, or rely on the current safeguard (it does not detect these routes) | APPROVED WITH PROTECTED GATES 18 Nov 2026 (owner); mounted and enabled only in local review and sandbox; safeguard amended (stage 3) to recognize account-status routes by class, module, name and path; protected writer and default-off switch fail closed independently; production blocked | Project owner | WF-02.05; AR-6C release tooling |
| D-70 | WF-02.05 directory scope | WF-02.05 includes a minimized eligible-account list and status detail under accounts.school_accounts.read; status history stays in WF-02.06 | Implement WF-02.06 first and reuse its views | APPROVED 18 Nov 2026 (owner); directory and read-only detail implemented stage 1; history stays in WF-02.06 | Project owner | WF-02.05; WF-02.06; FR-ADM-06 |
| D-71 | WF-02.05 administrators and last operator | Administrator and governance accounts are out of scope, so this workflow cannot disable any or the last effective administrator, including the actor; their deactivation belongs to a protected WF-03 governance process under V2-06 | Allow School Admin to deactivate other School Admins with a last-operator check now | APPROVED 18 Nov 2026 (owner); implemented stage 1; no approved administrative-account workflow is assumed in WF-03 | Project owner | WF-02.05; WF-03; SRS last-effective Super Admin rule |
| D-72 | WF-02.06 history permission | Use accounts.school_accounts.read for the status dates and the minimized status history of eligible accounts (already active for Admin; no new provisioning or P3B change) | access_control.audit.school.read (catalogue SCHOOL_AUDIT projection; visibility rules unresolved; needs governed provisioning and another protected P3B change) | APPROVED 18 Nov 2026 (owner): accounts.school_accounts.read reused; no new code, binding or provisioning; implemented | Project owner | WF-02.06; catalogue v2; WF-12 |
| D-73 | WF-02.06 actor disclosure | Show "You" when the viewer is the actor, otherwise "An administrator"; no administrator names or IDs; full attribution stays in the protected audit | Show the actor's name | APPROVED 18 Nov 2026 (owner): server-generated "You"/"An administrator" only; implemented | Project owner | WF-02.06; FR-AUD-05; catalogue v2 read-code exclusion of governance operators |
| D-74 | WF-02.06 event allowlist | Only account.registration.approve, account.status.suspend and account.status.activate for the target, as event type, time and actor label; never old/new JSON, reason, attestation, IDs or other identities; no governance, release, role, permission, authentication or reapplication events | Include role changes or all audit rows for the account | APPROVED 18 Nov 2026 (owner): exactly the three actions and the minimized fields, enforced by the server; implemented | Project owner | WF-02.06; FR-AUD-01/05 |
| D-75 | WF-02.06 status dates | Current status from accounts.is_active; "Approved on" from reviewed_at; "Last status change" from the latest account.status.* event; "Not recorded" when absent, never inferred | Derive status or dates from history | APPROVED WITH CLARIFICATION 18 Nov 2026 (owner): status from is_active, registration from request_status, approval time from the approval audit then reviewed_at, never invented; implemented | Project owner | WF-02.06; WF-02.03; WF-02.05 |
| D-76 | WF-02.06 API shape and release gate | Add approved_at and last_status_change to the WF-02.05 detail and one GET …/school-accounts/{id}/history/ route in the already-mounted isolated URLconf, under WORKSPACE_ACCOUNT_STATUS_ENABLED; local review and sandbox only; config.urls, config.settings and the protected writer unchanged | A separate switch, or history inside the detail response only | APPROVED 18 Nov 2026 (owner): detail extended; one read-only history route in the isolated URLconf under the existing switch; 20 per page newest first; implemented | Project owner | WF-02.06; D-69 |
| D-77 | WF-02.06 out-of-scope records | Pending, Rejected, deleted and protected accounts, governance and authentication events stay outside WF-02.06 (WF-12 protected audit review) | Show rejected or deleted applicants' history to School Admin | APPROVED 18 Nov 2026 (owner): exclusions enforced by the allowlist and eligibility; implemented | Project owner | WF-02.06; WF-02.04; WF-12; V2-08 |
| D-78 | WF-02.06 lint baseline | Report lint against the then-current baseline; any pre-existing findings need a new WF-02.06-specific exception (the WF-02.05 exception does not carry over) | Carry the WF-02.05 exception forward | APPROVED CONDITIONALLY 18 Nov 2026 (owner): condition met (the same two unchanged findings); WF-02.06-specific exception recorded | Project owner | WF-02.06 |

### Other open items

- WF-01.02 owner-stated OTP target IMPLEMENTED and locally verified: Staff ID and no school information; staged ownership/OTP before proof-backed Pending creation; shared Student-style generic 409 and feedback (consistency decision, OD-1(a)). Earlier direct-registration acceptance is historical. 16 Nov audit corrections: [WF-01 audit corrections record](group_a/WF-01_Audit_Corrections_2026-11-16.md). Current evidence: 164 focused backend, 93 related regressions, 51 focused frontend, 29 browser checks and one real OTP/browser/MySQL/protected-read scenario; build/lint passed. Human Approval remains pending. [Current report](group_a/WF-01.02_Instructor_OTP_Implementation.md).
- Official support contact – needs owner input (WF-01.01 and WF-01.02). No official office/email/phone/address was invented. Both roles show the shared generic contact-support wording; the earlier configured Instructor support action was retired by the consistency decision. Home contact details remain placeholders pending owner data. Password-reset link follows the existing backend feature flag; registration does not enable it.
- D-04b evidence CLOSED: 256-bit opaque browser challenge is held in a scoped HttpOnly cookie; DB stores only its keyed digest. Identity knowledge alone cannot continue/cancel; stages are never overwritten; fixed TTL survives resends. Configurable mechanism awaits policy sign-off.
- Staging/proof/atomicity implementation gap CLOSED for local WF-01.01: AES-GCM staging, keyed OTP digest, stage-row locks, atomic proof/account/profile creation and consumed-stage deletion implemented and tested. No role/login is created. Protected executor rollout remains separate and fails closed.
- Duplicate-count evidence gap CLOSED (DB-verified, configured development DB, 15 November 2026): 3 accounts, 1 NULL email, 0 blank/noncanonical emails, 0 normalized duplicate groups under both actual MySQL collation and Python normalization. Counts disclose no identities. Repeat preflight at any future release.
- Normalization evidence gap CLOSED (Code-verified): email_identity.py uses strip().lower() over the entire address without provider-specific rewriting. D-06 policy reconciliation remains OPEN.
- Development index/ledger discrepancy RECONCILED during the authorized implementation: exact index/column/collation and original 0004 canonical-data preflight verified; encrypted recovery snapshot saved; 0004 explicitly recorded as reconciled with --fake, then additive 0005 applied normally. Every legacy accounts/users column value remained unchanged. Historical index-creation provenance is not inferred; no additional owner file is needed to establish the current local schema.
- React source, component initial server rendering, build and route/proxy smoke checks verified; full interactive browser and real recipient inbox acceptance remain unverified. Earlier browser automation was blocked by safe URL determination. Local frontend/backend and purge worker are now running; no real test recipient was used.

## 7. Appendix B – Evidence Log

Evidence levels: SRS-only / Code-verified / DB-verified, supplemented by automated-test evidence. The earlier read-only inspection was followed by the user's authorization to implement WF-01.01. Local source, actual development schema (ctug_workspace, MySQL 8.4.13), applied migration/ledger reconciliation and automated OTP checks now establish the implemented state. Before/after checks preserved existing account/profile values. Earlier absence findings remain in the historical inspection record; they are not current implementation claims. No production environment or real recipient inbox was verified.

| Item | Evidence level | Evidence / gap |
| --- | --- | --- |
| WF-01.02 Instructor registration OTP | Code/DB/automated-test verified | Owner target implemented: Staff ID 1–7, no school information, protected staging/OTP, shared HTTP 409/no new code on conflicts, original-browser resume, atomic Pending/profile/proof and no role. 164 focused backend (30 unchanged Student OTP, 20 Instructor OTP), 93 related regressions, 51 focused frontend, 29 browser and one real OTP/CSRF/MySQL/protected-read scenario passed; build/lint passed. New schema/migrations absent. Actual inbox/full human-browser/production acceptance unverified; official support contact needs owner input with accepted fallback active. |
| WF-01.03 Login and session establishment | Code/automated-test verified | Owner-approved P-01 to P-05 implemented 16 Nov 2026: specific sign-in feedback, Staff ID label, existing-session view, request references, per-identity budget. 18/18 backend session tests, 6/6 feedback unit tests, 43/43 browser tests (7 new login scenarios), build passed. Pre-existing unrelated failures recorded under WF-01.03. P-06/D-17 blocked; interactive real-account sign-in and production configuration unverified. |
| WF-01.04 Logout and session termination | Code/automated-test verified | Owner-approved P-01 to P-05 with safeguards S-1 to S-5 implemented 16 Nov 2026: confirmed sign-out outcome, history replacement and restored-page recheck, cross-tab notice and visibility recheck, 401-only session recheck, logout boundary tests. 22/22 backend session tests, 5/5 sign-out unit tests, 51/51 browser tests (8 new), build passed. Genuine back/forward-cache restore and real-account sign-out unverified. |
| WF-01.05 Forgot-password request and reset | Code/automated-test verified | Owner-approved P-01 to P-07 under D-20 (a, development only), D-21 A, D-22, D-23, D-24 implemented 16 Nov 2026: verified-email eligibility, background delivery, post-commit notice, per-identity and separate reset limits, safe field errors, uncertain-outcome handling, label, executor fail-closed refusal. 21/21 backend password-reset tests (including two-thread concurrency), 7/7 unit, 58/58 browser tests (7 new), build passed. Gate stays off. Real SMTP through the background sender, the real executor server and production unverified. |
| WF-01.05 CR-01 email-OTP recovery | Code/automated-test verified | D-25 to D-28 approved (D-27 with the HttpOnly cookie) and implemented 17 Nov 2026: email-only request, 6-digit code, cumulative 5-attempt lock, 60-second resend, row-locked single-use ticket cookie, link flow retired. 26/26 backend recovery tests including three two-thread concurrency cases, 8/8 unit and 8/8 recovery browser tests; build passed. Gate stays off; protected mode refused. Depends on WF-01.01/02 (proof, staging key), WF-01.03, WF-01.06, WF-02.03/05, WF-04.04, WF-09.04, WF-12.01. Owner manual acceptance with real SMTP passed 17 Nov 2026 on account 7241423 (owner-authorized direct approval; genuine proof). The real executor server and production configuration are unverified. |
| WF-01.06 Session expiry and CSRF handling | Code/automated-test and interactively verified | Owner-approved P-01 to P-07 implemented 17 Nov 2026. Final run: access_control 1081/1081 (catalogue 119/119), accounts 426/426, unit 164/164, browser 63/63, 15/15 real-stack interactive checks (exact 30:00 idle and 8:00:00 absolute boundaries), build and check passed. Repository repair 23f9b8e (five pinned sources byte-exact plus .gitattributes) and test-only corrections f32a526. |
| WF-02.01 View pending applications | Code/automated-test verified | Owner-approved P-01 to P-08 implemented 17 Nov 2026: read-only list mounted at /api/v1/admin/registration-requests/ behind backend and frontend switches (default off); server search, filters, sort, has_next, name and proof flag; per-account 60/min limit; DatabaseError → review_unavailable. test_wf0201_pending_list 26/26; all 65 accounts and access_control test modules 1587/1587 after the corrections (manage.py test, config.test_settings). History: the first full run after implementation had 134 failures from one cause (the release safeguard, see Protected-file correction); the run after narrowing it had 2 further failures in previously masked recovery assertions; after the authorized assertion update every module passes. Frontend 169/169 unit, 73/73 browser (10 new), build and check passed. Inspection baseline at 51217b1 kept: 74/74 and 64/64. |
| WF-02.02 Verify and review applicant information | Code/automated-test verified | Owner-approved P-01 to P-08 with D-37 to D-43 implemented 17 Nov 2026 from 5ca1062: GET-only detail at /api/v1/admin/registration-requests/{id}/ behind the WF-02.01 read switch, shared eligibility filter, four email-evidence states, no writes; protected safeguard tolerates exactly the list and the detail (D-41); in-view detail page. test_wf0202_applicant_detail 19/19, safeguard 19/19, backend 1611/1611, frontend 176/176 unit and 92/92 browser (8 new), build, check and makemigrations --check passed. |
| WF-02.03 Approve applicant account | Code/automated-test verified | Implemented 18 Nov 2026 from fa525a1 (inspected at fa525a1). D-44 verified email and D-45 attestation enforced in the locked transaction and recorded through the narrow D-52 audit contract; 409 policy refusals; D-51 refusal with the protected writer enabled; attestation-only approve body; approval section and Modal dialog behind VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED (off). Still reachable only in local review mode and the sandbox. 41 new backend, 11 unit and 8 browser tests including two-connection concurrency; full regression passed (lint: 2 pre-existing findings). Bulk approval fails closed (D-53). AT-02 UNMET (D-50). Human Approval recorded by the owner (Ronald C. Arias, November 18, 2026). |
| WF-02.04 Reject applicant, notify by email, and delete rejected registration data | Code/automated-test verified | Implemented 18 Nov 2026 from 1615d8e in two owner-authorized stages: mandatory outbox and v2 template (D-54), verified recipient (D-55 revised), fixed 409 conflicts (D-58), queued-only reply, rejection UI behind VITE_WORKSPACE_REGISTRATION_REJECTION_ENABLED (off), recipient erasure at Delivered/Dead in the worker and executor trigger (D-57), reapplication disabled in the executor settings (D-61 partial), local review and sandbox outbox with in-memory mail (D-62). 31 + 14 + 11 new backend tests, 30 corrected tests, 11 unit and 9 browser tests; full regression passed (lint: WF-02.04-only baseline exception). Commit fac37a9. Human Approval recorded by the owner (Ronald C. Arias, November 18, 2026) for local development only; production blocked. |
| WF-02.05 Activate or deactivate an existing account | Code-verified; automated-test verified in the disposable test DB (committed f476294 and 85212e4); DB-verified in ctug_workspace (stage 3C governed provisioning); Human Approval for local development only (November 18, 2026) | Account-status service, schema-free session epoch with post-login re-check (D-66), API mounted only in local review and sandbox, account directory and status controls, governed companion provisioning command (3 phases, 9 receipts), an amended release safeguard and the Option A P3B compatibility change. 68 WF-02.05 backend tests (23 + 21 + 7 + 17) plus 4 safeguard cases, 8 unit and 8 browser tests pass; security regression 1780/1780; lint WF-02.05-only baseline exception. Provisioned in ctug_workspace; no live status change on real accounts; production blocked. |
| WF-02.06 View account status and permitted history | Code-verified; automated-test verified in the disposable test DB; read-only verified over ctug_workspace | Detail status dates (approval audit, then reviewed_at, else Not recorded) and one read-only, allowlisted, paginated history endpoint under accounts.school_accounts.read; Account status and Status history sections in the account detail. 12 new backend, 5 unit and 5 browser tests; full WF-02 category regression recorded in the WF-02.06 entry; lint WF-02.06-only baseline exception; production blocked. |
| Public Student registration | Code/test-verified; behavior retained | Approved Student OTP sequence, existing payloads, cookie ownership and conflict wording retained. All 30 unchanged Student OTP tests passed standalone and within the final focused suite. Instructor reuse is separately documented under WF-01.02; historical Student release evidence remains in its implementation record. |
| /register route | Code/test/HTTP-verified | App routes /register and /register/verify; VerifyEmailPage implements code entry, resend, cancel, errors and confirmation. Student button is Proceed Email Verification; separate resume control removed. Initial component server rendering and live route HTTP 200 verified. |
| Pending/inactive state | Code/DB/test-verified | Correct OTP atomically creates account/profile with Pending/inactive state and verified address/time; no AccountRole/login. Wrong/expired/replayed codes and transaction failure create no partial permanent records. Existing development records preserved; no real applicant created by verification work. |
| School ID uniqueness | Code/DB-verified | Account field and DBML specify uniqueness; public serializer accepts 1–7 ASCII digits. SHOW CREATE TABLE accounts confirms unique school_id index. Evidence gap closed for development DB. |
| Email uniqueness | Code/DB/test-verified | Fresh read-only SHOW CREATE TABLE accounts confirms unique nullable email key accounts_email_200aa879_uniq and unique school_id; ledger includes 0004_account_email_unique and 0005_student_registration_otp. SQL normalized duplicate groups: 0. Historical preflight also found 0; no records merged/deleted. Existing index effect was verified/reconciled into the 0004 ledger before 0005; all legacy values preserved. Current Student/Instructor OTP paths recheck uniqueness and rely on DB constraints. D-06 OPEN. |
| School Admin review lacks OTP-proof check | Code/automated-test verified | Resolved for approval 18 Nov 2026 (WF-02.03, D-44): approve_registration refuses inside the locked transaction unless the current address has matching proof (409 email_unverified). Rejection does not require proof. D-09 keeps the rest of the legacy transition open. |
| Registration OTP | Code/test-verified implementation | Six-digit CSPRNG code, keyed challenge-bound digest, fixed code/stage expiry, cumulative attempts, bounded resend and replay protection implemented. Simultaneous verify and staged-identity reservation tests passed. Protected executor mode refuses new local Student writes. |
| Staging | Code/DB/test-verified implementation | student_registration_staging installed by 0005. AES-GCM ciphertext holds form data and password hash only; identity/token/OTP digests reserve attempts; no pre-OTP account/profile exists. Ownership/duplicate/cancel tests passed. |
| Abandoned-registration cleanup | Code/DB/test-verified implementation | Expired stages immediately unusable; purge command deletes only expired staging. Local --watch worker started at 60-second intervals; cleanup tests preserve accounts and active stages. Supervised production scheduling remains separate. |
| Email-verification field | Code/DB/test-verified implementation | Installed accounts.email_verified_address and email_verified_at. New Student proof created atomically; legacy values remain NULL. Model, generated migration, SQL review and DB release verified. |
| Registration OTP mail path | Code/test-verified; SMTP connection verified | Registration sender wired; in-memory tests verify code path and failure/zero-send recovery without success claims. Real SMTP connection/authentication succeeded, without sending a real test message. Recipient inbox delivery remains unverified. |
| React rendered page | Code/test/build/HTTP-verified; interactive browser unverified | 34 focused frontend checks passed, including actual component initial server rendering and OTP transport contracts; build passed. HTTP 200 pages and expected cookie-less 410 through real proxy verified. Earlier browser safety blocker remains a limit on interactive/inbox acceptance only. |
| Public applicant support | Code-verified; owner input outstanding | Official support contact – needs owner input in WF-01.01/WF-01.02 and Appendix A/B. Both roles use the shared generic contact-support wording; no configured support action or support metadata is exposed (tests assert retired metadata is absent). No hard-coded official contact; password recovery neither enabled nor bypassed. |
| SRS alignment | Source-reconciled | Local SRS UC-01 and FR-REG-01–03 describe direct Pending/inactive account creation and password protection; no registration OTP requirement was found in that Markdown SRS. OTP staging/proof are workflow additions pending requirements change control. |

### Evidence needed from project owner — remaining only

- WF-01.02 identity, eligibility and conflict/recovery questions are resolved by owner answers. No additional local source/schema file is needed. Official support contact – needs owner input (supply the public email/URL); accepted neutral fallback is active. Human Approval, actual recipient inbox/full human-browser acceptance and protected deployment remain separate.
- No local React/backend source, accounts/users schema output or duplicate-count file is needed: those were inspected directly. This closes the original file requests for the configured development system.
- No additional local schema/index file is required: current development schema/ledger were reconciled and verified during the implementation. Historical index-creation provenance has not been fabricated.
- Need actual recipient-inbox/full interactive browser acceptance before claiming those verification levels. Earlier browser URL determination was the specific UI-access failure. Local frontend/backend and cleanup worker are running for this session.
- Need owner policy sign-off for implemented defaults/mechanisms D-01–D-09 and official public support details. No decision is approved by implementation/test success.
- Protected executor/production deployment requires a reviewed writer/credential/trigger contract, supervised cleanup, independent staging key and environment-specific acceptance. Development findings are not production claims. Human Approval remains unchecked.

## 8. Appendix C – Document control

| Control | Value |
| --- | --- |
| Document | CTU-G Workspace System Workflow Catalogue |
| Version | 0.3.3 |
| Date | 16 November 2026 |
| Status | Working Draft — owner approval pending |
| Scope | WF-01.01 main flow and conflict wording retained; WF-01.02 reconciled to the shared Student feedback (OD-1(a)); owner-approved WF-01 audit corrections recorded; other 60 flow specifications unchanged |
| Approval | No workflow Human Approval recorded; all boxes remain unchecked. Owner-stated implementation requirements/answers are documented without agent policy approval |

### Change log

| Version | Date | Changes | Approval |
| --- | --- | --- | --- |
| 0.1 | 14 November 2026 | Original classification, 62-entry register, WF-02.04 sample, rules and reusable template. | Not recorded |
| 0.2 | 15 November 2026 | Added Actor/Status to register; WF-01.01 detailed specification; 61 placeholders; preserved WF-02.04 as Pending detail; cross-cutting rules; Decisions/Evidence/Document Control appendices; updated template and checklist. | Pending owner approval |
| 0.3 | 15 November 2026 | Added draft WF-13 Group Rating category to classification, register, and detailed-spec section. No new subflow IDs assigned. All 62 existing workflows, WF-01.01 wording, open decisions, and unchecked approvals preserved. | Pending owner approval |
| 0.3.1 | 15 November 2026 | Moved existing WF-13 Group Rating category immediately after WF-07 SSG Financial Management in Section 2 classification, Section 3 workflow register, and Section 4 detailed specifications. Preserved all original 62 flow IDs and the unassigned draft Group Rating scope; no implementation decisions or approvals added. | Pending owner approval |
| 0.3.1 WF-01.01 review | 15 November 2026 | Inspected current registration UI/API/service/model/migration, executor dispatch and approval eligibility; retained owner-confirmed OTP target; corrected stale email evidence; added source/target traceability, acceptance record and decisions D-07–D-09. Documentation only. | OTP sequence confirmed; settings, implementation and final workflow approval pending |
| 0.3.1 WF-01.01 evidence closure | 15 November 2026 | Re-inspected only WF-01.01 references; SELECT/SHOW development DB inspection closed accounts/users schema, unique-index and duplicate-count evidence requests; recorded email-index/0004-ledger discrepancy; confirmed missing OTP/staging/cleanup/proof/mail paths and placeholder public support; mapped inline OPEN items to decisions; repaired moved review links; recorded blocked rendered-page inspection and 11 passing frontend tests; cleared Verified for incomplete target verification. No code, ERD, migration, decision approval or Human Approval changes. | All decisions remain unapproved; WF-01.02 not started |
| 0.3.1 WF-01.01 implementation | 15 November 2026 | Subsequent user instruction authorized implementation: added encrypted Student staging, OTP mail/verify/resend/cancel, atomic account/profile/proof creation, fixed-expiry cleanup, migration 0005 and ERD additions; guarded local release saved encrypted recovery snapshot, verified/reconciled existing 0004 index and applied 0005 preserving legacy values. Initial 121 focused backend checks (22 OTP) and 75 related regressions passed. SMTP connection authenticated; no real recipient test message sent. | Implementation verified locally; policy/Human Approval remain pending; WF-01.02 unchanged |
| 0.3.1 WF-01.01 UI follow-up | 16 November 2026 | Per user instruction removed separate resume verification control and changed Student form action to Proceed Email Verification; Instructor path retained. Final lock-wait expiry regression included: 122 focused backend checks (23 OTP), 34 frontend checks and production build passed; real local routes/proxy smoke-checked. AI checklist completed for documented local verification scope; actual inbox/full browser and protected production rollout remain explicitly unverified. | No decisions or Human Approval approved |
| 0.3.1 WF-01.02 inspection | 16 November 2026 | Owner authorized starting Instructor registration. Inspected catalogue/SRS/UI/API/service/models/writer dispatch/tests; found no defined main flow in the available catalogue and requested the actual steps/version. Recorded direct-registration baseline, neutral duplicates and uncertain recovery concern; 119 backend and 47 frontend checks passed. Checked Inspected only; documented the source blocker. No application code, ERD, migrations or service changes; WF-01.03 untouched. | Main-flow source required; no decisions or Human Approval approved |
| 0.3.1 WF-01.02 completion | 16 November 2026 | Renewed owner instruction authorized completing the AI checklist. Filled placeholder sequence from existing SRS/code/tests; retained direct Instructor creation and neutral HTTP 202; fixed Student-status misuse after uncertain Instructor writes and success-summary focus timing. Final 119 backend, 47 focused frontend and 15 browser checks plus build/lint passed; existing unrelated full-frontend failure reported (135/136 pass). Recorded D-10, completion evidence and all four AI checks within local scope. No ERD, migration, writer/review-gate or production changes; WF-01.03 untouched. | D-10 and Human Approval remain pending; no decision approved |
| 0.3.1 WF-01.02 full-flow acceptance | 16 November 2026 | Followed every current main step, alternative and error row. Added guarded real React/CSRF/API/MySQL/review-read acceptance (1 passed), concurrent HTTP regression and expanded browser recovery/overlap/429 checks (20 passed); expanded backend suite including review/routing boundaries: 147 passed. Eight read-only development DB prerequisite checks passed. Real duplicate responses preserve one original applicant/profile; protected visibility/denial exercised only in isolated tests. Updated evidence/report/checklist scope. Application behavior, ERD, migrations, deployment gates and other flows unchanged in this pass. | Human Approval/D-10 remain pending; no production or human acceptance claim |
| 0.3.1 WF-01.02 owner-target OTP implementation | 16 November 2026 | Owner explicitly authorized Instructor OTP reuse and confirmed Staff ID 1–7, School Admin review only, exact conflict sentence and configured/gated support/recovery. Replaced historical direct sequence with protected staging/OTP/proof; removed school section; retained Student behavior/wording. Reconciled shared rules and fresh SHOW CREATE TABLE/ledger/zero duplicates; no migration/ERD change. Final 164 focused backend, 93 related, 51 focused frontend, 29 browser and one real OTP/CSRF/MySQL/read-handoff scenario passed; build/lint passed. Full frontend 139/140, one known unrelated failure. Updated eleven verification items, footer, register and Appendices A/B/C. Development services/cleanup started and safe proxy 410 checked. | Ready for approval; no agent policy/Human Approval; official support contact needs owner input; WF-01.03 not started |
| 0.3.2 WF-01 audit corrections | 16 November 2026 | Phase 1-2 audit, then owner approval of OD-1(a), OD-2, OD-3 and packages P1-P4 (Human Approval line handling deferred by owner). Reconciled WF-01.02 to the implemented shared Student feedback (retired Instructor sentence/action panel/support configuration), replacing stale D-07/D-13 text and Appendix A/B rows. Code: verification mail sent only after the staging commit with digest-guarded invalidation (R-02); per-identity limits for Student (R-03); status endpoint IP-throttled for both roles (R-04); resumed-attempt notice (R-05); neutral no-session wording (R-06); dead direct-registration branch removed (R-07); accessible Resend label and single error announcement (R-08); pasted-code handling (R-09); request-timeout fallback (R-10); configured code lifetime and spam-folder guidance (OD-3). No ERD, migration, permission or Human Approval change. Evidence in [WF-01 audit corrections record](group_a/WF-01_Audit_Corrections_2026-11-16.md). | Scope owner-approved 16 Nov 2026; Human Approval and D-01-D-09/D-14 policy remain pending |
| 0.3.3 Workflow renumbering | 16 November 2026 | Per owner instruction, renumbered Group Rating from WF-13 to WF-08 (its position after WF-07) and shifted the following categories by one: Announcements & Notifications WF-08→WF-09, Account Concerns & Support WF-09→WF-10, System Administration & Configuration WF-10→WF-11, Audit, Security & Monitoring WF-11→WF-12, Reporting & Document Generation WF-12→WF-13, including all subflow IDs, Next-flow links and cross-references (e.g. D-08 and WF-01.01 Links now cite WF-09.04). Titles, content, statuses and checklists unchanged; Group Rating subflow IDs remain unassigned. Historical change-log rows keep the IDs used at the time. | Pending owner approval |
| 0.3.3 WF-01.03 inspection | 16 November 2026 | Owner instructed continuing WF-01 with read-only inspection and reconciliation of WF-01.03 using the existing Section 4 layout and the six-stage checklist (Inspect → Reconcile → Approve → Implement → Test → Commit). Filled the WF-01.03 specification from code, tests and the SRS (git HEAD); recorded proposals P-01 to P-06, decisions D-15 to D-19 and baseline test evidence (14 backend, 9 frontend, all passed). WF-01.03 Guidelines and checklist use the six-stage sequence; other flows unchanged. No application code, ERD or migration changes. | Approval of WF-01.03 pending; Human Approval unchecked |
| 0.3.3 WF-01.03 implementation | 16 November 2026 | Owner approved WF-01.03 ("I approve the wf-01.03"). Implemented P-01 (specific sign-in feedback, approval hint, countdown, security refresh, session confirmation after unknown outcomes, password cleared), P-02 ("School ID or Staff ID" label, maxLength), P-03 (signed-in view with Continue to Dashboard and Sign Out), P-04 (X-Request-ID on authentication responses) and P-05 (per-identity login budget before authentication, no lockout). Added 4 backend, 6 unit and 7 browser tests. Updated WF-01.03 status, flows, errors, checklist and evidence, D-15/D-16 and Appendix B. No ERD, migration, permission or settings change. P-06/D-17 still blocked. | Specification owner-approved; Human Approval unchecked |
| 0.3.3 WF-01.03 commit receipt | 16 November 2026 | Recorded implementation commit 66c1301 and ticked Committed in the WF-01.03 checklist. | Human Approval unchecked |
| 0.3.3 WF-01.04 inspection | 16 November 2026 | Owner instructed "proceed with wf-01.04" and supplied a draft. Reconciled the draft against the code read-only: kept its intent, replaced unverified items with findings, corrected the security-event link to WF-12.01 (renumbered) and the unverified role names. Recorded proposals P-01 to P-05 and existing test evidence. No application code, ERD or migration changes. | Approval of WF-01.04 pending; WF-01.03 Human Approval unchecked |
| 0.3.3 WF-01.04 implementation | 16 November 2026 | Owner approved P-01 to P-05 with safeguards S-1 to S-5. Implemented confirmed sign-out (session read after uncertain results; a failed read stays uncertain), history replacement plus restored-page recheck, data-free BroadcastChannel notice plus visibility recheck, and a 401-only session recheck (403 never signs out). Added 4 backend, 5 unit and 8 browser tests; server-side logout behavior needed no code change. Updated WF-01.04 status, flows, errors, checklist, evidence and Appendix B. No backend application code, ERD, migration, permission or settings change. | Specification owner-approved; Human Approval unchecked |
| 0.3.3 WF-01.04 commit receipt | 16 November 2026 | Recorded implementation commit f5eaace and ticked Committed in the WF-01.04 checklist. | Human Approval unchecked |
| 0.3.3 WF-01.05 inspection | 16 November 2026 | Owner supplied a WF-01.05 draft. Reconciled it against the code read-only: kept its intent, replaced unverified items with findings, corrected the identifier (School ID plus registered email), the button name, and the renumbered links (WF-09.04, WF-12.01). Recorded proposals P-01 to P-07, decisions D-20 to D-24 and baseline test evidence (6 backend, 3 frontend, all passed). No application code, ERD, migration or gate change. | Approval of WF-01.05 pending; WF-01.03 and WF-01.04 Human Approval unchecked |
| 0.3.3 WF-01.05 second reconciliation | 16 November 2026 | Owner asked to reconcile P-01 to P-07 and D-20 to D-24 further before implementation. Evaluated outbox reuse for D-20 (not reusable without an ERD change), legacy recovery for D-21 (no assisted path exists; options A to C), commit-only notice timing for D-22, the Django token for D-23 (no gap; unchanged), the gate and executor mode for D-24, and session invalidation (probe-verified, including executor-proof sessions). Found the shared request and reset rate-limit counter. A temporary probe test was run and deleted. No application code, ERD, migration or gate change; Human Approval for WF-01.03 to WF-01.05 left unchecked. | Approval of WF-01.05 pending |
| 0.3.3 WF-01.05 implementation | 16 November 2026 | Owner approved P-01 to P-07 with D-20 option (a) for development only, D-21 option A, D-22, D-23 and D-24 (recovery stays disabled). Implemented verified-email eligibility, a bounded background sender, a post-commit password-changed notice, a per-identity request budget and separate reset counters, allowlisted field errors and reset_link_invalid, uncertain-outcome handling, the Staff ID label, an assisted-recovery hint, and an explicit protected-executor refusal. Added 15 backend, 4 unit and 7 browser tests. Updated WF-01.05, Appendix A (D-16, D-20 to D-24), Appendix B and the register. No ERD, migration, model or settings change; gate default unchanged. | Implementation owner-approved; Human Approval unchecked |
| 0.3.3 WF-01.05 commit receipt | 16 November 2026 | Recorded implementation commit 8a96162 and ticked Committed in the WF-01.05 checklist. | Human Approval unchecked |
| 0.3.3 WF-01.05 change request CR-01 | 16 November 2026 | Owner requested an email-only request and a verification-code flow. Explained the missing development email (0 accounts eligible under D-21). Recorded CR-01 proposals P-08 to P-13 and decisions D-25 to D-28 inside WF-01.05; verified the existing password_reset_token columns are installed and unused. No application code changed; the committed link-based flow remains in effect until CR-01 is approved. | CR-01 approval pending |
| 0.3.3 WF-01.05 CR-01 specification | 16 November 2026 | Owner approved D-25, D-26 and D-28 and asked for D-27 to be reconciled. Rewrote the WF-01.05 header, main flow, alternative flows, errors, links, checklist, blockers and evidence for the email-OTP flow (proposed, not implemented); kept the link-based history and D-20 to D-24, marking the superseded reset-link behavior. Recorded the D-27 reconciliation and exact proposed implementation. Checklist now tracks CR-01: Inspected and Reconciled only. No application code, ERD, migration or gate change. | D-27 approval pending; Human Approval unchecked |
| 0.3.3 WF-01.05 CR-01 implementation | 17 November 2026 | Owner approved D-27 with the HttpOnly-cookie ticket. Implemented the email-OTP recovery: email-only request, 6-digit code stored as an HMAC in the existing password_reset_token columns, cumulative attempts that resends do not reset, 60-second resend, 30-minute window, row-locked verification issuing a single-use 10-minute ticket cookie, and a row-locked password change that clears the record; new endpoint POST /api/v1/auth/forgot-password/verify/; three-step /forgot-password page; /reset-password points to Forgot Password. Fixed a latent serializer bug found by testing. Rewrote the recovery tests (26 backend, 8 unit, 8 browser). Updated WF-01.05, register, Appendix A (D-23, D-25 to D-28) and Appendix B. No ERD, migration, model or settings change; gate default unchanged. | Implementation owner-approved; Human Approval unchecked |
| 0.3.3 WF-01.05 CR-01 commit receipt | 17 November 2026 | Recorded implementation commit da9e480 and ticked Committed in the WF-01.05 checklist. | Human Approval unchecked |
| 0.3.3 WF-01.05 owner acceptance | 17 November 2026 | Owner authorized database changes; the agent approved development account 7241423 (Approved, active, Student role) in one transaction without altering its genuine email proof and without a review or audit record. The owner then tested the email-OTP recovery with real Gmail delivery and reported "passed". Recorded in WF-01.05 Evidence level and Appendix B. | Human Approval unchecked |
| 0.3.3 WF-01.06 inspection | 17 November 2026 | Owner requested a full Inspect and Reconcile of WF-01.06. Filled WF-01.06 in the existing structure with the 16-case reconciliation (expected, actual, tests, gaps, corrections), proposals P-01 to P-07 with exact files and settings, quality considerations, and evidence (Django defaults, read-only session count, 64/64 baseline). Updated D-18 and added D-29 and D-30 in Appendix A, plus Appendix B and the register. No timeout values invented. No application code, ERD, migration or settings change; Approve to Commit and Human Approval unchecked; WF-02.01 not started. | Approval of WF-01.06 pending |
| 0.3.3 WF-01.06 implementation | 17 November 2026 | Owner approved P-01 to P-07 with D-18 (30-minute idle, 8-hour absolute, DEBUG off by default, HTTPS mandatory in production), D-29 (HttpOnly CSRF cookie), D-30 (daily clearsessions) and no polling. Implemented security_settings.py, session_timeout.py (login stamp, idle and absolute expiry, legacy fail-safe, 503 on store outage), settings and middleware wiring, the session-ended message and runbook sections 5A and 5B; added 22 backend tests and 4 browser scenarios. Recorded the separate pinned-catalogue finding. No ERD, migration, endpoint, JWT or .env change. Not committed; Human Approval unchecked. | Commit awaits owner review |
| 0.3.3 WF-01.06 verification | 17 November 2026 | Owner authorized restoring the two deleted pinned catalogue proposals: restored byte-exact from 9594a02 into the working tree (untracked; pins verified), test_catalogue 61/61. Found that a third pinned file (SRS v1, CRLF pin) is also missing, leaving 103 catalogue-v2 failures; not restored (outside scope). Diagnosed the 3 decision-email failures (unpinned WORKSPACE_PUBLIC_BASE_URL plus a LAN .env; 7/7 with localhost; same failures at the pre-WF-01.06 baseline) and the dashboard failure (stale AR-6C7D2 assertion superseded by AR-6C7E.1). Ran a 15/15 real-stack interactive verification including exact idle and absolute boundaries. Updated WF-01.06 evidence, blockers and checklist scope. No commit; Human Approval unchecked. | Commit awaits owner review |
| 0.3.3 WF-01.06 repository corrections | 17 November 2026 | Owner authorized restoring the pinned sources and test-only fixes. Commit 23f9b8e: restored five pinned catalogue sources byte-exact (SRS as CRLF, four documents as LF) and added path-scoped -text .gitattributes rules. Commit f32a526: pinned the decision-email test environment and updated the stale dashboard assertion for AR-6C7E.1. All suites pass (1081, 426, 164, 63). | WF-01.06 commit follows; Human Approval unchecked |
| 0.3.3 WF-01.06 commit receipt | 17 November 2026 | Recorded the three authorized local commits: 23f9b8e (repository repair), f32a526 (test-only corrections) and 9a56fd9 (WF-01.06). Ticked Committed. Not pushed. | Human Approval recorded |
| 0.3.3 WF-01 Human Approval | 17 November 2026 | Owner instructed "tick all the human approval, i approved". Recorded Human Approval for WF-01.01 (as the owner had written: Ronald Arias, 11/16/2026) and WF-01.02 to WF-01.06 (Ronald C. Arias, 11/17/2026, matching the owner's own WF-01.06 entry). Updated the register and the current Status and Blocked-by statements; historical inspection notes unchanged. Restored the catalogue from 9a56fd9 first, because an older open editor tab had been saved over the latest version. The WF-01.01 and WF-01.02 "Tested" checklist boxes were not changed. | Owner-approved |
| 0.3.4 WF-02.01 inspection | 17 November 2026 | Owner requested Inspect and Reconcile of WF-02.01. Filled WF-02.01 in the WF-01 structure (checklist Inspect → Reconcile → Approve → Implement → Test → Commit) with R-01 to R-17, proposals P-01 to P-08, main/alternative flows and errors; added D-31 to D-36, the register status and an Appendix B row. No code, ERD, migration, settings or database change; other entries unchanged; Approve to Commit and Human Approval unchecked; WF-02.02 not started. | Approval of WF-02.01 pending |
| 0.3.4 WF-02.01 implementation | 17 November 2026 | Owner approved P-01 to P-08 with D-31 to D-36 (D-34, D-35 with clarifications). Implemented the read-only list, its switches, server-side search, filters, sort and has_next, the name and proof fields, the per-account limit and the panel; added and updated tests; recorded Implementation basis, deviations, FU-02.01-A, evidence and the decision statuses. Ticked Approved to Committed; Human Approval unchecked; WF-02.02 not started. | Human Approval of WF-02.01 pending |
| 0.3.4 WF-02.01 safeguard correction | 17 November 2026 | First full regression after implementation: 134 failures from one cause (release tooling refused any mounted registration-review-pending route). Owner authorized Option A and the three protected files, then the three outdated recovery-test assertions (2 failures surfaced by the re-run). Narrowed the P1 and P3C safeguard to tolerate only the exact GET-only list while its switch is off; decision, bulk, altered, duplicate, unknown and uninspectable routes still refuse. Added 14 safeguard tests and updated the 3 recovery assertions; re-ran all suites. Updated Main flow, Alternative flows, Errors, Links and Evidence. | Human Approval of WF-02.01 pending |
| 0.3.5 Dashboard Shell v0.1 | 17 November 2026 | Owner asked to revise the dashboard to the docs/design references and chose the full Dashboard Shell v0.1 (draft) with a count-free Pending applications card. Frontend only: one shared shell (full-width header with brand and academic-period context, permission-filtered grouped sidebar with collapse and an accessible drawer, breadcrumbs, page header, user menu, shared states). WF-02.01 is now reached as Account operations → Applicant reviews; Main flow steps 1–2 and A6 updated. No backend, permission, ERD or workflow-scope change; other entries unchanged. | Owner review of the shell pending |
| 0.3.6 WF-02.02 inspection | 17 November 2026 | Owner requested Inspect and Reconcile of WF-02.02. Filled WF-02.02 in the existing structure (checklist Inspect → Reconcile → Approve → Implement → Test → Commit) with R-01 to R-14, proposals P-01 to P-08, flows, errors and required tests; added D-37 to D-43, the register status and an Appendix B row. Reported, without changing it, that the WF-02.01 Human Approval is ticked in the working copy but uncommitted while its register and change-log rows still say pending. No code, ERD, migration, settings or data change; WF-02.03 not started. | Approval of WF-02.02 pending |
| 0.3.6 WF-02.01 Human Approval reconciliation | 17 November 2026 | The owner's Human Approval line for WF-02.01 (Ronald C. Arias, November 17,2026), committed by the owner in 5ca1062, was preserved exactly. Reconciled the stale WF-02.01 register row, Status row and Blocked-by line that still said "Human Approval pending"; earlier change-log rows are kept as the historical record. No other WF-02.01 evidence changed. | Human Approval recorded |
| 0.3.6 WF-02.02 implementation | 17 November 2026 | Owner approved P-01 to P-08 with D-37 to D-43, including the D-41 protected-file authorization. Implemented the GET-only applicant detail, the shared eligibility filter, the narrowed two-route release safeguard and the in-view detail page; added 19 backend, 5 safeguard, 4 unit and 8 browser tests; recorded implementation basis, evidence and decision statuses. Ticked Approved to Committed; Human Approval unchecked pending the owner's review; WF-02.03 not started. | Human Approval of WF-02.02 pending |
| 0.3.6 WF-02.02 Human Approval | 17 November 2026 | Owner reviewed the finished WF-02.02 and approved it. Recorded Human Approval (Ronald C. Arias, November 17, 2026); updated the register, Status, checklist scope and Blocked-by statements. Implementation, test and commit evidence (5e7a2c6) unchanged. D-09 and D-12 stay OPEN for WF-02.03; WF-02.03 not started. | Human Approval recorded |
| 0.3.7 WF-02.03 inspection | 17 November 2026 | Owner requested Inspect and Reconcile of WF-02.03. Filled WF-02.03 in the existing structure with R-01 to R-16, proposals P-01 to P-09, flows, errors and required tests; added D-44 to D-51, the register status and an Appendix B row. Noted that Announcements & Notifications is WF-09 and Audit, Security & Monitoring is WF-12 in this catalogue. No code, ERD, migration, settings or data change; WF-02.04 not started. | Approval of WF-02.03 pending |
| 0.3.7 WF-02.03 implementation | 18 November 2026 | Owner authorized P-01 to P-09 with D-44 to D-51 on 17 November 2026, then the narrow protected audit.py change (D-52) and the bulk decision (D-53). Implemented the verified-email and attestation policy, the attestation-only approve API with 409 refusals, the approval-event audit contract, the D-51 executor refusal, the shared Modal and feedback tokens, and the approval section of the WF-02.02 detail; adjusted approval fixtures and bulk tests as recorded; added 41 backend, 11 unit and 8 browser tests; updated D-09, D-12 and the Appendix B gap only as covered by the approved policy. config.urls, release safeguard, P1–P4, executor and writer boundary unchanged; no migration or ERD change; nothing pushed. Human Approval left unchecked. | Human Approval pending |
| 0.3.7 WF-02.03 acceptance reconciliation | 18 November 2026 | Owner requested final acceptance reconciliation of b974087. Inspection confirmed the owner's conditions for the ninth (test_task1_reapplication) bulk-test change, which the owner then accepted; recorded lint accurately as failing on the pre-existing ThemeToggle.tsx:17 baseline error, and the owner's documented baseline exception for WF-02.03 only (the two unchanged findings; not a pass, not a general exception). Documentation only; no code change. Other uncommitted catalogue drafts preserved. | Owner acceptances recorded |
| 0.3.7 WF-02.03 Human Approval | 18 November 2026 | Owner reviewed the finished WF-02.03 and approved it, confirming that they made the Human Approval entry (Ronald C. Arias, November 18, 2026). Updated the register, Status, checklist scope, Blocked-by and Appendix B statements. Implementation, test and commit evidence (b974087) unchanged. D-50 (SRS AT-02 UNMET) and the protected-executor production blocker stay open; WF-02.04 not started. | Human Approval recorded |
| 0.3.9 WF-02.04 inspection | 18 November 2026 | Owner requested Inspect and Reconcile of WF-02.04. Filled WF-02.04 in the existing structure with R-01 to R-17, proposals P-01 to P-10, flows, errors and required tests; added D-54 to D-62, the register status and an Appendix B row; ticked Inspect and Reconcile only. Kept the other editor's standardized WF-02.04 footer lines and the preserved v0.1 sample. Numbered 0.3.9 because an uncommitted 0.3.8 row from another editor exists. No code, ERD, migration, settings or data change; no commit; WF-02.05 not started. | Approval of WF-02.04 pending |
| 0.3.9 WF-02.04 stage 1 implementation | 18 November 2026 | Owner authorized stage 1 with D-54 to D-62 (D-55 revised). Implemented the mandatory outbox and v2 template, the verified-recipient rule, fixed 409 conflicts, the queued-only success reply and the rejection section with a destructive confirmation dialog; added 31 backend, 11 unit and 9 browser tests (all passing); recorded 30 conflicting existing tests and the protected changes for separate approval. Ticked Approve only; Implement, Test, Commit and Human Approval unticked; not committed. | Stage 1 awaiting approvals |
| 0.3.9 WF-02.04 stage 2 implementation | 18 November 2026 | Owner approved the 30 test corrections and the protected changes. Corrected the tests as recorded; enabled the outbox and v2 template in local review and sandbox settings with in-memory mail; added terminal-state recipient erasure to the outbox worker and restricted the executor trigger and grant to it; disabled reapplication in both executor settings; added 25 tests; full regression passed; recorded the WF-02.04-only lint baseline exception, the remaining retention question and the reapplication removal proposal. Ticked Implement, Test and Commit; Human Approval unticked; committed locally, not pushed. | Human Approval pending |
| 0.3.9 WF-02.04 Human Approval | 18 November 2026 | Owner approved WF-02.04 for completed local development (implementation commit fac37a9), accepting the reported test results and the WF-02.04-only baseline lint exception. Recorded Human Approval (Ronald C. Arias, November 18, 2026); updated the register, Status, checklist scope, Blocked-by and Appendix B statements; recorded that queueing does not guarantee delivery and that terminal Dead notifications need an approved operational policy before production. Production rejection, retention policies, legacy-account cleanup and full reapplication removal stay open. Implementation, test and commit evidence unchanged; WF-02.05 not started. | Human Approval recorded (local development only) |
| 0.3.10 WF-02.05 inspection | 18 November 2026 | Owner requested Inspect and Reconcile of WF-02.05. Filled WF-02.05 in the existing structure with R-01 to R-12, proposals P-01 to P-12, flows, errors and required tests; added D-63 to D-71, the register status and an Appendix B row; ticked Inspect and Reconcile only. Confirmed the restored docs/workflows/group_a documents match HEAD. No code, ERD, migration, settings or data change; no commit; WF-02.06 not started. | Approval of WF-02.05 pending |
| 0.3.10 WF-02.05 stage 1 implementation | 18 November 2026 | Owner reconciled D-63 to D-71 (D-63 revised) and authorized application-level stage 1. Implemented the account-status service, the schema-free session epoch and post-login re-check, the isolated API URLconf and the account directory with status controls behind default-off switches; added 23 backend, 8 unit and 8 browser tests; recorded the protected changes needed to run it (mounting, governed permission rows, production executor parity). Ticked Approve only; not committed. | Protected authorizations pending |
| 0.3.10 WF-02.05 stage 2 | 18 November 2026 | Owner authorized local-only stage 2. Mounted the account-status API in the local review and sandbox URLconfs and enabled its switch in those settings only; verified D-66 over real HTTP in both, the epoch's integrity and cost, and the release safeguard; added 21 tests; recorded the WF-02.05-only lint baseline exception. Stopped at two protected boundaries (governed provisioning unsupported by P1/P2/P4; safeguard detection gap for opaque wrappers) with exact proposals. Not committed. | Protected authorizations pending |
| 0.3.10 WF-02.05 stage 3 | 18 November 2026 | Owner authorized the governed provisioning companion and the safeguard amendment. Implemented provision_school_accounts_local_dev (metadata, bindings, activate, verify) and the safeguard amendment; added 7 provisioning tests and 4 safeguard cases; full regression run. Stopped before applying provisioning to ctug_workspace and before committing: applying it would permanently disable the registration-review P4 compensation path (P3B snapshot), which needs a separate owner decision. | Protected decision pending |
| 0.3.10 WF-02.05 stage 3A | 18 November 2026 | Owner selected Option A conditionally. Narrow protected change to the P3B snapshot only: it tolerates exactly the three governed school-account definitions and their Admin bindings, proven by their receipts and recorded after the release; it keeps every registration-scope check; P4 compensation acts only on the registration rows and is refused while a WF-02.05 deactivation would be stranded. Added 17 compatibility tests and retired the obsolete dependency test; governance, safeguard and full regression run. Provisioning in ctug_workspace not run; not committed. | Owner decision on commit and live provisioning pending |
| 0.3.10 WF-02.05 stage 3B | 18 November 2026 | Owner approved stage 3A and authorized a local commit and read-only verification. Committed the WF-02.05 implementation locally as f476294 (not pushed). Verified ctug_workspace read-only (no --apply, no write phase, checksums unchanged): registration-review release complete and attributable, no school-account rows or conflicts, operator account 3 eligible, verify refusing as expected before metadata, P4 compensation available. Provisioning not authorized and not run. | Provisioning authorization and Human Approval pending |
| 0.3.10 WF-02.05 stage 3C | 18 November 2026 | Owner authorized governed local provisioning. Verified the preconditions and a restore-tested backup, then ran metadata, bindings and activate with verify after each: 3 permissions, 3 active Admin bindings and 9 receipts in ctug_workspace; nothing else changed; P4 compensation preview available (not executed). Read-only security checks over the real data and a new isolated role-coverage test; security regression run. Ticked Implement and Test (local development only). | Human Approval pending |
| 0.3.10 WF-02.05 Human Approval | 18 November 2026 | Owner approved WF-02.05 as completed for local development only (implementation f476294; documentation ce784e8 and 53f0616; final test 85212e4), on the reported implementation, provisioning, security and regression evidence. Recorded Human Approval (Ronald C. Arias, November 18, 2026); updated the register, Status, checklist scope, Blocked-by and Appendix B; corrected the stale stage 3C test note and the account_status_urls.py module docstring (no behavior change). Open: production activation and deactivation blocked; P4 compensation can disable the shared accounts service and is refused while a WF-02.05 deactivation would be stranded; D-67, V2-06 and V2-08 unresolved; no live status change on real accounts; the two frontend lint findings under the WF-02.05-only exception; full Account Management regression at WF-02.06. WF-02.06 not started. | Human Approval recorded (local development only) |
| 0.3.11 WF-02.06 inspection | 18 November 2026 | Owner requested Inspect and Reconcile of WF-02.06. Filled WF-02.06 in the existing structure with the inspection basis, a documentation traceability table, R-01 to R-14, proposals P-01 to P-04, flows, errors, links and the full WF-02 category regression plan; added D-72 to D-78, the register status and an Appendix B row; ticked Inspect and Reconcile only. Read-only checks of ctug_workspace. No code, ERD, migration, settings or data change; no commit; WF-03.01 not started. | Approval of WF-02.06 pending |
| 0.3.11 WF-02.06 implementation | 18 November 2026 | Owner approved D-72 to D-78 (D-75 with clarification, D-78 conditional) and authorized implementation. Implemented the detail status dates, one read-only allowlisted history endpoint and the Account status and Status history sections; added 12 backend, 5 unit and 5 browser tests and updated two exact WF-02.05 contract assertions and the safeguard matrix; ran focused, real-data read-only and the full WF-02 category regression; recorded the WF-02.06-specific lint exception. Ticked Approve, Implement and Test. | Human Approval pending |

### Workflow ID mapping (old → new)

Version 0.3.3 renumbered categories WF-08 to WF-13: Group Rating (formerly WF-13, a draft category with no subflow IDs) is now WF-08, and the former WF-08 to WF-12 subflows each moved up one category number. WF-01 to WF-07 IDs are unchanged. WF-01.01 and WF-01.02 title cleanups are recorded; the remaining original titles are preserved.

| Old ID (v0.1) | Current ID (v0.3.3) | Change |
| --- | --- | --- |
| WF-01.01 | WF-01.01 | Title cleaned to “Register Student Account” |
| WF-01.02 | WF-01.02 | Title clarified to Register Instructor Account per owner task; ID unchanged |
| WF-01.03 | WF-01.03 | ID and title unchanged |
| WF-01.04 | WF-01.04 | ID and title unchanged |
| WF-01.05 | WF-01.05 | ID and title unchanged |
| WF-01.06 | WF-01.06 | ID and title unchanged |
| WF-02.01 | WF-02.01 | ID and title unchanged |
| WF-02.02 | WF-02.02 | ID and title unchanged |
| WF-02.03 | WF-02.03 | ID and title unchanged |
| WF-02.04 | WF-02.04 | ID and title unchanged |
| WF-02.05 | WF-02.05 | ID and title unchanged |
| WF-02.06 | WF-02.06 | ID and title unchanged |
| WF-03.01 | WF-03.01 | ID and title unchanged |
| WF-03.02 | WF-03.02 | ID and title unchanged |
| WF-03.03 | WF-03.03 | ID and title unchanged |
| WF-03.04 | WF-03.04 | ID and title unchanged |
| WF-03.05 | WF-03.05 | ID and title unchanged |
| WF-03.06 | WF-03.06 | ID and title unchanged |
| WF-04.01 | WF-04.01 | ID and title unchanged |
| WF-04.02 | WF-04.02 | ID and title unchanged |
| WF-04.03 | WF-04.03 | ID and title unchanged |
| WF-04.04 | WF-04.04 | ID and title unchanged |
| WF-04.05 | WF-04.05 | ID and title unchanged |
| WF-05.01 | WF-05.01 | ID and title unchanged |
| WF-05.02 | WF-05.02 | ID and title unchanged |
| WF-05.03 | WF-05.03 | ID and title unchanged |
| WF-05.04 | WF-05.04 | ID and title unchanged |
| WF-06.01 | WF-06.01 | ID and title unchanged |
| WF-06.02 | WF-06.02 | ID and title unchanged |
| WF-06.03 | WF-06.03 | ID and title unchanged |
| WF-06.04 | WF-06.04 | ID and title unchanged |
| WF-06.05 | WF-06.05 | ID and title unchanged |
| WF-07.01 | WF-07.01 | ID and title unchanged |
| WF-07.02 | WF-07.02 | ID and title unchanged |
| WF-07.03 | WF-07.03 | ID and title unchanged |
| WF-07.04 | WF-07.04 | ID and title unchanged |
| WF-07.05 | WF-07.05 | ID and title unchanged |
| WF-07.06 | WF-07.06 | ID and title unchanged |
| WF-07.07 | WF-07.07 | ID and title unchanged |
| WF-07.08 | WF-07.08 | ID and title unchanged |
| WF-08.01 | WF-09.01 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-08.02 | WF-09.02 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-08.03 | WF-09.03 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-08.04 | WF-09.04 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-08.05 | WF-09.05 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-09.01 | WF-10.01 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-09.02 | WF-10.02 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-09.03 | WF-10.03 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-09.04 | WF-10.04 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-10.01 | WF-11.01 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-10.02 | WF-11.02 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-10.03 | WF-11.03 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-10.04 | WF-11.04 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-11.01 | WF-12.01 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-11.02 | WF-12.02 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-11.03 | WF-12.03 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-11.04 | WF-12.04 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-11.05 | WF-12.05 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-12.01 | WF-13.01 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-12.02 | WF-13.02 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-12.03 | WF-13.03 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-12.04 | WF-13.04 | Renumbered (Group Rating became WF-08); title unchanged |
| WF-13 (category added v0.3) | WF-08 | Group Rating category renumbered; no subflow IDs assigned |

Document control note: Proposed structure only. Review with project stakeholders before designating workflow definitions as approved requirements.
