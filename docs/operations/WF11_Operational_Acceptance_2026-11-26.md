# Academic Settings operational acceptance — executable checklist

**NOT PERFORMED against the actual application/database. Every checkbox below remains unchecked.**
Phase 1 (26 Nov 2026, `d451c67`) is provisioned and approved for the local launcher mode, and its read-only accessibility check passed. See the [runbook record](WF11_Migration_and_Activation_Runbook_2026-11-26.md#phase-1-provisioning-and-local-activation-26-november-2026). SA01–SA04 and SA12 are ready for the owner's interactive School Admin run. SA05–SA11 stay BLOCKED (later phases are off).
Run only the phase the owner has explicitly authorized. Record PASS/FAIL/BLOCKED, operator,
commit, mode, date/time in Asia/Manila, expected result, observed result and redacted evidence
for each ID. A passing isolated/mock test is supporting evidence, not operational acceptance.

## Preconditions and reproducible supporting commands

- [ ] P01 — Identify the approved local server/database, immutable application commit and exact
  feature phase. Require the reviewed migration/backup/restore evidence and the independently
  reviewed permission provision. Verify no extra launcher mode/flag, notification worker or
  unrelated workflow was enabled. Use the [runbook](WF11_Migration_and_Activation_Runbook_2026-11-26.md).
- [ ] P02 — Use an owner-approved test dataset and existing eligible accounts: School Admin,
  Student Regular, Student Irregular, Student+Instructor, Student+Admin, Treasurer and Technical
  Super Admin with/without genuine Admin authority. Do not invent appointments or create/modify
  real account Grants/Denies merely to run this checklist. Use separately provisioned Deny cases
  or disposable MySQL for destructive/race/failure injection cases.
- [ ] P03 — Select Admin for School Admin work and Student for Student work. Preserve account,
  history, logout and legitimately authorized non-Student operations. Capture only necessary
  internal object references in restricted evidence; no names, emails or verification references.

Supporting commands from repository root (disposable MySQL; frontend browser APIs mocked):

```powershell
backend\.venv\Scripts\python.exe review_only\academic_settings_v2_3\run_isolated_tests.py apps.academic.test_student_dashboard_boundary apps.academic.test_student_onboarding apps.academic.test_student_onboarding_concurrency apps.academic.test_student_onboarding_http apps.academic.test_wf1101_residual apps.finance.test_semester_fees
backend\.venv\Scripts\python.exe review_only\academic_settings_v2_3\run_isolated_tests.py --candidate
backend\.venv\Scripts\python.exe review_only\academic_settings_v2_3\run_isolated_tests.py schema_validation_tests
backend\.venv\Scripts\python.exe -m unittest discover -s review_only/academic_settings_v2_3 -p test_preparation.py -v
```

From `frontend/`, use `npm.cmd` on Windows where PowerShell blocks the npm.ps1 shim:

```powershell
node --test tests/browser/student-dashboard-boundary-errors.test.mjs tests/browser/student-onboarding-errors.test.mjs tests/browser/academic-settings-errors.test.mjs tests/browser/academic-readiness-errors.test.mjs tests/browser/school-periods-errors.test.mjs tests/browser/school-periods-lifecycle-errors.test.mjs tests/browser/semester-fees-errors.test.mjs
npm.cmd test
npm.cmd run build
npm.cmd run lint
```

Do not run these tests against the actual database. Candidate tests run the unapplied patch in a
separate source copy and throwaway schema. Report the known navigation/lint failures exactly;
never delete/skip assertions to obtain a green report.

## School Admin — Settings first, phases 1–4

| ID | Operator action | Required observable result |
| --- | --- | --- |
| SA01 ☐ | Sign in, select the genuine Admin context. Open **Academic configuration → Academic settings**, or `/dashboard?view=academic-references`. | Real courses/subjects/sections interface opens. “Settings” here is the existing **Academic settings** view, not System settings or a new route. No access-governance authority appears. |
| SA02 ☐ | Open **School years & semesters**, `/dashboard?view=school-periods`; create an approved unused starting year. | Exactly one School Year and **two automatically created Draft semesters** (First/Second). Repeating the year is refused; no Student participation, clearance or obligation is created. |
| SA03 ☐ | Set dates on both Draft semesters and save. Try reversed/overlapping dates separately on disposable data. | Valid ordered ranges save with version/audit; invalid range and stale version refuse without partial updates. Nothing activates from dates. |
| SA04 ☐ | In **Courses**, create/edit an approved course; in **Subjects**, create subjects with approved lecture/lab units; in **Sections**, create matching course/year sections. | Each area obeys its exact code; duplicates/invalid units rejected; referenced historical definitions protected. |
| SA05 ☐ | Open **Curriculum versions**, create a Draft version, add subjects per year/term, explicitly **Publish curriculum**. | Draft edits save; Published version becomes immutable; new versions preserve old plans. Publish does not activate a semester. |
| SA06 ☐ | Open **Offerings & instructors**, choose the Draft semester/course/year/section, **Add offering** from the correct published curriculum. | Course/year/term consistency enforced; duplicate subjects/offering links refused; unassigned offering shown as unready. |
| SA07 ☐ | Assign the real eligible Instructor to every required offering; inspect assignment history. | Uses `clearance.teaching_assignments.manage`; no adviser permission substituted; one current assignment per offering; history retained. |
| SA08 ☐ | Open **Semester fees**, `/dashboard?view=semester-fees`; save the full approved semester amount as a Draft. | Exactly a Draft rate/history, not approved. No obligation/payment/receipt created. A Treasurer context and a direct fee Grant alone cannot set it. |
| SA09 ☐ | Review approval preview and explicitly **Approve fee**. Exercise ₱0.00 only on separately approved data with its extra confirmation. | Exactly one current Approved rate; prior revisions preserved; still no semester activation. Missing confirmation/zero confirmation refuses. |
| SA10 ☐ | Return to semester readiness. Inspect valid dates, curriculum/offerings and approved-fee checks. | Each is real and Ready; unavailable/missing source blocks activation with useful reason. No source failure is treated as zero/no records. |
| SA11 ☐ | Review **Activate** preview, selected semester/version, current Active semester and warnings. Explicitly confirm activation once. | Exactly one Active semester; previous Active closes only as reviewed; audit commits atomically; no Student participation/clearance/obligation is created. Back/refresh does not repeat the POST. |
| SA12 ☐ | Reopen the pages in Light, System-dark and Dark at 360/768/1024/1440px; use keyboard and Escape on confirmations. | Existing dashboard layout, accessible focus/contrast and error/recovery states work. No unapproved Student onboarding or historical correction action becomes active. |

If current v2.2 bindings are still in force, SA08–SA11 are **BLOCKED**, not passed: fee management
is refused and `approved_fee` cannot be satisfied. Do not insert a binding as a test shortcut.

## Student — separately approved phases 6–8

| ID | Operator action | Required observable result |
| --- | --- | --- |
| ST01 ☐ | As the approved Student, identify the semester in the header/current-period read. | Active semester and School Year come from `GET /api/v1/academic/catalogue/current-period/`; failure does not claim no active semester. |
| ST02 ☐ | Before completion, open `/dashboard`, a direct `?view=my-subjects`, Back, refresh and another tab in selected Student context. Repeat with Student+Admin/Instructor membership. | Route to onboarding/appropriate blocked state; no normal Student home or current-semester data bypass. `GET /api/v1/academic/onboarding/my-semester/` gives structured 409 `onboarding_required`. |
| ST03 ☐ | Confirm **Step 1: Student type** as Regular; run the Irregular branch on a second approved Student. | Own server Draft only; school year/semester/CTU-G ID are not client-editable. No student identifier is accepted in a Student mutation. |
| ST04 ☐ | Regular: confirm the complete prepared section list. Irregular: choose eligible offerings of the confirmed course once per subject. | Missing/ineligible instructors, duplicate subjects, wrong course/year/term or incomplete Regular list refuse; no official CTU enrollment is inferred from this selection. |
| ST05 ☐ | Confirm course and year level; test a material change before final review on disposable data. | Inconsistent subjects require confirmation again; Draft resumes after reload. |
| ST06 ☐ | Review Step 4 and the approved semester fee; without accepted official evidence, explicitly attempt confirmation. | Recoverable Pending Verification with Draft retained; **zero** new participation/clearance/obligation rows. No false success or automatic retry. |
| ST07 ☐ | Student visits School Admin in person. In Admin context, use **Enrollment verification** (`?view=student-verification`) to check the official record and record the permitted controlled reference. | Record attributed to an authorized different Admin for this Student+semester; correct course/year/classification/subjects; no document upload/reference audit disclosure; no Student finalization by Admin. |
| ST08 ☐ | Student returns to their own Student context, reviews the matched evidence/subjects/course/year and current rate, explicitly **Confirm onboarding**. | One transaction returns `completed`/dashboard route; Completed onboarding, participation and confirmed subjects, one Uncleared clearance with Pending requirements, one Unpaid original-rate fee snapshot and corresponding audit rows. |
| ST09 ☐ | Use the separately approved read-only integrity procedure to verify atomic records. Repeat the identical finalization request on disposable data/concurrent isolated test. | Exactly one participation, clearance and obligation for Student+semester; no duplicates. On any injected failure, no partial record set. |
| ST10 ☐ | Open normal Student dashboard, **My semester** and own history; refresh/revisit onboarding. | Dashboard available only after current-semester completion; own records accurately shown; completion never fabricates signing/payment/clearance approval. |
| ST11 ☐ | On separate approved fixtures, activate a later semester with an uncleared consecutive previous participation, then a verified-gap return case. | Consecutive case blocks with Clearance Required; verified gap may permit onboarding while older signatures/Unpaid balances remain independent; missing history is never presumed non-enrollment. |
| ST12 ☐ | Switch the multi-role account to a valid non-Student context and back. | Its permitted Admin/Instructor/Treasurer work remains available; switching back to Student reapplies this semester's gate. No permissions are unioned from another selected role. |

## Security and historical independence

| ID | Case and executable expectation |
| --- | --- |
| SEC01 ☐ | Unauthenticated request refuses. Student/Instructor/Treasurer without genuine Admin authority receive 403 on School Admin APIs when their gates are enabled. With gates off, 503 is the expected first refusal. No database mutation occurs. |
| SEC02 ☐ | Preprovisioned account Deny on the exact area code defeats both role and direct Grants. Under the separately approved candidate patch, each old-code Deny also blocks its replacement, including after switching roles or old-service deactivation. Old Grants alone do not authorize replacements. Use candidate isolated tests for transition cases until the patch is independently approved. |
| SEC03 ☐ | Missing/stale/cross-account selected role is refused. Student+Admin selected Student cannot verify or set fees; Admin selection cannot submit another Student's onboarding. Technical Super Admin without a genuine Admin assignment cannot perform business operations. |
| SEC04 ☐ | Admin+Student cannot verify/correct their own Student evidence; Student who is the assigned instructor cannot become their own clearance signatory. No second reviewer is falsely claimed. |
| SEC05 ☐ | Duplicate year/offering/subject/participation/clearance/obligation and concurrent finalization cases preserve uniqueness. Stale reviewed versions/evidence/rate produce refusals; uncertain writes require explicit status recovery. |
| SEC06 ☐ | In a separately isolated default-off launch/build, all 14 flags absent: relevant UI remains unavailable and APIs refuse. Turning on only a child flag cannot bypass its parent or exact permission. Production-profile activation is rejected at startup. |
| SEC07 ☐ | Selected Student with denied/missing read permission, generic 403, contradictory `student_context_required`, unavailable status source or malformed response fails closed for Student home/semester views; account/logout remain available. Valid non-Student context can continue its own authorized work. |
| SEC08 ☐ | After any Student obligation, a revised fee may remain a Draft but cannot be approved (`obligations_assessed`); existing and later Students retain the same approved snapshot. Test zero-valued obligations too in isolation. No adjustment workflow is created. |
| SEC09 ☐ | Closed/Archived period correction cannot overwrite/delete existing participations, requirements, signatures or obligations, reopen the semester or invent a fee. If historical correction remains off, direct requests refuse. If separately approved later, test original-fee and evidence requirements and whichever second-reviewer policy was actually approved. |
| SEC10 ☐ | Compare older participating periods' clearance/fee snapshots before/after new onboarding, activation/closure/archive and verified-gap exceptions. No clearing, resetting, resnapshotting or deletion; old obligations/signatures remain independent. |
| SEC11 ☐ | Review audit atomicity and privacy: failed operations have no partial successful event; successful changes attributed to the active authorized context. No credential, verification document/reference, email or unnecessary personal field in test reports. |

Acceptance record template: `ID | PASS/FAIL/BLOCKED | expected | observed | commit | mode/phase |
operator | Manila timestamp | redacted evidence reference`. Do not tick Human Approval or call
the system production-ready because this checklist or isolated test suite exists.
