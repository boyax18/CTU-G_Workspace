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

# 24 Nov 2026 (owner-directed): explicit, one-time opt-in for REAL email from this loopback
# profile. Off unless backend/.env sets WORKSPACE_LOCAL_EMAIL_DELIVERY=1. It reuses the SMTP
# configuration already validated by config.settings (credentials are never re-read here),
# restores password recovery as configured in .env, and lets decision emails carry this
# loopback http link (WORKSPACE_EMAIL_DEV_LINKS_ALLOWED; DEBUG + local profile only). The
# outbox worker keeps its own WORKSPACE_OUTBOX_WORKER_ENABLED / _SMTP_DELIVERY_APPROVED gates.
WORKSPACE_LOCAL_EMAIL_DELIVERY = os.environ.get("WORKSPACE_LOCAL_EMAIL_DELIVERY") == "1"
WORKSPACE_EMAIL_DEV_LINKS_ALLOWED = False
if WORKSPACE_LOCAL_EMAIL_DELIVERY:
    from . import settings as _base_settings
    if not (_base_settings.WORKSPACE_EMAIL_SMTP_ENABLED
            and _base_settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"):
        raise ImproperlyConfigured(
            "WORKSPACE_LOCAL_EMAIL_DELIVERY=1 requires WORKSPACE_EMAIL_SMTP_ENABLED=1 and the Gmail settings in backend/.env."
        )
    WORKSPACE_EMAIL_SMTP_ENABLED = True
    EMAIL_BACKEND = _base_settings.EMAIL_BACKEND
    WORKSPACE_PASSWORD_RESET_ENABLED = _base_settings.WORKSPACE_PASSWORD_RESET_ENABLED
    WORKSPACE_EMAIL_DEV_LINKS_ALLOWED = True

# WF-03.01 D-100: separate opt-in; ordinary evidence adapter is default-deny.
# Leave this OFF until D-101/D-102 permission adoption, evidence integration, and deferred tests.
WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_ENABLED = (
    os.environ.get("CTUG_ORDINARY_ROLE_ASSIGNMENT_LOCAL_ACK") == "LOCAL_WF0301_D100"
)

# WF-03.01 D-110: evidence registrar/reviewer API staged; independent permission
# and campus-authority policy still unapproved. Leave env marker UNSET.
WORKSPACE_ORDINARY_APPOINTMENT_REGISTRY_ENABLED = (
    os.environ.get("CTUG_APPOINTMENT_REGISTRY_LOCAL_ACK") == "LOCAL_WF0301_D110"
)
# No settings module enables WORKSPACE_ORDINARY_APPOINTMENT_EVIDENCE_ENABLED.
# Grants remain denied even if this staging endpoint is later examined.

# WF-03.01 D-111: default-OFF continuous appointment enforcement. Even if
# ordinary role assignment gets enabled, the D-100 service blocks NEW grants
# until this is explicitly activated under an approved isolated rollout.
# Do NOT enable before the D-110 migration, independent reviewer policy and
# deferred security regression tests are complete.
WORKSPACE_ORDINARY_APPOINTMENT_RUNTIME_ENFORCEMENT_ENABLED = (
    os.environ.get("CTUG_APPOINTMENT_RUNTIME_LOCAL_ACK") == "LOCAL_WF0301_D111"
)

# WF-03.01 D-113. Session-selected role restriction; independent default-OFF
# local-only gate. No settings/DB/permission provisioning is authorized here.
WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED = (
    os.environ.get("CTUG_ROLE_CONTEXT_LOCAL_ACK") == "LOCAL_WF0301_D113"
)
MIDDLEWARE = [*MIDDLEWARE, "apps.accounts.active_role_context.ActiveRoleContextMiddleware"]

# WF-03.02: role-permission directory + separate mutation gate; default OFF.
WORKSPACE_WF0302_ROLE_PERMISSIONS_ENABLED = (
    os.environ.get("CTUG_WF0302_LOCAL_ACK") == "LOCAL_WF0302"
)
WORKSPACE_WF0302_ROLE_PERMISSION_MUTATIONS_ENABLED = (
    os.environ.get("CTUG_WF0302_LOCAL_MUTATION_ACK") == "LOCAL_WF0302_MUTATIONS"
)
# Mutation gate remains off until the reviewed delegation policy, S1 authority,
# protected writer and deferred WF-03 tests are authorized.

# WF-03.03 individual role-bound Grants: three independent, default-OFF gates.
# Requires owner-approved 0005 migration, D-101/102 delegated authority and
# preserved protected executor limitations before activation.
WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED = (
    os.environ.get("CTUG_WF0303_LOCAL_ACK") == "LOCAL_WF0303"
)
WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED = (
    os.environ.get("CTUG_WF0303_LOCAL_MUTATION_ACK") == "LOCAL_WF0303_MUTATIONS"
)
WORKSPACE_WF0303_SCOPED_GRANT_EVALUATION_ENABLED = (
    os.environ.get("CTUG_WF0303_LOCAL_EVALUATION_ACK") == "LOCAL_WF0303_EVALUATION"
)

# WF-03.04: isolated account-wide Denies and individual Grant/Deny removal.
# Explicit independent review/mutation gates. Requires owner-approved 0005,
# scoped Grant evaluation, delegated authority and protected writer parity.
WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED = (
    os.environ.get("CTUG_WF0304_LOCAL_ACK") == "LOCAL_WF0304"
)
WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED = (
    os.environ.get("CTUG_WF0304_LOCAL_MUTATION_ACK") == "LOCAL_WF0304_MUTATIONS"
)

# WF-03.05: read-only effective access / service state inspector, default OFF.
# Requires exact Technical Super Admin inspection permission and active role context.
# No service activation or permission mutation capability is exposed here.
WORKSPACE_WF0305_EFFECTIVE_ACCESS_INSPECT_ENABLED = (
    os.environ.get("CTUG_WF0305_LOCAL_INSPECT_ACK") == "LOCAL_WF0305_INSPECT"
)

# WF-03.06 read-only audit history; requires exact audit.read in Technical Super
# Admin role context and no protected executor. Default OFF until approved.
WORKSPACE_WF0306_AUDIT_HISTORY_ENABLED = (
    os.environ.get("CTUG_WF0306_AUDIT_LOCAL_ACK") == "LOCAL_WF0306_AUDIT_READ"
)
