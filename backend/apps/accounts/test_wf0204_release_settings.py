"""WF-02.04 D-62 and D-61: local-review/sandbox mail safety and the partial reapplication shutdown.

Run: python manage.py test apps.accounts.test_wf0204_release_settings --settings=config.test_settings --noinput
Offline settings checks reload the overlay modules with patched guards (no database is contacted);
reapplication checks use synthetic legacy rows in the disposable MySQL test database only.
"""

import ast
import importlib
import re
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core import mail, signing
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

import config.settings as base_settings
from apps.access_control.models import AccessAuditLog, Role

from . import reapplication
from .models import Account, UserProfile
from .outbox_worker import OutboxWorkerUnavailable, _require_delivery_enabled

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("WF-02.04 settings tests require --settings=config.test_settings.")

CONFIG = Path(base_settings.__file__).resolve().parent
LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
KEY_LIKE = re.compile(r"['\"][A-Za-z0-9+/]{43}=['\"]")  # a literal base64 256-bit key


def local_review(local_email="0"):
    database = {**base_settings.DATABASES["default"], "ENGINE": "django.db.backends.mysql",
                "NAME": "ctug_workspace", "HOST": "127.0.0.1"}
    # The developer's own backend/.env may opt in to local email; this helper pins the setting.
    with patch.dict("os.environ", {"CTUG_REVIEW_LOCAL_ACK": "LOCAL_REVIEW_ONLY",
                                   "WORKSPACE_LOCAL_EMAIL_DELIVERY": local_email}), \
            patch.object(base_settings, "DEBUG", True), \
            patch.object(base_settings, "DATABASES", {"default": database}):
        return importlib.reload(importlib.import_module("config.review_local_settings"))


def sandbox():
    database = {**base_settings.DATABASES["default"], "ENGINE": "django.db.backends.mysql", "HOST": "127.0.0.1"}
    with patch.dict("os.environ", {"CTUG_REVIEW_SANDBOX_ACK": "SANDBOX_ONLY"}), \
            patch.object(base_settings, "DATABASES", {"default": database}):
        return importlib.reload(importlib.import_module("config.review_sandbox_settings"))


