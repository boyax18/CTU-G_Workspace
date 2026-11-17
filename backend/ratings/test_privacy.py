from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

class PrivacyTests(APITestCase):
    def setUp(self):
        # Create a released period, two students, and a result for student A.
        ...

    def auth(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_student_cannot_read_another_students_result(self):
        self.auth(self.student_b)
        r = self.client.get(f"/api/ratings/periods/{self.period.id}/my-result/")
        self.assertEqual(r.json()["student"], self.student_b.id)  # B sees only B's data
        # Student B tries to reach A's result by ID:
        r = self.client.get(f"/api/ratings/results/{self.result_a.id}/")
        self.assertEqual(r.status_code, 404)

    def test_result_hidden_until_released(self):
        self.period.status = "closed"
        self.period.save()
        self.auth(self.student_a)
        r = self.client.get(f"/api/ratings/periods/{self.period.id}/my-result/")
        self.assertEqual(r.status_code, 404)

    def test_leader_status_has_no_scores(self):
        self.auth(self.leader)
        r = self.client.get(f"/api/ratings/periods/{self.period.id}/group-status/")
        self.assertNotIn("value", r.content.decode())

    def test_cannot_rate_self(self):
        self.auth(self.student_a)
        r = self.client.post(
            f"/api/ratings/periods/{self.period.id}/submit/",
            {"scores": [{"target_id": self.student_a.id,
                         "criterion_id": self.criterion.id, "value": 5}]},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_cannot_submit_twice(self):
        ...