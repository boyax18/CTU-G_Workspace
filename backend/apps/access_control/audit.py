"""Append-only audit primitive for explicitly transactional, trusted services.

This module attributes and validates audit data; it does not authorize callers.
Call only after authorization, inside the SAME atomic block as the mutation.
Return/notify success only after that enclosing block commits.
"""

import json
import re

from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS, transaction

from apps.accounts.models import Account

from .models import AccessAuditLog, Permission, Role


class AuditTransactionError(RuntimeError):
    """The caller has not supplied a usable enclosing atomic transaction."""


class AuditValidationError(ValidationError):
    """Audit input is invalid; messages never contain submitted values."""


# Controlled metadata only. These are audit reason codes, not permission codes
# or authority to mutate anything. Raw human/request text is deliberately refused.
AUDIT_REASON_CODES = frozenset({
    "access_review", "policy_enforcement", "assignment_change",
    "permission_change", "account_status_change", "correction",
})
MAX_STATE_BYTES = 2048
MAX_ID_LIST_ITEMS = 100
MAX_ID = 2_147_483_647
_ID_FIELDS = frozenset({
    "account_id", "role_id", "permission_id", "service_id",
    "account_role_id", "role_permission_id", "account_permission_id",
})
_ID_LIST_FIELDS = frozenset({"role_ids", "permission_ids"})
_ENUM_FIELDS = {
    "effect": frozenset({"Grant", "Deny"}),
    "request_status": frozenset({"Pending", "Approved", "Rejected"}),
}
_STATE_FIELDS = _ID_FIELDS | _ID_LIST_FIELDS | frozenset(_ENUM_FIELDS) | frozenset({"is_active"})
_ACTION_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]*", re.ASCII)


def _invalid(field, message):
    raise AuditValidationError({field: [message]})


def _reference_id(value, model, field, required=False):
    if value is None and not required:
        return None
    if (
        not isinstance(value, model)
        or value._state.adding
        or value._state.db != DEFAULT_DB_ALIAS
        or type(value.pk) is not int
        or not 1 <= value.pk <= MAX_ID
    ):
        _invalid(field, "Provide an existing persisted reference from the primary database.")
    if not model.objects.using(DEFAULT_DB_ALIAS).filter(pk=value.pk).exists():
        _invalid(field, "The referenced record does not exist.")
    # Foreign-key enforcement also protects against deletion after this check.
    return value.pk


def _valid_id(value):
    return type(value) is int and 1 <= value <= MAX_ID


def _state(value, field):
    if value is None:
        return None
    if type(value) is not dict or any(type(key) is not str for key in value):
        _invalid(field, "Provide a plain authorization-state object or null.")
    if value.keys() - _STATE_FIELDS:
        _invalid(field, "The snapshot contains unsupported fields.")
    for key, item in value.items():
        if key in _ID_FIELDS:
            valid = item is None or _valid_id(item)
        elif key in _ID_LIST_FIELDS:
            valid = type(item) is list and len(item) <= MAX_ID_LIST_ITEMS and all(_valid_id(entry) for entry in item)
        elif key == "is_active":
            valid = type(item) is bool
        else:
            valid = type(item) is str and item in _ENUM_FIELDS[key]
        if not valid:
            _invalid(field, "The snapshot contains an unsupported value or exceeds its bounds.")
    encoded = json.dumps(value, allow_nan=False, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_STATE_BYTES:
        _invalid(field, "The snapshot exceeds the serialized size limit.")
    # Detach all mutable caller-owned structures. No arbitrary objects, nested
    # payloads, personal text, secrets, or automatic string conversions are kept.
    return json.loads(encoded)


def record_access_audit(*, actor, action, target=None, role=None, permission=None,
                        old_value=None, new_value=None, reason=None):
    """Stage one audit INSERT in the caller's primary-database transaction.

    No model or success receipt is returned. Failures propagate AND mark the
    current atomic scope rollback-only, even if a caller accidentally catches
    them. Catch outside the owning transaction, not in a recovery savepoint.
    Direct ORM/SQL updates remain outside this append-only service contract.
    """
    connection = transaction.get_connection(DEFAULT_DB_ALIAS)
    if not connection.in_atomic_block or connection.needs_rollback:
        raise AuditTransactionError("Audit writes require a usable enclosing transaction.atomic() block.")

    try:
        if (
            type(action) is not str
            or not action
            or len(action) > AccessAuditLog._meta.get_field("action").max_length
            or not _ACTION_PATTERN.fullmatch(action)
        ):
            _invalid("action", "Provide a nonempty bounded action code using letters, digits, dots, underscores, colons or hyphens.")
        if reason is not None:
            if type(reason) is not str or len(reason) > AccessAuditLog._meta.get_field("reason").max_length:
                _invalid("reason", "Provide a bounded audit reason code or null.")
            if reason not in AUDIT_REASON_CODES:
                _invalid("reason", "Use a supported non-sensitive audit reason code.")

        previous = _state(old_value, "old_value")
        following = _state(new_value, "new_value")
        actor_id = _reference_id(actor, Account, "actor", required=True)
        target_id = _reference_id(target, Account, "target")
        role_id = _reference_id(role, Role, "role")
        permission_id = _reference_id(permission, Permission, "permission")
        AccessAuditLog.objects.using(DEFAULT_DB_ALIAS).create(
            actor_account_id=actor_id, target_account_id=target_id,
            role_id=role_id, permission_id=permission_id, action=action,
            old_value=previous, new_value=following, reason=reason,
        )
        # created_at comes solely from the existing database/model default.
    except Exception:
        transaction.set_rollback(True, using=DEFAULT_DB_ALIAS)
        raise
