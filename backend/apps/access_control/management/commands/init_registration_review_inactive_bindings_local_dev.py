"""AR-6C7D.8: guarded LOCAL-DEVELOPMENT P2 inactive Admin role bindings.

Requires a completed, audited AR-6C7D.7 P1. Never activates any service,
role grant, override, URL or API feature flag. No general permission management.
The frozen catalogue contract remains blocked for release/deployment.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections, transaction

from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role,
    RolePermission, Service,
)
from apps.access_control.management.commands import (
    init_registration_review_metadata_local_dev as p1,
)

EVENT = "workspace.review.role_binding.stage"
LOCK_NAME = p1.LOCK_NAME  # Serialize with the P1 initializer for the same catalogue.
DEV_CONFIRM = "ctug_workspace:AR-6C7D8:P2:INACTIVE-BINDINGS-ONLY"
TEST_CONFIRM = "AR-6C7D8:DISPOSABLE-TEST:P2"


class InactiveBindingRefused(RuntimeError):
    """Phase 2 is unsafe or does not match the exact authorized local scope."""


def _target(confirmation):
    """Reuse P1's strict target, URL and backend-gate checks without P1 writes."""
    module = settings.SETTINGS_MODULE
    if module == "config.test_settings":
        expected = TEST_CONFIRM
        phase_one_confirmation = p1.TEST_CONFIRM
    elif module == "config.settings":
        expected = DEV_CONFIRM
        phase_one_confirmation = p1.DEV_CONFIRM
    else:
        raise InactiveBindingRefused("Only the isolated test or local development configuration is allowed.")
    if confirmation != expected:
        raise InactiveBindingRefused("Exact Phase-2 confirmation required.")
    # P1 validates connection alias, MySQL, local host, selected DB, transaction
    # isolation, settings, both disabled flags, and the unmounted review URL.
    try:
        return p1._target(phase_one_confirmation)
    except Exception as exc:
        raise InactiveBindingRefused("The local Phase-2 database target is not safe.") from exc


def _prior_metadata(actor):
    """Lock and check exactly the already-initialized P1 catalogue and audits."""
    service_defs, permission_defs = p1._expected()
    services_list = list(Service.objects.select_for_update().order_by("service_id"))
    permissions_list = list(Permission.objects.select_for_update().order_by("permission_id"))
    services = {row.service_code: row for row in services_list}
    permissions = {row.permission_code: row for row in permissions_list}
    if (len(services_list) != 2 or len(permissions_list) != 3
            or set(services) != set(p1.SERVICE_CODES)
            or set(permissions) != set(p1.PERMISSION_CODES)):
        raise InactiveBindingRefused("P1 metadata is absent, partial, or includes foreign rows.")
    for code in p1.SERVICE_CODES:
        if not p1._matches_service(services[code], service_defs[code]):
            raise InactiveBindingRefused("P1 service data or inactive state has changed.")
    for code in p1.PERMISSION_CODES:
        expected = permission_defs[code]
        if not p1._matches_permission(permissions[code], expected, services[expected["service_code"]]):
            raise InactiveBindingRefused("P1 permission definition has changed.")
    try:
        p1._verify_prior_audits(services, permissions, actor)
    except Exception as exc:
        raise InactiveBindingRefused("P1 operational audit history is missing or differs.") from exc
    return permissions


def _verify_p2_audits(rows, admin, actor):
    """Require one exact append-only receipt per inactive binding."""
    logs = list(AccessAuditLog.objects.select_for_update()
                .filter(action=EVENT).order_by("access_audit_log_id"))
    if len(logs) != len(p1.PERMISSION_CODES):
        raise InactiveBindingRefused("Three P2 operational audit receipts are required.")
    by_permission_id = {row.permission_id: row for row in rows}
    seen = set()
    for audit in logs:
        grant = by_permission_id.get(audit.permission_id)
        if (grant is None or audit.permission_id in seen
                or audit.actor_account_id != actor.pk
                or audit.target_account_id is not None
                or audit.role_id != admin.pk
                or audit.reason != "permission_change"
                or audit.old_value is not None
                or audit.new_value != {
                    "role_id": admin.pk,
                    "permission_id": grant.permission_id,
                    "role_permission_id": grant.pk,
                    "is_active": False,
                }):
            raise InactiveBindingRefused("P2 audit attribution or payload does not match staged bindings.")
        seen.add(audit.permission_id)
    if seen != set(by_permission_id):
        raise InactiveBindingRefused("P2 audit coverage is incomplete.")


