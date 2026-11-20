"""TEST-ONLY helpers for WF-02.04 rejection prerequisites (D-54, revised D-55). Never imported by app code.

A completed rejection needs the durable outbox, the v2 template and an encryption key, and the
applicant must have verified proof for the current address. Tests whose purpose is a rejection use
`rejection_outbox` (a context manager and decorator) and, where the scenario needs it, verified
proof. Tests about missing or invalid proof must NOT add proof.
"""

import base64
import os
import secrets
from contextlib import contextmanager
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

REJECTION_READY = {
    "WORKSPACE_REGISTRATION_OUTBOX_ENABLED": True,
    "WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED": True,
    "WORKSPACE_OUTBOX_ACTIVE_KEY_VERSION": "v1",
}


def fresh_test_key():
    """A fresh random 256-bit key for one test; never a stored or real key."""
    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")


@contextmanager
def rejection_outbox(**extra_settings):
    with override_settings(**REJECTION_READY, **extra_settings), \
            patch.dict(os.environ, {"WORKSPACE_OUTBOX_KEK_V1_B64": fresh_test_key()}):
        yield


def verified_email(account, email):
    """Record OTP proof for the account's current address, as registration does."""
    type(account).objects.filter(pk=account.pk).update(
        email=email, email_verified_at=timezone.now(), email_verified_address=email,
    )
    account.refresh_from_db()
    return account
