"""Synthetic LAN development database: target checks, one-time setup and preflight.

Every function refuses to run unless Django is configured with
config.dev_lan_settings AND the connected MySQL schema is the hard-named
synthetic database carrying the synthetic marker row. ``ctug_workspace`` can
never be selected, created, migrated, seeded or reset from here.

* ``initialize`` (explicit, one-time): create the schema, write the marker, apply
  the repository migrations to THIS schema only, seed synthetic roles/accounts,
  and seed the catalogue permissions of registry-approved features.
* ``sync_catalogue`` (every startup, additive and idempotent): create only missing
  permission definitions for newly approved features, with their pinned catalogue
  default bindings and audit receipts. It never deletes or resets anything; a
  binding removed on purpose is not re-added once its permission exists.
* ``preflight`` (every startup): read-only readiness report for the launcher.

No password, key or secret value is printed, logged or returned.
"""

import secrets
from pathlib import Path

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from config import dev_features
from config.dev_lan_environment import SYNTHETIC_EMAIL_DOMAIN
from config.lan_role_context import LAN_ACK, SYNTHETIC_LAN_DATABASE

MARKER_TABLE = "ctug_dev_synthetic_marker"
MARKER_PROFILE = dev_features.LAN_SYNTHETIC
OPERATOR_ID = "LAN-TECHADMIN-01"
CREDENTIALS_PARTS = (".local", "ctug-lan", "synthetic-accounts.txt")
AUDIT_ACTION = "dev.synthetic.role_binding.create"
# Frontend listener (relative to frontend/): the existing Option A per-address Vite server.
FRONTEND_SCRIPT = "scripts/wf03_optiona_multi_vite.mjs"

# (school_id, role assignments, requested base role). Purely fictional records.
STAFF_ACCOUNTS = (
    ("LAN-SCHOOLADMIN-01", ("Admin",), "Instructor"),
    (OPERATOR_ID, ("Admin", "Technical Super Admin"), "Instructor"),
    ("LAN-INSTRUCTOR-01", ("Instructor",), "Instructor"),
    ("LAN-INSTRUCTOR-02", ("Instructor",), "Instructor"),
    ("LAN-STUDENT-01", ("Student",), "Student"),
    ("LAN-STUDENT-02", ("Student",), "Student"),
    ("LAN-STUDENT-03", ("Student",), "Student"),
    ("LAN-TREASURER-01", ("Student", "Treasurer"), "Student"),
)
PENDING_STUDENTS = 16
PENDING_INSTRUCTORS = 8


class DevLanRefused(RuntimeError):
    """The synthetic target could not be proven; nothing was written."""


# ---------------------------------------------------------------- target checks
def _configured_name():
    return settings.DATABASES[DEFAULT_DB_ALIAS]["NAME"]


def verify_profile():
    if (getattr(settings, "SETTINGS_MODULE", "") != "config.dev_lan_settings"
            or getattr(settings, "WORKSPACE_DEV_PROFILE", None) != MARKER_PROFILE
            or _configured_name() != SYNTHETIC_LAN_DATABASE
            or settings.DATABASES[DEFAULT_DB_ALIAS].get("HOST") not in ("127.0.0.1", "localhost", "::1")):
        raise DevLanRefused("Not the synthetic LAN profile; refusing to touch any database.")


def _selected_schema():
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        return cursor.fetchone()[0]


def _marker_present():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s",
            [MARKER_TABLE],
        )
        if cursor.fetchone()[0] != 1:
            return False
        cursor.execute(f"SELECT profile FROM {MARKER_TABLE} WHERE marker_id = 1")
        row = cursor.fetchone()
    return bool(row) and row[0] == MARKER_PROFILE


def verify_target():
    """Prove the connection is the marked synthetic schema before any read or write."""
    verify_profile()
    if _selected_schema() != SYNTHETIC_LAN_DATABASE:
        raise DevLanRefused("Connected schema is not the synthetic database.")
    if not _marker_present():
        raise DevLanRefused(
            "The synthetic marker is missing. Run .\\Initialize-CTUG-LAN.ps1 (it never adopts an unmarked schema)."
        )


