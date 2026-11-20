"""WF-02.05 stage 2: mounted local-review/sandbox HTTP, D-66 over real HTTP, epoch integrity, safeguard.

Run: python manage.py test apps.accounts.test_wf0205_stage2 --settings=config.test_settings --noinput
Disposable MySQL only; synthetic accounts; the catalogue rows are TEST FIXTURES in the test database
(the governed provisioning of real rows is a separate, pending authorization).
"""

import json
import re
from importlib import import_module
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import Resolver404, include, path, resolve
from django.views.decorators.csrf import csrf_exempt
from rest_framework.test import APIClient

from apps.access_control.management.commands.init_registration_review_metadata_local_dev import unexpected_review_routes
from apps.access_control.models import AccessAuditLog, AccountRole, Role

from .account_status import gate_open, status_epoch, suspend_account
from .account_status_api import SuspendSchoolAccountView
from .models import Account
from .test_wf0204_release_settings import local_review, sandbox
from .test_wf0205_account_status import PASSWORD, World

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("WF-02.05 stage-2 tests require --settings=config.test_settings.")

API = "/api/v1/admin/school-accounts/"
BACKEND = Path(settings.BASE_DIR)


def mode_settings(cfg):
    """The mounted configuration's own routing, middleware, cookies and gates (no DB switch)."""
    return dict(ROOT_URLCONF=cfg.ROOT_URLCONF, MIDDLEWARE=cfg.MIDDLEWARE,
                SESSION_COOKIE_NAME=cfg.SESSION_COOKIE_NAME, CSRF_COOKIE_NAME=cfg.CSRF_COOKIE_NAME,
                WORKSPACE_ACCOUNT_STATUS_ENABLED=cfg.WORKSPACE_ACCOUNT_STATUS_ENABLED,
                WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False, ALLOWED_HOSTS=["testserver", *cfg.ALLOWED_HOSTS])


class Browser:
    def __init__(self, school_id, password=PASSWORD):
        self.client = APIClient(enforce_csrf_checks=True)
        self.csrf = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        self.login = self.client.post("/api/v1/auth/login/", {"school_id": school_id, "password": password},
                                      format="json", HTTP_X_CSRFTOKEN=self.csrf).status_code
        self.csrf = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]  # rotated by login

    def signed_in(self):
        return self.client.get("/api/v1/auth/session/").json()["authenticated"]

    def change(self, account, action, expected):
        return self.client.post(f"{API}{account.pk}/{action}/", data=json.dumps({"expected_active": expected}),
                                content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf)


