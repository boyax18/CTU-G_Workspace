"""G1D-P3C4 guarded SELECT-only metadata/visibility report for local MySQL.

Never runs GRANT, REVOKE, CREATE USER, KILL, LOCK TABLES, migrations, or
role/permission writes. Prints ONLY aggregate counts and blocked release.
"""

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections

from apps.access_control.tests_support.g1d_p3c4_dba_visibility_test_only import (
    InventoryUnavailable, summarize_observations,
)


class Command(BaseCommand):
    help = "Read-only MySQL metadata visibility inventory; release remains blocked."
    requires_migrations_checks = False

    def add_arguments(self, parser):
        parser.add_argument("--expected-db", required=True)
        parser.add_argument("--ack", required=True)

    def handle(self, *args, **options):
        db = settings.DATABASES[DEFAULT_DB_ALIAS]
        if (
            settings.SETTINGS_MODULE != "config.settings"
            or settings.DEBUG is not True
            or db.get("ENGINE") != "django.db.backends.mysql"
            or db.get("HOST") not in {"127.0.0.1", "localhost", "::1"}
            or db.get("NAME") != "ctug_workspace"
            or options["expected_db"] != "ctug_workspace"
            or options["ack"] != "P3C4_SELECT_ONLY_VISIBILITY"
        ):
            raise CommandError("P3C4 refuses anything but the exact local read-only scope")

        connection = connections[DEFAULT_DB_ALIAS]
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT DATABASE()")
                selected = cursor.fetchone()
                if not selected or selected[0] != "ctug_workspace":
                    raise CommandError("Connected schema does not match local approved inventory scope")

                def get_count(sql):
                    # SQL strings are fixed internally in SOURCES. No user input.
                    try:
                        cursor.execute(sql)
                        row = cursor.fetchone()
                    except DatabaseError:
                        raise InventoryUnavailable() from None
                    if not row or len(row) != 1:
                        raise InventoryUnavailable()
                    return row[0]

                report = summarize_observations(get_count)
        except DatabaseError:
            raise CommandError("P3C4 read-only connection failed; no metadata disclosed") from None

        self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
        self.stdout.write("G1D-P3C4 RELEASE BLOCKED: metadata counts are NOT a writer fence. No writes attempted.")
