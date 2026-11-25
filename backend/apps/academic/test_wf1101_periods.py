"""WF-11.01 academic-period foundation: rules, Draft service, HDAC and lifecycle invariants.

Run: python manage.py test apps.academic --settings=config.test_settings --noinput
Disposable MySQL only (config.test_settings + IsolatedMySQLRunner); synthetic accounts. The
lifecycle tests use a test-only prerequisites substitute that the module itself refuses outside
the verified isolated database; it never creates fee or offering records.
"""

import threading
from datetime import date
from unittest.mock import patch

from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, connection, connections, transaction
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.access_control.models import AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.accounts.active_role_context import bind_role_scope
from apps.accounts.models import Account

from . import lifecycle, periods, services
from .models import AcademicPeriodAuditLog, SchoolYear, Semester, SemesterStatus, SemesterTerm
from .periods import SchoolYearStatus

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("WF-11.01 tests require --settings=config.test_settings.")

PASSWORD = "Harbor!Lantern5821"
GATE = dict(WORKSPACE_ACADEMIC_PERIODS_ENABLED=True, WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False)
TRANSITIONS = dict(GATE, WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED=True)
CODE = "academic.periods.manage"


def verify_database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
            raise ImproperlyConfigured("Refusing WF-11.01 fixtures on an unexpected database.")


class World:
    """The pinned v2.2 default: academic.periods.manage bound to Admin only."""

    ROLE_NAMES = ("Student", "Instructor", "Treasurer", "SSG Advisor", "Admin", "Technical Super Admin")

    def __init__(self):
        verify_database()
        self.service = Service.objects.create(service_code="academic", service_name="Academic Administration")
        self.roles = {name: Role.objects.create(role_name=name) for name in self.ROLE_NAMES}
        self.perm = Permission.objects.create(
            service=self.service, permission_code=CODE, permission_name="Manage school years and periods",
            module_name="school_periods", action_name="manage")
        RolePermission.objects.create(role=self.roles["Admin"], permission=self.perm)
        self.admin = self.account("WF1101-ADMIN", "Admin")

    def account(self, school_id, *roles, status="Approved", active=True, **flags):
        account = Account.objects.create_user(school_id=school_id, password=PASSWORD,
                                              requested_role=self.roles["Student"])
        Account.objects.filter(pk=account.pk).update(request_status=status, is_active=active, **flags)
        for role in roles:
            AccountRole.objects.create(account=account, role=self.roles[role])
        return Account.objects.get(pk=account.pk)

    def deny(self, account, active=True):
        return AccountPermission.objects.create(account=account, permission=self.perm, effect="Deny", is_active=active)


class IsolatedPrerequisites(lifecycle.ActivationPrerequisites):
    """TEST ONLY: keeps the real date rule and drops the two checks whose sources do not exist yet.

    lifecycle._entry accepts a substitute only on the verified disposable database.
    """

    def missing(self, semester):
        return tuple(item for item in super().missing(semester) if item == "valid_dates")


ISOLATED = IsolatedPrerequisites()


def other_table_counts():
    """Row counts of every installed model outside the academic app (participation, fee, clearance...)."""
    counts = {}
    for model in django_apps.get_models():
        if model._meta.app_label == "academic" or not model._meta.managed:
            continue
        counts[model._meta.label] = model.objects.count()
    return counts


