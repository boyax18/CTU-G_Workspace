"""Opt-in, no-schema-change reapplication of REJECTED Student/Instructor accounts.

A signed email link grants only permission to resubmit a full registration.
It does NOT verify school identity, log a user in, or assign any role.
"""

import hashlib
import hmac
import logging
import os
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.db import DEFAULT_DB_ALIAS, DatabaseError, transaction
from html import escape

from apps.access_control.audit import record_access_audit
from apps.access_control.models import AccountPermission, AccountRole, AccessAuditLog, Role

from .models import Account, UserProfile
from .registration_email_templates import _public_url, branded_sender_address

logger = logging.getLogger(__name__)
SALT = "ctug.workspace.registration.reapplication.v1"
LINK_MAX_AGE_SECONDS = 3600
GENERIC_LINK_ACK = "If these details match an eligible rejected registration, a verification link will be sent."


class ReapplicationDenied(Exception):
    """Missing, stale, replayed or ineligible reapplication token."""


class ReapplicationUnavailable(Exception):
    """Trusted reapplication service cannot proceed."""


def _digest(address):
    if not isinstance(address, str):
        return None
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        ("reapplication-email:" + address.strip().casefold()).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _latest_rejection(account_id):
    return (AccessAuditLog.objects.using(DEFAULT_DB_ALIAS)
            .filter(target_account_id=account_id, action="account.registration.reject")
            .order_by("-access_audit_log_id").first())


def _eligible(account):
    return (
        account is not None
        and account.request_status == "Rejected"
        and not account.is_active and not account.is_staff and not account.is_superuser
        and account.requested_role is not None
        and account.requested_role.is_active
        and account.requested_role.role_name in {"Student", "Instructor"}
        and account.rejection_reason in {
            "incomplete_submission", "ineligible_registration",
            "identity_mismatch", "duplicate_request",
        }
        and bool(account.email)
        and not AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(account_id=account.pk).exists()
        and not AccountPermission.objects.using(DEFAULT_DB_ALIAS).filter(account_id=account.pk).exists()
    )


def issue_reapplication_email_if_eligible(*, school_id, email):
    """Return silently for unknown accounts. Never mail an arbitrary new address.

    Restricted by separate view-level throttles and independent email gates.
    Because SMTP timing may be observable, production enablement also requires
    a separately reviewed async delivery plan; this synchronous path is test-only.
    """
    if not (getattr(settings, "WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED", False)
            and getattr(settings, "WORKSPACE_REGISTRATION_REAPPLICATION_EMAIL_ENABLED", False)):
        raise ReapplicationUnavailable("Reapplication email is disabled.")
    backend = getattr(settings, "EMAIL_BACKEND", "")
    if backend == "django.core.mail.backends.smtp.EmailBackend":
        if not (getattr(settings, "WORKSPACE_EMAIL_SMTP_ENABLED", False)
                and os.environ.get("WORKSPACE_REAPPLICATION_SMTP_DELIVERY_APPROVED") == "1"):
            raise ReapplicationUnavailable("Reapplication SMTP is not approved.")
    elif backend != "django.core.mail.backends.locmem.EmailBackend":
        raise ReapplicationUnavailable("Reapplication email backend is not approved.")
    try:
        base_url = _public_url("/register")
        from_address = branded_sender_address()
        account = (Account.objects.using(DEFAULT_DB_ALIAS)
                   .select_related("requested_role")
                   .filter(school_id=school_id, email__iexact=email)
                   .first())
        if not _eligible(account):
            return
        rejection = _latest_rejection(account.pk)
        if rejection is None:
            return
        payload = {
            "aid": account.pk,
            "rid": rejection.pk,
            "eh": _digest(account.email),
        }
        token = signing.dumps(payload, salt=SALT, compress=False)
        # Fragment stays out of HTTP requests and Referer headers.
        link = f"{base_url}#{urlencode({'reapply': token})}"
        subject = "CTU-G Workspace | Verify Registration Reapplication"
        body = (
            "CTU-G Workspace\n\nA request to reapply was received.\n"
            "To complete it, open this verification link within one hour and re-enter all registration fields:\n"
            f"{link}\n\nIf you did not request this, ignore the message."
        )
        html = (
            '<html><body><h1>CTU-G Workspace</h1>'
            '<p>A registration reapplication was requested.</p>'
            '<p>Use the link below within one hour. You must re-enter all registration details.</p>'
            f'<p><a href="{escape(link, quote=True)}">Verify and Reapply</a></p>'
            '<p>If you did not request this, ignore this message.</p></body></html>'
        )
        send_mail(subject, body, from_address, [account.email],
                  fail_silently=False, html_message=html)
    except Exception:
        # Safe non-enumerating response. Never log tokens, addresses or SMTP errors.
        logger.warning("Reapplication verification email could not be completed.")


