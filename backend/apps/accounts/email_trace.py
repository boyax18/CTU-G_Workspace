"""Internal email-delivery diagnostics (24 Nov 2026). Server log only; never sent to callers.

One line per delivery event on the ``ctug.email`` logger, e.g.::

    ctug.email event=smtp_accepted flow=reset_code corr=3f2a… outbox=17 attempt=1 msgid=<…@gmail.com> to=ga***@gmail.com

* Allow-listed fields only. No OTP, body, subject text, password, App Password or key ever.
* Recipients are masked (first two characters + domain). Unauthenticated HTTP responses are
  unchanged: eligibility and account existence stay invisible to callers.
* ``smtp_accepted`` means the SMTP server took the message. It is never "delivered":
  inbox placement can only be confirmed by the recipient (status ``recipient_unconfirmed``).

Delivery states, in order (25 Nov 2026)::

    account_ineligible    not eligible (public flows: server log only, response unchanged)
    otp_created           challenge created (only the keyed digest is stored)
    email_queued          durable outbox row written (security mail)
    smtp_attempt          processing (row leased, SMTP conversation started)
    smtp_accepted         the provider accepted THIS message: reply=<provider queue reply>, msgid=<Message-ID>
    retry_scheduled       temporary failure, bounded exponential backoff
    permanent_failure     dead-lettered (recipient refused, 5xx, attempts exhausted)
    expired / superseded  never sent: code expired, or replaced by a newer code / changed address
    recipient_unconfirmed accepted, receipt not yet proven
    recipient_confirmed   receipt PROVEN: the code from this exact message was entered correctly

``recipient_confirmed`` is the only receipt claim the system makes, and only for OTP messages.
Notices (password changed, decisions) carry no code, so their receipt stays unconfirmed.
"""

import logging
import secrets

logger = logging.getLogger("ctug.email")

EVENTS = frozenset({
    "request_accepted", "account_ineligible", "otp_created", "email_queued", "smtp_attempt",
    "smtp_accepted", "temporary_failure", "permanent_failure", "retry_scheduled", "expired",
    "superseded", "recipient_unconfirmed", "recipient_confirmed", "worker_unavailable",
})
_FIELDS = ("flow", "outbox", "attempt", "msgid", "reply", "to", "code", "next_in", "status")


def new_correlation_id():
    return secrets.token_hex(8)


def mask(address):
    if type(address) is not str or "@" not in address:
        return "-"
    local, _, domain = address.rpartition("@")
    return f"{local[:2]}***@{domain}"


def trace(event, correlation_id, **fields):
    if event not in EVENTS:
        raise ValueError("Unknown email trace event.")
    parts = [f"event={event}", f"corr={correlation_id or '-'}"]
    for name in _FIELDS:
        if fields.get(name) is not None:
            value = str(fields[name]).replace(" ", "_")[:200]
            parts.append(f"{name}={value}")
    logger.info(" ".join(parts))
