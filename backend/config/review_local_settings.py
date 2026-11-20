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
# WF-02.05 D-69 (owner-authorized 18 Nov 2026): account directory and status changes, in this
# local mode only. config.settings keeps WORKSPACE_ACCOUNT_STATUS_ENABLED absent (off); the protected
# writer still refuses; the accounts.school_accounts.* rows must exist (governed tooling) to act.
WORKSPACE_ACCOUNT_STATUS_ENABLED = True
# WF-03.01 D-87: a separate, exact, PROCESS-ONLY opt-in for local role-assignment operations.
# Nothing is enabled by the normal settings or by the existing local-review acknowledgement.
# Leave this unset until the dedicated WF-03 regression and security checks are authorized.
WORKSPACE_ROLE_ASSIGNMENT_ENABLED = (
    os.environ.get("CTUG_ROLE_ASSIGNMENT_LOCAL_ACK") == "LOCAL_WF0301_D87"
)

# Explicitly suppress external messages for local development tests.
# WF-02.04 D-54/D-62 (owner-authorized 18 Nov 2026): a rejection needs the durable encrypted
# outbox and the v2 template, or it refuses. Mail stays in Django's in-memory backend (locmem),
# so nothing can leave this machine; SMTP stays disabled. No key is stored in source control:
# set the test-only WORKSPACE_OUTBOX_KEK_V1_B64 in the local environment, otherwise every
# rejection rolls back. Delivery attempts still need WORKSPACE_OUTBOX_WORKER_ENABLED=1.
WORKSPACE_REGISTRATION_OUTBOX_ENABLED = True
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
# WF-02.04 D-54: the reason-bearing v2 rejection template (rendered only from the audit snapshot).
WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED = True
WORKSPACE_PUBLIC_BASE_URL = "http://localhost:5173"  # locmem + loopback only; never an external URL

# WF-03.01 D-100: separate opt-in; ordinary evidence adapter is default-deny.
# Leave this OFF until D-101/D-102 permission adoption, evidence integration, and deferred tests.
WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_ENABLED = (
    os.environ.get("CTUG_ORDINARY_ROLE_ASSIGNMENT_LOCAL_ACK") == "LOCAL_WF0301_D100"
)
