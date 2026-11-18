"""WF-03.01 Assign or revoke account roles (owner-approved staged implementation, 18 Nov 2026).

Run: python manage.py test apps.access_control.test_wf0301_role_assignment --settings=config.test_settings --noinput
Disposable MySQL ONLY; synthetic accounts. The Technical Super Admin is created only through the real
Django-Superuser procedure (framework_roles.configure_role). Test Specification IDs are noted per test.
"""

import json
import threading
from io import StringIO
from types import ModuleType
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import Resolver404, include, path, resolve
from rest_framework.test import APIClient

from apps.access_control import framework_roles, role_assignment
from apps.access_control.catalogue.validation_v2 import validate_manifest
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.role_management import RoleChangeConflict, RoleChangeDenied, RoleChangeUnavailable
from apps.access_control.services import get_effective_permissions, has_permission
from apps.access_control.technical_admin import has_technical_authority
from apps.access_control.writer_boundary import WriterBoundaryUnavailable
from apps.accounts.account_status import status_epoch
from apps.accounts.models import Account, UserProfile

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("WF-03.01 tests require --settings=config.test_settings.")

PASSWORD = "Harbor!Lantern5821"
ROOT = "WF0301-ROOT"
GATES = dict(WORKSPACE_ROLE_CONFIGURATION_OPERATORS=(ROOT,), WORKSPACE_ROLE_ASSIGNMENT_ENABLED=True,
             WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False)
GOVERNANCE = tuple(validate_manifest().data["composition"]["application_super_admin"]["required_effective_permissions"])
API = "/api/v1/admin/role-assignments/"
SCHOOL_CODE = "accounts.registration_requests.read"


def urlconf():
    module = ModuleType("wf0301_test_urlconf")
    module.urlpatterns = [path("api/v1/auth/", include("apps.accounts.urls")),
                          path("api/v1/admin/role-assignments/", include("apps.access_control.role_assignment_urls"))]
    return module


URLCONF = urlconf()


class World:
    def __init__(self, *, services=True):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            assert cursor.fetchone()[0] == settings.REGISTRATION_TEST_DATABASE
        if services:
            self.accounts = Service.objects.create(service_code="accounts", service_name="Accounts")
            Service.objects.create(service_code="access_control", service_name="Access Control")
            # A School Admin operational code so inheritance through Admin is observable.
            self.school = Permission.objects.create(service=self.accounts, permission_code=SCHOOL_CODE,
                                                    permission_name="Review", module_name="registration_requests",
                                                    action_name="read")
        self.roles = {n: Role.objects.get_or_create(role_name=n, defaults={"is_active": True})[0]
                      for n in ("Student", "Instructor", "Treasurer", "Admin")}
        if services:
            RolePermission.objects.create(role=self.roles["Admin"], permission=self.school)
        self.root = Account.objects.create_superuser(school_id=ROOT, password=PASSWORD)

    def account(self, school_id, *roles, status="Approved", active=True, **flags):
        account = Account.objects.create_user(school_id=school_id, password=PASSWORD)
        Account.objects.filter(pk=account.pk).update(request_status=status, is_active=active, **flags)
        UserProfile.objects.create(account=account, first_name="Ana", last_name=school_id.title())
        for role in roles:
            AccountRole.objects.create(account=account, role=self.roles[role] if role in self.roles
                                       else Role.objects.get(role_name=role))
        return Account.objects.get(pk=account.pk)


def configure(operation, target, *, operator=ROOT, password=PASSWORD, confirmation=None):
    return framework_roles.configure_role(
        operation=operation, operator_school_id=operator, operator_password=password, target_id=target.pk,
        confirmation=framework_roles.confirmation_for(operation, target.pk) if confirmation is None else confirmation)


def roles_of(account):
    return sorted(AccountRole.objects.filter(account=account).values_list("role__role_name", flat=True))


def state():
    return (sorted(AccountRole.objects.values_list("account_id", "role_id")), Role.objects.count(), Permission.objects.count(),
            RolePermission.objects.count(), AccessAuditLog.objects.count())


