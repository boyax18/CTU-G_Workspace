"""AR-6C5C: bounded, synchronous registration decisions.

Disabled at the API boundary; never a replacement for the trusted, locked
single-account review service. No queue, global transaction or implicit role
permission is introduced here.
"""

import logging

from rest_framework import exceptions

from .registration_review import (
    REJECTION_CODES,
    RegistrationReviewDenied,
    RegistrationReviewUnavailable,
    approve_registration,
    reject_registration,
)

logger = logging.getLogger(__name__)

MAX_DIRECT_BULK_ITEMS = 20
MAX_ACCOUNT_ID = 2_147_483_647


def validate_bulk_request(payload):
    """Validate an explicit ID snapshot before performing any writes.

    The caller must separately enforce session/CSRF/authorization, and may not
    pass a filter, select_all flag, actor ID or client-supplied result status.
    """
    if type(payload) is not dict:
        raise exceptions.ValidationError("Expected a JSON object.")
    action = payload.get("action")
    if action not in ("approve", "reject") or type(action) is not str:
        raise exceptions.ValidationError("Unsupported action.")
    allowed = {"action", "account_ids"}
    if action == "reject":
        allowed.add("rejection_code")
    if set(payload) != allowed:
        raise exceptions.ValidationError("Unsupported or missing request fields.")
    ids = payload.get("account_ids")
    if type(ids) is not list or not (1 <= len(ids) <= MAX_DIRECT_BULK_ITEMS):
        raise exceptions.ValidationError("Supply 1 to 20 explicit account IDs.")
    if any(type(pk) is not int or not (1 <= pk <= MAX_ACCOUNT_ID) for pk in ids):
        raise exceptions.ValidationError("Invalid account ID.")
    if len(set(ids)) != len(ids):
        raise exceptions.ValidationError("Repeated account IDs are not permitted.")
    code = payload.get("rejection_code")
    if action == "reject" and (type(code) is not str or code not in REJECTION_CODES):
        raise exceptions.ValidationError("Use an approved rejection code.")
    return action, tuple(ids), code


def process_bulk_registration(*, actor, action, account_ids, rejection_code=None,
                              recheck_authority=None):
    """Process validated explicit IDs individually, never as one long transaction.

    Each single-account service acquires its existing governance/role/account
    locks and performs one durable transaction. The optional callback rechecks
    the current actor's permission immediately before each new decision. A
    stale/ineligible target is safely skipped. Infrastructure failures stop the
    batch, retaining truthful results for earlier committed decisions.
    """
    if action not in ("approve", "reject") or type(action) is not str:
        raise ValueError("Invalid action.")
    if type(account_ids) not in (list, tuple):
        raise ValueError("Explicit IDs are required.")
    if not 1 <= len(account_ids) <= MAX_DIRECT_BULK_ITEMS:
        raise ValueError("Invalid batch size.")
    if any(type(pk) is not int or not 1 <= pk <= MAX_ACCOUNT_ID for pk in account_ids):
        raise ValueError("Invalid account ID.")
    if len(set(account_ids)) != len(account_ids):
        raise ValueError("Duplicate account ID.")
    if action == "reject" and (type(rejection_code) is not str or rejection_code not in REJECTION_CODES):
        raise ValueError("Invalid rejection code.")
    if action == "approve" and rejection_code is not None:
        raise ValueError("Unexpected rejection code.")

    results = []
    interrupted = False
    for pk in account_ids:
        try:
            if recheck_authority is not None:
                recheck_authority()
        except exceptions.APIException:
            # A permission or service change stops subsequent decisions.
            interrupted = True
            break

        try:
            if action == "approve":
                approve_registration(actor=actor, target_id=pk)
                outcome = "Approved"
            else:
                reject_registration(actor=actor, target_id=pk, rejection_code=rejection_code)
                outcome = "Rejected"
        except RegistrationReviewDenied:
            # Stale, forbidden and nonexistent targets intentionally look alike.
            outcome = "Skipped"
        except RegistrationReviewUnavailable:
            results.append({"account_id": pk, "outcome": "Failed"})
            interrupted = True
            break
        except Exception as exc:
            # The individual service rolls back its own transaction; do not
            # expose exception text, identifiers other than submitted IDs, or
            # continue blindly after an infrastructure error.
            logger.error("Bulk review stopped after %s.", type(exc).__name__)
            results.append({"account_id": pk, "outcome": "Failed"})
            interrupted = True
            break
        results.append({"account_id": pk, "outcome": outcome})

    counts = {label: sum(item["outcome"] == label for item in results)
              for label in ("Approved", "Rejected", "Skipped", "Failed")}
    return {
        "requested": len(account_ids),
        "processed": len(results),
        "remaining": len(account_ids) - len(results),
        "interrupted": interrupted,
        "counts": counts,
        "results": results,
    }
