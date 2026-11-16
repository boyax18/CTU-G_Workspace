"""AR-6C7D.9 P3B: disposable-MySQL-only activation + compensation exercise.

This is NOT the operational/local-development activation command. Explicit
code-level gate excludes config.settings and ctug_workspace, even with --run.
No migrations, URLs, settings changes or account-review actions are performed.
"""

import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction

from apps.accounts.models import Account
from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.management.commands import (
    init_registration_review_metadata_local_dev as p1,
    init_registration_review_inactive_bindings_local_dev as p2,
)
from apps.access_control.models import (
    AccountPermission, AccountRole, AccessAuditLog, Permission, Role,
    RolePermission, Service,
)
from apps.access_control.services import get_effective_permissions

TEST_CONFIRM = "AR-6C7D9:P3B:DISPOSABLE-TEST-ONLY"
SERVICE_ACTIVATE = "workspace.review.service.activate"
BINDING_ACTIVATE = "workspace.review.role_binding.activate"
SERVICE_DEACTIVATE = "workspace.review.service.deactivate"
BINDING_DEACTIVATE = "workspace.review.role_binding.deactivate"
TRANSITION_EVENTS = (
    SERVICE_ACTIVATE, BINDING_ACTIVATE,
    SERVICE_DEACTIVATE, BINDING_DEACTIVATE,
)


class ActivationExerciseRefused(RuntimeError):
    """Only exact, auditable, disposable-test operations are permitted."""


def _expected_ids(value):
    """An explicit exact set, not only a count of potentially affected Admins."""
    if type(value) is not str or not re.fullmatch(r"[1-9][0-9]*(,[1-9][0-9]*)*", value):
        raise ActivationExerciseRefused("Supply exact comma-separated Admin account IDs.")
    ids = [int(item) for item in value.split(",")]
    if len(ids) > 20 or len(ids) != len(set(ids)) or any(x > 2_147_483_647 for x in ids):
        raise ActivationExerciseRefused("The expected Admin account set is invalid.")
    return frozenset(ids)


def _test_target(confirmation):
    # Not merely a confirmation string: test settings and P2's isolated MySQL
    # DB/name/runner/isolation/flags/route/digest gates MUST all agree.
    if settings.SETTINGS_MODULE != "config.test_settings" or confirmation != TEST_CONFIRM:
        raise ActivationExerciseRefused("Only an isolated disposable MySQL test database is supported.")
    return p2._target(p2.TEST_CONFIRM)


def _acquire_lock(db):
    with db.cursor() as cursor:
        cursor.execute("SELECT GET_LOCK(%s, 0)", [p1.LOCK_NAME])
        if cursor.fetchone()[0] != 1:
            raise ActivationExerciseRefused("Another permission-catalogue operation is running.")


def _release_lock(db):
    with db.cursor() as cursor:
        cursor.execute("SELECT RELEASE_LOCK(%s)", [p1.LOCK_NAME])


def _eligible_admin_ids(admin):
    # A role grant could authorize staff/superusers too in the generic
    # evaluator. Refuse those assignments rather than excluding them silently.
    assignments = list(AccountRole.objects.select_for_update().filter(
        role_id=admin.pk, role__is_active=True,
        account__is_active=True, account__request_status="Approved",
    ).select_related("account").order_by("account_role_id"))
    if any(item.account.is_staff or item.account.is_superuser for item in assignments):
        raise ActivationExerciseRefused("A framework staff/superuser has an eligible Admin role assignment.")
    return frozenset(item.account_id for item in assignments)