@override_settings(**GATES)
class SuperuserProcedureTests(TestCase):
    """Stage A: the Django-Superuser-exclusive protected procedure."""

    @classmethod
    def setUpTestData(cls):
        cls.w = World()
        cls.instructor = cls.w.account("0030101", "Instructor")
        cls.instructor2 = cls.w.account("0030102", "Instructor")
        cls.student = cls.w.account("7300101", "Student")
        cls.legacy = cls.w.account("WF0301-LEGACY", "Admin")

    def refused(self, exc_type, operation, target, **kwargs):
        before = state()
        with self.assertRaises(exc_type) as caught:
            configure(operation, target, **kwargs)
        self.assertEqual(state(), before)
        return caught.exception

    def test_tc024_grant_technical_super_admin_creates_the_exact_catalogue_profile(self):
        result = configure("grant-technical-super-admin", self.instructor)
        self.assertEqual(result, {"account_id": self.instructor.pk, "operation": "grant-technical-super-admin"})
        self.assertEqual(roles_of(self.instructor), ["Admin", "Instructor", "Technical Super Admin"])  # Instructor kept
        technical = Role.objects.get(role_name="Technical Super Admin")
        self.assertTrue(technical.is_active)
        definitions = {p["permission_code"]: p for p in validate_manifest().data["permissions"]}
        for code in GOVERNANCE:
            row = Permission.objects.get(permission_code=code)
            self.assertEqual((row.service.service_code, row.permission_name, row.module_name, row.action_name, row.description),
                             ("access_control", definitions[code]["permission_name"], definitions[code]["module_name"],
                              definitions[code]["action_name"], definitions[code]["description"]))
            self.assertEqual(list(RolePermission.objects.filter(permission=row).values_list("role__role_name", "is_active")),
                             [("Technical Super Admin", True)])
            self.assertTrue(has_technical_authority(self.instructor, code))
        # Inheritance: School Admin operations through Admin; no framework flags changed.
        self.assertTrue(has_permission(self.instructor, SCHOOL_CODE))
        target = Account.objects.get(pk=self.instructor.pk)
        self.assertFalse(target.is_staff or target.is_superuser)
        audits = list(AccessAuditLog.objects.order_by("pk").values_list("action", "actor_account_id"))
        self.assertEqual([a for a, _ in audits], ["framework.role.create"] + ["framework.permission.create"] * 6
                         + ["framework.role_binding.create"] * 6 + ["framework.role.assign"] * 2)
        self.assertEqual({actor for _, actor in audits}, {self.w.root.pk})
        assigns = AccessAuditLog.objects.filter(action="framework.role.assign").order_by("pk")
        self.assertEqual([a.role.role_name for a in assigns], ["Admin", "Technical Super Admin"])
        self.assertEqual(assigns[1].new_value["account_id"], self.instructor.pk)
        self.assertIsNone(assigns[1].old_value)
        # A second grant reuses and verifies the profile; nothing is recreated.
        configure("grant-technical-super-admin", self.instructor2)
        self.assertEqual(Permission.objects.filter(permission_code__in=GOVERNANCE).count(), 6)
        self.assertEqual(AccessAuditLog.objects.filter(action__startswith="framework.permission").count(), 6)
        self.assertEqual(Role.objects.filter(role_name="Technical Super Admin").count(), 1)

    def test_tc026_tc027_only_a_designated_reauthenticated_framework_superuser_may_act(self):
        staff = self.w.account("WF0301-STAFF", is_staff=True)
        root_with_role = Account.objects.create_superuser(school_id="WF0301-ROOT2", password=PASSWORD)
        AccountRole.objects.create(account=root_with_role, role=self.w.roles["Instructor"])
        for kwargs in ({"password": "wrong-password"}, {"operator": "WF0301-UNKNOWN"}, {"operator": staff.school_id},
                       {"operator": self.instructor.school_id}, {"password": ""}):
            with self.subTest(kwargs=kwargs):
                self.refused(RoleChangeDenied, "grant-technical-super-admin", self.instructor, **kwargs)
        with override_settings(WORKSPACE_ROLE_CONFIGURATION_OPERATORS=(ROOT, "WF0301-ROOT2")):
            self.refused(RoleChangeDenied, "grant-technical-super-admin", self.instructor, operator="WF0301-ROOT2")
        with override_settings(WORKSPACE_ROLE_CONFIGURATION_OPERATORS=()):
            self.refused(RoleChangeDenied, "grant-technical-super-admin", self.instructor)  # nobody is designated
        self.refused(RoleChangeUnavailable, "grant-technical-super-admin", self.instructor, confirmation="yes")
        self.refused(RoleChangeUnavailable, "grant-technical-super-admin", self.instructor,
                     confirmation=framework_roles.confirmation_for("grant-technical-super-admin", self.instructor2.pk))
        with self.assertRaises(RoleChangeUnavailable):
            framework_roles.configure_role(operation="grant-everything", operator_school_id=ROOT, operator_password=PASSWORD,
                                           target_id=self.instructor.pk, confirmation="x")

    def test_tc033_targets_must_be_active_approved_instructors(self):
        pending = self.w.account("0030103", "Instructor", status="Pending", active=False)
        inactive = self.w.account("0030104", "Instructor", active=False)
        framework = self.w.account("0030105", "Instructor", is_staff=True, is_superuser=True)
        for target in (pending, inactive, framework):
            with self.subTest(target=target.school_id):
                self.refused(RoleChangeDenied, "grant-technical-super-admin", target)
        self.assertEqual(self.refused(RoleChangeConflict, "grant-technical-super-admin", self.student).reason, "not_eligible")
        self.assertEqual(self.refused(RoleChangeConflict, "grant-school-admin", self.student).reason, "not_eligible")
        self.assertEqual(self.refused(RoleChangeConflict, "grant-technical-super-admin", self.w.root).reason, "protected_account")
        configure("grant-technical-super-admin", self.instructor)
        self.assertEqual(self.refused(RoleChangeConflict, "grant-technical-super-admin", self.instructor).reason, "state_changed")

    def test_tc025_tc037_revocation_keeps_admin_and_instructor_and_never_strands_the_last_operator(self):
        configure("grant-technical-super-admin", self.instructor)
        self.assertEqual(self.refused(RoleChangeConflict, "revoke-technical-super-admin", self.instructor).reason,
                         "last_technical_super_admin")
        configure("grant-technical-super-admin", self.instructor2)
        epoch = status_epoch(self.instructor.pk)
        configure("revoke-technical-super-admin", self.instructor)
        self.assertEqual(roles_of(self.instructor), ["Admin", "Instructor"])
        self.assertFalse(has_technical_authority(self.instructor, "access_control.admin_assignments.manage"))
        self.assertTrue(has_permission(self.instructor, SCHOOL_CODE))  # still a School Admin
        revoke = AccessAuditLog.objects.filter(action="framework.role.revoke").get()
        self.assertEqual((revoke.actor_account_id, revoke.target_account_id, revoke.role.role_name, revoke.new_value),
                         (self.w.root.pk, self.instructor.pk, "Technical Super Admin", None))
        self.assertGreater(status_epoch(self.instructor.pk), epoch)
        self.assertEqual(self.refused(RoleChangeConflict, "revoke-technical-super-admin", self.instructor).reason, "state_changed")

    def test_tc018_tc022_superuser_school_admin_grant_and_revoke_rules(self):
        configure("grant-school-admin", self.instructor)
        self.assertEqual(roles_of(self.instructor), ["Admin", "Instructor"])
        configure("revoke-school-admin", self.instructor)
        self.assertEqual(roles_of(self.instructor), ["Instructor"])
        self.assertEqual(self.refused(RoleChangeConflict, "revoke-school-admin", self.instructor).reason, "state_changed")
        # The legacy Admin-only operator (D-94) and Technical Super Admin holders are protected here.
        self.assertEqual(self.refused(RoleChangeConflict, "revoke-school-admin", self.legacy).reason, "protected_account")
        configure("grant-technical-super-admin", self.instructor2)
        self.assertEqual(self.refused(RoleChangeConflict, "revoke-school-admin", self.instructor2).reason, "protected_account")

    def test_tc028_a_deny_on_a_governance_code_refuses_the_grant_and_rolls_everything_back(self):
        before = state()
        configure("grant-technical-super-admin", self.instructor2)  # creates the profile
        denied = Permission.objects.get(permission_code="access_control.audit.read")
        AccountPermission.objects.create(account=self.instructor, permission=denied, effect="Deny")
        mid = state()
        with self.assertRaises(RoleChangeConflict) as caught:
            configure("grant-technical-super-admin", self.instructor)
        self.assertEqual(caught.exception.reason, "not_eligible")
        self.assertEqual(state(), mid)
        self.assertEqual(roles_of(self.instructor), ["Instructor"])
        self.assertNotEqual(before, mid)

    def test_tc029_audit_failure_rolls_back_the_whole_first_grant(self):
        original = framework_roles.record_access_audit_receipt
        calls = {"n": 0}

        def failing(**kwargs):
            calls["n"] += 1
            if calls["n"] == 14:  # after the role, permission and binding receipts: the Admin assignment
                raise RuntimeError("audit store unavailable")
            return original(**kwargs)
        before = state()
        with patch.object(framework_roles, "record_access_audit_receipt", side_effect=failing):
            with self.assertRaises(RuntimeError):
                configure("grant-technical-super-admin", self.instructor)
        self.assertEqual(state(), before)
        self.assertFalse(Role.objects.filter(role_name="Technical Super Admin").exists())
        self.assertFalse(Permission.objects.filter(permission_code__in=GOVERNANCE).exists())

    def test_inconsistent_governance_state_is_refused_never_repaired(self):
        configure("grant-technical-super-admin", self.instructor2)
        Permission.objects.filter(permission_code="access_control.audit.read").update(permission_name="Changed")
        self.refused(RoleChangeUnavailable, "grant-technical-super-admin", self.instructor)
        Permission.objects.filter(permission_code="access_control.audit.read").update(
            permission_name={p["permission_code"]: p for p in validate_manifest().data["permissions"]}["access_control.audit.read"]["permission_name"])
        RolePermission.objects.filter(permission__permission_code="access_control.audit.read").update(is_active=False)
        self.refused(RoleChangeUnavailable, "grant-technical-super-admin", self.instructor)

    def test_writer_gate_and_database_guards_fail_closed(self):
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):
            self.refused(WriterBoundaryUnavailable, "grant-technical-super-admin", self.instructor)
        with override_settings(REGISTRATION_TEST_DATABASE="ctug_workspace"):
            self.refused(RoleChangeUnavailable, "grant-technical-super-admin", self.instructor)
        with patch.dict("os.environ", {"DJANGO_SETTINGS_MODULE": "config.settings"}):
            self.refused(RoleChangeUnavailable, "grant-technical-super-admin", self.instructor)
        self.assertIs(framework_roles.DEVELOPMENT_DATABASE_APPROVED, False)

    def test_tc009_the_command_never_takes_credentials_from_arguments(self):
        out = StringIO()
        call_command("configure_workspace_roles", operation="grant-technical-super-admin",
                     target_account_id=self.instructor.pk, stdout=out)
        self.assertIn(f"--confirm WF-03.01:grant-technical-super-admin:{self.instructor.pk}", out.getvalue())
        with self.assertRaises(CommandError):
            call_command("configure_workspace_roles", operation="grant-technical-super-admin",
                         target_account_id=self.instructor.pk, apply=True, confirm="wrong", stdout=StringIO())
        with patch("sys.stdin.isatty", return_value=False), self.assertRaises(CommandError):
            call_command("configure_workspace_roles", operation="grant-technical-super-admin",
                         target_account_id=self.instructor.pk, apply=True,
                         confirm=f"WF-03.01:grant-technical-super-admin:{self.instructor.pk}", stdout=StringIO())
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value=ROOT), \
                patch("getpass.getpass", return_value=PASSWORD):
            out = StringIO()
            call_command("configure_workspace_roles", operation="grant-technical-super-admin",
                         target_account_id=self.instructor.pk, apply=True,
                         confirm=f"WF-03.01:grant-technical-super-admin:{self.instructor.pk}", stdout=out)
        self.assertNotIn(PASSWORD, out.getvalue())
        self.assertIn("Technical Super Admin", roles_of(self.instructor))


