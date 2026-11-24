"""Process environment for the synthetic LAN development profile (config.dev_lan_settings).

Runs BEFORE config.settings loads backend/.env. python-dotenv never overrides a
variable that already exists, so every value prepared here wins over .env:

* the database is the hard-named synthetic schema, never ``ctug_workspace``;
* the session secret and outbox key come from the git-ignored local file
  ``.local/ctug-lan/synthetic.env`` (created once by Initialize-CTUG-LAN.ps1),
  never from the real configuration;
* every env-driven feature switch (``*_ENABLED``), opt-in acknowledgment
  (``*_ACK``) and protected-writer flag from the shell or .env is neutralized, so
  config.dev_features is the only source of feature availability;
* SMTP is off, so real mail credentials are never even read;
* when the launcher supplies ``CTUG_DEV_LAN_IP``, the existing Option A HTTP LAN
  gate is configured for exactly that private address (it re-validates
  everything at settings import and fails closed).

No secret value is ever printed or logged by this module.
"""

from ipaddress import IPv4Address, IPv4Network
from pathlib import Path

from .lan_role_context import LAN_ACK, SYNTHETIC_LAN_DATABASE

LAN_IP_VARIABLE = "CTUG_DEV_LAN_IP"
FRONTEND_PORT = 5173
SYNTHETIC_EMAIL_DOMAIN = "synthetic.ctug.test"  # RFC 6761 reserved: never deliverable
SECRET_FILE_PARTS = (".local", "ctug-lan", "synthetic.env")
REQUIRED_SECRETS = ("DJANGO_SECRET_KEY", "WORKSPACE_OUTBOX_KEK_V1_B64")

_PRIVATE = (IPv4Network("10.0.0.0/8"), IPv4Network("172.16.0.0/12"), IPv4Network("192.168.0.0/16"))
_FLAG_PREFIXES = ("WORKSPACE_", "CTUG_")
_FLAG_SUFFIXES = ("_ENABLED", "_ACK")
# Flags that do not follow the suffix convention but must never be inherited.
_ALWAYS_OFF = (
    "WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER",
    "WORKSPACE_TRUST_PROXY_SSL_HEADER",
    "WORKSPACE_HTTPS",
    "WORKSPACE_SSL_REDIRECT",
    # The outbox worker reads this from the process environment: never deliver from LAN.
    "WORKSPACE_OUTBOX_WORKER_ENABLED",
)
_ALWAYS_EMPTY = (
    "CTUG_ROLE_CONTEXT_LAN_DEV_IP",
    "CTUG_ROLE_CONTEXT_LAN_DEV_IPS",
    "CTUG_ROLE_CONTEXT_HTTPS_LAN_IPS",
    "WORKSPACE_EMAIL_PUBLIC_HOSTS",
    "WORKSPACE_EXECUTOR_URL",
)


class DevLanEnvironmentError(ValueError):
    """The synthetic LAN profile cannot start safely."""


def secret_file(repo_root):
    return Path(repo_root).joinpath(*SECRET_FILE_PARTS)


def validate_lan_ip(raw):
    try:
        ip = IPv4Address((raw or "").strip())
    except ValueError:
        raise DevLanEnvironmentError("CTUG_DEV_LAN_IP must be an explicit IPv4 address.") from None
    if not any(ip in network for network in _PRIVATE):
        raise DevLanEnvironmentError("CTUG_DEV_LAN_IP must be a private (RFC 1918) LAN address.")
    return str(ip)


def neutralized_flags(names):
    """Feature/ack flags that must be switched off whatever the shell or .env says."""
    updates = {}
    for name in names:
        if name.startswith(_FLAG_PREFIXES) and name.endswith(_FLAG_SUFFIXES):
            updates[name] = "" if name.endswith("_ACK") else "0"
    updates.update({name: "0" for name in _ALWAYS_OFF})
    updates.update({name: "" for name in _ALWAYS_EMPTY})
    return updates


