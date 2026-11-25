"""Read-only email delivery report: status counts and recent rows. No addresses, codes or bodies.

    manage.py email_delivery_report [--recent 15]
    manage.py email_delivery_report --trace <correlation id>   one message, request to final state

"Accepted" means the SMTP server accepted the message. Recipient receipt is reported as CONFIRMED
only when the durable trace shows the code from that exact message was entered correctly
(``recipient_confirmed``); otherwise it is "unconfirmed". Notices without a code stay unconfirmed.
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from apps.accounts.outbox_models import RegistrationNotificationOutbox
from apps.accounts.security_mail_models import SecurityMailOutbox

_CORR = re.compile(r"\A(?:[0-9a-f]{8,32}|dec-[0-9]{1,12})\Z")
_LINE_CORR = re.compile(r"\bcorr=(\S+)")
_STATE = {
    "Pending": "queued", "Leased": "processing", "Retry": "retry scheduled", "Dead": "permanently failed",
    "Expired": "expired (never sent)", "Superseded": "superseded (never sent)",
}


def _trace_lines():
    path = getattr(settings, "WORKSPACE_EMAIL_TRACE_LOG", None)
    if not path or not Path(path).is_file():
        return None
    with open(path, encoding="utf-8", errors="replace") as handle:
        return [line.rstrip("\n") for line in handle if " ctug.email " in line]


def _confirmed(lines):
    return {m.group(1) for line in lines or () if "event=recipient_confirmed" in line
            for m in [_LINE_CORR.search(line)] if m}


def _label(row, confirmed):
    if row.status != "Accepted":
        return _STATE.get(row.status, row.status)
    if row.kind == SecurityMailOutbox.KIND_PASSWORD_CHANGED:
        return "SMTP accepted; receipt unconfirmed (notice has no code)"
    if row.correlation_id in confirmed:
        return "SMTP accepted; receipt CONFIRMED (code redeemed)"
    return "SMTP accepted; receipt unconfirmed"


class Command(BaseCommand):
    help = "Show delivery status of security mail and decision notifications (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("--recent", type=int, default=15)
        parser.add_argument("--trace", metavar="CORR", help="Show one message's full trace by correlation ID")

    def handle(self, *args, **options):
        lines = _trace_lines()
        if options.get("trace"):
            return self._trace(options["trace"].strip().lower(), lines)
        out = self.stdout.write
        confirmed = _confirmed(lines)
        out("Security mail (password reset, password changed, email verification):")
        for row in SecurityMailOutbox.objects.values("kind", "status").annotate(n=Count("pk")).order_by("kind", "status"):
            out(f"  {row['kind']:<24} {row['status']:<11} {row['n']}")
        out(f"Recent security mail (newest {options['recent']}):")
        for r in SecurityMailOutbox.objects.order_by("-outbox_id")[:max(1, min(options["recent"], 200))]:
            out(f"  #{r.outbox_id} {r.created_at:%Y-%m-%d %H:%M:%S}Z {r.kind} {r.status} attempts={r.attempt_count}"
                f" corr={r.correlation_id} failure={r.last_failure_code or '-'} msgid={r.message_id or '-'}"
                f" -> {_label(r, confirmed)}")
        out("Decision notifications (approval/rejection outbox):")
        for row in RegistrationNotificationOutbox.objects.values("template_code", "delivery_status").annotate(
                n=Count("pk")).order_by("template_code", "delivery_status"):
            out(f"  {row['template_code']:<24} {row['delivery_status']:<11} {row['n']}")
        if lines is None:
            out("Durable trace log: not configured for this settings profile (receipt labels use the database only).")
        out("Accepted/Delivered = handed to the SMTP server. Receipt is CONFIRMED only when its code was redeemed.")

    def _trace(self, corr, lines):
        if not _CORR.match(corr):
            raise CommandError("A correlation ID is 8-32 lowercase hex characters (or dec-<outbox id>).")
        out = self.stdout.write
        rows = list(SecurityMailOutbox.objects.filter(correlation_id=corr).order_by("outbox_id"))
        if corr.startswith("dec-"):
            for r in RegistrationNotificationOutbox.objects.filter(pk=int(corr[4:])):
                out(f"Outbox row (decision) #{r.pk}: {r.template_code} {r.delivery_status} attempts={r.attempt_count}"
                    f" failure={r.last_failure_code or '-'}")
        confirmed = _confirmed(lines)
        for r in rows:
            out(f"Outbox row (security) #{r.outbox_id}: account #{r.account_id} {r.kind} {r.status}"
                f" attempts={r.attempt_count} failure={r.last_failure_code or '-'} msgid={r.message_id or '-'}"
                f" created={r.created_at:%Y-%m-%d %H:%M:%S}Z accepted={r.accepted_at or '-'}")
            out(f"  Final known state: {_label(r, confirmed)}")
        if lines is None:
            out("Durable trace log: not configured for this settings profile.")
        else:
            events = [line for line in lines if f"corr={corr} " in line + " "]
            out(f"Trace events ({len(events)}):")
            for line in events:
                out("  " + line)
        if not rows and not (lines and any(f"corr={corr} " in line + " " for line in lines)):
            out("No outbox row or trace event has this correlation ID.")
