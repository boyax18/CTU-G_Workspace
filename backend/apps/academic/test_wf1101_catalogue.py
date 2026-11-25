"""WF-11.01 current academic period (academic.catalogue.read), actionable readiness, and the full
School Admin lifecycle over HTTP: prepare -> configure -> approve fee -> explicitly activate.

Run: python manage.py test apps.academic.test_wf1101_catalogue --settings=config.test_settings --noinput
Disposable MySQL only. The fee success path uses the explicit throwaway-database-only Admin fee
binding from apps.finance.test_semester_fees.FeeWorld.grant_admin_fee (never an application grant).
"""

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.access_control.models import AccountPermission, Permission, RolePermission, Service
from apps.accounts.active_role_context import bind_role_scope
from apps.finance import fees
from apps.finance.test_semester_fees import FEES, FeeWorld, other_counts

from . import catalogue, configuration as cfg, services
from .models import Semester
from .test_wf1101_http import post, signed_in

CATALOGUE = dict(FEES, WORKSPACE_ACADEMIC_CATALOGUE_ENABLED=True)
FULL = dict(CATALOGUE, WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED=True)
CURRENT = "/api/v1/academic/catalogue/current-period/"
ACADEMIC = "/api/v1/academic/"
FEE_ROOT = "/api/v1/finance/semester-fees/"


class CatalogueWorld(FeeWorld):
    """FeeWorld + the pinned v2.0 academic.catalogue.read defaults (Student, Instructor, Treasurer, Admin)."""

    def __init__(self):
        super().__init__()
        self.catalogue = Permission.objects.create(service=self.service, permission_code=catalogue.CATALOGUE_CODE,
                                                   permission_name="Read academic catalogue", module_name="catalogue",
                                                   action_name="read")
        for role in ("Student", "Instructor", "Treasurer", "Admin"):
            RolePermission.objects.create(role=self.roles[role], permission=self.catalogue)
        self.student = self.account("WF1101-CSTU", "Student")


def prepare(w, start=2026):
    """School Admin flow through the real services: plan, dates, offering, approved fee."""
    from .test_academic_configuration import build_plan
    p = build_plan(w, start)
    services.update_semester_dates(actor=w.admin, semester_id=p["first"], start_date=f"{start}-08-10",
                                   end_date=f"{start}-12-18", expected_version=1)
    cfg.create_offering(actor=w.admin, semester_id=p["first"], section_id=p["section"]["section_id"],
                        curriculum_subject_id=p["entries"]["MATH 101"])
    return p


@override_settings(**CATALOGUE)
class CurrentPeriodTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = CatalogueWorld()

    def setUp(self):
        cache.clear()

    def test_every_catalogue_role_reads_the_current_period_and_nothing_else(self):
        self.assertEqual(catalogue.current_period(actor=self.w.student), {"active": None})
        for school_id, role in (("WF1101-CINS", "Instructor"), ("WF1101-CTRE", "Treasurer")):
            with self.subTest(role=role):
                self.assertEqual(catalogue.current_period(actor=self.w.account(school_id, role)), {"active": None})
        reply = signed_in(self.w.student).get(CURRENT)
        self.assertEqual((reply.status_code, reply.json()), (200, {"active": None}), reply.content)
        self.assertIn("no-store", reply["Cache-Control"])

    def test_refusals_fail_closed(self):
        none = self.w.account("WF1101-CNONE", "Technical Super Admin")  # no catalogue binding for this role
        with self.assertRaises(services.AcademicPeriodDenied):
            catalogue.current_period(actor=none)
        AccountPermission.objects.create(account=self.w.student, permission=self.w.catalogue, effect="Deny")
        with self.assertRaises(services.AcademicPeriodDenied):
            catalogue.current_period(actor=self.w.student)
        for flags in ({"is_staff": True}, {"status": "Pending"}, {"active": False}):
            with self.subTest(**{k: str(v) for k, v in flags.items()}), self.assertRaises(services.AcademicPeriodDenied):
                catalogue.current_period(actor=self.w.account(f"WF1101-CX{len(flags)}{list(flags)[0][:3]}", "Student", **flags))
        Service.objects.filter(pk=self.w.service.pk).update(is_active=False)
        with self.assertRaises(services.AcademicPeriodUnavailable):
            catalogue.current_period(actor=self.w.admin)
        anonymous = signed_in(self.w.student)
        anonymous.logout()
        self.assertEqual(anonymous.get(CURRENT).status_code, 401)

    @override_settings(WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True)
    def test_role_context_is_enforced(self):
        with bind_role_scope(self.w.student.pk, self.w.roles["Student"].pk):
            self.assertEqual(catalogue.current_period(actor=self.w.student), {"active": None})
        for role_id in (None, 999_999):
            with self.subTest(role_id=role_id), bind_role_scope(self.w.student.pk, role_id), \
                    self.assertRaises(services.AcademicPeriodDenied):
                catalogue.current_period(actor=self.w.student)

    def test_switch_is_default_off_and_independent(self):
        import config.settings as base
        self.assertIs(base.WORKSPACE_ACADEMIC_CATALOGUE_ENABLED, False)
        with override_settings(WORKSPACE_ACADEMIC_CATALOGUE_ENABLED=False):
            reply = signed_in(self.w.student).get(CURRENT)
            self.assertEqual((reply.status_code, reply.json()["error"]["code"]), (503, "academic_catalogue_unavailable"))
        with override_settings(WORKSPACE_ACADEMIC_PERIODS_ENABLED=False):  # the catalogue never opens management
            self.assertEqual(signed_in(self.w.admin).get(ACADEMIC + "school-years/").status_code, 503)
            self.assertEqual(signed_in(self.w.student).get(CURRENT).status_code, 200)


