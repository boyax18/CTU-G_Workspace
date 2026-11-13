import re
from contextlib import ExitStack
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.test.runner import DiscoverRunner


class IsolatedMySQLRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        name = getattr(settings, "REGISTRATION_TEST_DATABASE", "")
        if not re.fullmatch(r"test_ctug_registration_[0-9a-f]{16}", name):
            raise ImproperlyConfigured("Refusing tests without an isolated database name.")
        if self.keepdb or self.parallel not in (0, 1):
            raise ImproperlyConfigured("Isolated registration tests forbid database reuse and parallel clones.")
        for alias in connections:
            config = connections[alias].settings_dict
            if config["NAME"] != name or config.get("TEST", {}).get("NAME") != name:
                raise ImproperlyConfigured("Refusing to access a non-isolated test database.")
        # Replace Django's create-error recovery, which can drop an existing
        # database when --noinput is supplied. A collision must stop this run.
        self.interactive = False
        def fresh_creator(creation):
            def create(verbosity, autoclobber, keepdb=False):
                try:
                    with creation._nodb_cursor() as cursor:
                        cursor.execute(
                            "CREATE DATABASE " + creation.connection.ops.quote_name(name)
                            + " CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                        )
                except Exception as exc:
                    raise ImproperlyConfigured("Could not create a fresh disposable database; existing databases were preserved.") from exc
                return name
            return create

        with ExitStack() as stack:
            for alias in connections:
                creation = connections[alias].creation
                stack.enter_context(patch.object(creation, "_create_test_db", side_effect=fresh_creator(creation)))
            old_config = super().setup_databases(**kwargs)
        if "aliases" in kwargs and not kwargs["aliases"]:
            return old_config
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != name:
                raise ImproperlyConfigured("Connected database failed the isolation check.")
        return old_config