@override_settings(ROOT_URLCONF=URLCONF, **GATES)
class TechnicalSuperAdminAssignmentTests(TestCase):
    """Stage B: School Admin assignment and revocation by an effective Technical Super Admin."""

    @classmethod
    def setUpTestData(cls):
        cls.w = World()
        cls.tsa = cls.w.account("0030201", "Instructor")
        configure("grant-technical-super-admin", cls.tsa)
        cls.instructor = cls.w.account("0030202", "Instructor")
        cls.admin = cls.w.account("0030203", "Instructor", "Admin")
        cls.student = cls.w.account("7300201", "Student")
        cls.legacy = cls.w.account("WF0301-LEGACY2", "Admin")

    def setUp(self):
        cache.clear()
        self.client = self.signed_in(self.tsa)

    @staticmethod
    def signed_in(account):
        client = Client(enforce_csrf_checks=True)
        client.force_login(account)
        client.cookies[settings.CSRF_COOKIE_NAME] = "e" * 32
        return client

    def post(self, target_id, action, body, client=None):
        return (client or self.client).post(f"{API}{target_id}/school-admin/{action}/", data=json.dumps(body),
                                           content_type="application/json", HTTP_X_CSRFTOKEN="e" * 32)

    def test_tc021_assign_keeps_instructor_audits_and_recalculates_permissions(self):
        self.assertFalse(has_permission(self.instructor, SCHOOL_CODE))
        response = self.post(self.instructor.pk, "assign", {"expected_present": False})
        self.assertEqual((response.status_code, response.json()),
                         (200, {"account_id": self.instructor.pk, "role": "Admin", "assigned": True}))
        self.assertEqual(roles_of(self.instructor), ["Admin", "Instructor"])
        self.assertTrue(has_permission(self.instructor, SCHOOL_CODE))
        self.assertFalse(has_technical_authority(self.instructor, "access_control.admin_assignments.manage"))
        audit = AccessAuditLog.objects.filter(action="account.role.assign").get()
        assignment = AccountRole.objects.get(account=self.instructor, role__role_name="Admin")
        self.assertEqual((audit.actor_account_id, audit.target_account_id, audit.role.role_name, audit.old_value,
                          audit.new_value, audit.reason),
                         (self.tsa.pk, self.instructor.pk, "Admin", None,
                          {"account_id": self.instructor.pk, "role_id": self.w.roles["Admin"].pk,
                           "account_role_id": assignment.pk}, "assignment_change"))
        self.assertEqual(assignment.assigned_by_id, self.tsa.pk)
        stale = self.post(self.instructor.pk, "assign", {"expected_present": False})
        self.assertEqual((stale.status_code, stale.json()["error"]["reason"]), (409, "state_changed"))

    def test_tc022_revoke_keeps_instructor_and_protects_operators(self):
        response = self.post(self.admin.pk, "revoke", {"expected_present": True})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(roles_of(self.admin), ["Instructor"])
        self.assertFalse(has_permission(self.admin, SCHOOL_CODE))
        audit = AccessAuditLog.objects.filter(action="account.role.revoke").get()
        self.assertEqual((audit.new_value, audit.old_value["account_id"]), (None, self.admin.pk))
        for target, reason in ((self.legacy, "protected_account"), (self.student, "state_changed")):
            with self.subTest(target=target.school_id):
                cache.clear()
                r = self.post(target.pk, "revoke", {"expected_present": True})
                self.assertEqual((r.status_code, r.json()["error"]["reason"]), (409, reason))
        other_tsa = self.w.account("0030204", "Instructor")
        configure("grant-technical-super-admin", other_tsa)
        cache.clear()
        r = self.post(other_tsa.pk, "revoke", {"expected_present": True})
        self.assertEqual((r.status_code, r.json()["error"]["reason"]), (409, "protected_account"))  # demotion is superuser-only
        self.assertIn("Admin", roles_of(self.legacy))

    def test_tc023_tc028_no_technical_super_admin_elevation_self_change_or_tampering(self):
        r = self.post(self.tsa.pk, "revoke", {"expected_present": True})
        self.assertEqual((r.status_code, r.json()["error"]["reason"]), (409, "protected_account"))
        for body in ({}, {"expected_present": "false"}, {"expected_present": False, "role_id": 99},
                     {"role": "Technical Super Admin", "expected_present": False}, [False]):
            with self.subTest(body=body):
                cache.clear()
                self.assertEqual(self.post(self.instructor.pk, "assign", body).status_code, 400)
        cache.clear()
        r = self.post(self.student.pk, "assign", {"expected_present": False})
        self.assertEqual((r.status_code, r.json()["error"]["reason"]), (409, "not_eligible"))
        self.assertFalse(AccountRole.objects.filter(account=self.student, role__role_name="Admin").exists())
        # There is no route that grants or revokes Technical Super Admin at all.
        for suffix in ("technical-super-admin/assign/", "roles/assign/"):
            with self.subTest(suffix=suffix), self.assertRaises(Resolver404):
                resolve(f"{API}{self.instructor.pk}/{suffix}", urlconf=URLCONF)

    def test_tc004_tc020_school_admin_and_others_are_refused(self):
        anonymous = Client(enforce_csrf_checks=True)
        self.assertEqual(anonymous.get(API).status_code, 401)
        for account in (self.admin, self.legacy, self.instructor, self.student):
            with self.subTest(account=account.school_id):
                cache.clear()
                client = self.signed_in(account)
                self.assertEqual(client.get(API).status_code, 403)
                self.assertEqual(self.post(self.instructor.pk, "assign", {"expected_present": False}, client=client).status_code, 403)
        with self.assertRaises(RoleChangeDenied):
            role_assignment.assign_school_admin(actor=self.admin, target_id=self.instructor.pk)
        framework = self.signed_in(self.w.root)
        self.assertEqual(framework.get(API).status_code, 401)  # TC-027: no Workspace API superuser bypass
        self.assertFalse(AccountRole.objects.filter(account=self.instructor, role__role_name="Admin").exists())

    def test_tc032_deny_service_role_and_gate_restrictions(self):
        manage = Permission.objects.get(permission_code="access_control.admin_assignments.manage")
        AccountPermission.objects.create(account=self.tsa, permission=manage, effect="Deny")
        self.assertEqual(self.client.get(API).status_code, 403)
        self.assertEqual(self.post(self.instructor.pk, "assign", {"expected_present": False}).status_code, 403)
        AccountPermission.objects.filter(account=self.tsa).delete()
        cache.clear()
        Service.objects.filter(service_code="access_control").update(is_active=False)
        self.assertEqual(self.client.get(API).status_code, 503)
        Service.objects.filter(service_code="access_control").update(is_active=True)
        Role.objects.filter(role_name="Technical Super Admin").update(is_active=False)
        cache.clear()
        self.assertEqual(self.client.get(API).status_code, 403)
        Role.objects.filter(role_name="Technical Super Admin").update(is_active=True)
        cache.clear()
        with override_settings(WORKSPACE_ROLE_ASSIGNMENT_ENABLED=False):
            self.assertEqual(self.client.get(API).status_code, 503)
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):
            self.assertEqual(self.post(self.instructor.pk, "assign", {"expected_present": False}).status_code, 503)
        Account.objects.filter(pk=self.tsa.pk).update(is_active=False)
        cache.clear()
        self.assertEqual(self.client.get(API).status_code, 401)
        self.assertFalse(AccountRole.objects.filter(account=self.instructor, role__role_name="Admin").exists())

    def test_list_is_minimized_and_hints_follow_the_rules(self):
        response = self.client.get(API)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        rows = {r["account_id"]: r for r in response.json()["results"]}
        self.assertNotIn(self.tsa.pk, rows)  # never the actor
        self.assertNotIn(self.student.pk, rows)  # neither Instructor nor Admin
        self.assertNotIn(self.w.root.pk, rows)  # never a framework account
        self.assertEqual(set(rows[self.instructor.pk]), {"account_id", "school_id", "full_name", "roles",
                                                          "school_admin_action", "restriction"})
        self.assertEqual((rows[self.instructor.pk]["school_admin_action"], rows[self.admin.pk]["school_admin_action"],
                          rows[self.legacy.pk]["restriction"]), ("assign", "revoke", "legacy_admin"))
        for forbidden in ("password", "email", PASSWORD):
            self.assertNotIn(forbidden, response.content.decode())
        cache.clear()
        self.assertEqual([r["account_id"] for r in self.client.get(API, {"q": "0030202"}).json()["results"]], [self.instructor.pk])
        cache.clear()
        self.assertEqual(self.client.get(API, {"role": "Admin"}).status_code, 400)

    def test_tc029_audit_failure_rolls_back_the_assignment(self):
        with patch.object(role_assignment, "record_access_audit_receipt", side_effect=RuntimeError("audit down")):
            response = self.post(self.instructor.pk, "assign", {"expected_present": False})
        self.assertIn(response.status_code, (500, 503))
        self.assertEqual(roles_of(self.instructor), ["Instructor"])
        self.assertFalse(AccessAuditLog.objects.filter(action="account.role.assign").exists())

    def test_release_surface_is_isolated_and_reported(self):
        from apps.access_control.management.commands.init_registration_review_metadata_local_dev import unexpected_review_routes
        for conf in ("config.urls", "config.review_local_urls", "config.review_sandbox_urls"):
            with self.subTest(conf=conf), self.assertRaises(Resolver404):
                resolve(API, urlconf=conf)
        self.assertEqual(len(unexpected_review_routes(URLCONF)), 3)
        self.assertEqual(unexpected_review_routes("config.urls"), [])
        for name in ("config.settings", "config.review_local_settings", "config.review_sandbox_settings"):
            source = open(f"config/{name.split('.')[1]}.py", encoding="utf-8").read()
            self.assertNotIn("WORKSPACE_ROLE_ASSIGNMENT_ENABLED", source)
            self.assertNotIn("WORKSPACE_ROLE_CONFIGURATION_OPERATORS", source)


