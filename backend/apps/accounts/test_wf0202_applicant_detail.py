"""WF-02.02 Verify and review applicant information: isolated MySQL HTTP tests (P-07).

Run: python manage.py test apps.accounts.test_wf0202_applicant_detail --settings=config.test_settings --noinput
Uses the real config.urls routes with the read switch enabled ONLY inside these tests.
Every record is created in the disposable test database.
"""

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import OperationalError, connection
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import resolve

from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service,
)

from .models import Account, UserProfile
from .registration_review_api import (
    ApproveRegistrationRequestView, PendingRegistrationDetailView, ReviewListThrottle,
)
from .session_timeout import SEEN_AT


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Use --settings=config.test_settings for WF-02.02 tests.")

LIST = "/api/v1/admin/registration-requests/"
PASSWORD = "Copper!River7799"
KEYS = {"account_id", "school_id", "id_label", "name", "full_name", "email", "requested_role", "request_status",
        "created_at", "email_evidence", "institutional_check", "data_notes"}
BASE_TIME = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
WRITE_PREFIXES = ("INSERT", "UPDATE", "DELETE", "REPLACE")
APPLICANT_TABLES = ("`accounts`", "`users`", "`account_roles`", "`account_permissions`", "`access_audit_logs`")


def detail(account_id):
    return f"{LIST}{account_id}/"


