"""Owner-authorized LOCAL DEVELOPMENT P1 metadata initializer; never a general grant tool.

No flags, service activation, role grants, account overrides, or URL changes.
The frozen AR-6C7C5 draft remains a blocked proposal and is checked only for
catalogue provenance; it is NOT used as proof of execution authorization.
"""

import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections, transaction
from django.urls import NoReverseMatch, reverse

from apps.accounts.models import Account
from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission,
    Role, RolePermission, Service,
)
from scripts.validate_registration_review_execution_contract import (
    load_local, verify_contract,
)

SERVICE_CODES = ("accounts", "access_control")
PERMISSION_CODES = (
    "accounts.registration_requests.read",
    "accounts.registration_requests.approve",
    "accounts.registration_requests.reject",
)
SERVICE_EVENT = "workspace.review.service.create"
PERMISSION_EVENT = "workspace.review.permission.create"
LOCK_NAME = "ctug_review_p1_metadata_v1"
TEST_PATTERN = re.compile(r"test_ctug_registration_[0-9a-f]{16}\Z")
DEV_CONFIRM = "ctug_workspace:AR-6C7D7:P1:METADATA-ONLY"
TEST_CONFIRM = "AR-6C7D7:DISPOSABLE-TEST:P1"


class MetadataRefused(RuntimeError):
    pass


def _expected():
    try:
        contract, profile, source, raw = load_local()
        result = verify_contract(contract, profile, source, raw)
        if not result["all_gates_blocked"]:
            raise MetadataRefused("Frozen source gates are no longer blocked.")
        services = {x["service_code"]: x for x in source["services"]
                    if x.get("service_code") in SERVICE_CODES}
        permissions = {x["permission_code"]: x for x in source["permissions"]
                       if x.get("permission_code") in PERMISSION_CODES}
        if set(services) != set(SERVICE_CODES) or set(permissions) != set(PERMISSION_CODES):
            raise MetadataRefused("Source differs from the exact P1 allowlist.")
        return services, permissions
    except (KeyError, ValueError, OSError, TypeError) as exc:
        raise MetadataRefused("Pinned review catalogue failed validation.") from exc


def _target(confirm):
    if DEFAULT_DB_ALIAS != "default" or list(connections) != ["default"]:
        raise MetadataRefused("Only one primary database alias is allowed.")
    db = connections[DEFAULT_DB_ALIAS]
    cfg = db.settings_dict
    if (db.vendor != "mysql" or cfg.get("ENGINE") != "django.db.backends.mysql"
            or cfg.get("HOST") not in {"localhost", "127.0.0.1", "::1"}):
        raise MetadataRefused("A local MySQL database is required.")
    name = cfg.get("NAME")
    module = settings.SETTINGS_MODULE
    if (module == "config.test_settings"
            and isinstance(name, str) and TEST_PATTERN.fullmatch(name)
            and getattr(settings, "REGISTRATION_TEST_DATABASE", None) == name
            and cfg.get("TEST", {}).get("NAME") == name
            and getattr(settings, "TEST_RUNNER", None) == "config.test_runner.IsolatedMySQLRunner"):
        expected_confirmation = TEST_CONFIRM
    elif (module == "config.settings" and settings.DEBUG is True
          and name == "ctug_workspace" and not getattr(settings, "REGISTRATION_TEST_DATABASE", None)):
        expected_confirmation = DEV_CONFIRM
    else:
        raise MetadataRefused("Only the named local development DB or disposable MySQL test DB is permitted.")
    if confirm != expected_confirmation:
        raise MetadataRefused("The exact phase-1 database confirmation is required.")
    if (getattr(settings, "WORKSPACE_REGISTRATION_REVIEW_API_ENABLED", False) is not False
            or getattr(settings, "WORKSPACE_REGISTRATION_APPROVAL_ENABLED", False) is not False):
        raise MetadataRefused("Registration Review backend flags must both remain False.")
    try:
        route = reverse("registration-review-pending")
    except NoReverseMatch:
        pass
    else:
        raise MetadataRefused("Registration Review URL is already mounted: refuse P1.")
    with db.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        selected = cursor.fetchone()[0]
    if selected != name or db.isolation_level != "read committed":
        raise MetadataRefused("Connected database or transaction isolation differs from the reviewed target.")
    return db


