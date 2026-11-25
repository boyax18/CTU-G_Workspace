"""Academic configuration foundation: courses, subjects, sections, curricula, offerings, teaching.

Run: python manage.py test apps.academic.test_academic_configuration --settings=config.test_settings --noinput
Disposable MySQL only; synthetic accounts and definitions. Permissions mirror the pinned v2.0
defaults: every code below is bound to Admin only.
"""

import threading
from decimal import Decimal
from unittest.mock import patch

from django.db import IntegrityError, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.access_control.models import AccountPermission, AccountRole, Permission, RolePermission, Service
from apps.accounts.active_role_context import bind_role_scope
from apps.accounts.models import Account

from . import configuration as cfg
from . import dependencies, lifecycle, services, teaching
from .models import (
    AcademicConfigurationAuditLog, Course, CurriculumSubject, CurriculumVersion, Section, Semester, Subject,
    SubjectOffering, TeachingAssignment,
)
from .test_wf1101_periods import GATE, World, activate, bundle, close, other_table_counts

CONFIG = dict(GATE, WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED=True, WORKSPACE_ACADEMIC_CURRICULUM_WRITES_ENABLED=True,
              WORKSPACE_ACADEMIC_OFFERING_WRITES_ENABLED=True, WORKSPACE_ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED=True)
CODES = {"academic": ("academic.courses.manage", "academic.sections.manage"),
         "clearance": ("clearance.subjects.manage", "clearance.teaching_assignments.manage")}


class ConfigWorld(World):
    """World + the pinned v2.0 Admin defaults for courses, sections, subjects and teaching assignments."""

    def __init__(self):
        super().__init__()
        self.clearance = Service.objects.create(service_code="clearance", service_name="Clearance")
        self.perms = {CODE: self.perm for CODE in ("academic.periods.manage",)}
        for service, codes in CODES.items():
            for code in codes:
                perm = Permission.objects.create(service=self.service if service == "academic" else self.clearance,
                                                 permission_code=code, permission_name=code, module_name="m",
                                                 action_name="manage")
                RolePermission.objects.create(role=self.roles["Admin"], permission=perm)
                self.perms[code] = perm
        self.instructor = self.account("WF1101-INST1", "Instructor")
        self.instructor2 = self.account("WF1101-INST2", "Instructor")

    def deny_code(self, account, code):
        return AccountPermission.objects.create(account=account, permission=self.perms[code], effect="Deny")


def build_plan(w, start=2026):
    """Course + subjects + Published curriculum + section + a Draft School Year (real services)."""
    course = cfg.create_course(actor=w.admin, code="bsit", name="Bachelor of Science in Information Technology")
    math = cfg.create_subject(actor=w.admin, code="math 101", title="Mathematics in the Modern World", lecture_units=3)
    prog = cfg.create_subject(actor=w.admin, code="IT 102", title="Computer Programming 1", lecture_units=2, lab_units=1)
    curriculum = cfg.create_curriculum(actor=w.admin, course_id=course["course_id"], label="2024 Revised",
                                       effective_start_year=2024)
    cid = curriculum["curriculum_id"]
    curriculum = cfg.add_curriculum_entry(actor=w.admin, curriculum_id=cid, subject_id=math["subject_id"], year_level=1,
                                          term="first", expected_version=1)
    curriculum = cfg.add_curriculum_entry(actor=w.admin, curriculum_id=cid, subject_id=prog["subject_id"], year_level=1,
                                          term="second", expected_version=2)
    curriculum = cfg.publish_curriculum(actor=w.admin, curriculum_id=cid, expected_version=3, confirmed=True)
    section = cfg.create_section(actor=w.admin, course_id=course["course_id"], year_level=1, name="1-a")
    year = services.create_school_year(actor=w.admin, start_year=start)
    first, second = (s["semester_id"] for s in year["semesters"])
    entries = {e["subject"]["code"]: e["curriculum_subject_id"] for e in curriculum["entries"]}
    return dict(course=course, math=math, prog=prog, curriculum=curriculum, section=section, first=first,
                second=second, year=year, entries=entries)


