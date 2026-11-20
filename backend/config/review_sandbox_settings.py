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
# WF-02.05 D-69 (owner-authorized 18 Nov 2026): account directory and status changes, in this
# local mode only. config.settings keeps WORKSPACE_ACCOUNT_STATUS_ENABLED absent (off); the protected
# writer still refuses; the accounts.school_accounts.* rows must exist (governed tooling) to act.
WORKSPACE_ACCOUNT_STATUS_ENABLED = True

# No external emails or password reset activity in demos.
# WF-02.04 D-54/D-62 (owner-authorized 18 Nov 2026): a rejection needs the durable encrypted
# outbox and the v2 template, or it refuses. Mail stays in Django's in-memory backend (locmem),
# so nothing can leave this machine; SMTP stays disabled. No key is stored in source control:
# set the test-only WORKSPACE_OUTBOX_KEK_V1_B64 in the local environment, otherwise every
# rejection rolls back. Delivery attempts still need WORKSPACE_OUTBOX_WORKER_ENABLED=1.
WORKSPACE_REGISTRATION_OUTBOX_ENABLED = True
WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED = False
WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED = True
WORKSPACE_PUBLIC_BASE_URL = "http://localhost:5173"  # locmem + loopback only; never an external URL
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
