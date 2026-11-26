# Proposal: consolidated HDAC permission reconciliation for Academic Settings (WF-11.01, WF-05.04/05.05, WF11-D14)

**Status:** PROPOSAL ONLY. Not reviewed, not installed and not provisioned. The pinned v2.0, v2.1 and
v2.2 manifests, their validators, digests and default bindings are unchanged. No role, account or
service receives any permission from this document, and no account-specific Grant or Deny is changed.

**Date:** 26 November 2026 · **Supersedes nothing.** It consolidates the open items and keeps
`WF11_FeeSchedulePermission_Overlay_Proposal_2026-11-25.md` as the detailed fee proposal (item A).

**Sources:** WF11 R-01–R-03 and WF11-D01–D25 (WF-11 reconciliation record), the WF-11 pre-implementation
security readiness review (25 Nov 2026), catalogue `v2_0.json` with the `v2_1_delta.json` and
`v2_2_delta.json` deltas (independent review `OPEN`; neither delta touches any code below), and the
runtime in `backend/apps/academic` and `backend/apps/finance` at commit `ae583ad`.

## 1. What runs today (fail closed)

Every operation below is behind its own default-off switch, refused in production, and uses the existing
HDAC evaluator: genuine role assignment, the selected role context when it is enforced, active services,
the exact effective permission, and account-specific **Deny precedence**. Every write re-checks access
under row locks. None of the migrations is applied to `ctug_workspace`.

| Operation | Runtime code today | Pinned default binding | Effect today |
| --- | --- | --- | --- |
| Semester fee Draft, approval, revision | `finance.fee_schedule.manage`, **only through a genuine Admin role grant** (`admin_role_grant=True`) | Treasurer | Refused for everyone (no Admin binding exists) |
| Official CTU enrollment verification, non-enrollment gaps | `academic.profiles.manage` (Admin path) | Admin | Allowed for School Admin when the switch is on; the code is broader than the operation (item B) |
| Student onboarding Draft steps and finalization | `clearance.requests.self.submit` (Student path) | Student | Allowed for a Student when the switch is on; the semantic boundary is wrong (item C) |
| Student onboarding reads and own history | `academic.profile.self.read` | Student | Allowed; kept (item C) |
| Curricula | `academic.courses.manage` | Admin | Allowed behind `WORKSPACE_ACADEMIC_CURRICULUM_WRITES_ENABLED` (item D) |
| Subject offerings | `academic.periods.manage` | Admin | Allowed behind `WORKSPACE_ACADEMIC_OFFERING_WRITES_ENABLED` (item D) |
| WF11-D14 historical participation correction | `academic.periods.manage` **and** `academic.profiles.manage` | Admin | Allowed behind its own switch; needs a dedicated boundary (item E) |

The proposed codes in items B, C and E do not exist in any pinned catalogue, and the runtime does not
accept them. `apps.academic.test_student_dashboard_boundary.SignatoryAndSecurityTests.test_proposed_governance_codes_stay_inactive`
binds them in a throwaway database, removes the current bindings, and shows that every operation is
then **refused**.

## 2. Items

Each item lists the required fields. "Admin" is the School Admin role. A Technical Super Admin operates
only through a stored genuine Admin assignment (`allowed_role_ids`), never through the governance role
itself.

### A. Semester organizational fee — `finance.fee_schedule.manage`

