"""WF-02.01 Option A and WF-02.02 D-41: narrowed registration-review release safeguard (P1 and P3C).

Run: python manage.py test apps.access_control.test_wf0201_release_safeguard --settings=config.test_settings
Owner-authorized 17 Nov 2026. The approved GET-only pending list and GET-only applicant detail may
be mounted before the review release; approve, reject, bulk and any unexpected review route must
still refuse.
"""

from contextlib import contextmanager
from io import StringIO
from types import ModuleType
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import HttpResponse
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.urls import include, path, set_urlconf
from django.views import View

from apps.accounts.models import Account
from apps.accounts.registration_bulk_api import BulkRegistrationReviewView
from apps.accounts.registration_review_api import (
    ApproveRegistrationRequestView, PendingRegistrationDetailView, PendingRegistrationRequestsView,
    RejectRegistrationRequestView,
)
from apps.access_control.management.commands import (
    init_registration_review_inactive_bindings_local_dev as p2,
    init_registration_review_metadata_local_dev as p1,
    report_registration_review_operational_gate_p3c as p3c,
)
from apps.access_control.models import AccessAuditLog, AccountRole, Role, Service

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("WF-02.01 safeguard tests require --settings=config.test_settings.")

LIST = "api/v1/admin/registration-requests/"


class PlainView(View):
    def get(self, request):
        return HttpResponse("ok")


class WritableListView(PendingRegistrationRequestsView):
    http_method_names = ["get", "head", "options", "post"]

    def post(self, request):  # pragma: no cover - never dispatched in these tests
        return HttpResponse(status=405)


def urlconf(*patterns):
    module = ModuleType("wf0201_test_urlconf")
    module.urlpatterns = list(patterns)
    return module


DETAIL = LIST + "<int:account_id>/"


class WritableDetailView(PendingRegistrationDetailView):
    http_method_names = ["get", "head", "options", "post"]

    def post(self, request, account_id):  # pragma: no cover - never dispatched in these tests
        return HttpResponse(status=405)


def approved_detail():
    return path(DETAIL, PendingRegistrationDetailView.as_view(), name="registration-review-detail")


def approved_list():
    return path(LIST, PendingRegistrationRequestsView.as_view(), name="registration-review-pending")


# P1/P3C refuse under override_settings (UserSettingsHolder hides SETTINGS_MODULE), so these
# tests set the thread-local URLconf and patch only the one switch on the real settings.
@contextmanager
def mounted(conf):
    set_urlconf(conf)
    try:
        yield
    finally:
        set_urlconf(None)


def list_switch_on():
    return patch.object(settings, "WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED", True)


def refusal_messages(exc):
    """Every message in the cause chain: P3C inherits P1's route guard through P3A and P2."""
    found = []
    while exc is not None:
        found.append((type(exc), str(exc)))
        exc = exc.__cause__
    return found