@override_settings(
    ROOT_URLCONF="config.urls",
    WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=True,
    WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=False,
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=False,
)
class ApplicantDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.accounts_service = Service.objects.create(service_code="accounts", service_name="Accounts")
        cls.access_service = Service.objects.create(service_code="access_control", service_name="Access Control")
        cls.student = Role.objects.create(role_name="Student")
        cls.instructor = Role.objects.create(role_name="Instructor")
        cls.treasurer = Role.objects.create(role_name="Treasurer")
        cls.admin = Role.objects.create(role_name="Admin")
        cls.super_admin = Role.objects.create(role_name="Technical Super Admin")
        cls.read = Permission.objects.create(
            service=cls.accounts_service, permission_code="accounts.registration_requests.read",
            permission_name="Registration requests read", module_name="registration_requests", action_name="read",
        )
        cls.read_grant = RolePermission.objects.create(role=cls.admin, permission=cls.read)
        cls.reviewer = cls.approved("WF0202-ADMIN", cls.admin)

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

    def applicant(self, school_id, role=None, email=None, proof=True, profile=True, **names):
        self.serial += 1
        email = email if email is not None else f"person{self.serial}@example.edu"
        account = Account.objects.create_user(
            school_id=school_id, email=email or None, password=PASSWORD, requested_role=role or self.student,
        )
        update = {"created_at": BASE_TIME + timedelta(minutes=self.serial)}
        if proof:
            update.update(email_verified_at=BASE_TIME, email_verified_address=proof if isinstance(proof, str) else email)
        Account.objects.filter(pk=account.pk).update(**update)
        if profile:
            values = {"first_name": "Maria", "middle_name": "Luz", "last_name": "Santos", "suffix": None}
            values.update(names)
            UserProfile.objects.create(account=account, **values)
        return Account.objects.get(pk=account.pk)

    def get(self, path):
        return self.client.get(path)

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        body = response.json()
        self.assertEqual(set(body), {"error"})
        self.assertEqual(body["error"]["code"], code)

    # --- Content -------------------------------------------------------------------------

    def test_student_detail_has_exact_fields_and_no_store(self):
        target = self.applicant("7240001", email="maria.santos@example.edu", suffix="Jr.")
        response = self.get(detail(target.pk))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response.json(), {
            "account_id": target.pk, "school_id": "7240001", "id_label": "School ID",
            "name": {"first": "Maria", "middle": "Luz", "last": "Santos", "suffix": "Jr."},
            "full_name": "Maria Luz Santos Jr.", "email": "maria.santos@example.edu",
            "requested_role": "Student", "request_status": "Pending", "created_at": target.created_at.isoformat(),
            "email_evidence": {"state": "verified", "verified_at": target.email_verified_at.isoformat()},
            "institutional_check": {"subject": "enrollment", "verified_by_workspace": False},
            "data_notes": [],
        })

    def test_instructor_detail_uses_staff_id_and_employment(self):
        target = self.applicant("0012345", role=self.instructor, middle_name="")
        body = self.get(detail(target.pk)).json()
        self.assertEqual((body["id_label"], body["school_id"], body["requested_role"]), ("Staff ID", "0012345", "Instructor"))
        self.assertEqual(body["institutional_check"], {"subject": "employment", "verified_by_workspace": False})
        self.assertIsNone(body["name"]["middle"])

    def test_four_email_evidence_states(self):
        cases = {
            "verified": self.applicant("7240101"),
            "mixed case": self.applicant("7240102", email="case@example.edu", proof="CASE@Example.EDU"),
            "no_proof": self.applicant("7240103", proof=False),
            "address_changed": self.applicant("7240104", email="now@example.edu", proof="old@example.edu"),
            "no_email": self.applicant("7240105", email="", proof="gone@example.edu"),
        }
        Account.objects.filter(pk=cases["no_email"].pk).update(email=None)
        expected = {"verified": "verified", "mixed case": "verified", "no_proof": "no_proof",
                    "address_changed": "address_changed", "no_email": "no_email"}
        for label, account in cases.items():
            with self.subTest(case=label):
                body = self.get(detail(account.pk)).json()
                self.assertEqual(body["email_evidence"]["state"], expected[label])
                if expected[label] == "verified":
                    self.assertIsNotNone(body["email_evidence"]["verified_at"])
                else:
                    self.assertIsNone(body["email_evidence"]["verified_at"])
        self.assertIsNone(self.get(detail(cases["no_email"].pk)).json()["email"])

    def test_missing_profile_and_name_parts_are_reported_not_inferred(self):
        no_profile = self.applicant("7240201", profile=False)
        blank = self.applicant("7240202", first_name="  ", last_name="")
        body = self.get(detail(no_profile.pk)).json()
        self.assertEqual(body["data_notes"], ["missing_profile"])
        self.assertEqual(body["name"], {"first": None, "middle": None, "last": None, "suffix": None})
        self.assertIsNone(body["full_name"])
        self.assertEqual(self.get(detail(blank.pk)).json()["data_notes"], ["missing_first_name", "missing_last_name"])

    # --- Authorization ---------------------------------------------------------------------

    def test_technical_super_admin_only_through_admin(self):
        target = self.applicant("7240301")
        both = self.approved("WF0202-TSA-ADMIN", self.admin, self.super_admin)
        alone = self.approved("WF0202-TSA-ONLY", self.super_admin)
        direct = self.approved("WF0202-TSA-DIRECT", self.super_admin)
        AccountPermission.objects.create(account=direct, permission=self.read, effect="Grant")
        for actor, status in ((both, 200), (alone, 403), (direct, 403)):
            with self.subTest(actor=actor.school_id):
                self.client.force_login(actor)
                self.assertEqual(self.get(detail(target.pk)).status_code, status)

    def test_other_roles_and_ineligible_sessions_are_refused(self):
        target = self.applicant("7240302")
        student = self.approved("WF0202-STUDENT", self.student)
        AccountPermission.objects.create(account=student, permission=self.read, effect="Grant")
        for actor in (student, self.approved("WF0202-INSTR", self.instructor), self.approved("WF0202-TREAS", self.student, self.treasurer)):
            with self.subTest(actor=actor.school_id):
                self.client.force_login(actor)
                self.assert_error(self.get(detail(target.pk)), 403, "access_denied")
        superuser = Account.objects.create(school_id="WF0202-FW", is_active=True, request_status="Approved",
                                           is_staff=True, is_superuser=True)
        for actor in (self.approved("WF0202-NOROLE"), superuser):
            with self.subTest(actor=actor.school_id):
                self.client.force_login(actor)
                self.assert_error(self.get(detail(target.pk)), 401, "authentication_required")
        self.assert_error(Client().get(detail(target.pk)), 401, "authentication_required")

    def test_deny_inactive_grant_inactive_role_and_inactive_service(self):
        target = self.applicant("7240303")
        deny = AccountPermission.objects.create(account=self.reviewer, permission=self.read, effect="Deny")
        self.assert_error(self.get(detail(target.pk)), 403, "access_denied")
        deny.delete()
        RolePermission.objects.filter(pk=self.read_grant.pk).update(is_active=False)
        self.assert_error(self.get(detail(target.pk)), 403, "access_denied")
        RolePermission.objects.filter(pk=self.read_grant.pk).update(is_active=True)
        Role.objects.filter(pk=self.admin.pk).update(is_active=False)
        self.assertIn(self.get(detail(target.pk)).status_code, {401, 403})
        Role.objects.filter(pk=self.admin.pk).update(is_active=True)
        Service.objects.filter(pk=self.accounts_service.pk).update(is_active=False)
        self.assert_error(self.get(detail(target.pk)), 503, "review_unavailable")
        Service.objects.filter(pk=self.accounts_service.pk).update(is_active=True)
        self.assertEqual(self.get(detail(target.pk)).status_code, 200)

    def test_expired_session_is_refused(self):
        target = self.applicant("7240304")
        session = self.client.session
        session[SEEN_AT] = session[SEEN_AT] - 2 * 3600
        session.save()
        self.assert_error(self.get(detail(target.pk)), 401, "authentication_required")

    def test_switch_off_and_decision_views_stay_closed(self):
        target = self.applicant("7240305")
        with override_settings(WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=False):
            self.assert_error(self.get(detail(target.pk)), 503, "review_unavailable")
        request = RequestFactory().post("/", data="{}", content_type="application/json")
        self.assertEqual(ApproveRegistrationRequestView.as_view()(request, account_id=target.pk).status_code, 503)
        self.client.cookies[settings.CSRF_COOKIE_NAME] = "a" * 32
        response = self.client.post(detail(target.pk), data="{}", content_type="application/json", HTTP_X_CSRFTOKEN="a" * 32)
        self.assert_error(response, 405, "method_not_allowed")
        self.assertEqual(self.client.post(detail(target.pk), data="{}", content_type="application/json").status_code, 403)
        for path in (detail(target.pk) + "approve/", detail(target.pk) + "reject/"):
            self.assertEqual(self.get(path).status_code, 404)

    # --- Identifiers and eligibility ---------------------------------------------------------

    def test_unavailable_identifiers_share_one_safe_404(self):
        self.applicant("7240401")
        for account_id in (0, 999999, 2_147_483_648, 10 ** 12):
            with self.subTest(account_id=account_id):
                self.assert_error(self.get(detail(account_id)), 404, "request_unavailable")
        for raw in ("abc", "-1", "1.5", "%20"):
            with self.subTest(raw=raw):
                self.assertEqual(self.get(f"{LIST}{raw}/").status_code, 404)
        self.assert_error(self.get(detail(self.reviewer.pk)), 404, "request_unavailable")

    def test_ineligible_targets_are_indistinguishable_from_missing(self):
        targets = {name: self.applicant(f"72405{i:02d}") for i, name in enumerate(
            ["approved", "rejected", "active", "staff", "superuser", "reviewed_by", "reviewed_at", "assigned", "no_role", "treasurer"])}
        Account.objects.filter(pk=targets["approved"].pk).update(request_status="Approved")
        Account.objects.filter(pk=targets["rejected"].pk).update(request_status="Rejected")
        Account.objects.filter(pk=targets["active"].pk).update(is_active=True)
        Account.objects.filter(pk=targets["staff"].pk).update(is_staff=True)
        Account.objects.filter(pk=targets["superuser"].pk).update(is_superuser=True)
        Account.objects.filter(pk=targets["reviewed_by"].pk).update(reviewed_by=self.reviewer)
        Account.objects.filter(pk=targets["reviewed_at"].pk).update(reviewed_at=BASE_TIME)
        AccountRole.objects.create(account=targets["assigned"], role=self.student)
        Account.objects.filter(pk=targets["no_role"].pk).update(requested_role=None)
        Account.objects.filter(pk=targets["treasurer"].pk).update(requested_role=self.treasurer)
        missing = self.get(detail(999999))
        for label, account in targets.items():
            with self.subTest(case=label):
                response = self.get(detail(account.pk))
                self.assertEqual((response.status_code, response.content), (missing.status_code, missing.content))

    def test_status_change_between_list_and_detail(self):
        target = self.applicant("7240601")
        self.assertIn(target.pk, [row["account_id"] for row in self.get(LIST).json()["results"]])
        self.assertEqual(self.get(detail(target.pk)).status_code, 200)
        Account.objects.filter(pk=target.pk).update(request_status="Approved", is_active=True)
        self.assert_error(self.get(detail(target.pk)), 404, "request_unavailable")
        UserProfile.objects.filter(account=target).delete()  # same order as the real rejection path
        Account.objects.filter(pk=target.pk).delete()
        self.assert_error(self.get(detail(target.pk)), 404, "request_unavailable")

    def test_query_fields_are_rejected(self):
        target = self.applicant("7240701")
        for query in ("?x=1", "?status=Pending", "?applicant=1"):
            with self.subTest(query=query):
                self.assert_error(self.get(detail(target.pk) + query), 400, "invalid_request")

    # --- Read-only guarantees and data protection ---------------------------------------------

    def test_reading_never_writes_and_keeps_the_applicant_in_the_queue(self):
        target = self.applicant("7240801")
        before = Account.objects.filter(pk=target.pk).values().get()
        counts = (Account.objects.count(), UserProfile.objects.count(), AccountRole.objects.count(), AccessAuditLog.objects.count())
        with CaptureQueriesContext(connection) as queries:
            for _ in range(3):
                self.assertEqual(self.get(detail(target.pk)).status_code, 200)
                self.client.head(detail(target.pk))
        writes = [q["sql"] for q in queries.captured_queries
                  if q["sql"].lstrip().upper().startswith(WRITE_PREFIXES) and any(t in q["sql"] for t in APPLICANT_TABLES)]
        self.assertEqual(writes, [])
        self.assertEqual(Account.objects.filter(pk=target.pk).values().get(), before)
        self.assertEqual(counts, (Account.objects.count(), UserProfile.objects.count(), AccountRole.objects.count(), AccessAuditLog.objects.count()))
        self.assertIn(target.pk, [row["account_id"] for row in self.get(LIST).json()["results"]])

    def test_no_secrets_reviewer_or_session_data_in_the_body(self):
        target = self.applicant("7240901")
        Account.objects.filter(pk=target.pk).update(
            password_reset_token="rv1:otp:0:0:0:SECRET-TOKEN-VALUE", password_reset_token_expires=BASE_TIME,
            rejection_reason="SECRET-REASON",
        )
        target.refresh_from_db()
        response = self.get(detail(target.pk))
        body = response.content.decode()
        self.assertEqual(set(response.json()), KEYS)
        for secret in ("SECRET-TOKEN-VALUE", "SECRET-REASON", target.password, "pbkdf2", "sessionid", "reviewed",
                       "is_staff", "is_superuser", "password", "token", "otp"):
            self.assertNotIn(secret, body)
        self.assertNotIn("email", self.get(LIST).json()["results"][0])

    def test_database_failure_is_generic_and_does_not_leak_the_email(self):
        target = self.applicant("7241001", email="private.person@example.edu")
        with patch.object(Account.objects, "filter", side_effect=OperationalError("private.person@example.edu SQL")):
            with self.assertLogs(level="DEBUG") as logs:
                response = self.get(detail(target.pk))
                logging.getLogger("apps.accounts").debug("probe")  # assertLogs needs one record
        self.assert_error(response, 503, "review_unavailable")
        self.assertNotIn("private.person", response.content.decode())
        self.assertFalse(any("private.person" in line for line in logs.output))

    def test_query_count_is_constant(self):
        a = self.applicant("7241101")
        b = self.applicant("7241102", role=self.instructor, profile=False)
        with CaptureQueriesContext(connection) as first:
            self.get(detail(a.pk))
        with CaptureQueriesContext(connection) as second:
            self.get(detail(b.pk))
        self.assertEqual(len(first.captured_queries), len(second.captured_queries))

    @patch.object(ReviewListThrottle, "rate", "3/min")
    def test_detail_shares_the_per_account_read_budget_with_the_list(self):
        target = self.applicant("7241201")
        self.assertEqual(self.get(LIST).status_code, 200)
        self.assertEqual(self.get(detail(target.pk)).status_code, 200)
        self.assertEqual(self.get(detail(target.pk)).status_code, 200)
        self.assert_error(self.get(detail(target.pk)), 429, "rate_limited")
        self.client.force_login(self.approved("WF0202-ADMIN-2", self.admin))
        self.assertEqual(self.get(detail(target.pk)).status_code, 200)

    def test_route_is_get_only_and_bound_to_the_detail_view(self):
        match = resolve("/api/v1/admin/registration-requests/1/", urlconf="config.urls")
        self.assertEqual(match.url_name, "registration-review-detail")
        self.assertIs(match.func.view_class, PendingRegistrationDetailView)
        self.assertEqual(match.func.view_class.http_method_names, ["get", "head", "options"])
