"""WF-03.01 Django-Superuser-exclusive protected role configuration (owner-approved stage A, 18 Nov 2026).

FR-ADM-03, FR-DJA-04/06, D-91 to D-93: only an authenticated, designated Django framework superuser
may grant or revoke Technical Super Admin; it may also grant or revoke School Admin (`Admin`). This
is a framework procedure, NOT a Workspace API and NOT an is_superuser shortcut: Workspace requests
keep using the ordinary evaluator, and framework accounts never hold Workspace roles.

Every call: password re-authentication of a designated framework account (never a claimed identity),
an exact per-action confirmation, the WF-02.03/02.05 lock order in one writer_atomic READ COMMITTED
transaction, eligibility rechecked inside the lock (an active, Approved, non-framework account that
holds an active Instructor role; the Instructor role is always kept), one append-only audit receipt
per row created or removed, and a session-epoch bump for the target (D-83). Any failure rolls the
whole transaction back, so no partial state can be committed; a repeated call is refused as
state_changed. The Technical Super Admin role and its six governance permissions are created exactly
as catalogue v2 defines them (composition.application_super_admin, bound only to Technical Super
Admin) on the first grant, and verified on every later grant; inconsistent state is refused, never
repaired. The last effective Technical Super Admin is never removed (D-88).

Targets (default deny, checked before any data read): the disposable MySQL test database, or the local
development database through the D-93/D-95 development gate (owner-authorized implementation 19 Nov 2026;
NOT yet authorized for use). The development gate requires, all positively verified: the config.settings
module, DEBUG on, exactly one database alias, MySQL `ctug_workspace` on loopback (configured and live), READ
COMMITTED, no review backend / role-assignment API flag, no protected writer, no mounted review or
role-management route, and an operator allowlist taken only from the process environment (never from
backend/.env). Its confirmation is database-bound (`ctug_workspace:WF-03.01:<operation>:<account_id>`). The
low-level mutators refuse unless configure_role has passed every gate in the current transaction.
"""

import contextvars
import os
import re

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connection, connections, transaction

from apps.accounts import session_revocation
from apps.accounts.models import Account

from .audit import record_access_audit_receipt
from .catalogue.validation_v2 import validate_manifest
from .models import AccountRole, Permission, Role, RolePermission, Service
from .role_management import (
    ADMIN, ADMIN_ASSIGNMENT_CODE, FRAMEWORK_ASSIGN_ACTION, FRAMEWORK_REVOKE_ACTION, INSTRUCTOR, ROLE_REASON, TECHNICAL,
    RoleChangeConflict, RoleChangeDenied, RoleChangeUnavailable, admin_revocation_refusal, effective_holders,
    is_eligible_account, lock_state, refuse_while_protected_writer_enabled, require_mysql_read_committed, role_row,
    snapshot,
)
from .technical_admin import has_technical_authority
from .writer_boundary import writer_atomic

OPERATIONS = ("grant-school-admin", "revoke-school-admin", "grant-technical-super-admin", "revoke-technical-super-admin")
OPERATORS_SETTING = "WORKSPACE_ROLE_CONFIGURATION_OPERATORS"
# D-93/D-95 development gate: the ONLY non-test target, matched exactly (configuration and live connection).
DEVELOPMENT_SETTINGS_MODULE = "config.settings"
DEVELOPMENT_DATABASE = "ctug_workspace"
LOOPBACK = frozenset({"localhost", "127.0.0.1", "::1"})
# Modes that must be off for the development target: review backends and the role-assignment API (the
# protected writer is checked separately).
CONFLICTING_FLAGS = ("WORKSPACE_REGISTRATION_REVIEW_API_ENABLED", "WORKSPACE_REGISTRATION_APPROVAL_ENABLED",
                     "WORKSPACE_ROLE_ASSIGNMENT_ENABLED")
ROLE_MANAGEMENT_VIEW_MODULES = frozenset({"apps.access_control.role_assignment_api"})
_OPERATOR_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,49}")
_ENV_KEY_LINE = re.compile(r"^\s*(?:export\s+)?WORKSPACE_ROLE_CONFIGURATION_OPERATORS\s*=", re.MULTILINE)
# Set only by configure_role after every gate and the operator's re-authentication, for one transaction.
_AUTHORIZED = contextvars.ContextVar("wf0301_framework_operation", default=None)
PERMISSION_CREATE = "framework.permission.create"
ROLE_CREATE = "framework.role.create"
BINDING_CREATE = "framework.role_binding.create"


