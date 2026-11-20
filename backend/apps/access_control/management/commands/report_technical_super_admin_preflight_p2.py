"""Task 2: bounded, read-only local inventory for Technical Super Admin design.

This command deliberately contains no INSERT/UPDATE/DELETE, role provisioning,
activation, permission granting, migration, or audit-writing implementation.
Its counts do not confer or attest effective governance authority.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections

from apps.accounts.models import Account
from apps.access_control.delegation import is_reserved_role
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role,
    RolePermission, Service,
)


class Command(BaseCommand):
    help = "Read-only Technical Super Admin role/catalogue preflight (local development only)."

    def add_arguments(self, parser):
        parser.add_argument("--expected-db", required=True)
        parser.add_argument("--ack", required=True)

    def handle(self, *args, **options):
        database = settings.DATABASES[DEFAULT_DB_ALIAS]
        if (
            settings.SETTINGS_MODULE != "config.settings"
            or settings.DEBUG is not True
            or database.get("ENGINE") != "django.db.backends.mysql"
            or database.get("NAME") != "ctug_workspace"
            or database.get("HOST") not in {"127.0.0.1", "localhost", "::1"}
            or options["expected_db"] != "ctug_workspace"
            or options["ack"] != "READ_ONLY_PREFLIGHT"
        ):
            raise CommandError("Refusing preflight: exact local-development read-only scope is required.")

        alias = DEFAULT_DB_ALIAS
        try:
            with connections[alias].cursor() as cursor:
                cursor.execute("SELECT DATABASE()")
                actual = cursor.fetchone()[0]
            if actual != "ctug_workspace":
                raise CommandError("Connected schema differs from the approved local development target.")

            role_names = list(Role.objects.using(alias).values_list("role_name", flat=True))
            unexpected_reserved = [
                name for name in role_names
                if is_reserved_role(name) and name not in {"Admin", "Technical Super Admin"}
            ]
            if unexpected_reserved:
                raise CommandError("Noncanonical reserved role name detected; reconcile before implementing.")

            admin_role = Role.objects.using(alias).filter(role_name="Admin").first()
            tech_role = Role.objects.using(alias).filter(role_name="Technical Super Admin").first()
            for role, canonical in ((admin_role, "Admin"), (tech_role, "Technical Super Admin")):
                if role is not None and role.role_name != canonical:
                    raise CommandError("Unexpected case/variant of a protected role; reconcile first.")

            active_admin_ids = set(AccountRole.objects.using(alias).filter(
                role__role_name="Admin", role__is_active=True,
                account__request_status="Approved", account__is_active=True,
            ).values_list("account_id", flat=True))
            active_technical_ids = set(AccountRole.objects.using(alias).filter(
                role__role_name="Technical Super Admin", role__is_active=True,
                account__request_status="Approved", account__is_active=True,
            ).values_list("account_id", flat=True))
            composed = active_admin_ids & active_technical_ids
            incomplete = active_technical_ids - active_admin_ids
            technical_grants = RolePermission.objects.using(alias).filter(
                role__role_name="Technical Super Admin", is_active=True,
            ).count()
            governance_overrides = AccountPermission.objects.using(alias).filter(
                permission__service__service_code="access_control", is_active=True,
            ).count()
            stats = {
                "Framework superuser accounts": Account.objects.using(alias).filter(is_superuser=True).count(),
                "Admin role present": int(admin_role is not None),
                "Admin role active": int(bool(admin_role and admin_role.is_active)),
                "Technical Super Admin role present": int(tech_role is not None),
                "Technical Super Admin role active": int(bool(tech_role and tech_role.is_active)),
                "Eligible assigned Admin accounts": len(active_admin_ids),
                "Eligible dual-role profiles (not a grant)": len(composed),
                "Technical-only assigned eligible accounts (review)": len(incomplete),
                "Active Technical role bindings (review)": technical_grants,
                "Active direct governance overrides (review)": governance_overrides,
                "Catalogue services": Service.objects.using(alias).count(),
                "Catalogue permissions": Permission.objects.using(alias).count(),
                "Existing audit rows": AccessAuditLog.objects.using(alias).count(),
            }
        except DatabaseError as exc:
            raise CommandError("Read-only Technical Super Admin preflight could not complete.") from exc

        self.stdout.write("TASK 2: READ-ONLY TECHNICAL SUPER ADMIN PREFLIGHT")
        self.stdout.write("Target: ctug_workspace (loopback development database)")
        for key, value in stats.items():
            self.stdout.write(f"{key}: {value}")
        if incomplete or technical_grants or governance_overrides:
            self.stdout.write("REVIEW REQUIRED: existing privileged-state indicators need reconciliation.")
        else:
            self.stdout.write("No flagged technical-only assignment, technical grant, or governance override.")
        self.stdout.write("NO ROLE CREATION, GRANTS, AUDITS, OR OTHER DATABASE WRITES EXECUTED.")
        self.stdout.write("No bootstrap, governance write policy, or release approval is provided by this report.")
