"""Minimum WF-06 clearance records created by successful Student Semester Onboarding (WF-06.01/06.02).

One ``SemesterClearance`` per Student semester participation (UNIQUE), starting Uncleared. Its
``ClearanceRequirement`` rows are the mandatory signatory REQUIREMENTS derived from WF-06.02 step 4:
one per confirmed enrolled subject (its real assigned Instructor), one Treasurer organizational-fee
sign-off and one School Admin final approval. A requirement is not a signature: nothing here signs,
approves or clears; "Cleared" means every requirement signed plus final approval, which only a future
WF-06 signing workflow may record. Not registered in Django Admin.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.accounts.fields import CurrentTimestamp, MySQLEnumField, MySQLTimestampField


class ClearanceStatus(models.TextChoices):
    UNCLEARED = "Uncleared", "Uncleared"
    CLEARED = "Cleared", "Cleared"


class RequirementKind(models.TextChoices):
    SUBJECT_INSTRUCTOR = "subject_instructor", "Subject instructor"
    TREASURER_FEE = "treasurer_fee", "Treasurer organizational-fee sign-off"
    SCHOOL_ADMIN_FINAL = "school_admin_final", "School Admin final approval"


class RequirementStatus(models.TextChoices):
    PENDING = "Pending", "Pending"
    SIGNED = "Signed", "Signed"


class SemesterClearance(models.Model):
    clearance_id = models.AutoField(primary_key=True)
    participation = models.OneToOneField("academic.SemesterParticipation", db_column="participation_id",
                                         on_delete=models.PROTECT, related_name="clearance")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="student_account_id", on_delete=models.PROTECT,
                                related_name="semester_clearances")
    semester = models.ForeignKey("academic.Semester", db_column="semester_id", on_delete=models.PROTECT,
                                 related_name="clearances")
    status = MySQLEnumField(max_length=9, choices=ClearanceStatus.choices, default=ClearanceStatus.UNCLEARED,
                            db_default=ClearanceStatus.UNCLEARED)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    cleared_at = MySQLTimestampField(null=True, blank=True, editable=False)

    class Meta:
        db_table = "clearance_semester_clearances"
        constraints = [
            models.UniqueConstraint(fields=["student", "semester"], name="clearance_one_per_student_semester"),
            models.CheckConstraint(
                condition=(Q(status=ClearanceStatus.UNCLEARED, cleared_at__isnull=True)
                           | Q(status=ClearanceStatus.CLEARED, cleared_at__isnull=False)),
                name="clearance_status_consistent"),
        ]


class ClearanceRequirement(models.Model):
    requirement_id = models.AutoField(primary_key=True)
    clearance = models.ForeignKey(SemesterClearance, db_column="clearance_id", on_delete=models.PROTECT,
                                  related_name="requirements")
    # "subject:<subject_id>", "treasurer_fee" or "school_admin_final": a NOT NULL natural key (MySQL
    # treats NULLs as distinct, so (clearance, kind, subject) alone would not prevent duplicates).
    requirement_key = models.CharField(max_length=40)
    kind = MySQLEnumField(max_length=18, choices=RequirementKind.choices)
    subject = models.ForeignKey("academic.Subject", db_column="subject_id", on_delete=models.PROTECT, null=True,
                                blank=True, related_name="+")
    offering = models.ForeignKey("academic.SubjectOffering", db_column="offering_id", on_delete=models.PROTECT,
                                 null=True, blank=True, related_name="+")
    signatory = models.ForeignKey(settings.AUTH_USER_MODEL, db_column="signatory_account_id", on_delete=models.PROTECT,
                                  null=True, blank=True, related_name="clearance_requirements")
    status = MySQLEnumField(max_length=7, choices=RequirementStatus.choices, default=RequirementStatus.PENDING,
                            db_default=RequirementStatus.PENDING)
    signed_at = MySQLTimestampField(null=True, blank=True, editable=False)

    class Meta:
        db_table = "clearance_requirements"
        constraints = [
            models.UniqueConstraint(fields=["clearance", "requirement_key"], name="clearance_requirement_unique"),
            models.CheckConstraint(
                condition=(Q(kind=RequirementKind.SUBJECT_INSTRUCTOR, subject__isnull=False, offering__isnull=False,
                             signatory__isnull=False)
                           | (~Q(kind=RequirementKind.SUBJECT_INSTRUCTOR) & Q(subject__isnull=True, offering__isnull=True,
                                                                              signatory__isnull=True))),
                name="clearance_requirement_shape"),
            models.CheckConstraint(
                condition=(Q(status=RequirementStatus.PENDING, signed_at__isnull=True)
                           | Q(status=RequirementStatus.SIGNED, signed_at__isnull=False)),
                name="clearance_requirement_status_consistent"),
        ]
