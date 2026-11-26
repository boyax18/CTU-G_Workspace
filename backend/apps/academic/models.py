"""WF-11.01 academic-period foundation: School Years, their two semesters and change history.

Owner-authorized restricted local development, 25 November 2026 (WF11-D01 to D13 scope only).

* A School Year is identified by its starting calendar year (``2026`` means S.Y. 2026-2027). It has
  no status column of its own: its status is derived from its two semesters (WF11-D09).
* Every School Year has exactly one First and one Second Semester, created together in one
  transaction by ``apps.academic.services.create_school_year`` (WF11-D01).
* Semester status is Draft, Active, Closed or Archived. Lifecycle timestamps and the database
  CHECK constraints below keep the states consistent: a Draft has never been activated, and a
  period never returns to Draft or Active once Closed (WF11-D02, D11, D12).
* MySQL has no partial unique index, so "at most one Active semester campus-wide" (WF11-D04) is a
  UNIQUE nullable ``active_slot`` that is 1 only while Active (NULLs never collide), tied to the
  status by a CHECK constraint. Transitions also serialize on a row lock (see lifecycle.py).
* Draft dates may be incomplete. A configured range must start before it ends; every non-Draft
  period must have both dates.
* The audit table references periods by plain integer IDs, not foreign keys, so deleting an unused
  Draft School Year never deletes or orphans its own creation history.

These models are deliberately NOT registered in Django Admin: the only write path is the
service layer, which enforces Hybrid Dynamic Access Control and writes the audit row.
"""

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.accounts.fields import CurrentTimestamp, MySQLEnumField, MySQLTimestampField

MIN_START_YEAR = 2000
MAX_START_YEAR = 2100


class SemesterTerm(models.IntegerChoices):
    FIRST = 1, "First semester"
    SECOND = 2, "Second semester"


class SemesterStatus(models.TextChoices):
    DRAFT = "Draft", "Draft"
    ACTIVE = "Active", "Active"
    CLOSED = "Closed", "Closed"
    ARCHIVED = "Archived", "Archived"


class SchoolYear(models.Model):
    school_year_id = models.AutoField(primary_key=True)
    start_year = models.PositiveSmallIntegerField(unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, db_column="created_by", on_delete=models.PROTECT,
        related_name="school_years_created", editable=False,
    )
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    updated_at = MySQLTimestampField(db_default=CurrentTimestamp())

    class Meta:
        db_table = "school_years"
        constraints = [
            models.CheckConstraint(
                condition=Q(start_year__gte=MIN_START_YEAR, start_year__lte=MAX_START_YEAR),
                name="school_years_start_year_range",
            ),
        ]

    @property
    def end_year(self):
        return self.start_year + 1

    @property
    def label(self):
        return f"{self.start_year}–{self.end_year}"

    def __str__(self):
        return f"S.Y. {self.label}"


