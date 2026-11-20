"""G1D-P0: read-only inventory of the MISSING protected Technical Super Admin role.

Local development only. This report never creates role metadata, permissions,
accounts, audit records or approval evidence, and cannot authorize a P1 write.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections

from apps.access_control.delegation import is_reserved_role
from apps.access_control.management.commands.init_system_roles import SYSTEM_ROLES
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service,
)
from apps.access_control.management.commands.report_technical_governance_g0 import PROPOSED_CORE_K


class Command(BaseCommand):
    help = "G1D P0 SELECT-only local inventory; no protected role or grant creation."

    def add_arguments(self, parser):
        parser.add_argument("--expected-db", required=True)
        parser.add_argument("--ack", required=True)

    def handle(self, *args, **options):
        configured = settings.DATABASES[DEFAULT_DB_ALIAS]
        if (
            settings.SETTINGS_MODULE != "config.settings"
            or settings.DEBUG is not True
            or configured.get("ENGINE") != "django.db.backends.mysql"
            or configured.get("HOST") not in {"localhost", "127.0.0.1", "::1"}
            or configured.get("NAME") != "ctug_workspace"
            or options["expected_db"] != "ctug_workspace"
            or options["ack"] != "G1D_P0_READ_ONLY"
        ):
            raise CommandError("G1D-P0 refuses execution outside the exact read-only local scope.")

        try:
            with connections[DEFAULT_DB_ALIAS].cursor() as cursor:
                cursor.execute("SELECT DATABASE()")
                actual_db = cursor.fetchone()[0]
            if actual_db != "ctug_workspace":
                raise CommandError("Connected schema is not the approved read-only target.")

            role_names = list(Role.objects.using(DEFAULT_DB_ALIAS).values_list("role_name", flat=True))
            canonical_admin_count = sum(name == "Admin" for name in role_names)
            canonical_technical_count = sum(name == "Technical Super Admin" for name in role_names)
            protected_aliases = [
                name for name in role_names
                if is_reserved_role(name) and name not in {"Admin", "Technical Super Admin"}
            ]
            admin = Role.objects.using(DEFAULT_DB_ALIAS).filter(role_name="Admin").first()
            # P0 checks all records, not only active records. It cannot repair drift.
            assignments = AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(
                role__role_name="Technical Super Admin"
            ).count()
            bindings = RolePermission.objects.using(DEFAULT_DB_ALIAS).filter(
                role__role_name="Technical Super Admin"
            ).count()
            direct_governance = AccountPermission.objects.using(DEFAULT_DB_ALIAS).filter(
                permission__service__service_code="access_control", is_active=True
            ).count()
            catalogue_rows = list(Permission.objects.using(DEFAULT_DB_ALIAS).values_list(
                "permission_code", flat=True
            ))
            core_present = [code for code in PROPOSED_CORE_K if code in catalogue_rows]
            active_governance_services = Service.objects.using(DEFAULT_DB_ALIAS).filter(
                service_code="access_control", is_active=True
            ).count()
            audit_rows = AccessAuditLog.objects.using(DEFAULT_DB_ALIAS).count()
        except DatabaseError as exc:
            raise CommandError("G1D-P0 inventory failed without performing any writes.") from exc

        initializer_names = tuple(name for name, _description in SYSTEM_ROLES)
        initializer_unchanged = initializer_names == ("Student", "Instructor", "Treasurer", "Admin")
        issues = []
        if canonical_admin_count != 1 or admin is None or not admin.is_active:
            issues.append("expected one active canonical Admin role")
        if canonical_technical_count != 0:
            issues.append("protected technical role already exists; reconcile before P1")
        if protected_aliases:
            issues.append("noncanonical protected role names detected")
        if assignments or bindings:
            issues.append("unexpected technical assignments or role bindings")
        if direct_governance:
            issues.append("existing direct governance overrides require reconciliation")
        if core_present:
            issues.append("some proposed Core K metadata exists; reconcile before P1")
        if not initializer_unchanged:
            issues.append("general system-role initializer differs from source contract")

        self.stdout.write("G1D-P0: READ-ONLY TECHNICAL SUPER ADMIN ROLE READINESS")
        self.stdout.write("Target: local development MySQL ctug_workspace")
        self.stdout.write(f"Canonical Admin records: {canonical_admin_count}")
        self.stdout.write(f"Canonical Technical Super Admin records: {canonical_technical_count}")
        self.stdout.write(f"Noncanonical protected role aliases: {len(protected_aliases)}")
        self.stdout.write(f"Technical role assignments (all states): {assignments}")
        self.stdout.write(f"Technical role bindings (all states): {bindings}")
        self.stdout.write(f"Active direct governance overrides: {direct_governance}")
        self.stdout.write(f"Proposed Core K codes already installed: {len(core_present)} of {len(PROPOSED_CORE_K)}")
        self.stdout.write(f"Active access_control services: {active_governance_services}")
        self.stdout.write(f"Existing audit records: {audit_rows}")
        self.stdout.write(f"Ordinary init_system_roles unchanged: {initializer_unchanged}")
        self.stdout.write("Backup/restore, independent authorization and live-write readiness: NOT VERIFIED")
        self.stdout.write("NO ROLE, GRANT, ASSIGNMENT, AUDIT OR OTHER DATABASE WRITE EXECUTED.")
        if issues:
            raise CommandError("G1D-P0 requires reconciliation: " + "; ".join(issues))
        self.stdout.write(self.style.SUCCESS("G1D-P0 READ-ONLY INVENTORY PASSED (NOT P1 AUTHORIZATION)."))
