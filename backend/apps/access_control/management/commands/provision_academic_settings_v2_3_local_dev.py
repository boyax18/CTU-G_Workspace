"""WF-11.01 Academic Settings v2.3: LOCAL DEVELOPMENT provisioning of the independently approved delta.

Installed only by the reviewed v2.3 runtime patch. It writes NOTHING unless either the completed
independent sign-off (``validation_v2_3.require_independent_approval()``, required for production) or the
owner's LOCAL DEVELOPMENT authorization (``require_local_development_authorization()``, project governance
amendment of 27 Nov 2026; never independent approval) is recorded for the pinned bytes. Owner-authorized scope (policy decisions of 26 Nov 2026 and
historical dual control of 27 Nov 2026):

  service   finance                                    pinned v2.2 definition; created INACTIVE, then activated
  define    finance.fee_schedule.manage                pinned v2.2 definition
            academic.profile.self.read                 pinned v2.2 definition (onboarding reads)
            academic.enrollment_verifications.record   v2.3
            academic.semester_onboarding.self.submit   v2.3
            academic.historical_participation.correct  v2.3 (dual control is enforced by its runtime)
  restate   academic.courses.manage, academic.periods.manage   v2.3 definition clarifications
  bind      Admin   -> finance.fee_schedule.manage     v2.3 move: NO Treasurer binding is ever created
            Admin   -> academic.enrollment_verifications.record
            Student -> academic.semester_onboarding.self.submit
            Admin   -> academic.historical_participation.correct
            Student -> academic.profile.self.read      pinned v2.2 default

Same principles as phases 1 and 2: named local or disposable test database only, an exact confirmation
per phase, the shared governance lock, one durable transaction per phase, a named Approved application
Admin as actor, exact allowlists from the validated catalogue, append-only receipts, verify-only re-runs,
no automatic repair, every Academic Settings switch off while it runs, account Grants for these codes
refused, Denies preserved (they keep precedence, including the Deny-only predecessors of
permission_transitions) and nothing outside scope changed. Requires phases 1 and 2 complete.

Phases (each needs --apply and its exact confirmation; --phase verify is read-only):
  metadata  the finance service INACTIVE and the five definitions   (6 receipts)
  restate   the two definition clarifications                       (2 receipts)
  bindings  the five INACTIVE bindings                              (5 receipts)
  activate  the finance service and the five bindings               (6 receipts)
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction

from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.catalogue import validation_v2_3 as v23
from apps.access_control.management.commands import provision_academic_settings_phase1_local_dev as phase1
from apps.access_control.management.commands import provision_academic_settings_phase2_local_dev as phase2
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.permission_transitions import DENY_PREDECESSORS
from apps.access_control.services import has_permission
from apps.accounts.active_role_context import bind_role_scope, context_enabled
from apps.accounts.models import Account

SERVICE_CODE = "finance"
FEE = "finance.fee_schedule.manage"
PROFILE_READ = "academic.profile.self.read"
VERIFY = "academic.enrollment_verifications.record"
ONBOARD = "academic.semester_onboarding.self.submit"
HISTORY = "academic.historical_participation.correct"
CODES = (FEE, PROFILE_READ, VERIFY, ONBOARD, HISTORY)
CODE_SERVICES = {FEE: "finance", PROFILE_READ: "academic", VERIFY: "academic", ONBOARD: "academic", HISTORY: "academic"}
RESTATED = ("academic.courses.manage", "academic.periods.manage")
BINDINGS = (("Admin", FEE), ("Admin", VERIFY), ("Student", ONBOARD), ("Admin", HISTORY), ("Student", PROFILE_READ))
ROLES = phase2.ROLES
EVENTS = {
    "service_create": "workspace.academic_settings.v23.service.create",
    "permission_create": "workspace.academic_settings.v23.permission.create",
    "restate": "workspace.academic_settings.v23.permission.restate",
    "binding_stage": "workspace.academic_settings.v23.binding.stage",
    "service_activate": "workspace.academic_settings.v23.service.activate",
    "binding_activate": "workspace.academic_settings.v23.binding.activate",
}
PHASES = ("metadata", "restate", "bindings", "activate")
LOCK_NAME = phase1.LOCK_NAME
DEV_CONFIRM = {phase: f"ctug_workspace:WF-11.01:V2.3:{phase.upper()}" for phase in PHASES}
TEST_CONFIRM = {phase: f"WF-11.01:DISPOSABLE-TEST:V2.3:{phase.upper()}" for phase in PHASES}


class AcademicV23Refused(RuntimeError):
    """The phase is unsafe, unapproved or does not match the exact authorized local scope."""


def catalogue():
    """The finance service, the exact definitions and the restatements of the validated v2.3 catalogue."""
    try:
        data = v23.validate_catalogue().data
    except Exception as exc:
        raise AcademicV23Refused("Catalogue v2.3 failed validation.") from exc
    services = {s["service_code"]: dict(s) for s in data["services"]}
    definitions = {p["permission_code"]: dict(p) for p in data["permissions"] if p["permission_code"] in CODES + RESTATED}
    defaults = {(b["role_name"], b["permission_code"]) for b in data["default_bindings"]}
    blocked = {b["permission_code"] for b in data["blocked_permissions"]}
    restatements = {o["permission_code"]: (o["old"], o["new"]) for o in data["revision"]["operations"]
                    if o["op"] == "restate_permission_definition"}
    if (SERVICE_CODE not in services or set(definitions) != set(CODES + RESTATED) or blocked & set(CODES)
            or any(definitions[c]["service_code"] != CODE_SERVICES[c] or definitions[c]["readiness"] != "P"
                   or definitions[c]["grant_protection"] != "ORD" for c in CODES)
            or any(binding not in defaults for binding in BINDINGS) or ("Treasurer", FEE) in defaults
            or set(restatements) != set(RESTATED)
            or any(definitions[c]["description"] != restatements[c][1] for c in RESTATED)):
        raise AcademicV23Refused("Catalogue v2.3 no longer defines exactly this scope.")
    return services[SERVICE_CODE], definitions, restatements


def _restatement_matches(log, permission, actor=None):
    """Receipts carry identifiers only (the audit allowlist); the exact old and new text is the pinned,
    validated v2.3 restatement, and the row itself must hold the new text."""
    return (log.permission_id == permission.pk and log.role_id is None and log.target_account_id is None
            and log.reason == "permission_change" and (actor is None or log.actor_account_id == actor.pk)
            and log.old_value == {"permission_id": permission.pk} and log.new_value == {"permission_id": permission.pk})


def effective_definitions(permissions, definitions):
    """Phase-1 compatibility: a restated v2.3 definition is accepted ONLY with its exact receipt."""
    receipted = {code: list(AccessAuditLog.objects.filter(action=EVENTS["restate"], permission_id=permissions[code].pk)
                            .order_by("access_audit_log_id"))
                 for code in RESTATED if code in permissions}
    receipted = {code: logs for code, logs in receipted.items() if logs}
    if not receipted:
        return definitions
    _, _, restatements = catalogue()
    adjusted = dict(definitions)
    for code, logs in receipted.items():
        old, new = restatements[code]
        if len(logs) != 1 or definitions[code]["description"] != old or not _restatement_matches(logs[0], permissions[code]):
            raise AcademicV23Refused("Restated definition receipts are missing, duplicated or differ.")
        adjusted[code] = dict(definitions[code], description=new)
    return adjusted


def authorization_basis():
    """Independent approval, or the owner's local-development authorization on a local target only."""
    try:
        v23.require_independent_approval()
        return "independent_approval"
    except v23.CatalogueV23ValidationError:
        pass
    try:
        v23.require_local_development_authorization()
    except Exception as exc:
        raise AcademicV23Refused("Neither independent approval nor the owner's local authorization is recorded.") from exc
    if (settings.SETTINGS_MODULE not in ("config.settings", "config.test_settings")
            or getattr(settings, "WORKSPACE_DEPLOYMENT_PROFILE", "local") != "local"):
        raise AcademicV23Refused("The owner's authorization covers local development only.")
    return "owner_local_development_authorization"


