"""WF-03.01 SR-1 Stage A (owner-authorized 19 Nov 2026): advance an account's persistent session-revocation counter.

Account.session_revocation_version is bound into every session hash (Account._get_session_auth_hash), so one
increment ends every session the account signed in before it, on every device. It is stored on the account row
and is never derived from audit receipts: deleting, changing or forging a receipt cannot lower it (SR-1).

Contract for callers (each approved session-ending event, exactly once per operation):
- Call inside the SAME transaction as the account or role change and its audit receipt. This function never
  opens or commits a transaction of its own, so the change, the receipt and the increment commit or roll back
  together.
- Lock the target's accounts row first, in the caller's existing order (services first, then accounts by id;
  R-1/K-4/K-6). The UPDATE then reuses that exclusive row lock and adds no new lock to the order.
- The increment is one SQL expression (F() + 1), so concurrent advances can never lose an update.

Application-level only: a database administrator, raw SQL or a restored backup can still change the counter.
Only the separately approved non-decrease trigger refuses a lower value at the database level.
"""

from django.db import DEFAULT_DB_ALIAS, transaction
from django.db.models import F

from .models import SESSION_REVOCATION_FIELD, Account


class SessionRevocationUnavailable(RuntimeError):
    """The counter could not be advanced; the enclosing operation must roll back (fail closed)."""


def advance(account_id, *, using=DEFAULT_DB_ALIAS):
    """Increment the account's session-revocation counter by exactly one inside the caller's transaction."""
    if type(account_id) is not int or not 1 <= account_id <= 2_147_483_647:
        raise SessionRevocationUnavailable("An existing account is required.")
    if not transaction.get_connection(using).in_atomic_block:
        raise SessionRevocationUnavailable("Session revocation must run inside the protected operation's transaction.")
    # The base manager bypasses AccountQuerySet's refusal, which exists to stop every OTHER ORM write.
    updated = (Account._base_manager.using(using).filter(pk=account_id)
               .update(**{SESSION_REVOCATION_FIELD: F(SESSION_REVOCATION_FIELD) + 1}))
    if updated != 1:
        raise SessionRevocationUnavailable("The session-revocation counter could not be advanced.")
