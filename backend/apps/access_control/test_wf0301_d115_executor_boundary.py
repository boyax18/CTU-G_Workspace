"""Deferred WF-03.01 D-115 fail-closed regression contracts (no DB required).

Run only during consolidated WF-03 tests. NOT executed when packaged.
"""
from django.test import SimpleTestCase, override_settings

from apps.access_control.appointment_registry import (
    record_appointment, reject_appointment, revoke_appointment, verify_appointment,
)
from apps.access_control.appointment_registry_api import AppointmentRegistryAPI
from apps.access_control.executor.protocol import ORDINARY
from apps.access_control.role_assignment import (
    assign_ordinary_role, assign_school_admin, revoke_ordinary_role, revoke_school_admin,
)
from apps.access_control.role_assignment_api import RoleAssignmentAPI
from apps.access_control.ordinary_role_assignment_api import OrdinaryRoleAssignmentAPI
from apps.access_control.writer_boundary import WriterBoundaryUnavailable
from apps.accounts.active_role_context_api import RoleContextSwitchView
from apps.accounts.registration_review_api import ReviewAPIUnavailable


@override_settings(
    WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True,
    WORKSPACE_ROLE_ASSIGNMENT_ENABLED=True,
    WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_ENABLED=True,
    WORKSPACE_ORDINARY_APPOINTMENT_REGISTRY_ENABLED=True,
    WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True,
)
class ProtectedExecutorWF0301RefusalTests(SimpleTestCase):
    def test_all_staged_review_api_families_refuse_before_account_reads(self):
        # Calling initial without a DRF Request proves the early rejection:
        # no auth, role, appointment or other DB read may be required.
        for view_class in (RoleAssignmentAPI, OrdinaryRoleAssignmentAPI, AppointmentRegistryAPI):
            with self.subTest(view=view_class.__name__):
                with self.assertRaises(ReviewAPIUnavailable):
                    view_class().initial(None)

    def test_context_switch_refuses_even_without_middleware(self):
        result = RoleContextSwitchView().post(None)
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.data["error"]["code"], "role_context_unavailable")

    def test_existing_direct_role_service_guards_still_refuse(self):
        # No DB is available to SimpleTestCase. Any accidentally reached
        # role lookup/transaction causes this deferred test to fail.
        attempts = (
            lambda: assign_school_admin(actor=object(), target_id=2),
            lambda: revoke_school_admin(actor=object(), target_id=2),
            lambda: assign_ordinary_role(actor=object(), target_id=2, role_name="Treasurer"),
            lambda: revoke_ordinary_role(actor=object(), target_id=2, role_name="SSG Advisor"),
            lambda: record_appointment(actor=object(), target_id=2, role_name="Treasurer",
                                       document_sha256="0" * 64, valid_from=None, valid_until=None),
            lambda: verify_appointment(actor=object(), appointment_id=1, confirmed_digest="0" * 64),
            lambda: reject_appointment(actor=object(), appointment_id=1),
            lambda: revoke_appointment(actor=object(), appointment_id=1),
        )
        for attempt in attempts:
            with self.subTest(attempt=repr(attempt)):
                with self.assertRaises(WriterBoundaryUnavailable):
                    attempt()

    def test_legacy_role_assign_is_not_an_ordinary_responsibility_operation(self):
        # The existing executor's role.assign supports only base-role
        # assignment. No implicit translation of new WF-03.01 workflows.
        self.assertIn("role.assign", ORDINARY)
        self.assertFalse(any(name.startswith("appointment.") for name in ORDINARY))
        self.assertNotIn("role.revoke", ORDINARY)
        self.assertNotIn("role.context.switch", ORDINARY)