class Semester(models.Model):
    semester_id = models.AutoField(primary_key=True)
    school_year = models.ForeignKey(
        SchoolYear, db_column="school_year_id", on_delete=models.PROTECT, related_name="semesters",
    )
    term = models.PositiveSmallIntegerField(choices=SemesterTerm.choices)
    status = MySQLEnumField(max_length=8, choices=SemesterStatus.choices, default=SemesterStatus.DRAFT,
                            db_default=SemesterStatus.DRAFT)
    # 1 while Active, otherwise NULL. UNIQUE: at most one Active semester campus-wide.
    active_slot = models.PositiveSmallIntegerField(null=True, blank=True, unique=True, editable=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    # Optimistic concurrency: every accepted change advances the version the caller confirmed.
    version = models.PositiveIntegerField(default=1, db_default=1)
    activated_at = MySQLTimestampField(null=True, blank=True, editable=False)
    closed_at = MySQLTimestampField(null=True, blank=True, editable=False)
    archived_at = MySQLTimestampField(null=True, blank=True, editable=False)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    updated_at = MySQLTimestampField(db_default=CurrentTimestamp())

    class Meta:
        db_table = "semesters"
        constraints = [
            models.UniqueConstraint(fields=["school_year", "term"], name="semesters_school_year_term_unique"),
            models.CheckConstraint(condition=Q(term__in=[1, 2]), name="semesters_term_valid"),
            models.CheckConstraint(
                condition=Q(start_date__isnull=True) | Q(end_date__isnull=True) | Q(start_date__lt=F("end_date")),
                name="semesters_start_before_end",
            ),
            # "IS NOT NULL" is explicit: SQL CHECK passes on NULL, and "active_slot = 1" alone is NULL
            # (not FALSE) for an Active row whose slot is missing.
            models.CheckConstraint(
                condition=(Q(status=SemesterStatus.ACTIVE, active_slot__isnull=False, active_slot=1)
                           | (~Q(status=SemesterStatus.ACTIVE) & Q(active_slot__isnull=True))),
                name="semesters_active_slot_matches_status",
            ),
            # Lifecycle consistency: Draft was never activated; Active is open; Closed/Archived are
            # never reopened; any non-Draft period has a complete date range.
            models.CheckConstraint(
                condition=(
                    Q(status=SemesterStatus.DRAFT, activated_at__isnull=True, closed_at__isnull=True,
                      archived_at__isnull=True)
                    | Q(status=SemesterStatus.ACTIVE, activated_at__isnull=False, closed_at__isnull=True,
                        archived_at__isnull=True, start_date__isnull=False, end_date__isnull=False)
                    | Q(status=SemesterStatus.CLOSED, activated_at__isnull=False, closed_at__isnull=False,
                        archived_at__isnull=True, start_date__isnull=False, end_date__isnull=False)
                    | Q(status=SemesterStatus.ARCHIVED, activated_at__isnull=False, closed_at__isnull=False,
                        archived_at__isnull=False, start_date__isnull=False, end_date__isnull=False)
                ),
                name="semesters_lifecycle_consistent",
            ),
        ]

    @property
    def label(self):
        return SemesterTerm(self.term).label

    def __str__(self):
        return f"{self.label}, S.Y. {self.school_year_id}"


class AcademicPeriodAuditLog(models.Model):
    """Append-only attributable history of academic-period changes.

    Written only by the service layer inside the same transaction as the change. School Year and
    semester references are plain integers so history survives a permitted Draft deletion.
    """

    academic_period_audit_log_id = models.AutoField(primary_key=True)
    actor_account = models.ForeignKey(
        settings.AUTH_USER_MODEL, db_column="actor_account_id", on_delete=models.PROTECT,
        related_name="academic_period_audit_actions",
    )
    # The selected role context the actor used, when role-context enforcement was in effect.
    acting_role_id = models.PositiveIntegerField(null=True, blank=True)
    action = models.CharField(max_length=60)
    school_year_id = models.PositiveIntegerField()
    semester_id = models.PositiveIntegerField(null=True, blank=True)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    reason = models.CharField(max_length=40)
    # WF11-D05/D06: the School Admin's explanation for an Active edit or historical correction.
    reason_note = models.CharField(max_length=500, null=True, blank=True)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)

    class Meta:
        db_table = "academic_period_audit_logs"
        indexes = [models.Index(fields=["school_year_id", "academic_period_audit_log_id"],
                                name="academic_audit_year_idx")]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Academic-period audit entries are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Academic-period audit entries are append-only.")


# ---- Academic configuration foundation (restricted local development, 25 Nov 2026) ------------
# Course -> CurriculumVersion -> (year level, term) -> CurriculumSubject (planned requirement)
# School Year -> Semester -> SubjectOffering (actual offering for a section) -> TeachingAssignment
# Definitions are never hard-deleted once referenced: they are retired. Foreign keys are PROTECT.
# These are CTU-G Workspace configuration records; they are not CTU enrollment records.

MIN_YEAR_LEVEL, MAX_YEAR_LEVEL = 1, 6
MAX_UNITS = 30


class DefinitionStatus(models.TextChoices):
    ACTIVE = "Active", "Active"
    INACTIVE = "Inactive", "Inactive"
    RETIRED = "Retired", "Retired"


class CurriculumStatus(models.TextChoices):
    DRAFT = "Draft", "Draft"
    PUBLISHED = "Published", "Published"
    SUPERSEDED = "Superseded", "Superseded"