def _development_configuration():
    """Configuration only (no connection): does this process claim the D-93/D-95 development target?"""
    return (os.environ.get("DJANGO_SETTINGS_MODULE") == DEVELOPMENT_SETTINGS_MODULE
            and connections[DEFAULT_DB_ALIAS].settings_dict.get("NAME") == DEVELOPMENT_DATABASE)


def confirmation_for(operation, target_id):
    """Exact per-action confirmation; database-bound for the development target (D-93/D-95)."""
    base = f"WF-03.01:{operation}:{target_id}"
    return f"{DEVELOPMENT_DATABASE}:{base}" if _development_configuration() else base


def parse_operator_allowlist(raw):
    """D-95: designated framework-operator School IDs, comma-separated, from the process environment.

    Fail closed: anything empty, malformed or duplicated designates nobody, so a bad value is never mistaken
    for an approval. Deliberately NOT a Django setting: the WF-03.01 release safeguard forbids every settings
    module from defining the role gates (test_release_surface_is_isolated_and_reported)."""
    if type(raw) is not str or not raw.strip():
        return ()
    items = [part.strip() for part in raw.split(",")]
    if any(_OPERATOR_ID.fullmatch(item) is None for item in items) or len(set(items)) != len(items):
        return ()
    return tuple(items)


def _designated_operators(target_kind):
    """The disposable test database keeps its test-only setting; the development target reads ONLY the
    process environment (the gate has already refused a settings or backend/.env definition)."""
    if target_kind == "development":
        return parse_operator_allowlist(os.environ.get(OPERATORS_SETTING))
    return tuple(getattr(settings, OPERATORS_SETTING, ()) or ())


def _env_file():
    return settings.BASE_DIR / ".env"


def _mounted_role_management_routes(urlconf):
    from django.urls import URLResolver, get_resolver
    found = []

    def walk(patterns):
        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                walk(pattern.url_patterns)
                continue
            view = getattr(pattern.callback, "view_class", None) or pattern.callback
            if getattr(view, "__module__", "") in ROLE_MANAGEMENT_VIEW_MODULES:
                found.append(str(pattern.pattern))
    walk(get_resolver(urlconf).url_patterns)
    return found


def _require_development_target():
    """D-93/D-95 development gate: every condition positively verified, otherwise refuse (no data read)."""
    def refuse(reason):
        raise RoleChangeUnavailable(f"The development database gate refused: {reason}.")

    cfg = connection.settings_dict
    if os.environ.get("DJANGO_SETTINGS_MODULE") != DEVELOPMENT_SETTINGS_MODULE:
        refuse("not the config.settings module")
    if settings.DEBUG is not True:
        refuse("DEBUG is not enabled")
    if getattr(settings, "REGISTRATION_TEST_DATABASE", None):
        refuse("a test database is configured")
    if list(settings.DATABASES) != [DEFAULT_DB_ALIAS] or list(connections) != [DEFAULT_DB_ALIAS]:
        refuse("more than one database alias")
    if (connection.vendor != "mysql" or cfg.get("ENGINE") != "django.db.backends.mysql"
            or cfg.get("NAME") != DEVELOPMENT_DATABASE or cfg.get("HOST") not in LOOPBACK):
        refuse("not the local MySQL development database")
    if connection.isolation_level != "read committed":
        refuse("the isolation level is not READ COMMITTED")
    if any(getattr(settings, flag, False) is not False for flag in CONFLICTING_FLAGS):
        refuse("a review or role-management mode is enabled")
    from .executor.client import enabled as executor_enabled
    if executor_enabled():
        refuse("the protected writer is enabled")
    if settings.ROOT_URLCONF != "config.urls":
        refuse("an unexpected URL configuration is active")
    from .management.commands.init_registration_review_metadata_local_dev import unexpected_review_routes
    if unexpected_review_routes(settings.ROOT_URLCONF) or _mounted_role_management_routes(settings.ROOT_URLCONF):
        refuse("a review or role-management route is mounted")
    if getattr(settings, OPERATORS_SETTING, None):
        refuse("the operator allowlist must come only from the process environment, not a settings module")
    if not parse_operator_allowlist(os.environ.get(OPERATORS_SETTING)):
        refuse("no valid operator allowlist is designated in the process environment")
    try:
        env_text = _env_file().read_text(encoding="utf-8")
    except FileNotFoundError:
        env_text = ""
    if _ENV_KEY_LINE.search(env_text):
        refuse("the operator allowlist must not be stored in backend/.env")
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE(), @@transaction_isolation, SUBSTRING_INDEX(USER(), '@', -1), @@port")
        selected, isolation, client_host, port = cursor.fetchone()
    if (selected != DEVELOPMENT_DATABASE or isolation != "READ-COMMITTED" or client_host not in LOOPBACK
            or str(port) != str(cfg.get("PORT"))):
        refuse("the live connection differs from the reviewed local target")


