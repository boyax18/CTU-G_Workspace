"""G1D-P1 protected role *preparation*; NO OPERATIONAL APPLY PATH.

This command cannot create Technical Super Admin in any database. Real
release requires independently reviewed executor/evidence integration.
"""

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Read-only P1 role-creation readiness. --apply always refuses."

    def add_arguments(self, parser):
        parser.add_argument("--expected-db", required=True)
        parser.add_argument("--ack", required=True)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        # ALWAYS refuse mutation before accessing DB or reading evidence.
        if options["apply"]:
            raise CommandError("G1D-P1 live role creation is DISABLED pending separate authorization and release.")
        if (
            settings.SETTINGS_MODULE != "config.settings"
            or options["expected_db"] != "ctug_workspace"
            or options["ack"] != "G1D_P1_PREPARATION_ONLY"
        ):
            raise CommandError("Only exact local read-only P1 preparation is supported.")
        call_command(
            "report_g1d_p0_role_readiness", expected_db="ctug_workspace",
            ack="G1D_P0_READ_ONLY", stdout=self.stdout,
        )
        self.stdout.write("G1D-P1 PROTECTED ROLE PREPARATION: READ-ONLY CHECK PASSED")
        self.stdout.write("No signer trust roots, independent identity proof or one-use ledger are installed.")
        self.stdout.write("No verified live executor binding, approval-evidence consumption or release gate exists.")
        self.stdout.write("--apply is deliberately unavailable; NO DATABASE WRITE EXECUTED.")
