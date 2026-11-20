"""D-100 deferred test plan: run ONLY on disposable MySQL after WF-03 implementation.

Do not execute against ctug_workspace. No runtime appointment adapter exists yet;
`patch(...appointment_verified_for)` exercises the contract under synthetic trust.
Tests are authored now, not run under the temporary accelerated workflow.
"""

import json
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import Resolver404, resolve

from apps.access_control import role_assignment
from apps.access_control.models import AccessAuditLog, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.role_management import (
    ORDINARY_ASSIGNMENT_CODE, RoleChangeConflict, RoleChangeDenied, RoleChangeUnavailable,
)
from apps.access_control.test_wf0301_role_assignment import World, configure, roles_of, GATES, API
from apps.accounts.models import Account

GATES_D100 = {**GATES, "WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_ENABLED": True}


@override_settings(ROOT_URLCONF="config.review_sandbox_urls", **GATES_D100)
class OrdinaryRoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()
        cls.tsa = cls.w.account("WF0301-D100-TSA", "Instructor")
        configure("grant-technical-super-admin", cls.tsa)
        cls.student = cls.w.account("WF0301-D100-STUDENT", "Student")
        cls.instructor = cls.w.account("WF0301-D100-INSTR", "Instructor")
        cls.advisor, _ = Role.objects.get_or_create(role_name="SSG Advisor")
        cls.ordinary = Permission.objects.create(
            service=Service.objects.get(service_code="access_control"),
            permission_code=ORDINARY_ASSIGNMENT_CODE, permission_name="Manage ordinary assignments",
            module_name="role_assignments", action_name="ordinary_manage",
        )
        # Disposable S1 simulation only. Never provision a real profile through tests.
        RolePermission.objects.create(
            role=Role.objects.get(role_name="Technical Super Admin"), permission=cls.ordinary,
        )

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(Account.objects.get(pk=self.tsa.pk))
        self.client.cookies[settings.CSRF_COOKIE_NAME] = "d" * 32

    def post(self, target, slug, action, state, client=None):
        return (client or self.client).post(
            f"{API}{target.pk}/ordinary/{slug}/{action}/",
            data=json.dumps({"expected_present": state}), content_type="application/json",
            HTTP_X_CSRFTOKEN="d" * 32,
        )

    def test_verifier_is_default_deny_and_grants_never_create_a_role(self):
        start = AccessAuditLog.objects.count()
        self.assertEqual(self.post(self.student, "treasurer", "assign", False).status_code, 503)
        self.assertEqual(roles_of(self.student), ["Student"])
        self.assertEqual(AccessAuditLog.objects.count(), start)

    def test_mocked_independent_appointment_assigns_then_revokes_with_one_receipt_each(self):
        with patch.object(role_assignment, "appointment_verified_for", return_value=True):
            reply = self.post(self.student, "treasurer", "assign", False)
        self.assertEqual(reply.status_code, 200, reply.content)
        self.assertEqual(reply.json(), {"account_id": self.student.pk, "role": "Treasurer", "assigned": True})
        self.assertEqual(roles_of(self.student), ["Student", "Treasurer"])
        self.assertEqual(AccountRole.objects.get(account=self.student, role__role_name="Treasurer").assigned_by_id,
                         self.tsa.pk)
        self.assertEqual(self.post(self.student, "treasurer", "revoke", True).status_code, 200)
        self.assertEqual(roles_of(self.student), ["Student"])
        self.assertEqual(list(AccessAuditLog.objects.filter(action__startswith="account.role.")
                              .order_by("pk").values_list("action", flat=True)),
                         ["account.role.assign", "account.role.revoke"])

    def test_ssg_advisor_requires_instructor_and_no_other_roles(self):
        with patch.object(role_assignment, "appointment_verified_for", return_value=True):
            self.assertEqual(self.post(self.instructor, "ssg-advisor", "assign", False).status_code, 200)
            self.assertEqual(roles_of(self.instructor), ["Instructor", "SSG Advisor"])
            self.assertEqual(self.post(self.student, "ssg-advisor", "assign", False).json()["error"]["reason"], "not_eligible")
            self.assertEqual(self.post(self.instructor, "treasurer", "assign", False).json()["error"]["reason"], "not_eligible")

    def test_invalid_role_and_tampering_are_refused_without_mutation(self):
        before = list(AccountRole.objects.values_list("pk", "role_id", "account_id"))
        for slug in ("admin", "technical-super-admin", "instructor", "student"):
            self.assertEqual(self.post(self.student, slug, "assign", False).status_code, 404)
        res = self.client.post(f"{API}{self.student.pk}/ordinary/treasurer/assign/",
                               json.dumps({"expected_present": False, "appointment_verified": True}),
                               content_type="application/json", HTTP_X_CSRFTOKEN="d" * 32)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(list(AccountRole.objects.values_list("pk", "role_id", "account_id")), before)

    def test_stale_duplicate_actor_and_gates_are_refused(self):
        self.assertEqual(self.post(self.student, "treasurer", "assign", True).json()["error"]["reason"], "state_changed")
        self.assertEqual(self.post(self.tsa, "ssg-advisor", "assign", False).json()["error"]["reason"], "protected_account")
        with override_settings(WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_ENABLED=False):
            self.assertEqual(self.post(self.student, "treasurer", "assign", False).status_code, 503)
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):
            self.assertEqual(self.post(self.student, "treasurer", "assign", False).status_code, 503)

    def test_ordinary_code_deny_wins_and_school_admin_only_cannot_use_endpoint(self):
        from apps.access_control.models import AccountPermission
        AccountPermission.objects.create(account=self.tsa, permission=self.ordinary, effect="Deny")
        self.assertEqual(self.post(self.student, "treasurer", "assign", False).status_code, 403)
        AccountPermission.objects.filter(account=self.tsa).delete()
        ordinary_admin = self.w.account("WF0301-D100-ADMIN", "Instructor", "Admin")
        session = Client(enforce_csrf_checks=True)
        session.force_login(ordinary_admin)
        session.cookies[settings.CSRF_COOKIE_NAME] = "d" * 32
        self.assertEqual(self.post(self.student, "treasurer", "assign", False, client=session).status_code, 403)

    def test_list_is_s1_only_and_does_not_offer_unverified_assignments(self):
        response = self.client.get(f"{API}ordinary/")
        self.assertEqual(response.status_code, 200)
        rows = {r["account_id"]: r for r in response.json()["results"]}
        self.assertNotIn(self.tsa.pk, rows)
        self.assertIsNone(rows[self.student.pk]["treasurer_action"])
        self.assertIsNone(rows[self.instructor.pk]["advisor_action"])
        self.assertEqual(set(rows[self.student.pk]),
                         {"account_id", "school_id", "full_name", "roles", "treasurer_action", "advisor_action"})

    def test_release_conf_and_nonreview_settings_never_mount_or_activate_ordinary_roles(self):
        with self.assertRaises(Resolver404):
            resolve(f"{API}ordinary/", urlconf="config.urls")
        self.assertEqual(resolve(f"{API}ordinary/", urlconf="config.review_local_urls").url_name,
                         "role-assignments-ordinary-list")
        self.assertFalse(hasattr(settings, "WORKSPACE_APPOINTMENT_EVIDENCE_USER_OVERRIDE"))