class AssignmentStatus(models.TextChoices):
    ACTIVE = "Active", "Active"
    ENDED = "Ended", "Ended"


def _status_field():
    return MySQLEnumField(max_length=8, choices=DefinitionStatus.choices, default=DefinitionStatus.ACTIVE,
                          db_default=DefinitionStatus.ACTIVE)


class Course(models.Model):
    """academic.courses.manage: an approved course/program definition (normalized unique code)."""

    course_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    status = _status_field()
    version = models.PositiveIntegerField(default=1, db_default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="created_by", on_delete=models.PROTECT,
                                   related_name="academic_courses_created", editable=False)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    updated_at = MySQLTimestampField(db_default=CurrentTimestamp())

    class Meta:
        db_table = "academic_courses"


class Subject(models.Model):
    """clearance.subjects.manage: a reusable subject with optional lecture/lab units (admin-entered)."""

    subject_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    classification = models.CharField(max_length=60, null=True, blank=True)
    lecture_units = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    lab_units = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    status = _status_field()
    version = models.PositiveIntegerField(default=1, db_default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="created_by", on_delete=models.PROTECT,
                                   related_name="academic_subjects_created", editable=False)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    updated_at = MySQLTimestampField(db_default=CurrentTimestamp())

    class Meta:
        db_table = "academic_subjects"
        constraints = [
            models.CheckConstraint(
                condition=(Q(lecture_units__isnull=True) | Q(lecture_units__gte=0, lecture_units__lte=MAX_UNITS))
                & (Q(lab_units__isnull=True) | Q(lab_units__gte=0, lab_units__lte=MAX_UNITS)),
                name="academic_subjects_units_range"),
        ]


class Section(models.Model):
    """academic.sections.manage: a course/year-level section definition."""

    section_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, db_column="course_id", on_delete=models.PROTECT, related_name="sections")
    year_level = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=20)
    status = _status_field()
    version = models.PositiveIntegerField(default=1, db_default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="created_by", on_delete=models.PROTECT,
                                   related_name="academic_sections_created", editable=False)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    updated_at = MySQLTimestampField(db_default=CurrentTimestamp())

    class Meta:
        db_table = "academic_sections"
        constraints = [
            models.UniqueConstraint(fields=["course", "year_level", "name"], name="academic_sections_unique"),
            models.CheckConstraint(condition=Q(year_level__gte=MIN_YEAR_LEVEL, year_level__lte=MAX_YEAR_LEVEL),
                                   name="academic_sections_year_level_range"),
        ]


class CurriculumVersion(models.Model):
    """A versioned curriculum of one course. Draft is editable; Published and Superseded are immutable."""

    curriculum_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, db_column="course_id", on_delete=models.PROTECT, related_name="curricula")
    label = models.CharField(max_length=40)
    effective_start_year = models.PositiveSmallIntegerField(null=True, blank=True)
    status = MySQLEnumField(max_length=10, choices=CurriculumStatus.choices, default=CurriculumStatus.DRAFT,
                            db_default=CurriculumStatus.DRAFT)
    version = models.PositiveIntegerField(default=1, db_default=1)
    published_at = MySQLTimestampField(null=True, blank=True, editable=False)
    superseded_at = MySQLTimestampField(null=True, blank=True, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="created_by", on_delete=models.PROTECT,
                                   related_name="academic_curricula_created", editable=False)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    updated_at = MySQLTimestampField(db_default=CurrentTimestamp())

    class Meta:
        db_table = "academic_curriculum_versions"
        constraints = [
            models.UniqueConstraint(fields=["course", "label"], name="academic_curricula_course_label_unique"),
            models.CheckConstraint(
                condition=Q(effective_start_year__isnull=True)
                | Q(effective_start_year__gte=MIN_START_YEAR, effective_start_year__lte=MAX_START_YEAR),
                name="academic_curricula_start_year_range"),
            models.CheckConstraint(
                condition=(Q(status=CurriculumStatus.DRAFT, published_at__isnull=True, superseded_at__isnull=True)
                           | Q(status=CurriculumStatus.PUBLISHED, published_at__isnull=False, superseded_at__isnull=True)
                           | Q(status=CurriculumStatus.SUPERSEDED, published_at__isnull=False,
                               superseded_at__isnull=False)),
                name="academic_curricula_lifecycle_consistent"),
        ]


