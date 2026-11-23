"""WF-03.01 R-2 Option D phase 1 (owner-authorized PROTOTYPE): read-only audit-receipt checkpoint.

Computes a deterministic hash chain over every persisted access_audit_logs row in receipt-ID order, and
verifies the current table against a checkpoint the operator holds OUTSIDE the database. It never writes,
never repairs and is NOT wired into any grant, revoke, compensation or session path.

Trust boundary: a checkpoint kept only in the same database proves nothing; anyone who can rewrite the rows
can rewrite it too. Only a checkpoint held outside the database (for example the owner-controlled D-95
operational record), optionally authenticated with an HMAC key the database cannot read, lets a later run
detect that rows up to the checkpoint were modified, deleted, inserted, reordered or re-timestamped. Rows
committed after the checkpoint are reported as unanchored and are not verified. A database administrator
can still change anything; this only makes such a change detectable against an earlier external checkpoint.
"""

import hashlib
import hmac
import json
import re

from django.db import DEFAULT_DB_ALIAS, connections

from .models import AccessAuditLog

VERSION = "ctug.access_audit.checkpoint.v1"
FIELDS = ("access_audit_log_id", "action", "actor_account_id", "target_account_id", "role_id", "permission_id",
          "old_value", "new_value", "reason", "created_at")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_KEYS = {"version", "count", "max_id", "head"}


class CheckpointError(ValueError):
    """Malformed input or an inconsistent read; nothing is repaired."""


class CheckpointMismatch(Exception):
    """The current receipts do not reproduce the trusted checkpoint."""


def _canonical(row):
    data = dict(zip(FIELDS, row))
    created = data["created_at"]
    data["created_at"] = None if created is None else created.isoformat()
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _rows(using):
    connection = connections[using]
    if connection.in_atomic_block:
        raise CheckpointError("Run the checkpoint outside any transaction.")
    with connection.cursor() as cursor:
        cursor.execute("START TRANSACTION READ ONLY")  # any accidental write fails inside this transaction
    try:
        # One statement: under READ COMMITTED a single SELECT reads one consistent set of committed rows.
        return list(AccessAuditLog.objects.using(using).order_by("access_audit_log_id").values_list(*FIELDS))
    finally:
        with connection.cursor() as cursor:
            cursor.execute("ROLLBACK")


def _chain(rows):
    head = hashlib.sha256(VERSION.encode()).hexdigest()
    previous = 0
    for row in rows:
        identifier = row[0]
        if type(identifier) is not int or identifier <= previous:
            raise CheckpointError("Receipt identifiers are not strictly increasing.")
        previous = identifier
        head = hashlib.sha256(f"{head}\n{_canonical(row)}".encode("utf-8")).hexdigest()
    return head


def _mac(summary, key):
    message = json.dumps({k: summary[k] for k in sorted(_KEYS)}, sort_keys=True, separators=(",", ":"))
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()


def compute(*, using=DEFAULT_DB_ALIAS, key=None):
    """Checkpoint of the current table: version, count, max_id, head (and an HMAC if a key is supplied)."""
    rows = _rows(using)
    summary = {"version": VERSION, "count": len(rows), "max_id": rows[-1][0] if rows else 0, "head": _chain(rows)}
    if key is not None:
        summary["hmac"] = _mac(summary, _key(key))
    return summary


def _key(key):
    if type(key) is not bytes or len(key) < 32:
        raise CheckpointError("An HMAC key of at least 32 bytes is required.")
    return key


def parse(text):
    """Strictly parse a trusted checkpoint; anything unexpected fails closed."""
    try:
        data = json.loads(text, parse_constant=lambda c: (_ for _ in ()).throw(CheckpointError("Invalid constant.")))
    except (TypeError, ValueError) as exc:
        raise CheckpointError("The trusted checkpoint is not valid JSON.") from exc
    if type(data) is not dict or not (_KEYS <= set(data) <= _KEYS | {"hmac"}):
        raise CheckpointError("The trusted checkpoint has missing or unexpected fields.")
    if (data["version"] != VERSION or type(data["count"]) is not int or type(data["max_id"]) is not int
            or data["count"] < 0 or data["max_id"] < 0 or (data["count"] == 0) != (data["max_id"] == 0)
            or type(data["head"]) is not str or not _HEX64.fullmatch(data["head"])
            or ("hmac" in data and (type(data["hmac"]) is not str or not _HEX64.fullmatch(data["hmac"])))):
        raise CheckpointError("The trusted checkpoint is malformed.")
    return data


def verify(trusted, *, using=DEFAULT_DB_ALIAS, key=None):
    """Verify the receipts up to the trusted checkpoint; report newer rows as unanchored. Never repairs."""
    if "hmac" in trusted:
        if key is None:
            raise CheckpointError("The trusted checkpoint is authenticated; its HMAC key is required.")
        if not hmac.compare_digest(trusted["hmac"], _mac(trusted, _key(key))):
            raise CheckpointMismatch("The trusted checkpoint's HMAC does not verify.")
    elif key is not None:
        raise CheckpointError("An HMAC key was supplied for an unauthenticated checkpoint.")
    rows = _rows(using)
    anchored = [row for row in rows if row[0] <= trusted["max_id"]]
    if len(anchored) != trusted["count"] or (anchored and anchored[-1][0] != trusted["max_id"]):
        raise CheckpointMismatch("Receipts up to the checkpoint were added, removed or renumbered.")
    if _chain(anchored) != trusted["head"]:
        raise CheckpointMismatch("Receipts up to the checkpoint were changed or reordered.")
    return {"result": "VERIFIED", "anchored": len(anchored), "unanchored_newer": len(rows) - len(anchored)}
