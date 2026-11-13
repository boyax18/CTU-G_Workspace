"""Offline acceptance inventory; never reads DB credentials or connects."""

import json

from django.core.management.base import BaseCommand, CommandError


BLOCKERS = (
    "No reviewed production executor or authenticated ordinary-writer transport is integrated.",
    "No independently enrolled institutional trust roots, real signer custody or revocation channel.",
    "No approved persistent security ledger schema, retention policy or production migration.",
    "No verified production credential separation, complete writer inventory or DB-level fencing.",
    "No approved backup/restore, session draining, recovery ceremony or release authorization.",
    "Protected provisioning/bootstrap are executable only in guarded disposable tests.",
)


class Command(BaseCommand):
    help = "Offline Task 2 acceptance status. Never provisions, activates or certifies production."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--require-release", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write(json.dumps({
            "verdict": "INCOMPLETE", "production_release": "BLOCKED",
            "production_writer_fence_verified": False, "live_apply_available": False,
            "phases": {"P3C6B": "PARTIAL", "P3C7": "PARTIAL",
                       "P4": "ISOLATED_CANDIDATE", "P5": "ISOLATED_CANDIDATE",
                       "acceptance": "NOT_MET"},
            "blockers": BLOCKERS,
        }, indent=2))
        if options["require_release"]:
            raise CommandError("Task 2 release acceptance is blocked.")
