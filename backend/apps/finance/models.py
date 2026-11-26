"""Semester organizational fee configuration (owner-authorized restricted local development, 25 Nov 2026).

* ``SemesterFeeSchedule`` - exactly one per academic semester (UNIQUE). It holds the explicit
  ``current_approved_revision`` reference: the single unambiguous approved rate for the semester.
* ``SemesterFeeRevision`` - numbered, immutable-once-decided revisions of the full semester fee in
  PHP (Decimal, 2 places). Draft -> Approved -> Superseded, or Draft -> Withdrawn. MySQL has no
  partial unique index, so ``approved_slot`` / ``draft_slot`` are 1 only in that state (UNIQUE with
  the schedule): at most one Approved and one open Draft per semester. CHECK constraints keep the
  lifecycle columns consistent and the amount within 0.00 .. MAX_FEE_AMOUNT.
* ``FinanceAuditLog`` - append-only attributable history (plain entity IDs).

No model here represents a Student fee obligation, payment, receipt or clearance: obligations are
created only by successful Student Semester Onboarding (WF-05.05 / WF-07.02), not by this module.
Not registered in Django Admin: the only write path is apps.finance.fees (HDAC-enforced).
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.accounts.fields import CurrentTimestamp, MySQLEnumField, MySQLTimestampField

CURRENCY = "PHP"
MAX_FEE_AMOUNT = Decimal("100000.00")  # sanity bound for one semester fee; not a policy amount


class RevisionStatus(models.TextChoices):
    DRAFT = "Draft", "Draft"
    APPROVED = "Approved", "Approved"
    SUPERSEDED = "Superseded", "Superseded"
    WITHDRAWN = "Withdrawn", "Withdrawn"


class SemesterFeeSchedule(models.Model):
    schedule_id = models.AutoField(primary_key=True)
    semester = models.OneToOneField("academic.Semester", db_column="semester_id", on_delete=models.PROTECT,
                                    related_name="fee_schedule")
    current_approved_revision = models.OneToOneField(
        "SemesterFeeRevision", db_column="current_approved_revision_id", on_delete=models.PROTECT, null=True,
        blank=True, related_name="+", editable=False)
    version = models.PositiveIntegerField(default=1, db_default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="created_by", on_delete=models.PROTECT,
                                   related_name="semester_fee_schedules_created", editable=False)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    updated_at = MySQLTimestampField(db_default=CurrentTimestamp())

    class Meta:
        db_table = "finance_semester_fee_schedules"


class SemesterFeeRevision(models.Model):
    revision_id = models.AutoField(primary_key=True)
    schedule = models.ForeignKey(SemesterFeeSchedule, db_column="schedule_id", on_delete=models.PROTECT,
                                 related_name="revisions")
    revision_number = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default=CURRENCY, db_default=CURRENCY)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    status = MySQLEnumField(max_length=10, choices=RevisionStatus.choices, default=RevisionStatus.DRAFT,
                            db_default=RevisionStatus.DRAFT)
    approved_slot = models.PositiveSmallIntegerField(null=True, blank=True, editable=False)
    draft_slot = models.PositiveSmallIntegerField(null=True, blank=True, editable=False)
    # Required (10..500 characters) for every revision after an approved rate exists.
    change_reason = models.CharField(max_length=500, null=True, blank=True)
    version = models.PositiveIntegerField(default=1, db_default=1)
    configured_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="configured_by", on_delete=models.PROTECT,
                                      related_name="semester_fee_revisions_configured", editable=False)
    configured_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    updated_at = MySQLTimestampField(db_default=CurrentTimestamp())
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="approved_by", on_delete=models.PROTECT,
                                    related_name="semester_fee_revisions_approved", null=True, blank=True,
                                    editable=False)
    approved_at = MySQLTimestampField(null=True, blank=True, editable=False)
    superseded_at = MySQLTimestampField(null=True, blank=True, editable=False)
    withdrawn_at = MySQLTimestampField(null=True, blank=True, editable=False)

    class Meta:
        db_table = "finance_semester_fee_revisions"
        constraints = [
            models.UniqueConstraint(fields=["schedule", "revision_number"], name="finance_fee_revision_number_unique"),
            models.UniqueConstraint(fields=["schedule", "approved_slot"], name="finance_fee_one_approved"),
            models.UniqueConstraint(fields=["schedule", "draft_slot"], name="finance_fee_one_open_draft"),
            models.CheckConstraint(condition=Q(currency=CURRENCY), name="finance_fee_currency_php"),
            models.CheckConstraint(condition=Q(amount__gte=0, amount__lte=MAX_FEE_AMOUNT), name="finance_fee_amount_range"),
            models.CheckConstraint(condition=Q(revision_number__gte=1), name="finance_fee_revision_number_positive"),
            # "IS NOT NULL" terms are explicit: a CHECK passes on NULL (see academic semesters).
            models.CheckConstraint(
                condition=(
                    Q(status=RevisionStatus.DRAFT, draft_slot__isnull=False, draft_slot=1, approved_slot__isnull=True,
                      approved_at__isnull=True, approved_by__isnull=True, superseded_at__isnull=True,
                      withdrawn_at__isnull=True)
                    | Q(status=RevisionStatus.APPROVED, approved_slot__isnull=False, approved_slot=1,
                        draft_slot__isnull=True, approved_at__isnull=False, approved_by__isnull=False,
                        superseded_at__isnull=True, withdrawn_at__isnull=True)
                    | Q(status=RevisionStatus.SUPERSEDED, approved_slot__isnull=True, draft_slot__isnull=True,
                        approved_at__isnull=False, approved_by__isnull=False, superseded_at__isnull=False,
                        withdrawn_at__isnull=True)
                    | Q(status=RevisionStatus.WITHDRAWN, approved_slot__isnull=True, draft_slot__isnull=True,
                        approved_at__isnull=True, approved_by__isnull=True, superseded_at__isnull=True,
                        withdrawn_at__isnull=False)
                ),
                name="finance_fee_revision_lifecycle_consistent"),
        ]


class FinanceAuditLog(models.Model):
    """Append-only, attributable history of finance configuration changes."""

    finance_audit_log_id = models.AutoField(primary_key=True)
    actor_account = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="actor_account_id",
                                      on_delete=models.PROTECT, related_name="finance_audit_actions")
    acting_role_id = models.PositiveIntegerField(null=True, blank=True)
    action = models.CharField(max_length=60)
    entity_type = models.CharField(max_length=30)
    entity_id = models.PositiveIntegerField()
    semester_id = models.PositiveIntegerField(null=True, blank=True)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    reason = models.CharField(max_length=40)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)

    class Meta:
        db_table = "finance_audit_logs"
        indexes = [models.Index(fields=["semester_id", "finance_audit_log_id"], name="finance_audit_semester_idx")]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Finance audit entries are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Finance audit entries are append-only.")


class ObligationStatus(models.TextChoices):
    UNPAID = "Unpaid", "Unpaid"  # payments, receipts and settlement belong to later WF-07 slices


class FeeObligation(models.Model):
    """WF-07.02: exactly one full organizational fee obligation per Student semester participation.

    Created only inside successful onboarding finalization (or the evidenced WF11-D14 correction).
    ``amount`` is a snapshot of the approved revision at creation; later fee revisions never change it.
    Nothing here records a payment, receipt or paid status.
    """

    obligation_id = models.AutoField(primary_key=True)
    participation = models.OneToOneField("academic.SemesterParticipation", db_column="participation_id",
                                         on_delete=models.PROTECT, related_name="fee_obligation")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="student_account_id", on_delete=models.PROTECT,
                                related_name="fee_obligations")
    semester = models.ForeignKey("academic.Semester", db_column="semester_id", on_delete=models.PROTECT,
                                 related_name="fee_obligations")
    fee_revision = models.ForeignKey(SemesterFeeRevision, db_column="fee_revision_id", on_delete=models.PROTECT,
                                     related_name="obligations")
    currency = models.CharField(max_length=3, default=CURRENCY, db_default=CURRENCY)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    status = MySQLEnumField(max_length=6, choices=ObligationStatus.choices, default=ObligationStatus.UNPAID,
                            db_default=ObligationStatus.UNPAID)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)

    class Meta:
        db_table = "finance_fee_obligations"
        constraints = [
            models.UniqueConstraint(fields=["student", "semester"], name="finance_obligation_one_per_student_semester"),
            models.CheckConstraint(condition=Q(currency=CURRENCY), name="finance_obligation_currency_php"),
            models.CheckConstraint(condition=Q(amount__gte=0, amount__lte=MAX_FEE_AMOUNT), name="finance_obligation_amount_range"),
        ]
