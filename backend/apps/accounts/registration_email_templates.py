"""Decision email presentation: privacy-limited, versioned, no account lookup.

V2 messages use only immutable decision metadata supplied by the caller. Never
render current Account.rejection_reason for a queued historical notification.
"""

from email.utils import parseaddr
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


REJECTION_LABELS = {
    "incomplete_submission": "Incomplete registration information",
    "ineligible_registration": "Registration eligibility could not be confirmed",
    "identity_mismatch": "Registration identity could not be verified",
    "duplicate_request": "Duplicate registration request",
}


def _public_url(path):
    base = getattr(settings, "WORKSPACE_PUBLIC_BASE_URL", "").rstrip("/")
    parsed = urlsplit(base)
    approved = set(getattr(settings, "WORKSPACE_EMAIL_PUBLIC_HOSTS", ()))
    backend = getattr(settings, "EMAIL_BACKEND", "")
    is_test_mail = backend == "django.core.mail.backends.locmem.EmailBackend"
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    # Owner-directed local development delivery (config.review_local_settings opt-in): a loopback
    # http link is acceptable only in a DEBUG, local-profile process that explicitly allows it.
    dev_links = (getattr(settings, "WORKSPACE_EMAIL_DEV_LINKS_ALLOWED", False) is True
                 and getattr(settings, "DEBUG", False) is True
                 and getattr(settings, "WORKSPACE_DEPLOYMENT_PROFILE", "local") == "local")
    safe = (
        parsed.scheme in {"https", "http"} and parsed.netloc and
        not parsed.username and not parsed.password and
        not parsed.query and not parsed.fragment and not parsed.path.rstrip("/") and
        (parsed.scheme == "https" and parsed.hostname in approved or
         (is_test_mail or dev_links) and local and parsed.scheme == "http")
    )
    if not safe:
        raise ValueError("An approved HTTPS public application URL is required for email.")
    return base + path


def branded_sender_address():
    raw = getattr(settings, "DEFAULT_FROM_EMAIL", "")
    if type(raw) is not str or any(char in raw for char in "\r\n"):
        raise ValueError("Invalid email sender configuration.")
    _, email = parseaddr(raw)
    try:
        validate_email(email)
    except ValidationError as exc:
        raise ValueError("Invalid sender email address.") from exc
    return raw


def render_decision_email(*, approved, rejection_code=None):
    """Return (subject, plain text, HTML) for one decision. Validation and links are decided here;
    the branded presentation lives in email_design (the same design for individual and bulk)."""
    if type(approved) is not bool:
        raise ValueError("Invalid decision type.")
    if approved:
        if rejection_code is not None:
            raise ValueError("Approval must not have a rejection code.")
        url, reason = _public_url("/"), None
    else:
        if rejection_code not in REJECTION_LABELS:
            raise ValueError("A supported immutable rejection reason is required.")
        url, reason = _public_url("/register"), REJECTION_LABELS[rejection_code]
    from .email_design import registration_decision
    return registration_decision(approved=approved, url=url, reason=reason)
