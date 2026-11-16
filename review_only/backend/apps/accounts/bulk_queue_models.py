"""AR-6C5D REVIEW ONLY: do not install/import until migration signoff.

This is not imported in apps.accounts.models and does not create database tables.
Owner-approved ERD amendment is separate from approval to run migrations or activate jobs.
"""
from django.db import models

from .fields import CurrentTimestamp, MySQLEnumField, MySQLTimestampField
from .outbox_fields import MySQLDateTimeSecondsField, MySQLFixedBinaryField


class RegistrationBulkJob(models.Model):
    ACTIONS = [('Approve', 'Approve'), ('Reject', 'Reject')]
    MODES = [('Explicit', 'Explicit'), ('AllMatching', 'AllMatching')]
    STATUSES = [(x, x) for x in ('Queued', 'Running', 'Completed', 'Partial', 'Stopped', 'Cancelled')]

    bulk_job_id = models.BigAutoField(primary_key=True)
    requested_by_account = models.ForeignKey(
        'accounts.Account', db_column='requested_by_account_id',
        on_delete=models.PROTECT, related_name='registration_bulk_jobs',
    )
    idempotency_key_hash = MySQLFixedBinaryField(max_length=32)
    request_fingerprint = MySQLFixedBinaryField(max_length=32)
    selection_digest = MySQLFixedBinaryField(max_length=32)
    action = MySQLEnumField(max_length=7, choices=ACTIONS)
    rejection_code = models.CharField(max_length=64, null=True, blank=True)
    selection_mode = MySQLEnumField(max_length=11, choices=MODES)
    selection_count = models.IntegerField()
    status = MySQLEnumField(max_length=9, choices=STATUSES, default='Queued', db_default='Queued')
    succeeded_count = models.IntegerField(default=0, db_default=0)
    skipped_count = models.IntegerField(default=0, db_default=0)
    failed_count = models.IntegerField(default=0, db_default=0)
    cancelled_count = models.IntegerField(default=0, db_default=0)
    stop_reason_code = models.CharField(max_length=64, null=True, blank=True)
    cancel_requested_at = MySQLDateTimeSecondsField(null=True, blank=True)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    started_at = MySQLDateTimeSecondsField(null=True, blank=True)
    finished_at = MySQLDateTimeSecondsField(null=True, blank=True)
    updated_at = MySQLDateTimeSecondsField(null=True, blank=True)

    class Meta:
        db_table = 'registration_bulk_jobs'
        indexes = [models.Index(fields=['status', 'created_at'], name='bulk_job_status_idx')]
        constraints = [
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
                condition=(
                    models.Q(action='Approve', rejection_code__isnull=True) |
                    models.Q(action='Reject', rejection_code__isnull=False)
                ),
                name='bulk_rejection_code_guard',
            ),
            models.CheckConstraint(
                condition=models.Q(selection_count__gte=(
                    models.F('succeeded_count') + models.F('skipped_count') +
                    models.F('failed_count') + models.F('cancelled_count')
                )),
                name='bulk_count_bound',
            ),
        ]

    def __str__(self):
        return f'Registration bulk job #{self.pk}'


class RegistrationBulkJobItem(models.Model):
    STATUSES = [(x, x) for x in (
        'Pending', 'Leased', 'Approved', 'Rejected', 'Skipped', 'Failed', 'Cancelled',
    )]

    bulk_job_item_id = models.BigAutoField(primary_key=True)
    bulk_job = models.ForeignKey(
        'accounts.RegistrationBulkJob', db_column='bulk_job_id',
        on_delete=models.PROTECT, related_name='items',
    )
    target_account = models.ForeignKey(
        'accounts.Account', db_column='target_account_id',
        on_delete=models.PROTECT, related_name='registration_bulk_job_items',
    )
    status = MySQLEnumField(max_length=9, choices=STATUSES, default='Pending', db_default='Pending')
    attempt_count = models.IntegerField(default=0, db_default=0)
    next_attempt_at = MySQLDateTimeSecondsField(null=True, blank=True)
    lease_token = models.CharField(max_length=64, null=True, blank=True)
    lease_expires_at = MySQLDateTimeSecondsField(null=True, blank=True)
    decision_audit_log = models.OneToOneField(
        'access_control.AccessAuditLog', db_column='decision_audit_log_id',
        on_delete=models.PROTECT, null=True, blank=True,
        related_name='registration_bulk_job_item',
    )
    last_failure_code = models.CharField(max_length=64, null=True, blank=True)
    processed_at = MySQLDateTimeSecondsField(null=True, blank=True)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)
    updated_at = MySQLDateTimeSecondsField(null=True, blank=True)

    class Meta:
        db_table = 'registration_bulk_job_items'
        indexes = [
            models.Index(fields=['status', 'next_attempt_at'], name='bulk_item_due_idx'),
            models.Index(fields=['status', 'lease_expires_at'], name='bulk_item_lease_idx'),
            models.Index(fields=['bulk_job', 'status'], name='bulk_item_job_status_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['bulk_job', 'target_account'], name='bulk_job_target_uk',
            ),
            models.CheckConstraint(
                condition=models.Q(attempt_count__gte=0), name='bulk_item_nonneg_attempts',
            ),
        ]

    def __str__(self):
        return f'Registration bulk job item #{self.pk}'
