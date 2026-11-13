"""G1D-P3C6A integration seam: fail-closed *when explicitly enabled*.

This is not a database writer fence. It prevents the mapped Django write
services from running while an independently validated executor is absent.
Direct SQL, administrative DB accounts, other application code and database
users can still bypass Python. Do not treat this module as a release gate.

Existing operational code remains unchanged with the flag unset/False for
compatibility with already-approved development workflows. Enabling the
flag deliberately denies all mapped writes until a separate, reviewed
executor implementation replaces this stopgap.
"""

from django.conf import settings


class WriterBoundaryUnavailable(RuntimeError):
    """The requested Django write has no verified protected DB executor."""


GATE_SETTING = "WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER"
RELEASE_STATUS = "BLOCKED"
COVERED_OPERATIONS = frozenset({
    "registration.approve",
    "registration.reject",
    "role_permission.change",
    "account_permission.change",
    "bootstrap.initial_admin",
})


def require_verified_writer(operation):
    """Reject mapped write intents when P3C6 enforcement is enabled.

    This function runs BEFORE opening the operation's transaction. No caller
    may supply a success token, handler, connection alias, or bypass flag.
    It cannot grant permissions or authorize writes by itself.
    """
    if type(operation) is not str or operation not in COVERED_OPERATIONS:
        raise WriterBoundaryUnavailable("Unknown writer operation; denied.")
    enabled = getattr(settings, GATE_SETTING, False)
    if enabled is False:
        # Existing legacy workflow; NOT an attested or safe production fence.
        return
    if enabled is not True:
        raise WriterBoundaryUnavailable("Invalid protected-writer gate configuration; denied.")
    raise WriterBoundaryUnavailable(
        "A verified protected database writer is not integrated; operation denied."
    )
