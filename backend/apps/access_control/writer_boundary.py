"""Django integration guard for the separately authenticated database executor.

With enforcement enabled, service entry points forward fixed operations over
mTLS. Only a ledger-owned executor transaction can enter the local write body.
The actual database fence is implemented by restricted grants and writer-lease
triggers, not by this Python context. Legacy False is development compatibility.
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
    from .executor.runtime import active_operation
    current = active_operation()
    aliases = {"role_permission.change": {"role_permission.grant", "role_permission.revoke"},
               "account_permission.change": {"account_permission.grant", "account_permission.deny", "account_permission.deactivate",
                                              "account_permission.scoped_grant", "account_permission.restrict"}}
    if current is not None and (current == operation or current in aliases.get(operation, ())):
        # Only executor code joins the outer ledger transaction. Runtime has no
        # protected-table DML grants; forging Python state cannot grant SQL rights.
        from django.db import connection
        if connection.in_atomic_block:
            return
    raise WriterBoundaryUnavailable(
        "A verified protected database writer is not integrated; operation denied."
    )


def writer_atomic():
    """Join an authenticated ledger transaction; otherwise retain durable ownership."""
    from contextlib import nullcontext
    from django.db import connection, transaction
    from .executor.runtime import active_operation
    if active_operation() is not None and connection.in_atomic_block:
        return nullcontext()
    return transaction.atomic(using="default", durable=True)