class CurriculumSubject(models.Model):
    """A planned requirement: this subject, in this curriculum, for this year level and term."""

    curriculum_subject_id = models.AutoField(primary_key=True)
    curriculum = models.ForeignKey(CurriculumVersion, db_column="curriculum_id", on_delete=models.PROTECT,
                                   related_name="entries")
    subject = models.ForeignKey(Subject, db_column="subject_id", on_delete=models.PROTECT,
                                related_name="curriculum_entries")
    year_level = models.PositiveSmallIntegerField()
    term = models.PositiveSmallIntegerField(choices=SemesterTerm.choices)

    class Meta:
        db_table = "academic_curriculum_subjects"
        constraints = [
            models.UniqueConstraint(fields=["curriculum", "subject"], name="academic_curriculum_subject_unique"),
            models.CheckConstraint(condition=Q(year_level__gte=MIN_YEAR_LEVEL, year_level__lte=MAX_YEAR_LEVEL),
                                   name="academic_curriculum_year_level_range"),
            models.CheckConstraint(condition=Q(term__in=[1, 2]), name="academic_curriculum_term_valid"),
        ]
        indexes = [models.Index(fields=["curriculum", "year_level", "term"], name="academic_curriculum_plan_idx")]


class SubjectOffering(models.Model):
    """An actual offering of a curriculum subject to one section in one semester (not the plan itself)."""

    offering_id = models.AutoField(primary_key=True)
    semester = models.ForeignKey(Semester, db_column="semester_id", on_delete=models.PROTECT, related_name="offerings")
    section = models.ForeignKey(Section, db_column="section_id", on_delete=models.PROTECT, related_name="offerings")
    curriculum_subject = models.ForeignKey(CurriculumSubject, db_column="curriculum_subject_id",
                                           on_delete=models.PROTECT, related_name="offerings")
    # Denormalized from curriculum_subject so the natural key is enforced by the database.
    subject = models.ForeignKey(Subject, db_column="subject_id", on_delete=models.PROTECT, related_name="offerings")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="created_by", on_delete=models.PROTECT,
                                   related_name="academic_offerings_created", editable=False)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)

    class Meta:
        db_table = "academic_subject_offerings"
        constraints = [
            models.UniqueConstraint(fields=["semester", "section", "subject"], name="academic_offerings_natural_key"),
        ]


class TeachingAssignment(models.Model):
    """clearance.teaching_assignments.manage: one instructor for one offering, with full history.

    Distinct from section adviser appointments (academic.advisers.manage), which are not modelled
    here. ``active_slot`` is 1 only while Active (UNIQUE with the offering): at most one current
    instructor per offering on MySQL. Ended rows are kept; nothing is ever overwritten.
    """

    assignment_id = models.AutoField(primary_key=True)
    offering = models.ForeignKey(SubjectOffering, db_column="offering_id", on_delete=models.PROTECT,
                                 related_name="teaching_assignments")
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="instructor_account_id",
                                   on_delete=models.PROTECT, related_name="teaching_assignments")
    status = MySQLEnumField(max_length=6, choices=AssignmentStatus.choices, default=AssignmentStatus.ACTIVE,
                            db_default=AssignmentStatus.ACTIVE)
    active_slot = models.PositiveSmallIntegerField(null=True, blank=True, editable=False)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="assigned_by", on_delete=models.PROTECT,
                                    related_name="teaching_assignments_made", editable=False)
    assigned_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    ended_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="ended_by", on_delete=models.PROTECT,
                                 related_name="teaching_assignments_ended", null=True, blank=True, editable=False)
    ended_at = MySQLTimestampField(null=True, blank=True, editable=False)
    end_reason = models.CharField(max_length=40, null=True, blank=True)

    class Meta:
        db_table = "academic_teaching_assignments"
        constraints = [
            models.UniqueConstraint(fields=["offering", "active_slot"], name="academic_teaching_one_active"),
            models.CheckConstraint(
                condition=(Q(status=AssignmentStatus.ACTIVE, active_slot__isnull=False, active_slot=1,
                             ended_at__isnull=True)
                           | Q(status=AssignmentStatus.ENDED, active_slot__isnull=True, ended_at__isnull=False,
                               ended_by__isnull=False)),
                name="academic_teaching_lifecycle_consistent"),
        ]


