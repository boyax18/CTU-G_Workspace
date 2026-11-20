"""WF-01.06 (owner-approved 17 Nov 2026): validated, environment-driven security settings.

D-18: DEBUG defaults to off; HTTPS and Secure cookies are mandatory for the
"production" profile; local HTTP development keeps working under the default
"local" profile. Proxy SSL trust, HSTS and trusted origins apply only when
explicitly configured and consistent with HTTPS. Session limits: 30-minute idle,
8-hour absolute (enforced by apps.accounts.session_timeout).
D-29: the CSRF cookie is HttpOnly; the browser client takes the token from the
GET /api/v1/auth/csrf/ response body and never reads the cookie.

This module is pure (it reads only the mapping it is given) so it can be tested
without reloading Django settings. It never logs or returns secret values.
"""

from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

PROFILES = ("local", "production")
DEFAULT_IDLE_SECONDS = 1800        # D-18: 30 minutes
DEFAULT_ABSOLUTE_SECONDS = 28800   # D-18: 8 hours after sign-in
MAX_HSTS_SECONDS = 63072000        # 2 years


def _flag(env, name, default=False):
    value = (env.get(name) or "").strip()
    if value == "":
        return default
    if value not in ("0", "1"):
        raise ImproperlyConfigured(f"{name} must be 0 or 1.")
    return value == "1"


def _integer(env, name, default, minimum, maximum):
    value = (env.get(name) or "").strip()
    if value == "":
        return default
    if not value.isascii() or not value.isdigit():
        raise ImproperlyConfigured(f"{name} must be a whole number of seconds.")
    number = int(value)
    if not minimum <= number <= maximum:
        raise ImproperlyConfigured(f"{name} must be between {minimum} and {maximum}.")
    return number


def _origins(env, https):
    origins = []
    for raw in (env.get("WORKSPACE_CSRF_TRUSTED_ORIGINS") or "").split(","):
        origin = raw.strip()
        if not origin:
            continue
        parts = urlsplit(origin)
        if (parts.scheme not in ("http", "https") or not parts.netloc or parts.path not in ("", "/")
                or parts.query or parts.fragment or parts.username or parts.password or "*" in parts.netloc):
            raise ImproperlyConfigured("WORKSPACE_CSRF_TRUSTED_ORIGINS must list exact scheme://host[:port] origins.")
        if https and parts.scheme != "https":
            raise ImproperlyConfigured("WORKSPACE_CSRF_TRUSTED_ORIGINS must use https when WORKSPACE_HTTPS=1.")
        origins.append(f"{parts.scheme}://{parts.netloc}")
    return origins


def build_security_settings(env):
    """Return the security settings for the given environment mapping, or raise ImproperlyConfigured."""
    profile = (env.get("WORKSPACE_DEPLOYMENT_PROFILE") or "local").strip()
    if profile not in PROFILES:
        raise ImproperlyConfigured("WORKSPACE_DEPLOYMENT_PROFILE must be 'local' or 'production'.")
    debug = _flag(env, "DJANGO_DEBUG", False)
    https = _flag(env, "WORKSPACE_HTTPS", False)
    trust_proxy = _flag(env, "WORKSPACE_TRUST_PROXY_SSL_HEADER", False)
    hsts = _integer(env, "WORKSPACE_HSTS_SECONDS", 0, 0, MAX_HSTS_SECONDS)
    idle = _integer(env, "WORKSPACE_SESSION_IDLE_SECONDS", DEFAULT_IDLE_SECONDS, 60, 86400)
    absolute = _integer(env, "WORKSPACE_SESSION_ABSOLUTE_SECONDS", DEFAULT_ABSOLUTE_SECONDS, 300, 7 * 86400)
    if idle > absolute:
        raise ImproperlyConfigured("WORKSPACE_SESSION_IDLE_SECONDS must not exceed WORKSPACE_SESSION_ABSOLUTE_SECONDS.")
    if trust_proxy and not https:
        raise ImproperlyConfigured("WORKSPACE_TRUST_PROXY_SSL_HEADER requires WORKSPACE_HTTPS=1.")
    if hsts and not https:
        raise ImproperlyConfigured("WORKSPACE_HSTS_SECONDS requires WORKSPACE_HTTPS=1.")
    if profile == "production":
        if debug:
            raise ImproperlyConfigured("DJANGO_DEBUG must be off for the production profile.")
        if not https:
            raise ImproperlyConfigured("The production profile requires WORKSPACE_HTTPS=1 (HTTPS and Secure cookies).")
        if any(host.strip() == "*" for host in (env.get("WORKSPACE_ALLOWED_HOSTS") or "").split(",")):
            raise ImproperlyConfigured("WORKSPACE_ALLOWED_HOSTS must not contain '*' in production.")
    return {
        "WORKSPACE_DEPLOYMENT_PROFILE": profile,
        "DEBUG": debug,
        # Cookies: HttpOnly session and CSRF cookies; Secure whenever HTTPS is on.
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": https,
        "SESSION_COOKIE_AGE": absolute,
        "CSRF_COOKIE_HTTPONLY": True,
        "CSRF_COOKIE_SAMESITE": "Lax",
        "CSRF_COOKIE_SECURE": https,
        "CSRF_TRUSTED_ORIGINS": _origins(env, https),
        # HTTPS transport. Redirect can be turned off when a trusted proxy already redirects.
        "SECURE_SSL_REDIRECT": https and _flag(env, "WORKSPACE_SSL_REDIRECT", True),
        "SECURE_HSTS_SECONDS": hsts if https else 0,
        "SECURE_PROXY_SSL_HEADER": ("HTTP_X_FORWARDED_PROTO", "https") if trust_proxy else None,
        # No cross-origin browser access, and never credentialed CORS.
        "CORS_ALLOWED_ORIGINS": [],
        "CORS_ALLOW_ALL_ORIGINS": False,
        "CORS_ALLOW_CREDENTIALS": False,
        # Session expiry policy (D-18).
        "WORKSPACE_SESSION_IDLE_SECONDS": idle,
        "WORKSPACE_SESSION_ABSOLUTE_SECONDS": absolute,
    }
