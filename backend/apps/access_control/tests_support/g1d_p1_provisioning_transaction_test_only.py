"""G1D-P1: guarded disposable-MySQL role + audit atomicity demonstration.

DO NOT import in operational code. It cannot connect to real ctug_workspace,
and its HMAC approvals are fictional tests, not institutional authorization.
The real P1 command has no enabled apply path.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connections, transaction

from apps.accounts.models import Account
from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.delegation import is_reserved_role
from apps.access_control.management.commands.init_system_roles import SYSTEM_ROLES
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission,
)
from apps.access_control.tests_support.g1b_catalogue_test_only import CORE_K_CODES
from .g1d_p1_signed_evidence_test_only import (
    ROLE_NAME, ROLE_DESCRIPTION, fictional_independent_approval_issues,
)


_DB_RE = re.compile(r"test_ctug_registration_[0-9a-f]{16}\Z", re.ASCII)
_ACTION = "technical_admin.role_metadata.create"


class P1TestOnlyRefused(RuntimeError):
    """Safe denial; no live or permissive fallback is defined."""


@dataclass(frozen=True)
class P1TestOnlyReceipt:
    role_id: int
    audit_id: int


def _disposable_database_only():
    configured = settings.DATABASES[DEFAULT_DB_ALIAS]
    expected = getattr(settings, "REGISTRATION_TEST_DATABASE", None)
    if (
        settings.SETTINGS_MODULE != "config.test_settings"
        or type(expected) is not str or _DB_RE.fullmatch(expected) is None
        or configured.get("ENGINE") != "django.db.backends.mysql"
        or configured.get("HOST") not in {"localhost", "127.0.0.1", "::1"}
        or configured.get("NAME") != expected
        or configured.get("TEST", {}).get("NAME") != expected
    ):
        raise P1TestOnlyRefused("P1 applies only inside a disposable MySQL test schema.")
    with connections[DEFAULT_DB_ALIAS].cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        actual = cursor.fetchone()[0]
    if actual != expected:
        raise P1TestOnlyRefused("Connected schema is not the disposable MySQL test schema.")
    return expected


def current_pre_state_sha256_test_only(*, executor_account_id):
    """Read-only snapshot for the disposable P1 exact-state ticket fixture.

    This is NOT a signed institutional preflight or a complete concurrency lock.
    """
    _disposable_database_only()
    alias = DEFAULT_DB_ALIAS
    if type(executor_account_id) is not int or executor_account_id <= 0:
        raise P1TestOnlyRefused("Invalid executor ID for before-state fingerprint.")
    actor = Account.objects.using(alias).filter(pk=executor_account_id).values(
        "account_id", "request_status", "is_active"
    ).first()
    snapshot = {
        "executor": actor,
        "roles": list(Role.objects.using(alias).order_by("role_id").values_list(
            "role_id", "role_name", "is_active"
        )),
        "admin_assignments": list(AccountRole.objects.using(alias).filter(
            role__role_name="Admin"
        ).order_by("account_id").values_list("account_id", "role_id")),
        "technical_assignments": AccountRole.objects.using(alias).filter(
            role__role_name=ROLE_NAME
        ).count(),
        "technical_bindings": RolePermission.objects.using(alias).filter(
            role__role_name=ROLE_NAME
        ).count(),
        "installed_core_codes": list(Permission.objects.using(alias).filter(
            permission_code__in=CORE_K_CODES
        ).order_by("permission_code").values_list("permission_code", flat=True)),
        "active_governance_overrides": AccountPermission.objects.using(alias).filter(
            permission__service__service_code="access_control", is_active=True
        ).count(),
    }
    return hashlib.sha256(json.dumps(
        snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")).hexdigest()


def create_dormant_role_and_audit_test_only(*, actor, evidence, trusted_test_signers, ack, now=None):
    """Single all-or-nothing INSERT of dormant Role and audit, test DB only.

    Does not create a durable one-use approval ledger, verify real signers or
    authorize a production operation. The canonical Admin row serializes
    calls *using this function*; it cannot serialize unrelated writers.
    """
    if ack != "G1D_P1_ATOMIC_DISPOSABLE_ONLY":
        raise P1TestOnlyRefused("Explicit test-only acknowledgement required.")
    expected = _disposable_database_only()  # guarded BEFORE ANY write
    if type(actor) is not Account or actor._state.adding or actor._state.db != DEFAULT_DB_ALIAS:
        raise P1TestOnlyRefused("Persisted actor from disposable database required.")
    if type(actor.pk) is not int:
        raise P1TestOnlyRefused("Invalid actor identifier.")
    if now is None:
        now = datetime.now(timezone.utc)
    problems = fictional_independent_approval_issues(
        evidence, now=now, expected_schema=expected,
        expected_executor_id=actor.pk, trusted_test_signers=trusted_test_signers,
    )
    if problems:
        raise P1TestOnlyRefused("Fictional independent approval contract refused: " + ", ".join(problems))
    if tuple(name for name, _ in SYSTEM_ROLES) != ("Student", "Instructor", "Treasurer", "Admin"):
        raise P1TestOnlyRefused("General role initializer drift detected.")

    alias = DEFAULT_DB_ALIAS
    with transaction.atomic(using=alias, durable=True):
        # Serialize multiple trusted initializers on one existing stable row.
        # MySQL UNIQUE(roles.role_name) is the final uniqueness guard.
        admin = Role.objects.using(alias).select_for_update().filter(role_name="Admin").first()
        if admin is None or admin.role_name != "Admin" or not admin.is_active:
            raise P1TestOnlyRefused("Canonical active Admin role is missing.")
        # Validate the *same* state that was bound into the fictional ticket,
        # after acquiring the stable serialization lock.
        actual_before = current_pre_state_sha256_test_only(executor_account_id=actor.pk)
        if evidence.request.before_sha256 != actual_before:
            raise P1TestOnlyRefused("Pre-state changed since the fictional approval; refuse.")
        locked_actor = Account.objects.using(alias).select_for_update().filter(pk=actor.pk).first()
        if (
            locked_actor is None or not locked_actor.is_active
            or locked_actor.request_status != "Approved"
            or not AccountRole.objects.using(alias).filter(account=locked_actor, role=admin).exists()
        ):
            raise P1TestOnlyRefused("Trusted active Approved Normal Admin executor required.")
        role_names = list(Role.objects.using(alias).values_list("role_name", flat=True))
        if role_names.count("Admin") != 1 or any(is_reserved_role(name) and name != "Admin" for name in role_names):
            raise P1TestOnlyRefused("Protected role or alias exists; no upsert is permitted.")
        if Permission.objects.using(alias).filter(permission_code__in=CORE_K_CODES).exists():
            raise P1TestOnlyRefused("Governance catalogue drift; stop.")
        if AccountPermission.objects.using(alias).filter(
            permission__service__service_code="access_control", is_active=True
        ).exists():
            raise P1TestOnlyRefused("Governance overrides exist; stop.")
        if AccountRole.objects.using(alias).filter(role__role_name=ROLE_NAME).exists():
            raise P1TestOnlyRefused("Protected role already assigned; stop.")
        if RolePermission.objects.using(alias).filter(role__role_name=ROLE_NAME).exists():
            raise P1TestOnlyRefused("Protected role has grants; stop.")

        role = Role.objects.using(alias).create(
            role_name=ROLE_NAME, description=ROLE_DESCRIPTION, is_active=False
        )
        # Existing audit primitive uses no arbitrary evidence strings; no PII.
        audit_id = record_access_audit_receipt(
            actor=locked_actor, role=role, action=_ACTION,
            old_value=None, new_value={"role_id": role.pk, "is_active": False},
            reason="policy_enforcement",
        )
        if (
            role.is_active
            or AccountRole.objects.using(alias).filter(role=role).exists()
            or RolePermission.objects.using(alias).filter(role=role).exists()
            or not AccessAuditLog.objects.using(alias).filter(
                pk=audit_id, role=role, actor_account=locked_actor, action=_ACTION
            ).exists()
        ):
            raise P1TestOnlyRefused("Postcondition failed; role + audit transaction rolled back.")
    # Only return a receipt AFTER the owning atomic block has committed.
    return P1TestOnlyReceipt(role_id=role.pk, audit_id=audit_id)
