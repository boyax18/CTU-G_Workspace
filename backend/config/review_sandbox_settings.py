"""AR-6C7E.3: strictly isolated local Registration Review functional sandbox.

NEVER use this module with the CTU-G Workspace development database.
Unlike config.settings, it enables the review routes ONLY in a hard-named,
separate local MySQL schema containing synthetic sandbox accounts.
"""

import copy
import os

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F401,F403 -- identical installed apps and session API

SANDBOX_DATABASE_NAME = "ctug_review_sandbox"

if os.environ.get("CTUG_REVIEW_SANDBOX_ACK") != "SANDBOX_ONLY":
    raise ImproperlyConfigured("Sandbox requires CTUG_REVIEW_SANDBOX_ACK=SANDBOX_ONLY.")

if DATABASES["default"]["ENGINE"] != "django.db.backends.mysql":  # noqa: F405
    raise ImproperlyConfigured("Sandbox requires local MySQL.")

if DATABASES["default"].get("HOST") not in {"localhost", "127.0.0.1", "::1"}:  # noqa: F405
    raise ImproperlyConfigured("Sandbox refuses remote database hosts.")

# Deep copy: do not mutate config.settings.DATABASES for other Django processes.
DATABASES = copy.deepcopy(DATABASES)  # noqa: F405
DATABASES["default"]["NAME"] = SANDBOX_DATABASE_NAME

# Only this settings module mounts the otherwise-unmounted review endpoints.
ROOT_URLCONF = "config.review_sandbox_urls"
MIDDLEWARE = ["config.review_sandbox_middleware.LoopbackOnlyMiddleware", *MIDDLEWARE]  # noqa: F405
WORKSPACE_REGISTRATION_REVIEW_API_ENABLED = True
WORKSPACE_REGISTRATION_APPROVAL_ENABLED = True

# No emails, encrypted outbox deliveries, or password reset activity in demos.
WORKSPACE_REGISTRATION_OUTBOX_ENABLED = False
WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED = False
WORKSPACE_EMAIL_SMTP_ENABLED = False
WORKSPACE_PASSWORD_RESET_ENABLED = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Isolate login/CSRF cookies from your normal localhost sessions.
SESSION_COOKIE_NAME = "ctug_review_sandbox_session"
CSRF_COOKIE_NAME = "ctug_review_sandbox_csrf"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = False  # Loopback HTTP only
CSRF_COOKIE_SECURE = False  # Loopback HTTP only
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Make this an unmistakable development-only config. Backend is bound to
# 127.0.0.1:8001 by the operator's runserver command, not by this setting.
DEBUG = True