@override_settings(**GATES)
class RoleChangeSessionTests(TestCase):
    """Stage C (TC-031): every role elevation or removal ends earlier sessions; none revives."""

    @classmethod
    def setUpTestData(cls):
        cls.w = World()
        cls.tsa = cls.w.account("0030301", "Instructor")
        configure("grant-technical-super-admin", cls.tsa)
        cls.user = cls.w.account("0030302", "Instructor")
        cls.bystander = cls.w.account("0030303", "Instructor")

    def setUp(self):
        cache.clear()

    def browser(self, account):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        response = client.post("/api/v1/auth/login/", {"school_id": account.school_id, "password": PASSWORD},
                               format="json", HTTP_X_CSRFTOKEN=token)
        client.login_status = response.status_code
        return client

    @staticmethod
    def signed_in(client):
        return client.get("/api/v1/auth/session/").json()["authenticated"]

    def assign(self):
        return role_assignment.assign_school_admin(actor=self.tsa, target_id=self.user.pk, expected_present=False)

    def revoke(self):
        return role_assignment.revoke_school_admin(actor=self.tsa, target_id=self.user.pk, expected_present=True)

    def test_accounts_without_changes_keep_djangos_own_session_hash(self):
        self.assertEqual(status_epoch(self.bystander.pk), 0)
        self.assertEqual(self.bystander.get_session_auth_hash(), AbstractBaseUser._get_session_auth_hash(self.bystander))

    def test_elevation_and_revocation_end_sessions_and_re_adding_never_revives_them(self):
        first, second, other = self.browser(self.user), self.browser(self.user), self.browser(self.bystander)
        self.assertTrue(all(c.login_status == 200 for c in (first, second, other)))
        self.assertTrue(self.signed_in(first) and self.signed_in(second))
        self.assertNotIn(SCHOOL_CODE, first.get("/api/v1/auth/session/").json()["permissions"])
        self.assign()  # elevation needs a fresh sign-in
        self.assertFalse(self.signed_in(first))
        self.assertFalse(self.signed_in(second))
        self.assertTrue(self.signed_in(other))
        elevated = self.browser(self.user)
        self.assertTrue(self.signed_in(elevated))
        self.assertIn(SCHOOL_CODE, elevated.get("/api/v1/auth/session/").json()["permissions"])
        self.revoke()
        self.assertFalse(self.signed_in(elevated))
        self.assign()  # re-adding the role revives none of the earlier sessions
        for client in (first, second, elevated):
            self.assertFalse(self.signed_in(client))
        fresh = self.browser(self.user)
        self.assertTrue(self.signed_in(fresh))

    def test_superuser_grant_and_revoke_end_the_targets_sessions(self):
        client = self.browser(self.user)
        self.assertTrue(self.signed_in(client))
        configure("grant-technical-super-admin", self.user)
        self.assertFalse(self.signed_in(client))
        fresh = self.browser(self.user)
        self.assertIn("access_control.admin_assignments.manage", fresh.get("/api/v1/auth/session/").json()["permissions"])
        configure("revoke-technical-super-admin", self.user)
        self.assertFalse(self.signed_in(fresh))

    def test_suspension_guarantees_are_unchanged(self):
        from apps.accounts.account_status import ACTIVATE_ACTION, SUSPEND_ACTION
        self.assign()
        after_role = status_epoch(self.user.pk)
        log = AccessAuditLog.objects.create(actor_account=self.tsa, target_account=self.user, action=SUSPEND_ACTION,
                                            reason="account_status_change")
        self.assertEqual(status_epoch(self.user.pk), log.pk)
        AccessAuditLog.objects.create(actor_account=self.tsa, target_account=self.user, action=ACTIVATE_ACTION,
                                      reason="account_status_change")
        self.assertEqual(status_epoch(self.user.pk), log.pk)  # reactivation does not move the epoch
        self.assertGreater(log.pk, after_role)


