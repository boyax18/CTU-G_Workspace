"""Read-only email delivery report: status counts and recent rows. No addresses, codes or bodies.

    manage.py email_delivery_report [--recent 15]

"Accepted" means the SMTP server accepted the message; inbox arrival is never confirmed here.
"""

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.accounts.outbox_models import RegistrationNotificationOutbox
from apps.accounts.security_mail_models import SecurityMailOutbox


class Command(BaseCommand):
    help = "Show delivery status of security mail and decision notifications (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("--recent", type=int, default=15)

    def handle(self, *args, **options):
        out = self.stdout.write
        out("Security mail (password reset, password changed, email verification):")
        for row in SecurityMailOutbox.objects.values("kind", "status").annotate(n=Count("pk")).order_by("kind", "status"):
            out(f"  {row['kind']:<24} {row['status']:<11} {row['n']}")
        out(f"Recent security mail (newest {options['recent']}):")
        for r in SecurityMailOutbox.objects.order_by("-outbox_id")[:max(1, min(options["recent"], 200))]:
            out(f"  #{r.outbox_id} {r.created_at:%Y-%m-%d %H:%M:%S}Z {r.kind} {r.status} attempts={r.attempt_count}"
                f" corr={r.correlation_id} failure={r.last_failure_code or '-'} msgid={r.message_id or '-'}")
        out("Decision notifications (approval/rejection outbox):")
        for row in RegistrationNotificationOutbox.objects.values("template_code", "delivery_status").annotate(
                n=Count("pk")).order_by("template_code", "delivery_status"):
            out(f"  {row['template_code']:<24} {row['delivery_status']:<11} {row['n']}")
        out("Accepted/Delivered = handed to the SMTP server. Recipient inbox arrival: unconfirmed.")