class PeriodRuleTests(SimpleTestCase):
    def test_school_year_status_is_derived_from_semesters(self):
        D, A, C, X = SemesterStatus.DRAFT, SemesterStatus.ACTIVE, SemesterStatus.CLOSED, SemesterStatus.ARCHIVED
        cases = {
            (D, D): SchoolYearStatus.DRAFT, (A, D): SchoolYearStatus.ACTIVE, (C, A): SchoolYearStatus.ACTIVE,
            (C, D): SchoolYearStatus.BETWEEN_SEMESTERS, (X, D): SchoolYearStatus.BETWEEN_SEMESTERS,
            (D, C): SchoolYearStatus.BETWEEN_SEMESTERS, (C, C): SchoolYearStatus.COMPLETED,
            (C, X): SchoolYearStatus.COMPLETED, (X, X): SchoolYearStatus.ARCHIVED,
        }
        for statuses, expected in cases.items():
            with self.subTest(statuses=statuses):
                self.assertEqual(periods.derive_school_year_status(statuses), expected)
        for bad in ((), ("Open",), (D, "Active ")):
            self.assertEqual(periods.derive_school_year_status(bad), SchoolYearStatus.DRAFT)

    def test_school_year_has_no_independent_status_or_active_switch(self):
        names = {field.name for field in SchoolYear._meta.get_fields()}
        self.assertFalse(names & {"status", "is_active", "active"})

    def test_strict_iso_dates_only(self):
        self.assertEqual(periods.parse_iso_date("2026-08-10"), date(2026, 8, 10))
        self.assertIsNone(periods.parse_iso_date(None))
        for bad in ("2026-8-10", "2026-13-01", "2026-02-30", "20260810", "2026-08-10T00:00", " 2026-08-10",
                    "２０２６-08-10", 20260810, True, ["2026-08-10"]):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                periods.parse_iso_date(bad)

    def test_semester_overlap_rules_allow_a_break(self):
        overlap = periods.terms_overlap
        self.assertFalse(overlap((date(2026, 8, 1), date(2026, 12, 20)), (date(2027, 1, 10), date(2027, 5, 30))))
        self.assertFalse(overlap((date(2026, 8, 1), date(2026, 12, 20)), (date(2026, 12, 21), date(2027, 5, 30))))
        self.assertTrue(overlap((date(2026, 8, 1), date(2026, 12, 20)), (date(2026, 12, 20), date(2027, 5, 30))))
        self.assertTrue(overlap((date(2026, 8, 1), date(2026, 12, 20)), (date(2026, 11, 1), date(2027, 5, 30))))
        self.assertTrue(overlap((date(2027, 1, 1), None), (date(2026, 8, 1), None)))  # Second before First
        self.assertFalse(overlap((None, None), (date(2026, 8, 1), None)))

    def test_range_rules(self):
        self.assertIsNone(periods.range_problem(date(2026, 8, 1), date(2026, 12, 20), 2026))
        self.assertIsNone(periods.range_problem(date(2026, 8, 1), None, 2026))
        self.assertEqual(periods.range_problem(date(2026, 8, 1), date(2026, 8, 1), 2026), "start_not_before_end")
        self.assertEqual(periods.range_problem(date(2026, 9, 1), date(2026, 8, 1), 2026), "start_not_before_end")
        self.assertEqual(periods.range_problem(date(2025, 12, 31), None, 2026), "outside_school_year")
        self.assertEqual(periods.range_problem(None, date(2028, 1, 1), 2026), "outside_school_year")


