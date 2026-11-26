# Migration log

Centralized record of Django migrations added from 25 November 2026 onward. Earlier migrations
(`accounts` 0001–0008, `access_control` 0001–0005) predate this log; their history is in Git and
the workflow evidence that introduced them. Append new entries; never rewrite earlier ones.

**Applied to `ctug_workspace`** means independently confirmed on the development database. The
original implementation sessions did not connect to `ctug_workspace` for migrations or tests;
later explicitly owner-authorized maintenance is recorded separately below. Original isolated
test results come from disposable MySQL databases named `test_ctug_registration_<16 hex>`
(created and destroyed by `config.test_runner.IsolatedMySQLRunner`).

| App / migration | Slice | Tables and columns | Depends on | Isolated test result | Applied to `ctug_workspace` | Commit |
| --- | --- | --- | --- | --- | --- | --- |
| `academic.0001_initial` | WF-11.01 Draft School Year and semester foundation | New `school_years`, `semesters` (status, `active_slot`, dates, version, lifecycle timestamps; UNIQUE and CHECK constraints), `academic_period_audit_logs` | `accounts` (AUTH_USER_MODEL) | Applied on every isolated run; `test_wf1101_periods`, `test_wf1101_http` passed (see WF-11.01 evidence) | **No**: not applied by this work; not checked (no connection made) | `49e600c` |
| `academic.0002_audit_reason_note` | WF-11.01 lifecycle, controlled edits, historical corrections | `academic_period_audit_logs.reason_note` (VARCHAR 500, NULL) | `academic.0001` | Applied on every isolated run; `test_wf1101_lifecycle` passed | **No**: not applied by this work; not checked | `73257f9` |
| `academic.0003_academic_configuration` | Academic configuration foundation (courses, subjects, sections, curricula, offerings, teaching assignments) | New `academic_courses`, `academic_subjects` (units CHECK), `academic_sections` (UNIQUE course/year/name), `academic_curriculum_versions` (UNIQUE course/label; lifecycle CHECK), `academic_curriculum_subjects` (UNIQUE curriculum/subject; plan index), `academic_subject_offerings` (UNIQUE semester/section/subject), `academic_teaching_assignments` (UNIQUE offering/`active_slot`; lifecycle CHECK), `academic_configuration_audit_logs`. All foreign keys PROTECT | `academic.0002`, `accounts` | Applied on every isolated run; `test_academic_configuration` 25/25, `test_academic_configuration_http` 6/6, WF-11.01 suites 74/74 | **No**: not applied by this work; not checked | `d8fe6d1` |
| `finance.0001_semester_fee_configuration` | Semester organizational fee configuration and approval (WF-11.01 activation prerequisite; WF-07.02 rate source) | New `finance_semester_fee_schedules` (UNIQUE `semester_id`; UNIQUE `current_approved_revision_id`), `finance_semester_fee_revisions` (`amount` DECIMAL(9,2) CHECK 0.00–100000.00, `currency` CHECK PHP; UNIQUE schedule/revision_number, schedule/`approved_slot`, schedule/`draft_slot`; lifecycle CHECK), `finance_audit_logs`. All foreign keys PROTECT | `academic.0003`, `accounts` | Applied on every isolated run; `apps.finance.test_semester_fees` 24/24 | **No**: not applied by this work; not checked | `fbc8b31` |
| `academic.0004_student_semester_onboarding` | WF-05.05 Student Semester Onboarding, WF-05.04 minimum verification (R-02 lanes), WF11-D15/16 verified gaps, WF11-D14 historical participation | New `academic_enrollment_evidence` (UNIQUE student/semester/`active_slot`; lifecycle and in-person attribution CHECKs; controlled reference only), `academic_enrollment_evidence_subjects`, `academic_enrollment_gap_exceptions` (UNIQUE student/semester/`active_slot`; lifecycle CHECK), `academic_semester_onboardings` (UNIQUE student/semester; Completed-consistency CHECK), `academic_semester_onboarding_subjects`, `academic_semester_participations` (UNIQUE student/semester; onboarding-link CHECK), `academic_participation_subjects` (UNIQUE participation/subject; instructor required). All foreign keys PROTECT | `academic.0003`, `accounts` | Applied on every isolated run; `test_student_onboarding` 36/36, `test_student_onboarding_concurrency` 6/6, `test_student_onboarding_http` 6/6, `test_wf1101_residual` 7/7; full backend regression 2423 run, 4 known pre-existing `apps.accounts` failures | **No**: not applied by this work; not checked (no connection made) | `f8cf1d6` |
| `clearance.0001_semester_clearance` | WF-06.01 minimum clearance created at onboarding finalization; WF-06.02 requirements | New `clearance_semester_clearances` (UNIQUE student/semester; OneToOne participation; status CHECK), `clearance_requirements` (UNIQUE clearance/`requirement_key`; shape CHECK: subject requirements need subject, offering and signatory, role requirements have none; status CHECK). All foreign keys PROTECT | `academic.0004`, `accounts` | Applied on every isolated run (same suites as `academic.0004`) | **No**: not applied by this work; not checked | `f8cf1d6` |
| `finance.0002_fee_obligation` | WF-07.02 full organizational-fee obligation snapshot created at onboarding finalization | New `finance_fee_obligations` (UNIQUE student/semester; OneToOne participation; `amount` DECIMAL(9,2) CHECK 0.00–100000.00; `currency` CHECK PHP; status Unpaid only). No payment, receipt or balance table | `academic.0004`, `finance.0001`, `accounts` | Applied on every isolated run (same suites as `academic.0004`); `apps.finance.test_semester_fees` 24/24 | **No**: not applied by this work; not checked | `f8cf1d6` |

