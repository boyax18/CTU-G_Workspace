"""AR-6C5B.3 review-only schema: one durable registration notification outbox.

The table has no live writers, workers, admin registrations, or routes in this patch.
Import this module at the bottom of apps.accounts.models to register the model.
"""

from django.db import models

from .fields import CurrentTimestamp, MySQLEnumField, MySQLTimestampField
from .outbox_fields import (
    MySQLDateTimeSecondsField,
    MySQLFixedBinaryField,
    MySQLVarBinaryField,
)


class RegistrationNotificationOutbox(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Leased", "Leased"),
        ("Retry", "Retry"),
        ("Delivered", "Delivered"),
        ("Dead", "Dead"),
    ]
    TEMPLATE_CHOICES = [
        ("registration.approved", "Registration approved"),
        ("registration.rejected", "Registration rejected"),
    ]

    outbox_id = models.BigAutoField(primary_key=True)
    decision_audit_log = models.OneToOneField(
        "access_control.AccessAuditLog",
        db_column="decision_audit_log_id",
        on_delete=models.PROTECT,
        related_name="registration_notification_outbox",
    )
    template_code = models.CharField(max_length=64, choices=TEMPLATE_CHOICES)
    template_version = models.IntegerField(default=1, db_default=1)

    # Per-decision authenticated recipient envelope. No plaintext email column.
    encrypted_recipient = MySQLVarBinaryField(max_length=1024, null=True, blank=True)
    recipient_nonce = MySQLFixedBinaryField(max_length=12, null=True, blank=True)
    wrapped_data_key = MySQLVarBinaryField(max_length=512, null=True, blank=True)
    encryption_key_version = models.CharField(max_length=64, null=True, blank=True)
    recipient_erased_at = MySQLDateTimeSecondsField(null=True, blank=True)

    delivery_status = MySQLEnumField(
        max_length=9,
        choices=STATUS_CHOICES,
        default="Pending",
        db_default="Pending",
    )
    attempt_count = models.IntegerField(default=0, db_default=0)
    next_attempt_at = MySQLDateTimeSecondsField(null=True, blank=True)
    lease_expires_at = MySQLDateTimeSecondsField(null=True, blank=True)
    lease_token = models.CharField(max_length=64, null=True, blank=True)
    last_failure_code = models.CharField(max_length=64, null=True, blank=True)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    updated_at = MySQLDateTimeSecondsField(null=True, blank=True)
    delivered_at = MySQLDateTimeSecondsField(null=True, blank=True)

    class Meta:
        db_table = "registration_notification_outbox"
        indexes = [
            models.Index(fields=["delivery_status", "next_attempt_at"], name="outbox_due_idx"),
            models.Index(fields=["delivery_status", "lease_expires_at"], name="outbox_lease_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(attempt_count__gte=0),
                name="outbox_nonnegative_attempts",
            ),
            models.CheckConstraint(
                condition=models.Q(template_version__gte=1),
                name="outbox_positive_template_version",
            ),
        ]

    def __str__(self):
        # Do not expose recipient or personalized email details.
        return f"Registration notification outbox #{self.pk}"