class ReviewModeMailSafetyTests(SimpleTestCase):
    def test_both_modes_enable_the_outbox_and_v2_with_in_memory_mail_only(self):
        for name, cfg in (("local review", local_review()), ("sandbox", sandbox())):
            with self.subTest(mode=name):
                self.assertIs(cfg.WORKSPACE_REGISTRATION_OUTBOX_ENABLED, True)
                self.assertIs(cfg.WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED, True)
                self.assertIs(cfg.WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED, False)
                self.assertIs(cfg.WORKSPACE_EMAIL_SMTP_ENABLED, False)
                self.assertEqual(cfg.EMAIL_BACKEND, LOCMEM)
                self.assertRegex(cfg.WORKSPACE_PUBLIC_BASE_URL, r"^http://(localhost|127\.0\.0\.1)(:\d+)?$")
                self.assertEqual(cfg.MIDDLEWARE[0], "config.review_sandbox_middleware.LoopbackOnlyMiddleware")
                self.assertEqual(cfg.ALLOWED_HOSTS, ["127.0.0.1", "localhost"])
                self.assertIn(cfg.ROOT_URLCONF, {"config.review_local_urls", "config.review_sandbox_urls"})
                self.assertFalse([n for n in dir(cfg) if n.startswith("WORKSPACE_OUTBOX_KEK")], "no key in settings")
        self.assertIs(local_review().WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED, False)

    def test_local_email_opt_in_uses_the_validated_smtp_settings_only(self):
        smtp = "django.core.mail.backends.smtp.EmailBackend"
        with patch.object(base_settings, "WORKSPACE_EMAIL_SMTP_ENABLED", True), \
                patch.object(base_settings, "EMAIL_BACKEND", smtp), \
                patch.object(base_settings, "WORKSPACE_PASSWORD_RESET_ENABLED", True):
            cfg = local_review(local_email="1")
        self.assertEqual(cfg.EMAIL_BACKEND, smtp)
        self.assertIs(cfg.WORKSPACE_EMAIL_SMTP_ENABLED, True)
        self.assertIs(cfg.WORKSPACE_PASSWORD_RESET_ENABLED, True)
        self.assertIs(cfg.WORKSPACE_EMAIL_DEV_LINKS_ALLOWED, True)
        self.assertIs(cfg.WORKSPACE_REGISTRATION_OUTBOX_ENABLED, True)
        self.assertEqual(cfg.ALLOWED_HOSTS, ["127.0.0.1", "localhost"])  # still loopback-only
        with patch.object(base_settings, "WORKSPACE_EMAIL_SMTP_ENABLED", False), \
                self.assertRaises(ImproperlyConfigured):
            local_review(local_email="1")
        self.assertIs(local_review().WORKSPACE_EMAIL_DEV_LINKS_ALLOWED, False)

    def test_no_key_or_credential_is_in_source_control(self):
        for path in (CONFIG / "review_local_settings.py", CONFIG / "review_sandbox_settings.py"):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIsNone(KEY_LIKE.search(text))
                self.assertNotRegex(text, r"(?m)^\s*WORKSPACE_OUTBOX_KEK\w*\s*=")
                self.assertNotRegex(text, r"(?m)^\s*EMAIL_HOST_(USER|PASSWORD)\s*=")

    def test_guards_still_refuse_without_acknowledgement_or_a_local_database(self):
        with patch.dict("os.environ", {"CTUG_REVIEW_LOCAL_ACK": ""}), self.assertRaises(ImproperlyConfigured):
            importlib.reload(importlib.import_module("config.review_local_settings"))
        remote = {**base_settings.DATABASES["default"], "ENGINE": "django.db.backends.mysql", "NAME": "ctug_workspace",
                  "HOST": "db.example.edu"}
        with patch.dict("os.environ", {"CTUG_REVIEW_LOCAL_ACK": "LOCAL_REVIEW_ONLY"}), \
                patch.object(base_settings, "DEBUG", True), patch.object(base_settings, "DATABASES", {"default": remote}), \
                self.assertRaises(ImproperlyConfigured):
            importlib.reload(importlib.import_module("config.review_local_settings"))
        with patch.dict("os.environ", {"CTUG_REVIEW_SANDBOX_ACK": ""}), self.assertRaises(ImproperlyConfigured):
            importlib.reload(importlib.import_module("config.review_sandbox_settings"))

    def test_production_defaults_are_unchanged(self):
        text = (CONFIG / "settings.py").read_text(encoding="utf-8")
        self.assertIn('WORKSPACE_REGISTRATION_OUTBOX_ENABLED = os.environ.get("WORKSPACE_REGISTRATION_OUTBOX_ENABLED", "0") == "1"', text)
        self.assertRegex(text, r'"WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED", "0"')
        self.assertRegex(text, r'"WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED", "0"')

    def test_with_these_settings_the_worker_cannot_use_external_mail(self):
        for cfg in (local_review(), sandbox()):
            mode = dict(WORKSPACE_REGISTRATION_OUTBOX_ENABLED=cfg.WORKSPACE_REGISTRATION_OUTBOX_ENABLED,
                        WORKSPACE_EMAIL_SMTP_ENABLED=cfg.WORKSPACE_EMAIL_SMTP_ENABLED)
            with patch.dict("os.environ", {"WORKSPACE_OUTBOX_WORKER_ENABLED": "1"}):
                # Switching to SMTP is refused: SMTP is disabled and no delivery approval exists.
                with override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", **mode), \
                        self.assertRaises(OutboxWorkerUnavailable):
                    _require_delivery_enabled()
                with override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend", **mode), \
                        self.assertRaises(OutboxWorkerUnavailable):
                    _require_delivery_enabled()


@override_settings(EMAIL_BACKEND=LOCMEM)
class ReviewModeDeliveryIsInMemoryTests(TestCase):
    def test_a_rejection_email_under_sandbox_settings_stays_in_memory(self):
        from .rejection_test_support import fresh_test_key
        from .test_wf0203_approval import applicant, build_world
        from .outbox_worker import process_one
        from .registration_review import reject_registration
        cfg = sandbox()
        mode = {name: getattr(cfg, name) for name in (
            "WORKSPACE_REGISTRATION_OUTBOX_ENABLED", "WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED",
            "WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED", "WORKSPACE_EMAIL_SMTP_ENABLED",
            "EMAIL_BACKEND", "WORKSPACE_PUBLIC_BASE_URL", "WORKSPACE_REGISTRATION_APPROVAL_ENABLED")}
        world = build_world()
        target = applicant("WF0204-SANDBOX", world.roles["Student"])
        mail.outbox = []
        with override_settings(**mode), patch.dict("os.environ", {
                "WORKSPACE_OUTBOX_KEK_V1_B64": fresh_test_key(), "WORKSPACE_OUTBOX_WORKER_ENABLED": "1"}), \
                patch("smtplib.SMTP", side_effect=AssertionError("external SMTP must never be used")), \
                patch("smtplib.SMTP_SSL", side_effect=AssertionError("external SMTP must never be used")):
            reject_registration(actor=world.reviewer, target_id=target.pk, rejection_code="duplicate_request")
            self.assertEqual(process_one(), "delivered")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Duplicate registration request", mail.outbox[0].body)
        self.assertIn("http://localhost:5173/register", mail.outbox[0].body)


