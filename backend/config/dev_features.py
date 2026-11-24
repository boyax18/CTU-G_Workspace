"""Central development feature registry: the ONE place a finished feature is declared.

Start-CTUG-LAN.ps1 never names a workflow, flag or route. It asks
``manage.py ctug_lan preflight`` which features are ready and passes the result
through. A feature is usable in a development profile only when ALL hold:

1. it is registered below (implemented and integrated, not just a source file);
2. its ``profiles`` approve the selected development profile;
3. every feature in ``requires`` is also available;
4. its ``prerequisites`` pass (backend services, encryption key, catalogue rows);
5. the signed-in account has the exact effective permission (Django view/service);
6. the selected Active Role context permits it (ActiveRoleContextMiddleware).

This module decides 1-4 only. Points 5 and 6 stay with the existing per-request
checks; nothing here grants a permission, bypasses a role, or mounts a route for
a profile that has not approved it. Registered-but-unapproved features are
forced OFF in the profile, so stray environment flags cannot switch them on.

Adding a future module (e.g. WF-07 Finance) = add one ``Feature`` entry with its
settings gate(s), frontend build flag(s), route include(s) and catalogue
permission codes, approve it for ``LAN_SYNTHETIC`` once it is development-ready,
and verify it. No launcher change is ever needed.
"""

from dataclasses import dataclass

LAN_SYNTHETIC = "lan-synthetic"
PROFILES = frozenset({LAN_SYNTHETIC})


@dataclass(frozen=True)
class Feature:
    key: str
    workflow: str
    title: str
    # Development profiles that approve this feature. Empty = registered but gated.
    profiles: frozenset = frozenset()
    # Django settings applied when available; boolean True values are forced False otherwise.
    settings: tuple = ()
    # Vite build flags: "1" when available, "0" otherwise (overrides any frontend .env file).
    frontend_flags: tuple = ()
    # (url prefix, urlconf module) mounted by config.dev_lan_urls when available.
    routes: tuple = ()
    # Exact catalogue v2.2 permission codes this feature's views check.
    permissions: tuple = ()
    requires: tuple = ()
    prerequisites: tuple = ()
    note: str = ""


_LAN = frozenset({LAN_SYNTHETIC})

FEATURES = (
    # ---- WF-02 Account management (development-ready) -------------------------------
    Feature(
        key="wf02.applicant_reviews", workflow="WF-02.01/02.02",
        title="Applicant Reviews (pending list, search, filters, details)",
        profiles=_LAN,
        settings=(("WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED", True),),
        frontend_flags=("VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED",),
        permissions=("accounts.registration_requests.read",),
        prerequisites=("core_services", "catalogue_permissions"),
    ),
    Feature(
        key="wf02.applicant_decisions", workflow="WF-02.03/02.04",
        title="Approve / Reject applicant (audit + durable encrypted notification)",
        profiles=_LAN,
        settings=(
            ("WORKSPACE_REGISTRATION_REVIEW_API_ENABLED", True),
            ("WORKSPACE_REGISTRATION_APPROVAL_ENABLED", True),
            # D-54/D-62: decisions require the durable outbox and the v2 template.
            ("WORKSPACE_REGISTRATION_OUTBOX_ENABLED", True),
            ("WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED", True),
            # Legacy direct-send path stays off; the outbox is the only channel.
            ("WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED", False),
        ),
        frontend_flags=(
            "VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED",
            "VITE_WORKSPACE_REGISTRATION_REJECTION_ENABLED",
        ),
        routes=(("api/v1/admin/registration-requests/", "apps.accounts.registration_review_urls"),),
        permissions=("accounts.registration_requests.approve", "accounts.registration_requests.reject"),
        requires=("wf02.applicant_reviews",),
        prerequisites=("core_services", "catalogue_permissions", "outbox_encryption"),
    ),
    Feature(
        key="wf02.bulk_decisions", workflow="WF-02.03/02.04",
        title="Bulk Approve / Bulk Reject (1-20 explicit applicants, per-applicant results)",
        profiles=_LAN,
        settings=(("WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED", True),),
        frontend_flags=("VITE_WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED",),
        requires=("wf02.applicant_decisions",),
    ),
    Feature(
        key="wf02.account_directory", workflow="WF-02.05 (read)",
        title="Account Directory (accounts, status, minimized history; read-only)",
        profiles=_LAN,
        settings=(("WORKSPACE_ACCOUNT_DIRECTORY_ENABLED", True),),
        frontend_flags=("VITE_WORKSPACE_ACCOUNT_DIRECTORY_ENABLED",),
        permissions=("accounts.school_accounts.read",),
        prerequisites=("core_services", "catalogue_permissions"),
    ),
    # ---- Registered but NOT approved for any development profile --------------------
    Feature(
        key="wf02.account_status_changes", workflow="WF-02.05 (write)",
        title="Suspend / Activate accounts",
        settings=(("WORKSPACE_ACCOUNT_STATUS_ENABLED", True),),
        frontend_flags=("VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED",),
        note="Protected status mutations stay in the loopback review profiles.",
    ),
    Feature(
        key="wf03.role_assignment", workflow="WF-03.01",
        title="Role assignment / ordinary appointments",
        settings=(
            ("WORKSPACE_ROLE_ASSIGNMENT_ENABLED", True),
            ("WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_ENABLED", True),
            ("WORKSPACE_ORDINARY_APPOINTMENT_REGISTRY_ENABLED", True),
        ),
        frontend_flags=(
            "VITE_WORKSPACE_ROLE_ASSIGNMENT_ENABLED",
            "VITE_WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_ENABLED",
            "VITE_WORKSPACE_APPOINTMENT_MANAGEMENT_ENABLED",
        ),
        note="Protected governance; awaiting D-101/D-102 authority and deferred tests.",
    ),
    Feature(
        key="wf03.access_governance", workflow="WF-03.02-03.06",
        title="Role permissions, grants, restrictions, effective access, audit history",
        settings=(
            ("WORKSPACE_WF0302_ROLE_PERMISSIONS_ENABLED", True),
            ("WORKSPACE_WF0302_ROLE_PERMISSION_MUTATIONS_ENABLED", True),
            ("WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED", True),
            ("WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED", True),
            ("WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED", True),
            ("WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED", True),
            ("WORKSPACE_WF0305_EFFECTIVE_ACCESS_INSPECT_ENABLED", True),
            ("WORKSPACE_WF0306_AUDIT_HISTORY_ENABLED", True),
        ),
        frontend_flags=(
            "VITE_WORKSPACE_WF0302_ROLE_PERMISSIONS_ENABLED",
            "VITE_WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED",
            "VITE_WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED",
            "VITE_WORKSPACE_WF0305_EFFECTIVE_ACCESS_INSPECT_ENABLED",
            "VITE_WORKSPACE_WF0306_AUDIT_HISTORY_ENABLED",
        ),
        note="Protected governance; executor boundary and owner approvals pending.",
    ),
)