def _require_approved_target():
    """Default deny, before any data read: the disposable test database or the exact development target."""
    test_db = getattr(settings, "REGISTRATION_TEST_DATABASE", "")
    # The process's settings module (manage.py --settings sets it); settings.SETTINGS_MODULE reads as
    # None inside override_settings. The decisive check is the connected database below.
    module = os.environ.get("DJANGO_SETTINGS_MODULE")
    if module == "config.test_settings" and isinstance(test_db, str) and test_db.startswith("test_ctug_registration_"):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            selected = cursor.fetchone()[0]
        if selected != test_db or connection.settings_dict.get("HOST") not in LOOPBACK:
            raise RoleChangeUnavailable("The connected database is not the approved disposable test database.")
        return "test"
    if module == DEVELOPMENT_SETTINGS_MODULE:
        _require_development_target()
        return "development"
    raise RoleChangeUnavailable("This protected procedure runs only against the disposable test database or the "
                                "exactly verified local development database (D-93/D-95).")


def _require_authorized(*, operator, target=None):
    """Bypass resistance: the low-level mutators run only inside a configure_role transaction that passed
    every gate and re-authenticated this operator (for this target, when one is involved)."""
    current = _AUTHORIZED.get()
    if (current is None or not transaction.get_connection(DEFAULT_DB_ALIAS).in_atomic_block
            or current["operator"] != operator.pk or (target is not None and current["target"] != target.pk)):
        raise RoleChangeUnavailable("Role configuration runs only through the protected procedure.")


def _authenticate_operator(school_id, password, target_kind="test"):
    """Designated, active framework superuser with a usable password and NO Workspace role."""
    designated = _designated_operators(target_kind)
    if (type(school_id) is not str or not school_id or type(password) is not str or not password
            or school_id not in designated):
        raise RoleChangeDenied("A designated framework operator is required.")
    try:
        operator = Account.objects.using(DEFAULT_DB_ALIAS).select_for_update().get(
            school_id=school_id, is_staff=True, is_superuser=True, is_active=True, request_status="Approved")
    except (Account.DoesNotExist, Account.MultipleObjectsReturned) as exc:
        raise RoleChangeDenied("A designated framework operator is required.") from exc
    if not operator.has_usable_password() or not operator.check_password(password):
        raise RoleChangeDenied("Operator authentication failed.")
    if AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(account=operator).exists():
        raise RoleChangeDenied("The framework operator must hold no Workspace role.")
    return operator


def _governance_definitions():
    data = validate_manifest().data
    codes = tuple(data["composition"]["application_super_admin"]["required_effective_permissions"])
    permissions = {p["permission_code"]: p for p in data["permissions"]}
    bound = {}
    for b in data["default_bindings"]:
        bound.setdefault(b["permission_code"], set()).add(b["role_name"])
    role = next((r for r in data["roles"] if r["role_name"] == TECHNICAL), None)
    if (role is None or ADMIN_ASSIGNMENT_CODE not in codes or len(codes) != 6
            or any(code not in permissions or permissions[code]["service_code"] != "access_control"
                   or bound.get(code) != {TECHNICAL} for code in codes)):
        raise RoleChangeUnavailable("Catalogue v2 no longer defines the Technical Super Admin governance profile.")
    return codes, {code: permissions[code] for code in codes}, role


