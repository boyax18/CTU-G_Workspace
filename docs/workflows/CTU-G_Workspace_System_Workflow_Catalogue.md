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
| WF-02.01 | View pending applications | Not yet inspected | Draft |
| WF-02.02 | Verify and review applicant information | Not yet inspected | Draft |
| WF-02.03 | Approve applicant account | Not yet inspected | Draft |
| WF-02.04 | Reject applicant, notify by email, and delete rejected registration data | Not yet inspected | Draft |
| WF-02.05 | Activate or deactivate an existing account | Not yet inspected | Draft |
| WF-02.06 | View account status and permitted history | Not yet inspected | Draft |

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

Next flow: WF-02.02. Do not start until Approved is ticked.

#### WF-02.02 — Verify and review applicant information

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

Next flow: WF-02.03. Do not start until Approved is ticked.

#### WF-02.03 — Approve applicant account

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

Next flow: WF-02.04. Do not start until Approved is ticked.

#### WF-02.04 — Reject applicant, notify by email, and delete rejected registration data

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

#### Pending detail — preserved from v0.1 sample; not inspected or approved

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

Guidelines: Inspect → Reconcile → Clean → Verify → Approve → Continue

AI Agent Checklist: ☐ Inspected   ☐ Reconciled   ☐ Tested   ☐ Cleaned   ☐ Verified

Blocked by: Unknown – needs confirmation

Evidence level: Unknown – needs confirmation

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-02.05. Do not start until Approved is ticked.

#### WF-02.05 — Activate or deactivate an existing account

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

Next flow: WF-02.06. Do not start until Approved is ticked.

#### WF-02.06 — View account status and permitted history

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
| D-09 | Review eligibility and existing unverified Pending accounts | New Student/Instructor public registrations save proof atomically after OTP; legacy proof remains NULL | WF-02 eligibility/legacy transition remains separately reviewed; no WF-02 code/gates changed | Registration proof IMPLEMENTED — Code/DB/test-verified; existing shared review gates unchanged; legacy/cross-flow policy OPEN | Project owner |WF-01.01; WF-02.01; WF-02.03; WF-01.02 |
| D-10 | Instructor registration sequence | Owner-stated OTP before Pending account/profile, sharing protected staging and proof with Student; role stored in existing encrypted payload | Historical direct-to-Pending/neutral-202 baseline, now superseded by owner instruction | IMPLEMENTED/test-verified in development; owner-stated requirement recorded, no agent approval; Human Approval pending | Project owner | WF-01.02 |
| D-11 | Instructor identity | Owner-stated Staff ID, 1–7 ASCII digits, mapped to unique existing accounts.school_id; leading zeroes retained | Separate employee identity/format would require new owner/schema review | Owner answer recorded; Code/DB/test-verified; no migration or agent policy approval | Project owner | WF-01.02 |
| D-12 | Instructor eligibility verification | Owner-stated School Admin review only; OTP proves email access, not employment | Separate authoritative HR/verification process would require specified source/contract | Owner answer recorded; shared review service/gates retained; no agent policy approval | Project owner | WF-01.02; WF-02.01; WF-02.03 |
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
| Public Student registration | Code/test-verified; behavior retained | Approved Student OTP sequence, existing payloads, cookie ownership and conflict wording retained. All 30 unchanged Student OTP tests passed standalone and within the final focused suite. Instructor reuse is separately documented under WF-01.02; historical Student release evidence remains in its implementation record. |
| /register route | Code/test/HTTP-verified | App routes /register and /register/verify; VerifyEmailPage implements code entry, resend, cancel, errors and confirmation. Student button is Proceed Email Verification; separate resume control removed. Initial component server rendering and live route HTTP 200 verified. |
| Pending/inactive state | Code/DB/test-verified | Correct OTP atomically creates account/profile with Pending/inactive state and verified address/time; no AccountRole/login. Wrong/expired/replayed codes and transaction failure create no partial permanent records. Existing development records preserved; no real applicant created by verification work. |
| School ID uniqueness | Code/DB-verified | Account field and DBML specify uniqueness; public serializer accepts 1–7 ASCII digits. SHOW CREATE TABLE accounts confirms unique school_id index. Evidence gap closed for development DB. |
| Email uniqueness | Code/DB/test-verified | Fresh read-only SHOW CREATE TABLE accounts confirms unique nullable email key accounts_email_200aa879_uniq and unique school_id; ledger includes 0004_account_email_unique and 0005_student_registration_otp. SQL normalized duplicate groups: 0. Historical preflight also found 0; no records merged/deleted. Existing index effect was verified/reconciled into the 0004 ledger before 0005; all legacy values preserved. Current Student/Instructor OTP paths recheck uniqueness and rely on DB constraints. D-06 OPEN. |
| School Admin review lacks OTP-proof check | Code-verified | Current registration_review.py eligibility checks Pending/inactive state and requested base role, but no email-verification proof. D-09 records the transition gap. |
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