def _snapshot(*, actor_id, expected_ids, active):
    """Lock and validate every in-scope row, P1/P2 receipts, and impact scope."""
    try:
        admin = Role.objects.select_for_update().get(role_name="Admin", is_active=True)
        actor = p1._actor(actor_id)
    except Exception as exc:
        raise ActivationExerciseRefused("An eligible existing application Admin actor is required.") from exc
    if actor.pk not in expected_ids or _eligible_admin_ids(admin) != expected_ids:
        raise ActivationExerciseRefused("Eligible Admin accounts differ from the exact approved impact set.")
    if AccountPermission.objects.select_for_update().exists():
        raise ActivationExerciseRefused("Account-level overrides are outside this exercise.")

    service_defs, permission_defs = p1._expected()
    service_rows = list(Service.objects.select_for_update().order_by("service_id"))
    permission_rows = list(Permission.objects.select_for_update().order_by("permission_id"))
    services = {item.service_code: item for item in service_rows}
    permissions = {item.permission_code: item for item in permission_rows}
    if (len(service_rows) != 2 or len(permission_rows) != 3
            or set(services) != set(p1.SERVICE_CODES)
            or set(permissions) != set(p1.PERMISSION_CODES)):
        raise ActivationExerciseRefused("Unexpected or missing catalogue rows.")
    for code in p1.SERVICE_CODES:
        row, expected = services[code], service_defs[code]
        if (row.service_name != expected["service_name"]
                or row.description != expected["description"]
                or row.is_active is not active):
            raise ActivationExerciseRefused("Service metadata/state differs.")
    for code in p1.PERMISSION_CODES:
        expected = permission_defs[code]
        if not p1._matches_permission(
            permissions[code], expected, services[expected["service_code"]]
        ):
            raise ActivationExerciseRefused("Permission metadata differs.")
    try:
        p1._verify_prior_audits(services, permissions, actor)
    except Exception as exc:
        raise ActivationExerciseRefused("P1 audit evidence differs.") from exc

    binding_rows = list(RolePermission.objects.select_for_update().order_by("role_permission_id"))
    bindings = {item.permission_id: item for item in binding_rows}
    expected_permission_ids = {item.pk for item in permissions.values()}
    if (len(binding_rows) != 3
            or set(bindings) != expected_permission_ids
            or any(item.role_id != admin.pk
                   or item.granted_by_id != actor.pk
                   or item.is_active is not active
                   for item in binding_rows)):
        raise ActivationExerciseRefused("Admin binding scope/state differs.")
    try:
        p2._verify_p2_audits(binding_rows, admin, actor)
    except Exception as exc:
        raise ActivationExerciseRefused("P2 audit evidence differs.") from exc
    return actor, admin, services, permissions, bindings


def _service_state(service, state):
    return {"service_id": service.pk, "is_active": state}


def _binding_state(binding, state):
    return {
        "role_id": binding.role_id,
        "permission_id": binding.permission_id,
        "role_permission_id": binding.pk,
        "is_active": state,
    }


def _verify_receipts(*, event_service, event_binding, actor, admin,
                     services, permissions, bindings, before, after):
    service_logs = list(AccessAuditLog.objects.select_for_update().filter(
        action=event_service
    ).order_by("access_audit_log_id"))
    binding_logs = list(AccessAuditLog.objects.select_for_update().filter(
        action=event_binding
    ).order_by("access_audit_log_id"))
    if len(service_logs) != 2 or len(binding_logs) != 3:
        raise ActivationExerciseRefused("Transition receipt counts differ.")
    used_services = set()
    for log in service_logs:
        data = log.new_value
        service = next((s for s in services.values() if type(data) is dict
                        and s.pk == data.get("service_id")), None)
        if (service is None or service.pk in used_services
                or log.actor_account_id != actor.pk or log.target_account_id is not None
                or log.role_id is not None or log.permission_id is not None
                or log.reason != "permission_change"
                or log.old_value != _service_state(service, before)
                or data != _service_state(service, after)):
            raise ActivationExerciseRefused("Service transition receipt differs.")
        used_services.add(service.pk)
    if used_services != {s.pk for s in services.values()}:
        raise ActivationExerciseRefused("Service transition receipt coverage differs.")
    used_permissions = set()
    for log in binding_logs:
        binding = bindings.get(log.permission_id)
        if (binding is None or binding.permission_id in used_permissions
                or log.actor_account_id != actor.pk or log.target_account_id is not None
                or log.role_id != admin.pk or log.reason != "permission_change"
                or log.old_value != _binding_state(binding, before)
                or log.new_value != _binding_state(binding, after)):
            raise ActivationExerciseRefused("Binding transition receipt differs.")
        used_permissions.add(binding.permission_id)
    if used_permissions != set(bindings):
        raise ActivationExerciseRefused("Binding transition receipt coverage differs.")


def _assert_effective_permissions(expected_ids, *, active):
    """Explicitly check every test account; fail on any unintended new grant."""
    target_codes = frozenset(p1.PERMISSION_CODES)
    accounts = list(Account.objects.order_by("account_id"))
    if len(accounts) > 100:
        raise ActivationExerciseRefused("This exercise is limited to at most 100 test accounts.")
    for account in accounts:
        effective = get_effective_permissions(account) & target_codes
        expected = target_codes if active and account.pk in expected_ids else frozenset()
        if effective != expected:
            raise ActivationExerciseRefused("Unexpected effective permission detected.")


def _assert_no_prior_transition_audits():
    if AccessAuditLog.objects.filter(action__in=TRANSITION_EVENTS).exists():
        raise ActivationExerciseRefused("Existing Phase 3B receipts require manual review.")