@override_settings(**FULL)
class ReadinessAndLifecycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = CatalogueWorld()
        cls.w.grant_admin_fee()  # TEST ONLY: the binding a reviewed overlay would add

    def setUp(self):
        cache.clear()
        self.client = signed_in(self.w.admin)

    def checks(self, start=2026):
        year = next(y for y in self.client.get(ACADEMIC + "school-years/").json()["results"] if y["start_year"] == start)
        first = year["semesters"][0]
        return first, {c["key"]: (c["status"], c["reason"]) for c in first["activation"]["checks"]}

    def test_readiness_reasons_follow_the_real_records(self):
        from .test_academic_configuration import build_plan
        p = build_plan(self.w)
        first, checks = self.checks()
        self.assertEqual(checks, {"valid_dates": ("missing", "dates_incomplete"),
                                  "approved_fee": ("missing", "no_fee_configured"),
                                  "academic_offerings": ("missing", "no_valid_offerings")})
        self.assertFalse(first["activation"]["available"])
        services.update_semester_dates(actor=self.w.admin, semester_id=p["first"], start_date="2026-08-10",
                                       end_date="2026-12-18", expected_version=1)
        cfg.create_offering(actor=self.w.admin, semester_id=p["first"], section_id=p["section"]["section_id"],
                            curriculum_subject_id=p["entries"]["MATH 101"])
        fees.save_draft(actor=self.w.admin, semester_id=p["first"], amount="1500", expected_draft_version=None)
        _first, checks = self.checks()
        self.assertEqual(checks["approved_fee"], ("missing", "fee_awaiting_approval"))
        self.assertEqual((checks["valid_dates"][0], checks["academic_offerings"][0]), ("ready", "ready"))
        with override_settings(WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED=False):
            self.assertEqual(self.checks()[1]["approved_fee"], ("unavailable", "fee_source_disabled"))

    def test_full_lifecycle_over_http_activates_only_on_explicit_confirmation(self):
        p = prepare(self.w)
        student = signed_in(self.w.student)  # signed in before the snapshot: its session is not an activation effect
        others = other_counts()
        reply = post(self.client, f"{FEE_ROOT}{p['first']}/draft/", {"amount": "1500.00", "expected_draft_version": None})
        self.assertEqual(reply.status_code, 200, reply.content)
        preview = self.client.get(f"{FEE_ROOT}{p['first']}/approval/").json()
        reply = post(self.client, f"{FEE_ROOT}{p['first']}/approval/", {
            "revision_id": preview["proposed"]["revision_id"], "expected_version": preview["proposed"]["version"],
            "expected_current_approved_revision_id": None, "acknowledged_warnings": preview["warnings"], "confirmed": True})
        self.assertEqual(reply.status_code, 200, reply.content)
        first, checks = self.checks()
        self.assertEqual(set(checks.values()), {("ready", "")})
        self.assertTrue(first["activation"]["available"])
        self.assertEqual(Semester.objects.get(pk=p["first"]).status, "Draft")  # still not activated
        self.assertEqual(student.get(CURRENT).json(), {"active": None})
        activation = self.client.get(f"{ACADEMIC}semesters/{p['first']}/activation/").json()
        self.assertTrue(activation["can_confirm"], activation)
        reply = post(self.client, f"{ACADEMIC}semesters/{p['first']}/activation/", {
            "confirmed": True, "expected_version": activation["semester"]["version"],
            "expected_active_semester_id": None, "acknowledged_warnings": activation["warnings"]})
        self.assertEqual((reply.status_code, reply.json()["status"]), (200, "Active"), reply.content)
        current = student.get(CURRENT).json()["active"]
        self.assertEqual((current["semester_id"], current["label"], current["school_year_label"], current["start_date"]),
                         (p["first"], "First semester", "2026–2027", "2026-08-10"))
        self.assertEqual(set(current), {"semester_id", "term", "label", "school_year_id", "school_year_label",
                                        "start_date", "end_date"})
        self.assertEqual(other_counts(), others)  # no participation, clearance, obligation or payment created

    def test_unauthorized_activation_and_fee_requests_change_nothing(self):
        p = prepare(self.w)
        body = {"confirmed": True, "expected_version": 2, "expected_active_semester_id": None, "acknowledged_warnings": []}
        for account in (self.w.student, self.w.treasurer, self.w.instructor):
            client = signed_in(account)
            with self.subTest(account=account.school_id):
                self.assertEqual(post(client, f"{ACADEMIC}semesters/{p['first']}/activation/", body).status_code, 403)
                self.assertEqual(post(client, f"{FEE_ROOT}{p['first']}/draft/",
                                      {"amount": "1", "expected_draft_version": None}).status_code, 403)
        self.assertEqual(post(self.client, f"{ACADEMIC}semesters/{p['first']}/activation/", body, csrf=False).status_code, 403)
        self.assertEqual(Semester.objects.get(pk=p["first"]).status, "Draft")
        self.assertFalse(fees.SemesterFeeRevision.objects.exists())
