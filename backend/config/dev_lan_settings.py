"""Synthetic LAN development profile used by Start-CTUG-LAN.ps1. NEVER deploy.

* Database: the hard-named synthetic schema ``ctug_lan_synthetic`` only. Startup
  is refused if the configured name differs; ``manage.py ctug_lan preflight``
  additionally verifies the connected schema and its synthetic marker.
* Network: the existing Option A gate (config.lan_role_context) — HTTP on one
  private LAN address through Vite, Django on loopback behind the proxy guard.
* Features: only what config.dev_features approves for ``lan-synthetic``;
  every other registered gate is forced off.
* Mail: in-process (locmem) only; SMTP disabled, outbox worker never started.
  Decisions still durably queue encrypted notifications in the synthetic DB.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from .dev_lan_environment import DevLanEnvironmentError, apply_environment

if os.environ.get("DJANGO_SETTINGS_MODULE") != "config.dev_lan_settings":
    raise ImproperlyConfigured("Select this profile with DJANGO_SETTINGS_MODULE=config.dev_lan_settings.")
try:
    apply_environment(os.environ, backend_dir=Path(__file__).resolve().parent.parent)
except DevLanEnvironmentError as exc:
    raise ImproperlyConfigured(str(exc)) from exc

from .settings import *  # noqa: E402,F401,F403 -- same application, validated gates
from .settings import DATABASES, DEBUG  # noqa: E402
from .lan_role_context import SYNTHETIC_LAN_DATABASE  # noqa: E402
from .dev_features import LAN_SYNTHETIC, profile_settings  # noqa: E402

_db = DATABASES["default"]
if (_db["ENGINE"] != "django.db.backends.mysql"
        or _db["NAME"] != SYNTHETIC_LAN_DATABASE
        or _db.get("HOST") not in {"localhost", "127.0.0.1", "::1"}
        or DEBUG is not True):
    raise ImproperlyConfigured(
        f"The LAN profile requires local MySQL {SYNTHETIC_LAN_DATABASE} and DEBUG; refusing to start."
    )

WORKSPACE_DEV_PROFILE = LAN_SYNTHETIC
ROOT_URLCONF = "config.dev_lan_urls"

# Centrally registered features (approved on, everything else registered forced off).
globals().update(profile_settings(LAN_SYNTHETIC))

# Safe notification sink: nothing can leave this machine.
WORKSPACE_EMAIL_SMTP_ENABLED = False
WORKSPACE_PASSWORD_RESET_ENABLED = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
# The outbox worker stays off (WORKSPACE_OUTBOX_WORKER_ENABLED=0 in dev_lan_environment).

# Separate cookies so synthetic LAN sessions never mix with localhost sessions.
SESSION_COOKIE_NAME = "ctug_lan_synthetic_session"
CSRF_COOKIE_NAME = "ctug_lan_synthetic_csrf"
