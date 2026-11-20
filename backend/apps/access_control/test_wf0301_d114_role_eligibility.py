"""D-114 deferred regression: runtime eligibility drift after appointment approval.

Run only during the consolidated WF-03 disposable-MySQL test phase. Never
execute against live ctug_workspace during source staging.
"""
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from apps.access_control.models import AccountRole, Role
from apps.access_control.ordinary_role_runtime import verified_ordinary_roles_for
from apps.access_control.test_wf0301_role_assignment import World
from apps.accounts.active_role_context import available_roles

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("D-114 tests require isolated config.test_settings.")


@override_settings(WORKSPACE_ORDINARY_APPOINTMENT_RUNTIME_ENFORCEMENT_ENABLED=True)
class OrdinaryRoleEligibilityDriftTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.world = World()
        cls.assigner = cls.world.account("D114-ASSIGNER", "Instructor")
        cls.student = cls.world.account("D114-STUDENT", "Student")
        cls.instructor = cls.world.account("D114-INSTRUCTOR", "Instructor")
        cls.treasurer = cls.world.roles["Treasurer"]
        cls.advisor = Role.objects.get_or_create(role_name="SSG Advisor", defaults={"is_active": True})[0]
        AccountRole.objects.create(account=cls.student, role=cls.treasurer, assigned_by=cls.assigner)
        AccountRole.objects.create(account=cls.instructor, role=cls.advisor, assigned_by=cls.assigner)

    def verified(self, account):
        # Isolate the source-independent role preconditions. D-111/D-110 cover
        # real appointment evidence and audit receipt verification separately.
        with patch("apps.access_control.ordinary_role_runtime.appointment_verified_for", return_value=True):
            return verified_ordinary_roles_for(account.pk)

    def test_valid_base_roles_can_use_verified_ordinary_roles(self):
        self.assertEqual(self.verified(self.student), {"Treasurer"})
        self.assertEqual(self.verified(self.instructor), {"SSG Advisor"})

    def test_removing_student_base_immediately_denies_treasurer(self):
        AccountRole.objects.filter(account=self.student, role=self.world.roles["Student"]).delete()
        self.assertEqual(self.verified(self.student), frozenset())
        with patch("apps.access_control.ordinary_role_runtime.appointment_verified_for", return_value=True):
            self.assertNotIn("Treasurer", [r["role_name"] for r in available_roles(self.student.pk)])

    def test_disabling_instructor_base_immediately_denies_advisor(self):
        Role.objects.filter(pk=self.world.roles["Instructor"].pk).update(is_active=False)
        self.assertEqual(self.verified(self.instructor), frozenset())

    def test_protected_role_conflict_denies_even_when_protected_role_is_dormant(self):
        admin = self.world.roles["Admin"]
        AccountRole.objects.create(account=self.student, role=admin)
        self.assertEqual(self.verified(self.student), frozenset())
        Role.objects.filter(pk=admin.pk).update(is_active=False)
        self.assertEqual(self.verified(self.student), frozenset())

    def test_cross_base_and_ordinary_conflicts_are_refused(self):
        AccountRole.objects.create(account=self.student, role=self.world.roles["Instructor"])
        self.assertEqual(self.verified(self.student), frozenset())
        AccountRole.objects.create(account=self.instructor, role=self.treasurer, assigned_by=self.assigner)
        self.assertEqual(self.verified(self.instructor), frozenset())

    def test_framework_account_never_receives_ordinary_authority(self):
        type(self.student).objects.filter(pk=self.student.pk).update(is_staff=True)
        self.assertEqual(self.verified(self.student), frozenset())
