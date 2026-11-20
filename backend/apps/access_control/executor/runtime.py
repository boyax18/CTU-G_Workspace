"""Internal ledger-owned transaction context. DB grants remain authoritative."""
from contextlib import contextmanager
from contextvars import ContextVar

_active = ContextVar("workspace_executor_operation", default=None)


def active_operation():
    return _active.get()


@contextmanager
def executing(operation):
    token = _active.set(operation)
    try:
        yield
    finally:
        _active.reset(token)
