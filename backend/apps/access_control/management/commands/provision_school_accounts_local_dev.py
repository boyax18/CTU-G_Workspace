"""WF-02.05 stage 3: owner-authorized LOCAL DEVELOPMENT companion to P1/P2/P4 for exactly three codes.

accounts.school_accounts.read, .suspend and .activate, bound only to the existing Admin role, exactly
as catalogue v2 defines them. Follows the P1/P2/P4 principles: the named local database or the
disposable test database only, an exact confirmation per phase, the shared governance lock, one
durable transaction per phase, a named Approved application Admin as actor, an existing complete
registration-review release (P1, P2 and P4 receipts) as precondition, exact allowlists, append-only
receipts for every row, verify-only re-runs and no automatic repair of partial state.

Phases (each needs --apply and its exact confirmation; --phase verify is read-only):
  metadata  create the three permission definitions          (3 receipts)
  bindings  stage three INACTIVE Admin bindings               (3 receipts)
  activate  activate exactly those three bindings             (3 receipts)

Never creates services, roles, role assignments or account overrides, never touches any other code,
never grants Access Control Management authority and never runs in production settings.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction

from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.catalogue.validation_v2 import validate_manifest
from apps.access_control.management.commands import (
    exercise_registration_review_activation_recovery_test_only as p3b,
    init_registration_review_inactive_bindings_local_dev as p2,
    init_registration_review_metadata_local_dev as p1,
)
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.services import has_permission

CODES = ("accounts.school_accounts.read", "accounts.school_accounts.suspend", "accounts.school_accounts.activate")
SERVICE_CODE = "accounts"
EVENTS = {
    "metadata": "workspace.school_accounts.permission.create",
    "bindings": "workspace.school_accounts.role_binding.stage",
    "activate": "workspace.school_accounts.role_binding.activate",
}
PHASES = tuple(EVENTS)
LOCK_NAME = p1.LOCK_NAME  # serialize with every registration-review governance operation
DEV_CONFIRM = {phase: f"ctug_workspace:WF-02.05:S3:{phase.upper()}" for phase in PHASES}
TEST_CONFIRM = {phase: f"WF-02.05:DISPOSABLE-TEST:S3:{phase.upper()}" for phase in PHASES}


class SchoolAccountsProvisionRefused(RuntimeError):
    """The phase is unsafe or does not match the exact authorized local scope."""


def catalogue_definitions():
    """Exact definitions and Admin-only default bindings from the pinned, validated catalogue v2."""
    try:
        data = validate_manifest().data
    except Exception as exc:
        raise SchoolAccountsProvisionRefused("Catalogue v2 failed validation.") from exc
    definitions = {p["permission_code"]: dict(p) for p in data["permissions"] if p["permission_code"] in CODES}
    bindings = {}
    for binding in data["default_bindings"]:
        if binding["permission_code"] in CODES:
            bindings.setdefault(binding["permission_code"], set()).add(binding["role_name"])
    blocked = {b["permission_code"] for b in data["blocked_permissions"]}
    if (set(definitions) != set(CODES) or blocked & set(CODES)
            or any(bindings.get(code) != {"Admin"} for code in CODES)
            or any(d["service_code"] != SERVICE_CODE or d["readiness"] != "P" or d["scope"] != "SCHOOL"
                   or d["grant_protection"] != "GOV" for d in definitions.values())):
        raise SchoolAccountsProvisionRefused("Catalogue v2 no longer defines exactly these Admin-only codes.")
    return definitions


def _target(phase, confirmation):
    module = settings.SETTINGS_MODULE
    if module == "config.test_settings":
        expected, registration_confirm = TEST_CONFIRM.get(phase), p1.TEST_CONFIRM
    elif module == "config.settings":
        expected, registration_confirm = DEV_CONFIRM.get(phase), p1.DEV_CONFIRM
    else:
        raise SchoolAccountsProvisionRefused("Only the local development or disposable test configuration is allowed.")
    if expected is None or confirmation != expected:
        raise SchoolAccountsProvisionRefused("The exact confirmation for this phase is required.")
    if getattr(settings, "WORKSPACE_ACCOUNT_STATUS_ENABLED", False) is not False:
        raise SchoolAccountsProvisionRefused("The account-status switch must be off in the provisioning settings.")
    try:
        # One alias, local MySQL host, ctug_workspace (DEBUG) or the disposable test DB, READ COMMITTED,
        # registration-review flags off and no unexpected review or account-status route mounted.
        return p1._target(registration_confirm)
    except Exception as exc:
        raise SchoolAccountsProvisionRefused("The local database target is not safe.") from exc


def _registration_release(actor):
    """Precondition: the registration-review P1/P2/P4 release is complete and attributable."""
    services = {s.service_code: s for s in Service.objects.select_for_update().filter(service_code__in=p1.SERVICE_CODES)}
    registration = {p.permission_code: p for p in Permission.objects.select_for_update()
                    .filter(permission_code__in=p1.PERMISSION_CODES)}
    if (set(services) != set(p1.SERVICE_CODES) or not all(s.is_active for s in services.values())
            or set(registration) != set(p1.PERMISSION_CODES)):
        raise SchoolAccountsProvisionRefused("The registration-review release (P1/P4) is incomplete.")
    if (AccessAuditLog.objects.filter(action__in=(p1.SERVICE_EVENT, p1.PERMISSION_EVENT)).count() != 5
            or AccessAuditLog.objects.filter(action=p2.EVENT).count() != 3
            or AccessAuditLog.objects.filter(action=p3b.SERVICE_ACTIVATE).count() != 2
            or AccessAuditLog.objects.filter(action=p3b.BINDING_ACTIVATE).count() != 3
            or AccessAuditLog.objects.filter(action__in=(p3b.SERVICE_DEACTIVATE, p3b.BINDING_DEACTIVATE)).exists()):
        raise SchoolAccountsProvisionRefused("P1, P2 and P4 governance receipts are missing or compensated.")
    if not AccessAuditLog.objects.filter(action__in=(p1.SERVICE_EVENT, p1.PERMISSION_EVENT), actor_account_id=actor.pk).exists():
        raise SchoolAccountsProvisionRefused("The actor is not the attributed registration-review operator.")
    return services[SERVICE_CODE]


def _matches(row, definition, service):
    return (row.service_id == service.pk and row.permission_code == definition["permission_code"]
            and row.permission_name == definition["permission_name"] and row.module_name == definition["module_name"]
            and row.action_name == definition["action_name"] and row.description == definition["description"])


def _receipts(event):
    return list(AccessAuditLog.objects.select_for_update().filter(action=event).order_by("access_audit_log_id"))


def _verify_metadata(permissions, definitions, service, actor):
    if set(permissions) != set(CODES) or not all(_matches(permissions[c], definitions[c], service) for c in CODES):
        raise SchoolAccountsProvisionRefused("Permission definitions are partial or differ from catalogue v2.")
    logs = _receipts(EVENTS["metadata"])
    expected = {(p.pk, p.service_id) for p in permissions.values()}
    found = {(log.permission_id, (log.new_value or {}).get("service_id")) for log in logs}
    if (len(logs) != 3 or found != expected
            or any(log.actor_account_id != actor.pk or log.target_account_id is not None or log.role_id is not None
                   or log.old_value is not None or log.reason != "permission_change"
                   or log.new_value != {"permission_id": log.permission_id, "service_id": service.pk} for log in logs)):
        raise SchoolAccountsProvisionRefused("Metadata receipts are missing, duplicated or differ.")


def _verify_bindings(bindings, permissions, admin, actor, active):
    if (len(bindings) != 3 or {b.permission_id for b in bindings} != {p.pk for p in permissions.values()}
            or any(b.role_id != admin.pk or b.granted_by_id != actor.pk or b.is_active is not active for b in bindings)):
        raise SchoolAccountsProvisionRefused("Role bindings are partial, foreign, unattributed or in the wrong state.")
    by_permission = {b.permission_id: b for b in bindings}
    logs = _receipts(EVENTS["bindings"])
    if (len(logs) != 3 or {log.permission_id for log in logs} != set(by_permission)
            or any(log.actor_account_id != actor.pk or log.role_id != admin.pk or log.target_account_id is not None
                   or log.old_value is not None or log.reason != "permission_change"
                   or log.new_value != {"role_id": admin.pk, "permission_id": log.permission_id,
                                        "role_permission_id": by_permission[log.permission_id].pk, "is_active": False}
                   for log in logs)):
        raise SchoolAccountsProvisionRefused("Binding receipts are missing, duplicated or differ.")
    logs = _receipts(EVENTS["activate"])
    if not active:
        if logs:
            raise SchoolAccountsProvisionRefused("Activation receipts exist for inactive bindings.")
        return
    if (len(logs) != 3 or {log.permission_id for log in logs} != set(by_permission)
            or any(log.actor_account_id != actor.pk or log.role_id != admin.pk or log.reason != "permission_change"
                   or log.old_value != {"role_permission_id": by_permission[log.permission_id].pk, "is_active": False}
                   or log.new_value != {"role_permission_id": by_permission[log.permission_id].pk, "is_active": True}
                   for log in logs)):
        raise SchoolAccountsProvisionRefused("Activation receipts are missing, duplicated or differ.")


def _snapshot_outside_scope(scope_ids):
    """Everything this command must never change."""
    return (
        tuple(Service.objects.order_by("pk").values_list("pk", "service_code", "is_active")),
        tuple(Role.objects.order_by("pk").values_list("pk", "role_name", "is_active")),
        tuple(Permission.objects.exclude(pk__in=scope_ids).order_by("pk").values_list("pk", "permission_code")),
        tuple(RolePermission.objects.exclude(permission_id__in=scope_ids).order_by("pk")
              .values_list("pk", "role_id", "permission_id", "is_active")),
        tuple(AccountRole.objects.order_by("pk").values_list("pk", "account_id", "role_id")),
        tuple(AccountPermission.objects.order_by("pk").values_list("pk", "account_id", "permission_id", "effect", "is_active")),
    )


def run(*, phase, actor_account_id, confirmation=None, apply=False):
    if phase not in PHASES + ("verify",):
        raise SchoolAccountsProvisionRefused("Unknown phase.")
    definitions = catalogue_definitions()
    db = _target("metadata" if phase == "verify" else phase,
                 (TEST_CONFIRM if settings.SETTINGS_MODULE == "config.test_settings" else DEV_CONFIRM)["metadata"]
                 if phase == "verify" else confirmation)
    if phase != "verify" and not apply:
        raise SchoolAccountsProvisionRefused("No implicit writes: pass --apply with the exact confirmation.")
    with db.cursor() as cursor:
        cursor.execute("SELECT GET_LOCK(%s, 0)", [LOCK_NAME])
        if cursor.fetchone()[0] != 1:
            raise SchoolAccountsProvisionRefused("Another governance operation is running.")
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            # WF-03.01 K-4 (owner-authorized 19 Nov 2026, Option A under R-1): lock the shared service rows
            # FIRST, in service_id order, like every protected snapshot and role change; then as before.
            list(Service.objects.select_for_update().order_by("service_id"))
            try:
                admin = Role.objects.select_for_update().get(role_name="Admin", is_active=True)
            except (Role.DoesNotExist, Role.MultipleObjectsReturned) as exc:
                raise SchoolAccountsProvisionRefused("Exactly one active Admin role is required.") from exc
            try:
                actor = p1._actor(actor_account_id)
            except Exception as exc:
                raise SchoolAccountsProvisionRefused("A persisted, active, approved application Admin is required.") from exc
            service = _registration_release(actor)
            permissions = {p.permission_code: p for p in Permission.objects.select_for_update()
                           .filter(permission_code__in=CODES).order_by("pk")}
            scope_ids = [p.pk for p in permissions.values()]
            if AccountPermission.objects.filter(permission_id__in=scope_ids, effect="Grant").exists():
                raise SchoolAccountsProvisionRefused("Account-level Grants for these codes are unauthorized.")
            bindings = list(RolePermission.objects.select_for_update().filter(permission_id__in=scope_ids).order_by("pk"))
            before = _snapshot_outside_scope(scope_ids)
            result = "VERIFIED" if phase == "verify" else "ALREADY_COMPLETE"

            if phase == "metadata" and not permissions:
                if _receipts(EVENTS["metadata"]):
                    raise SchoolAccountsProvisionRefused("Orphaned metadata receipts require manual review.")
                for code in CODES:
                    d = definitions[code]
                    permission = Permission.objects.create(
                        service=service, permission_code=code, permission_name=d["permission_name"],
                        module_name=d["module_name"], action_name=d["action_name"], description=d["description"])
                    record_access_audit_receipt(actor=actor, permission=permission, action=EVENTS["metadata"],
                                                old_value=None, new_value={"permission_id": permission.pk, "service_id": service.pk},
                                                reason="permission_change")
                permissions = {p.permission_code: p for p in Permission.objects.filter(permission_code__in=CODES)}
                result = "CREATED"
            _verify_metadata(permissions, definitions, service, actor)

            if phase == "bindings" and not bindings:
                if _receipts(EVENTS["bindings"]) or _receipts(EVENTS["activate"]):
                    raise SchoolAccountsProvisionRefused("Orphaned binding receipts require manual review.")
                for code in CODES:
                    permission = permissions[code]
                    binding = RolePermission.objects.create(role=admin, permission=permission, is_active=False, granted_by=actor)
                    record_access_audit_receipt(actor=actor, role=admin, permission=permission, action=EVENTS["bindings"],
                                                old_value=None, new_value={"role_id": admin.pk, "permission_id": permission.pk,
                                                                           "role_permission_id": binding.pk, "is_active": False},
                                                reason="permission_change")
                bindings = list(RolePermission.objects.filter(permission_id__in=[p.pk for p in permissions.values()]).order_by("pk"))
                result = "CREATED"
            if bindings or phase in ("bindings", "activate"):
                if not bindings:
                    raise SchoolAccountsProvisionRefused("Inactive bindings must be staged first.")
                any_active = any(b.is_active for b in bindings)
                if phase == "activate" and not any_active:
                    _verify_bindings(bindings, permissions, admin, actor, active=False)
                    for binding in bindings:
                        RolePermission.objects.filter(pk=binding.pk, is_active=False).update(is_active=True)
                        record_access_audit_receipt(actor=actor, role=admin, permission=binding.permission, action=EVENTS["activate"],
                                                    old_value={"role_permission_id": binding.pk, "is_active": False},
                                                    new_value={"role_permission_id": binding.pk, "is_active": True},
                                                    reason="permission_change")
                    bindings = list(RolePermission.objects.filter(pk__in=[b.pk for b in bindings]).order_by("pk"))
                    result = "ACTIVATED"
                all_active = all(b.is_active for b in bindings)
                if any(b.is_active for b in bindings) and not all_active:
                    raise SchoolAccountsProvisionRefused("Partially active bindings are refused; no automatic repair.")
                _verify_bindings(bindings, permissions, admin, actor, active=all_active)
                if all_active:
                    # Effective result: the actor gains exactly these codes unless an own Deny applies.
                    for code in CODES:
                        denied = AccountPermission.objects.filter(account=actor, permission=permissions[code],
                                                                  effect="Deny", is_active=True).exists()
                        if has_permission(actor, code) is denied:
                            raise SchoolAccountsProvisionRefused("Effective Admin authority does not match.")

            if _snapshot_outside_scope([p.pk for p in permissions.values()]) != before:
                raise SchoolAccountsProvisionRefused("State outside the three authorized codes changed.")
            catalogue_definitions()  # the pinned catalogue must still match before commit
        return result
    finally:
        with db.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", [LOCK_NAME])


class Command(BaseCommand):
    help = "LOCAL DEV ONLY: governed provisioning of accounts.school_accounts.read/.suspend/.activate for Admin."

    def add_arguments(self, parser):
        parser.add_argument("--phase", choices=PHASES + ("verify",), required=True)
        parser.add_argument("--actor-account-id", type=int, required=True)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--confirm", default="")

    def handle(self, *args, **options):
        try:
            result = run(phase=options["phase"], actor_account_id=options["actor_account_id"],
                         confirmation=options["confirm"], apply=options["apply"])
        except Exception as exc:
            raise CommandError("WF-02.05 S3: refused or rolled back; no success reported. "
                               "Inspect the current state before retrying.") from exc
        self.stdout.write(f"WF-02.05 S3 {options['phase']}: {result}; codes=3; role=Admin; no other change")