def _target(phase, confirmation):
    confirms = TEST_CONFIRM if settings.SETTINGS_MODULE == "config.test_settings" else DEV_CONFIRM
    if phase not in confirms or confirmation != confirms[phase]:
        raise AcademicV23Refused("The exact confirmation for this phase is required.")
    try:
        # Phase 1's target rules: local MySQL, named or disposable DB, switches off, migrations applied.
        return phase1._target("metadata", (phase1.TEST_CONFIRM if settings.SETTINGS_MODULE == "config.test_settings"
                                           else phase1.DEV_CONFIRM)["metadata"])
    except Exception as exc:
        raise AcademicV23Refused("The local database target is not safe.") from exc


def _receipts(event):
    return list(AccessAuditLog.objects.select_for_update().filter(action=event).order_by("access_audit_log_id"))


def _prior_phases_complete():
    """Phases 1 and 2 complete and attributable, checked with their own verifiers and recorded actor."""
    try:
        first = AccessAuditLog.objects.filter(action=phase1.EVENTS["service_create"]).order_by("access_audit_log_id").first()
        if first is None:
            raise AcademicV23Refused("Phase 1 has not run.")
        prior = phase1.p1._actor(first.actor_account_id)
        services, _ = phase2._phase_one_complete(prior)
        roles = {r.role_name: r for r in Role.objects.filter(role_name__in=ROLES, is_active=True)}
        codes = (phase2.NEW_CODE, phase2.CATALOGUE_CODE)
        permissions = {p.permission_code: p for p in Permission.objects.filter(permission_code__in=codes)}
        if set(permissions) != set(codes):
            raise AcademicV23Refused("Phase 2 has not run.")
        phase2.verify_bindings(phase2.scoped_bindings(roles, permissions), roles, permissions, prior, active=True)
    except Exception as exc:
        raise AcademicV23Refused("Phases 1 and 2 must be complete first.") from exc
    return services