def _verify_rows(rows, admin, actor, permissions):
    expected_permission_ids = {permissions[code].pk for code in p1.PERMISSION_CODES}
    if (len(rows) != 3
            or {row.permission_id for row in rows} != expected_permission_ids
            or any(row.role_id != admin.pk
                   or row.is_active is not False
                   or row.granted_by_id != actor.pk
                   for row in rows)):
        raise InactiveBindingRefused("Unexpected, active, or unattributed role bindings found.")
    _verify_p2_audits(rows, admin, actor)


def _apply_phase_two(*, actor_account_id, confirmation):
    """Create exactly 3 inactive bindings and 3 receipts in one durable transaction.

    An exact second run only verifies state. Partial rows/audits are not repaired.
    """
    # Catalogue pinning is checked outside and within the transaction.
    p1._expected()
    db = _target(confirmation)
    with db.cursor() as cursor:
        cursor.execute("SELECT GET_LOCK(%s, 0)", [LOCK_NAME])
        if cursor.fetchone()[0] != 1:
            raise InactiveBindingRefused("Another registration metadata operation is running.")
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            # Lock the same Admin role and actor as P1, then services and
            # permissions in their established ordering.
            try:
                admin = Role.objects.select_for_update().get(role_name="Admin", is_active=True)
            except (Role.DoesNotExist, Role.MultipleObjectsReturned) as exc:
                raise InactiveBindingRefused("Exactly one active Admin role is required.") from exc
            try:
                actor = p1._actor(actor_account_id)
            except Exception as exc:
                raise InactiveBindingRefused("A persisted approved application Admin is required.") from exc
            if not AccountRole.objects.select_for_update().filter(
                account_id=actor.pk, role_id=admin.pk,
            ).exists():
                raise InactiveBindingRefused("The audit actor has no approved Admin assignment.")
            if AccountPermission.objects.select_for_update().exists():
                raise InactiveBindingRefused("Account-level overrides are outside P2 scope.")
            permissions = _prior_metadata(actor)
            rows = list(RolePermission.objects.select_for_update().order_by("role_permission_id"))
            if not rows:
                if AccessAuditLog.objects.filter(action=EVENT).exists():
                    raise InactiveBindingRefused("Orphaned P2 audit receipts require manual review.")
                for code in p1.PERMISSION_CODES:
                    permission = permissions[code]
                    binding = RolePermission.objects.create(
                        role=admin, permission=permission,
                        is_active=False, granted_by=actor,
                    )
                    record_access_audit_receipt(
                        actor=actor, role=admin, permission=permission,
                        action=EVENT, old_value=None,
                        new_value={
                            "role_id": admin.pk,
                            "permission_id": permission.pk,
                            "role_permission_id": binding.pk,
                            "is_active": False,
                        },
                        reason="permission_change",
                    )
                rows = list(RolePermission.objects.select_for_update().order_by("role_permission_id"))
                result = "CREATED"
            else:
                result = "ALREADY_COMPLETE"
            _verify_rows(rows, admin, actor, permissions)
            if (Service.objects.filter(is_active=True).exists()
                    or RolePermission.objects.filter(is_active=True).exists()
                    or AccountPermission.objects.exists()):
                raise InactiveBindingRefused("P2 must not grant effective access or activate services.")
            # Refuse completion if frozen catalogue or review state changed.
            p1._expected()
        return result
    finally:
        with db.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", [LOCK_NAME])


class Command(BaseCommand):
    help = "LOCAL DEV ONLY: stage exactly three inactive Admin Registration Review bindings."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--actor-account-id", type=int)
        parser.add_argument("--confirm-local-dev-phase2", type=str)

    def handle(self, *args, **options):
        if not options["apply"]:
            raise CommandError("No implicit writes. Run and inspect the read-only P1 report first.")
        try:
            result = _apply_phase_two(
                actor_account_id=options["actor_account_id"],
                confirmation=options["confirm_local_dev_phase2"],
            )
        except Exception as exc:
            raise CommandError("Phase-2 inactive binding initialization refused or rolled back; no success reported.") from exc
        self.stdout.write(
            f"AR-6C7D8 P2: {result}; inactive_admin_bindings=3; "
            "active_grants=0; service_activation=NO; api_activation=NO"
        )
