"""WF-11.01 HTTP contract: default-off gate, session/CSRF, HDAC, errors, routes and safeguards.

Run: python manage.py test apps.academic --settings=config.test_settings --noinput
Disposable MySQL only. Requests go through the real config.urls.
"""

from django.conf import settings
from django.contrib import admin
from django.core.cache import cache
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import URLPattern, URLResolver, get_resolver, resolve

from apps.access_control.management.commands import init_registration_review_metadata_local_dev as p1
from apps.accounts.active_role_context import SESSION_ROLE_KEY
from config import dev_features

from .api import (
    SchoolYearCollectionView, SchoolYearDeleteView, SchoolYearHistoryView, SemesterActivationView,
    SemesterArchiveView, SemesterClosureView, SemesterCorrectionView, SemesterDatesView,
)
from .models import AcademicPeriodAuditLog, SchoolYear, Semester
from .test_wf1101_periods import GATE, World

ROOT = "/api/v1/academic/"
YEARS = ROOT + "school-years/"
TOKEN = "e" * 32
ROLE_CONTEXT = dict(WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True,
                    MIDDLEWARE=[*settings.MIDDLEWARE, "apps.accounts.active_role_context.ActiveRoleContextMiddleware"])
YEAR_KEYS = {"school_year_id", "start_year", "end_year", "label", "status", "semesters", "can_delete",
             "created_at", "updated_at"}
SEMESTER_KEYS = {"semester_id", "term", "label", "status", "start_date", "end_date", "version", "can_edit_dates",
                 "activation", "updated_at"}


def signed_in(account):
    client = Client(enforce_csrf_checks=True)
    client.force_login(account)
    client.cookies[settings.CSRF_COOKIE_NAME] = TOKEN
    return client


def post(client, path, body, csrf=True):
    extra = {"HTTP_X_CSRFTOKEN": TOKEN} if csrf else {}
    return client.post(path, data=body, content_type="application/json", **extra)


def state():
    return (list(SchoolYear.objects.values().order_by("pk")), list(Semester.objects.values().order_by("pk")),
            AcademicPeriodAuditLog.objects.count())


class RouteSurfaceTests(SimpleTestCase):
    def academic_routes(self):
        found = {}

        def walk(patterns, prefix=""):
            for entry in patterns:
                if isinstance(entry, URLResolver):
                    walk(entry.url_patterns, prefix + str(entry.pattern))
                elif isinstance(entry, URLPattern) and (prefix + str(entry.pattern)).startswith("api/v1/academic/"):
                    found[prefix + str(entry.pattern)] = entry.callback.view_class
        walk(get_resolver("config.urls").url_patterns)
        return found

    def test_exact_academic_routes_and_no_fee_curriculum_or_participation_route(self):
        routes = self.academic_routes()
        for route in routes:
            for word in ("fee", "participation", "enrol", "clearance", "signature"):
                self.assertNotIn(word, route)
        period_routes = {r: v for r, v in routes.items() if not r.startswith("api/v1/academic/config/")}
        self.assertEqual(period_routes, {
            "api/v1/academic/school-years/": SchoolYearCollectionView,
            "api/v1/academic/school-years/<int:school_year_id>/delete/": SchoolYearDeleteView,
            "api/v1/academic/school-years/<int:school_year_id>/history/": SchoolYearHistoryView,
            "api/v1/academic/semesters/<int:semester_id>/dates/": SemesterDatesView,
            "api/v1/academic/semesters/<int:semester_id>/activation/": SemesterActivationView,
            "api/v1/academic/semesters/<int:semester_id>/closure/": SemesterClosureView,
            "api/v1/academic/semesters/<int:semester_id>/archive/": SemesterArchiveView,
            "api/v1/academic/semesters/<int:semester_id>/corrections/": SemesterCorrectionView,
        })
        self.assertEqual(SemesterDatesView.http_method_names, ["post", "options"])
        self.assertEqual(SchoolYearDeleteView.http_method_names, ["post", "options"])
        self.assertEqual(SchoolYearHistoryView.http_method_names, ["get", "head", "options"])
        for route in period_routes:
            for word in ("curriculum", "offering"):
                self.assertNotIn(word, route)
        self.assertEqual(resolve(YEARS).url_name, "academic-school-years")

    def test_existing_review_release_safeguard_still_holds(self):
        self.assertEqual(p1.unexpected_review_routes("config.urls"), [])
        from config.review_decision_local_urls import urlpatterns as local  # -Local profile includes config.urls
        self.assertTrue(any(isinstance(p, URLResolver) and str(p.pattern) == "api/v1/academic/" for p in local))

    def test_gates_default_off_and_no_unrestricted_admin_write_path(self):
        import config.settings as base
        self.assertIs(base.WORKSPACE_ACADEMIC_PERIODS_ENABLED, False)
        self.assertIs(base.WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED, False)
        self.assertIs(base.WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED, False)
        for model in (SchoolYear, Semester, AcademicPeriodAuditLog):
            self.assertFalse(admin.site.is_registered(model))

    def test_launcher_registers_the_feature_without_approving_any_mode(self):
        for key in ("wf11.academic_periods", "wf11.academic_period_lifecycle"):
            feature = next(f for f in dev_features.FEATURES if f.key == key)
            self.assertEqual(feature.modes, frozenset())
        for mode, extra in (("local", {}), ("lan", {"lan_ip": "192.168.1.20"})):
            result = dev_features.mode_environment(mode, env={}, **extra)
            self.assertEqual(result["frontend_env"]["VITE_WORKSPACE_ACADEMIC_PERIODS_ENABLED"], "0")
            for flag in ("VITE_WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED",
                         "VITE_WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED"):
                self.assertEqual(result["frontend_env"][flag], "0")
            for flag in ("WORKSPACE_ACADEMIC_PERIODS_ENABLED", "WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED",
                         "WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED"):
                self.assertNotIn(flag, result["backend_env"])


class GateOffTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()

    def setUp(self):
        cache.clear()

    def test_default_configuration_exposes_nothing(self):
        client = signed_in(self.w.admin)
        before = state()
        replies = [client.get(YEARS), post(client, YEARS, {"start_year": 2026}),
                   post(client, ROOT + "semesters/1/dates/", {"start_date": None, "end_date": None, "expected_version": 1}),
                   post(client, YEARS + "1/delete/", {"expected_start_year": 2026}), Client().get(YEARS),
                   client.get(YEARS + "1/history/")]
        for action in ("activation", "closure", "archive", "corrections"):
            replies += [client.get(f"{ROOT}semesters/1/{action}/"), post(client, f"{ROOT}semesters/1/{action}/", {})]
        for reply in replies:
            self.assertEqual(reply.status_code, 503, reply.content)
            self.assertEqual(reply.json()["error"]["code"], "academic_periods_unavailable")
        self.assertEqual(state(), before)


@override_settings(**GATE)
class HTTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()

    def setUp(self):
        cache.clear()
        self.client = signed_in(self.w.admin)

    def create(self, year=2026, client=None):
        return post(client or self.client, YEARS, {"start_year": year})

    def test_school_admin_end_to_end_draft_management(self):
        reply = self.create(2026)
        self.assertEqual(reply.status_code, 201, reply.content)
        self.assertIn("no-store", reply["Cache-Control"])
        body = reply.json()
        self.assertEqual(set(body), YEAR_KEYS)
        self.assertEqual([set(s) for s in body["semesters"]], [SEMESTER_KEYS, SEMESTER_KEYS])
        self.assertEqual([(s["term"], s["status"]) for s in body["semesters"]], [("first", "Draft"), ("second", "Draft")])
        first = body["semesters"][0]
        reply = post(self.client, f"{ROOT}semesters/{first['semester_id']}/dates/",
                     {"start_date": "2026-08-10", "end_date": "2026-12-18", "expected_version": 1})
        self.assertEqual(reply.status_code, 200, reply.content)
        self.assertEqual(reply.json()["semesters"][0]["version"], 2)
        listing = self.client.get(YEARS)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual([r["start_year"] for r in listing.json()["results"]], [2026])
        text = listing.content.decode()
        for hidden in ("active_slot", "created_by", "actor", self.w.admin.school_id, "acting_role"):
            self.assertNotIn(hidden, text)
        reply = post(self.client, f"{YEARS}{body['school_year_id']}/delete/", {"expected_start_year": 2026})
        self.assertEqual((reply.status_code, reply.json()), (200, {"deleted": True, "school_year_id": body["school_year_id"]}))
        self.assertEqual((SchoolYear.objects.count(), Semester.objects.count()), (0, 0))

    def test_unauthenticated_and_csrf_failures_do_not_mutate(self):
        self.create(2026)
        before = state()
        anonymous = Client(enforce_csrf_checks=True)
        anonymous.cookies[settings.CSRF_COOKIE_NAME] = TOKEN
        self.assertEqual(anonymous.get(YEARS).status_code, 401)
        reply = post(anonymous, YEARS, {"start_year": 2027})
        self.assertEqual((reply.status_code, reply.json()["error"]["code"]), (401, "authentication_required"))
        reply = post(self.client, YEARS, {"start_year": 2027}, csrf=False)
        self.assertEqual((reply.status_code, reply.json()["error"]["code"]), (403, "csrf_failed"))
        self.assertEqual(state(), before)

    def test_students_instructors_treasurers_and_denied_admins_get_403(self):
        self.create(2026)
        before = state()
        accounts = [self.w.account(f"WF1101-H{role[:3].upper()}", role) for role in ("Student", "Instructor", "Treasurer")]
        denied_admin = self.w.account("WF1101-HDENY", "Admin")
        self.w.deny(denied_admin)
        for account in [*accounts, denied_admin]:
            client = signed_in(account)
            for reply in (client.get(YEARS), post(client, YEARS, {"start_year": 2027})):
                with self.subTest(account=account.school_id):
                    self.assertEqual((reply.status_code, reply.json()["error"]["code"]), (403, "access_denied"))
        self.assertEqual(state(), before)

    def test_validation_and_conflicts_use_fixed_messages(self):
        for body in ({"start_year": True}, {"start_year": "2026"}, {"start_year": 1999}):
            reply = post(self.client, YEARS, body)
            self.assertEqual(reply.status_code, 400, body)
            self.assertEqual(reply.json()["error"]["fields"], {"start_year": ["Enter a starting year from 2000 to 2100."]})
        for body in ({}, {"start_year": 2026, "status": "Active"}, [2026]):
            self.assertEqual(post(self.client, YEARS, body).status_code, 400, body)
        bad_json = self.client.post(YEARS, data='{"start_year": 2026, "start_year": 2027}', content_type="application/json",
                                    HTTP_X_CSRFTOKEN=TOKEN)
        self.assertEqual(bad_json.status_code, 400)
        self.assertEqual(self.create(2026).status_code, 201)
        reply = self.create(2026)
        self.assertEqual((reply.status_code, reply.json()["error"]["reason"]), (409, "school_year_exists"))
        first = Semester.objects.get(term=1).pk
        dates = f"{ROOT}semesters/{first}/dates/"
        reply = post(self.client, dates, {"start_date": "2026-09-01", "end_date": "2026-08-01", "expected_version": 1})
        self.assertEqual(reply.json()["error"]["fields"], {"end_date": ["The end date must be after the start date."]})
        reply = post(self.client, dates, {"start_date": "<script>", "end_date": None, "expected_version": 1})
        self.assertNotIn("<script>", reply.content.decode())
        self.assertEqual(post(self.client, dates, {"start_date": None, "end_date": None}).status_code, 400)
        reply = post(self.client, dates, {"start_date": None, "end_date": None, "expected_version": 9})
        self.assertEqual((reply.status_code, reply.json()["error"]["reason"]), (409, "stale_version"))
        reply = post(self.client, f"{ROOT}semesters/999999/dates/", {"start_date": None, "end_date": None, "expected_version": 1})
        self.assertEqual((reply.status_code, reply.json()["error"]["code"]), (404, "period_unavailable"))
        self.assertEqual(self.client.get(YEARS, {"page": "x"}).status_code, 400)
        self.assertEqual(self.client.get(YEARS, {"sort": "start_year"}).status_code, 400)
        self.assertEqual(self.client.delete(YEARS, HTTP_X_CSRFTOKEN=TOKEN).status_code, 405)

    def test_duplicate_submissions_create_one_record(self):
        replies = [self.create(2026).status_code for _ in range(3)]
        self.assertEqual(replies, [201, 409, 409])
        self.assertEqual((SchoolYear.objects.count(), Semester.objects.count(), AcademicPeriodAuditLog.objects.count()),
                         (1, 2, 1))

    def test_writes_are_rate_limited_per_account(self):
        codes = [self.create(2001 + i).status_code for i in range(21)]
        self.assertEqual(codes[:20], [201] * 20)
        self.assertEqual(codes[20], 429)


@override_settings(**ROLE_CONTEXT, **GATE)
class HTTPRoleContextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()
        cls.dual = cls.w.account("WF1101-HDUAL", "Student", "Admin")

    def setUp(self):
        cache.clear()

    def client_for(self, role_name=None):
        client = signed_in(self.dual)
        if role_name is not None:
            session = client.session
            session[SESSION_ROLE_KEY] = self.w.roles[role_name].pk
            session.save()
        return client

    def test_selected_admin_context_is_required_for_writes_and_reads(self):
        for role_name in (None, "Student"):
            client = self.client_for(role_name)
            for reply in (client.get(YEARS), post(client, YEARS, {"start_year": 2026})):
                with self.subTest(role=role_name):
                    self.assertEqual(reply.status_code, 403, reply.content)
                    self.assertEqual(reply.json()["error"]["reason"], "admin_context_required")
        self.assertEqual(SchoolYear.objects.count(), 0)
        reply = post(self.client_for("Admin"), YEARS, {"start_year": 2026})
        self.assertEqual(reply.status_code, 201, reply.content)
        self.assertEqual(AcademicPeriodAuditLog.objects.get().acting_role_id, self.w.roles["Admin"].pk)