def _scoped_bindings(permissions):
    return list(RolePermission.objects.select_for_update()
                .filter(permission_id__in=[p.pk for p in permissions.values()]).order_by("pk"))


def _verify_metadata(finance, permissions, service_def, definitions, academic, actor, active):
    if (finance is None or set(permissions) != set(CODES)
            or not phase1._matches_service(finance, service_def, active)):
        raise AcademicV23Refused("The finance service or the v2.3 definitions are partial or differ.")
    services = {"finance": finance, "academic": academic}
    if not all(phase1._matches_permission(permissions[c], definitions[c], services[CODE_SERVICES[c]]) for c in CODES):
        raise AcademicV23Refused("A provisioned definition differs from catalogue v2.3.")
    logs = _receipts(EVENTS["service_create"])
    if (len(logs) != 1 or logs[0].actor_account_id != actor.pk or logs[0].reason != "permission_change"
            or logs[0].permission_id is not None or logs[0].old_value is not None
            or logs[0].new_value != {"service_id": finance.pk, "is_active": False}):
        raise AcademicV23Refused("The finance service receipt is missing or differs.")
    logs = _receipts(EVENTS["permission_create"])
    expected = {(p.pk, p.service_id) for p in permissions.values()}
    if (len(logs) != len(CODES) or {(log.permission_id, (log.new_value or {}).get("service_id")) for log in logs} != expected
            or any(log.actor_account_id != actor.pk or log.reason != "permission_change" or log.role_id is not None
                   or log.old_value is not None
                   or log.new_value != {"permission_id": log.permission_id, "service_id": (log.new_value or {}).get("service_id")}
                   for log in logs)):
        raise AcademicV23Refused("Definition receipts are missing, duplicated or differ.")


def _restated_state(restated, restatements, actor):
    """True when both clarifications are applied with exact receipts, False when neither is; else refuse."""
    logs = _receipts(EVENTS["restate"])
    done = [restated[c].description == restatements[c][1] for c in RESTATED]
    if not any(done) and not logs and all(restated[c].description == restatements[c][0] for c in RESTATED):
        return False
    if (all(done) and len(logs) == len(RESTATED)
            and all(any(_restatement_matches(log, restated[c], actor=actor) for log in logs) for c in RESTATED)):
        return True
    raise AcademicV23Refused("Definition restatements are partial or unreceipted; no automatic repair.")