@override_settings(ROOT_URLCONF=URLCONF, **GATES)
class RoleChangeConcurrencyTests(TransactionTestCase):
    """TC-029: concurrent changes decide once; the last School Admin cannot be removed twice over."""

    def tearDown(self):
        connections.close_all()

    def race(self, *calls):
        results, start = [], threading.Barrier(len(calls))

        def run(call):
            try:
                start.wait(5)
                results.append(("ok", call()))
            except RoleChangeConflict as exc:
                results.append(("conflict", exc.reason))
            except Exception as exc:  # pragma: no cover - reported
                results.append(("error", type(exc).__name__))
            finally:
                connections.close_all()
        threads = [threading.Thread(target=run, args=(c,)) for c in calls]
        for t in threads:
            t.start()
        for t in threads:
            t.join(20)
        return sorted(results, key=lambda r: r[0])

    def test_two_assignments_of_the_same_role_decide_once(self):
        w = World()
        tsa = w.account("0030401", "Instructor")
        configure("grant-technical-super-admin", tsa)
        target = w.account("0030402", "Instructor")
        call = lambda: role_assignment.assign_school_admin(actor=tsa, target_id=target.pk, expected_present=False)  # noqa: E731
        results = self.race(call, call)
        self.assertEqual([r[0] for r in results], ["conflict", "ok"], results)
        self.assertEqual(AccountRole.objects.filter(account=target, role__role_name="Admin").count(), 1)
        self.assertEqual(AccessAuditLog.objects.filter(action="account.role.assign").count(), 1)

    def test_concurrent_removals_never_leave_no_school_admin(self):
        w = World()
        first, second = w.account("0030403", "Instructor", "Admin"), w.account("0030404", "Instructor", "Admin")
        calls = [lambda t=t: configure("revoke-school-admin", t) for t in (first, second)]
        results = self.race(*calls)
        self.assertEqual(sorted(r[0] for r in results), ["conflict", "ok"], results)
        self.assertEqual([r[1] for r in results if r[0] == "conflict"], ["last_school_admin"])
        self.assertEqual(AccountRole.objects.filter(role__role_name="Admin").count(), 1)