def _actor(account_id):
    if type(account_id) is not int or not 1 <= account_id <= 2_147_483_647:
        raise MetadataRefused("Persisted numeric application Admin account ID required.")
    try:
        actor = Account.objects.select_for_update().get(pk=account_id)
    except Account.DoesNotExist as exc:
        raise MetadataRefused("Audit actor not found.") from exc
    if (actor.is_staff or actor.is_superuser or not actor.is_active
            or actor.request_status != "Approved"
            or not AccountRole.objects.filter(account_id=account_id,
                role__role_name="Admin", role__is_active=True).exists()):
        raise MetadataRefused("Audit actor must be an active approved Workspace Admin, not Django staff.")
    return actor


def _matches_service(row, expected):
    return (row.service_code == expected["service_code"]
            and row.service_name == expected["service_name"]
            and row.description == expected["description"]
            and row.is_active is False)


def _matches_permission(row, expected, service):
    return (row.service_id == service.pk
            and row.permission_code == expected["permission_code"]
            and row.permission_name == expected["permission_name"]
            and row.module_name == expected["module_name"]
            and row.action_name == expected["action_name"]
            and row.description == expected["description"])


def _verify_prior_audits(services, permissions, actor):
    rows = list(AccessAuditLog.objects.select_for_update()
                .filter(action__in=(SERVICE_EVENT, PERMISSION_EVENT))
                .order_by("access_audit_log_id"))
    if len(rows) != 5:
        raise MetadataRefused("Complete metadata must have exactly five attributable operational audit events.")
    expected = set()
    for row in services.values():
        expected.add((SERVICE_EVENT, row.pk))
    for row in permissions.values():
        expected.add((PERMISSION_EVENT, row.pk))
    found = set()
    for row in rows:
        if (row.actor_account_id != actor.pk or row.target_account_id is not None
                or row.role_id is not None or row.old_value is not None
                or row.reason != "permission_change"):
            raise MetadataRefused("Metadata audit actor or payload differs.")
        if row.action == SERVICE_EVENT:
            obj_id = row.new_value.get("service_id") if type(row.new_value) is dict else None
            if (obj_id not in [s.pk for s in services.values()]
                    or row.permission_id is not None
                    or row.new_value != {"service_id": obj_id, "is_active": False}):
                raise MetadataRefused("Service audit state differs.")
        elif row.action == PERMISSION_EVENT:
            obj_id = row.new_value.get("permission_id") if type(row.new_value) is dict else None
            obj = next((p for p in permissions.values() if p.pk == obj_id), None)
            if (obj is None or row.permission_id != obj_id
                    or row.new_value != {"permission_id": obj_id, "service_id": obj.service_id}):
                raise MetadataRefused("Permission audit state differs.")
        else:
            raise MetadataRefused("Unexpected operational audit action.")
        key = (row.action, obj_id)
        if key in found:
            raise MetadataRefused("Duplicated operational audit event.")
        found.add(key)
    if found != expected:
        raise MetadataRefused("Operational audit coverage is incomplete.")