def _verify_bindings(bindings, roles, permissions, actor, active):
    expected = {(roles[role].pk, permissions[code].pk) for role, code in BINDINGS}
    if (len(bindings) != len(BINDINGS) or {(b.role_id, b.permission_id) for b in bindings} != expected
            or any(b.granted_by_id != actor.pk or b.is_active is not active for b in bindings)):
        raise AcademicV23Refused("v2.3 bindings are partial, foreign, unattributed or in the wrong state.")
    by_key = {(b.role_id, b.permission_id): b for b in bindings}
    logs = _receipts(EVENTS["binding_stage"])
    if (len(logs) != len(BINDINGS) or {(log.role_id, log.permission_id) for log in logs} != expected
            or any(log.actor_account_id != actor.pk or log.target_account_id is not None or log.reason != "permission_change"
                   or log.old_value is not None
                   or log.new_value != {"role_id": log.role_id, "permission_id": log.permission_id,
                                        "role_permission_id": by_key[(log.role_id, log.permission_id)].pk, "is_active": False}
                   for log in logs)):
        raise AcademicV23Refused("v2.3 binding receipts are missing, duplicated or differ.")
    logs = _receipts(EVENTS["binding_activate"])
    if not active:
        if logs:
            raise AcademicV23Refused("Activation receipts exist for inactive v2.3 bindings.")
        return
    if (len(logs) != len(BINDINGS) or {(log.role_id, log.permission_id) for log in logs} != expected
            or any(log.actor_account_id != actor.pk or log.reason != "permission_change"
                   or log.old_value != {"role_permission_id": by_key[(log.role_id, log.permission_id)].pk, "is_active": False}
                   or log.new_value != {"role_permission_id": by_key[(log.role_id, log.permission_id)].pk, "is_active": True}
                   for log in logs)):
        raise AcademicV23Refused("v2.3 activation receipts are missing, duplicated or differ.")


def _verify_service_activation(finance, actor):
    logs = _receipts(EVENTS["service_activate"])
    if (len(logs) != 1 or logs[0].actor_account_id != actor.pk or logs[0].reason != "permission_change"
            or logs[0].old_value != {"service_id": finance.pk, "is_active": False}
            or logs[0].new_value != {"service_id": finance.pk, "is_active": True}):
        raise AcademicV23Refused("The finance activation receipt is missing or differs.")


def _snapshot_outside_scope(finance_id, new_ids, restated_ids, binding_ids):
    """Everything this command must never change (restated rows: every field except the description)."""
    return (
        tuple(Service.objects.exclude(pk__in=[finance_id] if finance_id else []).order_by("pk")
              .values_list("pk", "service_code", "service_name", "description", "is_active")),
        tuple(Role.objects.order_by("pk").values_list("pk", "role_name", "is_active")),
        tuple(Permission.objects.exclude(pk__in=new_ids + restated_ids).order_by("pk")
              .values_list("pk", "permission_code", "service_id", "permission_name", "module_name", "action_name", "description")),
        tuple(Permission.objects.filter(pk__in=restated_ids).order_by("pk")
              .values_list("pk", "permission_code", "service_id", "permission_name", "module_name", "action_name")),
        tuple(RolePermission.objects.exclude(pk__in=binding_ids).order_by("pk").values_list("pk", "role_id", "permission_id", "is_active")),
        tuple(AccountRole.objects.order_by("pk").values_list("pk", "account_id", "role_id")),
        tuple(AccountPermission.objects.order_by("pk").values_list("pk", "account_id", "permission_id", "effect", "is_active")),
        tuple(phase1.AccountPermissionRoleScope.objects.order_by("pk").values_list("account_permission_id", "role_id")),
    )


def _effective(roles):
    """Every eligible holder of each bound role gains the code in that role unless an own active Deny on it,
    or on one of its Deny-only predecessors, applies (Deny precedence is preserved, never repaired)."""
    for role_name, code in BINDINGS:
        role = roles[role_name]
        holders = Account.objects.filter(is_active=True, request_status="Approved", is_staff=False, is_superuser=False,
                                         pk__in=AccountRole.objects.filter(role=role).values("account_id"))
        for account in holders:
            denied = AccountPermission.objects.filter(
                account=account, effect="Deny", is_active=True,
                permission__permission_code__in=(code, *DENY_PREDECESSORS.get(code, ()))).exists()
            if context_enabled():
                with bind_role_scope(account.pk, role.pk):
                    granted = has_permission(account, code)
            else:
                granted = has_permission(account, code)
            if granted is denied:
                raise AcademicV23Refused("Effective authority does not match the provisioned v2.3 bindings.")