class AcademicConfigurationAuditLog(models.Model):
    """Append-only, attributable history of academic-configuration changes (plain entity IDs)."""

    academic_configuration_audit_log_id = models.AutoField(primary_key=True)
    actor_account = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="actor_account_id",
                                      on_delete=models.PROTECT, related_name="academic_configuration_audit_actions")
    acting_role_id = models.PositiveIntegerField(null=True, blank=True)
    action = models.CharField(max_length=60)
    entity_type = models.CharField(max_length=30)
    entity_id = models.PositiveIntegerField()
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    reason = models.CharField(max_length=40)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)

    class Meta:
        db_table = "academic_configuration_audit_logs"
        indexes = [models.Index(fields=["entity_type", "entity_id", "academic_configuration_audit_log_id"],
                                name="academic_config_audit_idx")]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Academic-configuration audit entries are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Academic-configuration audit entries are append-only.")


# ---- Student Semester Onboarding (WF-05.05) and official verification (WF-05.04 minimum) -------
# CTU's official enrollment system stays authoritative: EnrollmentEvidence records WHAT was verified
# (a controlled reference only, never a document), WHO verified it and WHEN. Participation exists only
# after the atomic finalization in apps.academic.onboarding (or the evidenced WF11-D14 correction).


class StudentType(models.TextChoices):
    REGULAR = "Regular", "Regular"
    IRREGULAR = "Irregular", "Irregular"


class EntryClassification(models.TextChoices):
    """WF-07.08 scenario recorded from official CTU records (no other student categories)."""

    CONTINUING = "continuing", "Continuing"
    RETURNING = "returning", "Returning"
    NEWCOMER = "newcomer", "Newcomer"
    TRANSFEREE = "transferee", "Transferee"


class EvidenceSource(models.TextChoices):
    IN_PERSON = "in_person", "In-person School Admin verification"     # R-02 lane 2
    CTU_INTEGRATION = "ctu_integration", "Approved CTU integration"     # R-02 lane 1: no runtime writer exists


class VerificationStatus(models.TextChoices):
    VERIFIED = "Verified", "Verified"
    REVOKED = "Revoked", "Revoked"


class EnrollmentEvidence(models.Model):
    evidence_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="student_account_id", on_delete=models.PROTECT,
                                related_name="enrollment_evidence")
    semester = models.ForeignKey(Semester, db_column="semester_id", on_delete=models.PROTECT, related_name="enrollment_evidence")
    source_type = MySQLEnumField(max_length=15, choices=EvidenceSource.choices)
    source_reference = models.CharField(max_length=80)  # controlled document/control number only
    source_as_of = models.DateField(null=True, blank=True)
    entry_classification = MySQLEnumField(max_length=10, choices=EntryClassification.choices)
    course = models.ForeignKey(Course, db_column="course_id", on_delete=models.PROTECT, related_name="enrollment_evidence")
    year_level = models.PositiveSmallIntegerField()
    status = MySQLEnumField(max_length=8, choices=VerificationStatus.choices, default=VerificationStatus.VERIFIED,
                            db_default=VerificationStatus.VERIFIED)
    active_slot = models.PositiveSmallIntegerField(null=True, blank=True, editable=False)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="verified_by", on_delete=models.PROTECT,
                                    related_name="enrollment_evidence_verified", null=True, blank=True)
    verified_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    revoked_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="revoked_by", on_delete=models.PROTECT,
                                   related_name="enrollment_evidence_revoked", null=True, blank=True)
    revoked_at = MySQLTimestampField(null=True, blank=True, editable=False)
    revoke_reason = models.CharField(max_length=40, null=True, blank=True)
    version = models.PositiveIntegerField(default=1, db_default=1)

    class Meta:
        db_table = "academic_enrollment_evidence"
        constraints = [
            models.UniqueConstraint(fields=["student", "semester", "active_slot"], name="academic_evidence_one_verified"),
            models.CheckConstraint(condition=Q(year_level__gte=MIN_YEAR_LEVEL, year_level__lte=MAX_YEAR_LEVEL),
                                   name="academic_evidence_year_level_range"),
            models.CheckConstraint(
                condition=(Q(status=VerificationStatus.VERIFIED, active_slot__isnull=False, active_slot=1,
                             revoked_at__isnull=True)
                           | Q(status=VerificationStatus.REVOKED, active_slot__isnull=True, revoked_at__isnull=False)),
                name="academic_evidence_lifecycle_consistent"),
            # In-person evidence is always attributable to the verifying School Admin.
            models.CheckConstraint(condition=~Q(source_type=EvidenceSource.IN_PERSON) | Q(verified_by__isnull=False),
                                   name="academic_evidence_in_person_attributed"),
        ]


