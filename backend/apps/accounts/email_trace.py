"""Internal email-delivery diagnostics (24 Nov 2026). Server log only; never sent to callers.

One line per delivery event on the ``ctug.email`` logger, e.g.::

    ctug.email event=smtp_accepted flow=reset_code corr=3f2a… outbox=17 attempt=1 msgid=<…@gmail.com> to=ga***@gmail.com

* Allow-listed fields only. No OTP, body, subject text, password, App Password or key ever.
* Recipients are masked (first two characters + domain). Unauthenticated HTTP responses are
  unchanged: eligibility and account existence stay invisible to callers.
* ``smtp_accepted`` means the SMTP server took the message. It is never "delivered":
  inbox placement can only be confirmed by the recipient (status ``recipient_unconfirmed``).
"""

import logging
import secrets

logger = logging.getLogger("ctug.email")

EVENTS = frozenset({
    "request_accepted", "account_ineligible", "otp_created", "email_queued", "smtp_attempt",
    "smtp_accepted", "temporary_failure", "permanent_failure", "retry_scheduled", "expired",
    "superseded", "recipient_unconfirmed", "worker_unavailable",
})
_FIELDS = ("flow", "outbox", "attempt", "msgid", "to", "code", "next_in", "status")


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
