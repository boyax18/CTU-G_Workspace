"""Isolated, default-off WF-03.01 appointment registry API.

School Admin's verified appointment-recording permission is NOT role assignment.
Reviewing requires a separate exact permission, a different account and an
externally checked document digest. Not included in production config.urls.
"""

from django.utils.dateparse import parse_datetime
from rest_framework import exceptions
from rest_framework.response import Response

from apps.accounts.registration_review_api import (
    MAX_ACCOUNT_ID, PAGE_SIZE, ReviewBurstThrottle, ReviewListThrottle, _single,
)

from .appointment_registry import (
    RECORD_PERMISSION, VERIFY_PERMISSION, AppointmentConflict, record_appointment,
    registry_gate_open, reject_appointment, revoke_appointment, verify_appointment,
)
from .models import OrdinaryAppointment
from .role_assignment_api import RoleAssignmentAPI


def _timestamp(value):
    if type(value) is not str or len(value) > 40:
        raise exceptions.ValidationError("Provide an ISO-8601 timestamp with a timezone offset.")
    result = parse_datetime(value)
    if result is None or result.tzinfo is None or result.utcoffset() is None:
        raise exceptions.ValidationError("Provide a timezone-aware appointment timestamp.")
    return result


class AppointmentRegistryAPI(RoleAssignmentAPI):
    def review_gate_open(self):
        return registry_gate_open()

    def handle_exception(self, exc):
        if isinstance(exc, AppointmentConflict):
            return Response({"error": {"code": "appointment_conflict", "reason": exc.reason,
                                       "message": "The appointment could not be changed."}}, status=409)
        return super().handle_exception(exc)


class AppointmentSubmitView(AppointmentRegistryAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [ReviewBurstThrottle]

    def post(self, request):
        actor = self.require_actor(request, RECORD_PERMISSION)
        data = request.data
        if not isinstance(data, dict) or set(data) != {
            "account_id", "role_name", "document_sha256", "valid_from", "valid_until",
        }:
            raise exceptions.ValidationError("Appointment candidate fields are incomplete.")
        target_id = data["account_id"]
        if type(target_id) is not int or not 1 <= target_id <= MAX_ACCOUNT_ID:
            raise exceptions.ValidationError("Account ID is invalid.")
        return Response(record_appointment(
            actor=actor, target_id=target_id, role_name=data["role_name"],
            document_sha256=data["document_sha256"],
            valid_from=_timestamp(data["valid_from"]),
            valid_until=_timestamp(data["valid_until"]),
        ), status=201)


class AppointmentReviewQueueView(AppointmentRegistryAPI):
    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def get(self, request):
        actor = self.require_actor(request, VERIFY_PERMISSION)
        if set(request.query_params) - {"page"}:
            raise exceptions.ValidationError("Unsupported query fields.")
        page_text = _single(request.query_params, "page", "1")
        if not page_text.isascii() or not page_text.isdecimal() or not 1 <= int(page_text) <= 10000:
            raise exceptions.ValidationError("Invalid page.")
        page = int(page_text)
        rows = list(OrdinaryAppointment.objects.filter(
            status="Submitted").exclude(submitted_by_id=actor.pk).exclude(account_id=actor.pk)
            .order_by("appointment_id")[(page - 1) * PAGE_SIZE:page * PAGE_SIZE + 1])
        # Deliberately omit submitted digest: independent reviewer must calculate
        # it from the official source rather than copy a value from this API.
        return Response({"page": page, "has_next": len(rows) > PAGE_SIZE, "results": [
            {"appointment_id": row.pk, "account_id": row.account_id,
             "role_name": row.role_name, "valid_from": row.valid_from,
             "valid_until": row.valid_until} for row in rows[:PAGE_SIZE]
        ]})


class AppointmentReviewView(AppointmentRegistryAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [ReviewBurstThrottle]

    def post(self, request, appointment_id, action):
        actor = self.require_actor(request, VERIFY_PERMISSION)
        if not 1 <= appointment_id <= MAX_ACCOUNT_ID or action not in {"verify", "reject", "revoke"}:
            raise exceptions.NotFound()
        data = request.data
        if not isinstance(data, dict):
            raise exceptions.ValidationError("Provide a JSON object.")
        if action == "verify":
            if set(data) != {"confirmed_document_sha256"}:
                raise exceptions.ValidationError("Independent source digest is required.")
            change = verify_appointment(actor=actor, appointment_id=appointment_id,
                                        confirmed_digest=data["confirmed_document_sha256"])
        else:
            if data:
                raise exceptions.ValidationError("This decision does not accept extra fields.")
            handler = reject_appointment if action == "reject" else revoke_appointment
            change = handler(actor=actor, appointment_id=appointment_id)
        return Response(change)
