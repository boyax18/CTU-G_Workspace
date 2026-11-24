"""Bounded, manually invoked AR-6C5B.5 worker; defaults to read-only preview.

    process_registration_outbox                     read-only count of due notifications
    process_registration_outbox --deliver           deliver one bounded batch (all due rows)
    process_registration_outbox --deliver --watch 15
        keep delivering every 15 s, but ONLY notifications queued after the watcher started;
        older queued rows are left for an explicit one-off --deliver (used by -Local mode).

All existing gates apply (WORKSPACE_OUTBOX_WORKER_ENABLED, outbox writer gate, SMTP delivery
approval, approved link/sender). Output is aggregate counts only: no address, body or error text.
"""

import time

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, close_old_connections

from apps.accounts.outbox_worker import (
    MAX_BATCH, OutboxWorkerUnavailable, due_job_count, newest_outbox_id, process_due,
)


class Command(BaseCommand):
    help = "Preview pending registration emails or explicitly deliver a bounded batch."

    def add_arguments(self, parser):
        parser.add_argument("--deliver", action="store_true", help="Attempt gated delivery instead of preview")
        parser.add_argument("--limit", type=int, default=25, help=f"Jobs to attempt (1-{MAX_BATCH})")
        parser.add_argument("--watch", type=int, default=0, metavar="SECONDS",
                            help="With --deliver: keep delivering NEW notifications every SECONDS (5-3600)")

    def handle(self, *args, **options):
        limit = options["limit"]
        if not 1 <= limit <= MAX_BATCH:
            raise CommandError(f"--limit must be between 1 and {MAX_BATCH}.")
        if not options["deliver"]:
            self.stdout.write(f"READ-ONLY: {due_job_count()} due jobs. No delivery attempted.")
            return
        if options["watch"]:
            return self._watch(limit, options["watch"])
        try:
            result = process_due(limit=limit)
        except OutboxWorkerUnavailable as exc:
            raise CommandError(str(exc)) from None
        # Aggregate counts only; no account, email or exception details.
        self.stdout.write(
            "Delivery batch: " + ", ".join(f"{name}={count}" for name, count in result.items())
        )

    def _watch(self, limit, seconds):
        if not 5 <= seconds <= 3600:
            raise CommandError("--watch must be between 5 and 3600 seconds.")
        try:
            watermark = newest_outbox_id()
            earlier = due_job_count()
            process_due(limit=1, after_id=watermark)  # fail closed now if any gate is off
        except OutboxWorkerUnavailable as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(f"Watching for new notifications every {seconds}s. "
                          f"{earlier} earlier queued notification(s) are left for a manual --deliver.", ending="\n")
        self.stdout.flush()
        while True:
            try:
                result = process_due(limit=limit, after_id=watermark)
                if any(result.values()):
                    self.stdout.write("Delivery batch: " + ", ".join(f"{k}={v}" for k, v in result.items()))
                    self.stdout.flush()
            except OutboxWorkerUnavailable as exc:
                raise CommandError(str(exc)) from None
            except DatabaseError:
                self.stdout.write("Delivery paused: database unavailable; retrying on the next cycle.")
                close_old_connections()
            time.sleep(seconds)
