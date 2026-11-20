from django.conf import settings
from django.db import models

from apps.accounts.fields import CurrentTimestamp, MySQLEnumField, MySQLTimestampField


class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_default=True)

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.role_name


class AccountRole(models.Model):
    """An assigned role; requested roles and assignment authorization are separate."""

    account_role_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="account_id",
        on_delete=models.PROTECT,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        Role,
        db_column="role_id",
        on_delete=models.PROTECT,
        related_name="account_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="assigned_by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="role_assignments_made",
        editable=False,
    )
    assigned_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)

    class Meta:
        db_table = "account_roles"
        constraints = [
            models.UniqueConstraint(
                fields=["account", "role"], name="account_roles_account_role_unique"
            ),
        ]

    def __str__(self):
        return f"Account {self.account_id}: role {self.role_id}"


class Service(models.Model):
    service_id = models.AutoField(primary_key=True)
    service_name = models.CharField(max_length=100, unique=True)
    service_code = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_default=True)

    class Meta:
        db_table = "services"

    def __str__(self):
        return self.service_name


class Permission(models.Model):
    permission_id = models.AutoField(primary_key=True)
    service = models.ForeignKey(
        Service,
        db_column="service_id",
        on_delete=models.PROTECT,
        related_name="permissions",
    )
    permission_code = models.CharField(max_length=150, unique=True)
    permission_name = models.CharField(max_length=100)
    module_name = models.CharField(max_length=100)
    action_name = models.CharField(max_length=50)
    description = models.CharField(max_length=255, null=True, blank=True)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)

    class Meta:
        db_table = "permissions"

    def __str__(self):
        return self.permission_code


class RolePermission(models.Model):
    """A stored role grant; authorization evaluation is implemented separately."""

    role_permission_id = models.AutoField(primary_key=True)
    role = models.ForeignKey(
        Role,
        db_column="role_id",
        on_delete=models.PROTECT,
        related_name="permission_grants",
    )
    permission = models.ForeignKey(
        Permission,
        db_column="permission_id",
        on_delete=models.PROTECT,
        related_name="role_grants",
    )
    is_active = models.BooleanField(default=True, db_default=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="granted_by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="role_permission_grants_made",
        editable=False,
    )
    granted_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)

    class Meta:
        db_table = "role_permissions"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="role_permissions_role_permission_unique",
            ),
        ]


class AccountPermission(models.Model):
    """An explicit account override; recording a row does not evaluate access."""

    EFFECT_CHOICES = [("Grant", "Grant"), ("Deny", "Deny")]

    account_permission_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="account_id",
        on_delete=models.PROTECT,
        related_name="permission_overrides",
    )
    permission = models.ForeignKey(
        Permission,
        db_column="permission_id",
        on_delete=models.PROTECT,
        related_name="account_overrides",
    )
    effect = MySQLEnumField(max_length=5, choices=EFFECT_CHOICES)
    is_active = models.BooleanField(default=True, db_default=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="assigned_by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="permission_overrides_made",
        editable=False,
    )
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    updated_at = MySQLTimestampField(null=True, blank=True)

    class Meta:
        db_table = "account_permissions"
        constraints = [
            models.UniqueConstraint(
                fields=["account", "permission"],
                name="account_permissions_account_permission_unique",
            ),
        ]


class AccessAuditLog(models.Model):
    access_audit_log_id = models.AutoField(primary_key=True)
    actor_account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="actor_account_id",
        on_delete=models.PROTECT,
        related_name="access_audit_actions",
    )
    target_account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="target_account_id",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="access_audit_entries",
    )
    role = models.ForeignKey(
        Role,
        db_column="role_id",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="access_audit_entries",
    )
    permission = models.ForeignKey(
        Permission,
        db_column="permission_id",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="access_audit_entries",
    )
    action = models.CharField(max_length=50)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    reason = models.CharField(max_length=255, null=True, blank=True)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)

    class Meta:
        db_table = "access_audit_logs"


class OrdinaryAppointment(models.Model):
    """Reviewable evidence of an external campus appointment, NOT a role grant.

    Status is controlled only through the gated appointment_registry service.
    The document digest is an integrity reference, never proof on its own.
    """

    STATUS_CHOICES = [
        ("Submitted", "Submitted"),
        ("Verified", "Verified"),
        ("Rejected", "Rejected"),
        ("Revoked", "Revoked"),
    ]
    ROLE_CHOICES = [("Treasurer", "Treasurer"), ("SSG Advisor", "SSG Advisor")]

    appointment_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL, db_column="account_id", on_delete=models.PROTECT,
        related_name="ordinary_appointments",
    )
    role_name = models.CharField(max_length=50, choices=ROLE_CHOICES)
    document_sha256 = models.CharField(max_length=64)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Submitted")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, db_column="submitted_by", on_delete=models.PROTECT,
        related_name="ordinary_appointments_submitted", editable=False,
    )
    submitted_at = models.DateTimeField(auto_now_add=True, editable=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, db_column="reviewed_by", on_delete=models.PROTECT,
        null=True, blank=True, related_name="ordinary_appointments_reviewed", editable=False,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, editable=False)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, db_column="revoked_by", on_delete=models.PROTECT,
        null=True, blank=True, related_name="ordinary_appointments_revoked", editable=False,
    )
    revoked_at = models.DateTimeField(null=True, blank=True, editable=False)
    # Traceability lives on the appointment row, not in the protected audit.py
    # snapshot contract (D-84). Each FK refers to an append-only audit receipt.
    submission_receipt = models.ForeignKey(
        "access_control.AccessAuditLog", db_column="submission_receipt_id",
        on_delete=models.PROTECT, null=True, blank=True, editable=False,
        related_name="submitted_appointment_evidence",
    )
    review_receipt = models.ForeignKey(
        "access_control.AccessAuditLog", db_column="review_receipt_id",
        on_delete=models.PROTECT, null=True, blank=True, editable=False,
        related_name="reviewed_appointment_evidence",
    )
    revocation_receipt = models.ForeignKey(
        "access_control.AccessAuditLog", db_column="revocation_receipt_id",
        on_delete=models.PROTECT, null=True, blank=True, editable=False,
        related_name="revoked_appointment_evidence",
    )

    class Meta:
        db_table = "ordinary_appointments"
        constraints = [
            models.UniqueConstraint(fields=["account", "role_name", "document_sha256"],
                                    name="ordinary_appt_document_unique"),
        ]
        indexes = [
            models.Index(fields=["account", "role_name", "status"], name="ordinary_appt_lookup"),
            models.Index(fields=["status", "valid_until"], name="ordinary_appt_expiry"),
        ]
