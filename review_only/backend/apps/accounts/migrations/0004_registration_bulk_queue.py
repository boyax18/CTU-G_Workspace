"""AR-6C5D REVIEW DRAFT ONLY. Never copy into live migrations or run migrate yet.

Hand-authored from approved v2 schema; compare against the actual migration graph
and output of Django makemigrations/sqlmigrate before any later approval to apply.
"""

import apps.accounts.fields
import apps.accounts.outbox_fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_registration_notification_outbox'),
        ('access_control', '0003_remaining_access_control'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegistrationBulkJob',
            fields=[
                ('bulk_job_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('requested_by_account', models.ForeignKey(
                    db_column='requested_by_account_id', on_delete=django.db.models.deletion.PROTECT,
                    related_name='registration_bulk_jobs', to='accounts.account')),
                ('idempotency_key_hash', apps.accounts.outbox_fields.MySQLFixedBinaryField(max_length=32)),
                ('request_fingerprint', apps.accounts.outbox_fields.MySQLFixedBinaryField(max_length=32)),
                ('selection_digest', apps.accounts.outbox_fields.MySQLFixedBinaryField(max_length=32)),
                ('action', apps.accounts.fields.MySQLEnumField(
                    max_length=7, choices=[('Approve', 'Approve'), ('Reject', 'Reject')])),
                ('rejection_code', models.CharField(max_length=64, null=True, blank=True)),
                ('selection_mode', apps.accounts.fields.MySQLEnumField(
                    max_length=11, choices=[('Explicit', 'Explicit'), ('AllMatching', 'AllMatching')])),
                ('selection_count', models.IntegerField()),
                ('status', apps.accounts.fields.MySQLEnumField(
                    max_length=9, choices=[(x, x) for x in (
                        'Queued', 'Running', 'Completed', 'Partial', 'Stopped', 'Cancelled',
                    )], default='Queued', db_default='Queued')),
                ('succeeded_count', models.IntegerField(default=0, db_default=0)),
                ('skipped_count', models.IntegerField(default=0, db_default=0)),
                ('failed_count', models.IntegerField(default=0, db_default=0)),
                ('cancelled_count', models.IntegerField(default=0, db_default=0)),
                ('stop_reason_code', models.CharField(max_length=64, null=True, blank=True)),
                ('cancel_requested_at', apps.accounts.outbox_fields.MySQLDateTimeSecondsField(null=True, blank=True)),
                ('created_at', apps.accounts.fields.MySQLTimestampField(
                    db_default=apps.accounts.fields.CurrentTimestamp(), editable=False)),
                ('started_at', apps.accounts.outbox_fields.MySQLDateTimeSecondsField(null=True, blank=True)),
                ('finished_at', apps.accounts.outbox_fields.MySQLDateTimeSecondsField(null=True, blank=True)),
                ('updated_at', apps.accounts.outbox_fields.MySQLDateTimeSecondsField(null=True, blank=True)),
            ],
            options={
                'db_table': 'registration_bulk_jobs',
                'indexes': [
                    models.Index(fields=['status', 'created_at'], name='bulk_job_status_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        fields=['requested_by_account', 'idempotency_key_hash'],
                        name='bulk_actor_idempotency_uk',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(selection_count__gte=1), name='bulk_positive_selection',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(succeeded_count__gte=0, skipped_count__gte=0,
                                           failed_count__gte=0, cancelled_count__gte=0),
                        name='bulk_nonnegative_counts',
                    ),
                    models.CheckConstraint(
                        condition=(models.Q(action='Approve', rejection_code__isnull=True) |
                                   models.Q(action='Reject', rejection_code__isnull=False)),
                        name='bulk_rejection_code_guard',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(selection_count__gte=(
                            models.F('succeeded_count') + models.F('skipped_count') +
                            models.F('failed_count') + models.F('cancelled_count')
                        )),
                        name='bulk_count_bound',
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name='RegistrationBulkJobItem',
            fields=[
                ('bulk_job_item_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('bulk_job', models.ForeignKey(
                    db_column='bulk_job_id', on_delete=django.db.models.deletion.PROTECT,
                    related_name='items', to='accounts.registrationbulkjob')),
                ('target_account', models.ForeignKey(
                    db_column='target_account_id', on_delete=django.db.models.deletion.PROTECT,
                    related_name='registration_bulk_job_items', to='accounts.account')),
                ('status', apps.accounts.fields.MySQLEnumField(
                    max_length=9, choices=[(x, x) for x in (
                        'Pending', 'Leased', 'Approved', 'Rejected', 'Skipped', 'Failed', 'Cancelled',
                    )], default='Pending', db_default='Pending')),
                ('attempt_count', models.IntegerField(default=0, db_default=0)),
                ('next_attempt_at', apps.accounts.outbox_fields.MySQLDateTimeSecondsField(null=True, blank=True)),
                ('lease_token', models.CharField(max_length=64, null=True, blank=True)),
                ('lease_expires_at', apps.accounts.outbox_fields.MySQLDateTimeSecondsField(null=True, blank=True)),
                ('decision_audit_log', models.OneToOneField(
                    db_column='decision_audit_log_id', on_delete=django.db.models.deletion.PROTECT,
                    null=True, blank=True, related_name='registration_bulk_job_item',
                    to='access_control.accessauditlog')),
                ('last_failure_code', models.CharField(max_length=64, null=True, blank=True)),
                ('processed_at', apps.accounts.outbox_fields.MySQLDateTimeSecondsField(null=True, blank=True)),
                ('created_at', apps.accounts.fields.MySQLTimestampField(
                    db_default=apps.accounts.fields.CurrentTimestamp(), editable=False)),
                ('updated_at', apps.accounts.outbox_fields.MySQLDateTimeSecondsField(null=True, blank=True)),
            ],
            options={
                'db_table': 'registration_bulk_job_items',
                'indexes': [
                    models.Index(fields=['status', 'next_attempt_at'], name='bulk_item_due_idx'),
                    models.Index(fields=['status', 'lease_expires_at'], name='bulk_item_lease_idx'),
                    models.Index(fields=['bulk_job', 'status'], name='bulk_item_job_status_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=['bulk_job', 'target_account'], name='bulk_job_target_uk'),
                    models.CheckConstraint(
                        condition=models.Q(attempt_count__gte=0), name='bulk_item_nonneg_attempts'),
                ],
            },
        ),
    ]