## Applying to `ctug_workspace` (owner decision; not done here)

Applying any of the rows above requires a separate owner decision. After applying, record it in
this table with the date, the operator and how it was verified (for example
`manage.py showmigrations academic` output). The academic switches stay off until their own approvals.

## Pending permission inventory dependency, 26 November 2026

| App / migration | Schema effect | Direct dependency | Local evidence |
| --- | --- | --- | --- |
| `access_control.0004_ordinary_appointments` | Creates `ordinary_appointments` with account and audit-receipt foreign keys, document uniqueness and status indexes | `access_control.0003_remaining_access_control`, `accounts.0001_initial` | Ledger entry and table both absent on local MySQL. Applied on the isolated restore with zero new business rows. |
| `access_control.0005_account_permission_role_scopes` | Creates `account_permission_role_scopes` with a one-to-one link to an account override and a foreign key to a role | `access_control.0004_ordinary_appointments` | Ledger entry and table both absent on local MySQL. Applied after `0004` on the isolated restore with zero new scope rows. |

The recorded prerequisites were present on the verified live database. The isolated forward plan
added exactly the two entries above and ended with 31 ledger rows. The live ledger remained at 29.
All seven Academic Settings targets listed earlier were absent from the live ledger, along with
their 24 expected tables. [Read-only verification and isolated rehearsal](../operations/WF11_Migration_and_Activation_Runbook_2026-11-26.md#authorized-ledger-check-and-isolated-restore-rehearsal).

## Authorized access-control maintenance, 26 November 2026

Continued from `7d9624f` on `ronald`. Named operator **Ronald**, owner-confirmed current-session
maintenance window; writers stopped through final verification at **20:20:55 Asia/Manila**.
The fresh encrypted full backup passed restoration and data/schema comparison before live work.

| Migration | Applied to actual `ctug_workspace` | Verification |
| --- | --- | --- |
| `access_control.0004_ordinary_appointments` | **Yes**, 26 November 2026, Ronald | Exact single-target forward plan and rehearsed DDL; ledger present once; empty table; PK, document uniqueness, lookup/expiry indexes and seven FKs match rehearsal. |
| `access_control.0005_account_permission_role_scopes` | **Yes**, immediately after `0004`, Ronald | Exact single-target forward plan and rehearsed DDL; ledger present once; empty table; one-to-one PK and two FKs match rehearsal; current leaf plan empty. |

Actual database: **22 tables / 31 migration rows**. All 17 existing application tables retain
their schema and row hashes; Django added only two ledger rows, two content types and eight
framework permissions. All 35 FK and 42 unique-key checks passed; nine CHECK constraints are
enforced. No HDAC permission, role binding, account override or business row was provisioned.

The seven Academic Settings migrations were rehearsed in the runbook's exact order on an isolated
restore: **24 tables / 224 columns verified, 90 prepared integrity queries passed**, no existing
application data changed. They remain **unapplied to the actual database**, with all seven ledger
entries and all 24 tables absent. All feature switches remain OFF; v2.3 is inactive and independent
governance review stays OPEN. [Backup, recovery and execution evidence](../operations/WF11_Migration_and_Activation_Runbook_2026-11-26.md#authorized-local-maintenance-execution-26-november-2026).
