"""Central development feature registry for Start-CTUG-LAN.ps1 (development only).

The launcher never names a workflow, flag or route. It asks
``backend/scripts/ctug_dev_preflight.py`` for the environment of a launch mode,
and this registry is the one place a finished feature is declared. Both modes use
the normal development database configured in backend/.env (``ctug_workspace``)
and EXISTING settings profiles; nothing here creates data, grants permissions,
mounts routes or relaxes a gate:

* ``lan``   - config.settings + the existing Option A HTTP LAN gate for the detected
  private address (Django on loopback behind Vite, role context, protected writers
  refused). Only the routes of config.urls exist in this mode.
* ``local`` - the existing loopback-only decision profile
  config.review_decision_local_settings (its own acknowledgment, LoopbackOnly
  middleware, decision routes, locmem mail) at http://127.0.0.1:5173.

A feature is available in a mode when it is registered here, approved for that
mode, its dependencies are available and its prerequisites pass. Exact effective
permissions, the active Admin assignment, Active Role scope, services and
CSRF/session checks remain enforced by Django on every request. Registered
features that are not approved for a mode get their frontend flags set to "0".

Finishing a future module = add one ``Feature`` (backend env gate, frontend build
flags, modes). No launcher change is needed.
"""

import base64
import binascii
import os
from dataclasses import dataclass, field
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path

LAN, LOCAL = "lan", "local"
MODES = frozenset({LAN, LOCAL})
FRONTEND_PORT = 5173
BACKEND_TARGET = "http://127.0.0.1:8000"
LAN_ACK = "LAN_HTTP_SYNTHETIC_ONLY_WF0301_A"  # existing Option A acknowledgment (config/lan_role_context.py)

SETTINGS_MODULES = {LAN: "config.settings", LOCAL: "config.review_decision_local_settings"}


@dataclass(frozen=True)
class Feature:
    key: str
    workflow: str
    title: str
    modes: frozenset = frozenset()          # empty = registered but not approved
    backend_env: dict = field(default_factory=dict)
    frontend_flags: tuple = ()
    requires: tuple = ()
    prerequisites: tuple = ()
    # Background commands (manage.py arguments) the launcher runs while this feature is available.
    workers: tuple = ()
    note: str = ""


FEATURES = (
    Feature("wf02.applicant_reviews", "WF-02.01/02.02", "Pending Applicants and Applicant Details",
            modes=frozenset({LAN, LOCAL}),
            backend_env={"WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED": "1"},
            frontend_flags=("VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED",)),
    Feature("wf02.account_directory", "WF-02.05 (read)", "Account Directory, account details and history",
            modes=frozenset({LAN, LOCAL}),
            backend_env={"WORKSPACE_ACCOUNT_DIRECTORY_ENABLED": "1"},
            frontend_flags=("VITE_WORKSPACE_ACCOUNT_DIRECTORY_ENABLED",)),
    Feature("wf02.applicant_decisions", "WF-02.03/02.04", "Approve / Reject applicant (durable encrypted outbox)",
            modes=frozenset({LOCAL}),
            frontend_flags=("VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED",
                            "VITE_WORKSPACE_REGISTRATION_REJECTION_ENABLED"),
            prerequisites=("outbox_key",),
            note="Decision routes exist only in the loopback decision profile (.\\Start-CTUG-LAN.ps1 -Local)."),
    Feature("wf02.bulk_decisions", "WF-02.03/02.04", "Bulk Approve / Bulk Reject (1-20 applicants)",
            modes=frozenset({LOCAL}),
            backend_env={"WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED": "1"},
            frontend_flags=("VITE_WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED",),
            requires=("wf02.applicant_decisions",),
            note="Decision routes exist only in the loopback decision profile (.\\Start-CTUG-LAN.ps1 -Local)."),
    Feature("wf01-02.email_delivery", "WF-01/WF-02", "Email delivery: registration OTP, password recovery, decision notifications",
            modes=frozenset({LOCAL}),
            prerequisites=("local_email_opt_in",),
            workers=(("manage.py", "process_registration_outbox", "--deliver", "--watch", "15"),),
            note="Optional: set WORKSPACE_LOCAL_EMAIL_DELIVERY=1, WORKSPACE_OUTBOX_WORKER_ENABLED=1 and "
                 "WORKSPACE_OUTBOX_SMTP_DELIVERY_APPROVED=1 once in backend/.env (Gmail SMTP must be configured)."),
    # Registered, not approved for any launcher mode (protected; separately gated).
    Feature("wf02.account_status_changes", "WF-02.05 (write)", "Suspend / Activate accounts",
            frontend_flags=("VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED",),
            note="Protected status writes stay in the separately acknowledged local-review profile."),
    Feature("wf03.access_governance", "WF-03.01-03.06", "Role assignment, permissions, grants, restrictions, inspector, audit",
            frontend_flags=("VITE_WORKSPACE_ROLE_ASSIGNMENT_ENABLED", "VITE_WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_ENABLED",
                            "VITE_WORKSPACE_APPOINTMENT_MANAGEMENT_ENABLED", "VITE_WORKSPACE_WF0302_ROLE_PERMISSIONS_ENABLED",
                            "VITE_WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED", "VITE_WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED",
                            "VITE_WORKSPACE_WF0305_EFFECTIVE_ACCESS_INSPECT_ENABLED", "VITE_WORKSPACE_WF0306_AUDIT_HISTORY_ENABLED"),
            note="Protected Access Control Management keeps its own acknowledgments and executor boundary."),
)

