"""AR-6C5B.3 review-only migration draft; DO NOT APPLY to development MySQL yet.

Hand-authored against the 2026-11-08 model snapshot. Compare with the real
project's migration autodetector and inspect `sqlmigrate` before applying.
"""

import apps.accounts.fields
import apps.accounts.outbox_fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_account_is_staff_account_is_superuser"),
        ("access_control", "0003_remaining_access_control"),
    ]

    operations = [
        migrations.CreateModel(
            name="RegistrationNotificationOutbox",
            fields=[
                ("outbox_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("decision_audit_log", models.OneToOneField(
                    db_column="decision_audit_log_id",
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="registration_notification_outbox",
                    to="access_control.accessauditlog",
                )),
                ("template_code", models.CharField(
                    choices=[
                        ("registration.approved", "Registration approved"),
                        ("registration.rejected", "Registration rejected"),
                    ],
                    max_length=64,
                )),
                ("template_version", models.IntegerField(db_default=1, default=1)),
                ("encrypted_recipient", apps.accounts.outbox_fields.MySQLVarBinaryField(
                    blank=True, max_length=1024, null=True,
                )),
                ("recipient_nonce", apps.accounts.outbox_fields.MySQLFixedBinaryField(
                    blank=True, max_length=12, null=True,
                )),
                ("wrapped_data_key", apps.accounts.outbox_fields.MySQLVarBinaryField(
                    blank=True, max_length=512, null=True,
                )),
                ("encryption_key_version", models.CharField(blank=True, max_length=64, null=True)),
                ("recipient_erased_at", apps.accounts.outbox_fields.MySQLDateTimeSecondsField(
                    blank=True, null=True,
                )),
                ("delivery_status", apps.accounts.fields.MySQLEnumField(
                    choices=[
                        ("Pending", "Pending"), ("Leased", "Leased"),
                        ("Retry", "Retry"), ("Delivered", "Delivered"),
                        ("Dead", "Dead"),
                    ],
                    max_length=9,
                    db_default="Pending",
                    default="Pending",
                )),
                ("attempt_count", models.IntegerField(db_default=0, default=0)),
                ("next_attempt_at", apps.accounts.outbox_fields.MySQLDateTimeSecondsField(
                    blank=True, null=True,
                )),
                ("lease_expires_at", apps.accounts.outbox_fields.MySQLDateTimeSecondsField(
                    blank=True, null=True,
                )),
                ("lease_token", models.CharField(blank=True, max_length=64, null=True)),
                ("last_failure_code", models.CharField(blank=True, max_length=64, null=True)),
                ("created_at", apps.accounts.fields.MySQLTimestampField(
                    db_default=apps.accounts.fields.CurrentTimestamp(), editable=False,
                )),
                ("updated_at", apps.accounts.outbox_fields.MySQLDateTimeSecondsField(
                    blank=True, null=True,
                )),
                ("delivered_at", apps.accounts.outbox_fields.MySQLDateTimeSecondsField(
                    blank=True, null=True,
                )),
            ],
            options={
                "db_table": "registration_notification_outbox",
                "indexes": [
                    models.Index(
                        fields=["delivery_status", "next_attempt_at"],
                        name="outbox_due_idx",
                    ),
                    models.Index(
                        fields=["delivery_status", "lease_expires_at"],
                        name="outbox_lease_idx",
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(attempt_count__gte=0),
                        name="outbox_nonnegative_attempts",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(template_version__gte=1),
                        name="outbox_positive_template_version",
                    ),
                ],
            },
        ),
    ]
