# Migration log

Centralized record of Django migrations added from 25 November 2026 onward. Earlier migrations
(`accounts` 0001–0008, `access_control` 0001–0005) predate this log; their history is in Git and
the workflow evidence that introduced them. Append new entries; never rewrite earlier ones.

**Applied to `ctug_workspace`** means independently confirmed on the development database. The
implementing sessions never connect to `ctug_workspace` for migrations or tests; isolated results
come from disposable MySQL databases named `test_ctug_registration_<16 hex>` (created and destroyed
by `config.test_runner.IsolatedMySQLRunner`).

| App / migration | Slice | Tables and columns | Depends on | Isolated test result | Applied to `ctug_workspace` | Commit |
| --- | --- | --- | --- | --- | --- | --- |
| `academic.0001_initial` | WF-11.01 Draft School Year and semester foundation | New `school_years`, `semesters` (status, `active_slot`, dates, version, lifecycle timestamps; UNIQUE and CHECK constraints), `academic_period_audit_logs` | `accounts` (AUTH_USER_MODEL) | Applied on every isolated run; `test_wf1101_periods`, `test_wf1101_http` passed (see WF-11.01 evidence) | **No**: not applied by this work; not checked (no connection made) | `49e600c` |
| `academic.0002_audit_reason_note` | WF-11.01 lifecycle, controlled edits, historical corrections | `academic_period_audit_logs.reason_note` (VARCHAR 500, NULL) | `academic.0001` | Applied on every isolated run; `test_wf1101_lifecycle` passed | **No**: not applied by this work; not checked | `73257f9` |
| `academic.0003_academic_configuration` | Academic configuration foundation (courses, subjects, sections, curricula, offerings, teaching assignments) | New `academic_courses`, `academic_subjects` (units CHECK), `academic_sections` (UNIQUE course/year/name), `academic_curriculum_versions` (UNIQUE course/label; lifecycle CHECK), `academic_curriculum_subjects` (UNIQUE curriculum/subject; plan index), `academic_subject_offerings` (UNIQUE semester/section/subject), `academic_teaching_assignments` (UNIQUE offering/`active_slot`; lifecycle CHECK), `academic_configuration_audit_logs`. All foreign keys PROTECT | `academic.0002`, `accounts` | Applied on every isolated run; `test_academic_configuration` 25/25, `test_academic_configuration_http` 6/6, WF-11.01 suites 74/74 | **No**: not applied by this work; not checked | `d8fe6d1` |

## Applying to `ctug_workspace` (owner decision; not done here)

Applying any of the rows above requires a separate owner decision. After applying, record it in
this table with the date, the operator and how it was verified (for example
`manage.py showmigrations academic` output). The academic switches stay off until their own approvals.
