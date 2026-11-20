"""WF-01.06 P-01 (owner-approved 17 Nov 2026): server-side session expiry.

D-18: a signed-in session ends after 30 minutes without activity or 8 hours
after sign-in, whichever comes first (WORKSPACE_SESSION_IDLE_SECONDS and
WORKSPACE_SESSION_ABSOLUTE_SECONDS, validated in config/security_settings.py).

- Every successful django.contrib.auth login() (the Workspace LoginView and
  Django admin alike) stamps the session with its sign-in time and last activity.
  login() has already cycled the session key and rotated the CSRF token.
- Activity is recorded at most once per ACTIVITY_WRITE_SECONDS, so an active
  user causes at most one session write per minute. The idle check therefore
  counts from the last recorded activity, which can end a session up to a minute
  early but never late.
- Activity never moves the sign-in time, so it cannot extend the absolute
  lifetime. The session's database expiry and cookie max-age are kept at the
  absolute deadline.
- An authenticated session without valid timestamps (created before this change,
  or tampered) is flushed: the user simply signs in again (fail-safe transition).
- An expired session is flushed (row deleted). A concurrent request that loaded
  it earlier cannot save it back, because Django refuses to update a deleted
  session row (SessionInterrupted), so expiry cannot be revived.
- If the session store is unavailable, the request fails closed with 503.

No timers run in the browser; enforcement is entirely server-side.
"""

import logging
import time

from django.conf import settings
from django.contrib.auth import SESSION_KEY, user_logged_in
from django.db import DatabaseError
from django.dispatch import receiver
from django.http import HttpResponse, JsonResponse
from django.utils.cache import patch_cache_control

logger = logging.getLogger(__name__)

AUTH_AT = "_workspace_auth_at"
SEEN_AT = "_workspace_seen_at"
ACTIVITY_WRITE_SECONDS = 60
CLOCK_SKEW_SECONDS = 5


def _now():
    return int(time.time())


def _limits():
    return settings.WORKSPACE_SESSION_IDLE_SECONDS, settings.WORKSPACE_SESSION_ABSOLUTE_SECONDS


@receiver(user_logged_in, dispatch_uid="workspace_session_clock")
def start_session_clock(sender, request, user, **kwargs):
    session = getattr(request, "session", None)
    if session is None:
        return
    now = _now()
    session[AUTH_AT] = now
    session[SEEN_AT] = now
    session.set_expiry(_limits()[1])


def session_state(session, now=None):
    """Return 'none', 'valid', 'touch' (valid and due an activity write) or 'expired'."""
    if SESSION_KEY not in session:
        return "none"
    now = _now() if now is None else now
    idle, absolute = _limits()
    auth_at, seen_at = session.get(AUTH_AT), session.get(SEEN_AT)
    if (type(auth_at) is not int or type(seen_at) is not int or seen_at < auth_at
            or seen_at > now + CLOCK_SKEW_SECONDS):
        return "expired"  # legacy or tampered session: fail safe
    if now - auth_at >= absolute or now - seen_at >= idle:
        return "expired"
    if now - seen_at >= ACTIVITY_WRITE_SECONDS:
        return "touch"
    return "valid"


class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session = getattr(request, "session", None)
        if session is not None:
            try:
                now = _now()
                state = session_state(session, now)
                if state == "expired":
                    session.flush()
                    request.workspace_session_expired = True
                elif state == "touch":
                    session[SEEN_AT] = now
                    remaining = session[AUTH_AT] + _limits()[1] - now
                    session.set_expiry(max(1, remaining))
            except DatabaseError as exc:
                # Fail closed: never treat an unreadable session as valid or anonymous.
                logger.warning("Workspace session check unavailable (%s).", type(exc).__name__)
                return self._unavailable(request)
        return self.get_response(request)

    @staticmethod
    def _unavailable(request):
        if request.path.startswith("/api/"):
            response = JsonResponse(
                {"error": {"code": "auth_unavailable", "message": "Authentication is temporarily unavailable."}},
                status=503,
            )
        else:
            response = HttpResponse("Service temporarily unavailable.", status=503, content_type="text/plain")
        patch_cache_control(response, no_store=True)
        return response