class UnexpectedReviewRoutesTests(SimpleTestCase):
    def assert_allowed(self, conf):
        self.assertEqual(p1.unexpected_review_routes(conf), [])

    def assert_refused(self, conf, count=1):
        found = p1.unexpected_review_routes(conf)
        self.assertEqual(len(found), count, found)

    def test_real_application_urlconf_mounts_only_the_two_read_only_routes(self):
        self.assert_allowed("config.urls")

    # ---- WF-02.02 (D-41): the read-only applicant detail ----

    def test_exact_detail_with_the_list_is_allowed(self):
        self.assert_allowed(urlconf(approved_list(), approved_detail()))
        nested = urlconf(
            path("admin/registration-requests/", PendingRegistrationRequestsView.as_view(), name="registration-review-pending"),
            path("admin/registration-requests/<int:account_id>/", PendingRegistrationDetailView.as_view(),
                 name="registration-review-detail"),
        )
        self.assert_allowed(urlconf(path("api/v1/", include(nested))))

    def test_detail_without_the_list_is_refused(self):
        self.assert_refused(urlconf(approved_detail()))

    def test_altered_detail_mounts_are_refused(self):
        cases = {
            "moved": path("api/v1/registration-requests/<int:account_id>/", PendingRegistrationDetailView.as_view(),
                          name="registration-review-detail"),
            "re-typed converter": path(LIST + "<str:account_id>/", PendingRegistrationDetailView.as_view(),
                                       name="registration-review-detail"),
            "renamed": path(DETAIL, PendingRegistrationDetailView.as_view(), name="applicant-detail"),
            "unnamed": path(DETAIL, PendingRegistrationDetailView.as_view()),
            "method override": path(DETAIL, PendingRegistrationDetailView.as_view(http_method_names=["get", "post"]),
                                    name="registration-review-detail"),
            "writable subclass": path(DETAIL, WritableDetailView.as_view(), name="registration-review-detail"),
            "list view at the detail path": path(DETAIL, PendingRegistrationRequestsView.as_view(),
                                                 name="registration-review-detail"),
            "detail view at the list path": path(LIST, PendingRegistrationDetailView.as_view(),
                                                 name="registration-review-pending"),
        }
        for label, pattern in cases.items():
            with self.subTest(case=label):
                found = p1.unexpected_review_routes(urlconf(approved_list(), pattern))
                self.assertGreaterEqual(len(found), 1, found)

    def test_a_second_detail_mount_is_refused(self):
        self.assert_refused(urlconf(approved_list(), approved_detail(), approved_detail()))

    def test_decision_routes_are_still_refused_next_to_list_and_detail(self):
        for pattern in (
            path(LIST + "<int:account_id>/approve/", ApproveRegistrationRequestView.as_view(), name="registration-review-approve"),
            path(LIST + "<int:account_id>/reject/", RejectRegistrationRequestView.as_view(), name="registration-review-reject"),
            path(LIST + "bulk/", BulkRegistrationReviewView.as_view(), name="bulk-registration-review"),
        ):
            with self.subTest(route=str(pattern.pattern)):
                self.assert_refused(urlconf(approved_list(), approved_detail(), pattern))

    def test_nothing_mounted_and_non_review_routes_are_allowed(self):
        self.assert_allowed(urlconf())
        self.assert_allowed(urlconf(path("api/v1/other/", PlainView.as_view(), name="other")))

    def test_exact_approved_list_is_allowed_including_through_an_include(self):
        self.assert_allowed(urlconf(approved_list()))
        nested = urlconf(path("admin/registration-requests/", PendingRegistrationRequestsView.as_view(),
                              name="registration-review-pending"))
        self.assert_allowed(urlconf(path("api/v1/", include(nested))))

    def test_decision_and_bulk_routes_are_refused(self):
        for pattern in (
            path(LIST + "<int:account_id>/approve/", ApproveRegistrationRequestView.as_view(), name="registration-review-approve"),
            path(LIST + "<int:account_id>/reject/", RejectRegistrationRequestView.as_view(), name="registration-review-reject"),
            path(LIST + "bulk/", BulkRegistrationReviewView.as_view(), name="bulk-registration-review"),
            # Renamed or moved decision views are still identified by their class.
            path("api/v1/x/", ApproveRegistrationRequestView.as_view(), name="harmless"),
        ):
            with self.subTest(route=str(pattern.pattern)):
                self.assert_refused(urlconf(approved_list(), pattern))

    def test_isolated_review_urlconfs_are_refused(self):
        for name in ("config.review_local_urls", "config.review_sandbox_urls", "apps.accounts.registration_bulk_urls",
                     "apps.accounts.registration_review_urls"):
            with self.subTest(urlconf=name):
                self.assertNotEqual(p1.unexpected_review_routes(name), [])

    def test_altered_list_mounts_are_refused(self):
        cases = {
            "moved": path("api/v1/registration-requests/", PendingRegistrationRequestsView.as_view(), name="registration-review-pending"),
            "renamed": path(LIST, PendingRegistrationRequestsView.as_view(), name="pending-list"),
            "unnamed": path(LIST, PendingRegistrationRequestsView.as_view()),
            "method override": path(LIST, PendingRegistrationRequestsView.as_view(http_method_names=["get", "post"]),
                                    name="registration-review-pending"),
            "writable subclass": path(LIST, WritableListView.as_view(), name="registration-review-pending"),
        }
        for label, pattern in cases.items():
            with self.subTest(case=label):
                self.assert_refused(urlconf(pattern))

    def test_a_second_list_mount_is_refused(self):
        self.assert_refused(urlconf(approved_list(), approved_list()))

    def test_unknown_review_routes_are_refused(self):
        for pattern in (
            path("api/v1/export/", PlainView.as_view(), name="registration-review-export"),
            path("api/v1/admin/registration-requests/export/", PlainView.as_view(), name="export"),
            path("api/v1/bulk/", PlainView.as_view(), name="bulk-review-anything"),
        ):
            with self.subTest(route=str(pattern.pattern)):
                self.assert_refused(urlconf(approved_list(), pattern))

    def test_uninspectable_urlconfs_fail_closed(self):
        self.assertNotEqual(p1.unexpected_review_routes("config.module_that_does_not_exist"), [])
        broken = ModuleType("wf0201_broken")
        broken.urlpatterns = ["not-a-url-pattern"]
        self.assertNotEqual(p1.unexpected_review_routes(broken), [])

    def test_shared_guard_refuses_switch_and_routes_with_the_callers_error(self):
        for error in (p1.MetadataRefused, p3c.OperationalGateRefused):
            with self.subTest(error=error.__name__):
                with override_settings(ROOT_URLCONF="config.urls", WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=False):
                    p1.refuse_unless_only_read_only_list(error, "mounted")
                with override_settings(ROOT_URLCONF="config.urls", WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=True):
                    with self.assertRaisesMessage(error, "pending-list switch must remain off"):
                        p1.refuse_unless_only_read_only_list(error, "mounted")
                with override_settings(ROOT_URLCONF="config.review_local_urls", WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=False):
                    with self.assertRaisesMessage(error, "mounted"):
                        p1.refuse_unless_only_read_only_list(error, "mounted")


