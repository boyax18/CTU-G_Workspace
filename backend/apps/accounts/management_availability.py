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
    from .registration_review import rejection_notification_ready
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
