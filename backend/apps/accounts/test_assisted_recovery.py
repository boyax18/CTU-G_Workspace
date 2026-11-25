"""Assisted email verification + recovery for legacy accounts that cannot sign in (25 Nov 2026).
Run: python manage.py test apps.accounts.test_assisted_recovery --settings=config.test_settings --noinput
Disposable MySQL only, synthetic accounts, locmem mail.
"""
import json
import re
from types import ModuleType
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase, override_settings
from django.urls import include, path
from django.utils import timezone

from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from . import email_verification, password_reset
from .assisted_recovery import ASSIST_CODE, AUTHORIZE_ACTION, VERIFIED_ACTION, AssistedRecoveryStartView
from .models import Account, UserProfile
from .rejection_test_support import fresh_test_key
from .security_mail_models import AccountEmailVerification, SecurityMailOutbox

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Use config.test_settings and a disposable MySQL database.")

PASSWORD = "Harbor!Lantern5821"
NEW_PASSWORD = "Copper!Meadow7392"
GATE = dict(WORKSPACE_ASSISTED_RECOVERY_ENABLED=True, WORKSPACE_PASSWORD_RESET_ENABLED=True,
            WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
START = "/api/v1/admin/school-accounts/{}/assisted-recovery/"
VERIFY = "/api/v1/auth/account-recovery/verify/"
RESET = "/api/v1/auth/reset-password/"


def urlconf():
    module = ModuleType("assisted_recovery_test_urlconf")
    module.urlpatterns = [
        path("api/v1/auth/", include("apps.accounts.urls")),
        path("api/v1/admin/school-accounts/<int:account_id>/assisted-recovery/", AssistedRecoveryStartView.as_view()),
    ]
    return module


URLCONF = urlconf()


def recovery_codes():
    return [m.group(1) for msg in mail.outbox for m in [re.search(r"account recovery code is (\d{6})\.", msg.body)] if m]


@override_settings(ROOT_URLCONF=URLCONF, **GATE)
class AssistedRecoveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        accounts_service = Service.objects.create(service_code="accounts", service_name="Accounts")
        Service.objects.create(service_code="access_control", service_name="Access Control")
        cls.roles = {n: Role.objects.create(role_name=n) for n in
                     ("Student", "Instructor", "Treasurer", "Admin", "Technical Super Admin")}
        cls.permission = Permission.objects.create(
            service=accounts_service, permission_code=ASSIST_CODE, permission_name="School accounts assisted recovery",
            module_name="school_accounts", action_name="assist_recovery")
        RolePermission.objects.create(role=cls.roles["Admin"], permission=cls.permission)
        cls.operator = cls.account("AR-OPERATOR", "Admin", email="operator@example.edu", verified=True)
        cls.second_operator = cls.account("AR-OPERATOR2", "Admin", email="operator2@example.edu", verified=True)
        cls.student = cls.account("7250001", "Student", email="legacy.student@example.edu")
        cls.instructor = cls.account("0025002", "Instructor", email="legacy.instructor@example.edu")
        cls.verified = cls.account("7250003", "Student", email="verified@example.edu", verified=True)
        cls.privileged = cls.account("9250004", "Admin", email="legacy.admin@example.edu")
        cls.super_admin = cls.account("9250005", "Technical Super Admin", email="legacy.tsa@example.edu")
        cls.inactive = cls.account("7250006", "Student", email="inactive@example.edu", active=False)

    @classmethod
    def account(cls, school_id, *roles, email, verified=False, active=True):
        account = Account.objects.create_user(school_id=school_id, email=email, password=PASSWORD)
        Account.objects.filter(pk=account.pk).update(request_status="Approved", is_active=active)
        if verified:
            Account.objects.filter(pk=account.pk).update(email_verified_at=timezone.now(), email_verified_address=email)
        UserProfile.objects.create(account=account, first_name="Ana", last_name=school_id.title())
        for role in roles:
            AccountRole.objects.create(account=account, role=cls.roles[role])
        return Account.objects.get(pk=account.pk)

    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        key = mock.patch.dict("os.environ", {"WORKSPACE_OUTBOX_KEK_V1_B64": fresh_test_key()})
        key.start()
        self.addCleanup(key.stop)
        self.clock = int(timezone.now().timestamp())
        for module in (email_verification, password_reset):
            patcher = mock.patch.object(module, "_now", side_effect=lambda: self.clock)
            patcher.start()
            self.addCleanup(patcher.stop)

    # ---- helpers
    @staticmethod
    def signed_in(account):
        client = Client(enforce_csrf_checks=True)
        client.force_login(account)  # synthetic test accounts in the disposable database only
        client.cookies[settings.CSRF_COOKIE_NAME] = "e" * 32
        return client

    @staticmethod
    def public():
        client = Client(enforce_csrf_checks=True)
        client.cookies[settings.CSRF_COOKIE_NAME] = "e" * 32
        return client

    def call(self, client, url, body):
        with self.captureOnCommitCallbacks(execute=True):
            return client.post(url, data=json.dumps(body), content_type="application/json", HTTP_X_CSRFTOKEN="e" * 32)

    def start(self, target, operator=None, body=None):
        return self.call(self.signed_in(operator or self.operator), START.format(target.pk),
                         {"identity_confirmed": True} if body is None else body)

    def verify(self, email, code, client=None):
        client = client or self.public()
        return client, self.call(client, VERIFY, {"email": email, "code": code})

    def snapshot(self, account):
        row = Account.objects.values("password", "request_status", "is_active", "school_id", "email",
                                     "is_staff", "is_superuser", "session_revocation_version").get(pk=account.pk)
        return (row, sorted(AccountRole.objects.filter(account=account).values_list("role_id", flat=True)),
                list(AccountPermission.objects.filter(account=account).values_list("pk", flat=True)))

    def wrong(self, code):
        return "000000" if code != "000000" else "111111"

    # ---- the full recovery path
    def test_operator_start_then_holder_verifies_and_sets_a_password_with_a_single_use_ticket(self):
        before = self.snapshot(self.student)
        response = self.start(self.student)
        self.assertEqual(response.status_code, 202, response.content)
        self.assertEqual(response.json(), {"account_id": self.student.pk, "status": "code_queued", "code_valid_seconds": 600})
        self.assertNotRegex(response.content.decode(), r"\d{6}")  # the operator never sees the code
        challenge = AccountEmailVerification.objects.get(account=self.student)
        self.assertEqual((challenge.purpose, challenge.authorized_by_id), ("assisted", self.operator.pk))
        row = SecurityMailOutbox.objects.get(account=self.student)
        self.assertEqual((row.kind, row.status), ("assisted_recovery_code", "Accepted"))
        self.assertEqual(mail.outbox[0].to, ["legacy.student@example.edu"])
        self.assertEqual(mail.outbox[0].subject, "CTU-G Workspace account recovery code")
        audit = AccessAuditLog.objects.get(action=AUTHORIZE_ACTION)
        self.assertEqual((audit.actor_account_id, audit.target_account_id, audit.old_value, audit.new_value),
                         (self.operator.pk, self.student.pk, None, None))
        code = recovery_codes()[0]
        self.assertEqual(self.snapshot(self.student), before, "starting recovery changes nothing on the account")
        self.assertIsNone(Account.objects.get(pk=self.student.pk).email_verified_at)

        client, wrong = self.verify("legacy.student@example.edu", self.wrong(code))
        self.assertEqual(wrong.status_code, 400)
        self.assertIsNone(Account.objects.get(pk=self.student.pk).email_verified_at)
        client, ok = self.verify("Legacy.Student@example.edu", code, client)
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(ok.json(), {"status": "verified"})
        self.assertIn(password_reset.TICKET_COOKIE, ok.cookies)
        account = Account.objects.get(pk=self.student.pk)
        self.assertEqual(account.email_verified_address, "legacy.student@example.edu")
        self.assertTrue(password_reset.eligible_account_queryset().filter(pk=account.pk).exists(), "now passes D-21")
        self.assertFalse(AccountEmailVerification.objects.filter(account=account).exists())
        self.assertEqual(AccessAuditLog.objects.filter(action=VERIFIED_ACTION, actor_account_id=account.pk).count(), 1)
        self.assertEqual(self.snapshot(account), before, "verification changes only the proof fields")

        body = {"email": "legacy.student@example.edu", "password": NEW_PASSWORD, "password_confirmation": NEW_PASSWORD}
        changed = self.call(client, RESET, body)
        self.assertEqual(changed.status_code, 200, changed.content)
        self.assertTrue(Account.objects.get(pk=account.pk).check_password(NEW_PASSWORD))
        replay = self.call(client, RESET, {**body, "password": PASSWORD, "password_confirmation": PASSWORD})
        self.assertEqual(replay.status_code, 400, "the ticket is single-use")
        self.assertTrue(Account.objects.get(pk=account.pk).check_password(NEW_PASSWORD))
        self.assertEqual(SecurityMailOutbox.objects.filter(account=account, kind="password_changed").count(), 1)

    # ---- authorization boundaries
    def test_privileged_accounts_stop_at_the_authorization_boundary(self):
        for target in (self.privileged, self.super_admin):
            with self.subTest(target=target.school_id):
                response = self.start(target)
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.json()["error"]["reason"], "privileged_account")
        self.assertFalse(AccountEmailVerification.objects.exists())
        self.assertFalse(SecurityMailOutbox.objects.exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_operator_cannot_recover_their_own_account(self):
        response = self.start(self.operator)
        self.assertEqual((response.status_code, response.json()["error"]["reason"]), (409, "own_account"))
        self.assertFalse(SecurityMailOutbox.objects.exists())

    def test_permission_identity_attestation_and_feature_gate_are_required(self):
        RolePermission.objects.filter(permission=self.permission).delete()
        self.assertEqual(self.start(self.student).status_code, 403)
        RolePermission.objects.create(role=self.roles["Admin"], permission=self.permission)
        self.assertEqual(self.call(self.public(), START.format(self.student.pk), {"identity_confirmed": True}).status_code, 401)
        self.assertEqual(self.start(self.student, operator=self.verified).status_code, 403, "non-admin")
        self.assertEqual(self.start(self.student, body={"identity_confirmed": False}).status_code, 400)
        self.assertEqual(self.start(self.student, body={"identity_confirmed": True, "email": "x@y.z"}).status_code, 400)
        with override_settings(WORKSPACE_ASSISTED_RECOVERY_ENABLED=False):
            self.assertEqual(self.start(self.student).status_code, 503)
            self.assertEqual(self.verify("legacy.student@example.edu", "123456")[1].status_code, 503)
        self.assertFalse(SecurityMailOutbox.objects.exists())

    def test_unprovisioned_permission_fails_closed(self):
        RolePermission.objects.filter(permission=self.permission).delete()
        self.permission.delete()
        self.assertIn(self.start(self.student).status_code, (403, 503))
        self.assertFalse(SecurityMailOutbox.objects.exists())

    def test_ineligible_targets_get_fixed_reasons_and_nothing_is_sent(self):
        self.assertEqual(self.start(self.verified).json()["error"]["reason"], "already_verified")
        self.assertEqual(self.start(self.inactive).json()["error"]["reason"], "inactive_account")
        self.assertFalse(SecurityMailOutbox.objects.exists())

    # ---- neutrality / no enumeration
    def test_public_failures_are_indistinguishable(self):
        self.start(self.student)
        code = recovery_codes()[0]
        bodies = set()
        for email, attempt in (("nobody@example.edu", code), ("legacy.admin@example.edu", code),
                               ("verified@example.edu", code), ("legacy.instructor@example.edu", code),
                               ("legacy.student@example.edu", self.wrong(code))):
            cache.clear()  # the shared reset throttles allow 4 checks a minute; see test_public_step_is_throttled
            response = self.verify(email, attempt)[1]
            self.assertEqual(response.status_code, 400)
            self.assertNotIn(password_reset.TICKET_COOKIE, response.cookies)
            bodies.add(response.content)
        self.assertEqual(len(bodies), 1, "every failure has the same body")

    # ---- binding, expiry, lockout, resend
    def test_codes_never_cross_between_signed_in_and_assisted_steps(self):
        self.start(self.student)
        assisted = recovery_codes()[0]
        owner = self.signed_in(self.student)
        confirm = self.call(owner, "/api/v1/auth/email-verification/confirm/", {"code": assisted})
        self.assertEqual(confirm.status_code, 400)
        self.assertIsNone(Account.objects.get(pk=self.student.pk).email_verified_at)
        # The signed-in owner's own request replaces the assisted challenge; its code is not redeemable publicly.
        mail.outbox.clear()
        self.clock += 61
        self.assertEqual(self.call(owner, "/api/v1/auth/email-verification/request/", {}).status_code, 202)
        own = re.search(r"verification code is (\d{6})\.", mail.outbox[0].body).group(1)
        self.assertEqual(self.verify("legacy.student@example.edu", own)[1].status_code, 400)
        self.assertEqual(self.verify("legacy.student@example.edu", assisted)[1].status_code, 400)
        self.assertIsNone(Account.objects.get(pk=self.student.pk).email_verified_at)

    def test_email_change_invalidates_the_outstanding_challenge(self):
        self.start(self.student)
        code = recovery_codes()[0]
        Account.objects.filter(pk=self.student.pk).update(email="changed@example.edu")
        self.assertEqual(self.verify("changed@example.edu", code)[1].status_code, 400)
        self.assertEqual(self.verify("legacy.student@example.edu", code)[1].status_code, 400)
        self.assertIsNone(Account.objects.get(pk=self.student.pk).email_verified_at)

    def test_expired_code_fails_and_an_expired_queued_code_is_never_sent(self):
        self.start(self.student)
        code = recovery_codes()[0]
        self.clock += 601
        self.assertEqual(self.verify("legacy.student@example.edu", code)[1].status_code, 400)
        mail.outbox.clear()
        from . import recovery_mail
        with mock.patch.object(recovery_mail, "kick"):
            self.clock += 61
            self.assertEqual(self.start(self.student).status_code, 202)
        self.clock += 601
        self.assertEqual(recovery_mail.process_due(), {"expired": 1})
        self.assertEqual(mail.outbox, [])

    def test_wrong_codes_lock_and_resend_waits(self):
        self.start(self.student)
        code = recovery_codes()[0]
        again = self.start(self.student)
        self.assertEqual((again.status_code, again.json()["error"]["reason"]), (409, "recovery_wait"))
        self.assertGreater(again.json()["error"]["retry_after"], 0)
        for _ in range(5):
            cache.clear()
            self.verify("legacy.student@example.edu", self.wrong(code))
        cache.clear()
        self.assertTrue(AccountEmailVerification.objects.get(account=self.student).locked)
        self.assertEqual(self.verify("legacy.student@example.edu", code)[1].status_code, 400)
        self.assertIsNone(Account.objects.get(pk=self.student.pk).email_verified_at)
        self.clock += 61
        self.assertEqual(self.start(self.student).json()["error"]["reason"], "recovery_wait", "locked until the window ends")

    def test_a_second_operator_resend_replaces_the_code(self):
        self.start(self.student)
        first = recovery_codes()[0]
        self.clock += 61
        self.assertEqual(self.start(self.student, operator=self.second_operator).status_code, 202)
        second = recovery_codes()[-1]
        self.assertEqual(AccountEmailVerification.objects.get(account=self.student).authorized_by_id, self.second_operator.pk)
        if first != second:
            self.assertEqual(self.verify("legacy.student@example.edu", first)[1].status_code, 400)
        self.assertEqual(self.verify("legacy.student@example.edu", second)[1].status_code, 200)

    def test_target_becoming_privileged_before_redemption_is_refused(self):
        self.start(self.student)
        code = recovery_codes()[0]
        AccountRole.objects.create(account=self.student, role=self.roles["Admin"])
        self.assertEqual(self.verify("legacy.student@example.edu", code)[1].status_code, 400)
        self.assertIsNone(Account.objects.get(pk=self.student.pk).email_verified_at)

    def test_public_step_is_throttled(self):
        statuses = [self.verify("nobody@example.edu", "123456")[1].status_code for _ in range(5)]
        self.assertEqual(statuses[:4], [400] * 4)
        self.assertEqual(statuses[4], 429)
