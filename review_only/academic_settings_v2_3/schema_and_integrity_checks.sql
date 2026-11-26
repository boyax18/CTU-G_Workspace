-- PREPARED ONLY. Execute only under a separate schema/data-inspection authorization.

-- Select ctug_workspace explicitly in the client; verify the identity before continuing.

SELECT DATABASE() AS expected_ctug_workspace, VERSION() AS server_version;

SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;

SET SESSION TRANSACTION READ ONLY;

START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;

SELECT app,name,COUNT(*) AS ledger_rows FROM django_migrations WHERE app IN ('academic','clearance','finance') GROUP BY app,name ORDER BY app,name;

SHOW CREATE TABLE `academic_configuration_audit_logs`;

SELECT 'academic_configuration_audit_logs' AS table_name,COUNT(*) AS row_count FROM `academic_configuration_audit_logs`;

SELECT 'academic_configuration_audit_logs.actor_account_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_configuration_audit_logs` t LEFT JOIN `accounts` p ON t.`actor_account_id`=p.`account_id` WHERE t.`actor_account_id` IS NOT NULL AND p.`account_id` IS NULL;

SHOW CREATE TABLE `academic_courses`;

SELECT 'academic_courses' AS table_name,COUNT(*) AS row_count FROM `academic_courses`;

SELECT 'academic_courses.created_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_courses` t LEFT JOIN `accounts` p ON t.`created_by`=p.`account_id` WHERE t.`created_by` IS NOT NULL AND p.`account_id` IS NULL;

SHOW CREATE TABLE `academic_curriculum_subjects`;

SELECT 'academic_curriculum_subjects' AS table_name,COUNT(*) AS row_count FROM `academic_curriculum_subjects`;

SELECT 'academic_curriculum_subjects.curriculum_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_curriculum_subjects` t LEFT JOIN `academic_curriculum_versions` p ON t.`curriculum_id`=p.`curriculum_id` WHERE t.`curriculum_id` IS NOT NULL AND p.`curriculum_id` IS NULL;

SELECT 'academic_curriculum_subjects.subject_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_curriculum_subjects` t LEFT JOIN `academic_subjects` p ON t.`subject_id`=p.`subject_id` WHERE t.`subject_id` IS NOT NULL AND p.`subject_id` IS NULL;

SELECT 'academic_curriculum_subject_unique' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `curriculum_id`,`subject_id` FROM `academic_curriculum_subjects` WHERE `curriculum_id` IS NOT NULL AND `subject_id` IS NOT NULL GROUP BY `curriculum_id`,`subject_id` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `academic_curriculum_versions`;

SELECT 'academic_curriculum_versions' AS table_name,COUNT(*) AS row_count FROM `academic_curriculum_versions`;

SELECT 'academic_curriculum_versions.course_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_curriculum_versions` t LEFT JOIN `academic_courses` p ON t.`course_id`=p.`course_id` WHERE t.`course_id` IS NOT NULL AND p.`course_id` IS NULL;

SELECT 'academic_curriculum_versions.created_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_curriculum_versions` t LEFT JOIN `accounts` p ON t.`created_by`=p.`account_id` WHERE t.`created_by` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_curricula_course_label_unique' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `course_id`,`label` FROM `academic_curriculum_versions` WHERE `course_id` IS NOT NULL AND `label` IS NOT NULL GROUP BY `course_id`,`label` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `academic_enrollment_evidence`;

SELECT 'academic_enrollment_evidence' AS table_name,COUNT(*) AS row_count FROM `academic_enrollment_evidence`;

SELECT 'academic_enrollment_evidence.course_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_enrollment_evidence` t LEFT JOIN `academic_courses` p ON t.`course_id`=p.`course_id` WHERE t.`course_id` IS NOT NULL AND p.`course_id` IS NULL;

SELECT 'academic_enrollment_evidence.revoked_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_enrollment_evidence` t LEFT JOIN `accounts` p ON t.`revoked_by`=p.`account_id` WHERE t.`revoked_by` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_enrollment_evidence.semester_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_enrollment_evidence` t LEFT JOIN `semesters` p ON t.`semester_id`=p.`semester_id` WHERE t.`semester_id` IS NOT NULL AND p.`semester_id` IS NULL;

