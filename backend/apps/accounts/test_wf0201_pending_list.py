"""WF-02.01 View pending applications: isolated MySQL HTTP tests (P-06).

Run: python manage.py test apps.accounts.test_wf0201_pending_list --settings=config.test_settings --noinput
Uses the real config.urls route with the list gate enabled ONLY inside these tests.
Every record is created in the disposable test database.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import OperationalError, connection
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from apps.access_control.models import (
    AccountPermission, AccountRole, Permission, Role, RolePermission, Service,
)

from .models import Account, UserProfile
from .registration_review_api import (
    ApproveRegistrationRequestView, RejectRegistrationRequestView, ReviewListThrottle,
)
from .session_timeout import SEEN_AT


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Use --settings=config.test_settings for WF-02.01 tests.")

URL = "/api/v1/admin/registration-requests/"
PASSWORD = "Copper!River7799"
ITEM_KEYS = {"account_id", "school_id", "full_name", "requested_role", "created_at", "email_verified"}
BASE_TIME = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
GATES_OFF = dict(
    WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=False,
    WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=False,
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=False,
)


@override_settings(
    ROOT_URLCONF="config.urls",
    WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=True,
    WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=False,
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=False,
)
class PendingApplicationsListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.accounts_service = Service.objects.create(service_code="accounts", service_name="Accounts")
        cls.access_service = Service.objects.create(service_code="access_control", service_name="Access Control")
        cls.student = Role.objects.create(role_name="Student")
        cls.instructor = Role.objects.create(role_name="Instructor")
        cls.treasurer = Role.objects.create(role_name="Treasurer")
        cls.admin = Role.objects.create(role_name="Admin")
        cls.super_admin = Role.objects.create(role_name="Technical Super Admin")
        cls.perms = {}
        for action in ("read", "approve", "reject"):
            code = f"accounts.registration_requests.{action}"
            cls.perms[action] = Permission.objects.create(
                service=cls.accounts_service, permission_code=code,
                permission_name=f"Registration requests {action}",
                module_name="registration_requests", action_name=action,
            )
        # Same binding as the v2 catalogue: Admin only. Technical Super Admin has none.
        cls.read_grant = RolePermission.objects.create(role=cls.admin, permission=cls.perms["read"])
        cls.reviewer = cls.approved("WF0201-ADMIN", cls.admin)

    @classmethod
    def approved(cls, school_id, *roles):
        account = Account.objects.create_user(school_id=school_id, password=PASSWORD)
        Account.objects.filter(pk=account.pk).update(is_active=True, request_status="Approved")
        for role in roles:
            AccountRole.objects.create(account=account, role=role)
        return Account.objects.get(pk=account.pk)

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.reviewer)
        self.serial = 0

    def applicant(self, school_id, role=None, first="Ana", last="Reyes", email=None, proof=True,
                  created_at=None, profile=True, middle=None, suffix=None):
        self.serial += 1
        email = email if email is not None else f"applicant{self.serial}@example.edu"
        account = Account.objects.create_user(
            school_id=school_id, email=email or None, password=PASSWORD,
            requested_role=role or self.student,
        )
        update = {"created_at": created_at or BASE_TIME + timedelta(minutes=self.serial)}
        if proof:
            update.update(email_verified_at=BASE_TIME, email_verified_address=proof if isinstance(proof, str) else email)
        Account.objects.filter(pk=account.pk).update(**update)
        if profile:
            UserProfile.objects.create(account=account, first_name=first, middle_name=middle,
                                       last_name=last, suffix=suffix)
        return Account.objects.get(pk=account.pk)

    def get(self, query=""):
        return self.client.get(URL + query)

    def ids(self, query=""):
        response = self.get(query)
        self.assertEqual(response.status_code, 200, response.content)
        return [row["account_id"] for row in response.json()["results"]]

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json(), {"error": {"code": code, "message": response.json()["error"]["message"]}})
        self.assertNotIn("results", response.json())

    # --- Authorization -----------------------------------------------------------------

    def test_authorized_admin_lists_with_exact_envelope_and_no_store(self):
        target = self.applicant("7240001", first="Maria", middle="Luz", last="Santos", suffix="Jr.")
        response = self.get()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("no-store", response["Cache-Control"])
        payload = response.json()
        self.assertEqual(set(payload), {"results", "page", "page_size", "has_next"})
        self.assertEqual((payload["page"], payload["page_size"], payload["has_next"]), (1, 20, False))
        self.assertEqual(payload["results"], [{
            "account_id": target.pk, "school_id": "7240001", "full_name": "Maria Luz Santos Jr.",
            "requested_role": "Student", "created_at": target.created_at.isoformat(), "email_verified": True,
        }])

    def test_technical_super_admin_inherits_only_through_admin_effective_permission(self):
        self.applicant("7240002")
        both = self.approved("WF0201-TSA-ADMIN", self.admin, self.super_admin)
        alone = self.approved("WF0201-TSA-ONLY", self.super_admin)
        direct = self.approved("WF0201-TSA-DIRECT", self.super_admin)
        AccountPermission.objects.create(account=direct, permission=self.perms["read"], effect="Grant")
        for actor, expected in ((both, 200), (alone, 403), (direct, 403)):
            with self.subTest(actor=actor.school_id):
                self.client.force_login(actor)
                response = self.get()
                self.assertEqual(response.status_code, expected, response.content)
                if expected != 200:
                    self.assert_error(response, 403, "access_denied")

    def test_other_roles_and_role_less_accounts_are_denied(self):
        self.applicant("7240003")
        student = self.approved("WF0201-STUDENT", self.student)
        AccountPermission.objects.create(account=student, permission=self.perms["read"], effect="Grant")
        for actor in (
            student,
            self.approved("WF0201-INSTRUCTOR", self.instructor),
            self.approved("WF0201-TREASURER", self.student, self.treasurer),
        ):
            with self.subTest(actor=actor.school_id):
                self.client.force_login(actor)
                self.assert_error(self.get(), 403, "access_denied")

    def test_ineligible_actor_sessions_are_not_workspace_authority(self):
        role_less = self.approved("WF0201-NOROLE")
        pending_admin = Account.objects.create_user(school_id="WF0201-PENDING-ADMIN", password=PASSWORD)
        AccountRole.objects.create(account=pending_admin, role=self.admin)
        superuser = Account.objects.create(
            school_id="WF0201-FRAMEWORK", is_active=True, request_status="Approved",
            is_staff=True, is_superuser=True,
        )
        for actor in (role_less, pending_admin, superuser):
            with self.subTest(actor=actor.school_id):
                self.client.force_login(actor)
                self.assert_error(self.get(), 401, "authentication_required")

    def test_anonymous_request_is_refused(self):
        self.applicant("7240004")
        self.assert_error(Client().get(URL), 401, "authentication_required")

    def test_deny_inactive_role_revoked_grant_and_inactive_service(self):
        self.applicant("7240005")
        deny = AccountPermission.objects.create(account=self.reviewer, permission=self.perms["read"], effect="Deny")
        self.assert_error(self.get(), 403, "access_denied")
        deny.delete()
        RolePermission.objects.filter(pk=self.read_grant.pk).update(is_active=False)
        self.assert_error(self.get(), 403, "access_denied")
        RolePermission.objects.filter(pk=self.read_grant.pk).update(is_active=True)
        Service.objects.filter(pk=self.accounts_service.pk).update(is_active=False)
        self.assert_error(self.get(), 503, "review_unavailable")
        Service.objects.filter(pk=self.accounts_service.pk).update(is_active=True)
        self.assertEqual(self.get().status_code, 200)

    def test_expired_session_is_refused(self):
        self.applicant("7240006")
        session = self.client.session
        session[SEEN_AT] = session[SEEN_AT] - 2 * 3600
        session.save()
        self.assert_error(self.get(), 401, "authentication_required")

    # --- Gates and routes ----------------------------------------------------------------

    def test_list_gate_off_returns_unavailable(self):
        self.applicant("7240007")
        with override_settings(**GATES_OFF):
            self.assert_error(self.get(), 503, "review_unavailable")

    def test_list_gate_never_opens_decision_views(self):
        factory = RequestFactory()
        for view in (ApproveRegistrationRequestView, RejectRegistrationRequestView):
            with self.subTest(view=view.__name__):
                request = factory.post("/", data="{}", content_type="application/json")
                response = view.as_view()(request, account_id=1)
                self.assertEqual(response.status_code, 503)

    def test_isolated_review_configs_keep_the_existing_gate_pair(self):
        self.applicant("7240008")
        with override_settings(
            WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=False,
            WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True,
            WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
        ):
            self.assertEqual(self.get().status_code, 200)
        with override_settings(
            WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=False,
            WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True,
            WORKSPACE_REGISTRATION_APPROVAL_ENABLED=False,
        ):
            self.assert_error(self.get(), 503, "review_unavailable")

    def test_post_is_not_allowed_and_safe_methods_reveal_no_records(self):
        self.applicant("7240009", first="Hidden", last="Applicant")
        self.client.cookies[settings.CSRF_COOKIE_NAME] = "a" * 32
        response = self.client.post(URL, data="{}", content_type="application/json", HTTP_X_CSRFTOKEN="a" * 32)
        self.assert_error(response, 405, "method_not_allowed")
        self.assertEqual(self.client.post(URL, data="{}", content_type="application/json").status_code, 403)
        head = self.client.head(URL)
        self.assertEqual(head.status_code, 200)
        self.assertEqual(head.content, b"")
        options = self.client.options(URL)
        self.assertNotIn(b"7240009", options.content)
        self.assertNotIn(b"Hidden", options.content)

    # --- Record selection ----------------------------------------------------------------

    def test_only_eligible_pending_student_and_instructor_rows_are_listed(self):
        student = self.applicant("7240010")
        instructor = self.applicant("7240011", role=self.instructor)
        hidden = {
            "approved": self.applicant("7240012"),
            "rejected": self.applicant("7240013"),
            "active": self.applicant("7240014"),
            "staff": self.applicant("7240015"),
            "superuser": self.applicant("7240016"),
            "reviewed_by": self.applicant("7240017"),
            "reviewed_at": self.applicant("7240018"),
            "assigned": self.applicant("7240019"),
            "no_role": self.applicant("7240020"),
            "treasurer": self.applicant("7240021"),
        }
        Account.objects.filter(pk=hidden["approved"].pk).update(request_status="Approved")
        Account.objects.filter(pk=hidden["rejected"].pk).update(request_status="Rejected")
        Account.objects.filter(pk=hidden["active"].pk).update(is_active=True)
        Account.objects.filter(pk=hidden["staff"].pk).update(is_staff=True)
        Account.objects.filter(pk=hidden["superuser"].pk).update(is_superuser=True)
        Account.objects.filter(pk=hidden["reviewed_by"].pk).update(reviewed_by=self.reviewer)
        Account.objects.filter(pk=hidden["reviewed_at"].pk).update(reviewed_at=BASE_TIME)
        AccountRole.objects.create(account=hidden["assigned"], role=self.student)
        Account.objects.filter(pk=hidden["no_role"].pk).update(requested_role=None)
        Account.objects.filter(pk=hidden["treasurer"].pk).update(requested_role=self.treasurer)
        self.assertEqual(self.ids(), [student.pk, instructor.pk])

    def test_inactive_requested_role_is_excluded(self):
        kept = self.applicant("7240022")
        self.applicant("7240023", role=self.instructor)
        Role.objects.filter(pk=self.instructor.pk).update(is_active=False)
        self.assertEqual(self.ids(), [kept.pk])

    def test_requested_role_filter(self):
        student = self.applicant("7240024")
        instructor = self.applicant("7240025", role=self.instructor)
        self.assertEqual(self.ids("?role=Student"), [student.pk])
        self.assertEqual(self.ids("?role=Instructor"), [instructor.pk])
        row = self.get("?role=Instructor").json()["results"][0]
        self.assertEqual(row["requested_role"], "Instructor")

    def test_legacy_applications_are_listed_and_flagged_without_proof(self):
        verified = self.applicant("7240026")
        mixed_case = self.applicant("7240027", email="mixed@example.edu", proof="MIXED@Example.EDU")
        no_proof = self.applicant("7240028", proof=False)
        mismatch = self.applicant("7240029", email="now@example.edu", proof="old@example.edu")
        no_email = self.applicant("7240030", email="", proof="gone@example.edu")
        Account.objects.filter(pk=no_email.pk).update(email=None)
        flags = {row["account_id"]: row["email_verified"] for row in self.get().json()["results"]}
        self.assertEqual(flags, {
            verified.pk: True, mixed_case.pk: True,
            no_proof.pk: False, mismatch.pk: False, no_email.pk: False,
        })
        self.assertEqual(set(self.ids("?proof=verified")), {verified.pk, mixed_case.pk})
        self.assertEqual(set(self.ids("?proof=legacy")), {no_proof.pk, mismatch.pk, no_email.pk})

    def test_missing_profile_gives_null_name(self):
        target = self.applicant("7240031", profile=False)
        self.assertIsNone(self.get().json()["results"][0]["full_name"])
        self.assertEqual(self.ids(), [target.pk])

    # --- Search, sort, pagination --------------------------------------------------------

    def test_search_by_school_id_prefix_and_name_terms(self):
        a = self.applicant("7240101", first="Maria", last="Santos")
        b = self.applicant("7240102", first="Jose", last="Cruz")
        c = self.applicant("8810101", first="Ana", last="Santos-Lim")
        self.assertEqual(self.ids("?q=724"), [a.pk, b.pk])
        self.assertEqual(self.ids("?q=0101"), [])  # School ID is prefix-only
        self.assertEqual(self.ids("?q=SANTOS"), [a.pk, c.pk])
        self.assertEqual(self.ids("?q=maria%20santos"), [a.pk])
        self.assertEqual(self.ids("?q=%20%20cruz%20"), [b.pk])
        self.assertEqual(self.ids("?q=maria%20cruz"), [])
        self.assertEqual(self.ids("?q=724&role=Instructor"), [])

    def test_search_wildcards_are_literal(self):
        self.applicant("7240201", first="Plain", last="Name")
        self.applicant("7240202", first="Under_score", last="Name")
        self.assertEqual(self.ids("?q=%25"), [])
        self.assertEqual(len(self.ids("?q=_")), 1)
        self.assertEqual(self.ids("?q=P_ain"), [])  # would match "Plain" if _ were a wildcard

    def test_sort_options_and_stable_tie_breaker(self):
        same = BASE_TIME + timedelta(days=1)
        old = self.applicant("7240303", created_at=BASE_TIME)
        tie_a = self.applicant("7240301", created_at=same)
        tie_b = self.applicant("7240302", created_at=same)
        self.assertEqual(self.ids(), [old.pk, tie_a.pk, tie_b.pk])
        self.assertEqual(self.ids("?sort=submitted"), [old.pk, tie_a.pk, tie_b.pk])
        self.assertEqual(self.ids("?sort=-submitted"), [tie_b.pk, tie_a.pk, old.pk])
        self.assertEqual(self.ids("?sort=school_id"), [tie_a.pk, tie_b.pk, old.pk])
        self.assertEqual(self.ids("?sort=-school_id"), [old.pk, tie_b.pk, tie_a.pk])

    def test_pagination_has_next_is_accurate(self):
        empty = self.get().json()
        self.assertEqual(empty, {"results": [], "page": 1, "page_size": 20, "has_next": False})
        created = [self.applicant(f"72405{n:02d}") for n in range(20)]
        exact = self.get().json()
        self.assertEqual((len(exact["results"]), exact["has_next"]), (20, False))
        created.append(self.applicant("7240599"))
        first, second = self.get("?page=1").json(), self.get("?page=2").json()
        self.assertEqual((len(first["results"]), first["has_next"]), (20, True))
        self.assertEqual((len(second["results"]), second["has_next"]), (1, False))
        seen = [row["account_id"] for row in first["results"] + second["results"]]
        self.assertEqual(seen, [account.pk for account in created])
        self.assertEqual(self.get("?page=9").json(), {"results": [], "page": 9, "page_size": 20, "has_next": False})

    def test_malformed_queries_are_rejected_without_data(self):
        self.applicant("7240601")
        for query in (
            "?unknown=1", "?page=1&page=2", "?q=a&q=b", "?q=", "?q=%20%20", "?q=" + "1" * 51,
            "?q=%C3%91ame", "?q=a%0Ab", "?q=a%20b%20c%20d%20e%20f", "?role=Admin", "?role=student",
            "?role=", "?proof=yes", "?proof=", "?sort=created_at", "?sort=", "?status=Approved",
            "?page=0", "?page=10001", "?page=1e3", "?page=%2B1", "?page=%201", "?page=",
        ):
            with self.subTest(query=query):
                self.assert_error(self.get(query), 400, "invalid_request")

    def test_valid_boundary_queries(self):
        self.applicant("7240701")
        for query in ("?q=" + "7" * 50, "?status=Pending&page=10000", "?q=a%20b%20c%20d%20e"):
            with self.subTest(query=query):
                self.assertEqual(self.get(query).status_code, 200)

    # --- Data protection and failures ----------------------------------------------------

    def test_response_never_contains_email_secrets_or_reviewer_data(self):
        target = self.applicant("7240801", email="private.person@example.edu")
        Account.objects.filter(pk=target.pk).update(
            password_reset_token="rv1:otp:0:0:0:SECRET-TOKEN-VALUE",
            password_reset_token_expires=BASE_TIME, rejection_reason="SECRET-REASON",
        )
        target.refresh_from_db()
        response = self.get()
        body = response.content.decode()
        self.assertEqual(set(response.json()["results"][0]), ITEM_KEYS)
        for secret in ("private.person", "example.edu", "SECRET-TOKEN-VALUE", "SECRET-REASON",
                       target.password, "pbkdf2", "sessionid", "reviewed", "is_staff", "password"):
            self.assertNotIn(secret, body)

    def test_database_failure_returns_generic_unavailable(self):
        self.applicant("7240901")
        with patch.object(Account.objects, "filter", side_effect=OperationalError("private SQL detail")):
            response = self.get()
        self.assert_error(response, 503, "review_unavailable")
        self.assertNotIn("private SQL detail", response.content.decode())

    def test_query_count_does_not_grow_with_rows(self):
        self.applicant("7241001")
        with CaptureQueriesContext(connection) as one:
            self.assertEqual(self.get().status_code, 200)
        for n in range(15):
            self.applicant(f"72411{n:02d}", role=self.instructor if n % 2 else self.student)
        with CaptureQueriesContext(connection) as many:
            self.assertEqual(len(self.get().json()["results"]), 16)
        self.assertEqual(len(one.captured_queries), len(many.captured_queries))

    @patch.object(ReviewListThrottle, "rate", "3/min")
    def test_list_throttle_is_per_account(self):
        self.applicant("7241201")
        for _ in range(3):
            self.assertEqual(self.get().status_code, 200)
        self.assert_error(self.get(), 429, "rate_limited")
        other = self.approved("WF0201-ADMIN-2", self.admin)
        self.client.force_login(other)
        self.assertEqual(self.get().status_code, 200)
