"""AR-6C7C.4: read-only, non-executable subset initialization preflight.

No --apply/--execute/--seed option. Uses existing v2 planner's MySQL
READ ONLY snapshot. This command cannot initialize or activate anything.
"""

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from apps.access_control.catalogue.planner import CataloguePlanningError
from apps.access_control.catalogue.planner_v2 import build_plan_v2
from apps.access_control.catalogue.validation_v2 import CatalogueV2ValidationError
from scripts.plan_registration_review_profile import load_local
from scripts.registration_review_initialization_preflight import (
    InitializationPreflightError, build_preflight,
)


class Command(BaseCommand):
    help = "Read-only registration-review initialization preflight; no execution path."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--format", choices=("text", "json"), default="text")

    def handle(self, *args, **options):
        try:
            profile, source, source_digest = load_local()
            # The pure preflight independently validates static provenance.
            # This existing planner validates all pinned v2 source documents
            # before entering its MySQL READ ONLY snapshot.
            report = build_plan_v2()
            preflight = build_preflight(
                profile=profile, source=source, source_sha256=source_digest,
                database_report=report,
            )
        except (InitializationPreflightError, CatalogueV2ValidationError,
                CataloguePlanningError, DatabaseError,
                OSError, ValueError, KeyError, TypeError) as exc:
            raise CommandError(
                "Registration-review preflight failed closed; no database "
                "records, grants, or activation flags were changed."
            ) from exc

        if options["format"] == "json":
            self.stdout.write(json.dumps(preflight, indent=2, sort_keys=True))
            return

        self.stdout.write("MODE: " + preflight["mode"])
        self.stdout.write("Profile: " + preflight["profile"])
        self.stdout.write("Source SHA-256: " + preflight["source_sha256"])
        for row in preflight["metadata_proposals"]:
            self.stdout.write(f"METADATA {row['state']} {row['kind']} {row['code']}")
        for row in preflight["deferred_role_grants"]:
            self.stdout.write(
                f"GRANT {row['state']} {row['role']} -> {row['permission_code']}"
            )
        self.stdout.write("GATES: all BLOCKED")
        self.stdout.write("EXECUTION AUTHORIZED: NO")
        self.stdout.write("WRITES PERFORMED: NO")
        self.stdout.write("RELEASE READY: NO")