def _apply_phase_one(*, actor_account_id, confirmation):
    """Commit only exact P1 metadata and five audits; refuse partial state."""
    service_defs, permission_defs = _expected()
    db = _target(confirmation)
    with db.cursor() as cursor:
        cursor.execute("SELECT GET_LOCK(%s, 0)", [LOCK_NAME])
        if cursor.fetchone()[0] != 1:
            raise MetadataRefused("Another P1 initializer may be running.")
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            try:
                admin = Role.objects.select_for_update().get(role_name="Admin", is_active=True)
            except (Role.DoesNotExist, Role.MultipleObjectsReturned) as exc:
                raise MetadataRefused("Exactly one active Admin role is required.") from exc
            actor = _actor(actor_account_id)
            if (not AccountRole.objects.filter(account_id=actor.pk, role_id=admin.pk).exists()
                    or RolePermission.objects.exists() or AccountPermission.objects.exists()):
                raise MetadataRefused("Existing grants, overrides or missing Admin assignment block P1.")
            services = {s.service_code: s for s in Service.objects.select_for_update().all()}
            permissions = {p.permission_code: p for p in Permission.objects.select_for_update().all()}
            if any(key not in SERVICE_CODES for key in services) or any(key not in PERMISSION_CODES for key in permissions):
                raise MetadataRefused("Unexpected catalogue rows exist; refusing P1.")
            if not services and not permissions:
                if AccessAuditLog.objects.filter(action__in=(SERVICE_EVENT, PERMISSION_EVENT)).exists():
                    raise MetadataRefused("Orphaned P1 audit events block initialization.")
                for code in SERVICE_CODES:
                    src = service_defs[code]
                    service = Service.objects.create(
                        service_code=code, service_name=src["service_name"],
                        description=src["description"], is_active=False,
                    )
                    record_access_audit_receipt(
                        actor=actor, action=SERVICE_EVENT, old_value=None,
                        new_value={"service_id": service.pk, "is_active": False},
                        reason="permission_change",
                    )
                services = {s.service_code: s for s in Service.objects.select_for_update().all()}
                for code in PERMISSION_CODES:
                    src = permission_defs[code]
                    service = services[src["service_code"]]
                    permission = Permission.objects.create(
                        service=service, permission_code=code,
                        permission_name=src["permission_name"], module_name=src["module_name"],
                        action_name=src["action_name"], description=src["description"],
                    )
                    record_access_audit_receipt(
                        actor=actor, permission=permission, action=PERMISSION_EVENT,
                        old_value=None,
                        new_value={"permission_id": permission.pk, "service_id": service.pk},
                        reason="permission_change",
                    )
                result = "CREATED"
                permissions = {p.permission_code: p for p in Permission.objects.select_for_update().all()}
            else:
                result = "ALREADY_COMPLETE"
            if set(services) != set(SERVICE_CODES) or set(permissions) != set(PERMISSION_CODES):
                raise MetadataRefused("Partial P1 state is refused; no automatic repair.")
            for code, service in services.items():
                if not _matches_service(service, service_defs[code]):
                    raise MetadataRefused("Service metadata differs from the pinned proposal.")
            for code, permission in permissions.items():
                service = services[permission_defs[code]["service_code"]]
                if not _matches_permission(permission, permission_defs[code], service):
                    raise MetadataRefused("Permission metadata differs from the pinned proposal.")
            _verify_prior_audits(services, permissions, actor)
            if (RolePermission.objects.exists() or AccountPermission.objects.exists()
                    or not Role.objects.filter(pk=admin.pk, is_active=True).exists()):
                raise MetadataRefused("P1 changed protected authorization state.")
        return result
    finally:
        with db.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", [LOCK_NAME])


class Command(BaseCommand):
    help = "LOCAL DEV ONLY: explicit owner-authorized P1 metadata; NEVER grants or activates."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--actor-account-id", type=int)
        parser.add_argument("--confirm-local-dev-phase1", type=str)

    def handle(self, *args, **options):
        if not options["apply"]:
            raise CommandError("No default execution. Use existing read-only plan_registration_review_initialization first.")
        try:
            result = _apply_phase_one(
                actor_account_id=options["actor_account_id"],
                confirmation=options["confirm_local_dev_phase1"],
            )
        except Exception as exc:
            # Never echo DB internals, submitted values, or credentials in a CLI error.
            raise CommandError("Phase-1 metadata initialization refused or rolled back; no success reported.") from exc
        self.stdout.write(f"AR-6C7D7 P1: {result}; services=2 inactive; definitions=3; grants=0; activation=NO")
