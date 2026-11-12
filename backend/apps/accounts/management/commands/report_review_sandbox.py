"""Read-only status of the isolated synthetic review sandbox."""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.accounts.management.commands.seed_review_sandbox import verify_target
from apps.accounts.models import Account
from apps.access_control.models import AccessAuditLog


class Command(BaseCommand):
    help = "Inspect synthetic registration decisions in ctug_review_sandbox; never writes."

    def handle(self, *args, **options):
        verify_target()
        expected = {
            "SANDBOX-ADMIN-001",
            "SANDBOX-STUDENT-PENDING-001",
            "SANDBOX-INSTRUCTOR-PENDING-001",
            "SANDBOX-STUDENT-ACTIVE-001",
        }
        rows = list(Account.objects.values_list("school_id", "request_status", "is_active"))
        if {row[0] for row in rows} != expected or len(rows) != 4:
            raise CommandError("Unexpected sandbox account population. Stop.")
        self.stdout.write("SANDBOX ACCOUNT STATUS (READ ONLY):")
        for school_id, status, is_active in sorted(rows):
            self.stdout.write(f"  {school_id}: {status}; active={is_active}")
        for action in ("account.registration.approve", "account.registration.reject"):
            self.stdout.write(f"  {action} receipts: {AccessAuditLog.objects.filter(action=action).count()}")
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            schema = cursor.fetchone()[0]
        self.stdout.write(f"Verified MySQL schema: {schema}")
        self.stdout.write("SANDBOX READ-ONLY VERIFICATION COMPLETE")