@override_settings(**GATE)
class DraftServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()

    def create(self, year=2026, actor=None):
        return services.create_school_year(actor=actor or self.w.admin, start_year=year)

    def dates(self, semester_id, start, end, version=1, actor=None, ack=False):
        return services.update_semester_dates(actor=actor or self.w.admin, semester_id=semester_id, start_date=start,
                                              end_date=end, expected_version=version,
                                              acknowledge_cross_year_overlap=ack)

    def conflict(self, reason, fn, *args, **kwargs):
        before = (SchoolYear.objects.count(), list(Semester.objects.values().order_by("pk")),
                  AcademicPeriodAuditLog.objects.count())
        with self.assertRaises(services.AcademicPeriodConflict) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(before, (SchoolYear.objects.count(), list(Semester.objects.values().order_by("pk")),
                                  AcademicPeriodAuditLog.objects.count()))

    def invalid(self, field, fn, *args, **kwargs):
        before = list(Semester.objects.values().order_by("pk"))
        with self.assertRaises(services.AcademicPeriodInvalid) as caught:
            fn(*args, **kwargs)
        self.assertIn(field, caught.exception.fields)
        self.assertEqual(before, list(Semester.objects.values().order_by("pk")))

    def ids(self, payload):
        return [s["semester_id"] for s in payload["semesters"]]

    # -- creation ---------------------------------------------------------------------------------
    def test_creating_a_school_year_creates_exactly_two_draft_semesters(self):
        others = other_table_counts()
        payload = self.create(2026)
        self.assertEqual((payload["start_year"], payload["end_year"], payload["label"]), (2026, 2027, "2026–2027"))
        self.assertEqual(payload["status"], SchoolYearStatus.DRAFT)
        rows = list(Semester.objects.filter(school_year_id=payload["school_year_id"]).order_by("term"))
        self.assertEqual([(s.term, s.status, s.start_date, s.end_date, s.active_slot, s.activated_at) for s in rows],
                         [(SemesterTerm.FIRST, "Draft", None, None, None, None),
                          (SemesterTerm.SECOND, "Draft", None, None, None, None)])
        self.assertEqual([s["term"] for s in payload["semesters"]], ["first", "second"])
        self.assertTrue(all(s["activation"] == {"available": False, "missing": ["valid_dates", "approved_fee",
                                                                               "academic_offerings"]}
                            for s in payload["semesters"]))
        self.assertTrue(payload["can_delete"])
        audit = AcademicPeriodAuditLog.objects.get()
        self.assertEqual((audit.actor_account_id, audit.action, audit.school_year_id, audit.acting_role_id, audit.reason),
                         (self.w.admin.pk, services.CREATE_ACTION, payload["school_year_id"], None, "period_setup"))
        self.assertEqual(audit.new_value["start_year"], 2026)
        self.assertEqual(other_table_counts(), others)  # no participation, clearance or fee records

    def test_duplicate_school_years_are_rejected_without_changes(self):
        self.create(2026)
        self.conflict("school_year_exists", self.create, 2026)
        self.assertEqual(Semester.objects.count(), 2)

    def test_invalid_start_years_are_rejected(self):
        for value in (True, "2026", 2026.0, 1999, 2101, None, -1):
            with self.subTest(value=value):
                self.invalid("start_year", services.create_school_year, actor=self.w.admin, start_year=value)
        self.assertEqual(SchoolYear.objects.count(), 0)

    def test_database_rejects_duplicate_or_invalid_semester_rows(self):
        year = SchoolYear.objects.get(pk=self.create(2026)["school_year_id"])
        for kwargs in ({"term": 1}, {"term": 2}, {"term": 3}, {"term": 0}):
            with self.subTest(**kwargs), self.assertRaises(IntegrityError), transaction.atomic():
                Semester.objects.create(school_year=year, **kwargs)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SchoolYear.objects.create(start_year=2026, created_by=self.w.admin)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Semester.objects.filter(school_year=year, term=1).update(start_date=date(2026, 9, 1), end_date=date(2026, 8, 1))
        with self.assertRaises(IntegrityError), transaction.atomic():  # a Draft that claims activation
            Semester.objects.filter(school_year=year, term=1).update(activated_at=timezone.now())

    def test_failed_creation_leaves_no_partial_records(self):
        original = Semester.save

        def fail_second(instance, *args, **kwargs):
            if instance.term == SemesterTerm.SECOND:
                raise RuntimeError("simulated failure")
            return original(instance, *args, **kwargs)

        with patch.object(Semester, "save", fail_second), self.assertRaises(RuntimeError):
            self.create(2026)
        self.assertEqual((SchoolYear.objects.count(), Semester.objects.count(), AcademicPeriodAuditLog.objects.count()),
                         (0, 0, 0))
        with patch.object(services, "write_audit", side_effect=RuntimeError("audit down")), self.assertRaises(RuntimeError):
            self.create(2026)
        self.assertEqual((SchoolYear.objects.count(), Semester.objects.count(), AcademicPeriodAuditLog.objects.count()),
                         (0, 0, 0))
        self.create(2026)  # nothing left behind blocks a clean retry
        self.assertEqual(Semester.objects.count(), 2)

    # -- dates ------------------------------------------------------------------------------------
    def test_valid_dates_with_a_break_are_saved_and_audited(self):
        first, second = self.ids(self.create(2026))
        payload = self.dates(first, "2026-08-10", "2026-12-18")
        self.assertEqual(payload["semesters"][0]["version"], 2)
        payload = self.dates(second, "2027-01-11", "2027-05-28")
        self.assertEqual((payload["semesters"][1]["start_date"], payload["semesters"][1]["end_date"]),
                         ("2027-01-11", "2027-05-28"))
        audit = AcademicPeriodAuditLog.objects.filter(action=services.DATES_ACTION).order_by("pk").last()
        self.assertEqual((audit.semester_id, audit.old_value["start_date"], audit.new_value["start_date"],
                          audit.new_value["version"]), (second, None, "2027-01-11", 2))
        self.assertEqual(audit.actor_account_id, self.w.admin.pk)
        self.dates(second, "2026-12-19", "2027-05-28", version=2)  # consecutive day: a zero-day break is allowed

    def test_draft_dates_may_be_incomplete_and_cleared(self):
        first, _ = self.ids(self.create(2026))
        self.dates(first, "2026-08-10", None)
        self.dates(first, None, None, version=2)
        self.assertEqual(Semester.objects.get(pk=first).version, 3)

    def test_invalid_dates_are_rejected(self):
        first, _ = self.ids(self.create(2026))
        for start, end, field in (("2026-08-10", "2026-08-10", "end_date"), ("2026-09-10", "2026-08-10", "end_date"),
                                  ("2025-12-31", "2026-05-01", "start_date"), ("2026-08-01", "2028-01-01", "start_date"),
                                  ("2026-13-01", None, "start_date"), (None, "10/08/2026", "end_date"),
                                  (20260810, None, "start_date")):
            with self.subTest(start=start, end=end):
                self.invalid(field, self.dates, first, start, end)
        for value in (True, 0, "1", None):
            with self.subTest(expected_version=value):
                self.invalid("expected_version", self.dates, first, None, None, version=value)

    def test_same_year_overlap_is_rejected(self):
        first, second = self.ids(self.create(2026))
        self.dates(first, "2026-08-10", "2026-12-18")
        self.conflict("semesters_overlap", self.dates, second, "2026-12-18", "2027-05-28")
        self.conflict("semesters_overlap", self.dates, second, "2026-10-01", "2027-05-28")
        self.conflict("semesters_overlap", self.dates, second, "2026-06-01", "2026-07-30")  # Second before First

    def test_stale_versions_and_unchanged_dates(self):
        first, _ = self.ids(self.create(2026))
        self.dates(first, "2026-08-10", "2026-12-18")
        self.conflict("stale_version", self.dates, first, "2026-08-11", "2026-12-18", version=1)
        audits = AcademicPeriodAuditLog.objects.count()
        self.dates(first, "2026-08-10", "2026-12-18", version=2)  # identical: no version bump, no audit
        self.assertEqual((Semester.objects.get(pk=first).version, AcademicPeriodAuditLog.objects.count()), (2, audits))

    def test_cross_year_overlap_needs_an_acknowledged_review(self):
        _, second_2026 = self.ids(self.create(2026))
        first_2027, _ = self.ids(self.create(2027))
        self.dates(second_2026, "2027-01-11", "2027-06-15")
        self.conflict("cross_year_overlap", self.dates, first_2027, "2027-06-01", "2027-10-15")
        self.dates(first_2027, "2027-06-01", "2027-10-15", ack=True)
        audit = AcademicPeriodAuditLog.objects.filter(semester_id=first_2027).get()
        self.assertIs(audit.new_value["cross_year_overlap_acknowledged"], True)
        self.invalid("acknowledge_cross_year_overlap", self.dates, first_2027, None, None, version=2, ack="yes")

    def test_unknown_semesters_are_not_found(self):
        for value in (0, -1, 2_147_483_648, "1", None):
            with self.subTest(value=value), self.assertRaises(services.AcademicPeriodNotFound):
                self.dates(value, None, None)
        with self.assertRaises(services.AcademicPeriodNotFound):
            self.dates(999_999, None, None)

    # -- deletion ---------------------------------------------------------------------------------
    def test_unused_draft_year_is_deleted_with_both_semesters_and_history_is_kept(self):
        payload = self.create(2027)
        self.dates(payload["semesters"][0]["semester_id"], "2027-08-10", None)
        result = services.delete_school_year(actor=self.w.admin, school_year_id=payload["school_year_id"],
                                             expected_start_year=2027)
        self.assertEqual(result, {"deleted": True, "school_year_id": payload["school_year_id"]})
        self.assertEqual((SchoolYear.objects.count(), Semester.objects.count()), (0, 0))
        actions = list(AcademicPeriodAuditLog.objects.filter(school_year_id=payload["school_year_id"])
                       .order_by("pk").values_list("action", flat=True))
        self.assertEqual(actions, [services.CREATE_ACTION, services.DATES_ACTION, services.DELETE_ACTION])
        deleted = AcademicPeriodAuditLog.objects.get(action=services.DELETE_ACTION)
        self.assertEqual(len(deleted.old_value["semesters"]), 2)

    def test_deletion_requires_matching_confirmation_and_no_dependents(self):
        payload = self.create(2027)
        self.conflict("confirmation_mismatch", services.delete_school_year, actor=self.w.admin,
                      school_year_id=payload["school_year_id"], expected_start_year=2026)
        with patch.object(services, "_dependents_exist", return_value=True):
            self.conflict("period_in_use", services.delete_school_year, actor=self.w.admin,
                          school_year_id=payload["school_year_id"], expected_start_year=2027)
        with self.assertRaises(services.AcademicPeriodNotFound):
            services.delete_school_year(actor=self.w.admin, school_year_id=999_999, expected_start_year=2027)

    @override_settings(**TRANSITIONS)
    def test_activated_periods_cannot_be_deleted_or_edited_and_future_drafts_coexist(self):
        first, second = self.ids(self.create(2026))
        self.dates(first, "2026-08-10", "2026-12-18")
        lifecycle.activate_semester(actor=self.w.admin, semester_id=first, expected_active_semester_id=None,
                                    confirmed=True, prerequisites=ISOLATED)
        year = SchoolYear.objects.get(start_year=2026)
        self.conflict("period_not_draft", services.delete_school_year, actor=self.w.admin,
                      school_year_id=year.pk, expected_start_year=2026)
        self.conflict("period_not_draft", self.dates, first, "2026-08-11", "2026-12-18", version=2)
        # WF11-D08: future School Years and their Draft semesters are prepared while a semester is Active.
        future = self.create(2027)
        self.dates(future["semesters"][0]["semester_id"], "2027-08-09", "2027-12-17")
        self.dates(second, "2027-01-11", "2027-05-28")  # the Active year's own Draft remains configurable
        listing = services.list_school_years(actor=self.w.admin)
        self.assertEqual([(r["start_year"], r["status"]) for r in listing["results"]],
                         [(2027, SchoolYearStatus.DRAFT), (2026, SchoolYearStatus.ACTIVE)])
        self.assertEqual([r["can_delete"] for r in listing["results"]], [True, False])
        lifecycle.close_semester(actor=self.w.admin, semester_id=first, confirmed=True, prerequisites=ISOLATED)
        self.assertEqual(services.list_school_years(actor=self.w.admin)["results"][1]["status"],
                         SchoolYearStatus.BETWEEN_SEMESTERS)
        self.conflict("period_not_draft", services.delete_school_year, actor=self.w.admin,
                      school_year_id=year.pk, expected_start_year=2026)

    def test_listing_is_ordered_paginated_and_minimized(self):
        for year in range(2001, 2023):
            self.create(year)
        page = services.list_school_years(actor=self.w.admin)
        self.assertEqual((len(page["results"]), page["has_next"], page["results"][0]["start_year"]), (20, True, 2022))
        second = services.list_school_years(actor=self.w.admin, page=2)
        self.assertEqual(([r["start_year"] for r in second["results"]], second["has_next"]), ([2002, 2001], False))
        text = repr(page)
        for hidden in ("active_slot", "created_by", "actor", self.w.admin.school_id):
            self.assertNotIn(hidden, text)
        for bad in (0, 501, True, "1"):
            with self.subTest(page=bad), self.assertRaises(services.AcademicPeriodInvalid):
                services.list_school_years(actor=self.w.admin, page=bad)