def complete_reapplication(*, token, data):
    """One-use account transition, with row lock and immutable audit attribution.

    Public token holder is represented by the account as the audit actor: this
    does NOT assert authenticated user identity or Admin authority. The School
    Admin must independently verify actual applicant identity before approval.
    """
    if not getattr(settings, "WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED", False):
        raise ReapplicationUnavailable("Reapplication is disabled.")
    if type(token) is not str or not 1 <= len(token) <= 1024:
        raise ReapplicationDenied()
    try:
        payload = signing.loads(token, salt=SALT, max_age=LINK_MAX_AGE_SECONDS)
    except (signing.BadSignature, signing.SignatureExpired, TypeError, ValueError) as exc:
        raise ReapplicationDenied() from exc
    if (type(payload) is not dict or set(payload) != {"aid", "rid", "eh"}
            or type(payload["aid"]) is not int or not 1 <= payload["aid"] <= 2_147_483_647
            or type(payload["rid"]) is not int or not 1 <= payload["rid"] <= 2_147_483_647
            or type(payload["eh"]) is not str or len(payload["eh"]) != 64):
        raise ReapplicationDenied()
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            account = (Account.objects.using(DEFAULT_DB_ALIAS)
                       .select_for_update()
                       .select_related("requested_role")
                       .filter(pk=payload["aid"]).first())
            if not _eligible(account):
                raise ReapplicationDenied()
            if (data["school_id"] != account.school_id
                    or not hmac.compare_digest(payload["eh"], _digest(account.email))):
                raise ReapplicationDenied()
            rejection = _latest_rejection(account.pk)
            if rejection is None or rejection.pk != payload["rid"]:
                raise ReapplicationDenied()
            snapshot = rejection.new_value if type(rejection.new_value) is dict else {}
            # Legacy rejection receipts predate a reason snapshot. Their current
            # bounded reason is bound to the current state through the row lock.
            if snapshot.get("rejection_code", account.rejection_reason) != account.rejection_reason:
                raise ReapplicationDenied()
            role = (Role.objects.using(DEFAULT_DB_ALIAS)
                    .filter(role_name=data["requested_role"], is_active=True).first())
            if role is None or role.role_name not in {"Student", "Instructor"}:
                raise ReapplicationDenied()
            profile = (UserProfile.objects.using(DEFAULT_DB_ALIAS)
                       .select_for_update().filter(account=account).first())
            if profile is None:
                raise ReapplicationDenied()
            old_state = {"account_id": account.pk, "request_status": "Rejected", "is_active": False}
            account.email = data["email"]
            account.requested_role = role
            account.set_password(data["password"])
            account.request_status = "Pending"
            account.is_active = False
            account.reviewed_by = None
            account.reviewed_at = None
            account.rejection_reason = None
            account.password_reset_token = None
            account.password_reset_token_expires = None
            account.save(using=DEFAULT_DB_ALIAS, update_fields=[
                "email", "requested_role", "password", "request_status", "is_active",
                "reviewed_by", "reviewed_at", "rejection_reason",
                "password_reset_token", "password_reset_token_expires",
            ])
            profile.first_name = data["first_name"]
            profile.middle_name = data["middle_name"] or None
            profile.last_name = data["last_name"]
            profile.suffix = data["suffix"] or None
            profile.save(using=DEFAULT_DB_ALIAS, update_fields=[
                "first_name", "middle_name", "last_name", "suffix",
            ])
            record_access_audit(
                actor=account, target=account, action="account.registration.reapply",
                old_value=old_state,
                new_value={"account_id": account.pk, "request_status": "Pending", "is_active": False},
                reason="account_status_change",
            )
    except DatabaseError as exc:
        raise ReapplicationUnavailable("Reapplication data service is unavailable.") from exc
