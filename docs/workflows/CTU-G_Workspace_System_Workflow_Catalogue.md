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
| WF-01.01 | Register Student Account | Student Applicant (public) | Implemented and locally verified; Human Approval pending |
| WF-01.02 | Register Instructor Account | Instructor Applicant (public) | Instructor OTP implemented and development-verified; Ready for approval |
| WF-01.03 | Login and session establishment | Approved Workspace account holder (public endpoint) | Owner-approved; P-01 to P-05 implemented and tested; Human Approval pending |
| WF-01.04 | Logout and session termination | Any account holder with a valid Workspace session | Owner-approved; P-01 to P-05 implemented and tested; Human Approval pending |
| WF-01.05 | Forgot-password request and reset | Approved account holder who cannot sign in (public, gated) | Owner-approved; P-01 to P-07 implemented and tested; gate off; Human Approval pending |
| WF-01.06 | Session expiry and CSRF handling | Not yet inspected | Draft |

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

Human Approval: ☐ Approved by: Ronald Arias  Date: 11/16/2026

Next flow: WF-01.02. Do not start until Approved is ticked.

#### WF-01.02 — Register Instructor Account

| Field | Definition |
| --- | --- |
| Actor | Instructor Applicant (public registration; no permission needed) |
| Trigger | Applicant submits the Instructor registration form |
| Preconditions | Registration and OTP email service are available; requested Instructor role is active; existing CSRF, rate and permitted-writer checks pass |
| Result | After OTP, one email-verified Pending/inactive Instructor account and linked profile await School Admin review; no role or authenticated session is created |
| Status | Implemented and verified in development against the owner-stated OTP target on 16 November 2026, with the owner's later instruction to adopt Student error feedback/response ([consistency report](group_a/WF-01.02_Feedback_Consistency.md)) and the owner-approved audit corrections ([WF-01 audit corrections record](group_a/WF-01_Audit_Corrections_2026-11-16.md)). Ready for approval; Human Approval remains unchecked. |

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

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-01.03. Do not start until Approved is ticked.

#### WF-01.03 — Login and session establishment