@override_settings(**GATE)
class AuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()

    def denied(self, actor, reason="access_denied"):
        with self.assertRaises(services.AcademicPeriodDenied) as caught:
            services.create_school_year(actor=actor, start_year=2030)
        self.assertEqual(caught.exception.reason, reason)
        with self.assertRaises(services.AcademicPeriodDenied):
            services.list_school_years(actor=actor)
        self.assertEqual(SchoolYear.objects.count(), 0)

    def allowed(self, actor, year=2030):
        services.create_school_year(actor=actor, start_year=year)
        return AcademicPeriodAuditLog.objects.order_by("pk").last()

    def test_authorized_school_admin_succeeds(self):
        self.assertEqual(self.allowed(self.w.admin).actor_account_id, self.w.admin.pk)

    def test_student_instructor_treasurer_and_advisor_are_denied_by_default(self):
        for role in ("Student", "Instructor", "Treasurer", "SSG Advisor"):
            with self.subTest(role=role):
                self.denied(self.w.account(f"WF1101-{role[:3].upper()}", role))

    def test_account_deny_overrides_the_admin_grant_and_inactive_deny_does_not(self):
        deny = self.w.deny(self.w.admin)
        self.denied(self.w.admin)
        AccountPermission.objects.filter(pk=deny.pk).update(is_active=False)
        self.allowed(self.w.admin)

    def test_a_direct_grant_never_replaces_a_genuine_admin_assignment(self):
        for roles in (("Technical Super Admin",), ("Treasurer",), ("Student",)):
            with self.subTest(roles=roles):
                account = self.w.account("WF1101-G" + str(len(roles[0])), *roles)
                AccountPermission.objects.create(account=account, permission=self.w.perm, effect="Grant")
                self.denied(account)

    def test_technical_super_admin_inherits_only_through_a_stored_admin_assignment(self):
        tsa = self.w.account("WF1101-TSA", "Technical Super Admin")
        RolePermission.objects.create(role=self.w.roles["Technical Super Admin"], permission=self.w.perm)
        self.denied(tsa)  # even a role-level grant: no genuine Admin assignment, no operational access
        RolePermission.objects.filter(role=self.w.roles["Technical Super Admin"]).delete()
        AccountRole.objects.create(account=tsa, role=self.w.roles["Admin"])
        self.allowed(tsa)

    def test_ineligible_accounts_are_denied(self):
        cases = {"pending": dict(status="Pending"), "rejected": dict(status="Rejected"),
                 "inactive": dict(active=False), "staff": dict(is_staff=True), "superuser": dict(is_superuser=True)}
        for label, flags in cases.items():
            with self.subTest(label):
                self.denied(self.w.account(f"WF1101-X{label[:4].upper()}", "Admin", **flags))
        for actor in (None, Account(school_id="unsaved"), "WF1101-ADMIN", self.w.admin.pk):
            with self.subTest(actor=actor):
                self.denied(actor)
        Role.objects.filter(pk=self.w.roles["Admin"].pk).update(is_active=False)
        self.denied(self.w.admin)

    def test_disabled_gate_service_or_protected_writer_deny_everything(self):
        for overrides in ({"WORKSPACE_ACADEMIC_PERIODS_ENABLED": False}, {"WORKSPACE_ACADEMIC_PERIODS_ENABLED": 1},
                          {"WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER": True},
                          {"WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER": "yes"}):
            with self.subTest(**overrides), override_settings(**overrides):
                with self.assertRaises(services.AcademicPeriodUnavailable):
                    services.create_school_year(actor=self.w.admin, start_year=2030)
                with self.assertRaises(services.AcademicPeriodUnavailable):
                    services.list_school_years(actor=self.w.admin)
        Service.objects.filter(pk=self.w.service.pk).update(is_active=False)
        with self.assertRaises(services.AcademicPeriodUnavailable):
            services.create_school_year(actor=self.w.admin, start_year=2030)
        self.assertEqual(SchoolYear.objects.count(), 0)

    def test_unprovisioned_permission_fails_closed(self):
        RolePermission.objects.all().delete()
        Permission.objects.filter(pk=self.w.perm.pk).delete()
        self.denied(self.w.admin)

    def test_authorization_is_rechecked_under_lock_for_every_mutation(self):
        real = services.authorize
        calls = []

        def revoke_after_first_check(actor):
            result = real(actor)
            calls.append(actor.pk)
            if len(calls) == 1:
                self.w.deny(self.w.admin)  # a Deny lands between the pre-check and the locked re-check
            return result

        with patch.object(services, "authorize", side_effect=revoke_after_first_check):
            with self.assertRaises(services.AcademicPeriodDenied):
                services.create_school_year(actor=self.w.admin, start_year=2030)
        self.assertEqual(SchoolYear.objects.count(), 0)
        AccountPermission.objects.all().delete()
        payload = services.create_school_year(actor=self.w.admin, start_year=2030)
        calls.clear()
        with patch.object(services, "authorize", side_effect=revoke_after_first_check):
            with self.assertRaises(services.AcademicPeriodDenied):
                services.update_semester_dates(actor=self.w.admin, semester_id=payload["semesters"][0]["semester_id"],
                                               start_date="2030-08-01", end_date=None, expected_version=1)
            calls.clear()
            AccountPermission.objects.all().delete()
            with self.assertRaises(services.AcademicPeriodDenied):
                services.delete_school_year(actor=self.w.admin, school_year_id=payload["school_year_id"],
                                            expected_start_year=2030)
        self.assertEqual((Semester.objects.filter(start_date__isnull=False).count(), SchoolYear.objects.count()), (0, 1))