def _matches(row, definition, service):
    return (row.service_id == service.pk and row.permission_name == definition["permission_name"]
            and row.module_name == definition["module_name"] and row.action_name == definition["action_name"]
            and row.description == definition["description"])


def _ensure_governance(operator, services):
    """Create (first grant) or verify the Technical Super Admin role and its six bindings; never repair."""
    _require_authorized(operator=operator)
    codes, definitions, role_definition = _governance_definitions()
    service = services["access_control"]
    existing = {p.permission_code: p for p in Permission.objects.using(DEFAULT_DB_ALIAS).select_for_update()
                .filter(permission_code__in=codes).order_by("permission_id")}
    role = role_row(TECHNICAL)
    if role is None and existing:
        raise RoleChangeUnavailable("Governance permissions exist without the Technical Super Admin role.")
    if role is not None and not role.is_active:
        raise RoleChangeUnavailable("The Technical Super Admin role is inactive; manual review is required.")
    for code, row in existing.items():
        if not _matches(row, definitions[code], service):
            raise RoleChangeUnavailable("A governance permission differs from catalogue v2.")
    if role is None:
        role = Role.objects.using(DEFAULT_DB_ALIAS).create(role_name=TECHNICAL, description=role_definition["description"],
                                                           is_active=True)
        record_access_audit_receipt(actor=operator, role=role, action=ROLE_CREATE, old_value=None,
                                    new_value={"role_id": role.pk, "is_active": True}, reason="permission_change")
    for code in codes:
        if code not in existing:
            d = definitions[code]
            existing[code] = Permission.objects.using(DEFAULT_DB_ALIAS).create(
                service=service, permission_code=code, permission_name=d["permission_name"], module_name=d["module_name"],
                action_name=d["action_name"], description=d["description"])
            record_access_audit_receipt(actor=operator, permission=existing[code], action=PERMISSION_CREATE, old_value=None,
                                        new_value={"permission_id": existing[code].pk, "service_id": service.pk},
                                        reason="permission_change")
    bindings = list(RolePermission.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(role=role)
                    .order_by("role_permission_id"))
    wanted = {existing[code].pk for code in codes}
    if any(b.permission_id not in wanted or not b.is_active for b in bindings):
        raise RoleChangeUnavailable("The Technical Super Admin bindings differ from catalogue v2.")
    have = {b.permission_id for b in bindings}
    for code in codes:
        permission = existing[code]
        if permission.pk in have:
            continue
        if RolePermission.objects.using(DEFAULT_DB_ALIAS).filter(permission=permission).exclude(role=role).exists():
            raise RoleChangeUnavailable("A governance permission is bound to another role.")
        binding = RolePermission.objects.using(DEFAULT_DB_ALIAS).create(role=role, permission=permission, is_active=True,
                                                                        granted_by=operator)
        record_access_audit_receipt(actor=operator, role=role, permission=permission, action=BINDING_CREATE, old_value=None,
                                    new_value={"role_id": role.pk, "permission_id": permission.pk,
                                               "role_permission_id": binding.pk, "is_active": True},
                                    reason="permission_change")
    return role, codes


def _add(operator, target, role):
    _require_authorized(operator=operator, target=target)
    row = AccountRole.objects.using(DEFAULT_DB_ALIAS).create(account=target, role=role, assigned_by=operator)
    record_access_audit_receipt(actor=operator, target=target, role=role, action=FRAMEWORK_ASSIGN_ACTION, old_value=None,
                                new_value=snapshot(target.pk, role, row.pk), reason=ROLE_REASON)


def _remove(operator, target, role, assignment):
    _require_authorized(operator=operator, target=target)
    deleted, _ = AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(pk=assignment.pk, account_id=target.pk,
                                                                 role_id=role.pk).delete()
    if deleted != 1:
        raise RoleChangeUnavailable("The role assignment could not be changed.")
    record_access_audit_receipt(actor=operator, target=target, role=role, action=FRAMEWORK_REVOKE_ACTION,
                                old_value=snapshot(target.pk, role, assignment.pk), new_value=None, reason=ROLE_REASON)