def prepare_environment(env, *, dotenv_names, local_secrets):
    """Return the variables to set for config.dev_lan_settings (``env`` is not modified)."""
    missing = [name for name in REQUIRED_SECRETS if not local_secrets.get(name)]
    if missing:
        raise DevLanEnvironmentError(
            "Synthetic LAN secrets are missing. Run .\\Initialize-CTUG-LAN.ps1 once from the repository root."
        )
    if env.get("WORKSPACE_DEPLOYMENT_SETTINGS") == "1":
        raise DevLanEnvironmentError("The synthetic LAN profile never runs with deployment settings.")

    updates = neutralized_flags(set(env) | set(dotenv_names))
    updates.update({
        "DJANGO_DEBUG": "1",
        "WORKSPACE_DEPLOYMENT_PROFILE": "local",
        "WORKSPACE_DEPLOYMENT_SETTINGS": "0",
        "WORKSPACE_HSTS_SECONDS": "0",
        "DB_NAME": SYNTHETIC_LAN_DATABASE,
        # Dedicated synthetic secrets: sessions and encrypted outbox rows are not
        # interchangeable with any real-database configuration.
        "DJANGO_SECRET_KEY": local_secrets["DJANGO_SECRET_KEY"],
        "STUDENT_REGISTRATION_STAGING_KEY": local_secrets["DJANGO_SECRET_KEY"],
        "WORKSPACE_OUTBOX_KEK_V1_B64": local_secrets["WORKSPACE_OUTBOX_KEK_V1_B64"],
        "WORKSPACE_OUTBOX_ACTIVE_KEY_VERSION": "v1",
        # SMTP off: real mail credentials are not read; mail stays in-process.
        "WORKSPACE_EMAIL_SMTP_ENABLED": "0",
        "WORKSPACE_PASSWORD_RESET_ENABLED": "0",
        "WORKSPACE_EMAIL_FROM": f"no-reply@{SYNTHETIC_EMAIL_DOMAIN}",
        "CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK": "",
        "CTUG_ROLE_CONTEXT_HTTPS_LAN_DEV_ACK": "",
    })

    raw_ip = env.get(LAN_IP_VARIABLE, "")
    loopback_origins = [f"http://localhost:{FRONTEND_PORT}", f"http://127.0.0.1:{FRONTEND_PORT}"]
    if raw_ip:
        ip = validate_lan_ip(raw_ip)
        origin = f"http://{ip}:{FRONTEND_PORT}"
        updates.update({
            # Existing Option A gate: exactly one approved LAN address, HTTP-only,
            # loopback Django behind Vite, protected writers refused.
            "CTUG_ROLE_CONTEXT_LAN_DEV_ACK": LAN_ACK,
            "CTUG_ROLE_CONTEXT_LAN_DEV_IPS": ip,
            "WORKSPACE_ALLOWED_HOSTS": f"localhost,127.0.0.1,[::1],{ip}",
            "WORKSPACE_CSRF_TRUSTED_ORIGINS": ",".join([*loopback_origins, origin]),
            "WORKSPACE_PUBLIC_BASE_URL": origin,
        })
    else:
        # Maintenance commands (initialize, shell) stay loopback-only.
        updates.update({
            "CTUG_ROLE_CONTEXT_LAN_DEV_ACK": "",
            "WORKSPACE_ALLOWED_HOSTS": "localhost,127.0.0.1,[::1]",
            "WORKSPACE_CSRF_TRUSTED_ORIGINS": ",".join(loopback_origins),
            "WORKSPACE_PUBLIC_BASE_URL": loopback_origins[0],
        })
    return updates


def apply_environment(environ, *, backend_dir):
    """Read the local files and update ``environ`` in place (os.environ in practice)."""
    from dotenv import dotenv_values

    backend_dir = Path(backend_dir)
    dotenv_names = list(dotenv_values(backend_dir / ".env")) if (backend_dir / ".env").exists() else []
    path = secret_file(backend_dir.parent)
    local_secrets = dotenv_values(path) if path.exists() else {}
    updates = prepare_environment(environ, dotenv_names=dotenv_names, local_secrets=local_secrets)
    environ.update(updates)
    return updates
