"""Decision email presentation: privacy-limited, versioned, no account lookup.

V2 messages use only immutable decision metadata supplied by the caller. Never
render current Account.rejection_reason for a queued historical notification.
"""

from email.utils import parseaddr
from html import escape
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
    safe = (
        parsed.scheme in {"https", "http"} and parsed.netloc and
        not parsed.username and not parsed.password and
        not parsed.query and not parsed.fragment and not parsed.path.rstrip("/") and
        (parsed.scheme == "https" and parsed.hostname in approved or
         is_test_mail and local and parsed.scheme == "http")
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
    if type(approved) is not bool:
        raise ValueError("Invalid decision type.")
    if approved:
        if rejection_code is not None:
            raise ValueError("Approval must not have a rejection code.")
        status = "APPROVED"
        description = "Your account registration has been approved by the administrator."
        action = "Log In to CTU-G Workspace"
        url = _public_url("/")
        subject = "CTU-G Workspace | Registration Approved"
        reason = None
    else:
        if rejection_code not in REJECTION_LABELS:
            raise ValueError("A supported immutable rejection reason is required.")
        status = "REJECTED"
        description = "Your account registration has been rejected by the administrator."
        action = "Reapply for Registration"
        url = _public_url("/register")
        subject = "CTU-G Workspace | Registration Rejected"
        reason = REJECTION_LABELS[rejection_code]

    reason_text = f"\nReason: {reason}\n" if reason else ""
    further = (
        "You can now sign in using your registered School ID and password."
        if approved else
        "You may request a verification link on the registration page, then re-enter all registration details."
    )
    body = (
        "CTU-G Workspace\nCebu Technological University - Ginatilan Campus\n\n"
        f"Registration status: {status}\n\n{description}\n"
        f"{reason_text}\n{further}\n\n{action}: {url}\n\n"
        "This is an automated notification. If you need help, contact the campus administrator."
    )
    reason_html = (
        f'<p><strong>Reason:</strong> {escape(reason)}</p>' if reason else ""
    )
    html = (
        '<!doctype html><html><body style="margin:0;padding:24px;font-family:Arial,sans-serif;color:#17312a">'
        '<main style="max-width:580px;margin:auto;border:1px solid #d6e2dc;border-radius:12px;padding:24px">'
        '<h1 style="color:#165e42;font-size:22px;margin:0">CTU-G Workspace</h1>'
        '<p style="color:#536a5f;font-size:13px">Cebu Technological University - Ginatilan Campus</p>'
        f'<h2 style="font-size:18px">Registration Status: {status}</h2>'
        f'<p>{escape(description)}</p>{reason_html}<p>{escape(further)}</p>'
        f'<p><a href="{escape(url, quote=True)}" style="display:inline-block;background:#166b4a;color:#fff;'
        f'padding:12px 18px;border-radius:6px;text-decoration:none">{escape(action)}</a></p>'
        '<p style="font-size:12px;color:#536a5f">Automated notification. Contact the campus administrator if you need help.</p>'
        '</main></body></html>'
    )
    return subject, body, html
