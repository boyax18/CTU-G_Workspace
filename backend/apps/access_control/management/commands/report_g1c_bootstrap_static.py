"""G1C: filesystem-only, static PLANNING report. No database access or writes."""

from django.core.management.base import BaseCommand, CommandError

from apps.access_control.tests_support.g1b_catalogue_test_only import (
    CORE_K_CODES, load_pinned_proposal_test_only, validate_catalogue_subset_test_only,
)
from apps.access_control.tests_support.g1c_evidence_test_only import (
    MAX_TICKET_LIFETIME, PROFILE, static_contract_issues_test_only,
)


class Command(BaseCommand):
    help = "G1C static-only bootstrap/evidence proposal check (no DB access)."
    requires_system_checks = []
    requires_migrations_checks = False

    def add_arguments(self, parser):
        parser.add_argument("--ack", required=True)

    def handle(self, *args, **options):
        if options["ack"] != "G1C_STATIC_ONLY":
            raise CommandError("G1C static report requires --ack G1C_STATIC_ONLY.")
        try:
            issues = set(static_contract_issues_test_only())
            issues.update(validate_catalogue_subset_test_only(load_pinned_proposal_test_only()))
        except (OSError, ValueError, TypeError) as exc:
            raise CommandError("Cannot validate G1C planning sources; no changes attempted.") from exc
        if issues:
            raise CommandError("G1C static contract drift: " + ", ".join(sorted(issues)))
        self.stdout.write("G1C STATIC-ONLY BOOTSTRAP AND EVIDENCE CONTRACT PASSED")
        self.stdout.write("Application Admin hierarchy: exactly 2 (Normal Admin, Technical Super Admin)")
        self.stdout.write("Technical profile requires: " + " + ".join(PROFILE))
        self.stdout.write(f"Core K planning codes (not installed): {len(CORE_K_CODES)}")
        self.stdout.write(f"Execution-ticket planning max lifetime: {int(MAX_TICKET_LIFETIME.total_seconds() // 60)} minutes")
        self.stdout.write("Human signer identity, real signatures, durable one-use ledger and DB lock protocol: UNIMPLEMENTED")
        self.stdout.write("NO account, role, grant, audit, migration, schema, database read/write or live authorization performed.")
