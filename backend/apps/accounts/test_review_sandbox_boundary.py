"""AR-6C7E.3 offline safety tests; run using config.test_settings only."""

import importlib
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from config.review_sandbox_middleware import LoopbackOnlyMiddleware
from django.urls import NoReverseMatch, reverse

from apps.accounts.management.commands import seed_review_sandbox


class ReviewSandboxSafetyTests(SimpleTestCase):
    def test_seed_refuses_test_settings_without_query(self):
        with self.assertRaisesMessage(CommandError, "config.review_sandbox_settings"):
            call_command("seed_review_sandbox")

    def test_sandbox_module_requires_ack(self):
        with patch.dict("os.environ", {"CTUG_REVIEW_SANDBOX_ACK": ""}):
            with self.assertRaises(ImproperlyConfigured):
                importlib.reload(importlib.import_module("config.review_sandbox_settings"))

    def test_sandbox_db_is_fixed_and_not_original(self):
        with patch.dict("os.environ", {"CTUG_REVIEW_SANDBOX_ACK": "SANDBOX_ONLY"}):
            cfg = importlib.reload(importlib.import_module("config.review_sandbox_settings"))
        self.assertEqual(cfg.DATABASES["default"]["NAME"], "ctug_review_sandbox")
        self.assertNotEqual(cfg.DATABASES["default"]["NAME"], "ctug_workspace")
        self.assertEqual(cfg.ROOT_URLCONF, "config.review_sandbox_urls")
        self.assertNotEqual(cfg.SESSION_COOKIE_NAME, "sessionid")
        self.assertNotEqual(cfg.CSRF_COOKIE_NAME, "csrftoken")
        self.assertEqual(cfg.EMAIL_BACKEND, "django.core.mail.backends.locmem.EmailBackend")

    def test_original_registration_review_url_not_mounted(self):
        with self.assertRaises(NoReverseMatch):
            reverse("registration-review-pending")
        with override_settings(ROOT_URLCONF="config.review_sandbox_urls"):
            self.assertEqual(
                reverse("registration-review-pending"),
                "/api/v1/admin/registration-requests/",
            )

    def test_sandbox_middleware_refuses_nonlocal_request_even_with_local_host(self):
        handler = LoopbackOnlyMiddleware(lambda request: HttpResponse("ok"))
        request = RequestFactory().get("/", HTTP_HOST="127.0.0.1", REMOTE_ADDR="192.168.1.3")
        self.assertEqual(handler(request).status_code, 403)
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        self.assertEqual(handler(request).status_code, 200)

    def test_seed_module_has_no_real_database_target(self):
        self.assertEqual(seed_review_sandbox.DB_NAME, "ctug_review_sandbox")
        self.assertEqual(seed_review_sandbox.CONFIRM, "CTUG-REVIEW-SANDBOX-SEED-ONLY")
