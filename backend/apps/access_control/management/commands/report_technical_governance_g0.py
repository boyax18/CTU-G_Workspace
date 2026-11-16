"""G0: exact-scope SELECT-only inventory. Not a protected governance authorizer.

Candidate catalogue codes shown here are PROPOSALS, not approved seeded/granted
permissions. No role, account, permission, audit, or approval evidence is changed.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections

from apps.access_control.models import AccountPermission, AccountRole, Permission, Role, RolePermission, Service


# G1-G5 policy proposal only. Deliberately NOT installed as a live catalogue.
PROPOSED_CORE_K = (
    "access_control.catalogue.read",
    "access_control.role_permissions.manage",
    "access_control.account_permissions.manage",
    "access_control.effective_permissions.inspect",
    "access_control.audit.read",
    "access_control.admin_assignments.manage",
)


class Command(BaseCommand):
    help = "SELECT-only governance catalogue inventory on the exact local development database."

    def add_arguments(self, parser):
        parser.add_argument("--expected-db", required=True)
        parser.add_argument("--ack", required=True)

    def handle(self, *args, **options):
        config = settings.DATABASES[DEFAULT_DB_ALIAS]
        if (
            settings.SETTINGS_MODULE != "config.settings"
            or settings.DEBUG is not True
            or config.get("ENGINE") != "django.db.backends.mysql"
            or config.get("NAME") != "ctug_workspace"
            or config.get("HOST") not in {"localhost", "127.0.0.1", "::1"}
            or options["expected_db"] != "ctug_workspace"
            or options["ack"] != "READ_ONLY_G0"
        ):
            raise CommandError("G0 refuses execution outside the exact local read-only scope.")

        try:
            with connections[DEFAULT_DB_ALIAS].cursor() as cursor:
                cursor.execute("SELECT DATABASE()")
                if cursor.fetchone()[0] != "ctug_workspace":
                    raise CommandError("Connected MySQL schema differs from the exact approved read-only target.")

            roles = list(Role.objects.using(DEFAULT_DB_ALIAS).values_list("role_name", flat=True))
            admin_exact = sum(name == "Admin" for name in roles)
            technical_exact = sum(name == "Technical Super Admin" for name in roles)
            if admin_exact != 1 or technical_exact > 1:
                raise CommandError("Protected role catalogue is inconsistent; stop and reconcile.")

            # Detect MySQL-collation variations: do not mistake lookalike role labels for authorization.
            from apps.access_control.delegation import is_reserved_role

            if any(is_reserved_role(name) and name not in {"Admin", "Technical Super Admin"} for name in roles):
                raise CommandError("Noncanonical protected role alias detected; stop and reconcile.")

            technical_assignments = AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(
                role__role_name="Technical Super Admin"
            ).count()
            technical_role_grants = RolePermission.objects.using(DEFAULT_DB_ALIAS).filter(
                role__role_name="Technical Super Admin", is_active=True
            ).count()
            protected_overrides = AccountPermission.objects.using(DEFAULT_DB_ALIAS).filter(
                permission__service__service_code="access_control", is_active=True
            ).count()
            governance_services = Service.objects.using(DEFAULT_DB_ALIAS).filter(service_code="access_control")
            governance_active = governance_services.filter(is_active=True).count()
            code_placements = list(Permission.objects.using(DEFAULT_DB_ALIAS).filter(
                permission_code__in=PROPOSED_CORE_K
            ).values_list("permission_code", "service__service_code"))
        except DatabaseError as exc:
            raise CommandError("Read-only G0 inventory failed; no writes attempted.") from exc

        self.stdout.write("TASK 2 G0: READ-ONLY TECHNICAL GOVERNANCE INVENTORY")
        self.stdout.write("Target: ctug_workspace (loopback only)")
        self.stdout.write(f"Exact Admin role records: {admin_exact}")
        self.stdout.write(f"Exact Technical Super Admin role records: {technical_exact}")
        self.stdout.write(f"Technical role assignments (any account status): {technical_assignments}")
        self.stdout.write(f"Active Technical role permission bindings: {technical_role_grants}")
        self.stdout.write(f"Active direct governance permission overrides: {protected_overrides}")
        self.stdout.write(f"Active access_control services: {governance_active}")
        self.stdout.write("Proposed core K catalogue (NOT approved metadata or grants):")
        for code in PROPOSED_CORE_K:
            # Exact Python equality is case-sensitive despite possible MySQL collation.
            placements = [service for stored, service in code_placements if stored == code]
            status = (
                "ABSENT" if not placements else
                "PRESENT (access_control service)" if placements == ["access_control"] else
                "REVIEW REQUIRED (unexpected service placement)"
            )
            self.stdout.write(f"  {code}: {status}")
        self.stdout.write("NO ROLE CREATION, GRANTS, APPROVALS, AUDITS, OR DATABASE WRITES EXECUTED.")
        self.stdout.write("This inventory is NOT evidence of bootstrap authorization or release readiness.")
