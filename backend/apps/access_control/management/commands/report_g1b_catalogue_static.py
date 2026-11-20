"""G1B: filesystem-only check of a planning JSON file; never accesses the DB."""

from django.core.management.base import BaseCommand, CommandError

from apps.access_control.tests_support.g1b_catalogue_test_only import (
    CORE_K_CODES,
    load_pinned_proposal_test_only,
    validate_catalogue_subset_test_only,
)


class Command(BaseCommand):
    help = "G1B static-only v2 proposal contract; no database reads or writes."
    requires_system_checks = []
    requires_migrations_checks = False

    def add_arguments(self, parser):
        parser.add_argument("--ack", required=True)

    def handle(self, *args, **options):
        if options["ack"] != "STATIC_G1B_ONLY":
            raise CommandError("G1B static report requires --ack STATIC_G1B_ONLY.")
        try:
            manifest = load_pinned_proposal_test_only()
            issues = validate_catalogue_subset_test_only(manifest)
        except (OSError, ValueError, TypeError) as exc:
            raise CommandError("Could not validate the pinned v2 planning JSON; no changes made.") from exc
        if issues:
            raise CommandError("G1B proposal drift: " + ", ".join(issues))
        self.stdout.write("G1B STATIC-ONLY CATALOGUE CONTRACT PASSED")
        self.stdout.write("Pinned planning manifest: catalogue-v2.0 / v2.0-review-1")
        self.stdout.write(f"Exact governance core K definitions: {len(CORE_K_CODES)}")
        self.stdout.write("Proposed bindings: Technical Super Admin only for these six codes")
        self.stdout.write("No metadata installation, role creation, grant, governance authority, database access, audit or write executed.")
        self.stdout.write("Bootstrap remains TEST-ONLY and all release gates remain disabled.")
