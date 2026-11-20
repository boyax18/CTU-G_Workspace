"""Run v2 and existing v1 static tests without loading development settings.

Run from backend: .venv/Scripts/python.exe -B scripts/test_catalogue_static.py
Uses a dummy backend and refuses every attempted database connection.
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from django.conf import settings
    if settings.configured:
        raise RuntimeError("Static runner requires a fresh, unconfigured process.")
    settings.configure(
        SECRET_KEY="static-catalogue-tests-only",
        INSTALLED_APPS=["django.contrib.auth", "django.contrib.contenttypes", "apps.accounts", "apps.access_control"],
        AUTH_USER_MODEL="accounts.Account",
        DATABASES={"default": {"ENGINE": "django.db.backends.dummy", "NAME": "static-only"}},
        # Only satisfies the existing module's isolation-name import guard. No
        # database is created; only its SimpleTestCase class is loaded below.
        REGISTRATION_TEST_DATABASE="test_ctug_registration_0000000000000000",
        USE_TZ=True,
    )
    from django.db.backends.base.base import BaseDatabaseWrapper
    with patch.object(BaseDatabaseWrapper, "ensure_connection", side_effect=AssertionError("Database access forbidden in static tests")) as guard:
        import django
        django.setup()
        suite = unittest.defaultTestLoader.loadTestsFromNames([
            "apps.access_control.test_catalogue_v2",
            "apps.access_control.test_catalogue.ManifestTests",
        ])
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        guard.assert_not_called()
    print("Database connections attempted: 0; dummy backend only; development settings not loaded.")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