# Prerequisite names understood by `manage.py ctug_lan preflight` (checked against the DB).
PREREQUISITES = frozenset({"core_services", "catalogue_permissions", "outbox_encryption"})

_BY_KEY = {feature.key: feature for feature in FEATURES}


def feature(key):
    return _BY_KEY[key]


def approved_keys(profile):
    """Registered features approved for ``profile`` whose dependencies are approved too."""
    if profile not in PROFILES:
        raise ValueError(f"Unknown development profile: {profile!r}")
    approved = {f.key for f in FEATURES if profile in f.profiles}
    changed = True
    while changed:  # dependency closure: drop anything whose requirement is unapproved
        changed = False
        for key in sorted(approved):
            if any(req not in approved for req in _BY_KEY[key].requires):
                approved.discard(key)
                changed = True
    return frozenset(approved)


def profile_settings(profile):
    """Settings overlay: unapproved feature gates forced off, approved gates opened."""
    approved = approved_keys(profile)
    values = {}
    for item in FEATURES:
        if item.key not in approved:
            values.update({name: False for name, value in item.settings if value is True})
    for item in FEATURES:
        if item.key in approved:
            values.update(dict(item.settings))
    return values


def profile_routes(profile):
    approved = approved_keys(profile)
    return tuple(route for item in FEATURES if item.key in approved for route in item.routes)


def profile_permission_codes(profile):
    approved = approved_keys(profile)
    return tuple(sorted({code for item in FEATURES if item.key in approved for code in item.permissions}))


def available_keys(profile, failed_prerequisites):
    """Approved features whose prerequisites passed, after dependency propagation.

    ``failed_prerequisites`` maps a feature key to a list of human-readable reasons.
    """
    available = {key for key in approved_keys(profile) if not failed_prerequisites.get(key)}
    changed = True
    while changed:
        changed = False
        for key in sorted(available):
            if any(req not in available for req in _BY_KEY[key].requires):
                available.discard(key)
                changed = True
    return frozenset(available)


def frontend_environment(available):
    """Every registered build flag, explicitly "1" or "0", so frontend .env files cannot leak."""
    flags = {}
    for item in FEATURES:
        for name in item.frontend_flags:
            flags[name] = "0"
    for item in FEATURES:
        if item.key in available:
            for name in item.frontend_flags:
                flags[name] = "1"
    return flags
