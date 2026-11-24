"""Synthetic LAN development profile tooling (config.dev_lan_settings only).

  initialize [--reset]   one-time setup / top-up (Initialize-CTUG-LAN.ps1)
  preflight --json       startup readiness report (Start-CTUG-LAN.ps1)
  verify --base-url URL  live end-to-end check against the running application
"""

import json

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.accounts import dev_lan


class Command(BaseCommand):
    help = "Initialize, preflight or verify the synthetic LAN development database (never ctug_workspace)."
    # Model checks open a DB connection; the schema may not exist yet on first initialize.
    # `migrate` (called by initialize) and runserver still run the full system checks.
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("action", choices=("initialize", "preflight", "verify"))
        parser.add_argument("--reset", action="store_true",
                            help="initialize: drop and recreate the MARKED synthetic schema first")
        parser.add_argument("--json", action="store_true", help="preflight: print one JSON object")
        parser.add_argument("--base-url", default="", help="verify: application URL, e.g. http://192.168.1.5:5173")
        parser.add_argument("--mutate-synthetic", action="store_true",
                            help="verify: also exercise approve/reject/bulk decisions on synthetic applicants")

    def handle(self, *args, **options):
        try:
            getattr(self, "_" + options["action"])(options)
        except dev_lan.DevLanRefused as exc:
            raise CommandError(str(exc)) from None

    def _initialize(self, options):
        state = dev_lan.prepare_schema(reset=options["reset"])
        self.stdout.write(f"Synthetic schema {dev_lan.SYNTHETIC_LAN_DATABASE}: {state}; marker verified.")
        dev_lan.verify_target()
        call_command("migrate", interactive=False, verbosity=1, stdout=self.stdout)
        dev_lan.verify_target()
        seeded = dev_lan.seed_synthetic_data()
        synced = dev_lan.sync_catalogue()
        self.stdout.write("Seeded (new rows): " + ", ".join(f"{k}={v}" for k, v in {**seeded, **synced}.items()))
        self.stdout.write(f"Synthetic account sign-in details: {dev_lan.credentials_file()}")
        self.stdout.write("ctug_workspace was not selected, migrated or written.")

    def _preflight(self, options):
        report = dev_lan.preflight()
        if options["json"]:
            self.stdout.write(json.dumps(report, sort_keys=True))
            return
        for feature in report["features"]:
            self.stdout.write(f"{feature['status']:>13}  {feature['key']}  {'; '.join(feature['reasons'])}")
        for line in report["warnings"]:
            self.stdout.write("WARNING: " + line)
        if not report["ok"]:
            raise CommandError("; ".join(report["errors"]))
        self.stdout.write("Preflight passed.")

    def _verify(self, options):
        from apps.accounts.dev_lan_verify import run_live_verification
        if not options["base_url"]:
            raise CommandError("--base-url is required.")
        results = run_live_verification(options["base_url"], mutate=options["mutate_synthetic"],
                                        write=self.stdout.write)
        failed = [name for name, ok in results if not ok]
        self.stdout.write(f"Live verification: {len(results) - len(failed)}/{len(results)} checks passed.")
        if failed:
            raise CommandError("Failed: " + "; ".join(failed))
