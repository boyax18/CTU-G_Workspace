"""WF-03.01 D-111 deferred tests: ONLY use disposable test MySQL after WF-03.06.

No tests run during the accelerated source-staging phase. These cases exercise
runtime authorization on every check rather than pretending a periodic job
updates appointments.
"""
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.access_control.appointment_registry import (
    RECORD_PERMISSION, VERIFY_PERMISSION, record_appointment, verify_appointment,
)
from apps.access_control.models import (
    AccountPermission, AccountRole, OrdinaryAppointment, Permission, Role,
    RolePermission, Service,
)
from apps.access_control.ordinary_role_runtime import verified_ordinary_roles_for
from apps.access_control.services import get_effective_permissions, has_permission
from apps.access_control.test_wf0301_role_assignment import World
from apps.accounts.session_auth import _account_payload


@override_settings(
    WORKSPACE_ORDINARY_APPOINTMENT_REGISTRY_ENABLED=True,
    WORKSPACE_ORDINARY_APPOINTMENT_EVIDENCE_ENABLED=True,
    WORKSPACE_ORDINARY_APPOINTMENT_RUNTIME_ENFORCEMENT_ENABLED=True,
)
class OrdinaryRuntimeEnforcementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.world = World()
        cls.recorder = cls.world.account("D111-RECORDER", "Instructor", "Admin")
        cls.reviewer = cls.world.account("D111-REVIEWER", "Instructor", "Admin")
        cls.assigner = cls.world.account("D111-ASSIGNER", "Instructor")
        cls.student = cls.world.account("D111-STUDENT", "Student")
        cls.treasurer = Role.objects.get(role_name="Treasurer")
        cls.base_permission = Permission.objects.create(
            service=cls.world.accounts, permission_code="d111.student.view",
            permission_name="Base", module_name="student", action_name="view",
        )
        cls.ordinary_permission = Permission.objects.create(
            service=Service.objects.get(service_code="access_control"),
            permission_code="d111.treasurer.manage", permission_name="Special",
            module_name="treasurer", action_name="manage",
        )
        RolePermission.objects.create(role=cls.world.roles["Student"], permission=cls.base_permission)
        RolePermission.objects.create(role=cls.treasurer, permission=cls.ordinary_permission)
        AccountRole.objects.create(account=cls.student, role=cls.treasurer,
                                   assigned_by=cls.assigner)
        admin = Role.objects.get(role_name="Admin")
        for code in (RECORD_PERMISSION, VERIFY_PERMISSION):
            p = Permission.objects.create(
                service=Service.objects.get(service_code="access_control"),
                permission_code=code, permission_name=code,
                module_name="appointments", action_name="review",
            )
            RolePermission.objects.create(role=admin, permission=p)

    def verify(self):
        result = record_appointment(
            actor=self.recorder, target_id=self.student.pk, role_name="Treasurer",
            document_sha256="b" * 64,
            valid_from=timezone.now() - timedelta(minutes=1),
            valid_until=timezone.now() + timedelta(days=4),
        )
        verify_appointment(actor=self.reviewer, appointment_id=result["appointment_id"],
                           confirmed_digest="b" * 64)
        return result["appointment_id"]

    def test_default_deny_keeps_base_access_and_filters_role_hint(self):
        self.assertFalse(has_permission(self.student, self.ordinary_permission.permission_code))
        self.assertTrue(has_permission(self.student, self.base_permission.permission_code))
        self.assertEqual(verified_ordinary_roles_for(self.student.pk), frozenset())
        payload = _account_payload(self.student)
        self.assertEqual(payload["account"]["roles"], ["Student"])

    def test_verified_supporting_record_enables_only_current_ordinary_grants(self):
        self.verify()
        self.assertTrue(has_permission(self.student, self.ordinary_permission.permission_code))
        self.assertEqual(verified_ordinary_roles_for(self.student.pk), frozenset({"Treasurer"}))
        self.assertEqual(_account_payload(self.student)["account"]["roles"], ["Student", "Treasurer"])

    def test_expiry_revocation_and_missing_assigned_by_immediately_remove_privilege(self):
        id_ = self.verify()
        self.assertTrue(has_permission(self.student, self.ordinary_permission.permission_code))
        OrdinaryAppointment.objects.filter(pk=id_).update(valid_until=timezone.now() - timedelta(seconds=1))
        self.assertFalse(has_permission(self.student, self.ordinary_permission.permission_code))
        self.assertTrue(has_permission(self.student, self.base_permission.permission_code))
        OrdinaryAppointment.objects.filter(pk=id_).update(valid_until=timezone.now() + timedelta(days=2),
                                                            status="Revoked")
        self.assertFalse(has_permission(self.student, self.ordinary_permission.permission_code))
        OrdinaryAppointment.objects.filter(pk=id_).update(status="Verified")
        AccountRole.objects.filter(account=self.student, role=self.treasurer).update(assigned_by=None)
        self.assertFalse(has_permission(self.student, self.ordinary_permission.permission_code))

    def test_direct_grant_cannot_bypass_appointment_requirement(self):
        AccountPermission.objects.create(account=self.student, permission=self.ordinary_permission,
                                         effect="Grant")
        self.assertFalse(has_permission(self.student, self.ordinary_permission.permission_code))
        self.assertEqual(get_effective_permissions(self.student),
                         frozenset({self.base_permission.permission_code}))

    @override_settings(WORKSPACE_ORDINARY_APPOINTMENT_EVIDENCE_ENABLED=False)
    def test_evidence_gate_off_discards_special_role_without_losing_base_role(self):
        self.verify()
        self.assertFalse(has_permission(self.student, self.ordinary_permission.permission_code))
        self.assertTrue(has_permission(self.student, self.base_permission.permission_code))

    @override_settings(WORKSPACE_ORDINARY_APPOINTMENT_RUNTIME_ENFORCEMENT_ENABLED=False)
    def test_staged_runtime_gate_off_preserves_legacy_evaluator_until_release(self):
        self.assertTrue(has_permission(self.student, self.ordinary_permission.permission_code))

    def test_shared_code_from_independent_student_role_remains_usable(self):
        # Only the invalid ordinary role's grant is suppressed; an independent
        # existing base-role grant to the same code remains effective.
        RolePermission.objects.create(role=self.world.roles["Student"],
                                      permission=self.ordinary_permission)
        self.assertTrue(has_permission(self.student, self.ordinary_permission.permission_code))

    def test_assignee_cannot_reuse_evidence_verified_by_its_role_assigner(self):
        self.verify()
        AccountRole.objects.filter(account=self.student, role=self.treasurer).update(
            assigned_by=self.reviewer)
        self.assertFalse(has_permission(self.student, self.ordinary_permission.permission_code))
