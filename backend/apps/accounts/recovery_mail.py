"""WF-01.05 D-20 (owner-approved 16 Nov 2026, development only): a bounded,
best-effort background sender for password-recovery mail.

Sending outside the request keeps a matching and a non-matching recovery
request equally fast, so response timing does not reveal which School ID and
email pairs are registered. Messages exist only in this process's memory: a
message still queued when the process stops is lost (the user can request
again), nothing is written to the database, and a reset link is never stored.

Production use stays blocked (D-24) until reliable delivery, failure handling
and security are verified separately.
"""

import logging
import queue
import threading

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

QUEUE_SIZE = 50
_queue = queue.Queue(maxsize=QUEUE_SIZE)
_start_lock = threading.Lock()
_worker = None


def _run():
    while True:
        kind, subject, body, recipient = _queue.get()
        try:
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)
        except Exception as exc:
            # Never log the recipient, the body or any link.
            logger.warning("Workspace recovery mail (%s) could not be sent (%s).", kind, type(exc).__name__)
        finally:
            _queue.task_done()


def _ensure_worker():
    global _worker
    with _start_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_run, name="ctug-recovery-mail", daemon=True)
            _worker.start()


def enqueue(kind, subject, body, recipient):
    """Queue one message. Returns False (and logs only `kind`) when the queue is full."""
    _ensure_worker()
    try:
        _queue.put_nowait((kind, subject, body, recipient))
    except queue.Full:
        logger.warning("Workspace recovery mail (%s) was dropped: queue full.", kind)
        return False
    return True


def wait_until_idle():
    """Block until every queued message has been attempted (used by tests)."""
    _queue.join()
