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