@override_settings(**CONFIG)
class DefinitionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = ConfigWorld()

    def conflict(self, reason, fn, **kwargs):
        before = AcademicConfigurationAuditLog.objects.count()
        with self.assertRaises(cfg.ConfigurationConflict) as caught:
            fn(**kwargs)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(AcademicConfigurationAuditLog.objects.count(), before)

    def invalid(self, field, fn, **kwargs):
        with self.assertRaises(services.AcademicPeriodInvalid) as caught:
            fn(**kwargs)
        self.assertIn(field, caught.exception.fields)

    def test_course_codes_are_normalized_unique_and_audited(self):
        course = cfg.create_course(actor=self.w.admin, code="  bs   it ", name="  Information   Technology ")
        self.assertEqual((course["code"], course["name"], course["status"], course["in_use"]),
                         ("BS IT", "Information Technology", "Active", False))
        self.conflict("code_exists", cfg.create_course, actor=self.w.admin, code="BS IT", name="Duplicate")
        self.conflict("code_exists", cfg.create_course, actor=self.w.admin, code="bs it", name="Duplicate")
        for code in ("", "-BSIT", "BS_IT", "B" * 21, "ＢＳＩＴ!", 12, None):
            with self.subTest(code=code):
                self.invalid("code", cfg.create_course, actor=self.w.admin, code=code, name="X")
        self.invalid("name", cfg.create_course, actor=self.w.admin, code="BSED", name="   ")
        audit = AcademicConfigurationAuditLog.objects.get(action="academic.course.create")
        self.assertEqual((audit.actor_account_id, audit.entity_id, audit.new_value["code"]),
                         (self.w.admin.pk, course["course_id"], "BS IT"))

    def test_course_edits_status_and_retirement(self):
        course = cfg.create_course(actor=self.w.admin, code="BSED", name="Education")
        cid = course["course_id"]
        course = cfg.update_course(actor=self.w.admin, course_id=cid, code="BSED", name="Secondary Education",
                                   expected_version=1)
        self.assertEqual((course["name"], course["version"]), ("Secondary Education", 2))
        self.conflict("stale_version", cfg.update_course, actor=self.w.admin, course_id=cid, code="BSED", name="X",
                      expected_version=1)
        self.conflict("no_change", cfg.update_course, actor=self.w.admin, course_id=cid, code="BSED",
                      name="Secondary Education", expected_version=2)
        course = cfg.set_course_status(actor=self.w.admin, course_id=cid, status="Inactive", expected_version=2)
        course = cfg.set_course_status(actor=self.w.admin, course_id=cid, status="Active", expected_version=3)
        course = cfg.set_course_status(actor=self.w.admin, course_id=cid, status="Retired", expected_version=4)
        self.conflict("invalid_transition", cfg.set_course_status, actor=self.w.admin, course_id=cid, status="Active",
                      expected_version=5)
        self.conflict("not_available", cfg.create_section, actor=self.w.admin, course_id=cid, year_level=1, name="A")
        self.conflict("not_available", cfg.create_curriculum, actor=self.w.admin, course_id=cid, label="2025")
        self.assertEqual(Course.objects.filter(pk=cid).count(), 1)  # retired, never deleted

    def test_subject_units_integrity_and_version_safe_references(self):
        subject = cfg.create_subject(actor=self.w.admin, code="ge 1", title="Understanding the Self",
                                     classification="General education", lecture_units="3", lab_units=0)
        self.assertEqual((subject["code"], subject["lecture_units"], subject["lab_units"]), ("GE 1", "3.0", "0.0"))
        blank = cfg.create_subject(actor=self.w.admin, code="GE 2", title="Readings")
        self.assertEqual((blank["lecture_units"], blank["classification"]), (None, None))  # never invented
        for units in (31, -1, "1.25", True, "abc", [3], float("nan")):
            with self.subTest(units=units):
                self.invalid("lecture_units", cfg.create_subject, actor=self.w.admin, code="GE 9", title="T",
                             lecture_units=units)
        self.conflict("code_exists", cfg.create_subject, actor=self.w.admin, code="GE 1", title="Copy")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Subject.objects.filter(pk=subject["subject_id"]).update(lab_units=Decimal("45.0"))
        plan = build_plan(self.w)
        sid = plan["math"]["subject_id"]
        self.conflict("in_use", cfg.update_subject, actor=self.w.admin, subject_id=sid, code="MATH 101",
                      title="Renamed", lecture_units=3, expected_version=1)
        self.conflict("in_use", cfg.update_subject, actor=self.w.admin, subject_id=sid, code="MATH 101",
                      title="Mathematics in the Modern World", lecture_units=4, expected_version=1)
        updated = cfg.update_subject(actor=self.w.admin, subject_id=sid, code="MATH 101",
                                     title="Mathematics in the Modern World", classification="General education",
                                     lecture_units=3, expected_version=1)
        self.assertEqual((updated["classification"], updated["in_use"]), ("General education", True))

    def test_sections_are_unique_per_course_and_year_and_protected_once_used(self):
        plan = build_plan(self.w)
        course_id = plan["course"]["course_id"]
        self.conflict("section_exists", cfg.create_section, actor=self.w.admin, course_id=course_id, year_level=1,
                      name="1-A")
        other = cfg.create_section(actor=self.w.admin, course_id=course_id, year_level=2, name="1-A")
        self.assertEqual(other["year_level"], 2)
        for level in (0, 7, "1", True):
            with self.subTest(level=level):
                self.invalid("year_level", cfg.create_section, actor=self.w.admin, course_id=course_id,
                             year_level=level, name="Z")
        cfg.create_offering(actor=self.w.admin, semester_id=plan["first"], section_id=plan["section"]["section_id"],
                            curriculum_subject_id=plan["entries"]["MATH 101"])
        self.conflict("in_use", cfg.update_section, actor=self.w.admin, section_id=plan["section"]["section_id"],
                      year_level=1, name="1-B", expected_version=1)
        with self.assertRaises(services.AcademicPeriodNotFound):
            cfg.create_section(actor=self.w.admin, course_id=999_999, year_level=1, name="A")