| Field | Value |
| --- | --- |
| Existing code and binding | `finance.fee_schedule.manage` (service `finance`, scope `FINANCE`) → **Treasurer**. Runtime requires it through a genuine Admin role grant, so today nobody can set fees |
| Proposed | **Option A (recommended):** a reviewed `v2_3_delta.json` that removes `Treasurer → finance.fee_schedule.manage` and adds `Admin → finance.fee_schedule.manage`. **Option B:** a narrower `finance.semester_fee.manage` → Admin, leaving the existing code unchanged. Details: `WF11_FeeSchedulePermission_Overlay_Proposal_2026-11-25.md` §4 |
| Authorized actor | School Admin; Technical Super Admin only through a genuine Admin assignment |
| Selected role | Admin context (or a Technical Super Admin context inheriting the stored Admin assignment). A Treasurer context never authorizes fee setting, even on a dual Treasurer+Admin account |
| Allowed | Save, edit and withdraw the semester fee Draft; explicitly approve one current rate (₱0.00 needs its own confirmation); a reasoned revision while no Student obligation exists |
| Prohibited | Approving a new rate after any obligation exists (`obligations_assessed`); changing, deleting or re-snapshotting obligations; adjustments, waivers, credits or refunds; payments and receipts; editing Closed or Archived fee history |
| Affected holders | Static: 1 Treasurer default binding (removed under Option A). Treasurer keeps `finance.fee_schedule.read` (pinned default for Student, Treasurer and Admin), `finance.payments.record`, `finance.ledger.read`, receipt, fund and expense codes. Live: see §3 |
| Deny | A Deny on the code (or on the Option B code) still wins. Existing Denies are never removed. Under Option B, Denies on the old code do not cover the new one and must be reviewed and mirrored deliberately |
| Runtime change | Option A: none (`admin_role_grant` stays as a defence in depth). Option B: `apps/finance/fees.py` `PERMISSION_CODE` plus its tests |
| Isolated tests | Already passing: `apps.finance.test_semester_fees` — `test_pinned_defaults_refuse_school_admin_and_treasurer`, `test_direct_grant_alone_never_authorizes`, `test_admin_binding_succeeds_and_deny_wins`, `test_technical_super_admin_only_through_a_genuine_admin_assignment`, `test_selected_admin_context_is_required`, `test_permission_revoked_between_precheck_and_lock_is_refused`. Needed after review: validator tests for v2.3 and the pinned digest |

### B. Official CTU enrollment verification — narrow `academic.enrollment_verifications.record`

`academic.profiles.manage` is defined as "Maintain approved student academic status and section/year
references; no role or credential changes". It covers any future maintenance of Student academic profiles,
which is broader than recording institutional enrollment evidence. Reusing it would let every holder of
profile maintenance record official verification, and the reverse.

| Field | Value |
| --- | --- |
| Existing code and binding | `academic.profiles.manage` (service `academic`, scope `SCHOOL`) → Admin |
| Proposed code and binding | **`academic.enrollment_verifications.record`** (service `academic`, scope `SCHOOL`, ordinary protection) → **Admin**. It follows the `access_control.appointments.record` pattern: a resource plus a narrow action |
| Authorized actor | School Admin at the counter, with the Student present and the official CTU record checked in person |
| Selected role | Admin context. A Student, Instructor or Treasurer context of the same account is refused |
| Allowed | Search eligible Student accounts by CTU-G ID prefix (minimal fields); read one Student's per-semester verification record; record, supersede and revoke Verified in-person enrollment evidence (course, year level, entry classification, subjects and a controlled reference only); record and revoke a verified non-enrollment gap for a Closed or Archived semester |
| Prohibited | Verifying one's own records (`self_verification`; enforced today); completing or confirming a Student's onboarding; creating participation, clearance or fee records; uploading or storing documents, scans or contents; writing the reference into audit history; revoking evidence that supports a finalized participation (`evidence_in_use`); any CTU integration or external source (none exists; lane 1 has no runtime writer) |
| Affected holders | Static: the Admin role (the same holders as today; no new holder). Live: see §3 |
| Deny | A Deny on the new code wins. Existing Denies on `academic.profiles.manage` would **no longer** block verification after the switch. Inventory them and mirror any that target verification as Denies on the new code **before** the runtime change; never remove the old Deny |
| Runtime change | `apps/academic/verification.py` `VERIFY_CODE`; the frontend hint `VERIFICATION_CODE`; the `student-verification` navigation code; tests |
| Isolated tests | Already passing: School Admin path, Deny, non-Admin roles, Admin-context requirement, self-verification refusal, privacy of the reference (`test_student_onboarding.VerificationTests`). Needed after review: the same suite run against the new code; a holder of `academic.profiles.manage` alone is refused; a Deny on the new code wins |

### C. Student onboarding writes — narrow `academic.semester_onboarding.self.submit`

`clearance.requests.self.submit` is defined as "Submit own eligible subject/signatory requests…". It is
a clearance-request boundary, not an academic onboarding boundary. Onboarding finalization creates the
clearance and the fee obligation as **internal consequences**. Those consequences must not depend on,
or be authorized by, a clearance self-service code.

