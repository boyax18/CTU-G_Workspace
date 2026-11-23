"""AR-6C7D.9 P3B: disposable-MySQL-only activation + compensation exercise.

This is NOT the operational/local-development activation command. Explicit
code-level gate excludes config.settings and ctug_workspace, even with --run.
No migrations, URLs, settings changes or account-review actions are performed.
"""

import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction
from django.db.models import Max

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


def _governed_school_accounts(*, permission_rows, binding_rows, services, admin, actor):
    """WF-02.05 stage 3A (owner-authorized Option A, 18 Nov 2026): the ONLY rows tolerated beyond
    the registration-review scope are the three governed accounts.school_accounts.* definitions and
    their Admin bindings, in one exact phase state (definitions only, inactive or active bindings),
    each proven by its own append-only WF-02.05 receipts recorded after the P4 activation. Anything
    else (a fourth or differing definition, a foreign role, a partial or tampered state, a receipt
    without its row) is refused, as before. Returns them so callers can prove they are untouched.
    """
    from . import provision_school_accounts_local_dev as s3

    registration_ids = {row.pk for row in permission_rows if row.permission_code in p1.PERMISSION_CODES}
    extra = {row.permission_code: row for row in permission_rows if row.pk not in registration_ids}
    extra_bindings = [row for row in binding_rows if row.permission_id not in registration_ids]
    receipts = AccessAuditLog.objects.select_for_update().filter(action__in=tuple(s3.EVENTS.values()))
    if not extra:
        if extra_bindings or receipts.exists():
            raise ActivationExerciseRefused("Unexpected or missing catalogue rows.")
        return {}, []
    released = (AccessAuditLog.objects.filter(action__in=(SERVICE_ACTIVATE, BINDING_ACTIVATE))
                .aggregate(last=Max("pk"))["last"])
    if released is None or receipts.filter(pk__lte=released).exists():
        raise ActivationExerciseRefused("School-account rows must be provisioned after the registration release.")
    try:
        s3._verify_metadata(extra, s3.catalogue_definitions(), services[s3.SERVICE_CODE], actor)
        if extra_bindings:
            states = {row.is_active for row in extra_bindings}
            if len(states) != 1:
                raise ActivationExerciseRefused("Partially active school-account bindings.")
            s3._verify_bindings(extra_bindings, extra, admin, actor, active=states.pop())
        elif receipts.filter(action__in=(s3.EVENTS["bindings"], s3.EVENTS["activate"])).exists():
            raise ActivationExerciseRefused("School-account binding receipts without bindings.")
    except s3.SchoolAccountsProvisionRefused as exc:
        raise ActivationExerciseRefused("Unexpected or missing catalogue rows.") from exc
    return extra, extra_bindings


def _governance_contract():
    """WF-03.01 D-85: the exact Technical Super Admin governance profile and its receipt actions,
    taken from the pinned catalogue v2 through the Django-Superuser procedure's own definitions."""
    from apps.access_control import framework_roles as fr
    from apps.access_control.role_management import RoleChangeUnavailable, TECHNICAL
    try:
        codes, definitions, role_definition = fr._governance_definitions()
    except RoleChangeUnavailable as exc:
        raise ActivationExerciseRefused("The governance profile is no longer defined by catalogue v2.") from exc
    return fr, TECHNICAL, tuple(codes), definitions, role_definition


