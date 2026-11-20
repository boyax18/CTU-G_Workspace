"""Opt-in executor process. Never installs schemas, grants or appointments."""
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.access_control.executor.engine import Executor
from apps.access_control.executor.server import make_server


class Command(BaseCommand):
    help = "Serve an already installed and institutionally enrolled mTLS executor."
    requires_system_checks = []

    def handle(self, *args, **options):
        try:
            c = settings.WORKSPACE_EXECUTOR_SERVER
            key = serialization.load_pem_private_key(Path(c["issuer_private_key"]).read_bytes(), password=None)
            executor = Executor(c, key)
            executor.identity()
            with __import__("django.db", fromlist=["transaction"]).transaction.atomic(durable=True):
                executor.control()  # refuse missing/expired/unapproved storage/trust before listening
            with make_server((c["host"], c["port"]), executor, ca=c["ca"], certificate=c["certificate"], private_key=c["private_key"]) as server:
                server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            return
        except Exception:
            if "c" in locals() and c.get("isolated_datadir"):
                raise  # isolated startup diagnostics, never a request-body log
            raise CommandError("Executor startup refused: verify storage, identity, signed trust and deployment configuration.") from None
