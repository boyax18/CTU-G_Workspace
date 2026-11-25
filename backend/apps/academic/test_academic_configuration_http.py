"""Academic configuration HTTP contract through the real config.urls.

Run: python manage.py test apps.academic.test_academic_configuration_http --settings=config.test_settings --noinput
"""

from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from apps.access_control.management.commands import init_registration_review_metadata_local_dev as p1

from . import services
from .models import AcademicConfigurationAuditLog, Course, SubjectOffering, TeachingAssignment
from .test_academic_configuration import CONFIG, ConfigWorld
from .test_wf1101_http import TOKEN, post, signed_in

ROOT = "/api/v1/academic/config/"


@override_settings(**CONFIG)
class ConfigurationHTTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = ConfigWorld()

    def setUp(self):
        cache.clear()
        self.client = signed_in(self.w.admin)

    def ok(self, reply, status=200):
        self.assertEqual(reply.status_code, status, reply.content)
        self.assertIn("no-store", reply["Cache-Control"])
        return reply.json()

    def test_end_to_end_plan_offering_and_instructor(self):
        course = self.ok(post(self.client, ROOT + "courses/", {"code": "bsit", "name": "Information Technology"}), 201)
        subject = self.ok(post(self.client, ROOT + "subjects/", {"code": "IT 101", "title": "Introduction to Computing",
                                                                 "lecture_units": 2, "lab_units": "1.0"}), 201)
        self.assertEqual((subject["lecture_units"], subject["lab_units"]), ("2.0", "1.0"))
        section = self.ok(post(self.client, ROOT + "sections/", {"course_id": course["course_id"], "year_level": 1,
                                                                 "name": "1-A"}), 201)
        cur = self.ok(post(self.client, ROOT + "curricula/", {"course_id": course["course_id"], "label": "2024"}), 201)
        cid = cur["curriculum_id"]
        cur = self.ok(post(self.client, f"{ROOT}curricula/{cid}/entries/", {"subject_id": subject["subject_id"],
                                                                            "year_level": 1, "term": "first",
                                                                            "expected_version": 1}))
        cur = self.ok(post(self.client, f"{ROOT}curricula/{cid}/publish/", {"expected_version": 2, "confirmed": True}))
        self.assertEqual(cur["status"], "Published")
        detail = self.ok(self.client.get(f"{ROOT}curricula/{cid}/"))
        self.assertEqual(detail["features"], {"curriculum_writes": True, "offering_writes": True,
                                              "teaching_assignments": True})
        year = services.create_school_year(actor=self.w.admin, start_year=2026)
        first = year["semesters"][0]["semester_id"]
        semesters = self.ok(self.client.get(ROOT + "semesters/"))["results"]
        self.assertEqual(semesters[0]["semester_id"], first)
        candidates = self.ok(self.client.get(ROOT + "offerings/candidates/",
                                             {"semester_id": first, "section_id": section["section_id"]}))["results"]
        self.assertEqual(len(candidates), 1)
        offering = self.ok(post(self.client, ROOT + "offerings/", {
            "semester_id": first, "section_id": section["section_id"],
            "curriculum_subject_id": candidates[0]["curriculum_subject_id"]}), 201)
        listing = self.ok(self.client.get(ROOT + "offerings/", {"semester_id": first}))
        self.assertEqual((listing["valid_offering_count"], len(listing["results"])), (1, 1))
        instructors = self.ok(self.client.get(ROOT + "instructors/", {"q": "WF1101-INST"}))["results"]
        self.assertEqual(set(instructors[0]), {"account_id", "ctug_id", "full_name"})  # minimized
        assigned = self.ok(post(self.client, f"{ROOT}offerings/{offering['offering_id']}/instructor/", {
            "instructor_account_id": instructors[0]["account_id"], "expected_assignment_id": None}))
        self.assertTrue(assigned["ready_for_confirmation"])
        history = self.ok(self.client.get(f"{ROOT}offerings/{offering['offering_id']}/instructor/history/"))
        self.assertEqual(len(history["results"]), 1)
        record = self.ok(self.client.get(f"{ROOT}history/courses/{course['course_id']}/"))
        self.assertEqual((record["results"][0]["event"], record["results"][0]["actor"]), ("academic.course.create", "You"))
        self.assertNotIn(self.w.admin.school_id, str(record))
        self.assertEqual(self.client.get(f"{ROOT}history/accounts/1/").status_code, 404)
        self.assertEqual(TeachingAssignment.objects.count(), 1)

    def test_errors_are_fixed_and_minimized(self):
        reply = post(self.client, ROOT + "courses/", {"code": "<script>", "name": "X"})
        self.assertEqual(reply.status_code, 400)
        self.assertEqual(reply.json()["error"]["fields"],
                         {"code": ["Use 1 to 20 letters, digits, spaces, dots, hyphens or slashes."]})
        self.assertNotIn("<script>", reply.content.decode())
        self.assertEqual(post(self.client, ROOT + "courses/", {"code": "BSIT", "name": "IT", "status": "Active"}).status_code, 400)
        self.ok(post(self.client, ROOT + "courses/", {"code": "BSIT", "name": "IT"}), 201)
        reply = post(self.client, ROOT + "courses/", {"code": "bsit", "name": "Again"})
        self.assertEqual((reply.status_code, reply.json()["error"]["reason"]), (409, "code_exists"))
        self.assertEqual(self.client.get(ROOT + "courses/", {"page": "x"}).status_code, 400)
        self.assertEqual(self.client.get(ROOT + "courses/", {"sort": "code"}).status_code, 400)
        self.assertEqual(self.client.get(ROOT + "offerings/").status_code, 400)  # a semester is required
        self.assertEqual(post(self.client, ROOT + "offerings/999999/remove/", {}).status_code, 404)

    def test_unauthenticated_csrf_and_role_refusals_change_nothing(self):
        anonymous = Client(enforce_csrf_checks=True)
        self.assertEqual(anonymous.get(ROOT + "courses/").status_code, 401)
        reply = post(self.client, ROOT + "courses/", {"code": "BSIT", "name": "IT"}, csrf=False)
        self.assertEqual((reply.status_code, reply.json()["error"]["code"]), (403, "csrf_failed"))
        for role in ("Student", "Instructor", "Treasurer"):
            client = signed_in(self.w.account(f"WF1101-H{role[:3].upper()}", role))
            for path in ("courses/", "subjects/", "sections/", "curricula/", "semesters/", "instructors/"):
                with self.subTest(role=role, path=path):
                    self.assertEqual(client.get(ROOT + path).status_code, 403)
            self.assertEqual(post(client, ROOT + "courses/", {"code": "BSIT", "name": "IT"}).status_code, 403)
        self.assertEqual((Course.objects.count(), AcademicConfigurationAuditLog.objects.count()), (0, 0))

    def test_area_write_switches_answer_feature_disabled_while_reads_work(self):
        course = self.ok(post(self.client, ROOT + "courses/", {"code": "BSIT", "name": "IT"}), 201)
        with override_settings(WORKSPACE_ACADEMIC_CURRICULUM_WRITES_ENABLED=False,
                               WORKSPACE_ACADEMIC_OFFERING_WRITES_ENABLED=False,
                               WORKSPACE_ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED=False):
            listing = self.ok(self.client.get(ROOT + "curricula/"))
            self.assertEqual(listing["features"], {"curriculum_writes": False, "offering_writes": False,
                                                   "teaching_assignments": False})
            for path, body in (("curricula/", {"course_id": course["course_id"], "label": "2024"}),
                               ("offerings/", {"semester_id": 1, "section_id": 1, "curriculum_subject_id": 1}),
                               ("offerings/1/instructor/", {"instructor_account_id": 1, "expected_assignment_id": None})):
                reply = post(self.client, ROOT + path, body)
                self.assertEqual((reply.status_code, reply.json()["error"]["code"]), (503, "feature_disabled"), path)
        self.assertEqual(SubjectOffering.objects.count(), 0)


class ConfigurationDefaultOffTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = ConfigWorld()

    def test_every_configuration_route_is_unavailable_by_default(self):
        cache.clear()
        client = signed_in(self.w.admin)
        gets = ("courses/", "subjects/", "sections/", "curricula/", "curricula/1/", "semesters/", "offerings/?semester_id=1",
                "offerings/candidates/?semester_id=1&section_id=1", "instructors/", "offerings/1/instructor/history/",
                "history/courses/1/")
        posts = ("courses/", "courses/1/", "courses/1/status/", "subjects/", "sections/", "curricula/",
                 "curricula/1/entries/", "curricula/1/publish/", "offerings/", "offerings/1/remove/",
                 "offerings/1/instructor/", "offerings/1/instructor/end/")
        with override_settings(WORKSPACE_ACADEMIC_PERIODS_ENABLED=True):  # the period switch enables none of this
            for path in gets:
                reply = client.get(ROOT + path)
                self.assertEqual((reply.status_code, reply.json()["error"]["code"]),
                                 (503, "academic_configuration_unavailable"), path)
            for path in posts:
                reply = post(client, ROOT + path, {})
                self.assertEqual(reply.status_code, 503, path)
        self.assertEqual(Course.objects.count(), 0)

    def test_release_safeguard_still_holds(self):
        self.assertEqual(p1.unexpected_review_routes("config.urls"), [])
        self.assertTrue(TOKEN)
