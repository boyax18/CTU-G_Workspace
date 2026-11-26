"""WF-11.01 Academic Settings phase 2: owner-authorized LOCAL DEVELOPMENT provisioning (26 Nov 2026).

The remaining Academic Settings bindings that need NO catalogue change, i.e. exactly pinned v2.2
definitions and default bindings (owner policy decisions of 26 Nov 2026):

  clearance.teaching_assignments.manage  -> Admin      (instructor assignments; new definition)
  academic.catalogue.read                -> Student, Instructor, Treasurer   (current period for all
                                                         authorized roles; Admin was bound in phase 1)

Curriculum (``academic.courses.manage``) and offering (``academic.periods.manage``) writes reuse the
phase-one Admin bindings; they need only their switches. Everything in the v2.3 candidate (the fee
binding move, the three narrow codes and the definition restatements) is NOT provisioned here: its
independent review is OPEN.

Same principles as phase 1: named local or disposable test database only, an exact confirmation per
phase, the shared governance lock, one durable transaction per phase, a named Approved application
Admin as actor, exact allowlists from the validated pinned catalogue, append-only receipts, verify-only
re-runs, no automatic repair, every Academic Settings switch off while it runs, account Grants for
these codes refused, Denies preserved, and nothing outside scope changed. Requires phase 1 complete.

Phases (each needs --apply and its exact confirmation; --phase verify is read-only):
  metadata  create the clearance.teaching_assignments.manage definition    (1 receipt)
  bindings  stage the four INACTIVE bindings above                          (4 receipts)
  activate  activate exactly those four bindings                            (4 receipts)
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction

from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.management.commands import provision_academic_settings_phase1_local_dev as phase1
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.services import has_permission
from apps.accounts.active_role_context import bind_role_scope, context_enabled
from apps.accounts.models import Account

NEW_CODE = "clearance.teaching_assignments.manage"
CATALOGUE_CODE = "academic.catalogue.read"
BINDINGS = (("Admin", NEW_CODE), ("Student", CATALOGUE_CODE), ("Instructor", CATALOGUE_CODE), ("Treasurer", CATALOGUE_CODE))
ROLES = ("Admin", "Student", "Instructor", "Treasurer")
EVENTS = {
    "permission_create": "workspace.academic_settings.p2.permission.create",
    "binding_stage": "workspace.academic_settings.p2.binding.stage",
    "binding_activate": "workspace.academic_settings.p2.binding.activate",
}
PHASES = ("metadata", "bindings", "activate")
LOCK_NAME = phase1.LOCK_NAME
DEV_CONFIRM = {phase: f"ctug_workspace:WF-11.01:PHASE2:{phase.upper()}" for phase in PHASES}
TEST_CONFIRM = {phase: f"WF-11.01:DISPOSABLE-TEST:PHASE2:{phase.upper()}" for phase in PHASES}


class AcademicPhase2Refused(RuntimeError):
    """The phase is unsafe or does not match the exact authorized local scope."""


def catalogue_definitions():
    """The pinned v2.2 definition of the new code, and proof every binding here is a pinned default."""
    try:
        validated = phase1.validate_catalogue()
    except Exception as exc:
        raise AcademicPhase2Refused("Pinned catalogue v2.2 failed validation.") from exc
    if validated.digest != phase1.PINNED_V22_DIGEST:
        raise AcademicPhase2Refused("Pinned catalogue v2.2 digest differs from the reviewed digest.")
    data = validated.data
    definition = next((dict(p) for p in data["permissions"] if p["permission_code"] == NEW_CODE), None)
    defaults = {(b["role_name"], b["permission_code"]) for b in data["default_bindings"]}
    blocked = {b["permission_code"] for b in data["blocked_permissions"]}
    if (definition is None or definition["service_code"] != "clearance" or definition["readiness"] != "P"
            or definition["grant_protection"] != "ORD" or {NEW_CODE, CATALOGUE_CODE} & blocked
            or any(binding not in defaults for binding in BINDINGS)):
        raise AcademicPhase2Refused("Catalogue v2.2 no longer defines exactly these phase-two bindings.")
    return definition


def _target(phase, confirmation):
    confirms = TEST_CONFIRM if settings.SETTINGS_MODULE == "config.test_settings" else DEV_CONFIRM
    if phase not in confirms or confirmation != confirms[phase]:
        raise AcademicPhase2Refused("The exact confirmation for this phase is required.")
    try:
        # Same target rules as phase 1 (local MySQL, named DB or disposable test DB, switches off,
        # migrations applied), checked through phase 1's own confirmation for its metadata phase.
        return phase1._target("metadata", (phase1.TEST_CONFIRM if settings.SETTINGS_MODULE == "config.test_settings"
                                           else phase1.DEV_CONFIRM)["metadata"])
    except Exception as exc:
        raise AcademicPhase2Refused("The local database target is not safe.") from exc


def _receipts(event):
    return list(AccessAuditLog.objects.select_for_update().filter(action=event).order_by("access_audit_log_id"))


def _phase_one_complete(actor):
    """Precondition: phase 1 is complete, active and attributable (verified with phase 1's own checks)."""
    service_defs, definitions = phase1.catalogue_definitions()
    services = {s.service_code: s for s in Service.objects.select_for_update().filter(service_code__in=phase1.SERVICE_CODES)}
    permissions = {p.permission_code: p for p in Permission.objects.select_for_update().filter(permission_code__in=phase1.CODES)}
    admin = Role.objects.get(role_name="Admin", is_active=True)
    try:
        phase1._verify_metadata(services, permissions, service_defs, definitions, actor, active=True)
        phase1._verify_bindings(list(RolePermission.objects.select_for_update()
                                     .filter(permission_id__in=[p.pk for p in permissions.values()], role=admin)
                                     .order_by("pk")), permissions, admin, actor, active=True)
        phase1._verify_service_activation(services, actor)
    except phase1.AcademicPhase1Refused as exc:
        raise AcademicPhase2Refused("Phase 1 is not complete.") from exc
    return services, permissions


def verify_bindings(bindings, roles, permissions, actor, active):
    """Exact phase-two bindings and receipts (also used by phase 1 to recognise them as authorized)."""
    expected = {(roles[role].pk, permissions[code].pk) for role, code in BINDINGS}
    if (len(bindings) != len(BINDINGS) or {(b.role_id, b.permission_id) for b in bindings} != expected
            or any(b.granted_by_id != actor.pk or b.is_active is not active for b in bindings)):
        raise AcademicPhase2Refused("Phase-two bindings are partial, foreign, unattributed or in the wrong state.")
    by_key = {(b.role_id, b.permission_id): b for b in bindings}
    logs = _receipts(EVENTS["binding_stage"])
    if (len(logs) != len(BINDINGS) or {(log.role_id, log.permission_id) for log in logs} != expected
            or any(log.actor_account_id != actor.pk or log.target_account_id is not None or log.reason != "permission_change"
                   or log.old_value is not None
                   or log.new_value != {"role_id": log.role_id, "permission_id": log.permission_id,
                                        "role_permission_id": by_key[(log.role_id, log.permission_id)].pk, "is_active": False}
                   for log in logs)):
        raise AcademicPhase2Refused("Phase-two binding receipts are missing, duplicated or differ.")
    logs = _receipts(EVENTS["binding_activate"])
    if not active:
        if logs:
            raise AcademicPhase2Refused("Activation receipts exist for inactive phase-two bindings.")
        return
    if (len(logs) != len(BINDINGS) or {(log.role_id, log.permission_id) for log in logs} != expected
            or any(log.actor_account_id != actor.pk or log.reason != "permission_change"
                   or log.old_value != {"role_permission_id": by_key[(log.role_id, log.permission_id)].pk, "is_active": False}
                   or log.new_value != {"role_permission_id": by_key[(log.role_id, log.permission_id)].pk, "is_active": True}
                   for log in logs)):
        raise AcademicPhase2Refused("Phase-two activation receipts are missing, duplicated or differ.")


def scoped_bindings(roles, permissions):
    return list(RolePermission.objects.select_for_update().filter(
        permission_id__in=[permissions[c].pk for c in (NEW_CODE, CATALOGUE_CODE) if c in permissions])
        .exclude(role=roles["Admin"], permission__permission_code=CATALOGUE_CODE).order_by("pk"))


def recognised_by_phase_one(bindings):
    """Phase 1 accepts non-Admin bindings of its codes only if they are exactly the receipted phase-two set."""
    roles = {r.role_name: r for r in Role.objects.filter(role_name__in=ROLES, is_active=True)}
    permissions = {p.permission_code: p for p in Permission.objects.filter(permission_code__in=(NEW_CODE, CATALOGUE_CODE))}
    if set(roles) != set(ROLES) or set(permissions) != {NEW_CODE, CATALOGUE_CODE} or not bindings:
        raise AcademicPhase2Refused("Non-Admin phase-one bindings are not phase-two bindings.")
    actor = Account.objects.get(pk=bindings[0].granted_by_id)
    complete = scoped_bindings(roles, permissions)
    if {b.pk for b in bindings} - {b.pk for b in complete}:
        raise AcademicPhase2Refused("Non-Admin phase-one bindings are not phase-two bindings.")
    verify_bindings(complete, roles, permissions, actor, active=all(b.is_active for b in complete))


def _snapshot_outside_scope(scope_binding_ids, new_permission_ids):
    return (
        tuple(Service.objects.order_by("pk").values_list("pk", "service_code", "is_active")),
        tuple(Role.objects.order_by("pk").values_list("pk", "role_name", "is_active")),
        tuple(Permission.objects.exclude(pk__in=new_permission_ids).order_by("pk")
              .values_list("pk", "permission_code", "service_id", "permission_name", "description")),
        tuple(RolePermission.objects.exclude(pk__in=scope_binding_ids).order_by("pk")
              .values_list("pk", "role_id", "permission_id", "is_active")),
        tuple(AccountRole.objects.order_by("pk").values_list("pk", "account_id", "role_id")),
        tuple(AccountPermission.objects.order_by("pk").values_list("pk", "account_id", "permission_id", "effect", "is_active")),
        tuple(phase1.AccountPermissionRoleScope.objects.order_by("pk").values_list("account_permission_id", "role_id")),
    )


def _effective(roles, permissions):
    """Every eligible holder of each bound role gains the code in that role, unless an own active Deny applies."""
    for role_name, code in BINDINGS:
        role = roles[role_name]
        holders = Account.objects.filter(is_active=True, request_status="Approved", is_staff=False, is_superuser=False,
                                         pk__in=AccountRole.objects.filter(role=role).values("account_id"))
        for account in holders:
            denied = AccountPermission.objects.filter(account=account, permission=permissions[code], effect="Deny",
                                                      is_active=True).exists()
            if context_enabled():
                with bind_role_scope(account.pk, role.pk):
                    granted = has_permission(account, code)
            else:
                granted = has_permission(account, code)
            if granted is denied:
                raise AcademicPhase2Refused("Effective authority does not match the provisioned bindings.")


def run(*, phase, actor_account_id, confirmation=None, apply=False):
    if phase not in PHASES + ("verify",):
        raise AcademicPhase2Refused("Unknown phase.")
    definition = catalogue_definitions()
    confirms = TEST_CONFIRM if settings.SETTINGS_MODULE == "config.test_settings" else DEV_CONFIRM
    db = _target("metadata" if phase == "verify" else phase, confirms["metadata"] if phase == "verify" else confirmation)
    if phase != "verify" and not apply:
        raise AcademicPhase2Refused("No implicit writes: pass --apply with the exact confirmation.")
    with db.cursor() as cursor:
        cursor.execute("SELECT GET_LOCK(%s, 0)", [LOCK_NAME])
        if cursor.fetchone()[0] != 1:
            raise AcademicPhase2Refused("Another governance operation is running.")
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            list(Service.objects.select_for_update().order_by("service_id"))  # shared lock order
            roles = {r.role_name: r for r in Role.objects.select_for_update().filter(role_name__in=ROLES, is_active=True)}
            if set(roles) != set(ROLES) or Role.objects.filter(role_name__in=ROLES).count() != len(ROLES):
                raise AcademicPhase2Refused("Exactly one active Admin, Student, Instructor and Treasurer role is required.")
            try:
                actor = phase1.p1._actor(actor_account_id)
            except Exception as exc:
                raise AcademicPhase2Refused("A persisted, active, approved application Admin is required.") from exc
            services, phase_one_permissions = _phase_one_complete(actor)
            permissions = {p.permission_code: p for p in Permission.objects.select_for_update()
                           .filter(permission_code__in=(NEW_CODE, CATALOGUE_CODE))}
            if AccountPermission.objects.filter(permission_id__in=[p.pk for p in permissions.values()], effect="Grant").exists():
                raise AcademicPhase2Refused("Account-level Grants for these codes are unauthorized.")
            bindings = scoped_bindings(roles, permissions)
            before = _snapshot_outside_scope([b.pk for b in bindings],
                                             [permissions[NEW_CODE].pk] if NEW_CODE in permissions else [])
            result = "VERIFIED" if phase == "verify" else "ALREADY_COMPLETE"

            if phase == "metadata" and NEW_CODE not in permissions:
                if _receipts(EVENTS["permission_create"]):
                    raise AcademicPhase2Refused("Orphaned metadata receipts require manual review.")
                service = services[definition["service_code"]]
                permission = Permission.objects.create(
                    service=service, permission_code=NEW_CODE, permission_name=definition["permission_name"],
                    module_name=definition["module_name"], action_name=definition["action_name"],
                    description=definition["description"])
                record_access_audit_receipt(actor=actor, permission=permission, action=EVENTS["permission_create"],
                                            old_value=None, new_value={"permission_id": permission.pk, "service_id": service.pk},
                                            reason="permission_change")
                permissions[NEW_CODE] = permission
                result = "CREATED"
            if NEW_CODE not in permissions:
                raise AcademicPhase2Refused("The phase-two definition must be created first.")
            new = permissions[NEW_CODE]
            if not phase1._matches_permission(new, definition, services["clearance"]):
                raise AcademicPhase2Refused("The phase-two definition differs from catalogue v2.2.")
            logs = _receipts(EVENTS["permission_create"])
            if (len(logs) != 1 or logs[0].permission_id != new.pk or logs[0].actor_account_id != actor.pk
                    or logs[0].new_value != {"permission_id": new.pk, "service_id": services["clearance"].pk}):
                raise AcademicPhase2Refused("The phase-two definition receipt is missing or differs.")

            if phase == "bindings" and not bindings:
                if _receipts(EVENTS["binding_stage"]) or _receipts(EVENTS["binding_activate"]):
                    raise AcademicPhase2Refused("Orphaned binding receipts require manual review.")
                for role_name, code in BINDINGS:
                    role, permission = roles[role_name], permissions[code]
                    binding = RolePermission.objects.create(role=role, permission=permission, is_active=False, granted_by=actor)
                    record_access_audit_receipt(actor=actor, role=role, permission=permission, action=EVENTS["binding_stage"],
                                                old_value=None, new_value={"role_id": role.pk, "permission_id": permission.pk,
                                                                           "role_permission_id": binding.pk, "is_active": False},
                                                reason="permission_change")
                bindings = scoped_bindings(roles, permissions)
                result = "CREATED"
            if phase == "activate" and not bindings:
                raise AcademicPhase2Refused("Inactive bindings must be staged first.")
            if bindings:
                active = all(b.is_active for b in bindings)
                if any(b.is_active for b in bindings) and not active:
                    raise AcademicPhase2Refused("Partially active bindings are refused; no automatic repair.")
                if phase == "activate" and not active:
                    verify_bindings(bindings, roles, permissions, actor, active=False)
                    for binding in bindings:
                        RolePermission.objects.filter(pk=binding.pk, is_active=False).update(is_active=True)
                        record_access_audit_receipt(actor=actor, role=binding.role, permission=binding.permission,
                                                    action=EVENTS["binding_activate"],
                                                    old_value={"role_permission_id": binding.pk, "is_active": False},
                                                    new_value={"role_permission_id": binding.pk, "is_active": True},
                                                    reason="permission_change")
                    bindings = scoped_bindings(roles, permissions)
                    active = True
                    result = "ACTIVATED"
                verify_bindings(bindings, roles, permissions, actor, active=active)
                if active:
                    _effective(roles, permissions)
            if _snapshot_outside_scope([b.pk for b in bindings], [new.pk]) != before:
                raise AcademicPhase2Refused("State outside the authorized phase-two scope changed.")
            catalogue_definitions()
        return result
    finally:
        with db.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", [LOCK_NAME])


class Command(BaseCommand):
    help = "LOCAL DEV ONLY: governed WF-11.01 phase-two pinned v2.2 bindings (instructor assignments, current period)."

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
            raise CommandError("WF-11.01 phase 2: refused or rolled back; no success reported. "
                               "Inspect the current state before retrying.") from exc
        self.stdout.write(f"WF-11.01 phase 2 {options['phase']}: {result}; definitions=1; bindings=4; no other change")
