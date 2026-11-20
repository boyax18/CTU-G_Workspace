"""READ ONLY prototype (WF-03.01 R-2 Option D phase 1): audit-receipt checkpoint report and verification.

Prints a checkpoint (version, count, max_id, head) or verifies the receipts against a trusted checkpoint
file held OUTSIDE the database. Output never contains receipt contents. An HMAC key, when used, is read from
the environment variable named by --hmac-key-env and is never printed. Not part of any governance path.
"""

import json
import os

from django.core.management.base import BaseCommand, CommandError

from apps.access_control import audit_checkpoint as checkpoint


class Command(BaseCommand):
    help = "READ ONLY: report or verify the access-audit receipt checkpoint (prototype; never writes)."

    def add_arguments(self, parser):
        parser.add_argument("--verify", metavar="CHECKPOINT_FILE",
                            help="Verify against a trusted checkpoint file held outside the database.")
        parser.add_argument("--hmac-key-env", metavar="NAME",
                            help="Environment variable holding the HMAC key (at least 32 bytes).")

    def handle(self, *args, **options):
        key = None
        if options["hmac_key_env"]:
            value = os.environ.get(options["hmac_key_env"])
            if not value:
                raise CommandError("The named HMAC key environment variable is not set.")
            key = value.encode("utf-8")
        try:
            if options["verify"]:
                with open(options["verify"], "r", encoding="utf-8") as handle:
                    trusted = checkpoint.parse(handle.read())
                result = checkpoint.verify(trusted, key=key)
            else:
                result = checkpoint.compute(key=key)
        except OSError as exc:
            raise CommandError("The trusted checkpoint file cannot be read.") from exc
        except checkpoint.CheckpointMismatch as exc:
            raise CommandError(f"MISMATCH: {exc} Nothing was changed.") from None
        except checkpoint.CheckpointError as exc:
            raise CommandError(f"Refused: {exc} Nothing was changed.") from None
        self.stdout.write(json.dumps(result, sort_keys=True))
