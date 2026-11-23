from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account
from apps.access_control.models import AccountRole, Role

from .models import (
    IndividualResult,
    RatingGroup,
    RatingMember,
    RatingSession,
    RatingSubmission,
)


class RatingModelPrivacyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student_role = Role.objects.create(role_name="Student")
        cls.instructor_role = Role.objects.create(role_name="Instructor")
        cls.instructor = Account.objects.create_user(
            school_id="PROF-RATING-TEST",
            password="Copper!River7392",
        )
        cls.instructor.is_active = True
        cls.instructor.request_status = "Approved"
        cls.instructor.save(update_fields=["is_active", "request_status"])
        AccountRole.objects.create(account=cls.instructor, role=cls.instructor_role)

        cls.rater = Account.objects.create_user(
            school_id="RATER-RATING-TEST",
            password="Copper!River7392",
        )
        cls.rater.is_active = True
        cls.rater.request_status = "Approved"
        cls.rater.save(update_fields=["is_active", "request_status"])
        AccountRole.objects.create(account=cls.rater, role=cls.student_role)

        cls.target = Account.objects.create_user(
            school_id="TARGET-RATING-TEST",
            password="Copper!River7392",
        )
        cls.target.is_active = True
        cls.target.request_status = "Approved"
        cls.target.save(update_fields=["is_active", "request_status"])
        AccountRole.objects.create(account=cls.target, role=cls.student_role)

        cls.session = RatingSession.objects.create(
            title="Private rating test",
            deadline=timezone.now(),
            criteria=["Teamwork", "Reliability"],
            status="published",
            created_by=cls.instructor,
        )
        cls.group = RatingGroup.objects.create(
            session=cls.session,
            name="Group One",
            leader=cls.rater,
        )
        RatingMember.objects.create(group=cls.group, account=cls.rater)
        RatingMember.objects.create(group=cls.group, account=cls.target)

    def test_submission_is_unique_per_session_rater_and_group(self):
        RatingSubmission.objects.create(
            session=self.session,
            rater=self.rater,
            group=self.group,
            ratings={"TARGET-RATING-TEST": {"Teamwork": 5, "Reliability": 4}},
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RatingSubmission.objects.create(
                    session=self.session,
                    rater=self.rater,
                    group=self.group,
                    ratings={"TARGET-RATING-TEST": {"Teamwork": 3, "Reliability": 3}},
                )

    def test_individual_result_is_unique_per_student_and_session(self):
        IndividualResult.objects.create(
            session=self.session,
            student=self.target,
            group=self.group,
            scores={"Teamwork": 5, "Reliability": 4},
            final_score="4.50",
            released_at=timezone.now(),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                IndividualResult.objects.create(
                    session=self.session,
                    student=self.target,
                    group=self.group,
                    scores={"Teamwork": 3, "Reliability": 3},
                    final_score="3.00",
                    released_at=timezone.now(),
                )
