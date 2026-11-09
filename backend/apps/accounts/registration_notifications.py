"""Optional, best-effort email for reviewed CTU-G Workspace registrations.

NO persistence or delivery guarantees: the on_commit callback is held in memory.
Do not use this as a substitute for an approved transactional outbox when
rejection deletion or operationally guaranteed email is required.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import DEFAULT_DB_ALIAS, transaction


logger = logging.getLogger(__name__)


def _send_registration_decision_email(*, recipient_email, approved):
    # Never place raw student data, rejection details, or credentials in logs.
    if approved:
        subject = "CTU-G Workspace: Registration approved"
        body = (
            "Your CTU-G Workspace registration has been approved. "
            "You may now sign in using your School ID and password.\n\n"
            "If you did not request an account, contact your campus office."
        )
    else:
        subject = "CTU-G Workspace: Registration not approved"
        body = (
            "Your CTU-G Workspace registration was not approved. "
            "Please contact your campus office if you need clarification.\n\n"
            "This message does not contain your password or personal details."
        )

    try:
        sent = send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        if sent != 1:
            logger.warning("Registration-decision email was not accepted by the email backend.")
    except Exception:
        # The database transaction has ALREADY committed at this point.
        # Avoid falsely turning a committed decision into an HTTP 500.
        # No exception text/traceback is logged to avoid secret leakage.
        logger.error("Registration-decision email delivery failed after commit.")


def schedule_registration_decision_email_after_commit(*, recipient_email, approved):
    """Register an on_commit callback; return False when no address exists.

    The caller must already be in an atomic DB transaction and must have
    independently authorized and audited the registration decision.
    """
    if not recipient_email or not isinstance(recipient_email, str):
        return False

    transaction.on_commit(
        lambda: _send_registration_decision_email(
            recipient_email=recipient_email,
            approved=approved,
        ),
        using=DEFAULT_DB_ALIAS,
    )
    return True
