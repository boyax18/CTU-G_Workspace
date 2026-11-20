"""Email invariants on disposable MySQL only, including real racing inserts."""

from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from threading import Barrier
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import IntegrityError, connection, connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.access_control.models import AccessAuditLog, AccountRole, Role
from .models import Account, UserProfile
from .outbox_models import RegistrationNotificationOutbox
from .serializers import RegistrationSerializer
from .services import register_account
from . import test_registration

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Email tests require --settings=config.test_settings.")


class EmailRegistrationAPITests(test_registration.RegistrationAPITests):
    def test_duplicate_email_has_identical_public_response_and_preserves_owner(self):
        self.assertEqual(self.complete().status_code, 200)
        owner = Account.objects.get()
        before = Account.objects.values().get(pk=owner.pk)
        self.data.update(school_id="0012346", email=" \tREGISTRANT@EXAMPLE.EDU\t ", first_name="Other")
        second = self.post()
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["error"]["code"], "conflict")
        other = self.post({**self.data, "school_id": owner.school_id, "email": "other@example.edu"})
        self.assertEqual(other.status_code, 409)
        self.assertEqual(second.json()["error"]["message"], other.json()["error"]["message"])
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)
        self.assertEqual(Account.objects.values().get(pk=owner.pk), before)
        self.assertEqual(owner.profile.first_name, "Maria")
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())

    def test_new_email_is_canonical_in_serializer_and_database(self):
        self.data["email"] = " \tNew.Person@EXAMPLE.EDU\n "
        serializer = RegistrationSerializer(data=self.data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["email"], "new.person@example.edu")
        self.assertEqual(self.complete().status_code, 200)
        self.assertEqual(Account.objects.get().email, "new.person@example.edu")

    def test_unrelated_duplicate_key_error_stays_unavailable(self):
        self.assertEqual(self.post().status_code, 202)
        with patch("apps.accounts.registration_staging.UserProfile.objects.create", side_effect=IntegrityError(1062, "private detail")):
            self.assert_rejected(self.verify(), status=503)

    def test_executor_unavailability_does_not_fall_back_to_local_writes(self):
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):
            self.assert_rejected(self.post(), status=503)


class EmailDatabaseTests(TestCase):
    def test_model_and_manager_normalize_and_allow_multiple_nulls(self):
        for n, email in enumerate((None, "", " \t\n "), 1):
            account = Account.objects.create(school_id=f"null{n}", email=email)
            account.refresh_from_db()
            self.assertIsNone(account.email)
        account = Account.objects.create_user("email1", " Person@EXAMPLE.EDU ")
        self.assertEqual(account.email, "person@example.edu")
        account.email = " Updated@EXAMPLE.EDU "
        account.save(update_fields=["email"])
        account.refresh_from_db()
        self.assertEqual(account.email, "updated@example.edu")
        other = Account(school_id="email2", email=" UPDATED@EXAMPLE.EDU ")
        with self.assertRaises(IntegrityError), transaction.atomic():
            other.save()

    def test_mysql_rejects_case_duplicate_without_model_validation(self):
        Account.objects.create(school_id="raw1", email="person@example.edu")
        with self.assertRaises(IntegrityError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO accounts (school_id, password_hash, email) VALUES (%s,%s,%s)",
                    ("raw2", "unusable", "PERSON@EXAMPLE.EDU"),
                )
        self.assertEqual(Account.objects.count(), 1)
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, "accounts")
        self.assertTrue(any(c["unique"] and c["columns"] == ["email"] for c in constraints.values()))
        self.assertTrue(any(c["unique"] and c["columns"] == ["school_id"] for c in constraints.values()))

    def test_model_validation_and_school_id_uniqueness_remain_effective(self):
        Account.objects.create(school_id="school1", email="person@example.edu")
        candidate = Account(school_id="school2", email="person@example.edu")
        with self.assertRaises(ValidationError):
            candidate.validate_unique()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Account.objects.create(school_id="school1", email="another@example.edu")

    def test_partial_password_write_does_not_change_email(self):
        account = Account.objects.create(school_id="partial", email="person@example.edu")
        account.email = "OTHER@example.edu"
        account.set_password("Good!Password5432")
        account.save(update_fields=["password"])
        account.refresh_from_db()
        self.assertEqual(account.email, "person@example.edu")
        self.assertTrue(account.check_password("Good!Password5432"))


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ConcurrentEmailRegistrationTests(TransactionTestCase):
    def test_concurrent_instructor_http_requests_reserve_one_stage_then_create_one_verified_pair(self):
        from django.core import mail
        from .test_student_registration_otp import last_code
        cache.clear()
        Role.objects.create(role_name="Instructor")
        barrier = Barrier(2, timeout=20)

        def submit(n):
            try:
                client = APIClient(enforce_csrf_checks=True)
                csrf = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
                barrier.wait()
                response = client.post("/api/v1/auth/register/", {
                    "school_id": "1000011", "email": f"race{n}@example.edu",
                    "first_name": "Concurrent", "last_name": "Instructor",
                    "requested_role": "Instructor", "password": "Copper!River7392",
                    "password_confirmation": "Copper!River7392",
                }, format="json", HTTP_X_CSRFTOKEN=csrf)
                self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
                return response, client, csrf
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=30) for future in [pool.submit(submit, 1), pool.submit(submit, 2)]]
        self.assertCountEqual([response.status_code for response, _, _ in results], [202, 409])
        self.assertNotEqual(results[0][0]["X-Request-ID"], results[1][0]["X-Request-ID"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(Account.objects.exists())
        self.assertFalse(UserProfile.objects.exists())
        _, owner, csrf = next(row for row in results if row[0].status_code == 202)
        completed = owner.post("/api/v1/auth/register/verify/?requested_role=Instructor", {"code": last_code()}, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(completed.status_code, 200, completed.content)
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)
        self.assertIsNotNone(Account.objects.get().email_verified_at)
        self.assertFalse(Account.objects.get().is_active)
        self.assertFalse(AccountRole.objects.exists())
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())

    def test_racing_instructor_normalized_email_reservations_then_completion_create_one_account(self):
        from .registration_staging import student_verification_action
        from .test_student_registration_otp import last_code
        cache.clear()
        for name in ("Student", "Instructor"):
            Role.objects.create(role_name=name)
        barrier = Barrier(2, timeout=20)

        def submit(n, email):
            try:
                serializer = RegistrationSerializer(data={
                    "school_id": f"100000{n}", "email": email,
                    "first_name": "Concurrent", "last_name": "Applicant",
                    "requested_role": "Instructor", "password": "Copper!River7392",
                    "password_confirmation": "Copper!River7392",
                })
                serializer.is_valid(raise_exception=True)
                barrier.wait()
                return register_account(serializer.validated_data)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=30) for future in [pool.submit(submit, 1, "Race@EXAMPLE.EDU"), pool.submit(submit, 2, " race@example.edu ")]]
        self.assertCountEqual([result["status"] for result in results], ["verification_required", "conflict"])
        self.assertFalse(Account.objects.exists())
        owner = next(result for result in results if result["status"] == "verification_required")
        self.assertEqual(student_verification_action(owner["browser_token"], "verify", last_code())["status"], "completed")
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(Account.objects.get().email, "race@example.edu")
        self.assertEqual(UserProfile.objects.count(), 1)
        self.assertFalse(AccountRole.objects.exists())
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())