SELECT 'academic_enrollment_evidence.student_account_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_enrollment_evidence` t LEFT JOIN `accounts` p ON t.`student_account_id`=p.`account_id` WHERE t.`student_account_id` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_enrollment_evidence.verified_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_enrollment_evidence` t LEFT JOIN `accounts` p ON t.`verified_by`=p.`account_id` WHERE t.`verified_by` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_evidence_one_verified' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `student_account_id`,`semester_id`,`active_slot` FROM `academic_enrollment_evidence` WHERE `student_account_id` IS NOT NULL AND `semester_id` IS NOT NULL AND `active_slot` IS NOT NULL GROUP BY `student_account_id`,`semester_id`,`active_slot` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `academic_enrollment_evidence_subjects`;

SELECT 'academic_enrollment_evidence_subjects' AS table_name,COUNT(*) AS row_count FROM `academic_enrollment_evidence_subjects`;

SELECT 'academic_enrollment_evidence_subjects.evidence_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_enrollment_evidence_subjects` t LEFT JOIN `academic_enrollment_evidence` p ON t.`evidence_id`=p.`evidence_id` WHERE t.`evidence_id` IS NOT NULL AND p.`evidence_id` IS NULL;

SELECT 'academic_enrollment_evidence_subjects.subject_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_enrollment_evidence_subjects` t LEFT JOIN `academic_subjects` p ON t.`subject_id`=p.`subject_id` WHERE t.`subject_id` IS NOT NULL AND p.`subject_id` IS NULL;

SELECT 'academic_evidence_subject_unique' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `evidence_id`,`subject_id` FROM `academic_enrollment_evidence_subjects` WHERE `evidence_id` IS NOT NULL AND `subject_id` IS NOT NULL GROUP BY `evidence_id`,`subject_id` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `academic_enrollment_gap_exceptions`;

SELECT 'academic_enrollment_gap_exceptions' AS table_name,COUNT(*) AS row_count FROM `academic_enrollment_gap_exceptions`;

SELECT 'academic_enrollment_gap_exceptions.revoked_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_enrollment_gap_exceptions` t LEFT JOIN `accounts` p ON t.`revoked_by`=p.`account_id` WHERE t.`revoked_by` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_enrollment_gap_exceptions.semester_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_enrollment_gap_exceptions` t LEFT JOIN `semesters` p ON t.`semester_id`=p.`semester_id` WHERE t.`semester_id` IS NOT NULL AND p.`semester_id` IS NULL;

SELECT 'academic_enrollment_gap_exceptions.student_account_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_enrollment_gap_exceptions` t LEFT JOIN `accounts` p ON t.`student_account_id`=p.`account_id` WHERE t.`student_account_id` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_enrollment_gap_exceptions.verified_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_enrollment_gap_exceptions` t LEFT JOIN `accounts` p ON t.`verified_by`=p.`account_id` WHERE t.`verified_by` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_gap_one_verified' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `student_account_id`,`semester_id`,`active_slot` FROM `academic_enrollment_gap_exceptions` WHERE `student_account_id` IS NOT NULL AND `semester_id` IS NOT NULL AND `active_slot` IS NOT NULL GROUP BY `student_account_id`,`semester_id`,`active_slot` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `academic_participation_subjects`;

SELECT 'academic_participation_subjects' AS table_name,COUNT(*) AS row_count FROM `academic_participation_subjects`;

SELECT 'academic_participation_subjects.instructor_account_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_participation_subjects` t LEFT JOIN `accounts` p ON t.`instructor_account_id`=p.`account_id` WHERE t.`instructor_account_id` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_participation_subjects.offering_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_participation_subjects` t LEFT JOIN `academic_subject_offerings` p ON t.`offering_id`=p.`offering_id` WHERE t.`offering_id` IS NOT NULL AND p.`offering_id` IS NULL;

