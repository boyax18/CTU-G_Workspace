"""Offline acceptance inventory; never reads DB credentials or connects."""

import json

from django.core.management.base import BaseCommand, CommandError


BLOCKERS = (
    "No independently enrolled institutional trust roots, real signer custody or revocation channel.",
    "Production approval and installation of the implemented security SQL/ERD amendments and retention policy remain required.",
    "Production credential activation, complete external-writer/session inventory and environment-specific fence verification remain required.",
    "No approved backup/restore, session draining, recovery ceremony or release authorization.",
    "The implemented protected executor and operator client have not been authorized for live provisioning/bootstrap.",
)


class Command(BaseCommand):
    help = "Offline Task 2 acceptance status. Never provisions, activates or certifies production."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--require-release", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write(json.dumps({
            "verdict": "IMPLEMENTATION COMPLETE BUT RELEASE BLOCKED", "production_release": "BLOCKED",
            "engineering_implemented": True, "production_writer_fence_verified": False,
            "protected_apply_implemented": True, "production_apply_authorized": False,
            "verification_evidence": "See CORE_TASK_2_COMPLETION_REPORT.md; this offline command does not run or certify tests.",
            "phases": {"P3C6B": "IMPLEMENTED", "P3C7": "IMPLEMENTED",
                       "P4": "IMPLEMENTED", "P5": "IMPLEMENTED",
                       "acceptance": "PRODUCTION_RELEASE_BLOCKED"},
            "blockers": BLOCKERS,
        }, indent=2))
        if options["require_release"]:
            raise CommandError("Task 2 release acceptance is blocked.")