def run(*, phase, actor_account_id, confirmation=None, apply=False):
    if phase not in PHASES + ("verify",):
        raise AcademicV23Refused("Unknown phase.")
    authorization_basis()
    service_def, definitions, restatements = catalogue()
    confirms = TEST_CONFIRM if settings.SETTINGS_MODULE == "config.test_settings" else DEV_CONFIRM
    db = _target("metadata" if phase == "verify" else phase, confirms["metadata"] if phase == "verify" else confirmation)
    if phase != "verify" and not apply:
        raise AcademicV23Refused("No implicit writes: pass --apply with the exact confirmation.")
    with db.cursor() as cursor:
        cursor.execute("SELECT GET_LOCK(%s, 0)", [LOCK_NAME])
        if cursor.fetchone()[0] != 1:
            raise AcademicV23Refused("Another governance operation is running.")
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            list(Service.objects.select_for_update().order_by("service_id"))  # shared lock order
            roles = {r.role_name: r for r in Role.objects.select_for_update().filter(role_name__in=ROLES, is_active=True)}
            if set(roles) != set(ROLES) or Role.objects.filter(role_name__in=ROLES).count() != len(ROLES):
                raise AcademicV23Refused("Exactly one active Admin, Student, Instructor and Treasurer role is required.")
            try:
                actor = phase1.p1._actor(actor_account_id)
            except Exception as exc:
                raise AcademicV23Refused("A persisted, active, approved application Admin is required.") from exc
            academic = _prior_phases_complete()["academic"]
            finance = Service.objects.select_for_update().filter(service_code=SERVICE_CODE).first()
            permissions = {p.permission_code: p for p in Permission.objects.select_for_update().filter(permission_code__in=CODES)}
            restated = {p.permission_code: p for p in Permission.objects.select_for_update().filter(permission_code__in=RESTATED)}
            if set(restated) != set(RESTATED):
                raise AcademicV23Refused("The restated phase-one definitions are missing.")
            if AccountPermission.objects.filter(permission_id__in=[p.pk for p in permissions.values()], effect="Grant").exists():
                raise AcademicV23Refused("Account-level Grants for these codes are unauthorized.")
            bindings = _scoped_bindings(permissions)
            before = _snapshot_outside_scope(finance.pk if finance else None, [p.pk for p in permissions.values()],
                                             [p.pk for p in restated.values()], [b.pk for b in bindings])
            result = "VERIFIED" if phase == "verify" else "ALREADY_COMPLETE"

            if finance is None and not permissions:
                if any(_receipts(event) for event in EVENTS.values()):
                    raise AcademicV23Refused("Orphaned v2.3 receipts require manual review.")
                if bindings:
                    raise AcademicV23Refused("Foreign bindings exist; no automatic repair.")
                if phase == "verify":
                    if _restated_state(restated, restatements, actor):
                        raise AcademicV23Refused("Restatements exist without v2.3 metadata.")
                    return "NOT_STARTED"
                if phase != "metadata":
                    raise AcademicV23Refused("The v2.3 metadata must be created first.")
                finance = Service.objects.create(service_code=SERVICE_CODE, service_name=service_def["service_name"],
                                                 description=service_def["description"], is_active=False)
                record_access_audit_receipt(actor=actor, action=EVENTS["service_create"], old_value=None,
                                            new_value={"service_id": finance.pk, "is_active": False}, reason="permission_change")
                owners = {"finance": finance, "academic": academic}
                for code in CODES:
                    d = definitions[code]
                    service = owners[CODE_SERVICES[code]]
                    permission = Permission.objects.create(
                        service=service, permission_code=code, permission_name=d["permission_name"],
                        module_name=d["module_name"], action_name=d["action_name"], description=d["description"])
                    record_access_audit_receipt(actor=actor, permission=permission, action=EVENTS["permission_create"],
                                                old_value=None, new_value={"permission_id": permission.pk, "service_id": service.pk},
                                                reason="permission_change")
                    permissions[code] = permission
                result = "CREATED"
            finance_active = finance is not None and finance.is_active
            _verify_metadata(finance, permissions, service_def, definitions, academic, actor, active=finance_active)

            restated_done = _restated_state(restated, restatements, actor)
            if phase == "restate" and not restated_done:
                for code in RESTATED:
                    old, new = restatements[code]
                    if Permission.objects.filter(pk=restated[code].pk, description=old).update(description=new) != 1:
                        raise AcademicV23Refused("A restated definition changed concurrently.")
                    record_access_audit_receipt(actor=actor, permission=restated[code], action=EVENTS["restate"],
                                                old_value={"permission_id": restated[code].pk},
                                                new_value={"permission_id": restated[code].pk},
                                                reason="permission_change")
                restated = {p.permission_code: p for p in Permission.objects.filter(permission_code__in=RESTATED)}
                restated_done = _restated_state(restated, restatements, actor)
                result = "RESTATED"

            if phase == "bindings" and not bindings:
                if not restated_done:
                    raise AcademicV23Refused("The definition restatements must be applied first.")
                if _receipts(EVENTS["binding_stage"]) or _receipts(EVENTS["binding_activate"]):
                    raise AcademicV23Refused("Orphaned binding receipts require manual review.")
                for role_name, code in BINDINGS:
                    role, permission = roles[role_name], permissions[code]
                    binding = RolePermission.objects.create(role=role, permission=permission, is_active=False, granted_by=actor)
                    record_access_audit_receipt(actor=actor, role=role, permission=permission, action=EVENTS["binding_stage"],
                                                old_value=None, new_value={"role_id": role.pk, "permission_id": permission.pk,
                                                                           "role_permission_id": binding.pk, "is_active": False},
                                                reason="permission_change")
                bindings = _scoped_bindings(permissions)
                result = "CREATED"
            if phase == "activate" and not bindings:
                raise AcademicV23Refused("Inactive bindings must be staged first.")
            if bindings:
                if not restated_done:
                    raise AcademicV23Refused("Bindings exist without the definition restatements.")
                active = all(b.is_active for b in bindings)
                if any(b.is_active for b in bindings) and not active:
                    raise AcademicV23Refused("Partially active bindings are refused; no automatic repair.")
                if active != finance_active:
                    raise AcademicV23Refused("Service and binding activation states differ; no automatic repair.")
                if phase == "activate" and not active:
                    _verify_bindings(bindings, roles, permissions, actor, active=False)
                    Service.objects.filter(pk=finance.pk, is_active=False).update(is_active=True)
                    record_access_audit_receipt(actor=actor, action=EVENTS["service_activate"],
                                                old_value={"service_id": finance.pk, "is_active": False},
                                                new_value={"service_id": finance.pk, "is_active": True}, reason="permission_change")
                    for binding in bindings:
                        RolePermission.objects.filter(pk=binding.pk, is_active=False).update(is_active=True)
                        record_access_audit_receipt(actor=actor, role=binding.role, permission=binding.permission,
                                                    action=EVENTS["binding_activate"],
                                                    old_value={"role_permission_id": binding.pk, "is_active": False},
                                                    new_value={"role_permission_id": binding.pk, "is_active": True},
                                                    reason="permission_change")
                    finance = Service.objects.get(pk=finance.pk)
                    bindings = _scoped_bindings(permissions)
                    active = finance_active = True
                    result = "ACTIVATED"
                _verify_metadata(finance, permissions, service_def, definitions, academic, actor, active=finance_active)
                _verify_bindings(bindings, roles, permissions, actor, active=active)
                if active:
                    _verify_service_activation(finance, actor)
                    _effective(roles)
            elif finance_active:
                raise AcademicV23Refused("An active finance service without staged bindings is refused.")
            if phase == "verify" and not (bindings and finance_active):
                result = "INCOMPLETE"
            _prior_phases_complete()  # phase 1 still verifies, accepting exactly the receipted restatements
            if _snapshot_outside_scope(finance.pk, [p.pk for p in permissions.values()], [p.pk for p in restated.values()],
                                       [b.pk for b in bindings]) != before:
                raise AcademicV23Refused("State outside the authorized v2.3 scope changed.")
            authorization_basis()
            catalogue()
        return result
    finally:
        with db.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", [LOCK_NAME])


class Command(BaseCommand):
    help = "LOCAL DEV ONLY: governed WF-11.01 catalogue v2.3 provisioning (requires the recorded independent approval)."

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
            raise CommandError("WF-11.01 v2.3: refused or rolled back; no success reported. "
                               "Inspect the current state before retrying.") from exc
        self.stdout.write(f"WF-11.01 v2.3 {options['phase']}: {result}; services=1; definitions=5; restated=2; "
                          f"bindings=5; no other change; basis={authorization_basis()} (independent review stays OPEN "
                          "unless independently approved)")
