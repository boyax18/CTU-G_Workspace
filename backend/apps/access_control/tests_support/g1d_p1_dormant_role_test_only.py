"""G1D-P1 disposable-MySQL role-creation demonstration ONLY.

No live initializer, CLI write command, URL, grant or activation. An explicit
settings + actual connected test-schema guard runs BEFORE any ORM write.
DO NOT import this module from operational application code.
"""

import re

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connections, transaction

from apps.access_control.delegation import is_reserved_role
from apps.access_control.management.commands.init_system_roles import SYSTEM_ROLES
from apps.access_control.management.commands.report_technical_governance_g0 import PROPOSED_CORE_K
from apps.access_control.models import AccountPermission, AccountRole, Permission, Role, RolePermission


TECHNICAL_ROLE_NAME = "Technical Super Admin"
# Fixture description only; NOT an approved live metadata payload.
TEST_ONLY_DESCRIPTION = "TEST FIXTURE: protected role inactive; no permissions or assignments."
_SCHEMA_PATTERN = re.compile(r"test_ctug_registration_[0-9a-f]{16}\Z", re.ASCII)


class TestOnlyRoleProvisioningRefused(RuntimeError):
    """A safe refusal, never a signal to fall back to a live initializer."""


def _require_disposable_mysql():
    configured = settings.DATABASES[DEFAULT_DB_ALIAS]
    expected = getattr(settings, "REGISTRATION_TEST_DATABASE", None)
    if (
        settings.SETTINGS_MODULE != "config.test_settings"
        or type(expected) is not str
        or _SCHEMA_PATTERN.fullmatch(expected) is None
        or configured.get("ENGINE") != "django.db.backends.mysql"
        or configured.get("HOST") not in {"localhost", "127.0.0.1", "::1"}
        or configured.get("NAME") != expected
        or configured.get("TEST", {}).get("NAME") != expected
    ):
        raise TestOnlyRoleProvisioningRefused("G1D-P1 requires disposable MySQL test settings.")
    connection = connections[DEFAULT_DB_ALIAS]
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        actual = cursor.fetchone()[0]
    if actual != expected:
        raise TestOnlyRoleProvisioningRefused("Actual connected schema is not the disposable test schema.")
    return DEFAULT_DB_ALIAS


def create_inactive_technical_role_fixture_test_only(*, ack):
    """Write ONE dormant fixture role in the disposable test DB; refuse any drift.

    Deliberately NOT idempotent: existing roles or variants are errors, not
    success. No account assignment, role binding, privilege or audit is created.
    This is not suitable for real provisioner concurrency or audit semantics.
    """
    if ack != "G1D_P1_DISPOSABLE_ONLY":
        raise TestOnlyRoleProvisioningRefused("Explicit disposable-test acknowledgement required.")
    alias = _require_disposable_mysql()
    if tuple(name for name, _description in SYSTEM_ROLES) != (
        "Student", "Instructor", "Treasurer", "Admin"
    ):
        raise TestOnlyRoleProvisioningRefused("Normal role initializer changed; review first.")

    with transaction.atomic(using=alias):
        names = list(Role.objects.using(alias).values_list("role_name", flat=True))
        if names.count("Admin") != 1 or not Role.objects.using(alias).get(role_name="Admin").is_active:
            raise TestOnlyRoleProvisioningRefused("Exactly one active canonical Admin role required.")
        if any(is_reserved_role(name) and name != "Admin" for name in names):
            raise TestOnlyRoleProvisioningRefused("Protected role already exists or has a lookalike alias.")
        if AccountRole.objects.using(alias).filter(role__role_name=TECHNICAL_ROLE_NAME).exists():
            raise TestOnlyRoleProvisioningRefused("Protected role assignments unexpectedly exist.")
        if RolePermission.objects.using(alias).filter(role__role_name=TECHNICAL_ROLE_NAME).exists():
            raise TestOnlyRoleProvisioningRefused("Protected role bindings unexpectedly exist.")
        if Permission.objects.using(alias).filter(permission_code__in=PROPOSED_CORE_K).exists():
            raise TestOnlyRoleProvisioningRefused("Core K metadata already exists; stop and reconcile.")
        if AccountPermission.objects.using(alias).filter(
            permission__service__service_code="access_control", is_active=True
        ).exists():
            raise TestOnlyRoleProvisioningRefused("Existing direct governance overrides require reconciliation.")
        role = Role.objects.using(alias).create(
            role_name=TECHNICAL_ROLE_NAME,
            description=TEST_ONLY_DESCRIPTION,
            is_active=False,
        )
        if role.is_active or AccountRole.objects.using(alias).filter(role=role).exists():
            raise TestOnlyRoleProvisioningRefused("Fixture was not dormant; transaction rolled back.")
        if RolePermission.objects.using(alias).filter(role=role).exists():
            raise TestOnlyRoleProvisioningRefused("Unexpected fixture role grant; transaction rolled back.")
        return role