SELECT 'academic_participation_subjects.subject_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_participation_subjects` t LEFT JOIN `academic_subjects` p ON t.`subject_id`=p.`subject_id` WHERE t.`subject_id` IS NOT NULL AND p.`subject_id` IS NULL;

SELECT 'academic_participation_subjects.participation_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_participation_subjects` t LEFT JOIN `academic_semester_participations` p ON t.`participation_id`=p.`participation_id` WHERE t.`participation_id` IS NOT NULL AND p.`participation_id` IS NULL;

SELECT 'academic_participation_subject_unique' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `participation_id`,`subject_id` FROM `academic_participation_subjects` WHERE `participation_id` IS NOT NULL AND `subject_id` IS NOT NULL GROUP BY `participation_id`,`subject_id` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `academic_period_audit_logs`;

SELECT 'academic_period_audit_logs' AS table_name,COUNT(*) AS row_count FROM `academic_period_audit_logs`;

SELECT 'academic_period_audit_logs.actor_account_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_period_audit_logs` t LEFT JOIN `accounts` p ON t.`actor_account_id`=p.`account_id` WHERE t.`actor_account_id` IS NOT NULL AND p.`account_id` IS NULL;

SHOW CREATE TABLE `academic_sections`;

SELECT 'academic_sections' AS table_name,COUNT(*) AS row_count FROM `academic_sections`;

SELECT 'academic_sections.course_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_sections` t LEFT JOIN `academic_courses` p ON t.`course_id`=p.`course_id` WHERE t.`course_id` IS NOT NULL AND p.`course_id` IS NULL;

SELECT 'academic_sections.created_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_sections` t LEFT JOIN `accounts` p ON t.`created_by`=p.`account_id` WHERE t.`created_by` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_sections_unique' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `course_id`,`year_level`,`name` FROM `academic_sections` WHERE `course_id` IS NOT NULL AND `year_level` IS NOT NULL AND `name` IS NOT NULL GROUP BY `course_id`,`year_level`,`name` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `academic_semester_onboarding_subjects`;

SELECT 'academic_semester_onboarding_subjects' AS table_name,COUNT(*) AS row_count FROM `academic_semester_onboarding_subjects`;

SELECT 'academic_semester_onboarding_subjects.offering_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_semester_onboarding_subjects` t LEFT JOIN `academic_subject_offerings` p ON t.`offering_id`=p.`offering_id` WHERE t.`offering_id` IS NOT NULL AND p.`offering_id` IS NULL;

SELECT 'academic_semester_onboarding_subjects.onboarding_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_semester_onboarding_subjects` t LEFT JOIN `academic_semester_onboardings` p ON t.`onboarding_id`=p.`onboarding_id` WHERE t.`onboarding_id` IS NOT NULL AND p.`onboarding_id` IS NULL;

SELECT 'academic_semester_onboarding_subjects.subject_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_semester_onboarding_subjects` t LEFT JOIN `academic_subjects` p ON t.`subject_id`=p.`subject_id` WHERE t.`subject_id` IS NOT NULL AND p.`subject_id` IS NULL;

SELECT 'academic_onboarding_subject_unique' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `onboarding_id`,`subject_id` FROM `academic_semester_onboarding_subjects` WHERE `onboarding_id` IS NOT NULL AND `subject_id` IS NOT NULL GROUP BY `onboarding_id`,`subject_id` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `academic_semester_onboardings`;

SELECT 'academic_semester_onboardings' AS table_name,COUNT(*) AS row_count FROM `academic_semester_onboardings`;

SELECT 'academic_semester_onboardings.course_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_semester_onboardings` t LEFT JOIN `academic_courses` p ON t.`course_id`=p.`course_id` WHERE t.`course_id` IS NOT NULL AND p.`course_id` IS NULL;

SELECT 'academic_semester_onboardings.semester_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_semester_onboardings` t LEFT JOIN `semesters` p ON t.`semester_id`=p.`semester_id` WHERE t.`semester_id` IS NOT NULL AND p.`semester_id` IS NULL;