class EmailMigrationTests(TransactionTestCase):
    before = ("accounts", "0003_registration_notification_outbox")
    after = ("accounts", "0004_account_email_unique")

    def setUp(self):
        MigrationExecutor(connection).migrate([self.before])
        self.old_apps = MigrationExecutor(connection).loader.project_state([self.before]).apps
        self.old_account = self.old_apps.get_model("accounts", "Account")

    def tearDown(self):
        # These are exclusively this test's synthetic fixtures.
        self.old_account.objects.all().delete()
        # Restore the CURRENT accounts leaf (not a hard-coded name): since SR-1 Stage A that is 0006, and stopping at
        # 0005 would leave every later test without accounts.session_revocation_version.
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes("accounts"))
        super().tearDown()

    def test_forward_and_reverse_preserve_all_account_values(self):
        for n, email in enumerate((None, None, "canonical@example.edu")):
            self.old_account.objects.create(school_id=f"m{n}", email=email, password="preserved-hash")
        before = list(self.old_account.objects.order_by("pk").values())
        MigrationExecutor(connection).migrate([self.after])
        migrated_account = MigrationExecutor(connection).loader.project_state([self.after]).apps.get_model("accounts", "Account")
        self.assertEqual(list(migrated_account.objects.order_by("pk").values()), before)
        with self.assertRaises(IntegrityError), transaction.atomic():
            migrated_account.objects.create(school_id="collision", email="CANONICAL@example.edu")
        with CaptureQueriesContext(connection) as queries:
            MigrationExecutor(connection).migrate([self.before])
        ddl = [q["sql"] for q in queries if q["sql"].startswith("ALTER TABLE")]
        self.assertEqual(ddl, ["ALTER TABLE `accounts` DROP INDEX `accounts_email_200aa879_uniq`"])
        self.assertEqual(list(self.old_account.objects.order_by("pk").values()), before)

    def test_unsafe_legacy_emails_stop_preflight_without_writes(self):
        guard = import_module("apps.accounts.migrations.0004_account_email_unique").require_reconciled_emails
        for emails in (("same@example.edu", "same@example.edu"),
                       ("Person@example.edu", " person@example.edu\t"),
                       ("", " \t"), ("person@example.edu\u2003",),
                       ("cafe@example.edu", "caf\u00e9@example.edu")):
            with self.subTest(emails=emails):
                for n, email in enumerate(emails):
                    self.old_account.objects.create(school_id=f"legacy{n}", email=email)
                before = list(self.old_account.objects.order_by("pk").values())
                with CaptureQueriesContext(connection) as queries, connection.schema_editor() as editor:
                    with self.assertRaises(RuntimeError):
                        guard(self.old_apps, editor)
                self.assertTrue(all(q["sql"].lstrip().upper().startswith("SELECT") for q in queries))
                self.assertEqual(list(self.old_account.objects.order_by("pk").values()), before)
                self.old_account.objects.all().delete()
