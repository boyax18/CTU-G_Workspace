"""WF-02.05 Activate or deactivate an existing account (stage 1).

Run: python manage.py test apps.accounts.test_wf0205_account_status --settings=config.test_settings --noinput
Disposable MySQL only; isolated synthetic accounts; the status API is reached through its
isolated URLconf and the session checks through config.urls (login and session endpoints).
"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from types import ModuleType
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import Resolver404, include, path, resolve
from rest_framework.test import APIClient

from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.writer_boundary import WriterBoundaryUnavailable

from . import account_status, session_auth
from .account_status import (
    AccountStatusConflict, AccountStatusDenied, AccountStatusUnavailable, activate_account, status_epoch, suspend_account,
)
from .models import Account, UserProfile

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("WF-02.05 tests require --settings=config.test_settings.")

PASSWORD = "Harbor!Lantern5821"
GATE = dict(WORKSPACE_ACCOUNT_STATUS_ENABLED=True, WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False)
BASE = "/"


def verify_database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
            raise ImproperlyConfigured("Refusing WF-02.05 fixtures on an unexpected database.")


class World:
    """Services, the three catalogue permissions bound to Admin, roles and synthetic accounts."""

    def __init__(self):
        verify_database()
        self.accounts_service = Service.objects.create(service_code="accounts", service_name="Accounts")
        Service.objects.create(service_code="access_control", service_name="Access Control")
        self.roles = {n: Role.objects.create(role_name=n) for n in
                      ("Student", "Instructor", "Treasurer", "Admin", "Technical Super Admin")}
        self.perms = {}
        for action in ("read", "suspend", "activate"):
            self.perms[action] = Permission.objects.create(
                service=self.accounts_service, permission_code=f"accounts.school_accounts.{action}",
                permission_name=f"School accounts {action}", module_name="school_accounts", action_name=action)
            RolePermission.objects.create(role=self.roles["Admin"], permission=self.perms[action])
        self.reviewer = self.account("WF0205-ADMIN", "Admin")

    def account(self, school_id, *roles, status="Approved", active=True, requested="Student", **flags):
        account = Account.objects.create_user(school_id=school_id, password=PASSWORD,
                                              requested_role=self.roles[requested])
        Account.objects.filter(pk=account.pk).update(request_status=status, is_active=active, **flags)
        UserProfile.objects.create(account=account, first_name="Ana", last_name=school_id.title())
        for role in roles:
            AccountRole.objects.create(account=account, role=self.roles[role])
        return Account.objects.get(pk=account.pk)


def snapshot(account):
    """Everything WF-02.05 must leave untouched (all columns but is_active, plus roles and overrides)."""
    row = Account.objects.values().get(pk=account.pk)
    row.pop("is_active")
    return (row,
            sorted(AccountRole.objects.filter(account=account).values_list("role_id", "assigned_by_id")),
            sorted(AccountPermission.objects.filter(account=account).values_list("permission_id", "effect", "is_active")),
            UserProfile.objects.values().get(account=account))


@override_settings(**GATE)
class AccountStatusServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()

    def suspend(self, target, expected=True, actor=None):
        return suspend_account(actor=actor or self.w.reviewer, target_id=target.pk, expected_active=expected)

    def activate(self, target, expected=False, actor=None):
        return activate_account(actor=actor or self.w.reviewer, target_id=target.pk, expected_active=expected)

    def conflict(self, reason, fn, *args, **kwargs):
        before = AccessAuditLog.objects.count()
        with self.assertRaises(AccountStatusConflict) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(AccessAuditLog.objects.count(), before)

    def test_student_and_instructor_round_trip_change_only_is_active(self):
        for school_id, role, requested in (("WF0205-S", "Student", "Student"), ("WF0205-I", "Instructor", "Instructor")):
            with self.subTest(role=role):
                target = self.w.account(school_id, role, requested=requested)
                AccountPermission.objects.create(account=target, permission=self.w.perms["read"], effect="Deny")
                before = snapshot(target)
                self.assertEqual(self.suspend(target), {"account_id": target.pk, "is_active": False})
                self.assertFalse(Account.objects.get(pk=target.pk).is_active)
                self.assertEqual(snapshot(target), before)
                self.assertEqual(self.activate(target), {"account_id": target.pk, "is_active": True})
                self.assertTrue(Account.objects.get(pk=target.pk).is_active)
                self.assertEqual(snapshot(target), before)
                audits = list(AccessAuditLog.objects.filter(target_account=target).order_by("pk"))
                self.assertEqual([a.action for a in audits], ["account.status.suspend", "account.status.activate"])
                for audit, was in zip(audits, (True, False)):
                    self.assertEqual((audit.actor_account_id, audit.reason, audit.role_id),
                                     (self.w.reviewer.pk, "account_status_change", None))
                    self.assertEqual(audit.old_value, {"account_id": target.pk, "request_status": "Approved", "is_active": was})
                    self.assertEqual(audit.new_value, {"account_id": target.pk, "request_status": "Approved", "is_active": not was})
                    self.assertIsNotNone(audit.created_at)

    def test_treasurer_only_and_student_treasurer_accounts_are_supported(self):
        for school_id, roles in (("WF0205-T", ("Treasurer",)), ("WF0205-ST", ("Student", "Treasurer"))):
            with self.subTest(roles=roles):
                target = self.w.account(school_id, *roles)
                self.suspend(target)
                self.activate(target)
                self.assertTrue(Account.objects.get(pk=target.pk).is_active)
                self.assertEqual(AccountRole.objects.filter(account=target).count(), len(roles))

    def test_no_active_role_can_be_deactivated_but_never_reactivated(self):
        nobody = self.w.account("WF0205-NONE")
        self.suspend(nobody)
        self.conflict("no_operational_role", self.activate, nobody)
        self.assertFalse(Account.objects.get(pk=nobody.pk).is_active)
        inactive_role = Role.objects.create(role_name="Retired Club Role", is_active=False)
        holder = self.w.account("WF0205-RETIRED")
        AccountRole.objects.create(account=holder, role=inactive_role)
        self.suspend(holder)
        self.conflict("no_operational_role", self.activate, holder)
        self.assertFalse(AccountRole.objects.filter(account=nobody).exists())  # nothing granted to make it eligible

    def test_pending_rejected_and_missing_accounts_look_alike(self):
        pending = self.w.account("WF0205-PENDING", status="Pending", active=False)
        rejected = self.w.account("WF0205-REJECTED", status="Rejected", active=False)
        for target, call, expected in ((pending, self.activate, False), (rejected, self.activate, False),
                                       (pending, self.suspend, True), (rejected, self.suspend, True)):
            with self.subTest(status=target.request_status, call=call.__name__):
                with self.assertRaises(AccountStatusDenied) as caught:
                    call(target, expected=expected)
                self.assertNotIsInstance(caught.exception, AccountStatusConflict)
        with self.assertRaises(AccountStatusDenied):
            suspend_account(actor=self.w.reviewer, target_id=2_000_000_000, expected_active=True)
        self.assertEqual(Account.objects.get(pk=pending.pk).request_status, "Pending")
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_administrators_governance_framework_accounts_and_self_are_protected(self):
        protected = [self.w.account("WF0205-OTHER-ADMIN", "Admin"),
                     self.w.account("WF0205-TSA", "Technical Super Admin"),
                     self.w.account("WF0205-TSA-ADMIN", "Admin", "Technical Super Admin"),
                     self.w.account("WF0205-STUDENT-ADMIN", "Student", "Admin"),
                     self.w.account("WF0205-STAFF", "Student", is_staff=True),
                     self.w.account("WF0205-SUPER", "Student", is_superuser=True, is_staff=True)]
        for target in protected:
            with self.subTest(target=target.school_id):
                self.conflict("protected_account", self.suspend, target)
                self.assertTrue(Account.objects.get(pk=target.pk).is_active)
        self.conflict("protected_account", self.suspend, self.w.reviewer)
        inactive_admin = self.w.account("WF0205-OFF-ADMIN", "Admin", active=False)
        self.conflict("protected_account", self.activate, inactive_admin)

    def test_stale_or_repeated_confirmation_never_changes_or_audits_twice(self):
        target = self.w.account("WF0205-STALE", "Student")
        self.conflict("state_changed", self.suspend, target, expected=False)
        self.suspend(target)
        self.conflict("state_changed", self.suspend, target)
        self.conflict("state_changed", self.activate, target, expected=True)
        self.activate(target)
        self.conflict("state_changed", self.activate, target)
        self.assertEqual(AccessAuditLog.objects.filter(target_account=target).count(), 2)

    def test_reviewer_authorization_denials(self):
        target = self.w.account("WF0205-AUTHZ", "Student")
        deny = AccountPermission.objects.create(account=self.w.reviewer, permission=self.w.perms["suspend"], effect="Deny")
        with self.assertRaises(AccountStatusDenied):
            self.suspend(target)
        deny.delete()
        Role.objects.filter(pk=self.w.roles["Admin"].pk).update(is_active=False)
        with self.assertRaises(AccountStatusDenied):
            self.suspend(target)
        Role.objects.filter(pk=self.w.roles["Admin"].pk).update(is_active=True)
        Account.objects.filter(pk=self.w.reviewer.pk).update(is_active=False)
        with self.assertRaises(AccountStatusDenied):
            self.suspend(target, actor=Account.objects.get(pk=self.w.reviewer.pk))
        Account.objects.filter(pk=self.w.reviewer.pk).update(is_active=True)
        Service.objects.filter(service_code="accounts").update(is_active=False)
        with self.assertRaises(AccountStatusUnavailable):
            self.suspend(target)
        Service.objects.filter(service_code="accounts").update(is_active=True)
        RolePermission.objects.filter(permission__permission_code="accounts.school_accounts.suspend").delete()
        Permission.objects.filter(permission_code="accounts.school_accounts.suspend").delete()
        with self.assertRaises(AccountStatusUnavailable):  # missing catalogue row
            self.suspend(target)
        self.assertTrue(Account.objects.get(pk=target.pk).is_active)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_audit_failure_rolls_back_and_gates_refuse(self):
        target = self.w.account("WF0205-ROLLBACK", "Student")
        with patch("apps.accounts.account_status.record_access_audit", side_effect=RuntimeError("audit down")):
            with self.assertRaises(RuntimeError):
                self.suspend(target)
        self.assertTrue(Account.objects.get(pk=target.pk).is_active)
        with override_settings(WORKSPACE_ACCOUNT_STATUS_ENABLED=False), self.assertRaises(AccountStatusUnavailable):
            self.suspend(target)
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True), \
                patch("apps.access_control.executor.client.remote_call") as remote, \
                self.assertRaises(WriterBoundaryUnavailable):
            self.suspend(target)
        remote.assert_not_called()
        self.assertTrue(Account.objects.get(pk=target.pk).is_active)
        self.assertFalse(AccessAuditLog.objects.exists())


def mounted_urlconf():
    module = ModuleType("wf0205_test_urlconf")
    module.urlpatterns = [path("api/v1/auth/", include("apps.accounts.urls")),
                          path("api/v1/admin/school-accounts/", include("apps.accounts.account_status_urls"))]
    return module


URLCONF = mounted_urlconf()
API = "/api/v1/admin/school-accounts/"


@override_settings(ROOT_URLCONF=URLCONF, **GATE)
class AccountStatusHTTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()
        cls.student = cls.w.account("7240001", "Student")
        cls.instructor = cls.w.account("0012345", "Instructor", requested="Instructor")
        cls.inactive = cls.w.account("7240002", "Student", active=False)
        cls.pending = cls.w.account("7240003", status="Pending", active=False)
        cls.admin_target = cls.w.account("9000009", "Admin")

    def setUp(self):
        cache.clear()
        self.client = self.signed_in(self.w.reviewer)

    @staticmethod
    def signed_in(account):
        client = Client(enforce_csrf_checks=True)
        client.force_login(account)
        client.cookies[settings.CSRF_COOKIE_NAME] = "e" * 32
        return client

    def post(self, target_id, action, body, client=None, csrf=True):
        return (client or self.client).post(f"{API}{target_id}/{action}/", data=json.dumps(body),
                                           content_type="application/json",
                                           **({"HTTP_X_CSRFTOKEN": "e" * 32} if csrf else {}))

    def test_directory_lists_only_eligible_accounts_with_minimized_fields(self):
        response = self.client.get(API)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("no-store", response["Cache-Control"])
        rows = response.json()["results"]
        ids = {r["account_id"] for r in rows}
        self.assertEqual(ids, {self.student.pk, self.instructor.pk, self.inactive.pk})  # not pending, admins or self
        row = next(r for r in rows if r["account_id"] == self.instructor.pk)
        self.assertEqual(set(row), {"account_id", "school_id", "id_label", "full_name", "roles", "is_active"})
        self.assertEqual((row["id_label"], row["roles"], row["is_active"]), ("Staff ID", ["Instructor"], True))
        self.assertNotIn("password", response.content.decode())
        self.assertEqual({r["account_id"] for r in self.client.get(API, {"status": "inactive"}).json()["results"]},
                         {self.inactive.pk})
        self.assertEqual([r["account_id"] for r in self.client.get(API, {"q": "00123"}).json()["results"]],
                         [self.instructor.pk])
        for bad in ({"status": "Active"}, {"page": "0"}, {"sort": "x"}, {"q": "é"}):
            with self.subTest(bad=bad):
                cache.clear()
                self.assertEqual(self.client.get(API, bad).status_code, 400)

    def test_detail_is_read_only_and_ineligible_accounts_share_one_404(self):
        response = self.client.get(f"{API}{self.inactive.pk}/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), {"account_id", "school_id", "id_label", "name", "full_name", "roles",
                                     "is_active", "request_status", "created_at", "can_reactivate",
                                     # WF-02.06 D-75/D-76 status dates (exact contract in test_wf0206_account_history)
                                     "approved_at", "last_status_change"})
        self.assertEqual((body["is_active"], body["can_reactivate"], body["roles"]), (False, True, ["Student"]))
        missing = [self.client.get(f"{API}{pk}/") for pk in (self.pending.pk, self.admin_target.pk, self.w.reviewer.pk, 2_000_000_000)]
        self.assertEqual({r.status_code for r in missing}, {404})
        self.assertEqual(len({r.content for r in missing}), 1)
        self.assertEqual(self.client.post(f"{API}{self.student.pk}/", data="{}", content_type="application/json",
                                          HTTP_X_CSRFTOKEN="e" * 32).status_code, 405)

    def test_suspend_and_activate_contract(self):
        response = self.post(self.student.pk, "suspend", {"expected_active": True})
        self.assertEqual((response.status_code, response.json()), (200, {"account_id": self.student.pk, "is_active": False}))
        stale = self.post(self.student.pk, "suspend", {"expected_active": True})
        self.assertEqual((stale.status_code, stale.json()), (409, {"error": {
            "code": "account_status_conflict", "reason": "state_changed", "message": "The account status could not be changed."}}))
        self.assertEqual(self.post(self.student.pk, "activate", {"expected_active": False}).json()["is_active"], True)
        protected = self.post(self.admin_target.pk, "suspend", {"expected_active": True})
        self.assertEqual((protected.status_code, protected.json()["error"]["reason"]), (409, "protected_account"))
        self.assertEqual(self.post(self.pending.pk, "activate", {"expected_active": False}).status_code, 404)
        for body in ({}, {"expected_active": "true"}, {"expected_active": 1}, {"expected_active": True, "role_id": 1}, [True]):
            with self.subTest(body=body):
                cache.clear()
                self.assertEqual(self.post(self.student.pk, "suspend", body).status_code, 400)
        self.assertEqual(AccessAuditLog.objects.count(), 2)

    def test_authentication_permissions_and_gates(self):
        self.assertEqual(self.post(self.student.pk, "suspend", {"expected_active": True}, csrf=False).status_code, 403)
        anonymous = Client(enforce_csrf_checks=True)
        anonymous.cookies[settings.CSRF_COOKIE_NAME] = "e" * 32
        self.assertEqual(self.post(self.student.pk, "suspend", {"expected_active": True}, client=anonymous).status_code, 401)
        self.assertEqual(anonymous.get(API).status_code, 401)
        for school_id, roles in (("WF0205-H-S", ("Student",)), ("WF0205-H-I", ("Instructor",)),
                                 ("WF0205-H-T", ("Treasurer",)), ("WF0205-H-TSA", ("Technical Super Admin",))):
            with self.subTest(roles=roles):
                cache.clear()
                other = self.signed_in(self.w.account(school_id, *roles))
                self.assertEqual(other.get(API).status_code, 403)
                self.assertEqual(self.post(self.student.pk, "suspend", {"expected_active": True}, client=other).status_code, 403)
        cache.clear()
        both = self.signed_in(self.w.account("WF0205-H-BOTH", "Admin", "Technical Super Admin"))
        self.assertEqual(both.get(API).status_code, 200)
        AccountPermission.objects.create(account=self.w.reviewer, permission=self.w.perms["suspend"], effect="Deny")
        self.assertEqual(self.post(self.student.pk, "suspend", {"expected_active": True}).status_code, 403)
        self.assertEqual(self.client.get(API).status_code, 200)  # a Deny on suspend leaves read intact
        AccountPermission.objects.filter(account=self.w.reviewer).delete()
        with override_settings(WORKSPACE_ACCOUNT_STATUS_ENABLED=False):
            self.assertEqual(self.client.get(API).status_code, 503)
            self.assertEqual(self.post(self.student.pk, "suspend", {"expected_active": True}).status_code, 503)
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):
            self.assertEqual(self.post(self.student.pk, "suspend", {"expected_active": True}).status_code, 503)
        RolePermission.objects.filter(permission__permission_code="accounts.school_accounts.activate").delete()
        Permission.objects.filter(permission_code="accounts.school_accounts.activate").delete()
        self.assertEqual(self.post(self.inactive.pk, "activate", {"expected_active": False}).status_code, 403)
        self.assertTrue(Account.objects.get(pk=self.student.pk).is_active)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_rate_limit(self):
        statuses = [self.post(self.student.pk, "suspend", {}).status_code for _ in range(21)]
        self.assertEqual((statuses[:20], statuses[20]), ([400] * 20, 429))

    def test_not_mounted_in_config_urls_and_the_release_safeguard_refuses_it(self):
        for url in (API, f"{API}1/suspend/", f"{API}1/activate/"):
            with self.subTest(url=url), self.assertRaises(Resolver404):
                resolve(url, urlconf="config.urls")
        from apps.access_control.management.commands.init_registration_review_metadata_local_dev import unexpected_review_routes
        self.assertEqual(len(unexpected_review_routes(URLCONF)), 5)  # list, detail, history (WF-02.06), suspend, activate
        self.assertEqual(unexpected_review_routes("config.urls"), [])


@override_settings(**GATE)
class AccountStatusSessionTests(TestCase):
    """D-66: deactivation ends access everywhere; reactivation never revives an older session."""

    @classmethod
    def setUpTestData(cls):
        cls.w = World()

    def setUp(self):
        cache.clear()
        self.user = self.w.account("7240100", "Student")
        self.bystander = self.w.account("7240101", "Student")

    def browser(self, account=None):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        response = client.post("/api/v1/auth/login/", {"school_id": (account or self.user).school_id, "password": PASSWORD},
                               format="json", HTTP_X_CSRFTOKEN=token)
        client.login_status = response.status_code
        return client

    @staticmethod
    def signed_in(client):
        return client.get("/api/v1/auth/session/").json()["authenticated"]

    def sessions_of(self, account):
        return [s for s in Session.objects.all() if s.get_decoded().get("_auth_user_id") == str(account.pk)]

    def test_never_suspended_accounts_keep_djangos_own_session_hash(self):
        self.assertEqual(status_epoch(self.user.pk), 0)
        self.assertEqual(self.user.get_session_auth_hash(), AbstractBaseUser._get_session_auth_hash(self.user))

    def test_deactivation_ends_every_session_and_reactivation_revives_none(self):
        first, second, other = self.browser(), self.browser(), self.browser(self.bystander)
        self.assertTrue(all(c.login_status == 200 for c in (first, second, other)))
        self.assertTrue(self.signed_in(first) and self.signed_in(second))
        suspend_account(actor=self.w.reviewer, target_id=self.user.pk, expected_active=True)
        self.assertFalse(self.signed_in(first))
        self.assertFalse(self.signed_in(second))
        self.assertTrue(self.signed_in(other))  # nobody else is affected
        # Logging in while inactive is refused.
        self.assertEqual(self.browser().login_status, 401)
        activate_account(actor=self.w.reviewer, target_id=self.user.pk, expected_active=False)
        # The old cookies stay dead after reactivation; a fresh sign-in works.
        self.assertFalse(self.signed_in(first))
        self.assertFalse(self.signed_in(second))
        fresh = self.browser()
        self.assertEqual(fresh.login_status, 200)
        self.assertTrue(self.signed_in(fresh))
        self.assertEqual(len(self.sessions_of(self.user)), 1)  # the old rows were flushed on use

    def test_unused_old_session_rows_cannot_be_revived_either(self):
        idle = self.browser()
        old_keys = {s.session_key for s in self.sessions_of(self.user)}
        suspend_account(actor=self.w.reviewer, target_id=self.user.pk, expected_active=True)
        activate_account(actor=self.w.reviewer, target_id=self.user.pk, expected_active=False)
        self.assertTrue(old_keys)
        self.assertFalse(self.signed_in(idle))  # first use after reactivation: hash mismatch, flushed
        self.assertFalse(Session.objects.filter(session_key__in=old_keys).exists())

    def test_a_delayed_session_save_from_an_in_flight_request_cannot_restore_access(self):
        client = self.browser()
        key = client.cookies[settings.SESSION_COOKIE_NAME].value
        store = import_module(settings.SESSION_ENGINE).SessionStore(session_key=key)
        store.load()  # an in-flight request holding the pre-suspension session
        suspend_account(actor=self.w.reviewer, target_id=self.user.pk, expected_active=True)
        store["_workspace_seen_at"] = store["_workspace_seen_at"] + 1
        store.save()  # its delayed write-back after the suspension
        activate_account(actor=self.w.reviewer, target_id=self.user.pk, expected_active=False)
        self.assertFalse(self.signed_in(client))

    def test_a_suspension_racing_a_login_never_leaves_a_revivable_session(self):
        real_login = session_auth.login

        def suspend_before(request, user, *args, **kwargs):
            suspend_account(actor=self.w.reviewer, target_id=self.user.pk, expected_active=True)
            return real_login(request, user, *args, **kwargs)

        def suspend_after(request, user, *args, **kwargs):
            result = real_login(request, user, *args, **kwargs)
            suspend_account(actor=self.w.reviewer, target_id=self.user.pk, expected_active=True)
            return result

        for label, hook in (("committed before login()", suspend_before), ("committed after login()", suspend_after)):
            with self.subTest(label):
                with patch.object(session_auth, "login", side_effect=hook):
                    client = self.browser()
                self.assertEqual(client.login_status, 401)  # the post-login re-check refuses and signs out
                self.assertFalse(self.signed_in(client))
                activate_account(actor=self.w.reviewer, target_id=self.user.pk, expected_active=False)
                self.assertFalse(self.signed_in(client))

    def test_session_rows_of_other_accounts_are_untouched(self):
        other = self.browser(self.bystander)
        before = {s.session_key for s in self.sessions_of(self.bystander)}
        suspend_account(actor=self.w.reviewer, target_id=self.user.pk, expected_active=True)
        self.assertTrue(self.signed_in(other))
        self.assertEqual({s.session_key for s in self.sessions_of(self.bystander)}, before)


@override_settings(**GATE)
class AccountStatusConcurrencyTests(TransactionTestCase):
    """Two real MySQL connections; the second decision waits on the first one's row locks."""

    def setUp(self):
        self.w = World()
        self.target = self.w.account("WF0205-RACE", "Student")
        self.holding, self.release = threading.Event(), threading.Event()

    def tearDown(self):
        self.release.set()
        connections.close_all()

    def pause_first(self):
        real = account_status.has_permission
        first = threading.Lock()

        def paused(account, code):
            if first.acquire(blocking=False):
                self.holding.set()
                self.release.wait(timeout=20)
            return real(account, code)
        return patch.object(account_status, "has_permission", paused)

    @staticmethod
    def in_thread(fn):
        def call():
            try:
                verify_database()
                return ("ok", fn())
            except Exception as exc:  # noqa: BLE001 - asserted by the test
                return ("error", exc)
            finally:
                connections.close_all()
        return call

    def race(self, first, second):
        rid, tid = self.w.reviewer.pk, self.target.pk
        with self.pause_first(), ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(self.in_thread(lambda: first(Account.objects.get(pk=rid), tid)))
            self.assertTrue(self.holding.wait(timeout=20))
            b = pool.submit(self.in_thread(lambda: second(Account.objects.get(pk=rid), tid)))
            self.release.wait(timeout=1.0)
            self.assertFalse(b.done(), "the second decision must wait on the first one's locks")
            self.release.set()
            return a.result(timeout=30), b.result(timeout=60)

    def test_two_suspensions_from_the_same_view_decide_once(self):
        def suspend(actor, pk):
            return suspend_account(actor=actor, target_id=pk, expected_active=True)
        (a, _), (b, err) = self.race(suspend, suspend)
        self.assertEqual((a, b), ("ok", "error"))
        self.assertIsInstance(err, AccountStatusConflict)
        self.assertEqual(err.reason, "state_changed")
        self.assertEqual(AccessAuditLog.objects.filter(target_account=self.target).count(), 1)

    def test_two_reactivations_from_the_same_view_decide_once(self):
        Account.objects.filter(pk=self.target.pk).update(is_active=False)

        def activate(actor, pk):
            return activate_account(actor=actor, target_id=pk, expected_active=False)
        (a, _), (b, err) = self.race(activate, activate)
        self.assertEqual((a, b, err.reason), ("ok", "error", "state_changed"))
        self.assertTrue(Account.objects.get(pk=self.target.pk).is_active)

    def test_reviewer_permission_revoked_while_the_request_waits(self):
        from django.db import transaction
        rp = RolePermission.objects.get(permission=self.w.perms["suspend"]).pk
        rid, tid = self.w.reviewer.pk, self.target.pk
        revoked, commit = threading.Event(), threading.Event()

        def revoke():
            with transaction.atomic():
                list(Service.objects.select_for_update().filter(
                    service_code__in=["access_control", "accounts"]).order_by("service_id"))
                RolePermission.objects.filter(pk=rp).update(is_active=False)
                revoked.set()
                commit.wait(timeout=20)
        with ThreadPoolExecutor(max_workers=2) as pool:
            r = pool.submit(self.in_thread(revoke))
            self.assertTrue(revoked.wait(timeout=20))
            b = pool.submit(self.in_thread(lambda: suspend_account(
                actor=Account.objects.get(pk=rid), target_id=tid, expected_active=True)))
            commit.wait(timeout=1.0)
            self.assertFalse(b.done())
            commit.set()
            self.assertEqual(r.result(timeout=30)[0], "ok")
            status, err = b.result(timeout=60)
        self.assertEqual(status, "error")
        self.assertIsInstance(err, AccountStatusDenied)
        self.assertTrue(Account.objects.get(pk=self.target.pk).is_active)
        self.assertFalse(AccessAuditLog.objects.exists())