| Field | Value |
| --- | --- |
| Existing code and binding | `clearance.requests.self.submit` (service `clearance`, scope `OWN`) → Student |
| Proposed code and binding | **`academic.semester_onboarding.self.submit`** (service `academic`, scope `OWN`, ordinary protection) → **Student**. Reads stay on `academic.profile.self.read` (Student) |
| Authorized actor | The Student, for their own record only. No route accepts a student identifier (enforced today) |
| Selected role | Student context. Another context of the same account is refused (`student_context_required`) |
| Allowed | Save the own Draft (Step 1 type, Step 2 subjects, Step 3 course and year level); confirm the own final review and finalization for the current Active semester |
| Internal consequences (server only) | In one atomic finalization: participation, confirmed subjects, one Uncleared clearance with Pending requirements, one Unpaid fee-obligation snapshot of the approved rate, and audit rows. None of these can be requested separately |
| Prohibited | Signing, approving or clearing any clearance; arbitrary clearance creation; creating or changing financial obligations, or choosing an amount; fee configuration; institutional verification; any other Student's records |
| Affected holders | Static: the Student role (the same holders). `clearance.requests.self.submit` keeps its Student default binding for the future WF-06 Student actions, but onboarding stops accepting it. Live: see §3 |
| Deny | A Deny on the new code wins. Existing Denies on `clearance.requests.self.submit` would no longer block onboarding: inventory and mirror them deliberately, and never remove them |
| Runtime change | `apps/academic/onboarding.py` `WRITE_CODE` (the permission row is also the lock taken by `lock_and_authorize_student`); the frontend hint `ONBOARDING_WRITE_CODE`; tests |
| Review point | `my-history` shows the Student's own clearance and fee summaries under `academic.profile.self.read`. Reviewers may prefer to require `clearance.requests.self.read` and `finance.fee_schedule.read` for those parts |
| Isolated tests | Already passing: the Student path, Deny on read and write, selected Student context, multi-role isolation, inactive and ineligible accounts, revalidation inside finalization (`test_authorization_is_revalidated_inside_the_finalization`). Needed after review: the same suites against the new code; a holder of `clearance.requests.self.submit` alone is refused |

### D. Curricula and subject offerings — confirm existing narrow codes (no new code)

| Field | Value |
| --- | --- |
| Existing codes and bindings | Curricula → `academic.courses.manage` (Admin; "Maintain approved course definitions…"). Offerings → `academic.periods.manage` (Admin; "Maintain school-year/semester dates and activation…"). Subjects → `clearance.subjects.manage`, sections → `academic.sections.manage`, instructors → `clearance.teaching_assignments.manage` (all Admin) |
| Proposed | **Option A (recommended):** keep these codes and record, in the same reviewed overlay, definition clarifications only. `academic.courses.manage` would add "…and each course's versioned curriculum (subject plan per year level and term); a published version is immutable". `academic.periods.manage` would add "…and the subject offerings of each period's sections". No broad `academic.settings.*` code is introduced. **Option B:** dedicated `academic.curricula.manage` and `academic.offerings.manage` → Admin, if reviewers want to separate the duties |
| Authorized actor | School Admin; Technical Super Admin only through a genuine Admin assignment |
| Selected role | Admin context |
| Allowed | Curricula: create, edit Draft entries, publish, supersede, delete an unused Draft. Offerings: create for a Draft or Active semester from a matching published curriculum entry; remove only while the semester is Draft and the offering has no assignment history |
| Prohibited | Through these codes: assigning instructors (needs `clearance.teaching_assignments.manage`), editing a published curriculum, changing Closed or Archived offerings, and any Student, clearance or fee record |
| Affected holders | The Admin role only (no change). Live: see §3 |
| Deny | Unchanged. A Deny on each code wins for its area |
| Runtime change | Option A: none. Option B: `apps/academic/configuration.py` `AREAS` plus the frontend `AREA_CODES` and tests |
| Isolated tests | Already passing: `apps.academic.test_academic_configuration` and `..._http` (exact code per area, Deny, Admin context, switches) |

### E. WF11-D14 historical participation correction — narrow `academic.historical_participation.correct`

