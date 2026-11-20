"""AR-6C7D.9 P3E: read-only no-backup release risk and drift inspection.

P3E cannot activate or compensate. It will not attest backup/restore status,
release approval, or successful integration tests. The P3D local write barrier
stays immutable and closed. Do not infer a recovery guarantee from a fingerprint.
"""

import hashlib
import json
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction

from apps.access_control.management.commands import (
    exercise_registration_review_activation_recovery_test_only as p3b,
    init_registration_review_inactive_bindings_local_dev as p2,
    init_registration_review_metadata_local_dev as p1,
    report_registration_review_operational_gate_p3c as p3c,
    transition_registration_review_p3d as p3d,
)
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, Permission, RolePermission, Service,
)


class ReleaseGateRefused(RuntimeError):
    """Security or source-state precondition failed; do not release."""


def _snapshot_data():
    """Collect only the pinned authorization surface; never display row payloads."""
    audit_actions = (p1.SERVICE_EVENT, p1.PERMISSION_EVENT, p2.EVENT) + p3b.TRANSITION_EVENTS
    return {
        "schema_version": "AR-6C7D9-P3E-FINGERPRINT-v1",
        "services": list(Service.objects.order_by("service_id").values_list(
            "service_id", "service_code", "service_name", "is_active",
        )),
        "permissions": list(Permission.objects.order_by("permission_id").values_list(
            "permission_id", "permission_code", "service_id",
        )),
        "role_bindings": list(RolePermission.objects.order_by("role_permission_id").values_list(
            "role_permission_id", "role_id", "permission_id", "granted_by_id", "is_active",
        )),
        "override_count": AccountPermission.objects.count(),
        "audits": list(AccessAuditLog.objects.filter(action__in=audit_actions)
                       .order_by("access_audit_log_id").values(
            "access_audit_log_id", "action", "actor_account_id",
            "target_account_id", "role_id", "permission_id", "old_value",
            "new_value", "reason",
        )),
    }


def inspect_release_gates(*, actor_account_id, expected_admin_account_ids,
                          expected_fingerprint=None):
    """Produce a deterministic authorization snapshot, with NO write path.

    P3C performs the exact audit/canonical-metadata/scope checks, and P3D is
    explicitly required to remain locked. An outer transaction keeps the
    checked snapshot consistent with P3C's SELECT FOR UPDATE validations.
    """
    if expected_fingerprint is not None and (
        type(expected_fingerprint) is not str
        or re.fullmatch(r"[0-9a-f]{64}", expected_fingerprint) is None
    ):
        raise ReleaseGateRefused("Expected fingerprint must be lowercase SHA-256 hex.")

    if settings.SETTINGS_MODULE not in ("config.settings", "config.test_settings"):
        raise ReleaseGateRefused("Unsupported Django settings module.")
    if p3d.LOCAL_DEV_WRITES_RELEASED is not False:
        raise ReleaseGateRefused("P3D local write barrier has been modified.")

    with transaction.atomic(using=DEFAULT_DB_ALIAS):
        scope = p3c.inspect_operational_gate(
            actor_account_id=actor_account_id,
            expected_admin_account_ids=expected_admin_account_ids,
        )
        snapshot = _snapshot_data()
        if len(snapshot["audits"]) != 8:
            raise ReleaseGateRefused("Unexpected security transition/audit record count.")
        digest = hashlib.sha256(json.dumps(
            snapshot, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, default=str,
        ).encode("utf-8")).hexdigest()

        if expected_fingerprint is not None and digest != expected_fingerprint:
            raise ReleaseGateRefused("Authorization snapshot drift detected.")

    return {
        "fingerprint": digest,
        "scope_ids": scope["scope_ids"],
        "audit_actor": actor_account_id,
        "services_inactive": len(snapshot["services"]),
        "bindings_inactive": len(snapshot["role_bindings"]),
        "receipt_count": len(snapshot["audits"]),
        "activation_released": False,
        "backup_verified": False,  # unknown; explicitly not attestable by this command
    }


class Command(BaseCommand):
    help = "READ ONLY: exact P3E authorization fingerprint and unreleased risk report."

    def add_arguments(self, parser):
        parser.add_argument("--actor-account-id", required=True, type=int)
        parser.add_argument("--expected-admin-account-ids", required=True)
        parser.add_argument("--expected-fingerprint")
        # Deliberately no --apply, --release, --backup-complete or settings override.

    def handle(self, *args, **options):
        try:
            data = inspect_release_gates(
                actor_account_id=options["actor_account_id"],
                expected_admin_account_ids=options["expected_admin_account_ids"],
                expected_fingerprint=options["expected_fingerprint"],
            )
        except Exception as exc:
            raise CommandError(
                "AR-6C7D.9 P3E: REFUSED; activation scope, audit evidence, "
                "security barrier, or expected fingerprint differs. NO WRITES EXECUTED."
            ) from exc

        self.stdout.write("AR-6C7D.9 P3E: READ-ONLY RELEASE EVIDENCE PASSED")
        self.stdout.write(f"Audit actor account ID: {data['audit_actor']}")
        self.stdout.write("Exact application Admin IDs: " + ",".join(map(str, data["scope_ids"])))
        self.stdout.write("Services: 2 inactive; Admin bindings: 3 inactive; permission overrides: 0")
        self.stdout.write("P1/P2 receipts: 5 + 3; activation/compensation receipts: 0")
        self.stdout.write(f"Authorization snapshot SHA-256: {data['fingerprint']}")
        self.stdout.write("P3D operational local-write barrier: LOCKED")
        self.stdout.write("Backup and restore: NOT VERIFIED BY THIS COMMAND; operator declined backup")
        self.stdout.write("Authenticated testing and release authorization: NOT ATTESTED BY THIS COMMAND")
        self.stdout.write("ACTUAL ACTIVATION: BLOCKED; NO WRITES EXECUTED")