@override_settings(**CONFIG)
class CurriculumTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = ConfigWorld()

    def setUp(self):
        self.course = cfg.create_course(actor=self.w.admin, code="BSIT", name="Information Technology")
        self.subject = cfg.create_subject(actor=self.w.admin, code="IT 101", title="Introduction to Computing")
        self.subject2 = cfg.create_subject(actor=self.w.admin, code="IT 103", title="Discrete Structures")
        self.cur = cfg.create_curriculum(actor=self.w.admin, course_id=self.course["course_id"], label="2018")

    def add(self, subject, version, cid=None, year=1, term="first"):
        return cfg.add_curriculum_entry(actor=self.w.admin, curriculum_id=cid or self.cur["curriculum_id"],
                                        subject_id=subject["subject_id"], year_level=year, term=term,
                                        expected_version=version)

    def refused(self, reason, fn, **kwargs):
        with self.assertRaises(cfg.ConfigurationConflict) as caught:
            fn(**kwargs)
        self.assertEqual(caught.exception.reason, reason)

    def test_draft_versioning_unique_entries_and_publication(self):
        cid = self.cur["curriculum_id"]
        self.assertEqual((self.cur["status"], self.cur["can_edit"]), ("Draft", True))
        self.refused("curriculum_empty", cfg.publish_curriculum, actor=self.w.admin, curriculum_id=cid,
                     expected_version=1, confirmed=True)
        cur = self.add(self.subject, 1)
        self.refused("entry_exists", self.add, subject=self.subject, version=2, year=2, term="second")
        self.refused("stale_version", self.add, subject=self.subject2, version=1)
        cur = self.add(self.subject2, 2, year=1, term="second")
        self.assertEqual([(e["year_level"], e["term"], e["subject"]["code"]) for e in cur["entries"]],
                         [(1, "first", "IT 101"), (1, "second", "IT 103")])
        with self.assertRaises(IntegrityError), transaction.atomic():
            CurriculumSubject.objects.create(curriculum_id=cid, subject_id=self.subject["subject_id"], year_level=3, term=1)
        cur = cfg.remove_curriculum_entry(actor=self.w.admin, curriculum_id=cid,
                                          curriculum_subject_id=cur["entries"][1]["curriculum_subject_id"],
                                          expected_version=3)
        self.assertEqual((cur["entry_count"], cur["version"]), (1, 4))
        with self.assertRaises(services.AcademicPeriodInvalid):
            cfg.publish_curriculum(actor=self.w.admin, curriculum_id=cid, expected_version=4, confirmed="yes")
        cur = cfg.publish_curriculum(actor=self.w.admin, curriculum_id=cid, expected_version=4, confirmed=True)
        self.assertEqual((cur["status"], cur["can_edit"]), ("Published", False))
        self.assertTrue(cur["published_at"])

    def test_published_and_superseded_versions_are_immutable_history(self):
        cid = self.cur["curriculum_id"]
        self.add(self.subject, 1)
        cfg.publish_curriculum(actor=self.w.admin, curriculum_id=cid, expected_version=2, confirmed=True)
        self.refused("not_draft", self.add, subject=self.subject2, version=3)
        self.refused("not_draft", cfg.update_curriculum, actor=self.w.admin, curriculum_id=cid, label="2018 B",
                     effective_start_year=None, expected_version=3)
        self.refused("not_draft", cfg.delete_draft_curriculum, actor=self.w.admin, curriculum_id=cid, expected_version=3)
        # A second version of the same course; labels are unique per course regardless of case.
        self.refused("label_exists", cfg.create_curriculum, actor=self.w.admin, course_id=self.course["course_id"],
                     label="2018")
        newer = cfg.create_curriculum(actor=self.w.admin, course_id=self.course["course_id"], label="2024")
        self.add(self.subject2, 1, cid=newer["curriculum_id"])
        cfg.publish_curriculum(actor=self.w.admin, curriculum_id=newer["curriculum_id"], expected_version=2,
                               confirmed=True)
        self.assertEqual(CurriculumVersion.objects.get(pk=cid).status, "Published")  # never silently replaced
        old = cfg.supersede_curriculum(actor=self.w.admin, curriculum_id=cid, expected_version=3, confirmed=True)
        self.assertEqual((old["status"], old["entry_count"]), ("Superseded", 1))
        self.refused("not_published", cfg.supersede_curriculum, actor=self.w.admin, curriculum_id=cid,
                     expected_version=4, confirmed=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CurriculumVersion.objects.filter(pk=cid).update(status="Draft")

    def test_only_unpublished_drafts_are_deleted_and_history_is_kept(self):
        cid = self.cur["curriculum_id"]
        self.add(self.subject, 1)
        result = cfg.delete_draft_curriculum(actor=self.w.admin, curriculum_id=cid, expected_version=2)
        self.assertEqual(result, {"deleted": True, "curriculum_id": cid})
        self.assertFalse(CurriculumVersion.objects.filter(pk=cid).exists())
        self.assertEqual(list(AcademicConfigurationAuditLog.objects.filter(entity_type="curriculum", entity_id=cid)
                              .order_by("pk").values_list("action", flat=True)),
                         ["academic.curriculum.create", "academic.curriculum.entry.add", "academic.curriculum.delete_draft"])
        self.assertTrue(Subject.objects.filter(pk=self.subject["subject_id"]).exists())

    def test_inactive_subjects_cannot_enter_a_curriculum_or_be_published(self):
        cfg.set_subject_status(actor=self.w.admin, subject_id=self.subject2["subject_id"], status="Inactive",
                               expected_version=1)
        self.refused("not_available", self.add, subject=self.subject2, version=1)
        self.add(self.subject, 1)
        cfg.set_subject_status(actor=self.w.admin, subject_id=self.subject["subject_id"], status="Inactive",
                               expected_version=1)
        self.refused("not_available", cfg.publish_curriculum, actor=self.w.admin,
                     curriculum_id=self.cur["curriculum_id"], expected_version=2, confirmed=True)


@override_settings(**CONFIG)
class OfferingAndActivationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = ConfigWorld()

    def setUp(self):
        self.p = build_plan(self.w)

    def offer(self, semester=None, entry="MATH 101", section=None):
        return cfg.create_offering(actor=self.w.admin, semester_id=semester or self.p["first"],
                                   section_id=section or self.p["section"]["section_id"],
                                   curriculum_subject_id=self.p["entries"][entry])

    def refused(self, reason, fn, *args, **kwargs):
        before = (SubjectOffering.objects.count(), AcademicConfigurationAuditLog.objects.count())
        with self.assertRaises(cfg.ConfigurationConflict) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(before, (SubjectOffering.objects.count(), AcademicConfigurationAuditLog.objects.count()))

    def test_valid_offering_and_reference_validation(self):
        offering = self.offer()
        self.assertEqual((offering["subject"]["code"], offering["semester"]["term"], offering["assignment"],
                          offering["ready_for_confirmation"], offering["can_remove"]),
                         ("MATH 101", "first", None, False, True))
        self.refused("offering_exists", self.offer)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SubjectOffering.objects.create(semester_id=self.p["first"], section_id=self.p["section"]["section_id"],
                                           curriculum_subject_id=self.p["entries"]["MATH 101"],
                                           subject_id=self.p["math"]["subject_id"], created_by=self.w.admin)
        self.refused("reference_mismatch", self.offer, entry="IT 102")  # a Second-semester plan in the First
        second_year = cfg.create_section(actor=self.w.admin, course_id=self.p["course"]["course_id"], year_level=2,
                                         name="2-A")
        self.refused("reference_mismatch", self.offer, section=second_year["section_id"])
        other = cfg.create_course(actor=self.w.admin, code="BSED", name="Education")
        foreign = cfg.create_section(actor=self.w.admin, course_id=other["course_id"], year_level=1, name="1-A")
        self.refused("reference_mismatch", self.offer, section=foreign["section_id"])
        self.offer(semester=self.p["second"], entry="IT 102")
        candidates = cfg.offering_candidates(actor=self.w.admin, semester_id=self.p["second"],
                                             section_id=self.p["section"]["section_id"])
        self.assertEqual(candidates["results"], [])  # IT 102 is already offered

    def test_draft_curricula_cannot_be_offered(self):
        draft = cfg.create_curriculum(actor=self.w.admin, course_id=self.p["course"]["course_id"], label="2026 Draft")
        draft = cfg.add_curriculum_entry(actor=self.w.admin, curriculum_id=draft["curriculum_id"],
                                         subject_id=self.p["prog"]["subject_id"], year_level=1, term="first",
                                         expected_version=1)
        self.refused("not_published", cfg.create_offering, actor=self.w.admin, semester_id=self.p["first"],
                     section_id=self.p["section"]["section_id"],
                     curriculum_subject_id=draft["entries"][0]["curriculum_subject_id"])

    def test_activation_uses_real_offerings_and_still_requires_the_fee(self):
        preview = lifecycle.activation_preview(actor=self.w.admin, semester_id=self.p["first"])
        self.assertEqual(preview["prerequisites"][2], {"key": "academic_offerings", "status": "missing",
                                                       "reason": "no_valid_offerings"})
        services.update_semester_dates(actor=self.w.admin, semester_id=self.p["first"], start_date="2026-08-10",
                                       end_date="2026-12-18", expected_version=1)
        self.offer()
        preview = lifecycle.activation_preview(actor=self.w.admin, semester_id=self.p["first"])
        self.assertEqual([(c["key"], c["status"]) for c in preview["prerequisites"]],
                         [("valid_dates", "ready"), ("approved_fee", "unavailable"), ("academic_offerings", "ready")])
        self.assertFalse(preview["can_confirm"])
        self.assertEqual(lifecycle.activation_preview(actor=self.w.admin, semester_id=self.p["second"])
                         ["prerequisites"][2]["status"], "missing")  # an offering is valid only for its semester
        with override_settings(WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED=True), \
                self.assertRaises(lifecycle.TransitionRefused) as caught:
            lifecycle.activate_semester(actor=self.w.admin, semester_id=self.p["first"], expected_version=2,
                                        expected_active_semester_id=None, acknowledged_warnings=preview["warnings"],
                                        confirmed=True)
        self.assertEqual((caught.exception.reason, caught.exception.missing), ("prerequisites_missing", ("approved_fee",)))
        cfg.set_section_status(actor=self.w.admin, section_id=self.p["section"]["section_id"], status="Inactive",
                               expected_version=1)
        self.assertEqual(lifecycle.activation_preview(actor=self.w.admin, semester_id=self.p["first"])
                         ["prerequisites"][2]["status"], "missing")  # re-validated, never assumed

    def test_closed_periods_reject_offering_changes_and_drafts_allow_safe_removal(self):
        offering = self.offer()
        removed = cfg.remove_offering(actor=self.w.admin, offering_id=offering["offering_id"])
        self.assertTrue(removed["deleted"])
        offering = self.offer()
        services.update_semester_dates(actor=self.w.admin, semester_id=self.p["first"], start_date="2026-08-10",
                                       end_date="2026-12-18", expected_version=1)
        with override_settings(WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED=True):
            activate(self.w.admin, self.p["first"], source=bundle(offerings=dependencies.READY))
            self.refused("period_not_draft", cfg.remove_offering, actor=self.w.admin, offering_id=offering["offering_id"])
            close(self.w.admin, self.p["first"])
        self.refused("period_closed", self.offer, entry="MATH 101",
                     section=cfg.create_section(actor=self.w.admin, course_id=self.p["course"]["course_id"],
                                                year_level=1, name="1-C")["section_id"])
        self.assertEqual(SubjectOffering.objects.filter(semester_id=self.p["first"]).count(), 1)


@override_settings(**CONFIG)
class TeachingAssignmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = ConfigWorld()

    def setUp(self):
        self.p = build_plan(self.w)
        self.offering = cfg.create_offering(actor=self.w.admin, semester_id=self.p["first"],
                                            section_id=self.p["section"]["section_id"],
                                            curriculum_subject_id=self.p["entries"]["MATH 101"])
        self.oid = self.offering["offering_id"]

    def assign(self, account, expected=None):
        return teaching.assign_instructor(actor=self.w.admin, offering_id=self.oid, instructor_account_id=account.pk,
                                          expected_assignment_id=expected)

    def refused(self, reason, fn, *args, **kwargs):
        before = list(TeachingAssignment.objects.values().order_by("pk"))
        with self.assertRaises(cfg.ConfigurationConflict) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(before, list(TeachingAssignment.objects.values().order_by("pk")))

    def test_eligible_instructor_assignment_and_replacement_keep_history(self):
        others = other_table_counts()
        first = self.assign(self.w.instructor)
        current = first["assignment"]
        self.assertEqual((current["instructor"]["ctug_id"], current["eligible"], first["ready_for_confirmation"]),
                         ("WF1101-INST1", True, True))
        self.refused("assignment_changed", self.assign, self.w.instructor2, None)
        self.refused("no_change", self.assign, self.w.instructor, current["assignment_id"])
        second = self.assign(self.w.instructor2, current["assignment_id"])
        history = teaching.assignment_history(actor=self.w.admin, offering_id=self.oid)["results"]
        self.assertEqual([(h["instructor"]["ctug_id"], h["status"], h["end_reason"]) for h in history],
                         [("WF1101-INST2", "Active", None), ("WF1101-INST1", "Ended", "replaced")])
        self.assertEqual(second["assignment"]["instructor"]["ctug_id"], "WF1101-INST2")
        with self.assertRaises(IntegrityError), transaction.atomic():
            TeachingAssignment.objects.create(offering_id=self.oid, instructor=self.w.instructor, active_slot=1,
                                              assigned_by=self.w.admin)
        self.assertEqual(other_table_counts(), others)  # no clearance, signatory or student record touched
        self.assertEqual([a["ctug_id"] for a in teaching.eligible_instructors(actor=self.w.admin)["results"]],
                         ["WF1101-INST1", "WF1101-INST2"])

    def test_ineligible_accounts_are_refused(self):
        cases = [self.w.account("WF1101-STUD", "Student"), self.w.account("WF1101-PEND", "Instructor", status="Pending"),
                 self.w.account("WF1101-SUSP", "Instructor", active=False),
                 self.w.account("WF1101-STAF", "Instructor", is_staff=True), self.w.account("WF1101-NONE")]
        for account in cases:
            with self.subTest(account=account.school_id):
                self.refused("instructor_ineligible", self.assign, account)
        with self.assertRaises(services.AcademicPeriodNotFound):
            teaching.assign_instructor(actor=self.w.admin, offering_id=self.oid, instructor_account_id=999_999,
                                       expected_assignment_id=None)

    def test_revoked_eligibility_is_reported_and_blocks_confirmation_without_auto_changes(self):
        current = self.assign(self.w.instructor)["assignment"]
        AccountRole.objects.filter(account=self.w.instructor, role=self.w.roles["Instructor"]).delete()
        listing = cfg.list_offerings(actor=self.w.admin, semester_id=self.p["first"])["results"][0]
        self.assertEqual((listing["assignment"]["eligible"], listing["ready_for_confirmation"]), (False, False))
        self.assertFalse(teaching.offering_ready_for_confirmation(SubjectOffering.objects.get(pk=self.oid)))
        self.assertEqual(TeachingAssignment.objects.get(pk=current["assignment_id"]).status, "Active")  # never auto-ended
        Account.objects.filter(pk=self.w.instructor2.pk).update(is_active=False)
        self.refused("instructor_ineligible", self.assign, self.w.instructor2, current["assignment_id"])
        ended = teaching.end_assignment(actor=self.w.admin, offering_id=self.oid,
                                        expected_assignment_id=current["assignment_id"], reason_code="instructor_unavailable")
        self.assertIsNone(ended["assignment"])
        with self.assertRaises(services.AcademicPeriodInvalid):
            teaching.end_assignment(actor=self.w.admin, offering_id=self.oid, expected_assignment_id=current["assignment_id"],
                                    reason_code="because")

    def test_closed_periods_keep_their_teaching_history(self):
        current = self.assign(self.w.instructor)["assignment"]
        Semester.objects.filter(pk=self.p["first"]).update(status="Closed", activated_at=timezone.now(),
                                                           closed_at=timezone.now(), start_date="2026-08-10",
                                                           end_date="2026-12-18")
        self.refused("period_closed", self.assign, self.w.instructor2, current["assignment_id"])
        self.refused("period_closed", teaching.end_assignment, actor=self.w.admin, offering_id=self.oid,
                     expected_assignment_id=current["assignment_id"], reason_code="schedule_change")


@override_settings(**CONFIG)
class ConfigurationAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = ConfigWorld()

    def denied(self, fn, reason="access_denied", **kwargs):
        before = AcademicConfigurationAuditLog.objects.count()
        with self.assertRaises(services.AcademicPeriodDenied) as caught:
            fn(**kwargs)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(AcademicConfigurationAuditLog.objects.count(), before)

    def test_student_instructor_and_treasurer_cannot_configure_anything(self):
        for role in ("Student", "Instructor", "Treasurer"):
            actor = self.w.account(f"WF1101-K{role[:3].upper()}", role)
            for fn, kwargs in ((cfg.create_course, dict(code="X1", name="X")), (cfg.list_courses, {}),
                               (cfg.create_subject, dict(code="X1", title="X")), (cfg.list_sections, {}),
                               (cfg.list_curricula, {}), (cfg.list_semesters, {}),
                               (teaching.eligible_instructors, {})):
                with self.subTest(role=role, fn=fn.__name__):
                    self.denied(fn, actor=actor, **kwargs)

    def test_each_area_uses_its_exact_code_and_deny_wins(self):
        self.w.deny_code(self.w.admin, "academic.courses.manage")
        self.denied(cfg.create_course, actor=self.w.admin, code="BSIT", name="IT")
        self.denied(cfg.list_curricula, actor=self.w.admin)  # curricula use the proposed courses code
        subject = cfg.create_subject(actor=self.w.admin, code="GE 1", title="Self")  # a different exact code
        self.assertEqual(subject["code"], "GE 1")
        RolePermission.objects.filter(permission=self.w.perms["clearance.subjects.manage"]).delete()
        self.denied(cfg.create_subject, actor=self.w.admin, code="GE 2", title="Readings")
        Service.objects.filter(pk=self.w.clearance.pk).update(is_active=False)
        with self.assertRaises(services.AcademicPeriodDenied):  # inactive service => no effective permission
            teaching.eligible_instructors(actor=self.w.admin)
        # academic.advisers.manage is never accepted for teaching assignments.
        RolePermission.objects.filter(permission=self.w.perms["clearance.teaching_assignments.manage"]).delete()
        Service.objects.filter(pk=self.w.clearance.pk).update(is_active=True)
        advisers = Permission.objects.create(service=self.w.service, permission_code="academic.advisers.manage",
                                             permission_name="a", module_name="m", action_name="manage")
        RolePermission.objects.create(role=self.w.roles["Admin"], permission=advisers)
        self.denied(teaching.eligible_instructors, actor=self.w.admin)

    def test_technical_super_admin_and_framework_accounts_have_no_implicit_access(self):
        tsa = self.w.account("WF1101-KTSA", "Technical Super Admin")
        for code in self.w.perms:
            RolePermission.objects.get_or_create(role=self.w.roles["Technical Super Admin"], permission=self.w.perms[code])
        self.denied(cfg.create_course, actor=tsa, code="BSIT", name="IT")
        AccountRole.objects.create(account=tsa, role=self.w.roles["Admin"])
        self.assertEqual(cfg.create_course(actor=tsa, code="BSIT", name="IT")["code"], "BSIT")
        staff = self.w.account("WF1101-KSTF", "Admin", is_staff=True)
        self.denied(cfg.list_courses, actor=staff)

    @override_settings(WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True)
    def test_selected_role_context_and_cross_account_scope(self):
        dual = self.w.account("WF1101-KDUA", "Student", "Admin")
        with bind_role_scope(dual.pk, self.w.roles["Student"].pk):
            self.denied(cfg.create_course, reason="admin_context_required", actor=dual, code="BSIT", name="IT")
        with bind_role_scope(self.w.admin.pk, self.w.roles["Admin"].pk):
            self.denied(cfg.create_course, reason="admin_context_required", actor=dual, code="BSIT", name="IT")
        with bind_role_scope(dual.pk, self.w.roles["Admin"].pk):
            cfg.create_course(actor=dual, code="BSIT", name="IT")
        self.assertEqual(AcademicConfigurationAuditLog.objects.get().acting_role_id, self.w.roles["Admin"].pk)

    def test_feature_gates_are_independent_and_default_off(self):
        import config.settings as base
        for name in ("WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED", "WORKSPACE_ACADEMIC_CURRICULUM_WRITES_ENABLED",
                     "WORKSPACE_ACADEMIC_OFFERING_WRITES_ENABLED", "WORKSPACE_ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED"):
            self.assertIs(getattr(base, name), False, name)
        course = cfg.create_course(actor=self.w.admin, code="BSIT", name="IT")
        with override_settings(WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED=False):
            for fn, kwargs in ((cfg.list_courses, {}), (cfg.create_course, dict(code="X", name="X"))):
                with self.assertRaises(services.AcademicPeriodUnavailable):
                    fn(actor=self.w.admin, **kwargs)
        with override_settings(WORKSPACE_ACADEMIC_CURRICULUM_WRITES_ENABLED=False):
            self.assertEqual(cfg.list_curricula(actor=self.w.admin)["features"]["curriculum_writes"], False)
            with self.assertRaises(services.AcademicPeriodFeatureDisabled):
                cfg.create_curriculum(actor=self.w.admin, course_id=course["course_id"], label="2024")
        for setting, fn, kwargs in (
                ("WORKSPACE_ACADEMIC_OFFERING_WRITES_ENABLED", cfg.create_offering,
                 dict(semester_id=1, section_id=1, curriculum_subject_id=1)),
                ("WORKSPACE_ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED", teaching.assign_instructor,
                 dict(offering_id=1, instructor_account_id=1, expected_assignment_id=None))):
            with self.subTest(setting=setting), override_settings(**{setting: False}), \
                    self.assertRaises(services.AcademicPeriodFeatureDisabled):
                fn(actor=self.w.admin, **kwargs)
        # Configuration switches never enable semester transitions.
        self.assertFalse(lifecycle.transitions_enabled())

    def test_authorization_is_rechecked_under_lock_and_failures_roll_back(self):
        real = services.authorize
        calls = []

        def deny_after_precheck(actor, *args, **kwargs):
            result = real(actor, *args, **kwargs)
            calls.append(1)
            if len(calls) == 1:
                self.w.deny_code(self.w.admin, "academic.courses.manage")
            return result

        with patch.object(services, "authorize", side_effect=deny_after_precheck):
            self.denied(cfg.create_course, actor=self.w.admin, code="BSIT", name="IT")
        self.assertFalse(Course.objects.exists())
        AccountPermission.objects.all().delete()
        with patch.object(cfg, "audit", side_effect=RuntimeError("audit down")), self.assertRaises(RuntimeError):
            cfg.create_course(actor=self.w.admin, code="BSIT", name="IT")
        self.assertFalse(Course.objects.exists())  # the change and its audit commit together or not at all


class ConfigurationConcurrencyTests(TransactionTestCase):
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

    @override_settings(**CONFIG)
    def test_concurrent_duplicate_course_codes_create_one_course(self):
        w = ConfigWorld()
        results = self.race(*[lambda: cfg.create_course(actor=w.admin, code="BSIT", name="IT")] * 3)
        self.assertEqual(sum(r[0] == "ok" for r in results), 1, results)
        self.assertTrue(all(isinstance(r[1], cfg.ConfigurationConflict) and r[1].reason == "code_exists"
                            for r in results if r[0] == "error"))
        self.assertEqual((Course.objects.count(), AcademicConfigurationAuditLog.objects.count()), (1, 1))

    @override_settings(**CONFIG)
    def test_concurrent_instructor_assignments_leave_one_active(self):
        w = ConfigWorld()
        p = build_plan(w)
        offering = cfg.create_offering(actor=w.admin, semester_id=p["first"], section_id=p["section"]["section_id"],
                                       curriculum_subject_id=p["entries"]["MATH 101"])
        results = self.race(*[
            (lambda inst=inst: teaching.assign_instructor(actor=w.admin, offering_id=offering["offering_id"],
                                                          instructor_account_id=inst.pk, expected_assignment_id=None))
            for inst in (w.instructor, w.instructor2)])
        self.assertEqual(sum(r[0] == "ok" for r in results), 1, results)
        self.assertTrue(all(isinstance(r[1], cfg.ConfigurationConflict) and r[1].reason == "assignment_changed"
                            for r in results if r[0] == "error"))
        self.assertEqual(TeachingAssignment.objects.filter(status="Active").count(), 1)

    @override_settings(**CONFIG)
    def test_concurrent_curriculum_edits_with_one_version_apply_once(self):
        w = ConfigWorld()
        course = cfg.create_course(actor=w.admin, code="BSIT", name="IT")
        subjects = [cfg.create_subject(actor=w.admin, code=f"IT {n}", title=f"Subject {n}") for n in (1, 2)]
        cur = cfg.create_curriculum(actor=w.admin, course_id=course["course_id"], label="2024")
        results = self.race(*[
            (lambda s=s: cfg.add_curriculum_entry(actor=w.admin, curriculum_id=cur["curriculum_id"],
                                                  subject_id=s["subject_id"], year_level=1, term="first",
                                                  expected_version=1)) for s in subjects])
        self.assertEqual(sum(r[0] == "ok" for r in results), 1, results)
        self.assertEqual(CurriculumSubject.objects.count(), 1)
        self.assertEqual(CurriculumVersion.objects.get().version, 2)
