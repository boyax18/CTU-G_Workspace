"""Create synthetic demo data only in ctug_review_sandbox.

Refuses standard development settings, other MySQL databases, and already
populated sandbox databases. Never copies real student/account records.
"""

from getpass import getpass

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connection, transaction

from apps.accounts.models import Account
from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.models import (
    AccessAuditLog,
    AccountPermission,
    AccountRole,
    Permission,
    Role,
    RolePermission,
    Service,
)

DB_NAME = "ctug_review_sandbox"
CONFIRM = "CTUG-REVIEW-SANDBOX-SEED-ONLY"


def verify_target():
    if settings.SETTINGS_MODULE != "config.review_sandbox_settings":
        raise CommandError("Sandbox seed requires config.review_sandbox_settings.")
    db = settings.DATABASES[DEFAULT_DB_ALIAS]
    if (
        db["ENGINE"] != "django.db.backends.mysql"
        or db["NAME"] != DB_NAME
        or db.get("HOST") not in ("127.0.0.1", "localhost", "::1")
        or not settings.DEBUG
        or settings.ROOT_URLCONF != "config.review_sandbox_urls"
        or not settings.WORKSPACE_REGISTRATION_REVIEW_API_ENABLED
        or not settings.WORKSPACE_REGISTRATION_APPROVAL_ENABLED
    ):
        raise CommandError("Sandbox configuration mismatch. No writes allowed.")
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        selected_name = cursor.fetchone()[0]
    if selected_name != DB_NAME:
        raise CommandError("Connected MySQL schema is not the sandbox. Stop.")


def require_empty_sandbox():
    checks = (Account, AccountRole, Role, Service, Permission,
              RolePermission, AccountPermission, AccessAuditLog)
    populated = [model._meta.db_table for model in checks if model.objects.exists()]
    if populated:
        raise CommandError(
            "Sandbox already has application rows; no reseeding or overwriting. "
            "Existing tables: " + ", ".join(populated)
        )


class Command(BaseCommand):
    help = "Seed a fresh, separate MySQL Registration Review sandbox (never ctug_workspace)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--confirm", default="")

    def handle(self, *args, **options):
        verify_target()
        require_empty_sandbox()
        if not options["apply"]:
            self.stdout.write("SANDBOX PREVIEW PASSED; fresh schema; NO WRITES EXECUTED.")
            return
        if options["confirm"] != CONFIRM:
            raise CommandError("Explicit sandbox seed confirmation is required.")

        # Password is entered locally without placing it on the command line,
        # in Git history, a file, or output. Use a unique demo-only password.
        try:
            password = getpass("New SANDBOX Admin password (not your real password): ")
            verify_password = getpass("Confirm SANDBOX password: ")
        except (EOFError, KeyboardInterrupt) as exc:
            raise CommandError("Password input cancelled; no writes.") from exc
        if password != verify_password or not password:
            raise CommandError("Demo passwords do not match; no writes.")
        if len(password) < 12:
            raise CommandError("Use a unique demo password of at least 12 characters.")

        # All synthetic rows commit or roll back as one MySQL transaction.
        try:
            with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
                require_empty_sandbox()
                roles = {
                    name: Role.objects.create(role_name=name, is_active=True)
                    for name in ("Student", "Instructor", "Admin")
                }
                admin = Account.objects.create_user(
                    school_id="SANDBOX-ADMIN-001", password=password,
                )
                admin.request_status = "Approved"
                admin.is_active = True
                admin.save(update_fields=["request_status", "is_active"])
                AccountRole.objects.create(account=admin, role=roles["Admin"], assigned_by=admin)

                # Only obviously fictional records; no real student data.
                for school_id, requested_role in (
                    ("SANDBOX-STUDENT-PENDING-001", roles["Student"]),
                    ("SANDBOX-INSTRUCTOR-PENDING-001", roles["Instructor"]),
                ):
                    Account.objects.create_user(
                        school_id=school_id, password=password,
                        requested_role=requested_role,
                    )
                student = Account.objects.create_user(
                    school_id="SANDBOX-STUDENT-ACTIVE-001", password=password,
                )
                student.request_status = "Approved"
                student.is_active = True
                student.save(update_fields=["request_status", "is_active"])
                AccountRole.objects.create(
                    account=student, role=roles["Student"], assigned_by=admin,
                )

                services = {
                    code: Service.objects.create(
                        service_code=code, service_name=label, is_active=True,
                    )
                    for code, label in (("accounts", "Accounts"),
                                        ("access_control", "Access Control"))
                }
                for action in ("read", "approve", "reject"):
                    permission = Permission.objects.create(
                        service=services["accounts"],
                        permission_code=f"accounts.registration_requests.{action}",
                        permission_name=f"Review registration requests: {action}",
                        module_name="registration_requests",
                        action_name=action,
                    )
                    binding = RolePermission.objects.create(
                        role=roles["Admin"], permission=permission,
                        is_active=True, granted_by=admin,
                    )
                    record_access_audit_receipt(
                        actor=admin,
                        role=roles["Admin"],
                        permission=permission,
                        action="sandbox.review.role_binding.create",
                        old_value=None,
                        new_value={
                            "role_id": roles["Admin"].pk,
                            "permission_id": permission.pk,
                            "role_permission_id": binding.pk,
                            "is_active": True,
                        },
                        reason="permission_change",
                    )
        except Exception as exc:
            raise CommandError(
                "Sandbox seed failed and transaction was rolled back. No success reported."
            ) from exc

        self.stdout.write("SANDBOX SEEDED: one demo Admin, two pending demo accounts, "
                          "one active demo Student, three active Admin grants, three audit receipts.")
        self.stdout.write("SANDBOX LOGIN: School ID SANDBOX-ADMIN-001 (use the unique password entered).")
        self.stdout.write("Original ctug_workspace database was not selected or written.")
