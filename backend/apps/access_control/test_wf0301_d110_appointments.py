"""WF-03.01 D-110 DEFERRED tests. Run on disposable MySQL after WF-03.06.

Never use ctug_workspace as a test database. Tests are authored, not executed
under the owner's accelerated Inspect/Reconcile/Approve/Implement/Commit policy.
"""
from datetime import timedelta
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from apps.access_control.appointment_registry import (
    AppointmentConflict, RECORD_PERMISSION, VERIFY_PERMISSION,
    record_appointment, registry_gate_open, verify_appointment, revoke_appointment,
)
from apps.access_control.models import AccountRole, OrdinaryAppointment, Permission, Role, RolePermission, Service
from apps.access_control.ordinary_appointment_evidence import appointment_verified_for
from apps.access_control.role_management import RoleChangeDenied
from apps.access_control.test_wf0301_role_assignment import World, configure, GATES


class AppointmentGateTests(SimpleTestCase):
    @override_settings(WORKSPACE_ORDINARY_APPOINTMENT_REGISTRY_ENABLED=False)
    def test_registry_default_off(self):
        self.assertFalse(registry_gate_open())

    @override_settings(WORKSPACE_ORDINARY_APPOINTMENT_EVIDENCE_ENABLED=False)
    def test_evidence_default_off_even_if_caller_supplies_a_role(self):
        self.assertFalse(appointment_verified_for(target_account_id=1, role_name="Treasurer"))


@override_settings(WORKSPACE_ORDINARY_APPOINTMENT_REGISTRY_ENABLED=True, **GATES)
class AppointmentLedgerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()
        cls.recorder = cls.w.account("D110-RECORDER", "Instructor", "Admin")
        cls.verifier = cls.w.account("D110-VERIFIER", "Instructor", "Admin")
        cls.assigner = cls.w.account("D110-ASSIGNER", "Instructor")
        configure("grant-technical-super-admin", cls.assigner)
        cls.student = cls.w.account("D110-STUDENT", "Student")
        service = Service.objects.get(service_code="access_control")
        admin = Role.objects.get(role_name="Admin")
        for code in (RECORD_PERMISSION, VERIFY_PERMISSION):
            perm = Permission.objects.create(service=service, permission_code=code,
                                             permission_name=code, module_name="appointments",
                                             action_name="review")
            RolePermission.objects.create(role=admin, permission=perm)

    def submit(self):
        return record_appointment(
            actor=self.recorder, target_id=self.student.pk, role_name="Treasurer",
            document_sha256="a" * 64,
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=7),
        )

    def test_submitted_digest_never_grants_access_without_independent_review(self):
        ref = self.submit()
        with override_settings(WORKSPACE_ORDINARY_APPOINTMENT_EVIDENCE_ENABLED=True):
            self.assertFalse(appointment_verified_for(target_account_id=self.student.pk, role_name="Treasurer"))
        self.assertEqual(OrdinaryAppointment.objects.get(pk=ref["appointment_id"]).status, "Submitted")

    def test_recording_and_reviewing_by_same_account_is_refused(self):
        ref = self.submit()
        with self.assertRaises(RoleChangeDenied):
            verify_appointment(actor=self.recorder, appointment_id=ref["appointment_id"],
                               confirmed_digest="a" * 64)

    def test_verified_record_requires_distinct_assigner_and_current_dates(self):
        ref = self.submit()
        verify_appointment(actor=self.verifier, appointment_id=ref["appointment_id"],
                           confirmed_digest="a" * 64)
        with override_settings(WORKSPACE_ORDINARY_APPOINTMENT_EVIDENCE_ENABLED=True):
            self.assertTrue(appointment_verified_for(target_account_id=self.student.pk,
                              role_name="Treasurer", assigning_account_id=self.assigner.pk))
            self.assertFalse(appointment_verified_for(target_account_id=self.student.pk,
                              role_name="Treasurer", assigning_account_id=self.verifier.pk))
            self.assertFalse(appointment_verified_for(target_account_id=self.student.pk,
                              role_name="Treasurer", assigning_account_id=self.recorder.pk))
        OrdinaryAppointment.objects.filter(pk=ref["appointment_id"]).update(
            valid_until=timezone.now() - timedelta(seconds=1))
        with override_settings(WORKSPACE_ORDINARY_APPOINTMENT_EVIDENCE_ENABLED=True):
            self.assertFalse(appointment_verified_for(target_account_id=self.student.pk, role_name="Treasurer"))

    def test_revoke_requires_removing_existing_role_first(self):
        ref = self.submit()
        verify_appointment(actor=self.verifier, appointment_id=ref["appointment_id"],
                           confirmed_digest="a" * 64)
        treasurer = Role.objects.get(role_name="Treasurer")
        AccountRole.objects.create(account=self.student, role=treasurer, assigned_by=self.assigner)
        with self.assertRaises(AppointmentConflict) as caught:
            revoke_appointment(actor=self.verifier, appointment_id=ref["appointment_id"])
        self.assertEqual(caught.exception.reason, "role_still_assigned")

    def test_wrong_digest_does_not_verify(self):
        ref = self.submit()
        with self.assertRaises(AppointmentConflict):
            verify_appointment(actor=self.verifier, appointment_id=ref["appointment_id"],
                               confirmed_digest="b" * 64)
        self.assertEqual(OrdinaryAppointment.objects.get(pk=ref["appointment_id"]).status, "Submitted")
