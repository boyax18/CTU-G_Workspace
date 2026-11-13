"""C2A deliberately has no apply/seed/activation mode."""

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from apps.access_control.catalogue.planner import CataloguePlanningError, build_plan
from apps.access_control.catalogue.validation import CatalogueValidationError


class Command(BaseCommand):
    help = "Validate C1 v1 and report a read-only catalogue initialization plan; never writes."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--format", choices=("text", "json"), default="text")

    def handle(self, *args, **options):
        try:
            report = build_plan()
        except CatalogueValidationError as exc:
            raise CommandError(f"Catalogue validation blocked planning: {exc} No database modifications performed.") from exc
        except (DatabaseError, CataloguePlanningError) as exc:
            raise CommandError("Read-only planning unavailable: database/transaction prerequisite failed. No database modifications performed; no repairs attempted.") from exc
        if options["format"] == "json":
            self.stdout.write(json.dumps(report, indent=2, ensure_ascii=True))
        else:
            self.stdout.write(f"MODE: {report['mode']}\nManifest: C1 proposal v1 ({report['manifest']})")
            self.stdout.write(f"Source SHA-256: {report['source']['sha256']}")
            self.stdout.write(f"Services: {report['proposed']['services']} proposed\nPermissions: {report['proposed']['permissions']} proposed\nRole bindings: {report['proposed']['role_bindings']} proposed, NOT approved for application")
            self.stdout.write("Existing roles: " + ", ".join(report["existing_roles"]))
            for record in report["records"]:
                self.stdout.write(f"{record['classification']} {record['kind']} {record['key']}: {record['detail']}")
            self.stdout.write("Manifest record totals: " + json.dumps(report["totals"], sort_keys=True))
            self.stdout.write("Unexpected existing records (preserved): " + str(len(report["unexpected"])))
            for record in report["unexpected"]:
                self.stdout.write(f"DEFER unexpected {record['kind']} #{record['existing_id']} {record['key']}")
            for group in report["account_override_review"]:
                self.stdout.write(f"DEFER overrides permission_id={group['permission_id']} effect={group['effect']} active={group['is_active']} count={group['count']}: preserved")
            for decision in report["pending_decisions"]:
                self.stdout.write(f"OPEN {decision['id']}: {decision['description']}")
            for blocker in report["blocked_dependencies"]:
                self.stdout.write(f"BLOCKED {blocker['id']}: {blocker['description']}")
            self.stdout.write("Delegation candidates: all OFF; no settings changed.")
            self.stdout.write(report["guarantee"])
        if report["totals"]["CONFLICT"]:
            raise CommandError("Existing-record conflicts require explicit review; no records changed.", returncode=2)
