# accounts/test_tokens.py
import uuid
from datetime import timedelta

import jwt
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User

PW = "StrongPass!123"


class TokenLifecycleTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user("tok_s", password=PW, role=User.Role.STUDENT)
        self.form_url = "/api/ratings/periods/1/form/"

    def bearer(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_valid_token_is_accepted(self):
        # Control case: proves the rejection tests below are not rejecting everything.
        self.bearer(AccessToken.for_user(self.student))
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

    def test_expired_access_token_is_rejected(self):
        token = AccessToken.for_user(self.student)
        # Issued 1 hour ago with a 30-minute lifetime, so it expired 30 minutes ago.
        token.set_exp(from_time=timezone.now() - timedelta(hours=1),
                      lifetime=timedelta(minutes=30))
        self.bearer(token)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_expired_token_rejected_on_rating_endpoint(self):
        token = AccessToken.for_user(self.student)
        token.set_exp(from_time=timezone.now() - timedelta(hours=1),
                      lifetime=timedelta(minutes=30))
        self.bearer(token)
        self.assertEqual(self.client.get(self.form_url).status_code, 401)

    def test_token_signed_with_wrong_key_is_rejected(self):
        # Structurally valid, unexpired, correct user, but signed with a different secret.
        payload = {
            "token_type": "access",
            "user_id": self.student.id,
            "jti": uuid.uuid4().hex,
            "exp": timezone.now() + timedelta(minutes=30),
        }
        forged = jwt.encode(payload, "not-the-real-secret", algorithm="HS256")
        self.bearer(forged)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_payload_edited_without_resigning_is_rejected(self):
        # Take a real token, change the user_id in its payload, and keep the original signature.
        real = str(AccessToken.for_user(self.student))
        header, _payload, signature = real.split(".")
        other = User.objects.create_user("tok_other", password=PW, role=User.Role.STUDENT)
        forged_payload = jwt.utils.base64url_encode(
            jwt.api_jwt.json.dumps({"token_type": "access", "user_id": other.id,
                                    "jti": uuid.uuid4().hex,
                                    "exp": int((timezone.now() + timedelta(minutes=30)).timestamp())}
                                   ).encode()
        ).decode()
        self.bearer(f"{header}.{forged_payload}.{signature}")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_token_for_real_secret_but_wrong_token_type_is_rejected(self):
        # A token signed correctly but labelled as something other than an access token.
        payload = {
            "token_type": "refresh",
            "user_id": self.student.id,
            "jti": uuid.uuid4().hex,
            "exp": int((timezone.now() + timedelta(minutes=30)).timestamp()),
        }
        forged = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        self.bearer(forged)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)