class ExecutorReapplicationRetiredSourceTests(SimpleTestCase):
    def test_both_executor_settings_disable_reapplication(self):
        for name in ("executor_settings.py", "executor_isolated_settings.py"):
            tree = ast.parse((CONFIG / name).read_text(encoding="utf-8"))
            values = [node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED" for t in node.targets)]
            with self.subTest(module=name):
                self.assertEqual(len(values), 1)
                self.assertIsInstance(values[0], ast.Constant)
                self.assertIs(values[0].value, False)


@override_settings(
    WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED=False,  # the executor's effective value now
    WORKSPACE_REGISTRATION_REAPPLICATION_EMAIL_ENABLED=True,
    WORKSPACE_PUBLIC_BASE_URL="http://localhost:5173",
    EMAIL_BACKEND=LOCMEM,
)
class LegacyReapplicationShutdownTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = Role.objects.create(role_name="Student")
        cls.reviewer = Account.objects.create(school_id="LEGACY-REVIEWER", request_status="Approved", is_active=True)
        cls.legacy = Account.objects.create_user(school_id="1234567", email="legacy@example.edu",
                                                 password="Legacy!Harbor4821", requested_role=cls.student)
        Account.objects.filter(pk=cls.legacy.pk).update(request_status="Rejected", rejection_reason="incomplete_submission",
                                                         reviewed_by=cls.reviewer)
        UserProfile.objects.create(account=cls.legacy, first_name="Legacy", last_name="Applicant")
        # A pre-deletion rejection receipt that references the row, as in the development database.
        cls.receipt = AccessAuditLog.objects.create(
            actor_account=cls.reviewer, target_account=cls.legacy, action="account.registration.reject",
            old_value={"request_status": "Pending"}, new_value={"request_status": "Rejected"})

    def setUp(self):
        mail.outbox = []
        self.before = Account.objects.values().get(pk=self.legacy.pk)
        self.audits = AccessAuditLog.objects.count()

    def token(self):
        return signing.dumps({"aid": self.legacy.pk, "rid": self.receipt.pk,
                              "eh": reapplication._digest("legacy@example.edu")}, salt=reapplication.SALT, compress=False)

    def assert_legacy_untouched(self):
        self.assertEqual(Account.objects.values().get(pk=self.legacy.pk), self.before)
        self.assertEqual(AccessAuditLog.objects.count(), self.audits)
        self.assertEqual(UserProfile.objects.get(account=self.legacy).first_name, "Legacy")
        self.assertEqual(len(mail.outbox), 0)

    def test_a_validly_signed_token_cannot_revive_a_legacy_rejected_account(self):
        data = {"school_id": "1234567", "email": "new@example.edu", "requested_role": "Student",
                "password": "New!Harbor48217", "first_name": "New", "last_name": "Name"}
        with self.assertRaises(reapplication.ReapplicationUnavailable):
            reapplication.complete_reapplication(token=self.token(), data=data)
        self.assert_legacy_untouched()

    def test_no_reapplication_link_is_sent(self):
        with self.assertRaises(reapplication.ReapplicationUnavailable):
            reapplication.issue_reapplication_email_if_eligible(school_id="1234567", email="legacy@example.edu")
        self.assert_legacy_untouched()

    def test_legacy_routes_fail_closed_even_with_a_valid_token_and_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        csrf = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        link = client.post("/api/v1/auth/reapply/link/", {"school_id": "1234567", "email": "legacy@example.edu"},
                           format="json", HTTP_X_CSRFTOKEN=csrf)
        complete = client.post("/api/v1/auth/reapply/complete/", {
            "reapplication_token": self.token(), "school_id": "1234567", "email": "new@example.edu",
            "requested_role": "Student", "password": "New!Harbor48217", "password_confirmation": "New!Harbor48217",
            "first_name": "New", "last_name": "Name"}, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual((link.status_code, complete.status_code), (503, 503))
        self.assert_legacy_untouched()

    def test_the_legacy_row_still_reserves_its_identity_d60(self):
        # D-60: legacy Rejected data are left as they are; WF-02.04 deletion frees only new rejections.
        from .registration_staging import _identity_conflicts
        self.assertTrue(_identity_conflicts({"school_id": "1234567", "email": "other@example.edu"}))
        self.assert_legacy_untouched()
