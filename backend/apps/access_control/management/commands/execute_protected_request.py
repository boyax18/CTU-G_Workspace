"""Offline operator client; existing prepare --apply stays disabled."""
import getpass
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.test import override_settings

from apps.access_control.executor.client import authenticate_actor, transport
from apps.access_control.executor.protocol import decode, request


class Command(BaseCommand):
    help = "Review a signed P4/P5 bundle; explicit --apply uses a separate protected mTLS identity."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--bundle", required=True)
        parser.add_argument("--client-config", required=True)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        try:
            bundle = decode(Path(options["bundle"]).read_bytes())
            operation = bundle["request"]["operation"]
            if operation not in {"technical_role.provision", "technical_admin.bootstrap"}:
                raise ValueError()
            self.stdout.write("Operation: " + operation + "; request: " + bundle["request"]["request_id"])
            if not options["apply"]:
                self.stdout.write("REVIEW ONLY. No authentication, connection or write performed.")
                return
            import sys
            if not sys.stdin.isatty():
                raise ValueError()
            client = decode(Path(options["client_config"]).read_bytes())
            with override_settings(WORKSPACE_EXECUTOR_CLIENTS={"protected": client}):
                actor = input("Enrolled operator CTU-G ID: ").strip()
                proof = authenticate_actor(actor, getpass.getpass("Operator password: "), kind="protected")["proof"]
                envelope = request(operation, {"bundle": bundle}, proof)
                envelope.update(request_id=bundle["request"]["request_id"], nonce=bundle["request"]["nonce"])
                result = transport("/execute", envelope, kind="protected")
            self.stdout.write("Committed ledger request: " + result["request_id"])
        except Exception:
            raise CommandError("Protected request refused or outcome unresolved; reconcile the request before any retry.") from None
