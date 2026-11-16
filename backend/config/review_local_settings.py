"""AR-6C7E.4 opt-in LOCAL DEVELOPMENT ONLY (real local ctug_workspace).

Normal config.settings and config.urls stay unchanged and disabled. Never deploy.
This settings module intentionally exposes real account mutations ONLY on loopback.
"""

import os
from django.core.exceptions import ImproperlyConfigured
from .settings import *  # noqa: F401,F403 -- opt-in overlay, same Django application

if os.environ.get("CTUG_REVIEW_LOCAL_ACK") != "LOCAL_REVIEW_ONLY":
    raise ImproperlyConfigured("Explicit local release marker is required.")
if DEBUG is not True:  # noqa: F405
    raise ImproperlyConfigured("Local review requires DEBUG=True.")
if (DATABASES["default"]["ENGINE"] != "django.db.backends.mysql"  # noqa: F405
    or DATABASES["default"]["NAME"] != "ctug_workspace"  # noqa: F405
    or DATABASES["default"].get("HOST") not in {"localhost", "127.0.0.1", "::1"}):  # noqa: F405
    raise ImproperlyConfigured("Local review requires the named LOCAL MySQL database.")

ROOT_URLCONF = "config.review_local_urls"
MIDDLEWARE = ["config.review_sandbox_middleware.LoopbackOnlyMiddleware", *MIDDLEWARE]  # noqa: F405
WORKSPACE_REGISTRATION_REVIEW_API_ENABLED = True
WORKSPACE_REGISTRATION_APPROVAL_ENABLED = True

# Explicitly suppress external messages for local development tests.
WORKSPACE_REGISTRATION_OUTBOX_ENABLED = False
WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED = False
WORKSPACE_EMAIL_SMTP_ENABLED = False
WORKSPACE_PASSWORD_RESET_ENABLED = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
SESSION_COOKIE_NAME = "ctug_review_local_session"
CSRF_COOKIE_NAME = "ctug_review_local_csrf"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = False  # strictly loopback HTTP development
CSRF_COOKIE_SECURE = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Task 1: local review connects to real ctug_workspace. It must NEVER become a
# reapplication testing environment, even if a developer sets global .env flags.
WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED = False
WORKSPACE_REGISTRATION_REAPPLICATION_EMAIL_ENABLED = False
WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED = False