class MountedModeMixin:
    cfg = None

    @classmethod
    def setUpTestData(cls):
        cls.w = World()
        cls.tsa = cls.w.account("WF0205-S2-TSA", "Admin", "Technical Super Admin")

    def setUp(self):
        cache.clear()
        self.user = self.w.account("7250001", "Student", "Treasurer")

    def test_configuration_mounts_and_enables_only_here(self):
        self.assertIs(self.cfg.WORKSPACE_ACCOUNT_STATUS_ENABLED, True)
        self.assertEqual(resolve(f"{API}1/suspend/", urlconf=self.cfg.ROOT_URLCONF).url_name, "school-accounts-suspend")
        with self.assertRaises(Resolver404):
            resolve(f"{API}1/suspend/", urlconf="config.urls")

    def test_d66_sequence_over_real_http(self):
        admin = Browser(self.w.reviewer.school_id)
        first, second = Browser(self.user.school_id), Browser(self.user.school_id)
        self.assertEqual((admin.login, first.login, second.login), (200, 200, 200))
        self.assertTrue(first.signed_in() and second.signed_in())
        listed = admin.client.get(API).json()["results"]
        self.assertIn(self.user.pk, [r["account_id"] for r in listed])
        # 2-3: deactivate through the mounted endpoint; both sessions lose access.
        response = admin.change(self.user, "suspend", True)
        self.assertEqual((response.status_code, response.json()), (200, {"account_id": self.user.pk, "is_active": False}))
        self.assertFalse(first.signed_in())
        self.assertFalse(second.signed_in())
        self.assertEqual(Browser(self.user.school_id).login, 401)
        # 4-5: reactivate; both old cookies stay invalid.
        self.assertEqual(admin.change(self.user, "activate", False).status_code, 200)
        self.assertFalse(first.signed_in())
        self.assertFalse(second.signed_in())
        # 6: a fresh login succeeds.
        fresh = Browser(self.user.school_id)
        self.assertEqual(fresh.login, 200)
        self.assertTrue(fresh.signed_in())
        # Roles and overrides unchanged; the admin is still signed in.
        self.assertEqual(sorted(AccountRole.objects.filter(account=self.user).values_list("role__role_name", flat=True)),
                         ["Student", "Treasurer"])
        self.assertTrue(admin.signed_in())

    def test_delayed_session_save_cannot_revive(self):  # 7
        admin = Browser(self.w.reviewer.school_id)
        victim = Browser(self.user.school_id)
        store = import_module(settings.SESSION_ENGINE).SessionStore(
            session_key=victim.client.cookies[settings.SESSION_COOKIE_NAME].value)
        store.load()
        self.assertEqual(admin.change(self.user, "suspend", True).status_code, 200)
        store["_workspace_seen_at"] = store["_workspace_seen_at"] + 1
        store.save()
        self.assertEqual(admin.change(self.user, "activate", False).status_code, 200)
        self.assertFalse(victim.signed_in())

    def test_failed_deactivation_changes_neither_state_nor_epoch(self):  # 8
        admin = Browser(self.w.reviewer.school_id)
        victim = Browser(self.user.school_id)
        before = status_epoch(self.user.pk)
        with patch("apps.accounts.account_status.record_access_audit", side_effect=RuntimeError("audit down")):
            response = admin.change(self.user, "suspend", True)
        self.assertGreaterEqual(response.status_code, 500)
        self.assertNotIn("audit down", response.content.decode())
        self.assertEqual(status_epoch(self.user.pk), before)
        self.assertTrue(Account.objects.get(pk=self.user.pk).is_active)
        self.assertTrue(victim.signed_in())
        stale = admin.change(self.user, "activate", False)  # stale confirmation: refused, epoch untouched
        self.assertEqual((stale.status_code, stale.json()["error"]["reason"]), (409, "state_changed"))
        self.assertEqual(status_epoch(self.user.pk), before)
        self.assertTrue(victim.signed_in())

    def test_technical_super_admin_acts_only_through_admin(self):
        tsa = Browser(self.tsa.school_id)
        self.assertEqual(tsa.change(self.user, "suspend", True).status_code, 200)
        AccountRole.objects.filter(account=self.tsa, role__role_name="Admin").delete()
        self.assertEqual(Browser(self.tsa.school_id).change(self.user, "activate", False).status_code, 403)
        self.assertFalse(Account.objects.get(pk=self.user.pk).is_active)

    def test_protected_writer_and_switch_still_refuse_when_mounted(self):
        admin = Browser(self.w.reviewer.school_id)
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):
            self.assertEqual(admin.change(self.user, "suspend", True).status_code, 503)
        with override_settings(WORKSPACE_ACCOUNT_STATUS_ENABLED=False):
            self.assertEqual(admin.change(self.user, "suspend", True).status_code, 503)
            self.assertEqual(admin.client.get(API).status_code, 503)
        self.assertTrue(Account.objects.get(pk=self.user.pk).is_active)
        self.assertFalse(AccessAuditLog.objects.filter(action__startswith="account.status.").exists())


LOCAL = local_review()
SANDBOX = sandbox()


@override_settings(**mode_settings(LOCAL))
class LocalReviewModeTests(MountedModeMixin, TestCase):
    cfg = LOCAL


@override_settings(**mode_settings(SANDBOX))
class SandboxModeTests(MountedModeMixin, TestCase):
    cfg = SANDBOX


@override_settings(WORKSPACE_ACCOUNT_STATUS_ENABLED=True, WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False)
class SessionEpochIntegrityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()

    def setUp(self):
        self.user = self.w.account("7250100", "Student")

    def cycle(self):
        suspend_account(actor=self.w.reviewer, target_id=self.user.pk, expected_active=True)
        from .account_status import activate_account
        activate_account(actor=self.w.reviewer, target_id=self.user.pk, expected_active=False)

    def test_epoch_only_moves_forward_and_only_on_a_committed_suspension(self):
        self.assertEqual(status_epoch(self.user.pk), 0)
        self.cycle()
        first = status_epoch(self.user.pk)
        self.assertGreater(first, 0)
        hash_after_first = Account.objects.get(pk=self.user.pk).get_session_auth_hash()
        # Other audited operations on the same account never move or reset the epoch.
        from apps.access_control.audit import record_access_audit
        from django.db import transaction
        with transaction.atomic():
            record_access_audit(actor=self.w.reviewer, target=self.user, action="account.status.activate",
                                old_value={"is_active": False}, new_value={"is_active": True}, reason="account_status_change")
            record_access_audit(actor=self.w.reviewer, target=self.user, action="test.unrelated",
                                new_value={"is_active": True})
        self.assertEqual(status_epoch(self.user.pk), first)
        self.assertEqual(Account.objects.get(pk=self.user.pk).get_session_auth_hash(), hash_after_first)
        self.cycle()
        self.assertGreater(status_epoch(self.user.pk), first)
        self.assertNotEqual(Account.objects.get(pk=self.user.pk).get_session_auth_hash(), hash_after_first)

    def test_a_session_from_between_two_suspensions_also_dies(self):
        self.cycle()
        with override_settings(ROOT_URLCONF="config.urls"):
            middle = Browser(self.user.school_id)
            self.assertTrue(middle.signed_in())
            self.cycle()
            self.assertFalse(middle.signed_in())
            self.assertTrue(Browser(self.user.school_id).signed_in())

    def test_the_epoch_cannot_be_reset_by_reverting_to_djangos_hash(self):
        from django.contrib.auth.base_user import AbstractBaseUser
        default = AbstractBaseUser._get_session_auth_hash(self.user)
        self.cycle()
        current = Account.objects.get(pk=self.user.pk)
        self.assertNotEqual(current.get_session_auth_hash(), default)
        self.assertNotIn(default, list(current.get_session_auth_fallback_hash()))

    def test_session_lookup_cost_is_one_indexed_aggregate_per_request(self):
        self.cycle()
        with override_settings(ROOT_URLCONF="config.urls"):
            browser = Browser(self.user.school_id)
            with CaptureQueriesContext(connection) as queries:
                self.assertTrue(browser.signed_in())
        epoch_queries = [q["sql"] for q in queries if "MAX(" in q["sql"].upper() and "access_audit_logs" in q["sql"]]
        self.assertEqual(len(epoch_queries), 1)
        with connection.cursor() as cursor:
            cursor.execute("EXPLAIN SELECT MAX(access_audit_log_id) FROM access_audit_logs "
                           "WHERE target_account_id=%s AND action=%s", [self.user.pk, "account.status.suspend"])
            columns = [c[0] for c in cursor.description]
            plan = dict(zip(columns, cursor.fetchone()))
        self.assertIsNotNone(plan.get("key"), plan)  # served by an index, not a table scan