class ReleaseToolingWithReadOnlyListTests(TransactionTestCase):
    """The real P1 and P3C commands against the disposable test database."""

    def setUp(self):
        self.admin = Role.objects.create(role_name="Admin", is_active=True)
        self.actor = Account(school_id="WF0201-SAFEGUARD-ADMIN", request_status="Approved", is_active=True)
        self.actor.set_unusable_password()
        self.actor.save()
        AccountRole.objects.create(account=self.actor, role=self.admin)

    def p1(self):
        call_command("init_registration_review_metadata_local_dev", apply=True, actor_account_id=self.actor.pk,
                     confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO())

    def p2(self):
        call_command("init_registration_review_inactive_bindings_local_dev", apply=True, actor_account_id=self.actor.pk,
                     confirm_local_dev_phase2=p2.TEST_CONFIRM, stdout=StringIO())

    def p3c(self):
        out = StringIO()
        call_command("report_registration_review_operational_gate_p3c", actor_account_id=self.actor.pk,
                     expected_admin_account_ids=str(self.actor.pk), stdout=out)
        return out.getvalue()

    def assert_p1_refused(self, cause_text):
        with self.assertRaises(CommandError) as raised:
            self.p1()
        self.assertIsInstance(raised.exception.__cause__, p1.MetadataRefused)
        self.assertIn(cause_text, str(raised.exception.__cause__))
        self.assertFalse(Service.objects.exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_p1_and_p3c_pass_with_only_the_read_only_list_mounted(self):
        # The default ROOT_URLCONF is config.urls, which mounts the WF-02.01 list and WF-02.02 detail.
        self.assertEqual(settings.ROOT_URLCONF, "config.urls")
        self.p1()
        self.p2()
        self.assertIn("OPERATIONAL SCOPE VERIFIED", self.p3c())
        self.assertFalse(Service.objects.filter(is_active=True).exists())

    def test_p1_refuses_decision_routes_and_unknown_review_routes(self):
        for conf in ("config.review_local_urls",
                     urlconf(approved_list(), path("x/", PlainView.as_view(), name="registration-review-export"))):
            with self.subTest(conf=conf if isinstance(conf, str) else "unknown review route"):
                with mounted(conf):
                    self.assert_p1_refused("already mounted")

    def test_p1_refuses_while_the_list_switch_is_on(self):
        with list_switch_on():
            self.assert_p1_refused("pending-list switch must remain off")

    def test_p3c_refuses_decision_routes_unknown_routes_and_the_list_switch(self):
        self.p1()
        self.p2()
        audits = AccessAuditLog.objects.count()
        reject = path(LIST + "<int:account_id>/reject/", RejectRegistrationRequestView.as_view(),
                      name="registration-review-reject")
        cases = (
            ("sandbox", lambda: mounted("config.review_sandbox_urls"), "already mounted"),
            ("reject", lambda: mounted(urlconf(approved_list(), reject)), "already mounted"),
            ("unknown", lambda: mounted(urlconf(path("y/", PlainView.as_view(), name="registration-review-x"))),
             "already mounted"),
            ("switch", list_switch_on, "switch must remain off"),
        )
        for label, context, cause_text in cases:
            with self.subTest(case=label):
                with context():
                    with self.assertRaises(CommandError) as raised:
                        self.p3c()
                chain = refusal_messages(raised.exception)
                self.assertTrue(any(cause_text in message and kind in (p1.MetadataRefused, p3c.OperationalGateRefused)
                                    for kind, message in chain), chain)
                self.assertEqual(AccessAuditLog.objects.count(), audits)
                self.assertFalse(Service.objects.filter(is_active=True).exists())
        # Back to the real URLconf with the switch off: the gate reports normally again.
        self.assertIn("OPERATIONAL SCOPE VERIFIED", self.p3c())


# ---- WF-02.05 stage 3: account-status routes (owner-authorized safeguard amendment) ----

def _account_status_function_view(request, account_id):  # pragma: no cover - never dispatched
    return HttpResponse(status=405)


_account_status_function_view.__module__ = "apps.accounts.account_status_extra"


class AccountStatusSafeguardTests(SimpleTestCase):
    """Every recognized layer refuses an account-status mount; registration-review checks are unchanged."""

    def setUp(self):
        from apps.accounts.account_status_api import (
            ActivateSchoolAccountView, SchoolAccountListView, SuspendSchoolAccountView,
        )
        self.suspend = SuspendSchoolAccountView.as_view()
        self.views = (SchoolAccountListView, SuspendSchoolAccountView, ActivateSchoolAccountView)

    def refused(self, *patterns):
        return p1.unexpected_review_routes(urlconf(approved_list(), approved_detail(), *patterns))

    def test_every_mount_shape_is_refused(self):
        suspend = self.suspend

        class Renamed(self.views[1]):
            pass
        opaque = lambda request, account_id: suspend(request, account_id=account_id)  # noqa: E731
        from django.views.decorators.csrf import csrf_exempt
        shapes = {
            "direct": path("api/v1/admin/school-accounts/<int:account_id>/suspend/", suspend, name="school-accounts-suspend"),
            "include": path("api/v1/admin/school-accounts/", include("apps.accounts.account_status_urls")),
            "include elsewhere": path("x/", include("apps.accounts.account_status_urls")),
            "renamed path and name": path("other/<int:account_id>/off/", suspend, name="plain"),
            "subclass": path("s/<int:account_id>/", Renamed.as_view()),
            "class-based wrapper": path("c/<int:account_id>/", type("Wrap", (self.views[1],), {}).as_view()),
            "csrf_exempt": path("e/<int:account_id>/", csrf_exempt(suspend)),
            "opaque wrapper on a school-accounts path": path("api/v1/admin/school-accounts/<int:account_id>/off/", opaque),
            "opaque wrapper with a school-accounts name": path("o/<int:account_id>/", opaque, name="school-accounts-x"),
            "function view in an account_status module": path("f/<int:account_id>/", _account_status_function_view),
            "read-only list": path("api/v1/admin/school-accounts/", self.views[0].as_view(), name="school-accounts-list"),
        }
        for label, pattern in shapes.items():
            with self.subTest(label):
                self.assertTrue(self.refused(pattern))

    def test_the_approved_registration_read_routes_alone_are_still_allowed(self):
        self.assertEqual(p1.unexpected_review_routes(urlconf(approved_list(), approved_detail())), [])
        self.assertEqual(p1.unexpected_review_routes("config.urls"), [])
        for name in ("config.review_local_urls", "config.review_sandbox_urls"):
            found = p1.unexpected_review_routes(name)
            self.assertTrue(any("school-accounts" in item for item in found), name)
            self.assertTrue(any("approve" in item for item in found), name)

    def test_p1_and_p3c_guard_refuses_a_mounted_account_status_route(self):
        with patch.object(p1, "unexpected_review_routes", wraps=p1.unexpected_review_routes):
            set_urlconf(urlconf(approved_list(), path("api/v1/admin/school-accounts/", include("apps.accounts.account_status_urls"))))
            try:
                with self.assertRaises(CommandError):
                    p1.refuse_unless_only_read_only_list(CommandError, "refused")
            finally:
                set_urlconf(None)

    def test_remaining_limit_an_opaque_wrapper_on_an_unrelated_path_and_module(self):
        suspend = self.suspend
        opaque = lambda request, account_id: suspend(request, account_id=account_id)  # noqa: E731
        # Statically undetectable for every review route; the default-off backend switch and the
        # protected-writer refusal are the independent layers (tested in test_wf0205_stage2).
        self.assertEqual(self.refused(path("unrelated/<int:account_id>/", opaque)), [])
