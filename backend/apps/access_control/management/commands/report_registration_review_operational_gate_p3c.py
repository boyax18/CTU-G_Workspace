"""AR-6C7D.9 P3C: read-only operational activation-scope inspection.

This command cannot enable grants, services, routes, flags, or accounts. It
requires the immutable P1/P2 state and rejects any unanticipated Admin scope.
A passing report is not authorization to execute operational activation.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction
from django.urls import NoReverseMatch, reverse

from apps.access_control.management.commands import (
    exercise_registration_review_activation_recovery_test_only as p3b,
    report_registration_review_activation_readiness as p3a,
)
from apps.access_control.models import (
    AccountPermission, AccessAuditLog, Role, RolePermission, Service,
)


class OperationalGateRefused(RuntimeError):
    """Fail closed if the exact review-activation starting state differs."""


def inspect_operational_gate(*, actor_account_id, expected_admin_account_ids):
    if type(actor_account_id) is not int or not 1 <= actor_account_id <= 2_147_483_647:
        raise OperationalGateRefused("An existing numeric audit actor is required.")

    # The exact ID set is supplied by the operator, not guessed from a count.
    approved_scope = p3b._expected_ids(expected_admin_account_ids)
    if actor_account_id not in approved_scope:
        raise OperationalGateRefused("The audit actor must be in the expected Admin set.")

    # All P1/P2 verification, local MySQL identity, unmounted URLs, disabled
    # flags, catalogue and audit checks are inherited from the read-only P3A.
    base = p3a.inspect_readiness(actor_account_id=actor_account_id)

    with transaction.atomic(using=DEFAULT_DB_ALIAS):
        admin = Role.objects.select_for_update().get(role_name="Admin", is_active=True)
        actual_scope = p3b._eligible_admin_ids(admin)
        if actual_scope != approved_scope:
            raise OperationalGateRefused("Unexpected eligible Admin account assignment(s).")
        if len(actual_scope) != base["eligible_admin_count"]:
            raise OperationalGateRefused("Admin account count disagrees with the P3A inspection.")

        if (AccountPermission.objects.select_for_update().exists()
                or Service.objects.select_for_update().filter(is_active=True).exists()
                or RolePermission.objects.select_for_update().filter(is_active=True).exists()):
            raise OperationalGateRefused("One or more permission surfaces are already active.")
        if AccessAuditLog.objects.select_for_update().filter(
            action__in=p3b.TRANSITION_EVENTS
        ).exists():
            raise OperationalGateRefused("Transition receipts exist; investigate before planning activation.")

        if (getattr(settings, "WORKSPACE_REGISTRATION_REVIEW_API_ENABLED", False)
                or getattr(settings, "WORKSPACE_REGISTRATION_APPROVAL_ENABLED", False)):
            raise OperationalGateRefused("The Registration Review feature is already enabled.")
        try:
            reverse("registration-review-pending")
        except NoReverseMatch:
            pass
        else:
            raise OperationalGateRefused("Registration Review route is already mounted.")

    return {
        "actor_account_id": actor_account_id,
        "eligible_admin_count": len(approved_scope),
        "scope_ids": tuple(sorted(approved_scope)),
        "phase_one_audits": base["p1_receipts"],
        "phase_two_audits": base["p2_receipts"],
    }


class Command(BaseCommand):
    help = "READ ONLY: inspect exact Admin impact scope and leave activation BLOCKED."

    def add_arguments(self, parser):
        parser.add_argument("--actor-account-id", type=int, required=True)
        parser.add_argument("--expected-admin-account-ids", required=True)

    def handle(self, *args, **options):
        try:
            result = inspect_operational_gate(
                actor_account_id=options["actor_account_id"],
                expected_admin_account_ids=options["expected_admin_account_ids"],
            )
        except Exception as exc:
            raise CommandError(
                "AR-6C7D.9 P3C: REFUSED; exact Admin scope, catalogue, audits, "
                "or disabled feature gates differ. NO WRITES EXECUTED."
            ) from exc
        self.stdout.write("AR-6C7D.9 P3C: OPERATIONAL SCOPE VERIFIED (READ ONLY)")
        self.stdout.write(f"Audit actor account ID: {result['actor_account_id']}")
        self.stdout.write(f"Exact eligible Admin account IDs: {','.join(map(str, result['scope_ids']))}")
        self.stdout.write(f"Eligible Admin count: {result['eligible_admin_count']}")
        self.stdout.write("Services: 2 inactive; Admin bindings: 3 inactive; account overrides: 0")
        self.stdout.write(
            f"P1/P2 audit receipts: {result['phase_one_audits']} + {result['phase_two_audits']}; "
            "P3 transition receipts: 0"
        )
        self.stdout.write("Registration Review flags: disabled; routes: unmounted")
        self.stdout.write("ACTIVATION: BLOCKED (NO WRITES EXECUTED)")
        self.stdout.write("Backup/restore, API test evidence, and operational compensation approval are NOT inferred.")
