"""Dedicated executor process; reads no backend/.env or runtime DB credential."""
import json
import os
from pathlib import Path

_executor_config = json.loads(Path(os.environ["WORKSPACE_EXECUTOR_CONFIG"]).read_text(encoding="utf-8"))
os.environ["WORKSPACE_DEPLOYMENT_SETTINGS"] = "1"
for _key, _field in (("DB_NAME", "NAME"), ("DB_USER", "USER"), ("DB_PASSWORD", "PASSWORD"), ("DB_HOST", "HOST"), ("DB_PORT", "PORT")):
    os.environ[_key] = str(_executor_config["database"][_field])
from .settings import *  # noqa: F403

DATABASES = {"default": _executor_config["database"]}
WORKSPACE_EXECUTOR_SERVER = _executor_config["server"]
WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER = True
DEBUG = False
ALLOWED_HOSTS = []  # the dedicated mTLS server has no Django routes
WORKSPACE_REGISTRATION_APPROVAL_ENABLED = True
# WF-02.04 D-61 (owner-authorized 18 Nov 2026, partial retirement): rejected-account
# reapplication is disabled in the executor too, so no Rejected account can be revived through
# it. The code, routes and protocol handler stay until a separately authorized removal.
WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED = False
WORKSPACE_FIRST_ADMIN_BOOTSTRAP_ENABLED = _executor_config.get("first_admin_bootstrap_enabled", False)
if type(WORKSPACE_FIRST_ADMIN_BOOTSTRAP_ENABLED) is not bool:
    raise ValueError("Explicit boolean first-Admin bootstrap policy required.")
WORKSPACE_REGISTRATION_OUTBOX_ENABLED = _executor_config.get("outbox_enabled", False)
ACCESS_CONTROL_DELEGATION_POLICY = _executor_config.get("delegation_policy", {})
WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_POLICY = _executor_config.get("ordinary_assignment_policy", {})
# Explicitly disabled until the new role-scope table has a matching SQL fence
# and runtime/ordinary executor use the same approved delegation policy.
WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED = _executor_config.get("wf03_executor_account_writes_enabled", False)
WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED = _executor_config.get("wf03_active_role_context_enabled", False)
WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED = _executor_config.get("wf0303_account_grant_mutations_enabled", False)
WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED = _executor_config.get("wf0304_account_restriction_mutations_enabled", False)
WORKSPACE_WF0303_SCOPED_GRANT_EVALUATION_ENABLED = _executor_config.get("wf0303_scoped_grant_evaluation_enabled", False)
for _wf03_toggle in (WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED,
                     WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED,
                     WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED,
                     WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED,
                     WORKSPACE_WF0303_SCOPED_GRANT_EVALUATION_ENABLED):
    if type(_wf03_toggle) is not bool:
        raise ValueError("WF-03 executor toggles must be explicit booleans.")

# Plain transport exceptions exist only in the independently identity-checked
# second-server harness. Production must validate the MySQL server over TLS.
if not _executor_config.get("isolated_test", False):
    from django.core.exceptions import ImproperlyConfigured
    if DATABASES["default"].get("OPTIONS", {}).get("ssl_mode") != "VERIFY_IDENTITY":
        raise ImproperlyConfigured("Executor DB transport requires verified TLS.")
else:
    from django.core.exceptions import ImproperlyConfigured
    if not DATABASES["default"]["NAME"].startswith("test_ctug_executor_") or DATABASES["default"].get("HOST") != ".":
        raise ImproperlyConfigured("Isolated executor requires a private named-pipe test database.")
