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
# The runtime is deliberately not authorized to activate WF-03 by .env.
# Only an explicit validated deployment config may opt in, after the scope
# table is fenced and the executor and runtime are upgraded together.
ACCESS_CONTROL_DELEGATION_POLICY = _runtime_config.get("delegation_policy", {})
WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED = _runtime_config.get("wf03_executor_account_writes_enabled", False)
WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED = _runtime_config.get("wf03_active_role_context_enabled", False)
WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED = _runtime_config.get("wf0303_account_grants_enabled", False)
WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED = _runtime_config.get("wf0303_account_grant_mutations_enabled", False)
WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED = _runtime_config.get("wf0304_account_restrictions_enabled", False)
WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED = _runtime_config.get("wf0304_account_restriction_mutations_enabled", False)
WORKSPACE_WF0303_SCOPED_GRANT_EVALUATION_ENABLED = _runtime_config.get("wf0303_scoped_grant_evaluation_enabled", False)
for _wf03_toggle in (WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED,
                     WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED,
                     WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED,
                     WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED,
                     WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED,
                     WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED,
                     WORKSPACE_WF0303_SCOPED_GRANT_EVALUATION_ENABLED):
    if type(_wf03_toggle) is not bool:
        raise ImproperlyConfigured("WF-03 runtime toggles must be explicit booleans.")
# Middleware remains inert with default-off role-context configuration.
MIDDLEWARE = [*MIDDLEWARE, "apps.accounts.active_role_context.ActiveRoleContextMiddleware",
              "apps.access_control.executor.client.ExecutorProofMiddleware"]  # noqa: F405