def conf(*patterns):
    module = ModuleType("wf0205_unauthorized_urlconf")
    module.urlpatterns = list(patterns)
    return module


class ReleaseSafeguardVerificationTests(TestCase):
    """The existing P1/P3C safeguard against unauthorized account-status mounts (no safeguard change)."""

    def test_production_urlconf_exposes_nothing(self):
        self.assertEqual(unexpected_review_routes("config.urls"), [])
        for url in (API, f"{API}1/", f"{API}1/suspend/", f"{API}1/activate/"):
            with self.subTest(url=url), self.assertRaises(Resolver404):
                resolve(url, urlconf="config.urls")

    def test_class_based_unauthorized_mounts_are_detected(self):
        view = SuspendSchoolAccountView.as_view()

        class Renamed(SuspendSchoolAccountView):
            pass
        for label, pattern in (
            ("include elsewhere", path("x/", include("apps.accounts.account_status_urls"))),
            ("renamed path and name", path("other/<int:account_id>/off/", view, name="plain")),
            ("csrf_exempt wrapper", path("w/<int:account_id>/", csrf_exempt(view))),
            ("subclass", path("s/<int:account_id>/", Renamed.as_view())),
        ):
            with self.subTest(label):
                self.assertTrue(unexpected_review_routes(conf(pattern)))
        self.assertTrue(len(unexpected_review_routes("config.review_local_urls")) >= 4)
        self.assertTrue(len(unexpected_review_routes("config.review_sandbox_urls")) >= 4)

    def test_known_gap_an_opaque_function_wrapper_is_not_detected_but_cannot_write_by_default(self):
        view = SuspendSchoolAccountView.as_view()
        wrapped = conf(path("api/v1/auth/", include("apps.accounts.urls")),
                       path("opaque/<int:account_id>/", lambda request, account_id: view(request, account_id=account_id)))
        self.assertEqual(unexpected_review_routes(wrapped), [])  # residual limit: unrelated path and module
        w = World()
        target = w.account("7250200", "Student")
        with override_settings(ROOT_URLCONF=wrapped):  # production defaults: no account-status switch
            self.assertFalse(gate_open())
            client = APIClient(enforce_csrf_checks=True)
            client.force_login(w.reviewer)
            token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
            response = client.post(f"/opaque/{target.pk}/", {"expected_active": True}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 503)
        self.assertTrue(Account.objects.get(pk=target.pk).is_active)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_the_switch_is_default_off_and_not_environment_controlled(self):
        text = (BACKEND / "config" / "settings.py").read_text(encoding="utf-8")
        self.assertNotIn("WORKSPACE_ACCOUNT_STATUS_ENABLED", text)
        for name in ("security_settings.py", "test_settings.py", "executor_settings.py", "executor_isolated_settings.py"):
            self.assertNotIn("WORKSPACE_ACCOUNT_STATUS_ENABLED", (BACKEND / "config" / name).read_text(encoding="utf-8"), name)
        self.assertFalse(hasattr(settings, "WORKSPACE_ACCOUNT_STATUS_ENABLED"))  # absent under test settings
        self.assertFalse(gate_open())
        with override_settings(WORKSPACE_ACCOUNT_STATUS_ENABLED="1"):
            self.assertFalse(gate_open())  # only the boolean True opens it

    def test_no_other_code_path_reaches_the_service(self):
        callers = []
        for file in (BACKEND / "apps").rglob("*.py"):
            if file.name.startswith("test") or "tests_support" in file.parts:
                continue
            text = file.read_text(encoding="utf-8")
            if file.name != "account_status.py" and re.search(r"\b(suspend_account|activate_account)\b", text):
                callers.append(file.name)
        # Only the authenticated API views reference the service; no command, signal or other route does.
        self.assertEqual(callers, ["account_status_api.py"])
