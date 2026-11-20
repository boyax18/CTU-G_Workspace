"""AR-6C7D.9 P3A: READ-ONLY activation-readiness inspection.

No activation path, apply switch, writing ORM calls, migrations, URL edits,
settings changes or user operations exist in this command. It inspects the
already-committed P1/P2 metadata and 8 audit receipts on the guarded local
MySQL target. A passing inspection is NOT approval to activate permissions.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction

from apps.access_control.management.commands import (
    init_registration_review_metadata_local_dev as p1,
    init_registration_review_inactive_bindings_local_dev as p2,
)
from apps.access_control.models import (
    AccountPermission, AccountRole, AccessAuditLog, Role, RolePermission, Service,
)
from apps.access_control.services import get_effective_permissions


class ActivationReadinessRefused(RuntimeError):
    """The database does not match the precisely staged P1/P2 boundary."""


def inspect_readiness(*, actor_account_id):
    """Verify P1/P2 and current disabled gates; acquire only short-lived read locks.

    No write operations are possible in this function. The existing protected
    P1/P2 validators issue SELECT FOR UPDATE, so they run inside one atomic
    read-only-in-effect transaction (no new or updated rows).
    """
    if type(actor_account_id) is not int or not 1 <= actor_account_id <= 2_147_483_647:
        raise ActivationReadinessRefused("A numeric existing Admin audit actor is required.")

    # Guard DB identity, local host, configured settings, URL and flags, and
    # frozen catalogue. These methods do NOT execute P1/P2 writes.
    p1._expected()
    if settings.SETTINGS_MODULE == "config.settings":
        confirmation = p2.DEV_CONFIRM
    elif settings.SETTINGS_MODULE == "config.test_settings":
        confirmation = p2.TEST_CONFIRM
    else:
        raise ActivationReadinessRefused("Only reviewed local or disposable-test settings are supported.")
    p2._target(confirmation)

    with transaction.atomic(using=DEFAULT_DB_ALIAS):
        admin = Role.objects.select_for_update().get(role_name="Admin", is_active=True)
        actor = p1._actor(actor_account_id)
        if not AccountRole.objects.select_for_update().filter(
            account_id=actor.pk, role_id=admin.pk
        ).exists():
            raise ActivationReadinessRefused("The audit actor has no active Admin assignment.")
        if AccountPermission.objects.select_for_update().exists():
            raise ActivationReadinessRefused("Unexpected account-level overrides exist.")

        permissions = p2._prior_metadata(actor)
        staged = list(RolePermission.objects.select_for_update().order_by("role_permission_id"))
        p2._verify_rows(staged, admin, actor, permissions)

        # This service has NO effective privileges at P2: both services and
        # three staged bindings are intentionally inactive.
        if Service.objects.filter(is_active=True).exists():
            raise ActivationReadinessRefused("Unexpected active service.")
        if RolePermission.objects.filter(is_active=True).exists():
            raise ActivationReadinessRefused("Unexpected active binding.")
        if get_effective_permissions(actor):
            raise ActivationReadinessRefused("Unexpected effective permission detected.")

        # An Admin role grant would apply to ALL eligible Admin assignees, not
        # only the audit actor. Print the scope so an operator can assess it.
        eligible_admin_count = (
            AccountRole.objects.filter(
                role_id=admin.pk, role__is_active=True,
                account__is_active=True, account__request_status="Approved",
                account__is_staff=False, account__is_superuser=False,
            ).values("account_id").distinct().count()
        )
        if eligible_admin_count < 1:
            raise ActivationReadinessRefused("No eligible application Admin is present.")
        p1_count = AccessAuditLog.objects.filter(
            action__in=(p1.SERVICE_EVENT, p1.PERMISSION_EVENT)
        ).count()
        p2_count = AccessAuditLog.objects.filter(action=p2.EVENT).count()
        if p1_count != 5 or p2_count != 3:
            raise ActivationReadinessRefused("Operational receipt counts differ.")

    return {
        "actor_account_id": actor_account_id,
        "eligible_admin_count": eligible_admin_count,
        "inactive_services": 2,
        "permission_definitions": 3,
        "inactive_admin_bindings": 3,
        "p1_receipts": p1_count,
        "p2_receipts": p2_count,
    }


class Command(BaseCommand):
    help = "READ ONLY: verify P1/P2 and report unresolved Phase-3 activation blockers."

    def add_arguments(self, parser):
        parser.add_argument("--actor-account-id", type=int, required=True)

    def handle(self, *args, **options):
        try:
            result = inspect_readiness(actor_account_id=options["actor_account_id"])
        except Exception as exc:
            # Keep database details and personal account identifiers out of
            # error output. Fail closed on ANY unexpected inspection error.
            raise CommandError(
                "AR-6C7D.9 P3A: REFUSED; database or feature gates did not match the staged P1/P2 contract."
            ) from exc

        self.stdout.write("AR-6C7D.9 P3A: DATABASE INSPECTION PASSED (READ ONLY)")
        self.stdout.write(f"Audit actor account ID: {result['actor_account_id']}")
        self.stdout.write(f"Eligible application Admin accounts affected by future grants: {result['eligible_admin_count']}")
        self.stdout.write("Services: 2 inactive; permission definitions: 3")
        self.stdout.write("Admin bindings: 3 inactive; account overrides: 0")
        self.stdout.write("Operational audit receipts: P1=5; P2=3")
        self.stdout.write("Effective permissions for audit actor: 0")
        self.stdout.write("Registration Review backend flags: disabled; route: not mounted")
        self.stdout.write("ACTIVATION: BLOCKED (NO WRITES EXECUTED)")
        self.stdout.write("Manual gates remain: verified database restore, approved impact scope,")
        self.stdout.write("separate activation/compensation design, and authenticated API security tests.")
