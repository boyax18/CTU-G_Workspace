"""Isolated MySQL settings: never point tests at the development database."""

import copy
import secrets

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403

DATABASES = copy.deepcopy(DATABASES)  # noqa: F405
database = DATABASES["default"]
if database["ENGINE"] != "django.db.backends.mysql" or database["HOST"] not in {"127.0.0.1", "localhost", "::1"}:
    raise ImproperlyConfigured("Registration tests require local MySQL.")

# A fresh unpredictable name prevents reuse or deletion of an existing database.
REGISTRATION_TEST_DATABASE = "test_ctug_registration_" + secrets.token_hex(8)
database["NAME"] = REGISTRATION_TEST_DATABASE
database["TEST"] = {
    "NAME": REGISTRATION_TEST_DATABASE,
    "CHARSET": "utf8mb4",
    "COLLATION": "utf8mb4_unicode_ci",
}
TEST_RUNNER = "config.test_runner.IsolatedMySQLRunner"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DEBUG = False
# Keep test output readable; tests assert on email diagnostics with assertLogs where needed.
LOGGING["loggers"]["ctug.email"]["level"] = "WARNING"  # noqa: F405
# Durable security mail: attempt kicked rows in the calling thread (test transactions are uncommitted).
WORKSPACE_SECURITY_MAIL_INLINE = True
