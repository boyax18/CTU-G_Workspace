"""WF-03.06 read-only access-control audit history (isolated and default OFF).

This API NEVER changes records. It does not augment, bypass or replace the
protected append-only audit writer. Only a signed-in Technical Super Admin
holding the exact audit.read permission in the active role context may read.
"""
import re
from datetime import date, datetime, time, timedelta, timezone as datetime_timezone

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS, DatabaseError
from rest_framework import exceptions
from rest_framework.response import Response

from apps.accounts.active_role_context import context_enabled
from apps.accounts.registration_review_api import (
    RegistrationReviewAPI, ReviewAPIUnavailable, ReviewListThrottle,
)
from .audit import _state, APPROVAL_ACTION, AUDIT_REASON_CODES
from .executor.client import enabled as executor_enabled
from .models import AccessAuditLog
from .technical_admin import has_technical_authority

READ_CODE = "access_control.audit.read"
PAGE_SIZE = 20
MAX_PAGE = 1000
MAX_ID = 2_147_483_647
ALLOWED_FILTERS = frozenset({"page", "actor", "target", "action", "from", "to"})
ACTION = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,49}\Z", re.ASCII)


class AuditHistoryAPI(RegistrationReviewAPI):
    throttle_classes = [ReviewListThrottle]

    def review_gate_open(self):
        return getattr(settings, "WORKSPACE_WF0306_AUDIT_HISTORY_ENABLED", False) is True

    def initial(self, request, *args, **kwargs):
        # No executor contract was approved for these isolated UI reads.
        if executor_enabled() or not context_enabled():
            raise ReviewAPIUnavailable()
        return super().initial(request, *args, **kwargs)

    def require_technical(self, request):
        actor = self.require_actor(request, READ_CODE)
        if not has_technical_authority(actor, READ_CODE):
            raise exceptions.PermissionDenied("Technical Super Admin authority required.")
        return actor

    def handle_exception(self, exc):
        if isinstance(exc, DatabaseError):
            exc = ReviewAPIUnavailable()
        return super().handle_exception(exc)


def _single(params, key, default=""):
    values = params.getlist(key)
    if len(values) > 1:
        raise exceptions.ValidationError("Repeated audit filter.")
    return values[0] if values else default


def _ctug_id(raw):
    if not raw:
        return ""
    if (type(raw) is not str or not 3 <= len(raw) <= 50 or raw != raw.strip()
            or not raw.isascii() or not all("!" <= c <= "~" for c in raw)):
        raise exceptions.ValidationError("Invalid CTU-G ID filter.")
    return raw


def _date(raw):
    if not raw:
        return None
    if type(raw) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raise exceptions.ValidationError("Dates must be YYYY-MM-DD.")
    try:
        value = date.fromisoformat(raw)
    except ValueError as exc:
        raise exceptions.ValidationError("Invalid date filter.") from exc
    if value.isoformat() != raw:
        raise exceptions.ValidationError("Invalid date filter.")
    return value


def _filters(params):
    if set(params.keys()) - ALLOWED_FILTERS:
        raise exceptions.ValidationError("Unsupported audit filter.")
    raw_page = _single(params, "page", "1")
    if type(raw_page) is not str or not raw_page.isascii() or not re.fullmatch(r"[1-9]\d{0,3}", raw_page):
        raise exceptions.ValidationError("Invalid page.")
    page = int(raw_page)
    if page > MAX_PAGE:
        raise exceptions.ValidationError("Page exceeds the audit history limit.")
    actor = _ctug_id(_single(params, "actor"))
    target = _ctug_id(_single(params, "target"))
    action = _single(params, "action")
    if action and (type(action) is not str or not ACTION.fullmatch(action)):
        raise exceptions.ValidationError("Invalid action filter.")
    start, end = _date(_single(params, "from")), _date(_single(params, "to"))
    if end == date.max:
        raise exceptions.ValidationError("Date exceeds the supported range.")
    if start and end and (start > end or (end-start).days > 366):
        raise exceptions.ValidationError("Select a date range of up to 366 days.")
    return {"page":page, "actor":actor, "target":target, "action":action,
            "from":start,"to":end}


def _query(filters):
    qs = AccessAuditLog.objects.using(DEFAULT_DB_ALIAS).select_related(
        "actor_account", "target_account", "role", "permission"
    )
    if filters["actor"]:
        qs = qs.filter(actor_account__school_id__iexact=filters["actor"])
    if filters["target"]:
        qs = qs.filter(target_account__school_id__iexact=filters["target"])
    if filters["action"]:
        qs = qs.filter(action=filters["action"])
    if filters["from"]:
        start = datetime.combine(filters["from"], time.min, tzinfo=datetime_timezone.utc)
        qs = qs.filter(created_at__gte=start)
    if filters["to"]:
        next_day = datetime.combine(filters["to"] + timedelta(days=1), time.min,
                                    tzinfo=datetime_timezone.utc)
        qs = qs.filter(created_at__lt=next_day)
    return qs


def _summary(record):
    return {
        "audit_id": record.pk,
        "action": record.action,
        "occurred_at": record.created_at.isoformat(),
        "actor_ctug_id": record.actor_account.school_id,
        "target_ctug_id": record.target_account.school_id if record.target_account else None,
        "role_name": record.role.role_name if record.role else None,
        "permission_code": record.permission.permission_code if record.permission else None,
    }


def _safe_snapshot(value, action, *, new=False):
    """Revalidate old/legacy JSON before displaying; never expose arbitrary fields.

    Only the audit writer's strict, controlled state schema is displayable. A
    legacy row outside that schema is redacted rather than echoed to clients.
    """
    if value is None:
        return None, False
    try:
        safe = _state(value, "new_value" if new else "old_value",
                      approval_attestation=new and action == APPROVAL_ACTION)
        return safe, False
    except (ValidationError, TypeError, ValueError, UnicodeError):
        return None, True


class AuditHistoryListView(AuditHistoryAPI):
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        self.require_technical(request)
        filters = _filters(request.query_params)
        start = (filters["page"]-1)*PAGE_SIZE
        rows = list(_query(filters).order_by("-created_at", "-access_audit_log_id")
                    [start:start+PAGE_SIZE+1])
        return Response({"page":filters["page"], "page_size":PAGE_SIZE,
                         "has_next":len(rows)>PAGE_SIZE,
                         "events":[_summary(entry) for entry in rows[:PAGE_SIZE]]})


class AuditHistoryDetailView(AuditHistoryAPI):
    http_method_names = ["get", "head", "options"]

    def get(self, request, audit_id):
        self.require_technical(request)
        if request.query_params or type(audit_id) is not int or not 1 <= audit_id <= MAX_ID:
            raise exceptions.NotFound()
        entry = AccessAuditLog.objects.using(DEFAULT_DB_ALIAS).select_related(
            "actor_account", "target_account", "role", "permission"
        ).filter(pk=audit_id).first()
        if entry is None:
            raise exceptions.NotFound()
        before, old_redacted = _safe_snapshot(entry.old_value, entry.action)
        after, new_redacted = _safe_snapshot(entry.new_value, entry.action, new=True)
        return Response({**_summary(entry), "reason":entry.reason if entry.reason in AUDIT_REASON_CODES else None,
                         "old_value":before, "new_value":after,
                         "old_redacted":old_redacted, "new_redacted":new_redacted})