class ProtectedCompatibilityTests(TransactionTestCase):
    """TC-035 / TC-030: P4 compensation refuses while the governance profile exists (D-85, see test_wf0301_d85_p3b_compatibility); the old
    executor bootstrap stays dormant; catalogue v2 is unchanged and still validates."""

    def tearDown(self):
        connections.close_all()

    def test_p4_compensation_refuses_after_a_technical_super_admin_grant(self):
        from apps.access_control.management.commands import (
            exercise_registration_review_activation_recovery_test_only as p3b,
            init_registration_review_inactive_bindings_local_dev as p2,
            init_registration_review_metadata_local_dev as p1,
            release_registration_review_local_dev_p4 as p4,
            report_registration_review_release_gates_p3e as p3e,
        )
        w = World(services=False)
        actor = w.account("WF0301-P4-ADMIN", "Admin")
        call_command("init_registration_review_metadata_local_dev", apply=True, actor_account_id=actor.pk,
                     confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO())
        call_command("init_registration_review_inactive_bindings_local_dev", apply=True, actor_account_id=actor.pk,
                     confirm_local_dev_phase2=p2.TEST_CONFIRM, stdout=StringIO())
        scope = str(actor.pk)
        fingerprint = p3e.inspect_release_gates(actor_account_id=actor.pk, expected_admin_account_ids=scope)["fingerprint"]
        with patch.object(p4, "_local_target", return_value=connections["default"]):
            self.assertEqual(p4._perform(mode="activate", actor_id=actor.pk, expected_ids=scope, fingerprint=fingerprint,
                                         confirmation=p4.LOCAL_CONFIRM), "LOCAL_ACTIVATED")
        instructor = w.account("0030501", "Instructor")
        with override_settings(**GATES):  # only the superuser procedure; P1/P2/P4 run under the real test settings
            configure("grant-technical-super-admin", instructor)
        before = state()
        for scope_ids in (scope, ",".join(str(i) for i in sorted([actor.pk, instructor.pk]))):
            with self.subTest(scope=scope_ids), patch.object(p4, "_local_target", return_value=connections["default"]):
                with self.assertRaises((p4.LocalReleaseRefused, p3b.ActivationExerciseRefused)):
                    p4._perform(mode="compensate", actor_id=actor.pk, expected_ids=scope_ids, fingerprint=None,
                                confirmation=p4.LOCAL_CONFIRM)
        self.assertEqual(state(), before)
        self.assertTrue(Service.objects.filter(service_code="access_control", is_active=True).exists())

    def test_old_bootstrap_paths_stay_dormant_and_the_catalogue_is_unchanged(self):
        from apps.access_control.executor import client
        from apps.access_control.writer_boundary import RELEASE_STATUS
        self.assertEqual(RELEASE_STATUS, "BLOCKED")
        self.assertFalse(client.enabled())
        data = validate_manifest().data
        bound = {b["permission_code"]: b["role_name"] for b in data["default_bindings"]
                 if b["permission_code"] == "access_control.role_assignments.ordinary.manage"}
        self.assertEqual(bound, {"access_control.role_assignments.ordinary.manage": "Admin"})  # v2.1 pending (D-89)
        self.assertFalse(hasattr(role_assignment, "assign_ordinary_role"))  # no Treasurer/SSG Advisor path yet
