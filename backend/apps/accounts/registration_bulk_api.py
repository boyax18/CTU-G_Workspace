"""Detached AR-6C5C bulk API: NEVER include in config.urls without approval.

Requires three independent feature gates and the existing exact-permission
Workspace session / CSRF / scoped-review checks. No role-name bypass.
"""

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .registration_bulk import process_bulk_registration, validate_bulk_request
from .registration_review_api import (
    APPROVE_CODE, REJECT_CODE, RegistrationReviewAPI, ReviewAPIUnavailable,
    ReviewBurstThrottle,
)


class BulkReviewBurstThrottle(SimpleRateThrottle):
    scope = "workspace_bulk_review_burst"
    rate = "3/min"

    def get_cache_key(self, request, view):
        # Do not trust unvalidated X-Forwarded-For or client-supplied identities.
        return self.cache_format % {
            "scope": self.scope,
            "ident": request.META.get("REMOTE_ADDR", "unknown"),
        }


class BulkRegistrationReviewView(RegistrationReviewAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [BulkReviewBurstThrottle, ReviewBurstThrottle]

    def initial(self, request, *args, **kwargs):
        if not getattr(settings, "WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED", False):
            raise ReviewAPIUnavailable()
        super().initial(request, *args, **kwargs)

    def post(self, request):
        # Validate the entire batch *before* any decision is committed.
        action, ids, rejection_code = validate_bulk_request(request.data)
        permission = APPROVE_CODE if action == "approve" else REJECT_CODE
        actor = self.require_actor(request, permission)

        report = process_bulk_registration(
            actor=actor,
            action=action,
            account_ids=ids,
            rejection_code=rejection_code,
            recheck_authority=lambda: self.require_actor(request, permission),
        )
        return Response(report, status=status.HTTP_200_OK)
