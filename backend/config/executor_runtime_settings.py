"""Restricted web/runtime profile; no executor DB credential is accepted."""
import json
import os
from pathlib import Path

_runtime_config = json.loads(Path(os.environ["WORKSPACE_RUNTIME_CONFIG"]).read_text(encoding="utf-8"))
os.environ["WORKSPACE_DEPLOYMENT_SETTINGS"] = "1"
for _key, _field in (("DB_NAME", "NAME"), ("DB_USER", "USER"), ("DB_PASSWORD", "PASSWORD"), ("DB_HOST", "HOST"), ("DB_PORT", "PORT")):
    os.environ[_key] = str(_runtime_config["database"][_field])
from .settings import *  # noqa: F403

DATABASES = {"default": _runtime_config["database"]}
WORKSPACE_EXECUTOR_CLIENTS = _runtime_config["clients"]
from django.core.exceptions import ImproperlyConfigured
if set(WORKSPACE_EXECUTOR_CLIENTS) != {"ordinary"}:
    raise ImproperlyConfigured("Web runtime may hold only the ordinary client identity.")
if DATABASES["default"].get("OPTIONS", {}).get("ssl_mode") != "VERIFY_IDENTITY":
    raise ImproperlyConfigured("Runtime DB transport requires verified TLS.")
WORKSPACE_RUNTIME_IDENTITY = _runtime_config["identity"]
WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER = True
DEBUG = False
ALLOWED_HOSTS = _runtime_config["allowed_hosts"]
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
MIDDLEWARE = [*MIDDLEWARE, "apps.access_control.executor.client.ExecutorProofMiddleware"]  # noqa: F405
