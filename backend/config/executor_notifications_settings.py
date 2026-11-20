"""Independent least-privilege outbox worker. Delivery remains separately gated."""
import json
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

_notification_config = json.loads(Path(os.environ["WORKSPACE_NOTIFICATIONS_CONFIG"]).read_text())
os.environ["WORKSPACE_DEPLOYMENT_SETTINGS"] = "1"
for _key, _field in (("DB_NAME", "NAME"), ("DB_USER", "USER"), ("DB_PASSWORD", "PASSWORD"), ("DB_HOST", "HOST"), ("DB_PORT", "PORT")):
    os.environ[_key] = str(_notification_config["database"][_field])
from .settings import *  # noqa: F403

DATABASES = {"default": _notification_config["database"]}
WORKSPACE_REGISTRATION_OUTBOX_ENABLED = True
DEBUG = False
if DATABASES["default"].get("OPTIONS", {}).get("ssl_mode") != "VERIFY_IDENTITY":
    raise ImproperlyConfigured("Notification worker DB transport requires verified TLS.")
WORKSPACE_NOTIFICATIONS_IDENTITY = _notification_config["identity"]