@override_settings(WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True, **GATE)
class RoleContextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()
        cls.dual = cls.w.account("WF1101-DUAL", "Student", "Admin")

    def create(self, account, role_id, year=2030):
        with bind_role_scope(account.pk, role_id):
            return services.create_school_year(actor=account, start_year=year)

    def refused(self, account, role_id, reason="admin_context_required"):
        with self.assertRaises(services.AcademicPeriodDenied) as caught:
            self.create(account, role_id)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(SchoolYear.objects.count(), 0)

    def test_selected_admin_context_is_required_and_recorded(self):
        self.refused(self.dual, self.w.roles["Student"].pk)
        self.refused(self.dual, None)
        self.refused(self.dual, 999_999)
        self.refused(self.dual, self.w.roles["Treasurer"].pk)  # a role this account does not hold
        with self.assertRaises(services.AcademicPeriodDenied) as caught:
            services.create_school_year(actor=self.dual, start_year=2030)  # no scope at all
        self.assertEqual(caught.exception.reason, "admin_context_required")
        with bind_role_scope(self.w.admin.pk, self.w.roles["Admin"].pk), self.assertRaises(services.AcademicPeriodDenied):
            services.create_school_year(actor=self.dual, start_year=2030)  # another account's scope
        self.create(self.dual, self.w.roles["Admin"].pk)
        self.assertEqual(AcademicPeriodAuditLog.objects.get().acting_role_id, self.w.roles["Admin"].pk)

    def test_stale_context_fails_closed(self):
        AccountRole.objects.filter(account=self.dual, role=self.w.roles["Admin"]).delete()
        self.refused(self.dual, self.w.roles["Admin"].pk, reason="access_denied")

    def test_deny_applies_inside_an_admin_context(self):
        self.w.deny(self.dual)
        self.refused(self.dual, self.w.roles["Admin"].pk, reason="access_denied")

    def test_technical_super_admin_context_inherits_the_stored_admin_assignment_only(self):
        tsa = self.w.account("WF1101-TSAC", "Technical Super Admin")
        self.refused(tsa, self.w.roles["Technical Super Admin"].pk, reason="access_denied")
        AccountRole.objects.create(account=tsa, role=self.w.roles["Admin"])
        self.create(tsa, self.w.roles["Technical Super Admin"].pk)
        self.assertEqual(AcademicPeriodAuditLog.objects.get().acting_role_id, self.w.roles["Technical Super Admin"].pk)


