"""Remove only expired temporary Student registrations; never permanent accounts."""
import time
from django.core.management.base import BaseCommand
from apps.accounts.registration_staging import purge_expired_stages


class Command(BaseCommand):
    help = "Purge expired encrypted registration stages (schedule every minute, or use --watch)."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")

    def handle(self, *args, **options):
        try:
            while True:
                count = purge_expired_stages()
                self.stdout.write(f"Purged {count} expired Student registration stages.")
                if not options["watch"]:
                    return
                time.sleep(60)
        except KeyboardInterrupt:
            return