| Field | Value |
| --- | --- |
| Existing codes and binding | Both `academic.periods.manage` and `academic.profiles.manage` (Admin), behind `WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED` |
| Proposed code and binding | **`academic.historical_participation.correct`** (service `academic`, scope `SCHOOL`; reviewers to decide whether it should carry **protected** handling) → **Admin**. It replaces the two broad codes for this operation |
| Authorized actor | School Admin. Review point: whether the person who recorded the Verified evidence (item B) may also confirm the correction, or whether a second School Admin is required (two-person rule) |
| Selected role | Admin context |
| Allowed | For a Closed or Archived semester only: create **one** missing participation from the reviewed Verified evidence, its subjects with the real assigned instructors, one Uncleared clearance with Pending requirements, and one Unpaid obligation snapshot of the semester's **original** approved fee, atomically and with a reason note. The semester stays Closed or Archived |
| Prohibited | Editing or deleting any existing participation, clearance, requirement or obligation; inventing an amount when no original approved fee exists (`historical_fee_unavailable`); reopening or reactivating a period; signing, approving or clearing; fee adjustments; recording gaps; self-correction (`self_verification`); a Student who is the assigned instructor (`instructor_conflict`) |
| Affected holders | The Admin role only. Live: see §3 |
| Deny | A Deny on the new code wins. Today a Deny on either broad code blocks the correction; after the switch, inventory and mirror those Denies deliberately |
| Runtime change | `apps/academic/historical_participation.py` `PERIOD_CODE` and `PROFILE_CODE` replaced by the one code; tests |
| Isolated tests | Already passing: `apps.academic.test_wf1101_residual.HistoricalParticipationTests` (refusals, original fee required, period not reopened, non-Admin roles, switch off, self-correction). Needed after review: the suite against the new code; a holder of only `academic.periods.manage` and `academic.profiles.manage` is refused |

## 3. Read-only live inventory (required before review; not done here)

No connection to `ctug_workspace` was made. A separately authorized operator should run read-only
queries and report **counts only, with no personal data**:

1. `role_permissions` rows for each code above: role, `is_active`.
2. `account_permissions` Grant and Deny rows for each code above: effect, `is_active`, role scope.
3. Accounts holding more than one of Student, Instructor, Treasurer and Admin (counts per combination).
4. Accounts with a Deny on `academic.profiles.manage`, `clearance.requests.self.submit`, `academic.periods.manage`
   or `finance.fee_schedule.manage`. These decide which Denies must be mirrored onto the new codes before any runtime switch.

## 4. Sequence still required (none authorized here)

1. Independent security and governance review of items A–E and of the options.
2. Read-only live inventory (§3) and a Deny-mirroring plan.
3. One reviewed `v2_3_delta.json` (bindings and definitions only), validator chain v2.3, pinned digest and tests.
4. The runtime constant changes listed above, in one commit, with the "Needed after review" tests.
5. Separately authorized provisioning on `ctug_workspace`, after the Academic Settings migrations are approved and applied.
6. Separate owner decisions for each feature switch and launcher mode.

Until then the runtime stays exactly as described in §1: fee setting is refused for everyone, and the
other operations stay behind their default-off switches.

## 5. Authorized inventory follow-up, 26 November 2026

The owner authorized the prepared SELECT-only inventory starting from `10e3fe8`, but its
[connection preflight](WF11_Permission_Inventory_Preflight_2026-11-26.md) found no usable verified
reader in the available local configurations/login profiles. The application connection uses
root and was not used. No database connection or SQL statement was executed; all live binding,
Grant/Deny, holder and transition counts remain **unknown**, not zero. Independent review remains
OPEN, and actual inventory validation of items A–E is outstanding. That pass ended with the
[reader setup steps](WF11_Permission_Inventory_Reader_Setup_2026-11-26.md) awaiting authorization.

At `f9cf56b`, the owner approved the eight-table reader setup. The administrative preflight
verified the local `ctug_workspace` target, found seven of the eight required InnoDB tables and
confirmed the reader account was absent. The missing `account_permission_role_scopes` table
blocked the grant set and inventory. No account was created and no application permission rows
were queried. Live counts and validation of items A–E are still pending. The owner must decide
whether to approve a reduced inventory for the current schema. Independent review remains open.
[Live preflight findings](WF11_Permission_Inventory_Preflight_2026-11-26.md).

The owner subsequently approved the seven-table reader and reduced inventory. The verified snapshot
found zero live definitions, bindings, Allows, Denies and source holders for all 13 reviewed codes.
It also found none of the three required service rows. The catalogue defaults therefore describe
intended bindings, while the local baseline still requires separate provisioning. Two Admin
accounts and two Student accounts are potential cohorts if the corresponding authorities are
later provisioned. No existing Treasurer fee-holder loss or Deny migration was identified in
scope. Role-scope evidence is unavailable and scope-enabled evaluation remains unverified.
Independent governance review remains OPEN.
[Reduced inventory results](WF11_Permission_Inventory_Preflight_2026-11-26.md#reduced-inventory-from-f63f8ac).
