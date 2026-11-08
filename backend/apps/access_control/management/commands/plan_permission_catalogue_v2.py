"""Catalogue v2: report only; no apply, seed, activation, or database override options."""

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from apps.access_control.catalogue.planner import CataloguePlanningError
from apps.access_control.catalogue.planner_v2 import build_plan_v2
from apps.access_control.catalogue.validation_v2 import CatalogueV2ValidationError


class Command(BaseCommand):
    help = "Report a read-only v2 catalogue database comparison; never writes or approves grants."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--format", choices=("text", "json"), default="text")

    def handle(self, *args, **options):
        try:
            report = build_plan_v2()
        except CatalogueV2ValidationError as exc:
            raise CommandError("v2 source/manifest validation failed before database planning. "
                               "No database changes performed.") from exc
        except (DatabaseError, CataloguePlanningError) as exc:
            raise CommandError("Read-only v2 planning unavailable; database or transaction prerequisite failed. "
                               "No database changes performed; no automatic repair.") from exc

        if options["format"] == "json":
            self.stdout.write(json.dumps(report, indent=2, ensure_ascii=True))
        else:
            self.stdout.write(f"MODE: {report['mode']} (NOT APPROVED FOR APPLICATION)")
            self.stdout.write(f"Manifest: {report['manifest']} ({report['source_revision']})")
            self.stdout.write(f"Pinned proposal SHA-256: {report['provenance']['sha256']}")
            self.stdout.write("Proposed: " + json.dumps(report["proposed"], sort_keys=True))
            self.stdout.write("Manifest record totals: " + json.dumps(report["totals"], sort_keys=True))
            self.stdout.write(f"Unexpected existing rows: {len(report['unexpected'])}")
            self.stdout.write(f"Retired definition rows found: {len(report['retirement_review'])}")
            self.stdout.write(f"Override aggregate groups: {len(report['account_override_review'])}")
            self.stdout.write("Review totals: " + json.dumps(report["review_totals"], sort_keys=True))
            for entry in report["records"]:
                self.stdout.write(f"{entry['classification']} {entry['kind']} {entry['key']}: {entry['detail']}")
            for entry in report["unexpected"]:
                self.stdout.write(f"{entry['classification']} unexpected {entry['kind']} {entry['key']}")
            for entry in report["retirement_review"]:
                self.stdout.write(f"{entry['classification']} retired {entry['key']}: "
                                  f"active grants={entry['active_role_grants']}, "
                                  f"active overrides={entry['active_account_overrides']}")
            for entry in report["account_override_review"]:
                self.stdout.write(f"{entry['classification']} account-override aggregate "
                                  f"permission_id={entry['permission_id']} effect={entry['effect']} "
                                  f"active={entry['is_active']} count={entry['count']}")
            for blocker in report["blocked_dependencies"]:
                self.stdout.write(f"BLOCKED {blocker['id']}: {blocker['description']}")
            self.stdout.write(report["guarantee"])

        conflicts = report["totals"]["CONFLICT"] + report["review_totals"]["CONFLICT"]
        if conflicts:
            raise CommandError("Catalogue v2 conflicts require explicit review; no records changed.", returncode=2)
