"""WF-11.01 Academic Settings phase 1: owner-authorized LOCAL DEVELOPMENT provisioning (26 Nov 2026).

Exactly the reviewed phase-one minimum of the activation runbook ("Reviewed minimum for phase 1"):
services ``academic`` and ``clearance`` and five EXISTING pinned v2.2 definitions, each bound to the
existing ``Admin`` role only:

  academic.periods.manage  academic.courses.manage  academic.sections.manage
  academic.catalogue.read  clearance.subjects.manage

Follows the established P1/P2/P4 and WF-02.05 S3 principles: the named local database or the
disposable test database only, an exact confirmation per phase, the shared governance lock, one
durable transaction per phase, a named Approved application Admin as actor, exact allowlists from
the validated pinned catalogue, append-only receipts for every row, verify-only re-runs and no
automatic repair of partial state. Every Academic Settings feature switch must be OFF while it runs.

Phases (each needs --apply and its exact confirmation; --phase verify is read-only):
  metadata  create the two services INACTIVE and the five definitions      (7 receipts)
  bindings  stage five INACTIVE Admin bindings                             (5 receipts)
  activate  activate exactly those two services and five bindings          (7 receipts)

Never creates roles, role assignments, account overrides or role scopes; never changes another
service, permission or binding; never installs v2.3 (its own reviewed command does; phase 1 accepts a restated v2.3 definition only
with its exact receipt); never runs in production settings.
``academic.catalogue.read`` is pinned for Student, Instructor, Treasurer and Admin; phase one binds
it to Admin only, as reviewed.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction
from django.db.migrations.recorder import MigrationRecorder

from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.catalogue.validation_v2_2 import validate_catalogue
from apps.access_control.management.commands import init_registration_review_metadata_local_dev as p1
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountPermissionRoleScope, AccountRole, Permission, Role, RolePermission, Service,
)
from apps.access_control.services import has_permission
from apps.accounts.active_role_context import bind_role_scope, context_enabled

SERVICE_CODES = ("academic", "clearance")
CODES = ("academic.periods.manage", "academic.courses.manage", "academic.sections.manage",
         "academic.catalogue.read", "clearance.subjects.manage")
PINNED_V22_DIGEST = "192ba955d1dae06bfbdf574e52ef454390b9fd41b803f63778d1d220b6cd8c6d"
MIGRATIONS = (("academic", "0001_initial"), ("academic", "0002_audit_reason_note"),
              ("academic", "0003_academic_configuration"), ("finance", "0001_semester_fee_configuration"),
              ("academic", "0004_student_semester_onboarding"), ("clearance", "0001_semester_clearance"),
              ("finance", "0002_fee_obligation"))
ACADEMIC_SWITCHES = (
    "WORKSPACE_ACADEMIC_PERIODS_ENABLED", "WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED",
    "WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED", "WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED",
    "WORKSPACE_ACADEMIC_CURRICULUM_WRITES_ENABLED", "WORKSPACE_ACADEMIC_OFFERING_WRITES_ENABLED",
    "WORKSPACE_ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED", "WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED",
    "WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED", "WORKSPACE_ACADEMIC_CATALOGUE_ENABLED",
    "WORKSPACE_STUDENT_ONBOARDING_ENABLED", "WORKSPACE_STUDENT_ONBOARDING_FINALIZATION_ENABLED",
    "WORKSPACE_ENROLLMENT_VERIFICATION_ENABLED", "WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED",
)
EVENTS = {
    "service_create": "workspace.academic_settings.service.create",
    "permission_create": "workspace.academic_settings.permission.create",
    "binding_stage": "workspace.academic_settings.role_binding.stage",
    "service_activate": "workspace.academic_settings.service.activate",
    "binding_activate": "workspace.academic_settings.role_binding.activate",
}
PHASES = ("metadata", "bindings", "activate")
LOCK_NAME = p1.LOCK_NAME  # serialize with every registration-review / account governance operation
DEV_CONFIRM = {phase: f"ctug_workspace:WF-11.01:PHASE1:{phase.upper()}" for phase in PHASES}
TEST_CONFIRM = {phase: f"WF-11.01:DISPOSABLE-TEST:PHASE1:{phase.upper()}" for phase in PHASES}


class AcademicPhase1Refused(RuntimeError):
    """The phase is unsafe or does not match the exact authorized local scope."""


def catalogue_definitions():
    """Exact service and permission definitions from the validated pinned v2.2 catalogue chain."""
    try:
        validated = validate_catalogue()
    except Exception as exc:
        raise AcademicPhase1Refused("Pinned catalogue v2.2 failed validation.") from exc
    if validated.digest != PINNED_V22_DIGEST:
        raise AcademicPhase1Refused("Pinned catalogue v2.2 digest differs from the reviewed digest.")
    data = validated.data
    services = {s["service_code"]: dict(s) for s in data["services"] if s["service_code"] in SERVICE_CODES}
    definitions = {p["permission_code"]: dict(p) for p in data["permissions"] if p["permission_code"] in CODES}
    defaults = {}
    for binding in data["default_bindings"]:
        if binding["permission_code"] in CODES:
            defaults.setdefault(binding["permission_code"], set()).add(binding["role_name"])
    blocked = {b["permission_code"] for b in data["blocked_permissions"]}
    if (set(services) != set(SERVICE_CODES) or set(definitions) != set(CODES) or blocked & set(CODES)
            or any("Admin" not in defaults.get(code, set()) for code in CODES)
            or any(d["readiness"] != "P" or d["grant_protection"] != "ORD" for d in definitions.values())):
        raise AcademicPhase1Refused("Catalogue v2.2 no longer defines exactly these phase-one codes.")
    return services, definitions


def _target(phase, confirmation):
    module = settings.SETTINGS_MODULE
    if module == "config.test_settings":
        expected, registration_confirm = TEST_CONFIRM.get(phase), p1.TEST_CONFIRM
    elif module == "config.settings":
        expected, registration_confirm = DEV_CONFIRM.get(phase), p1.DEV_CONFIRM
    else:
        raise AcademicPhase1Refused("Only the local development or disposable test configuration is allowed.")
    if expected is None or confirmation != expected:
        raise AcademicPhase1Refused("The exact confirmation for this phase is required.")
    if any(getattr(settings, name, False) is not False for name in ACADEMIC_SWITCHES):
        raise AcademicPhase1Refused("Every Academic Settings switch must be off while provisioning.")
    if getattr(settings, "WORKSPACE_DEPLOYMENT_PROFILE", "local") != "local":
        raise AcademicPhase1Refused("Only the local deployment profile is allowed.")
    try:
        # One alias, local MySQL host, ctug_workspace (DEBUG) or the disposable test DB, READ COMMITTED,
        # registration-review flags off and no unexpected review route mounted.
        db = p1._target(registration_confirm)
    except Exception as exc:
        raise AcademicPhase1Refused("The local database target is not safe.") from exc
    applied = MigrationRecorder(db).applied_migrations()
    if any(key not in applied for key in MIGRATIONS):
        raise AcademicPhase1Refused("The seven Academic Settings migrations must be applied first.")
    return db


def _matches_service(row, definition, active):
    return (row.service_code == definition["service_code"] and row.service_name == definition["service_name"]
            and row.description == definition["description"] and row.is_active is active)


def _matches_permission(row, definition, service):
    return (row.service_id == service.pk and row.permission_code == definition["permission_code"]
            and row.permission_name == definition["permission_name"] and row.module_name == definition["module_name"]
            and row.action_name == definition["action_name"] and row.description == definition["description"])


def _receipts(event):
    return list(AccessAuditLog.objects.select_for_update().filter(action=event).order_by("access_audit_log_id"))


def _plain(log, actor):
    return (log.actor_account_id == actor.pk and log.target_account_id is None and log.reason == "permission_change")


def _restated(permissions, definitions):
    """Catalogue v2.3 restates two of these definitions; its text is accepted only with the exact receipt."""
    if not AccessAuditLog.objects.filter(action="workspace.academic_settings.v23.permission.restate").exists():
        return definitions
    from apps.access_control.management.commands import provision_academic_settings_v2_3_local_dev as v23
    try:
        return v23.effective_definitions(permissions, definitions)
    except Exception as exc:
        raise AcademicPhase1Refused("Restated v2.3 definitions are not exactly receipted.") from exc


def _verify_metadata(services, permissions, service_defs, definitions, actor, active):
    if set(services) != set(SERVICE_CODES) or set(permissions) != set(CODES):
        raise AcademicPhase1Refused("Services or definitions are partial.")
    definitions = _restated(permissions, definitions)
    if not all(_matches_service(services[c], service_defs[c], active) for c in SERVICE_CODES):
        raise AcademicPhase1Refused("Service rows differ from catalogue v2.2 or are in the wrong state.")
    if not all(_matches_permission(permissions[c], definitions[c], services[definitions[c]["service_code"]]) for c in CODES):
        raise AcademicPhase1Refused("Permission definitions differ from catalogue v2.2.")
    logs = _receipts(EVENTS["service_create"])
    if (len(logs) != 2 or {(log.new_value or {}).get("service_id") for log in logs} != {s.pk for s in services.values()}
            or any(not _plain(log, actor) or log.role_id is not None or log.permission_id is not None
                   or log.old_value is not None
                   or log.new_value != {"service_id": log.new_value.get("service_id"), "is_active": False} for log in logs)):
        raise AcademicPhase1Refused("Service receipts are missing, duplicated or differ.")
    logs = _receipts(EVENTS["permission_create"])
    expected = {(p.pk, p.service_id) for p in permissions.values()}
    if (len(logs) != 5 or {(log.permission_id, (log.new_value or {}).get("service_id")) for log in logs} != expected
            or any(not _plain(log, actor) or log.role_id is not None or log.old_value is not None
                   or log.new_value != {"permission_id": log.permission_id, "service_id": (log.new_value or {}).get("service_id")}
                   for log in logs)):
        raise AcademicPhase1Refused("Permission receipts are missing, duplicated or differ.")


def _verify_bindings(bindings, permissions, admin, actor, active):
    if (len(bindings) != 5 or {b.permission_id for b in bindings} != {p.pk for p in permissions.values()}
            or any(b.role_id != admin.pk or b.granted_by_id != actor.pk or b.is_active is not active for b in bindings)):
        raise AcademicPhase1Refused("Role bindings are partial, foreign, unattributed or in the wrong state.")
    by_permission = {b.permission_id: b for b in bindings}
    logs = _receipts(EVENTS["binding_stage"])
    if (len(logs) != 5 or {log.permission_id for log in logs} != set(by_permission)
            or any(not _plain(log, actor) or log.role_id != admin.pk or log.old_value is not None
                   or log.new_value != {"role_id": admin.pk, "permission_id": log.permission_id,
                                        "role_permission_id": by_permission[log.permission_id].pk, "is_active": False}
                   for log in logs)):
        raise AcademicPhase1Refused("Binding receipts are missing, duplicated or differ.")
    logs = _receipts(EVENTS["binding_activate"])
    if not active:
        if logs:
            raise AcademicPhase1Refused("Activation receipts exist for inactive bindings.")
        return
    if (len(logs) != 5 or {log.permission_id for log in logs} != set(by_permission)
            or any(not _plain(log, actor) or log.role_id != admin.pk
                   or log.old_value != {"role_permission_id": by_permission[log.permission_id].pk, "is_active": False}
                   or log.new_value != {"role_permission_id": by_permission[log.permission_id].pk, "is_active": True}
                   for log in logs)):
        raise AcademicPhase1Refused("Binding activation receipts are missing, duplicated or differ.")


def _verify_service_activation(services, actor):
    logs = _receipts(EVENTS["service_activate"])
    ids = {s.pk for s in services.values()}
    if (len(logs) != 2 or {(log.new_value or {}).get("service_id") for log in logs} != ids
            or any(not _plain(log, actor) or log.role_id is not None or log.permission_id is not None
                   or log.old_value != {"service_id": log.new_value.get("service_id"), "is_active": False}
                   or log.new_value != {"service_id": log.new_value.get("service_id"), "is_active": True} for log in logs)):
        raise AcademicPhase1Refused("Service activation receipts are missing, duplicated or differ.")


def _snapshot_outside_scope(service_ids, permission_ids, admin_id):
    """Everything this command must never change: other services, roles, definitions and bindings (including
    non-Admin bindings of these codes), every role assignment, every account Grant/Deny and every Grant role scope."""
    return (
        tuple(Service.objects.exclude(pk__in=service_ids).order_by("pk").values_list("pk", "service_code", "is_active")),
        tuple(Role.objects.order_by("pk").values_list("pk", "role_name", "is_active")),
        tuple(Permission.objects.exclude(pk__in=permission_ids).order_by("pk").values_list("pk", "permission_code", "service_id")),
        tuple(RolePermission.objects.exclude(permission_id__in=permission_ids, role_id=admin_id).order_by("pk")
              .values_list("pk", "role_id", "permission_id", "is_active")),
        tuple(AccountRole.objects.order_by("pk").values_list("pk", "account_id", "role_id")),
        tuple(AccountPermission.objects.order_by("pk").values_list("pk", "account_id", "permission_id", "effect", "is_active")),
        tuple(AccountPermissionRoleScope.objects.order_by("pk").values_list("account_permission_id", "role_id")),
    )


def _effective(actor, admin, permissions):
    """Post-activation check: the actor holds exactly these codes unless an own active Deny applies."""
    for code in CODES:
        denied = AccountPermission.objects.filter(account=actor, permission=permissions[code], effect="Deny",
                                                  is_active=True).exists()
        if context_enabled():
            with bind_role_scope(actor.pk, admin.pk):
                granted = has_permission(actor, code)
        else:
            granted = has_permission(actor, code)
        if granted is denied:
            raise AcademicPhase1Refused("Effective Admin authority does not match the provisioned bindings.")


def run(*, phase, actor_account_id, confirmation=None, apply=False):
    if phase not in PHASES + ("verify",):
        raise AcademicPhase1Refused("Unknown phase.")
    service_defs, definitions = catalogue_definitions()
    confirms = TEST_CONFIRM if settings.SETTINGS_MODULE == "config.test_settings" else DEV_CONFIRM
    db = _target("metadata" if phase == "verify" else phase, confirms["metadata"] if phase == "verify" else confirmation)
    if phase != "verify" and not apply:
        raise AcademicPhase1Refused("No implicit writes: pass --apply with the exact confirmation.")
    with db.cursor() as cursor:
        cursor.execute("SELECT GET_LOCK(%s, 0)", [LOCK_NAME])
        if cursor.fetchone()[0] != 1:
            raise AcademicPhase1Refused("Another governance operation is running.")
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            # Shared lock order: every service row first, in service_id order.
            list(Service.objects.select_for_update().order_by("service_id"))
            try:
                admin = Role.objects.select_for_update().get(role_name="Admin", is_active=True)
            except (Role.DoesNotExist, Role.MultipleObjectsReturned) as exc:
                raise AcademicPhase1Refused("Exactly one active Admin role is required.") from exc
            try:
                actor = p1._actor(actor_account_id)
            except Exception as exc:
                raise AcademicPhase1Refused("A persisted, active, approved application Admin is required.") from exc
            services = {s.service_code: s for s in Service.objects.select_for_update().filter(service_code__in=SERVICE_CODES)}
            permissions = {p.permission_code: p for p in Permission.objects.select_for_update()
                           .filter(permission_code__in=CODES).order_by("pk")}
            permission_ids = [p.pk for p in permissions.values()]
            # Account-level Grants for these codes are not part of the reviewed scope; Denies are preserved and win.
            if AccountPermission.objects.filter(permission_id__in=permission_ids, effect="Grant").exists():
                raise AcademicPhase1Refused("Account-level Grants for these codes are unauthorized.")
            bindings = list(RolePermission.objects.select_for_update().filter(permission_id__in=permission_ids, role=admin)
                            .order_by("pk"))
            others = list(RolePermission.objects.select_for_update().filter(permission_id__in=permission_ids)
                          .exclude(role=admin).order_by("pk"))
            if others:
                # Only the exact, receipted phase-two current-period bindings may exist besides Admin's.
                from apps.access_control.management.commands import provision_academic_settings_phase2_local_dev as phase2
                try:
                    phase2.recognised_by_phase_one(others)
                except Exception as exc:
                    raise AcademicPhase1Refused("Foreign bindings for these codes exist; no automatic repair.") from exc
            before = _snapshot_outside_scope([s.pk for s in services.values()], permission_ids, admin.pk)
            result = "VERIFIED" if phase == "verify" else "ALREADY_COMPLETE"

            if phase == "metadata" and not services and not permissions:
                if _receipts(EVENTS["service_create"]) or _receipts(EVENTS["permission_create"]):
                    raise AcademicPhase1Refused("Orphaned metadata receipts require manual review.")
                for code in SERVICE_CODES:
                    d = service_defs[code]
                    service = Service.objects.create(service_code=code, service_name=d["service_name"],
                                                     description=d["description"], is_active=False)
                    record_access_audit_receipt(actor=actor, action=EVENTS["service_create"], old_value=None,
                                                new_value={"service_id": service.pk, "is_active": False},
                                                reason="permission_change")
                services = {s.service_code: s for s in Service.objects.filter(service_code__in=SERVICE_CODES)}
                for code in CODES:
                    d = definitions[code]
                    service = services[d["service_code"]]
                    permission = Permission.objects.create(
                        service=service, permission_code=code, permission_name=d["permission_name"],
                        module_name=d["module_name"], action_name=d["action_name"], description=d["description"])
                    record_access_audit_receipt(actor=actor, permission=permission, action=EVENTS["permission_create"],
                                                old_value=None, new_value={"permission_id": permission.pk, "service_id": service.pk},
                                                reason="permission_change")
                permissions = {p.permission_code: p for p in Permission.objects.filter(permission_code__in=CODES)}
                result = "CREATED"
            services_active = bool(services) and all(s.is_active for s in services.values())
            if services and any(s.is_active for s in services.values()) and not services_active:
                raise AcademicPhase1Refused("Partially active services are refused; no automatic repair.")
            _verify_metadata(services, permissions, service_defs, definitions, actor, active=services_active)

            if phase == "bindings" and not bindings:
                if _receipts(EVENTS["binding_stage"]) or _receipts(EVENTS["binding_activate"]):
                    raise AcademicPhase1Refused("Orphaned binding receipts require manual review.")
                for code in CODES:
                    permission = permissions[code]
                    binding = RolePermission.objects.create(role=admin, permission=permission, is_active=False, granted_by=actor)
                    record_access_audit_receipt(actor=actor, role=admin, permission=permission, action=EVENTS["binding_stage"],
                                                old_value=None, new_value={"role_id": admin.pk, "permission_id": permission.pk,
                                                                           "role_permission_id": binding.pk, "is_active": False},
                                                reason="permission_change")
                bindings = list(RolePermission.objects.filter(permission_id__in=[p.pk for p in permissions.values()], role=admin)
                                .order_by("pk"))
                result = "CREATED"
            if phase == "activate" and not bindings:
                raise AcademicPhase1Refused("Inactive bindings must be staged first.")
            if bindings:
                bindings_active = all(b.is_active for b in bindings)
                if any(b.is_active for b in bindings) and not bindings_active:
                    raise AcademicPhase1Refused("Partially active bindings are refused; no automatic repair.")
                if bindings_active != services_active:
                    raise AcademicPhase1Refused("Service and binding activation states differ; no automatic repair.")
                if phase == "activate" and not bindings_active:
                    _verify_bindings(bindings, permissions, admin, actor, active=False)
                    for code in SERVICE_CODES:
                        service = services[code]
                        Service.objects.filter(pk=service.pk, is_active=False).update(is_active=True)
                        record_access_audit_receipt(actor=actor, action=EVENTS["service_activate"],
                                                    old_value={"service_id": service.pk, "is_active": False},
                                                    new_value={"service_id": service.pk, "is_active": True},
                                                    reason="permission_change")
                    for binding in bindings:
                        RolePermission.objects.filter(pk=binding.pk, is_active=False).update(is_active=True)
                        record_access_audit_receipt(actor=actor, role=admin, permission=binding.permission,
                                                    action=EVENTS["binding_activate"],
                                                    old_value={"role_permission_id": binding.pk, "is_active": False},
                                                    new_value={"role_permission_id": binding.pk, "is_active": True},
                                                    reason="permission_change")
                    services = {s.service_code: s for s in Service.objects.filter(service_code__in=SERVICE_CODES)}
                    bindings = list(RolePermission.objects.filter(pk__in=[b.pk for b in bindings]).order_by("pk"))
                    bindings_active = services_active = True
                    result = "ACTIVATED"
                _verify_metadata(services, permissions, service_defs, definitions, actor, active=services_active)
                _verify_bindings(bindings, permissions, admin, actor, active=bindings_active)
                if bindings_active:
                    _verify_service_activation(services, actor)
                    _effective(actor, admin, permissions)
            elif services_active:
                raise AcademicPhase1Refused("Active services without staged bindings are refused.")

            if _snapshot_outside_scope([s.pk for s in services.values()], [p.pk for p in permissions.values()], admin.pk) != before:
                raise AcademicPhase1Refused("State outside the authorized phase-one scope changed.")
            catalogue_definitions()  # the pinned catalogue must still match before commit
        return result
    finally:
        with db.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", [LOCK_NAME])


class Command(BaseCommand):
    help = "LOCAL DEV ONLY: governed WF-11.01 phase-one services, definitions and Admin bindings."

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
            raise CommandError("WF-11.01 phase 1: refused or rolled back; no success reported. "
                               "Inspect the current state before retrying.") from exc
        self.stdout.write(f"WF-11.01 phase 1 {options['phase']}: {result}; services=2; codes=5; role=Admin; "
                          "no other change")