SELECT 'academic_semester_onboardings.student_account_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_semester_onboardings` t LEFT JOIN `accounts` p ON t.`student_account_id`=p.`account_id` WHERE t.`student_account_id` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_onboarding_unique' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `student_account_id`,`semester_id` FROM `academic_semester_onboardings` WHERE `student_account_id` IS NOT NULL AND `semester_id` IS NOT NULL GROUP BY `student_account_id`,`semester_id` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `academic_semester_participations`;

SELECT 'academic_semester_participations' AS table_name,COUNT(*) AS row_count FROM `academic_semester_participations`;

SELECT 'academic_semester_participations.course_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_semester_participations` t LEFT JOIN `academic_courses` p ON t.`course_id`=p.`course_id` WHERE t.`course_id` IS NOT NULL AND p.`course_id` IS NULL;

SELECT 'academic_semester_participations.created_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_semester_participations` t LEFT JOIN `accounts` p ON t.`created_by`=p.`account_id` WHERE t.`created_by` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_semester_participations.evidence_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_semester_participations` t LEFT JOIN `academic_enrollment_evidence` p ON t.`evidence_id`=p.`evidence_id` WHERE t.`evidence_id` IS NOT NULL AND p.`evidence_id` IS NULL;

SELECT 'academic_semester_participations.onboarding_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_semester_participations` t LEFT JOIN `academic_semester_onboardings` p ON t.`onboarding_id`=p.`onboarding_id` WHERE t.`onboarding_id` IS NOT NULL AND p.`onboarding_id` IS NULL;

SELECT 'academic_semester_participations.semester_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_semester_participations` t LEFT JOIN `semesters` p ON t.`semester_id`=p.`semester_id` WHERE t.`semester_id` IS NOT NULL AND p.`semester_id` IS NULL;

SELECT 'academic_semester_participations.student_account_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_semester_participations` t LEFT JOIN `accounts` p ON t.`student_account_id`=p.`account_id` WHERE t.`student_account_id` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_participation_unique' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `student_account_id`,`semester_id` FROM `academic_semester_participations` WHERE `student_account_id` IS NOT NULL AND `semester_id` IS NOT NULL GROUP BY `student_account_id`,`semester_id` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `academic_subject_offerings`;

SELECT 'academic_subject_offerings' AS table_name,COUNT(*) AS row_count FROM `academic_subject_offerings`;

SELECT 'academic_subject_offerings.created_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_subject_offerings` t LEFT JOIN `accounts` p ON t.`created_by`=p.`account_id` WHERE t.`created_by` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_subject_offerings.curriculum_subject_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_subject_offerings` t LEFT JOIN `academic_curriculum_subjects` p ON t.`curriculum_subject_id`=p.`curriculum_subject_id` WHERE t.`curriculum_subject_id` IS NOT NULL AND p.`curriculum_subject_id` IS NULL;

SELECT 'academic_subject_offerings.section_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_subject_offerings` t LEFT JOIN `academic_sections` p ON t.`section_id`=p.`section_id` WHERE t.`section_id` IS NOT NULL AND p.`section_id` IS NULL;

SELECT 'academic_subject_offerings.semester_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_subject_offerings` t LEFT JOIN `semesters` p ON t.`semester_id`=p.`semester_id` WHERE t.`semester_id` IS NOT NULL AND p.`semester_id` IS NULL;

SELECT 'academic_subject_offerings.subject_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_subject_offerings` t LEFT JOIN `academic_subjects` p ON t.`subject_id`=p.`subject_id` WHERE t.`subject_id` IS NOT NULL AND p.`subject_id` IS NULL;

SELECT 'academic_offerings_natural_key' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `semester_id`,`section_id`,`subject_id` FROM `academic_subject_offerings` WHERE `semester_id` IS NOT NULL AND `section_id` IS NOT NULL AND `subject_id` IS NOT NULL GROUP BY `semester_id`,`section_id`,`subject_id` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `academic_subjects`;

SELECT 'academic_subjects' AS table_name,COUNT(*) AS row_count FROM `academic_subjects`;

