"""G1D-P3C2 single-login, read-only MySQL grants triage.

Explicit local-development scope only. Never authorizes a protected write.
Never prints SHOW GRANTS SQL rows, usernames, hostnames, secrets or credentials.
"""

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections

from apps.access_control.tests_support.g1d_p3c2_grants_triage_test_only import summarize_grants


class Command(BaseCommand):
    help = "Read-only P3C2 report for CURRENT_USER grants; always release BLOCKED."
    requires_migrations_checks = False

    def add_arguments(self, parser):
        parser.add_argument("--expected-db", required=True)
        parser.add_argument("--ack", required=True)

    def handle(self, *args, **options):
        configured = settings.DATABASES[DEFAULT_DB_ALIAS]
        if (
            settings.SETTINGS_MODULE != "config.settings"
            or settings.DEBUG is not True
            or configured.get("ENGINE") != "django.db.backends.mysql"
            or configured.get("HOST") not in {"localhost", "127.0.0.1", "::1"}
            or configured.get("NAME") != "ctug_workspace"
            or options["expected_db"] != "ctug_workspace"
            or options["ack"] != "P3C2_READ_ONLY_CURRENT_USER"
        ):
            raise CommandError("G1D-P3C2 refuses anything except exact local, read-only scope.")

        try:
            with connections[DEFAULT_DB_ALIAS].cursor() as cursor:
                cursor.execute("SELECT DATABASE()")
                actual = cursor.fetchone()
                if not actual or actual[0] != "ctug_workspace":
                    raise CommandError("Unexpected connected schema. No grant inspection attempted.")
                cursor.execute("SHOW GRANTS FOR CURRENT_USER()")
                rows = cursor.fetchall()
        except DatabaseError as exc:
            # Do not leak grant contents, login names or DSNs through error output.
            raise CommandError("Read-only MySQL grants inspection unavailable; no writes attempted.") from None
        if not rows or any(not isinstance(row, tuple) or not row or not isinstance(row[0], str) for row in rows):
            raise CommandError("Unexpected grants shape. Fail closed; no writes attempted.")
        result = summarize_grants(tuple(row[0] for row in rows))
        self.stdout.write(json.dumps(result, indent=2, sort_keys=True))
        self.stdout.write("G1D-P3C2 RELEASE: BLOCKED. Credential/DBA fence unverified; no DB writes executed.")
