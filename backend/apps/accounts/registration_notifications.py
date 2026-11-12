"""Opt-in post-commit decision email (non-durable legacy delivery path).

The reason is captured by value before the callback is scheduled. For durable
notifications prefer the audited encrypted v2 outbox, not this best-effort path.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import DEFAULT_DB_ALIAS, transaction

from .registration_email_templates import render_decision_email, branded_sender_address

logger = logging.getLogger(__name__)


def _send_registration_decision_email(*, recipient_email, approved, rejection_code=None):
    try:
        subject, plain, html = render_decision_email(
            approved=approved, rejection_code=rejection_code
        )
        sent = send_mail(
            subject=subject, message=plain,
            from_email=branded_sender_address(),
            recipient_list=[recipient_email],
            fail_silently=False, html_message=html,
        )
        if sent != 1:
            logger.warning("Registration-decision email was not accepted by the email backend.")
    except Exception:
        # Transaction has committed. Never leak recipient, SMTP details or reason.
        logger.error("Registration-decision email delivery failed after commit.")


def schedule_registration_decision_email_after_commit(*, recipient_email, approved,
                                                       rejection_code=None):
    """Non-durable callback; never a substitute for the transaction-bound outbox."""
    if not recipient_email or not isinstance(recipient_email, str):
        return False
    if approved and rejection_code is not None:
        raise ValueError("Approval email cannot have a rejection reason.")
    if not approved:
        from .registration_email_templates import REJECTION_LABELS
        if rejection_code not in REJECTION_LABELS:
            raise ValueError("Rejection email requires a supported reason.")
    transaction.on_commit(
        lambda: _send_registration_decision_email(
            recipient_email=recipient_email, approved=approved,
            rejection_code=rejection_code,
        ),
        using=DEFAULT_DB_ALIAS,
    )
    return True
