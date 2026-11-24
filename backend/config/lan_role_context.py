"""WF-03.01 Option A: fail-closed HTTP LAN testing for explicit host IPs.

Only for synthetic development accounts/data. Not an HTTPS deployment mode,
not device authentication, and not a firewall replacement. No public/VPN
interfaces should be exposed. The launcher binds Vite once per approved local
physical LAN interface and Django to loopback only.

Since the permanent LAN launcher (Start-CTUG-LAN.ps1), Option A refuses the real
``ctug_workspace`` database: HTTP LAN sessions may only reach the hard-named,
marker-verified synthetic database below (see config/dev_lan_settings.py).
"""
from ipaddress import IPv4Address, IPv4Network

LAN_ACK = "LAN_HTTP_SYNTHETIC_ONLY_WF0301_A"
# The only database an HTTP LAN listener may use. Never ctug_workspace.
SYNTHETIC_LAN_DATABASE = "ctug_lan_synthetic"
# config.settings (manual Option A) or the launcher's synthetic LAN profile.
LAN_SETTINGS_MODULES = frozenset({"config.settings", "config.dev_lan_settings"})
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]"})
_PRIVATE_LAN = (
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
)
_MAX_LAN_IPS = 4
_PROTECTED_ENV_FLAGS = (
    "WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER",
    "WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED",
    "WORKSPACE_ROLE_ASSIGNMENT_ENABLED",
    "WORKSPACE_WF0302_ROLE_PERMISSION_MUTATIONS_ENABLED",
    "WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED",
    "WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED",
)


def _parse_lan_ips(env):
    """Accept either the legacy one-IP opt-in or a new explicit 1–4 IP list."""
    legacy = env.get("CTUG_ROLE_CONTEXT_LAN_DEV_IP", "")
    multiple = env.get("CTUG_ROLE_CONTEXT_LAN_DEV_IPS", "")
    if legacy and multiple:
        raise ValueError("Set only one of CTUG_ROLE_CONTEXT_LAN_DEV_IP or CTUG_ROLE_CONTEXT_LAN_DEV_IPS.")
    if not legacy and not multiple:
        raise ValueError("An explicit approved private LAN IP is required.")

    parts = multiple.split(",") if multiple else [legacy]
    if not 1 <= len(parts) <= _MAX_LAN_IPS:
        raise ValueError("LAN test mode accepts between one and four explicitly approved IPv4 addresses.")
    ips = []
    for part in parts:
        raw = part.strip()
        if not raw:
            raise ValueError("Empty LAN IP entry is not allowed.")
        try:
            ip = IPv4Address(raw)
        except (ValueError, TypeError):
            raise ValueError("Every LAN test host must be an explicit IPv4 address.") from None
        if not any(ip in network for network in _PRIVATE_LAN):
            raise ValueError("LAN test IPs must be RFC1918 private IPv4 addresses.")
        if str(ip) in ips:
            raise ValueError("Duplicate LAN IP entry is not allowed.")
        ips.append(str(ip))
    return ips


def validate_lan_dev_role_context(env, *, debug, allowed_hosts, database,
                                  csrf_origins, session_secure, csrf_secure):
    """Return the primary approved LAN IP, None if off, or fail before startup.

    The return shape intentionally stays compatible with settings.py: the
    primary IP is a nonempty str, even when several validated IPs are listed.
    Host/Origin validation never replaces real firewall/client isolation.
    """
    acknowledgment = env.get("CTUG_ROLE_CONTEXT_LAN_DEV_ACK", "")
    if not acknowledgment:
        return None
    if acknowledgment != LAN_ACK:
        raise ValueError("Invalid CTUG_ROLE_CONTEXT_LAN_DEV_ACK; LAN test mode refused.")
    if env.get("CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK"):
        raise ValueError("Localhost and LAN role-context development opt-ins are mutually exclusive.")
    if (env.get("DJANGO_SETTINGS_MODULE") not in LAN_SETTINGS_MODULES
            or env.get("WORKSPACE_DEPLOYMENT_SETTINGS") == "1"
            or env.get("WORKSPACE_DEPLOYMENT_PROFILE", "local") != "local"
            or debug is not True):
        raise ValueError("LAN role switching requires normal, DEBUG-only local settings.")
    if (env.get("WORKSPACE_HTTPS", "0") != "0"
            or env.get("WORKSPACE_TRUST_PROXY_SSL_HEADER", "0") != "0"
            or session_secure or csrf_secure):
        raise ValueError("Option A is HTTP-only testing; HTTPS/proxy deployment requires Option B.")
    if (database.get("ENGINE") != "django.db.backends.mysql"
            or database.get("NAME") != SYNTHETIC_LAN_DATABASE
            or database.get("HOST") not in {"localhost", "127.0.0.1", "::1"}):
        raise ValueError(
            "LAN role switching requires the local synthetic MySQL database "
            f"{SYNTHETIC_LAN_DATABASE}; real data is never served over HTTP LAN. "
            "Use .\\Start-CTUG-LAN.ps1 and remove CTUG_ROLE_CONTEXT_LAN_DEV_* from backend/.env."
        )

    lan_ips = _parse_lan_ips(env)
    permitted_hosts = LOOPBACK_HOSTS | set(lan_ips)
    hosts = list(allowed_hosts)
    if (not hosts or len(hosts) != len(set(hosts))
            or not set(lan_ips).issubset(hosts)
            or any(host not in permitted_hosts for host in hosts)):
        raise ValueError("LAN testing requires only localhost and all explicitly approved LAN IPs in ALLOWED_HOSTS.")

    permitted_origins = {f"http://{ip}:5173" for ip in lan_ips}
    permitted_origins.update({"http://127.0.0.1:5173", "http://localhost:5173"})
    if (any(origin not in permitted_origins for origin in csrf_origins)
            or not {f"http://{ip}:5173" for ip in lan_ips}.issubset(csrf_origins)):
        raise ValueError("CSRF_TRUSTED_ORIGINS must include every approved LAN origin and no extras.")
    if any(env.get(name) == "1" for name in _PROTECTED_ENV_FLAGS):
        raise ValueError("Protected writer/governance flags must remain disabled in LAN test mode.")
    return lan_ips[0]