# One-time, explicit opt-in for real email in -Local mode (all three, in backend/.env).
LOCAL_EMAIL_FLAGS = ("WORKSPACE_EMAIL_SMTP_ENABLED", "WORKSPACE_LOCAL_EMAIL_DELIVERY",
                     "WORKSPACE_OUTBOX_WORKER_ENABLED", "WORKSPACE_OUTBOX_SMTP_DELIVERY_APPROVED")

_PRIVATE = (IPv4Network("10.0.0.0/8"), IPv4Network("172.16.0.0/12"), IPv4Network("192.168.0.0/16"))


def validate_lan_ip(raw):
    try:
        ip = IPv4Address((raw or "").strip())
    except ValueError:
        raise ValueError("The LAN address must be an explicit IPv4 address.") from None
    if not any(ip in network for network in _PRIVATE):
        raise ValueError("The LAN address must be a private (RFC 1918) address.")
    return str(ip)


def outbox_key_ready(env):
    """Same rule as apps.accounts.outbox_crypto: a 32-byte base64 key and the AEAD library."""
    value = env.get("WORKSPACE_OUTBOX_KEK_V1_B64") or ""
    try:
        if len(base64.b64decode(value, validate=True)) != 32:
            return False
        import cryptography.hazmat.primitives.ciphers.aead  # noqa: F401
    except (ValueError, binascii.Error, ImportError):
        return False
    return True


def _prerequisite_failures(item, env):
    failures = []
    for name in item.prerequisites:
        if name == "local_email_opt_in":
            missing = [flag for flag in LOCAL_EMAIL_FLAGS if env.get(flag) != "1"]
            if missing:
                failures.append("not enabled (optional): set " + ", ".join(f"{flag}=1" for flag in missing)
                                + " once in backend/.env")
        if name == "outbox_key" and not outbox_key_ready(env):
            failures.append("no valid WORKSPACE_OUTBOX_KEK_V1_B64 in backend/.env or the environment "
                            "(decisions stay fail-closed)")
    return failures