def _schema_state(name):
    """Return (exists, table_count, marked) without selecting the schema."""
    with connection.creation._nodb_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s", [name])
        exists = cursor.fetchone()[0] == 1
        if not exists:
            return False, 0, False
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s", [name])
        tables = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
            [name, MARKER_TABLE],
        )
        marked = cursor.fetchone()[0] == 1
    return exists, tables, marked


def pending_migrations():
    executor = MigrationExecutor(connection)
    return executor.migration_plan(executor.loader.graph.leaf_nodes())


# ---------------------------------------------------------------- initialization
def prepare_schema(*, reset=False):
    """Create (or, only on explicit reset, recreate) the marked synthetic schema."""
    verify_profile()
    name = SYNTHETIC_LAN_DATABASE
    exists, tables, marked = _schema_state(name)
    quoted = connection.ops.quote_name(name)
    if exists and not marked and tables:
        raise DevLanRefused(f"{name} exists without the synthetic marker; it was left untouched.")
    with connection.creation._nodb_cursor() as cursor:
        if reset and exists:
            if not marked:
                raise DevLanRefused("Reset refused: the schema is not marked synthetic.")
            cursor.execute(f"DROP DATABASE {quoted}")
            exists = False
        if not exists:
            cursor.execute(f"CREATE DATABASE {quoted} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    connection.close()
    if _selected_schema() != name:
        raise DevLanRefused("Connected schema is not the synthetic database.")
    with connection.cursor() as cursor:
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {MARKER_TABLE} (marker_id TINYINT UNSIGNED PRIMARY KEY, "
            "profile VARCHAR(40) NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        cursor.execute(f"INSERT IGNORE INTO {MARKER_TABLE} (marker_id, profile) VALUES (1, %s)", [MARKER_PROFILE])
    verify_target()
    return "recreated" if reset else ("created" if not tables else "existing")


def _catalogue():
    from apps.access_control.catalogue.validation_v2_2 import validate_catalogue
    return validate_catalogue().data


def credentials_file():
    return Path(settings.BASE_DIR).parent.joinpath(*CREDENTIALS_PARTS)


def _synthetic_password():
    """One local, random, git-ignored password shared by all synthetic accounts."""
    path = credentials_file()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("PASSWORD="):
                return line.split("=", 1)[1]
    password = "Lan-" + secrets.token_urlsafe(12)
    path.parent.mkdir(parents=True, exist_ok=True)
    accounts = [sid for sid, _roles, _req in STAFF_ACCOUNTS]
    path.write_text(
        "# CTU-G Workspace synthetic LAN accounts (development only, never real people).\n"
        "# Do not reuse this password anywhere. Git-ignored; regenerate with -Reset.\n"
        f"PASSWORD={password}\n"
        + "".join(f"ACCOUNT={sid}\n" for sid in accounts),
        encoding="utf-8",
    )
    return password


def _email(school_id):
    return f"{school_id.lower()}@{SYNTHETIC_EMAIL_DOMAIN}"


def _ensure_account(school_id, *, password, requested, roles, role_names, status, assigned_by=None):
    from apps.access_control.models import AccountRole
    from .models import Account, UserProfile

    if Account.objects.filter(school_id=school_id).exists():
        return False
    account = Account.objects.create_user(
        school_id=school_id, email=_email(school_id), password=password, requested_role=roles[requested],
    )
    Account.objects.filter(pk=account.pk).update(
        request_status=status, is_active=(status == "Approved"),
        email_verified_at=timezone.now(), email_verified_address=_email(school_id),
    )
    label = school_id.replace("LAN-", "").replace("-", " ").title()
    UserProfile.objects.create(account=account, first_name="Synthetic", last_name=label)
    for name in role_names:
        AccountRole.objects.create(account=account, role=roles[name], assigned_by=assigned_by)
    return True


def seed_synthetic_data():
    """Create any missing synthetic roles, services and accounts (never resets existing rows)."""
    from apps.access_control.models import Role, Service
    from .models import Account

    verify_target()
    data = _catalogue()
    password = _synthetic_password()
    created = {"roles": 0, "services": 0, "accounts": 0, "pending_applicants": 0}
    with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
        verify_target()
        for item in data["roles"]:
            _role, new = Role.objects.get_or_create(
                role_name=item["role_name"], defaults={"description": item.get("description"), "is_active": True})
            created["roles"] += new
        for item in data["services"]:
            if item["service_code"] in ("accounts", "access_control"):
                _service, new = Service.objects.get_or_create(
                    service_code=item["service_code"],
                    defaults={"service_name": item["service_name"], "description": item.get("description"),
                              "is_active": True})
                created["services"] += new
        roles = {role.role_name: role for role in Role.objects.all()}
        for school_id, role_names, requested in STAFF_ACCOUNTS:
            created["accounts"] += _ensure_account(
                school_id, password=password, requested=requested, roles=roles,
                role_names=role_names, status="Approved")
        # Top up the pending pool to its target size with fresh IDs; decided applicants
        # (approved, or rejected and deleted) are never reverted or reused.
        for prefix, requested, target in (("S", "Student", PENDING_STUDENTS), ("I", "Instructor", PENDING_INSTRUCTORS)):
            pending = Account.objects.filter(request_status="Pending", requested_role=roles[requested],
                                             school_id__startswith=f"LAN-APPLICANT-{prefix}").count()
            number = 0
            while pending < target:
                number += 1
                school_id = f"LAN-APPLICANT-{prefix}{number:03d}"
                if _ensure_account(school_id, password=password, requested=requested,
                                   roles=roles, role_names=(), status="Pending"):
                    pending += 1
                    created["pending_applicants"] += 1
    return created


def sync_catalogue():
    """Additively create catalogue permissions for registry-approved features (synthetic DB only)."""
    from apps.access_control.audit import record_access_audit_receipt
    from apps.access_control.models import Permission, Role, RolePermission, Service
    from .models import Account

    verify_target()
    codes = dev_features.profile_permission_codes(MARKER_PROFILE)
    data = _catalogue()
    definitions = {item["permission_code"]: item for item in data["permissions"]}
    services = {item["service_code"]: item for item in data["services"]}
    unknown = [code for code in codes if code not in definitions]
    if unknown:
        raise DevLanRefused("Registered permission codes are not in the validated catalogue: " + ", ".join(unknown))
    missing = [code for code in codes if not Permission.objects.filter(permission_code=code).exists()]
    if not missing:
        return {"permissions": 0, "bindings": 0}
    operator = Account.objects.filter(school_id=OPERATOR_ID, request_status="Approved", is_active=True).first()
    if operator is None:
        raise DevLanRefused("Synthetic operator account is missing; run .\\Initialize-CTUG-LAN.ps1.")
    created = {"permissions": 0, "bindings": 0}
    with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
        verify_target()
        for code in missing:
            item = definitions[code]
            service, _new = Service.objects.get_or_create(
                service_code=item["service_code"],
                defaults={"service_name": services[item["service_code"]]["service_name"],
                          "description": services[item["service_code"]].get("description"), "is_active": True})
            permission, new = Permission.objects.get_or_create(
                permission_code=code,
                defaults={"service": service, "permission_name": item["permission_name"][:100],
                          "module_name": item["module_name"], "action_name": item["action_name"],
                          "description": (item.get("description") or "")[:255] or None})
            if not new:
                continue
            created["permissions"] += 1
            for binding in data["default_bindings"]:
                if binding["permission_code"] != code:
                    continue
                role = Role.objects.filter(role_name=binding["role_name"]).first()
                if role is None:
                    continue
                row = RolePermission.objects.create(role=role, permission=permission, is_active=True,
                                                    granted_by=operator)
                record_access_audit_receipt(
                    actor=operator, role=role, permission=permission, action=AUDIT_ACTION, old_value=None,
                    new_value={"role_id": role.pk, "permission_id": permission.pk,
                               "role_permission_id": row.pk, "is_active": True},
                    reason="permission_change",
                )
                created["bindings"] += 1
    return created


# ---------------------------------------------------------------- preflight
def _prerequisite_failures(item):
    from apps.access_control.models import Permission, Service
    from .outbox_crypto import outbox_encryption_ready

    reasons = []
    for name in item.prerequisites:
        if name == "core_services":
            active = set(Service.objects.filter(service_code__in=("accounts", "access_control"), is_active=True)
                         .values_list("service_code", flat=True))
            if active != {"accounts", "access_control"}:
                reasons.append("accounts/access_control services are not active")
        elif name == "catalogue_permissions":
            present = set(Permission.objects.filter(permission_code__in=item.permissions)
                          .values_list("permission_code", flat=True))
            if present != set(item.permissions):
                reasons.append("catalogue permissions are missing")
        elif name == "outbox_encryption":
            if not outbox_encryption_ready():
                reasons.append("outbox encryption key or dependency is unavailable")
        else:
            reasons.append(f"unknown prerequisite {name}")
    return reasons


def preflight(*, sync=True):
    """Return the launcher's readiness report. Only ``sync_catalogue`` may write (additively)."""
    from .models import Account

    report = {"ok": False, "profile": MARKER_PROFILE, "database": _configured_name(), "errors": [],
              "warnings": [], "features": [], "frontend_env": {}, "lan_ip": None, "role_context": False}
    try:
        verify_target()
    except DevLanRefused as exc:
        report["errors"].append(str(exc))
        return report
    except Exception as exc:  # connection failures: type only, never credentials
        report["errors"].append(f"Synthetic database connection failed ({type(exc).__name__}). Is MySQL running?")
        return report
    report["database_verified"] = True
    if pending_migrations():
        report["errors"].append("The synthetic database schema is behind the code. Run .\\Initialize-CTUG-LAN.ps1.")
        return report
    if sync:
        try:
            report["catalogue_sync"] = sync_catalogue()
        except DevLanRefused as exc:
            report["errors"].append(str(exc))
            return report

    approved = dev_features.approved_keys(MARKER_PROFILE)
    failures = {item.key: _prerequisite_failures(item) for item in dev_features.FEATURES if item.key in approved}
    available = dev_features.available_keys(MARKER_PROFILE, failures)
    for item in dev_features.FEATURES:
        if item.key in available:
            status, reasons = "available", []
        elif item.key in approved:
            status = "blocked"
            reasons = failures.get(item.key) or ["a required feature is unavailable: " + ", ".join(item.requires)]
        else:
            status, reasons = "not-approved", [item.note] if item.note else []
        report["features"].append({"key": item.key, "workflow": item.workflow, "title": item.title,
                                   "status": status, "reasons": reasons})

    lan_ip = getattr(settings, "WORKSPACE_ROLE_CONTEXT_LAN_DEV_IP", None)
    report["lan_ip"] = lan_ip
    report["role_context"] = bool(getattr(settings, "WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED", False))
    report["frontend_env"] = dev_features.frontend_environment(available)
    report["frontend_script"] = FRONTEND_SCRIPT
    if lan_ip:
        # Consumed by frontend/scripts/wf03_optiona_multi_vite.mjs (Option A listener).
        report["frontend_env"].update({
            "CTUG_ROLE_CONTEXT_LAN_DEV_ACK": LAN_ACK,
            "CTUG_ROLE_CONTEXT_LAN_DEV_IPS": lan_ip,
            "CTUG_API_TARGET": "http://127.0.0.1:8000",
        })
    else:
        report["errors"].append("No LAN address is configured for this profile (CTUG_DEV_LAN_IP).")

    foreign = (Account.objects.exclude(email__isnull=True).exclude(email="")
               .exclude(email__iendswith="@" + SYNTHETIC_EMAIL_DOMAIN).count())
    if foreign:
        report["warnings"].append(
            f"{foreign} account(s) use non-synthetic email addresses (registered over LAN). "
            "Use only synthetic data on HTTP LAN.")
    pending = Account.objects.filter(request_status="Pending", is_active=False).count()
    if pending == 0:
        report["warnings"].append("No pending synthetic applicants remain. Re-run .\\Initialize-CTUG-LAN.ps1 to top up.")
    report["pending_applicants"] = pending
    report["ok"] = not report["errors"]
    return report