@override_settings(**TRANSITIONS)
class LifecycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()

    def setUp(self):
        self.year = services.create_school_year(actor=self.w.admin, start_year=2026)
        self.first, self.second = (s["semester_id"] for s in self.year["semesters"])
        services.update_semester_dates(actor=self.w.admin, semester_id=self.first, start_date="2026-08-10",
                                       end_date="2026-12-18", expected_version=1)
        services.update_semester_dates(actor=self.w.admin, semester_id=self.second, start_date="2027-01-11",
                                       end_date="2027-05-28", expected_version=1)

    def activate(self, semester_id, expected=None, prerequisites=ISOLATED, confirmed=True):
        return lifecycle.activate_semester(actor=self.w.admin, semester_id=semester_id,
                                           expected_active_semester_id=expected, confirmed=confirmed,
                                           prerequisites=prerequisites)

    def refused(self, reason, fn, *args, **kwargs):
        before = list(Semester.objects.values().order_by("pk"))
        with self.assertRaises(lifecycle.TransitionRefused) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(before, list(Semester.objects.values().order_by("pk")))
        return caught.exception

    def statuses(self):
        return dict(Semester.objects.values_list("pk", "status"))

    def test_transitions_are_unavailable_unless_the_undefined_gate_is_overridden(self):
        import config.settings as base_settings
        import config.test_settings as isolated_settings
        for module in (base_settings, isolated_settings):
            self.assertFalse(hasattr(module, lifecycle.TRANSITIONS_SETTING))
        with override_settings(WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED=False):
            for fn in (lambda: self.activate(self.first), lambda: lifecycle.close_semester(
                    actor=self.w.admin, semester_id=self.first, confirmed=True),
                    lambda: lifecycle.archive_semester(actor=self.w.admin, semester_id=self.first, confirmed=True)):
                with self.assertRaises(services.AcademicPeriodUnavailable):
                    fn()

    def test_real_preflight_fails_closed_and_never_fabricates_fee_or_offerings(self):
        error = self.refused("prerequisites_missing", self.activate, self.first, prerequisites=None)
        self.assertEqual(error.missing, ("approved_fee", "academic_offerings"))
        self.assertEqual(lifecycle.preflight(Semester.objects.get(pk=self.first)), ["approved_fee", "academic_offerings"])
        Semester.objects.filter(pk=self.first).update(end_date=None)
        self.assertEqual(lifecycle.preflight(Semester.objects.get(pk=self.first)),
                         ["valid_dates", "approved_fee", "academic_offerings"])

    def test_substitute_prerequisites_are_refused_outside_the_isolated_database(self):
        with patch.object(lifecycle, "_isolated_test_database", return_value=False):
            with self.assertRaises(services.AcademicPeriodUnavailable):
                self.activate(self.first)
        self.assertEqual(set(self.statuses().values()), {"Draft"})

    def test_activation_requires_dates_confirmation_and_permission(self):
        Semester.objects.filter(pk=self.first).update(end_date=None)
        error = self.refused("prerequisites_missing", self.activate, self.first)
        self.assertEqual(error.missing, ("valid_dates",))
        self.refused("confirmation_required", self.activate, self.second, confirmed="yes")
        self.w.deny(self.w.admin)
        with self.assertRaises(services.AcademicPeriodDenied):
            self.activate(self.second)
        self.assertEqual(set(self.statuses().values()), {"Draft"})

    def test_atomic_one_active_transition_closes_the_previous_semester(self):
        others = other_table_counts()
        self.activate(self.first)
        self.assertEqual(self.statuses(), {self.first: "Active", self.second: "Draft"})
        self.refused("active_changed", self.activate, self.second, expected=None)
        self.activate(self.second, expected=self.first)
        self.assertEqual(self.statuses(), {self.first: "Closed", self.second: "Active"})
        self.assertEqual(Semester.objects.filter(status="Active").count(), 1)
        actions = list(AcademicPeriodAuditLog.objects.filter(action__startswith="academic.semester.")
                       .exclude(action=services.DATES_ACTION).order_by("pk").values_list("action", "semester_id"))
        self.assertEqual(actions, [(lifecycle.ACTIVATE_ACTION, self.first), (lifecycle.CLOSE_ACTION, self.first),
                                   (lifecycle.ACTIVATE_ACTION, self.second)])
        self.assertEqual(other_table_counts(), others)  # activation never creates participation/clearance/fees

    def test_failed_transition_rolls_back_completely(self):
        self.activate(self.first)
        real = services.write_audit

        def fail_on_activate(auth, **kwargs):
            if kwargs["action"] == lifecycle.ACTIVATE_ACTION:
                raise RuntimeError("audit down")
            return real(auth, **kwargs)

        before = list(Semester.objects.values().order_by("pk"))
        with patch.object(services, "write_audit", side_effect=fail_on_activate), self.assertRaises(RuntimeError):
            self.activate(self.second, expected=self.first)
        self.assertEqual(before, list(Semester.objects.values().order_by("pk")))  # no half-closed semester

    def test_database_backstop_forbids_two_active_semesters(self):
        self.activate(self.first)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Semester.objects.filter(pk=self.second).update(status="Active", active_slot=1, activated_at=timezone.now())
        with self.assertRaises(IntegrityError), transaction.atomic():  # Active without its slot
            Semester.objects.filter(pk=self.second).update(status="Active", activated_at=timezone.now())

    def test_closed_and_archived_periods_are_never_reopened(self):
        self.activate(self.first)
        lifecycle.close_semester(actor=self.w.admin, semester_id=self.first, confirmed=True)
        self.refused("not_draft", self.activate, self.first)
        self.refused("not_active", lifecycle.close_semester, actor=self.w.admin, semester_id=self.first, confirmed=True)
        self.refused("not_closed", lifecycle.archive_semester, actor=self.w.admin, semester_id=self.second, confirmed=True)
        lifecycle.archive_semester(actor=self.w.admin, semester_id=self.first, confirmed=True)
        self.refused("not_draft", self.activate, self.first)
        row = Semester.objects.get(pk=self.first)
        self.assertEqual((row.status, row.active_slot), ("Archived", None))
        self.assertTrue(row.activated_at and row.closed_at and row.archived_at)
        with self.assertRaises(IntegrityError), transaction.atomic():  # the database refuses a reopen too
            Semester.objects.filter(pk=self.first).update(status="Draft")