class EnrollmentEvidenceSubject(models.Model):
    evidence = models.ForeignKey(EnrollmentEvidence, db_column="evidence_id", on_delete=models.PROTECT, related_name="subjects")
    subject = models.ForeignKey(Subject, db_column="subject_id", on_delete=models.PROTECT, related_name="+")

    class Meta:
        db_table = "academic_enrollment_evidence_subjects"
        constraints = [models.UniqueConstraint(fields=["evidence", "subject"], name="academic_evidence_subject_unique")]


class EnrollmentGapException(models.Model):
    """School Admin-verified, CTU-evidenced NON-enrollment of a Student in one past semester (WF11-D15/16).
    Lets a returning Student onboard despite an older Uncleared clearance; never clears or waives anything."""

    gap_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="student_account_id", on_delete=models.PROTECT,
                                related_name="enrollment_gaps")
    semester = models.ForeignKey(Semester, db_column="semester_id", on_delete=models.PROTECT, related_name="enrollment_gaps")
    source_reference = models.CharField(max_length=80)
    status = MySQLEnumField(max_length=8, choices=VerificationStatus.choices, default=VerificationStatus.VERIFIED,
                            db_default=VerificationStatus.VERIFIED)
    active_slot = models.PositiveSmallIntegerField(null=True, blank=True, editable=False)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="verified_by", on_delete=models.PROTECT,
                                    related_name="enrollment_gaps_verified")
    verified_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    revoked_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="revoked_by", on_delete=models.PROTECT,
                                   related_name="enrollment_gaps_revoked", null=True, blank=True)
    revoked_at = MySQLTimestampField(null=True, blank=True, editable=False)
    version = models.PositiveIntegerField(default=1, db_default=1)

    class Meta:
        db_table = "academic_enrollment_gap_exceptions"
        constraints = [
            models.UniqueConstraint(fields=["student", "semester", "active_slot"], name="academic_gap_one_verified"),
            models.CheckConstraint(
                condition=(Q(status=VerificationStatus.VERIFIED, active_slot__isnull=False, active_slot=1,
                             revoked_at__isnull=True)
                           | Q(status=VerificationStatus.REVOKED, active_slot__isnull=True, revoked_at__isnull=False)),
                name="academic_gap_lifecycle_consistent"),
        ]


class OnboardingStatus(models.TextChoices):
    DRAFT = "Draft", "Draft"
    PENDING_VERIFICATION = "PendingVerification", "Pending verification"
    COMPLETED = "Completed", "Completed"