def _governed_governance_profile(*, permission_rows, binding_rows, services, released):
    """WF-03.01 D-85 (owner-authorized 18 Nov 2026, local development only): besides the registration
    and WF-02.05 school-account rows, the ONLY tolerated rows are the Technical Super Admin governance
    profile created by the Django-Superuser procedure: exactly the six catalogue v2 composition codes on
    the access_control service with the catalogue's attributes, bound only to an active Technical Super
    Admin role (exactly six active bindings and nothing else on that role), proven field by field by
    exactly one framework.role.create, six framework.permission.create and six
    framework.role_binding.create receipts from ONE designated framework superuser, in creation order
    and all after the registration P4 activation. Anything else - a missing, extra or altered
    definition, a foreign or inactive binding, an inactive role, or a missing, duplicated, forged,
    reordered, stale or mismatched receipt - is refused. Returns the rows so callers exclude them from
    the registration checks; it never authorizes compensation by itself (see _assert_no_governance_profile).
    """
    fr, technical_name, codes, definitions, role_definition = _governance_contract()
    governance = {row.permission_code: row for row in permission_rows if row.permission_code in codes}
    governance_ids = {row.pk for row in governance.values()}
    role = Role.objects.select_for_update().filter(role_name=technical_name).first()
    receipts = list(AccessAuditLog.objects.select_for_update()
                    .filter(action__in=(fr.ROLE_CREATE, fr.PERMISSION_CREATE, fr.BINDING_CREATE))
                    .order_by("access_audit_log_id"))
    governance_bindings = [b for b in binding_rows if b.permission_id in governance_ids]
    role_bindings = [b for b in binding_rows if role is not None and b.role_id == role.pk]
    if not governance:
        # A bare Technical Super Admin role row (e.g. an inactive protected-executor fixture) was
        # tolerated before D-85 and still is; any binding on it or any governance receipt is not.
        if receipts or role_bindings:
            raise ActivationExerciseRefused("Governance evidence or bindings exist without their definitions.")
        return {}, []
    service = services["access_control"]
    if (set(governance) != set(codes) or role is None or not role.is_active
            or role.description != role_definition["description"]
            or any(not fr._matches(governance[code], definitions[code], service) for code in codes)):
        raise ActivationExerciseRefused("The Technical Super Admin governance definitions are partial or differ.")
    bound = {b.pk for b in governance_bindings}
    if (bound != {b.pk for b in role_bindings} or len(governance_bindings) != len(codes)
            or {b.permission_id for b in governance_bindings} != governance_ids
            or any(b.role_id != role.pk or not b.is_active for b in governance_bindings)):
        raise ActivationExerciseRefused("The Technical Super Admin governance bindings are partial, foreign or inactive.")

    role_receipts = [r for r in receipts if r.action == fr.ROLE_CREATE]
    permission_receipts = [r for r in receipts if r.action == fr.PERMISSION_CREATE]
    binding_receipts = [r for r in receipts if r.action == fr.BINDING_CREATE]
    if (len(role_receipts), len(permission_receipts), len(binding_receipts)) != (1, len(codes), len(codes)):
        raise ActivationExerciseRefused("Governance receipts are missing or duplicated.")
    actors = {r.actor_account_id for r in receipts}
    operator = Account.objects.filter(pk=next(iter(actors))).first() if len(actors) == 1 else None
    if (operator is None or not (operator.is_staff and operator.is_superuser)
            or AccountRole.objects.filter(account=operator).exists()):
        raise ActivationExerciseRefused("Governance receipts are not from one framework operator.")
    by_permission = {b.permission_id: b for b in governance_bindings}
    created = role_receipts[0]
    valid = (created.role_id == role.pk and created.permission_id is None and created.target_account_id is None
             and created.old_value is None and created.new_value == {"role_id": role.pk, "is_active": True}
             and created.reason == "permission_change")
    valid = valid and {r.permission_id for r in permission_receipts} == governance_ids and all(
        r.role_id is None and r.target_account_id is None and r.old_value is None and r.reason == "permission_change"
        and r.new_value == {"permission_id": r.permission_id, "service_id": service.pk} for r in permission_receipts)
    valid = valid and {r.permission_id for r in binding_receipts} == governance_ids and all(
        r.role_id == role.pk and r.target_account_id is None and r.old_value is None and r.reason == "permission_change"
        and r.new_value == {"role_id": role.pk, "permission_id": r.permission_id,
                            "role_permission_id": by_permission[r.permission_id].pk, "is_active": True}
        and by_permission[r.permission_id].granted_by_id == operator.pk for r in binding_receipts)
    if not valid:
        raise ActivationExerciseRefused("Governance receipts do not match the governance rows.")
    if not (released is not None and released < created.pk < min(r.pk for r in permission_receipts)
            and max(r.pk for r in permission_receipts) < min(r.pk for r in binding_receipts)):
        raise ActivationExerciseRefused("Governance receipts are out of order or precede the registration release.")
    return governance, governance_bindings


def _assert_no_governance_profile():
    """WF-03.01 D-85: compensation is one-way and deactivates the shared access_control service, which
    would strand both the Technical Super Admin and the Django-Superuser procedure (it needs that
    service active), so it is refused while the governance profile exists - whether or not a holder is
    currently effective. Without the six governance permission rows no Technical Super Admin can be
    effective, so a bare role assignment is left exactly as before D-85 (this check also runs on P4's
    post-activation snapshot). The permission rows are already locked by _snapshot, assignment rows are
    locked here, and every role change locks the two service rows that this snapshot already holds, so
    a concurrent grant waits and then finds the services inactive."""
    from apps.access_control.role_management import TECHNICAL
    from apps.access_control.technical_admin import has_technical_authority
    _, _, codes, _, _ = _governance_contract()
    if not Permission.objects.filter(permission_code__in=codes).exists():
        return
    holders = list(AccountRole.objects.select_for_update().filter(role__role_name=TECHNICAL)
                   .select_related("account").order_by("account_role_id"))
    if any(has_technical_authority(h.account, code) for h in holders for code in codes):
        raise ActivationExerciseRefused("An effective Technical Super Admin exists; compensation refused.")
    if holders:
        raise ActivationExerciseRefused("A Technical Super Admin assignment exists; compensation refused.")
    raise ActivationExerciseRefused("The governance profile depends on the shared access_control service; compensation refused.")