def _perform(*, mode, actor_account_id, expected_admin_account_ids, confirmation):
    if mode not in ("activate", "compensate"):
        raise ActivationExerciseRefused("Unsupported exercise mode.")
    if type(actor_account_id) is not int or not 1 <= actor_account_id <= 2_147_483_647:
        raise ActivationExerciseRefused("An existing numeric Admin actor ID is required.")
    exact_scope = _expected_ids(expected_admin_account_ids)
    db = _test_target(confirmation)
    _acquire_lock(db)
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            before = mode == "compensate"
            actor, admin, services, permissions, bindings = _snapshot(
                actor_id=actor_account_id, expected_ids=exact_scope, active=before,
            )
            if mode == "activate":
                _assert_no_prior_transition_audits()
                _assert_effective_permissions(exact_scope, active=False)
                for code in p1.SERVICE_CODES:
                    service = services[code]
                    service.is_active = True
                    service.save(update_fields=["is_active"])
                    record_access_audit_receipt(
                        actor=actor, action=SERVICE_ACTIVATE,
                        old_value=_service_state(service, False),
                        new_value=_service_state(service, True),
                        reason="permission_change",
                    )
                for code in p1.PERMISSION_CODES:
                    permission = permissions[code]
                    binding = bindings[permission.pk]
                    binding.is_active = True
                    binding.save(update_fields=["is_active"])
                    record_access_audit_receipt(
                        actor=actor, role=admin, permission=permission,
                        action=BINDING_ACTIVATE,
                        old_value=_binding_state(binding, False),
                        new_value=_binding_state(binding, True),
                        reason="permission_change",
                    )
            else:
                _verify_receipts(
                    event_service=SERVICE_ACTIVATE,
                    event_binding=BINDING_ACTIVATE,
                    actor=actor, admin=admin, services=services,
                    permissions=permissions, bindings=bindings,
                    before=False, after=True,
                )
                if AccessAuditLog.objects.filter(
                    action__in=(SERVICE_DEACTIVATE, BINDING_DEACTIVATE)
                ).exists():
                    raise ActivationExerciseRefused("Compensation already attempted; manual review required.")
                for code in p1.PERMISSION_CODES:
                    permission = permissions[code]
                    binding = bindings[permission.pk]
                    binding.is_active = False
                    binding.save(update_fields=["is_active"])
                    record_access_audit_receipt(
                        actor=actor, role=admin, permission=permission,
                        action=BINDING_DEACTIVATE,
                        old_value=_binding_state(binding, True),
                        new_value=_binding_state(binding, False),
                        reason="permission_change",
                    )
                for code in p1.SERVICE_CODES:
                    service = services[code]
                    service.is_active = False
                    service.save(update_fields=["is_active"])
                    record_access_audit_receipt(
                        actor=actor, action=SERVICE_DEACTIVATE,
                        old_value=_service_state(service, True),
                        new_value=_service_state(service, False),
                        reason="permission_change",
                    )

            after = not before
            _snapshot(actor_id=actor_account_id, expected_ids=exact_scope, active=after)
            _verify_receipts(
                event_service=SERVICE_ACTIVATE,
                event_binding=BINDING_ACTIVATE,
                actor=actor, admin=admin, services=services,
                permissions=permissions, bindings=bindings,
                before=False, after=True,
            )
            if mode == "compensate":
                _verify_receipts(
                    event_service=SERVICE_DEACTIVATE,
                    event_binding=BINDING_DEACTIVATE,
                    actor=actor, admin=admin, services=services,
                    permissions=permissions, bindings=bindings,
                    before=True, after=False,
                )
            else:
                if AccessAuditLog.objects.filter(
                    action__in=(SERVICE_DEACTIVATE, BINDING_DEACTIVATE)
                ).exists():
                    raise ActivationExerciseRefused("Unexpected compensation receipt.")
            _assert_effective_permissions(exact_scope, active=after)
            # Repeat the target, pin, flags and URL checks before commit.
            _test_target(confirmation)
        return "EXERCISED_ACTIVATION" if mode == "activate" else "EXERCISED_COMPENSATION"
    finally:
        _release_lock(db)


class Command(BaseCommand):
    help = "DISPOSABLE TEST DATABASE ONLY: exercise activation or compensation; never local dev."

    def add_arguments(self, parser):
        parser.add_argument("--run-disposable-test", action="store_true")
        parser.add_argument("--mode", choices=("activate", "compensate"), required=True)
        parser.add_argument("--actor-account-id", type=int, required=True)
        parser.add_argument("--expected-admin-account-ids", required=True)
        parser.add_argument("--confirm-disposable-test", required=True)

    def handle(self, *args, **options):
        if not options["run_disposable_test"]:
            raise CommandError("No implicit activation. Disposable-test execution must be explicit.")
        try:
            result = _perform(
                mode=options["mode"],
                actor_account_id=options["actor_account_id"],
                expected_admin_account_ids=options["expected_admin_account_ids"],
                confirmation=options["confirm_disposable_test"],
            )
        except Exception as exc:
            raise CommandError(
                "AR-6C7D.9 P3B: REFUSED or rolled back; no activation success reported."
            ) from exc
        self.stdout.write(
            f"AR-6C7D.9 P3B: {result}; disposable_test_only=YES; "
            "development_database_writes=NO; api_activation=NO"
        )