def configure_role(*, operation, operator_school_id, operator_password, target_id, confirmation):
    """Run one protected framework role change; returns a data-free result or raises a fixed refusal.

    It runs in a fresh context, so the mutators' authorization (set only after every gate and the operator's
    re-authentication) can never outlive this call or leak to its caller."""
    return contextvars.copy_context().run(
        _configure_role, operation=operation, operator_school_id=operator_school_id,
        operator_password=operator_password, target_id=target_id, confirmation=confirmation)


def _configure_role(*, operation, operator_school_id, operator_password, target_id, confirmation):
    if operation not in OPERATIONS:
        raise RoleChangeUnavailable("Unknown operation.")
    if type(target_id) is not int or not 1 <= target_id <= 2_147_483_647:
        raise RoleChangeDenied("An existing account is required.")
    if confirmation != confirmation_for(operation, target_id):
        raise RoleChangeUnavailable("The exact confirmation for this operation and account is required.")
    target_kind = _require_approved_target()
    refuse_while_protected_writer_enabled()
    with writer_atomic():
        require_mysql_read_committed()
        # WF-03.01 R-1 K-5 (owner-authorized 19 Nov 2026): lock the shared service rows BEFORE the operator's
        # account, in lock_state's order, so this procedure and the P3B/P3D/P4 snapshot (which may lock other
        # account rows through its joins) never wait on each other. A lock is not authentication: the operator
        # is still authenticated and authorized below, and lock_state re-locks and validates the same rows.
        list(Service.objects.using(DEFAULT_DB_ALIAS).select_for_update()
             .filter(service_code__in=["access_control", "accounts"]).order_by("service_id").values_list("pk", flat=True))
        operator = _authenticate_operator(operator_school_id, operator_password, target_kind)
        _AUTHORIZED.set({"operator": operator.pk, "target": target_id})  # this call's own context only
        if operator.pk == target_id:
            raise RoleChangeConflict("protected_account")
        services, accounts, assignments, held = lock_state([operator.pk, target_id])
        target = accounts[target_id]
        if not is_eligible_account(target):
            raise RoleChangeDenied("The account is not an eligible Workspace account.")
        target_roles = held[target_id]
        admin = role_row(ADMIN)
        if admin is None or not admin.is_active:
            raise RoleChangeUnavailable("The School Admin role is unavailable.")
        current = {a.role_id: a for a in assignments if a.account_id == target_id}

        if operation == "grant-school-admin":
            if ADMIN in target_roles:
                raise RoleChangeConflict("state_changed")
            if INSTRUCTOR not in target_roles:
                raise RoleChangeConflict("not_eligible")
            _add(operator, target, admin)
        elif operation == "revoke-school-admin":
            if admin.pk not in current:
                raise RoleChangeConflict("state_changed")
            refusal = admin_revocation_refusal(target, target_roles)
            if refusal:
                raise RoleChangeConflict(refusal)
            _remove(operator, target, admin, current[admin.pk])
        elif operation == "grant-technical-super-admin":
            if TECHNICAL in target_roles:
                raise RoleChangeConflict("state_changed")
            if INSTRUCTOR not in target_roles:
                raise RoleChangeConflict("not_eligible")
            technical, codes = _ensure_governance(operator, services)
            if ADMIN not in target_roles:
                _add(operator, target, admin)
            _add(operator, target, technical)
            target.refresh_from_db()
            if not all(has_technical_authority(target, code) for code in codes):
                # For example an account-level Deny on a governance code: refuse and roll everything back.
                raise RoleChangeConflict("not_eligible")
        else:  # revoke-technical-super-admin
            technical = role_row(TECHNICAL)
            if technical is None or technical.pk not in current:
                raise RoleChangeConflict("state_changed")
            if not effective_holders([ADMIN, TECHNICAL], excluding=target_id).exists():
                raise RoleChangeConflict("last_technical_super_admin")
            _remove(operator, target, technical, current[technical.pk])  # Admin and Instructor are kept
        # D-83 / SR-1: exactly one advance per successful operation (a Technical Super Admin grant may add two
        # roles); lock_state already holds the target's row lock, so no lock is added to the order.
        session_revocation.advance(target_id)
    return {"account_id": target_id, "operation": operation}