SELECT 'academic_subjects.created_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_subjects` t LEFT JOIN `accounts` p ON t.`created_by`=p.`account_id` WHERE t.`created_by` IS NOT NULL AND p.`account_id` IS NULL;

SHOW CREATE TABLE `academic_teaching_assignments`;

SELECT 'academic_teaching_assignments' AS table_name,COUNT(*) AS row_count FROM `academic_teaching_assignments`;

SELECT 'academic_teaching_assignments.assigned_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_teaching_assignments` t LEFT JOIN `accounts` p ON t.`assigned_by`=p.`account_id` WHERE t.`assigned_by` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_teaching_assignments.ended_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_teaching_assignments` t LEFT JOIN `accounts` p ON t.`ended_by`=p.`account_id` WHERE t.`ended_by` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_teaching_assignments.instructor_account_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_teaching_assignments` t LEFT JOIN `accounts` p ON t.`instructor_account_id`=p.`account_id` WHERE t.`instructor_account_id` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'academic_teaching_assignments.offering_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `academic_teaching_assignments` t LEFT JOIN `academic_subject_offerings` p ON t.`offering_id`=p.`offering_id` WHERE t.`offering_id` IS NOT NULL AND p.`offering_id` IS NULL;

SELECT 'academic_teaching_one_active' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `offering_id`,`active_slot` FROM `academic_teaching_assignments` WHERE `offering_id` IS NOT NULL AND `active_slot` IS NOT NULL GROUP BY `offering_id`,`active_slot` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `clearance_requirements`;

SELECT 'clearance_requirements' AS table_name,COUNT(*) AS row_count FROM `clearance_requirements`;

SELECT 'clearance_requirements.offering_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `clearance_requirements` t LEFT JOIN `academic_subject_offerings` p ON t.`offering_id`=p.`offering_id` WHERE t.`offering_id` IS NOT NULL AND p.`offering_id` IS NULL;

SELECT 'clearance_requirements.signatory_account_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `clearance_requirements` t LEFT JOIN `accounts` p ON t.`signatory_account_id`=p.`account_id` WHERE t.`signatory_account_id` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'clearance_requirements.subject_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `clearance_requirements` t LEFT JOIN `academic_subjects` p ON t.`subject_id`=p.`subject_id` WHERE t.`subject_id` IS NOT NULL AND p.`subject_id` IS NULL;

SELECT 'clearance_requirements.clearance_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `clearance_requirements` t LEFT JOIN `clearance_semester_clearances` p ON t.`clearance_id`=p.`clearance_id` WHERE t.`clearance_id` IS NOT NULL AND p.`clearance_id` IS NULL;

SELECT 'clearance_requirement_unique' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `clearance_id`,`requirement_key` FROM `clearance_requirements` WHERE `clearance_id` IS NOT NULL AND `requirement_key` IS NOT NULL GROUP BY `clearance_id`,`requirement_key` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `clearance_semester_clearances`;

SELECT 'clearance_semester_clearances' AS table_name,COUNT(*) AS row_count FROM `clearance_semester_clearances`;

SELECT 'clearance_semester_clearances.participation_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `clearance_semester_clearances` t LEFT JOIN `academic_semester_participations` p ON t.`participation_id`=p.`participation_id` WHERE t.`participation_id` IS NOT NULL AND p.`participation_id` IS NULL;

SELECT 'clearance_semester_clearances.semester_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `clearance_semester_clearances` t LEFT JOIN `semesters` p ON t.`semester_id`=p.`semester_id` WHERE t.`semester_id` IS NOT NULL AND p.`semester_id` IS NULL;

SELECT 'clearance_semester_clearances.student_account_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `clearance_semester_clearances` t LEFT JOIN `accounts` p ON t.`student_account_id`=p.`account_id` WHERE t.`student_account_id` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'clearance_one_per_student_semester' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `student_account_id`,`semester_id` FROM `clearance_semester_clearances` WHERE `student_account_id` IS NOT NULL AND `semester_id` IS NOT NULL GROUP BY `student_account_id`,`semester_id` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `finance_audit_logs`;

