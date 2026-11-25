"""WF-03.01: explicit HTTPS LAN *development* role-context activation.

This does not enable role grants, protected executor operations, or any database
migration. TLS is terminated at an explicitly bound Vite dev proxy; Django
accepts the matching proxy header from localhost only.

The HTTPS dev profile is deliberately distinct from the existing localhost and
HTTP Option A profiles. It is NOT a production deployment authorization.
"""
from ipaddress import IPv4Address, IPv4Network
from urllib.parse import urlsplit

HTTPS_ACK = "LAN_HTTPS_DEV_SYNTHETIC_WF0301_B"
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]"})
PRIVATE_NETWORKS = (
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
)
PROTECTED_FLAGS = (
    "WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER",
    "WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED",
    "WORKSPACE_ROLE_ASSIGNMENT_ENABLED",
    "WORKSPACE_WF0302_ROLE_PERMISSION_MUTATIONS_ENABLED",
    "WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED",
    "WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED",
)


def _approved_ips(value):
    if not value or not isinstance(value, str):
        raise ValueError("CTUG_ROLE_CONTEXT_HTTPS_LAN_IPS requires 1-4 private LAN IPv4 addresses.")
    values = value.split(",")
    if not 1 <= len(values) <= 4:
        raise ValueError("CTUG_ROLE_CONTEXT_HTTPS_LAN_IPS requires 1-4 private LAN IPv4 addresses.")
    addresses = []
    for raw in values:
        candidate = raw.strip()
        try:
            address = IPv4Address(candidate)
        except (ValueError, TypeError):
            raise ValueError("HTTPS LAN IP list contains an invalid IPv4 address.") from None
        if candidate != str(address) or not any(address in network for network in PRIVATE_NETWORKS):
            raise ValueError("HTTPS LAN IPs must be canonical RFC1918 private IPv4 addresses.")
        if candidate in addresses:
            raise ValueError("Duplicate HTTPS LAN IP in the allowlist.")
        addresses.append(candidate)
    return tuple(addresses)


def validate_https_lan_dev_role_context(
    env, *, debug, allowed_hosts, database, csrf_origins, session_secure,
    csrf_secure, ssl_redirect, proxy_ssl_header, hsts_seconds,
):
    """Return approved IPs, None when off; raise ValueError if enabled unsafely."""
    ack = (env.get("CTUG_ROLE_CONTEXT_HTTPS_LAN_DEV_ACK") or "").strip()
    if not ack:
        return None
    if ack != HTTPS_ACK:
        raise ValueError("Invalid HTTPS LAN role-context acknowledgment.")
    if env.get("CTUG_ROLE_CONTEXT_LAN_DEV_ACK") or env.get("CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK"):
        raise ValueError("HTTPS LAN, HTTP LAN and localhost role-context modes are mutually exclusive.")
    if (
        env.get("DJANGO_SETTINGS_MODULE") != "config.settings"
        or env.get("WORKSPACE_DEPLOYMENT_SETTINGS") == "1"
        or env.get("WORKSPACE_DEPLOYMENT_PROFILE", "local") != "local"
        or debug is not True
    ):
        raise ValueError("HTTPS LAN role switching requires normal, DEBUG-only local settings.")
    if (
        env.get("WORKSPACE_HTTPS") != "1"
        or env.get("WORKSPACE_TRUST_PROXY_SSL_HEADER") != "1"
        or session_secure is not True
        or csrf_secure is not True
        or ssl_redirect is not False
        or proxy_ssl_header != ("HTTP_X_FORWARDED_PROTO", "https")
        or hsts_seconds != 0
    ):
        raise ValueError("HTTPS LAN development requires Secure cookies, controlled TLS proxy, SSL_REDIRECT=0 and HSTS=0.")
    if (
        database.get("ENGINE") != "django.db.backends.mysql"
        or database.get("NAME") != "ctug_workspace"
        or database.get("HOST") not in {"localhost", "127.0.0.1", "::1"}
    ):
        raise ValueError("HTTPS LAN development requires local ctug_workspace MySQL.")

    ips = _approved_ips(env.get("CTUG_ROLE_CONTEXT_HTTPS_LAN_IPS"))
    host_list = list(allowed_hosts)
    permitted_hosts = LOOPBACK_HOSTS.union(ips)
    if (
        not host_list
        or len(host_list) != len(set(host_list))
        or set(ips).difference(host_list)
        or any(host not in permitted_hosts for host in host_list)
    ):
        raise ValueError("HTTPS LAN ALLOWED_HOSTS must contain the approved IPs and only loopback extras.")
    accepted_origins = {f"https://{ip}:5173" for ip in ips}
    accepted_origins.update({"https://localhost:5173", "https://127.0.0.1:5173"})
    origins = list(csrf_origins)
    if (
        len(origins) != len(set(origins))
        or set(f"https://{ip}:5173" for ip in ips).difference(origins)
        or any(origin not in accepted_origins for origin in origins)
    ):
        raise ValueError("HTTPS LAN CSRF origins must be exact HTTPS :5173 origins for approved IPs.")
    public_url = env.get("WORKSPACE_PUBLIC_BASE_URL", "")
    parsed = urlsplit(public_url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != f"{ips[0]}:5173"
        or parsed.path not in {"", "/"}
        or parsed.query or parsed.fragment or parsed.username or parsed.password
    ):
        raise ValueError("WORKSPACE_PUBLIC_BASE_URL must use HTTPS and the first approved LAN IP :5173.")
    if any(env.get(name) == "1" for name in PROTECTED_FLAGS):
        raise ValueError("Protected executor or governance mutation flags must be disabled in HTTPS LAN development.")
    return ips
