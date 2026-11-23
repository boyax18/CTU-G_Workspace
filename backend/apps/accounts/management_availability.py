"""Request-local UI hints; mutation services remain authoritative inside their locks.

An enabled frontend must not advertise actions absent from this server's URLconf,
disabled by its gates, denied in the selected role context, or blocked by the executor.
No applicant data, credentials or permissions are written by this helper.
"""
from django.urls import Resolver404, resolve

from apps.access_control.services import has_permission

HEADER = "X-Workspace-Available-Actions"


def attach_available_actions(response, actor, account_id, kind):
    from apps.access_control.executor.client import enabled as executor_enabled
    from .account_status import ACTIVATE_CODE, SUSPEND_CODE, gate_open
    from .account_status_api import ActivateSchoolAccountView, SuspendSchoolAccountView
    from .registration_review import approval_notification_ready, rejection_notification_ready
    from .registration_review_api import (
        APPROVE_CODE, REJECT_CODE, ApproveRegistrationRequestView,
        RejectRegistrationRequestView, _decision_gates_open,
    )

    actions = []
    if not executor_enabled():
        if kind == "registration" and _decision_gates_open():
            candidates = [
                ("approve", APPROVE_CODE, "registration-requests", ApproveRegistrationRequestView),
                ("reject", REJECT_CODE, "registration-requests", RejectRegistrationRequestView),
            ]
        elif kind == "status" and gate_open():
            candidates = [
                ("suspend", SUSPEND_CODE, "school-accounts", SuspendSchoolAccountView),
                ("activate", ACTIVATE_CODE, "school-accounts", ActivateSchoolAccountView),
            ]
        else:
            candidates = []
        for action, code, root, view in candidates:
            if action == "approve" and not approval_notification_ready():
                continue
            if action == "reject" and not rejection_notification_ready():
                continue
            try:
                matched = resolve(f"/api/v1/admin/{root}/{account_id}/{action}/")
            except Resolver404:
                continue
            if (getattr(matched.func, "view_class", None) is view
                    and not getattr(matched.func, "view_initkwargs", {})
                    and not getattr(matched.func, "initkwargs", {})
                    and has_permission(actor, code)):
                actions.append(action)
    response[HEADER] = ",".join(actions)
    return response


def attach_pending_registration_actions(response, actor, request):
    """Include bulk actions only when their detached endpoint and every gate are ready."""
    from django.conf import settings
    from apps.access_control.executor.client import enabled as executor_enabled
    from .registration_review import approval_notification_ready, rejection_notification_ready
    from .registration_review_api import APPROVE_CODE, REJECT_CODE, _decision_gates_open

    response = attach_available_actions(response, actor, 0, "registration")
    actions = [item for item in response[HEADER].split(",") if item]
    if not executor_enabled() and _decision_gates_open() \
            and getattr(settings, "WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED", False):
        from .registration_bulk_api import BulkRegistrationReviewView
        candidates = (
            ("bulk-approve", APPROVE_CODE, approval_notification_ready),
            ("bulk-reject", REJECT_CODE, rejection_notification_ready),
        )
        path = f"{request.path.rstrip('/')}/bulk/"
        try:
            matched = resolve(path)
        except Resolver404:
            matched = None
        if (matched is not None
                and getattr(matched.func, "view_class", None) is BulkRegistrationReviewView
                and not getattr(matched.func, "view_initkwargs", {})
                and not getattr(matched.func, "initkwargs", {})):
            for action, code, notification_ready in candidates:
                if notification_ready() and has_permission(actor, code):
                    actions.append(action)
    response[HEADER] = ",".join(actions)
    return response