def _assert_no_stranded_suspensions():
    """Compensation is one-way (P4 cannot re-activate after it). Refuse it while any account is still
    deactivated through WF-02.05, because the rollback would leave it with no governed path back."""
    latest = (AccessAuditLog.objects.filter(action__startswith="account.status.", target_account_id__isnull=False)
              .values("target_account_id").annotate(last=Max("pk")))
    for row in latest:
        event = AccessAuditLog.objects.get(pk=row["last"])
        if event.action == "account.status.suspend" and Account.objects.filter(
                pk=row["target_account_id"], is_active=False).exists():
            raise ActivationExerciseRefused("An account deactivated through WF-02.05 would be stranded; compensation refused.")


def school_account_scope_codes():
    from . import provision_school_accounts_local_dev as s3
    return frozenset(s3.CODES)


def _snapshot(*, actor_id, expected_ids, active):
    """Lock and validate every in-scope row, P1/P2 receipts, and impact scope."""
    # WF-03.01 R-1 (Option A, owner-authorized 19 Nov 2026): lock the shared service rows FIRST, in the
    # service_id order role_management.lock_state uses, so a concurrent role change and this snapshot
    # serialize on them instead of deadlocking over the Admin role, the actor's account, the Admin
    # assignments or the overrides. The rows are re-read and validated below unchanged; no write.
    list(Service.objects.select_for_update().order_by("service_id"))
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
    registration_rows = [item for item in permission_rows if item.permission_code in p1.PERMISSION_CODES]
    permissions = {item.permission_code: item for item in registration_rows}
    if (len(service_rows) != 2 or len(registration_rows) != 3
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

    all_bindings = list(RolePermission.objects.select_for_update().order_by("role_permission_id"))
    # WF-03.01 D-85: partition the exact Technical Super Admin governance profile out FIRST (it is
    # verified on its own receipts), so the WF-02.05 check still sees only registration + school rows.
    released = (AccessAuditLog.objects.filter(action__in=(SERVICE_ACTIVATE, BINDING_ACTIVATE))
                .aggregate(last=Max("pk"))["last"])
    governance, governance_bindings = _governed_governance_profile(
        permission_rows=permission_rows, binding_rows=all_bindings, services=services, released=released,
    )
    governance_ids = {row.pk for row in governance.values()}
    school_rows = [row for row in permission_rows if row.pk not in governance_ids]
    school_binding_rows = [row for row in all_bindings if row not in governance_bindings]
    extra, extra_bindings = _governed_school_accounts(
        permission_rows=school_rows, binding_rows=school_binding_rows,
        services=services, admin=admin, actor=actor,
    )
    if len(permission_rows) != 3 + len(extra) + len(governance):
        raise ActivationExerciseRefused("Unexpected or missing catalogue rows.")
    if active:
        _assert_no_stranded_suspensions()
        _assert_no_governance_profile()
    # The registration-review scope and every check on it are exactly as before; P3B/P4 operate
    # only on these three bindings and never on the governed school-account or governance rows.
    binding_rows = [item for item in school_binding_rows if item not in extra_bindings]
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
    # WF-02.05: the governed school-account codes are effective only for the exact Admin scope,
    # only while their bindings are active AND the shared services are active; never otherwise.
    school_codes = school_account_scope_codes()
    school_bindings = list(RolePermission.objects.filter(permission__permission_code__in=school_codes))
    school_live = active and len(school_bindings) == 3 and all(b.is_active for b in school_bindings)
    # WF-03.01 D-85: a governance code may be effective only for an Admin + Technical Super Admin
    # composite holder (never through Admin alone, an override, or a framework flag).
    _, technical_name, governance_codes, _, _ = _governance_contract()
    governance_codes = frozenset(governance_codes)
    accounts = list(Account.objects.order_by("account_id"))
    if len(accounts) > 100:
        raise ActivationExerciseRefused("This exercise is limited to at most 100 test accounts.")
    for account in accounts:
        granted = get_effective_permissions(account)
        expected = target_codes if active and account.pk in expected_ids else frozenset()
        expected_school = school_codes if school_live and account.pk in expected_ids else frozenset()
        if granted & target_codes != expected or granted & school_codes != expected_school:
            raise ActivationExerciseRefused("Unexpected effective permission detected.")
        governed = granted & governance_codes
        if governed and not (account.pk in expected_ids and AccountRole.objects.filter(
                account=account, role__role_name=technical_name, role__is_active=True).exists()):
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