def mode_environment(mode, *, lan_ip=None, env=None):
    """Return {settings_module, backend_env, frontend_env, frontend_args, url, features}."""
    if mode not in MODES:
        raise ValueError(f"Unknown launch mode {mode!r}.")
    env = dict(os.environ if env is None else env)
    backend = {
        "DJANGO_SETTINGS_MODULE": SETTINGS_MODULES[mode],
        # Exactly one role-context opt-in per mode; the others are cleared so a
        # stale value in backend/.env cannot combine with it.
        "CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK": "",
        "CTUG_ROLE_CONTEXT_HTTPS_LAN_DEV_ACK": "",
        "CTUG_ROLE_CONTEXT_LAN_DEV_IP": "",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    }
    frontend = {"CTUG_API_TARGET": BACKEND_TARGET}
    if mode == LAN:
        ip = validate_lan_ip(lan_ip)
        origin = f"http://{ip}:{FRONTEND_PORT}"
        backend.update({
            "CTUG_ROLE_CONTEXT_LAN_DEV_ACK": LAN_ACK,
            "CTUG_ROLE_CONTEXT_LAN_DEV_IPS": ip,
            "WORKSPACE_ALLOWED_HOSTS": f"localhost,127.0.0.1,[::1],{ip}",
            "WORKSPACE_CSRF_TRUSTED_ORIGINS": f"http://localhost:{FRONTEND_PORT},http://127.0.0.1:{FRONTEND_PORT},{origin}",
            "WORKSPACE_PUBLIC_BASE_URL": origin,
        })
        frontend.update({"CTUG_ROLE_CONTEXT_LAN_DEV_ACK": LAN_ACK, "CTUG_ROLE_CONTEXT_LAN_DEV_IPS": ip})
        frontend_args = ["scripts/wf03_optiona_multi_vite.mjs"]
        url = origin
    else:
        backend.update({
            "CTUG_ROLE_CONTEXT_LAN_DEV_ACK": "",
            "CTUG_ROLE_CONTEXT_LAN_DEV_IPS": "",
            "CTUG_REVIEW_LOCAL_ACK": "LOCAL_REVIEW_ONLY",          # existing loopback decision profile
            "CTUG_ROLE_CONTEXT_LOCAL_ACK": "LOCAL_WF0301_D113",    # existing local role-context opt-in
            "WORKSPACE_ALLOWED_HOSTS": "localhost,127.0.0.1,[::1]",
            "WORKSPACE_CSRF_TRUSTED_ORIGINS": f"http://localhost:{FRONTEND_PORT},http://127.0.0.1:{FRONTEND_PORT}",
        })
        frontend_args = ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", str(FRONTEND_PORT),
                         "--strictPort"]
        url = f"http://127.0.0.1:{FRONTEND_PORT}"

    merged = {**env, **backend}
    available, report = set(), []
    for item in FEATURES:  # FEATURES are ordered so requirements come first
        if mode not in item.modes:
            report.append({"key": item.key, "title": item.title, "status": "not-in-mode", "reasons": [item.note] if item.note else []})
            continue
        reasons = _prerequisite_failures(item, merged)
        reasons += [f"requires {req}" for req in item.requires if req not in available]
        if not reasons:
            available.add(item.key)
            backend.update(item.backend_env)
        optional_off = bool(reasons) and "local_email_opt_in" in item.prerequisites and all(
            reason.startswith("not enabled (optional)") for reason in reasons)
        status = "available" if not reasons else "optional" if optional_off else "blocked"
        report.append({"key": item.key, "title": item.title, "status": status, "reasons": reasons})
    for item in FEATURES:
        for flag in item.frontend_flags:
            frontend[flag] = "1" if item.key in available else "0"
    workers = [list(command) for item in FEATURES if item.key in available for command in item.workers]
    return {"mode": mode, "settings_module": SETTINGS_MODULES[mode], "backend_env": backend,
            "frontend_env": frontend, "frontend_args": frontend_args, "url": url, "features": report,
            "workers": workers}


def dotenv_environment(backend_dir):
    """backend/.env values overlaid by the real process environment (process wins, like Django)."""
    from dotenv import dotenv_values
    path = Path(backend_dir) / ".env"
    values = {k: v for k, v in (dotenv_values(path) if path.exists() else {}).items() if v is not None}
    values.update(os.environ)
    return values