class SemesterOnboarding(models.Model):
    """The Student's recoverable Draft for one semester. A Draft is never participation."""

    onboarding_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="student_account_id", on_delete=models.PROTECT,
                                related_name="semester_onboardings")
    semester = models.ForeignKey(Semester, db_column="semester_id", on_delete=models.PROTECT, related_name="onboardings")
    status = MySQLEnumField(max_length=19, choices=OnboardingStatus.choices, default=OnboardingStatus.DRAFT,
                            db_default=OnboardingStatus.DRAFT)
    student_type = MySQLEnumField(max_length=9, choices=StudentType.choices, null=True, blank=True)
    course = models.ForeignKey(Course, db_column="course_id", on_delete=models.PROTECT, null=True, blank=True,
                               related_name="onboardings")
    year_level = models.PositiveSmallIntegerField(null=True, blank=True)
    subjects_confirmed = models.BooleanField(default=False, db_default=False)
    course_confirmed = models.BooleanField(default=False, db_default=False)
    version = models.PositiveIntegerField(default=1, db_default=1)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    updated_at = MySQLTimestampField(db_default=CurrentTimestamp())
    completed_at = MySQLTimestampField(null=True, blank=True, editable=False)

    class Meta:
        db_table = "academic_semester_onboardings"
        constraints = [
            models.UniqueConstraint(fields=["student", "semester"], name="academic_onboarding_unique"),
            models.CheckConstraint(condition=Q(year_level__isnull=True)
                                   | Q(year_level__gte=MIN_YEAR_LEVEL, year_level__lte=MAX_YEAR_LEVEL),
                                   name="academic_onboarding_year_level_range"),
            models.CheckConstraint(
                condition=~Q(status=OnboardingStatus.COMPLETED)
                | Q(completed_at__isnull=False, student_type__isnull=False, course__isnull=False, year_level__isnull=False,
                    subjects_confirmed=True, course_confirmed=True),
                name="academic_onboarding_completed_consistent"),
        ]


class SemesterOnboardingSubject(models.Model):
    onboarding = models.ForeignKey(SemesterOnboarding, db_column="onboarding_id", on_delete=models.PROTECT, related_name="subjects")
    offering = models.ForeignKey(SubjectOffering, db_column="offering_id", on_delete=models.PROTECT, related_name="+")
    subject = models.ForeignKey(Subject, db_column="subject_id", on_delete=models.PROTECT, related_name="+")

    class Meta:
        db_table = "academic_semester_onboarding_subjects"
        constraints = [models.UniqueConstraint(fields=["onboarding", "subject"], name="academic_onboarding_subject_unique")]


class ParticipationSource(models.TextChoices):
    ONBOARDING = "onboarding", "Student Semester Onboarding"
    HISTORICAL_CORRECTION = "historical_correction", "Evidenced historical correction"


class SemesterParticipation(models.Model):
    participation_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="student_account_id", on_delete=models.PROTECT,
                                related_name="semester_participations")
    semester = models.ForeignKey(Semester, db_column="semester_id", on_delete=models.PROTECT, related_name="participations")
    onboarding = models.OneToOneField(SemesterOnboarding, db_column="onboarding_id", on_delete=models.PROTECT, null=True,
                                      blank=True, related_name="participation")
    evidence = models.ForeignKey(EnrollmentEvidence, db_column="evidence_id", on_delete=models.PROTECT, related_name="participations")
    source = MySQLEnumField(max_length=21, choices=ParticipationSource.choices)
    student_type = MySQLEnumField(max_length=9, choices=StudentType.choices)
    course = models.ForeignKey(Course, db_column="course_id", on_delete=models.PROTECT, related_name="participations")
    year_level = models.PositiveSmallIntegerField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="created_by", on_delete=models.PROTECT,
                                   related_name="participations_created")
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)

    class Meta:
        db_table = "academic_semester_participations"
        constraints = [
            models.UniqueConstraint(fields=["student", "semester"], name="academic_participation_unique"),
            models.CheckConstraint(condition=Q(year_level__gte=MIN_YEAR_LEVEL, year_level__lte=MAX_YEAR_LEVEL),
                                   name="academic_participation_year_level_range"),
            models.CheckConstraint(condition=~Q(source=ParticipationSource.ONBOARDING) | Q(onboarding__isnull=False),
                                   name="academic_participation_onboarding_link"),
        ]


class ParticipationSubject(models.Model):
    participation = models.ForeignKey(SemesterParticipation, db_column="participation_id", on_delete=models.PROTECT,
                                      related_name="subjects")
    subject = models.ForeignKey(Subject, db_column="subject_id", on_delete=models.PROTECT, related_name="+")
    offering = models.ForeignKey(SubjectOffering, db_column="offering_id", on_delete=models.PROTECT, related_name="+")
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="instructor_account_id", on_delete=models.PROTECT,
                                   related_name="+")

    class Meta:
        db_table = "academic_participation_subjects"
        constraints = [models.UniqueConstraint(fields=["participation", "subject"], name="academic_participation_subject_unique")]