SELECT 'finance_audit_logs' AS table_name,COUNT(*) AS row_count FROM `finance_audit_logs`;

SELECT 'finance_audit_logs.actor_account_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `finance_audit_logs` t LEFT JOIN `accounts` p ON t.`actor_account_id`=p.`account_id` WHERE t.`actor_account_id` IS NOT NULL AND p.`account_id` IS NULL;

SHOW CREATE TABLE `finance_fee_obligations`;

SELECT 'finance_fee_obligations' AS table_name,COUNT(*) AS row_count FROM `finance_fee_obligations`;

SELECT 'finance_fee_obligations.fee_revision_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `finance_fee_obligations` t LEFT JOIN `finance_semester_fee_revisions` p ON t.`fee_revision_id`=p.`revision_id` WHERE t.`fee_revision_id` IS NOT NULL AND p.`revision_id` IS NULL;

SELECT 'finance_fee_obligations.participation_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `finance_fee_obligations` t LEFT JOIN `academic_semester_participations` p ON t.`participation_id`=p.`participation_id` WHERE t.`participation_id` IS NOT NULL AND p.`participation_id` IS NULL;

SELECT 'finance_fee_obligations.semester_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `finance_fee_obligations` t LEFT JOIN `semesters` p ON t.`semester_id`=p.`semester_id` WHERE t.`semester_id` IS NOT NULL AND p.`semester_id` IS NULL;

SELECT 'finance_fee_obligations.student_account_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `finance_fee_obligations` t LEFT JOIN `accounts` p ON t.`student_account_id`=p.`account_id` WHERE t.`student_account_id` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'finance_obligation_one_per_student_semester' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `student_account_id`,`semester_id` FROM `finance_fee_obligations` WHERE `student_account_id` IS NOT NULL AND `semester_id` IS NOT NULL GROUP BY `student_account_id`,`semester_id` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `finance_semester_fee_revisions`;

SELECT 'finance_semester_fee_revisions' AS table_name,COUNT(*) AS row_count FROM `finance_semester_fee_revisions`;

SELECT 'finance_semester_fee_revisions.approved_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `finance_semester_fee_revisions` t LEFT JOIN `accounts` p ON t.`approved_by`=p.`account_id` WHERE t.`approved_by` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'finance_semester_fee_revisions.configured_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `finance_semester_fee_revisions` t LEFT JOIN `accounts` p ON t.`configured_by`=p.`account_id` WHERE t.`configured_by` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'finance_semester_fee_revisions.schedule_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `finance_semester_fee_revisions` t LEFT JOIN `finance_semester_fee_schedules` p ON t.`schedule_id`=p.`schedule_id` WHERE t.`schedule_id` IS NOT NULL AND p.`schedule_id` IS NULL;

SELECT 'finance_fee_revision_number_unique' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `schedule_id`,`revision_number` FROM `finance_semester_fee_revisions` WHERE `schedule_id` IS NOT NULL AND `revision_number` IS NOT NULL GROUP BY `schedule_id`,`revision_number` HAVING COUNT(*)>1) duplicates;

SELECT 'finance_fee_one_approved' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `schedule_id`,`approved_slot` FROM `finance_semester_fee_revisions` WHERE `schedule_id` IS NOT NULL AND `approved_slot` IS NOT NULL GROUP BY `schedule_id`,`approved_slot` HAVING COUNT(*)>1) duplicates;

SELECT 'finance_fee_one_open_draft' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `schedule_id`,`draft_slot` FROM `finance_semester_fee_revisions` WHERE `schedule_id` IS NOT NULL AND `draft_slot` IS NOT NULL GROUP BY `schedule_id`,`draft_slot` HAVING COUNT(*)>1) duplicates;

SHOW CREATE TABLE `finance_semester_fee_schedules`;

SELECT 'finance_semester_fee_schedules' AS table_name,COUNT(*) AS row_count FROM `finance_semester_fee_schedules`;

SELECT 'finance_semester_fee_schedules.created_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `finance_semester_fee_schedules` t LEFT JOIN `accounts` p ON t.`created_by`=p.`account_id` WHERE t.`created_by` IS NOT NULL AND p.`account_id` IS NULL;