class ConcurrencyTests(TransactionTestCase):
    def tearDown(self):
        connections.close_all()

    def race(self, *calls):
        barrier = threading.Barrier(len(calls))
        results = [None] * len(calls)

        def run(index, fn):
            try:
                barrier.wait(5)
                results[index] = ("ok", fn())
            except Exception as exc:  # noqa: BLE001 - reported to the test
                results[index] = ("error", exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=run, args=(i, fn)) for i, fn in enumerate(calls)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
        return results

    @override_settings(**GATE)
    def test_concurrent_duplicate_creation_yields_one_year_with_two_semesters(self):
        w = World()
        results = self.race(*[lambda: services.create_school_year(actor=w.admin, start_year=2026)] * 3)
        oks = [r for r in results if r[0] == "ok"]
        errors = [r[1] for r in results if r[0] == "error"]
        self.assertEqual(len(oks), 1, results)
        self.assertTrue(all(isinstance(e, services.AcademicPeriodConflict) and e.reason == "school_year_exists"
                            for e in errors), errors)
        self.assertEqual((SchoolYear.objects.count(), Semester.objects.count(),
                          AcademicPeriodAuditLog.objects.count()), (1, 2, 1))

    @override_settings(**TRANSITIONS)
    def test_concurrent_activations_never_produce_two_active_semesters(self):
        w = World()
        ids = []
        for year in (2026, 2027):
            payload = services.create_school_year(actor=w.admin, start_year=year)
            first = payload["semesters"][0]["semester_id"]
            services.update_semester_dates(actor=w.admin, semester_id=first, start_date=f"{year}-08-10",
                                           end_date=f"{year}-12-18", expected_version=1)
            ids.append(first)
        results = self.race(*[
            (lambda sid=sid: lifecycle.activate_semester(actor=w.admin, semester_id=sid, expected_active_semester_id=None,
                                                         confirmed=True, prerequisites=ISOLATED)) for sid in ids])
        self.assertEqual(sum(r[0] == "ok" for r in results), 1, results)
        refused = [r[1] for r in results if r[0] == "error"]
        self.assertTrue(all(isinstance(e, lifecycle.TransitionRefused) and e.reason == "active_changed" for e in refused))
        self.assertEqual(Semester.objects.filter(status="Active").count(), 1)
        self.assertEqual(AcademicPeriodAuditLog.objects.filter(action=lifecycle.ACTIVATE_ACTION).count(), 1)

    @override_settings(**GATE)
    def test_concurrent_date_edits_with_the_same_version_apply_once(self):
        w = World()
        first = services.create_school_year(actor=w.admin, start_year=2026)["semesters"][0]["semester_id"]
        results = self.race(*[
            (lambda day=day: services.update_semester_dates(actor=w.admin, semester_id=first, start_date=f"2026-08-{day}",
                                                            end_date="2026-12-18", expected_version=1))
            for day in ("10", "11")])
        self.assertEqual(sum(r[0] == "ok" for r in results), 1, results)
        self.assertTrue(all(isinstance(r[1], services.AcademicPeriodConflict) and r[1].reason == "stale_version"
                            for r in results if r[0] == "error"))
        self.assertEqual(Semester.objects.get(pk=first).version, 2)
        self.assertEqual(AcademicPeriodAuditLog.objects.filter(action=services.DATES_ACTION).count(), 1)