| Field | Definition |
| --- | --- |
| Actor / required permission | Approved Workspace account holder: Student, Instructor, or any account with at least one active assigned role. The login endpoint is public, so no permission code is needed to attempt it. Django framework staff and superuser accounts are refused here and use /admin/ only (ADR-001). |
| Trigger | The user submits School ID (Staff ID for Instructors, the same field; D-11) and password on the home-page sign-in card (/#login), which sends POST /api/v1/auth/login/. |
| Preconditions | The account exists with request_status Approved and is_active true, and holds at least one AccountRole whose role is active. It is not is_staff or is_superuser. The browser has a CSRF token from GET /api/v1/auth/csrf/ and the request comes from a trusted origin. The per-IP login throttle has not been exceeded. |
| Result | Django creates a server-side session (HttpOnly session cookie) for the account. The response returns school_id, the sorted active role names and the current effective permission codes as UI hints only. The browser opens /dashboard, which reads GET /api/v1/auth/session/ again. Login creates no role, permission or approval, and stores no grants in the session. |
| Status | Inspected and reconciled 16 November 2026, then approved by the owner the same day ("I approve the wf-01.03"). P-01 to P-05 are implemented and verified by automated backend, frontend and browser tests. P-06 (authentication events, D-17) stays blocked pending an approved contract. D-18 is deferred to WF-01.06 and D-19 is recorded without code change. Human Approval of the finished flow remains unchecked. |

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

Blocked by: No remaining development implementation blocker for P-01 to P-05. Open: D-17 authentication-event contract (P-06; plus ERD review if storage is required); production cookie, HTTPS and DEBUG settings (D-18, WF-01.06); shared cache and trusted-proxy deployment for the throttles (D-16); session deletion and limits (D-19); policy sign-off of the D-16 values. WF-01.02 Human Approval is still unchecked; the owner proceeded with WF-01.03 by explicit instruction and approval on 16 November 2026. Actual interactive sign-in against a real development account is unverified.

Evidence level: Code-verified and automated-test verified, 16 November 2026 (Django 6.1.2). Inspection baseline: 14/14 backend session tests and 9/9 frontend session tests. After implementation: `manage.py test apps.accounts.test_session_auth --settings=config.test_settings` 18/18 passed (14 existing + 4 new: identity budget across IPs and normalized IDs, budget checked before authentication, no raw ID in cache keys, distinct request reference on every auth response). All 23 accounts test modules: 380 tests, 377 passed; the 3 failures are in test_registration_review_notifications and fail identically with the original session_auth.py, so they belong to pre-existing uncommitted outbox work, not this flow. Frontend `npm test`: 154 tests, 153 passed; the 1 failure is the known unrelated dashboard/mock-isolation test. `npm run test:registration-ui`: 43/43 passed, including 7 new real-browser login scenarios on the actual home page with mocked APIs (wrong credentials, rate limit, CSRF refresh, unknown outcome with and without a session, existing session and sign-out, success). `npm run build` passed. `npm run lint`: the new and changed files are clean; 1 pre-existing error (ThemeToggle.tsx) and 1 pre-existing warning (RegistrationReviewLivePanel.tsx) in untouched files. Disposable test databases were created and destroyed. Not verified: interactive sign-in with a real development account, production configuration and HTTPS deployment. access_control suites were not re-run (no access_control code changed).

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-01.04. Do not start until Approved is ticked.

#### WF-01.04 — Logout and session termination

| Field | Definition |
| --- | --- |
| Actor / required permission | Any account holder with a valid Workspace session, whatever its active assigned roles. Signing out needs no feature-permission grant: the endpoint requires only a CSRF-verified browser request. Django framework staff and superusers never hold a Workspace session (WF-01.03), so they sign out of /admin/ separately. |
| Trigger | The user selects **Sign out** in the dashboard sidebar (DashboardShell), or **Sign Out** on the home-page signed-in card (WF-01.03 P-03). Both call POST /api/v1/auth/logout/. |
| Preconditions | The browser can obtain a CSRF token (GET /api/v1/auth/csrf/) and the request comes from a trusted origin. A session normally exists; an expired or already-terminated session is handled the same way (see Alternatives A and B). |
| Result | Django deletes the current server-side session row and expires the session cookie. The response is {"authenticated": false} with no-store caching and a request reference. The browser loads the public page /, which discards all in-memory account state. Any later request carrying the old session cookie is anonymous. Other devices' sessions are unaffected. |
| Status | Inspected and reconciled 16 November 2026 from the owner-supplied draft, then approved by the owner the same day with five safeguards (S-1 to S-5 below). P-01 to P-05 are implemented and verified by automated backend, unit and browser tests. The server-side logout needed no code change; its behavior is now covered by tests. D-17 and D-19 stay open. Human Approval of the finished flow remains unchecked. |

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

Blocked by: No remaining development implementation blocker for P-01 to P-05. Open: D-17 (logout events), D-19 (session deletion, limits and sign-out from all devices), and cookie and session lifetime settings (D-18, WF-01.06). WF-01.03 Human Approval is still unchecked; the owner proceeded with WF-01.04 by explicit instruction and approval on 16 November 2026. A real back/forward-cache restore and sign-out with a real development account are unverified.

Evidence level: Code-verified and automated-test verified, 16 November 2026. Backend: `manage.py test apps.accounts.test_session_auth --settings=config.test_settings` 22/22 passed (18 existing + 4 new: the replayed old cookie is anonymous for /session/ and refused with 401 by the review API, and its session row is deleted; the logout response expires the session cookie with no-store and no account data; anonymous and repeated logout return 200 {"authenticated": false} and create no session; a session-store failure returns 503 auth_unavailable and the session honestly stays active). All 23 accounts test modules: 384 tests, 381 passed; the same 3 test_registration_review_notifications failures as in WF-01.03, which belong to pre-existing uncommitted outbox work. Frontend: tests/sign-out.test.mjs 5/5 (confirmed sign-out; uncertain then anonymous; still active; failed status read stays unconfirmed; only 401 authentication_required signals, not 403 or login 401), with the POST sent exactly once in every case. `npm test`: 159 tests, 158 passed; the 1 failure is the known unrelated dashboard/mock-isolation test. `npm run test:registration-ui`: 51/51 passed, including 8 new real-browser scenarios on the actual dashboard with mocked APIs (sign-out then Back stays on /; uncertain then anonymous; still active; failed status read; other tab via BroadcastChannel; other tab without BroadcastChannel on visibility; restored-page recheck via a simulated persisted pageshow; protected 401 versus 403). `npm run build` passed; `npm run lint` is clean for changed files, with the same 2 pre-existing problems in untouched files. Not verified: a genuine browser back/forward-cache restore (simulated with a persisted pageshow event), sign-out with a real development account, and production configuration.

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-01.05. Do not start until Approved is ticked.

#### WF-01.05 — Forgot-password request and reset

| Field | Definition |
| --- | --- |
| Actor / required permission | Holder of an approved Workspace account who cannot sign in. It is a public flow: no session and no feature permission are needed. The account must pass the recovery eligibility check: active, Approved, not framework staff or superuser, at least one active role, and an email on file with verification proof for that same address (D-21). Framework administrators recover through /admin/ only. |
| Trigger | The user selects **Forgot Password?** on the home sign-in card, opens /forgot-password and submits School ID (Staff ID for Instructors, the same field) plus registered email. |
| Preconditions | WORKSPACE_PASSWORD_RESET_ENABLED is on. It defaults to off and activation needs separate owner approval (D-24). The mail backend is configured (SMTP only when WORKSPACE_EMAIL_SMTP_ENABLED; otherwise the console backend). WORKSPACE_PUBLIC_BASE_URL points at the frontend. CSRF and trusted-origin checks pass. |
| Result | An eligible account receives a 30-minute reset link. Submitting a new password that meets the password validators replaces the password hash. The link stops working, and every existing session for that account stops working on its next request. No session is created and approval, activation, roles and permissions are unchanged. The user then signs in through WF-01.03. |
| Status | Approved by the owner on 16 November 2026 for P-01 to P-07 with D-20 option (a) for development only, D-21 option A, D-22, D-23 and D-24 (gate stays off). P-01 to P-07 are implemented and verified by automated backend, unit and browser tests. WORKSPACE_PASSWORD_RESET_ENABLED remains off, and protected executor mode refuses recovery. Earlier history: inspected and reconciled read-only on 16 November 2026, starting from the owner-supplied draft. Recovery is implemented behind its feature gate (off by default), with stateless single-use tokens, a fragment-only link, a row-locked atomic reset and automatic session invalidation. Gaps: password-rule and invalid-link messages never reach the user, all failures look alike, uncertain reset results are not handled, the "School ID" label, no per-identity limit, a timing difference that reveals a valid ID and email pair, mail sent to unverified addresses, no password-changed notice, and missing tests. A second read-only reconciliation (same day, on the owner's instruction) verified session invalidation, expiry, multiple links, mail failure and ineligible accounts with a temporary probe, found that request and reset share one rate-limit counter, and evaluated D-20 to D-24. Proposals P-01 to P-07 and decisions D-20 to D-24 await owner approval. No application code was changed. |

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

1. User opens / and selects Forgot Password? on the sign-in card.
2. /forgot-password shows "Forgot Password" with "School ID or Staff ID" and "Registered email" fields.
3. User enters both values and selects Send reset link.
4. Frontend checks both are filled ("Enter your School ID or Staff ID and registered email."), blocks a second submit, gets a CSRF token and sends POST /api/v1/auth/forgot-password/ with exactly {school_id, email}; no automatic retry.
5. Backend enforces POST only, CSRF, trusted origin and the per-IP request limits (4/minute, 20/day). It returns 503 recovery_disabled while the gate is off, and 503 recovery_unavailable in protected executor mode, before reading the body.
6. Backend accepts only those two fields (school_id up to 50 characters, trimmed; email up to 150, valid format), then applies the per-identity budget (3/hour, 6/day per HMAC digest of the trimmed, lower-cased school_id) before any lookup.
7. Backend looks for an eligible account (active, Approved, not staff or superuser, an active role, an email whose verification proof matches it) with that school_id and that email (case-insensitive). Legacy accounts without proof never match (D-21).
8. If one matches, Django's token generator makes a token bound to the account's current password hash, email and the time. Nothing is stored.
9. Backend builds {WORKSPACE_PUBLIC_BASE_URL}/reset-password#uid=…&token=… (fragment only) after validating the base URL.
10. Backend hands the plain-text reset mail ("Use this link within 30 minutes … If this wasn't you, ignore this email.") to the in-memory background sender (D-20), so the response does not wait for delivery.
11. Backend returns HTTP 202 "If the account details match an eligible account, a password reset email will be sent." in every case. The page shows that message and the hint "If no email arrives, your account may need assisted recovery. Contact support."
12. User opens the link. The reset page reads uid and token from the fragment, removes them from browser history, and shows the form. Nothing is consumed by opening it.
13. User enters a new password and confirmation (password requirements shown as helper text) and selects Update password.
14. Frontend checks they match and are at least 8 characters, then sends POST /api/v1/auth/reset-password/ with {uid, token, password, password_confirmation}.
15. Backend enforces the gate, the protected-mode refusal, CSRF, trusted origin and its own reset counters (4/minute, 20/day, separate from requests). Inside one transaction it locks the account row, rechecks eligibility including verified-email proof, verifies the token, runs AUTH_PASSWORD_VALIDATORS (similarity, minimum length, common, numeric) and saves the new hash. Failures return reset_link_invalid or allowlisted field errors.
16. The new hash makes this and every other outstanding link invalid, and every existing session of the account stops working on its next request.
17. After the transaction commits, the password-changed notice is queued to the account email (D-22; no link or token). Backend returns "Password changed. You can now sign in." without creating a session, and the page shows it with Back to login.
18. User signs in with the new password through WF-01.03.

Rules:
- Recovery never approves, activates, deactivates or assigns roles, and never recreates a rejected or deleted registration.
- Public responses never reveal whether a School ID, Staff ID or email exists or is eligible.
- Passwords and tokens never appear in logs, responses or stored state. Only the password hash is stored.
- Opening a link (GET) never changes anything; only an explicit POST uses the token.
- Reset never signs the user in. Password recovery stays separate from the authenticated password change in WF-04.03.
- The gate stays off until activation is separately approved (D-24). CSRF and trusted-origin checks are never relaxed for recovery.

#### Alternative flows

Alternative A — Account not found or not eligible (implemented): 1. No eligible account matches. 2. No token or mail is created. 3. The same HTTP 202 message is returned, and because delivery is in the background, a match no longer takes measurably longer (test-verified with a 1-second simulated send).

Alternative B — Link expired (implemented): 1. The token is older than 30 minutes. 2. Confirm returns 400 reset_link_invalid: "This reset link is invalid or expired. Request a new reset link." (test-verified). 3. The page hides the form and offers Request a new reset link.

Alternative C — Link invalid or already used (implemented): 1. A tampered, malformed or used token, or a malformed uid, is refused with reset_link_invalid and the password is unchanged (test-verified). 2. The page offers Request a new reset link.

Alternative D — Several requests (implemented by design, D-23): 1. Each eligible request sends a new link with its own 30-minute lifetime. 2. Earlier links stay valid until they expire or the password changes. 3. The first successful reset invalidates all of them. Concurrent use of one token is serialized by the row lock, so only one can succeed (sequential use probe-verified; a concurrent test is proposed in P-07). Note: request and reset share the per-IP counter, so several requests can block the reset step (P-03).

Alternative E — Mail delivery fails (implemented): 1. The background sender's send_mail raises, or the 50-message queue is full. 2. Only the message kind and exception type are logged, never the ID, email, link or token (test-verified). 3. The request had already returned the same neutral 202, so no delivery is claimed. 4. The unsent token was never shown to anyone and expires; the user may request again within the limits.

Alternative F — New password rejected (implemented): 1. A password that fails the validators, or a confirmation that does not match, leaves the password unchanged. 2. The field shows "Choose a stronger password using the requirements shown." or "Passwords do not match.", and the requirements stay visible. 3. Both password fields are cleared, and the link stays usable until it expires.

Alternative G — Account without a verified email (implemented, D-21 option A): 1. A legacy account with an email but no verification proof, or whose proof is for a different address, receives no link, and a link made for it cannot be used (test-verified). 2. An account without any email receives nothing. 3. Feedback is the same neutral message plus the assisted-recovery hint. 4. No assisted recovery procedure exists yet: these users depend on a future authorized School Admin or support procedure and the official support contact, which is still pending owner input.

Alternative H — Uncertain reset result (implemented, P-02): 1. The reset POST times out or its response is lost. 2. The page says "We could not confirm whether your password was changed. Try signing in with your new password. If that does not work, request a new reset link." 3. The POST is never repeated automatically; the form stays available for an explicit retry, and a used token then fails safely (browser-test-verified).

Alternative I — Sessions after a reset (implemented): 1. The password hash changes. 2. Django's get_user sees a mismatched session-auth hash on each other session's next request and flushes it, including sessions holding an executor proof. 3. Protected endpoints then treat them as anonymous (test-verified for an ordinary session and for one holding an executor proof, whose session row is deleted). 4. In protected executor mode both recovery endpoints now refuse explicitly with 503 recovery_unavailable before any read, write or mail (test-verified), in addition to the database fencing.

#### Errors

| Step | Problem | What happens |
| --- | --- | --- |
| 4–5 | Gate off, or protected executor mode | HTTP 503 recovery_disabled (gate) or recovery_unavailable (executor) on both endpoints; no read, write or mail (test-verified). Page: "Password recovery is unavailable." or "Password recovery is temporarily unavailable. Please try again later." |
| 4 | Field empty | "Enter your School ID or Staff ID and registered email."; no request |
| 4–5 | CSRF missing or invalid, or untrusted Origin | HTTP 403 csrf_failed before parsing; no mail (test-verified). Page: alert with "Refresh security check" (no automatic POST) |
| 5–6, 15 | Too many requests (per IP; per identity for requests; reset has its own counters) | HTTP 429 too_many_attempts + Retry-After before any lookup or mail. Page: alert + "Try again in N seconds." with the button disabled. Requests no longer block the reset step (test-verified) |
| 6 | Extra, missing or invalid fields | HTTP 400 invalid_request; no mail |
| 7 | No eligible match (including legacy accounts without proof) | Neutral HTTP 202 and the assisted-recovery hint; no token or mail (test-verified). Same response time as a match (D-20) |
| 8–10 | Base URL invalid, database error, mail failure or full queue | Logged by exception type (or message kind) only; neutral HTTP 202; no delivery claimed (test-verified) |
| 12 | Fragment missing or malformed | "This reset link is invalid or incomplete."; no form, no request |
| 14 | Passwords do not match or are under 8 characters (client check) | Message shown; no request |
| 15 | Token invalid, expired, used, uid malformed, or account no longer eligible | HTTP 400 reset_link_invalid; password unchanged (test-verified). Page: message and "Request a new reset link" |
| 15 | Password fails a validator, or confirmation differs | HTTP 400 with allowlisted fields.password or fields.password_confirmation; password unchanged (test-verified). Page: field error, fields cleared |
| 15 | Database error, or protected executor mode refuses the credential update | Transaction rolled back; HTTP 503 recovery_unavailable; no notice is sent. Page: "Password recovery is temporarily unavailable. Please try again later." |
| 13–17 | Network failure or timeout after the reset POST | Page: "We could not confirm whether your password was changed…"; no automatic repeat (browser-test-verified) |
| 15 | Two simultaneous resets with the same link | The row lock serializes them; exactly one succeeds and exactly one notice is sent (test-verified with two threads) |

#### Links

Depends on: WF-01.01 and WF-01.02 (registered email and verification proof). WF-01.03 (the sign-in card link; signing in afterwards; the D-15 label). WF-01.06 (CSRF, cookies, HTTPS; D-18). WF-02.03 and WF-02.05 (approval and activation decide eligibility). The configured mail backend.

Feeds: WF-01.03 (sign-in with the new password). WF-01.06 (sessions ended by the password change). WF-04.03 (separate authenticated password change). WF-09.04 (email notifications, if P-06 is approved). WF-12.01 (recovery events, once D-17 is approved).

Traceability: SRS v0.3 (git HEAD) has no account-holder password-recovery requirement; FR-REC-01 and FR-REC-02 are cited only by docs/testing/MASTER_TEST_UAT_PLAN_DRAFT.md TC-010 (AT-17: request and reset, replay and expired tokens, wrong CSRF, enumeration-resistant, no token disclosure), probably from a later SRS version that is not in the repository. TC-010's criteria are met in code except the timing channel (P-04) and the feedback gaps (P-01). FR-AUD-05 is met (no reset tokens or password hashes in logs or responses). FR-AUTH-01 is met (CSRF and trusted origin). FR-AUTH-03 is met (Pending and inactive accounts cannot recover). NFR-SEC-02 is partially met (Django password hashing and validators; HTTPS depends on D-18). The accounts table and its email-verification proof fields are used as-is. No new ERD entity, column, endpoint or permission is proposed.

Guidelines: Inspect → Reconcile → Approve → Implement → Test → Commit

AI Agent Checklist: ☒ Inspected   ☒ Reconciled   ☒ Approved   ☒ Implemented   ☒ Tested   ☒ Committed

Checklist scope: Approved records the owner's 16 November 2026 authorization of P-01 to P-07 under D-20 to D-24; it is not Human Approval of the finished flow. Implemented and Tested cover P-01 to P-07 as described under Implementation basis and Evidence level. Committed: 8a96162 on branch ronald (10 files: the source and test changes listed under Implementation basis and this catalogue); unrelated uncommitted work, including backend/config/settings.py, was left unstaged. Earlier inspection scope: Inspected and Reconciled cover the read-only inspection above: the gate, both endpoints, eligibility, token generation and expiry, link handling, mail handling, CSRF, limits, atomic reset, session invalidation, frontend pages and existing tests. The baseline test runs show how the existing code behaves; they are not the Test stage. The second reconciliation also covered D-20 reuse options, the D-21 legacy procedure, D-22 commit timing, D-23 token review, D-24 gate and executor mode, and session invalidation. Approved stays unchecked until the owner explicitly approves P-01 to P-07 and decides D-20 to D-24.

Blocked by: No remaining development implementation blocker for P-01 to P-07. Production blockers (recovery stays disabled, D-24): reliable delivery for the background sender (it is in-memory and best effort, and loses queued mail on restart; D-20 is approved for development only); production HTTPS and an https WORKSPACE_PUBLIC_BASE_URL (D-18); a reviewed protected-executor recovery operation, since protected mode refuses recovery today; a future authorized assisted-recovery procedure and the official support contact for legacy accounts without proof (D-21; the only approved development account is in this state); policy sign-off of the D-16 and recovery budget values; and the authentication-event contract (D-17). Separate activation approval is required (D-24). WF-01.03 and WF-01.04 Human Approval are still unchecked.

Evidence level: Code-verified and automated-test verified, 16 November 2026. Backend: `manage.py test apps.accounts.test_password_reset --settings=config.test_settings` 21/21 passed (6 existing, the fixture now carrying verification proof, plus 15 new): legacy account without proof gets the neutral response, no mail and an unusable link; proof for a different address is refused; an expired link returns reset_link_invalid; a second link is refused after the first is used; allowlisted field errors; another session (including one holding an executor proof) ends after a reset, and reset creates no session; the notice is sent only after commit, never on rollback, and contains no link or token; the response does not wait for a 1-second simulated send; mail failure is neutral and logs no ID, email, link or token; a full queue is dropped and logged; the per-identity budget applies across IP addresses and normalized IDs; a request burst does not block the reset step; protected executor mode fails closed with no mail or write; the reset endpoint is gated; and two simultaneous resets with one link (two threads, TransactionTestCase) succeed exactly once with exactly one notice. All 23 accounts test modules: 399 tests, 396 passed; the same 3 test_registration_review_notifications failures as in WF-01.03 and WF-01.04, which belong to pre-existing uncommitted outbox work. Frontend: tests/password-reset-feedback.test.mjs 4/4 and tests/password-reset.test.mjs 3/3. `npm test`: 163 tests, 162 passed; the 1 failure is the known unrelated dashboard/mock-isolation test. `npm run test:registration-ui`: 58/58 passed, including 7 new real-browser scenarios on the actual recovery pages with mocked APIs (neutral request with the label and hint; recovery_disabled message; 429 countdown; CSRF refresh without a POST; token removed from the address bar and invalid link offering a new request; rejected password with field error and cleared fields; uncertain reset without a repeated POST; success). `npm run build` passed; `npm run lint` is clean for changed files, with the same 2 pre-existing problems in untouched files. The gate default stays off. Not verified: real SMTP delivery through the background sender, the real protected executor server, production configuration, and an interactive run with a real development account. Earlier evidence: Code-verified (files listed under Inspection basis; Django 6.1.2 token generator and get_user read). Automated-test baseline, 16 November 2026: `manage.py test apps.accounts.test_password_reset --settings=config.test_settings` 6/6 passed: a matching request sends mail and a wrong one is neutral with the same body; a reset changes the password only once; a bad token changes nothing; the disabled gate sends no mail; inactive and framework staff accounts get no mail; CSRF is required. `node --test tests/password-reset.test.mjs` 3/3 passed. Second reconciliation, 16 November 2026: a temporary probe on an isolated MySQL test database (6 cases, all passed as probes, file deleted afterwards) verified session invalidation including a session holding an executor proof; no session created by reset; expiry; two links valid until one is used, then the other refused; neutral handling of Pending, no-email and mail-failure cases with exception-type-only logging; loss of field messages; and the shared rate-limit counter (HTTP 429). Read-only development-database counts: 1 approved, active, non-staff account, with email and no proof. Not verified: real mail delivery, a browser run of the pages, truly concurrent resets, the real executor server, and measured timing.

Human Approval: ☐ Approved by: ______  Date: ______

Next flow: WF-01.06. Do not start until Approved is ticked.

#### WF-01.06 — Session expiry and CSRF handling

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
| D-18 | Session lifetime and cookie flags | Explicit production settings: Secure session and CSRF cookies, HTTPS, DEBUG off, an approved absolute and idle session lifetime | Django defaults (14-day persistent cookie, no idle timeout, Secure off) | OPEN; defaults active in config/settings.py; decide in WF-01.06 | Project owner | WF-01.03; WF-01.06 |
| D-19 | Session revocation timing and concurrent sessions | Keep the per-request database eligibility recheck; decide whether to delete sessions on deactivation or role change and whether to limit sessions per account (SRS OD-13) | Revoke only at expiry | Recheck IMPLEMENTED and test-verified; deletion and limits OPEN | Project owner | WF-01.03; WF-01.04; WF-01.06; WF-02.05; WF-03.01 |
| D-20 | Recovery mail dispatch and timing | Send the reset mail outside the request through a bounded background dispatcher so matching and non-matching requests take the same time | Keep synchronous sending (reveals valid ID and email pairs by timing) or pad every response | Option (a) owner-approved 16 Nov 2026 for development only; IMPLEMENTED and test-verified (recovery_mail.py: 50-message in-memory queue, one daemon thread, kind-only logging). Production BLOCKED until reliable delivery, failure handling and security are verified (D-24). The registration outbox is not reused (it would need an ERD change) | Project owner | WF-01.05 |
| D-21 | Recovery eligibility: verified email | Require email_verified_at and email_verified_address matching the current email; others get the neutral response and the support path | Keep sending to any email on file, including legacy unverified addresses | Option A owner-approved 16 Nov 2026; IMPLEMENTED and test-verified at request and reset. Legacy accounts without proof (dev DB: 1 of 1 approved accounts) get the neutral response and the assisted-recovery hint. The future authorized assisted-recovery procedure and the official support contact are OPEN | Project owner | WF-01.05; WF-01.01; WF-01.02; WF-02.03; WF-10 |
| D-22 | Password-changed notice | After commit, send a link-free "password was changed" email; failure never changes the result | No notice | Owner-approved 16 Nov 2026; IMPLEMENTED and test-verified: queued with transaction.on_commit only after the update commits (none on rollback; exactly one under concurrency), sent through the D-20 sender, no link or token | Project owner | WF-01.05; WF-09.04 |
| D-23 | Reset token model | Keep Django stateless tokens (single-use through the password hash, 30-minute expiry; several links valid until one is used) and leave password_reset_token columns unused | Store a digest of the latest token in the existing columns so a newer request invalidates older links | Owner-approved 16 Nov 2026: keep Django's stateless token unchanged (IMPLEMENTED and test-verified: expiry, single use, other links refused after use); password_reset_token columns stay unused | Project owner | WF-01.05 |
| D-24 | Password-recovery activation | Keep WORKSPACE_PASSWORD_RESET_ENABLED off until P-01 to P-07, D-20, D-21 and production HTTPS (D-18) are done, then approve activation separately | Activate now | Owner decision 16 Nov 2026: keep disabled; gate default off (test-verified). Protected executor mode refuses recovery explicitly (test-verified). Activation needs separate approval after production security, reliable delivery and protected-executor compatibility | Project owner | WF-01.05; WF-01.03 |

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
