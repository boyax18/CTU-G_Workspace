"""Bounded, manually invoked AR-6C5B.5 worker; defaults to read-only preview."""

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.outbox_worker import (
    MAX_BATCH, OutboxWorkerUnavailable, due_job_count, process_due,
)


class Command(BaseCommand):
    help = "Preview pending registration emails or explicitly deliver a bounded batch."

    def add_arguments(self, parser):
        parser.add_argument("--deliver", action="store_true", help="Attempt gated delivery instead of preview")
        parser.add_argument("--limit", type=int, default=25, help=f"Jobs to attempt (1-{MAX_BATCH})")

    def handle(self, *args, **options):
        limit = options["limit"]
        if not 1 <= limit <= MAX_BATCH:
            raise CommandError(f"--limit must be between 1 and {MAX_BATCH}.")
        if not options["deliver"]:
            self.stdout.write(f"READ-ONLY: {due_job_count()} due jobs. No delivery attempted.")
            return
        try:
            result = process_due(limit=limit)
        except OutboxWorkerUnavailable as exc:
            raise CommandError(str(exc)) from None
        # Aggregate counts only; no account, email or exception details.
        self.stdout.write(
            "Delivery batch: " + ", ".join(f"{name}={count}" for name, count in result.items())
        )