SELECT 'finance_semester_fee_schedules.current_approved_revision_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `finance_semester_fee_schedules` t LEFT JOIN `finance_semester_fee_revisions` p ON t.`current_approved_revision_id`=p.`revision_id` WHERE t.`current_approved_revision_id` IS NOT NULL AND p.`revision_id` IS NULL;

SELECT 'finance_semester_fee_schedules.semester_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `finance_semester_fee_schedules` t LEFT JOIN `semesters` p ON t.`semester_id`=p.`semester_id` WHERE t.`semester_id` IS NOT NULL AND p.`semester_id` IS NULL;

SHOW CREATE TABLE `school_years`;

SELECT 'school_years' AS table_name,COUNT(*) AS row_count FROM `school_years`;

SELECT 'school_years.created_by' AS foreign_key_check,COUNT(*) AS orphan_count FROM `school_years` t LEFT JOIN `accounts` p ON t.`created_by`=p.`account_id` WHERE t.`created_by` IS NOT NULL AND p.`account_id` IS NULL;

SHOW CREATE TABLE `semesters`;

SELECT 'semesters' AS table_name,COUNT(*) AS row_count FROM `semesters`;

SELECT 'semesters.school_year_id' AS foreign_key_check,COUNT(*) AS orphan_count FROM `semesters` t LEFT JOIN `school_years` p ON t.`school_year_id`=p.`school_year_id` WHERE t.`school_year_id` IS NOT NULL AND p.`school_year_id` IS NULL;

SELECT 'semesters_school_year_term_unique' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT `school_year_id`,`term` FROM `semesters` WHERE `school_year_id` IS NOT NULL AND `term` IS NOT NULL GROUP BY `school_year_id`,`term` HAVING COUNT(*)>1) duplicates;

SELECT 'atomic_participation_bundle' AS integrity_check,COUNT(*) AS violation_count FROM academic_semester_participations p LEFT JOIN clearance_semester_clearances c ON c.participation_id=p.participation_id LEFT JOIN finance_fee_obligations o ON o.participation_id=p.participation_id WHERE c.clearance_id IS NULL OR o.obligation_id IS NULL OR c.student_account_id<>p.student_account_id OR c.semester_id<>p.semester_id OR o.student_account_id<>p.student_account_id OR o.semester_id<>p.semester_id;

SELECT 'completed_onboarding' AS integrity_check,COUNT(*) AS violation_count FROM academic_semester_onboardings b LEFT JOIN academic_semester_participations p ON p.onboarding_id=b.onboarding_id WHERE b.status='Completed' AND (p.participation_id IS NULL OR p.student_account_id<>b.student_account_id OR p.semester_id<>b.semester_id);

SELECT 'fee_snapshot' AS integrity_check,COUNT(*) AS violation_count FROM finance_fee_obligations o JOIN finance_semester_fee_revisions r ON r.revision_id=o.fee_revision_id JOIN finance_semester_fee_schedules s ON s.schedule_id=r.schedule_id WHERE o.amount<>r.amount OR o.currency<>r.currency OR o.semester_id<>s.semester_id;

SELECT 'subject_signatory' AS integrity_check,COUNT(*) AS violation_count FROM clearance_requirements r JOIN clearance_semester_clearances c ON c.clearance_id=r.clearance_id LEFT JOIN academic_participation_subjects p ON p.participation_id=c.participation_id AND p.subject_id=r.subject_id AND p.offering_id=r.offering_id WHERE r.kind='subject_instructor' AND (p.id IS NULL OR p.instructor_account_id<>r.signatory_account_id OR c.student_account_id=r.signatory_account_id);

SELECT 'requirement_count' AS integrity_check,COUNT(*) AS violation_count FROM clearance_semester_clearances c WHERE (SELECT COUNT(*) FROM clearance_requirements r WHERE r.clearance_id=c.clearance_id)<>(SELECT COUNT(*)+2 FROM academic_participation_subjects p WHERE p.participation_id=c.participation_id);

ROLLBACK;
