"""AR-6C7D.9 P3D: operational transition *candidate*, not a release.

Local ``config.settings`` supports read-only preview only. A hard-coded release
barrier rejects ALL local-development writes, independently of CLI arguments.
Activation and compensation are executable solely in disposable MySQL tests.

Do not remove the release barrier without a separate, reviewed delivery that
includes a verified database restore and authenticated rollout/rollback plan.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction

from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.management.commands import (
    exercise_registration_review_activation_recovery_test_only as p3b,
    init_registration_review_inactive_bindings_local_dev as p2,
    init_registration_review_metadata_local_dev as p1,
    report_registration_review_operational_gate_p3c as p3c,
)
from apps.access_control.models import AccessAuditLog

# SECURITY RELEASE BARRIER: no P3D writes to local development at this stage.
# This is deliberately not a settings variable or a CLI override.
LOCAL_DEV_WRITES_RELEASED = False
TEST_CONFIRM = "AR-6C7D9:P3D:DISPOSABLE-TEST-TRANSITION"


class TransitionRefused(RuntimeError):
    """Any inconsistent scope, safety gate, or transition stops the operation."""


def _write_target(confirmation):
    """Fail closed on operational DB; permit only pinned disposable test DB."""
    if settings.SETTINGS_MODULE == "config.settings":
        # Even a correct local DB, explicit --apply and backup assertion cannot
        # bypass this. Promoting requires a distinct reviewed code change.
        raise TransitionRefused("P3D local-development writes are NOT released.")
    if settings.SETTINGS_MODULE != "config.test_settings" or confirmation != TEST_CONFIRM:
        raise TransitionRefused("Only the disposable MySQL test target is writable.")
    try:
        return p2._target(p2.TEST_CONFIRM)
    except Exception as exc:
        raise TransitionRefused("Disposable test database does not match the pinned target.") from exc


def _check_compensation_preview(*, actor_account_id, expected_admin_account_ids):
    """Inspect an ACTIVE state without writing; for incident-runbook planning."""
    if settings.SETTINGS_MODULE == "config.settings":
        confirmation = p2.DEV_CONFIRM
    elif settings.SETTINGS_MODULE == "config.test_settings":
        confirmation = p2.TEST_CONFIRM
    else:
        raise TransitionRefused("Unsupported settings for preview.")
    p2._target(confirmation)
    scope = p3b._expected_ids(expected_admin_account_ids)
    if actor_account_id not in scope:
        raise TransitionRefused("Audit actor must be in the exact expected Admin set.")
    with transaction.atomic(using=DEFAULT_DB_ALIAS):
        actor, admin, services, permissions, bindings = p3b._snapshot(
            actor_id=actor_account_id, expected_ids=scope, active=True,
        )
        p3b._verify_receipts(
            event_service=p3b.SERVICE_ACTIVATE,
            event_binding=p3b.BINDING_ACTIVATE,
            actor=actor, admin=admin, services=services,
            permissions=permissions, bindings=bindings,
            before=False, after=True,
        )
        if AccessAuditLog.objects.filter(
            action__in=(p3b.SERVICE_DEACTIVATE, p3b.BINDING_DEACTIVATE)
        ).exists():
            raise TransitionRefused("Existing compensation receipts require manual review.")
        p3b._assert_effective_permissions(scope, active=True)
    return len(scope)


def _preview(*, mode, actor_account_id, expected_admin_account_ids):
    if mode == "activate":
        result = p3c.inspect_operational_gate(
            actor_account_id=actor_account_id,
            expected_admin_account_ids=expected_admin_account_ids,
        )
        return result["eligible_admin_count"]
    if mode == "compensate":
        return _check_compensation_preview(
            actor_account_id=actor_account_id,
            expected_admin_account_ids=expected_admin_account_ids,
        )
    raise TransitionRefused("Unsupported transition mode.")


def _record_service(*, service, actor, activate):
    old = not activate
    service.is_active = activate
    service.save(update_fields=["is_active"])
    record_access_audit_receipt(
        actor=actor,
        action=p3b.SERVICE_ACTIVATE if activate else p3b.SERVICE_DEACTIVATE,
        old_value=p3b._service_state(service, old),
        new_value=p3b._service_state(service, activate),
        reason="permission_change",
    )


def _record_binding(*, binding, permission, actor, admin, activate):
    old = not activate
    binding.is_active = activate
    binding.save(update_fields=["is_active"])
    record_access_audit_receipt(
        actor=actor, role=admin, permission=permission,
        action=p3b.BINDING_ACTIVATE if activate else p3b.BINDING_DEACTIVATE,
        old_value=p3b._binding_state(binding, old),
        new_value=p3b._binding_state(binding, activate),
        reason="permission_change",
    )


def _execute_test_transition(*, mode, actor_account_id,
                             expected_admin_account_ids, confirmation):
    """Exercise proposed operational mechanics, with no path to dev DB writes.

    Validates exact scope, source/receipt provenance, BEFORE and AFTER states,
    transaction rollback, current effective grants, and unchanged API gates.
    """
    if mode not in ("activate", "compensate"):
        raise TransitionRefused("Unsupported transition mode.")
    if type(actor_account_id) is not int or not 1 <= actor_account_id <= 2_147_483_647:
        raise TransitionRefused("A valid application Admin audit actor ID is required.")
    scope = p3b._expected_ids(expected_admin_account_ids)
    if actor_account_id not in scope:
        raise TransitionRefused("Audit actor must be in the expected scope.")
    p1._expected()  # frozen contract pinning before advisory lock
    db = _write_target(confirmation)
    p3b._acquire_lock(db)
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            before = mode == "compensate"
            actor, admin, services, permissions, bindings = p3b._snapshot(
                actor_id=actor_account_id, expected_ids=scope, active=before,
            )
            p3b._assert_effective_permissions(scope, active=before)
            if mode == "activate":
                p3b._assert_no_prior_transition_audits()
                for code in p1.SERVICE_CODES:
                    _record_service(service=services[code], actor=actor, activate=True)
                for code in p1.PERMISSION_CODES:
                    permission = permissions[code]
                    _record_binding(binding=bindings[permission.pk], permission=permission,
                                    actor=actor, admin=admin, activate=True)
            else:
                p3b._verify_receipts(
                    event_service=p3b.SERVICE_ACTIVATE,
                    event_binding=p3b.BINDING_ACTIVATE,
                    actor=actor, admin=admin, services=services,
                    permissions=permissions, bindings=bindings,
                    before=False, after=True,
                )
                if AccessAuditLog.objects.filter(
                    action__in=(p3b.SERVICE_DEACTIVATE, p3b.BINDING_DEACTIVATE)
                ).exists():
                    raise TransitionRefused("Compensation already attempted; manual review required.")
                # Revoke grants before the services: fail-closed order.
                for code in p1.PERMISSION_CODES:
                    permission = permissions[code]
                    _record_binding(binding=bindings[permission.pk], permission=permission,
                                    actor=actor, admin=admin, activate=False)
                for code in p1.SERVICE_CODES:
                    _record_service(service=services[code], actor=actor, activate=False)

            after = not before
            p3b._snapshot(actor_id=actor_account_id, expected_ids=scope, active=after)
            p3b._verify_receipts(
                event_service=p3b.SERVICE_ACTIVATE,
                event_binding=p3b.BINDING_ACTIVATE,
                actor=actor, admin=admin, services=services,
                permissions=permissions, bindings=bindings,
                before=False, after=True,
            )
            if mode == "compensate":
                p3b._verify_receipts(
                    event_service=p3b.SERVICE_DEACTIVATE,
                    event_binding=p3b.BINDING_DEACTIVATE,
                    actor=actor, admin=admin, services=services,
                    permissions=permissions, bindings=bindings,
                    before=True, after=False,
                )
            elif AccessAuditLog.objects.filter(
                action__in=(p3b.SERVICE_DEACTIVATE, p3b.BINDING_DEACTIVATE)
            ).exists():
                raise TransitionRefused("Unexpected compensation receipt.")
            p3b._assert_effective_permissions(scope, active=after)
            _write_target(confirmation)  # repeat target, flags, URL and hard barrier before commit
        return "TEST_ACTIVATED" if mode == "activate" else "TEST_COMPENSATED"
    finally:
        p3b._release_lock(db)


class Command(BaseCommand):
    help = ("P3D operational transition preview for local dev; activation and "
            "compensation execute ONLY in disposable tests. Local writes locked.")

    def add_arguments(self, parser):
        parser.add_argument("--mode", choices=("activate", "compensate"), required=True)
        parser.add_argument("--actor-account-id", type=int, required=True)
        parser.add_argument("--expected-admin-account-ids", required=True)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--confirm-disposable-test")

    def handle(self, *args, **options):
        try:
            if options["apply"]:
                result = _execute_test_transition(
                    mode=options["mode"],
                    actor_account_id=options["actor_account_id"],
                    expected_admin_account_ids=options["expected_admin_account_ids"],
                    confirmation=options["confirm_disposable_test"],
                )
                self.stdout.write(
                    f"AR-6C7D.9 P3D: {result}; disposable_test_only=YES; "
                    "development_database_writes=NO; api_activation=NO"
                )
            else:
                count = _preview(
                    mode=options["mode"],
                    actor_account_id=options["actor_account_id"],
                    expected_admin_account_ids=options["expected_admin_account_ids"],
                )
                self.stdout.write(
                    f"AR-6C7D.9 P3D: PREVIEW PASSED; mode={options['mode']}; "
                    f"eligible_admin_count={count}; ACTUAL WRITES BLOCKED"
                )
                self.stdout.write(
                    "Backup/restore and release authorization NOT attested; NO WRITES EXECUTED."
                )
        except Exception as exc:
            raise CommandError(
                "AR-6C7D.9 P3D: REFUSED; transition unsafe, unreleased, or inconsistent. "
                "NO SUCCESS REPORTED."
            ) from exc
