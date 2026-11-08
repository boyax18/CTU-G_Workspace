from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.db import NotSupportedError
from django.db.backends.mysql.base import DatabaseWrapper
from django.db.migrations.writer import MigrationWriter
from django.test import SimpleTestCase, override_settings

from apps.access_control.models import Role

from .fields import CurrentTimestamp, MySQLEnumField, MySQLTimestampField
from .models import Account

from contextlib import nullcontext

@override_settings(
    AUTH_PASSWORD_VALIDATORS=[
        {
            "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
            "OPTIONS": {"min_length": 12},
        }
    ]
)
class AccountCreationTests(SimpleTestCase):
    """Exercise account creation without allowing database access."""

    password = "Z8!qV4#mN7@rL2$w"

    def test_password_is_hashed_and_new_account_is_pending_and_inactive(self):
        with patch.object(Account, "save") as save:
            account = Account.objects.create_user(" 2026-12345 ", password=self.password)

        save.assert_called_once_with(using=None)
        self.assertEqual(account.school_id, "2026-12345")
        self.assertNotEqual(account.password, self.password)
        self.assertTrue(account.check_password(self.password))
        self.assertFalse(account.check_password("incorrect password"))
        self.assertEqual(account.request_status, "Pending")
        self.assertFalse(account.is_active)
        self.assertFalse(account.is_staff)
        self.assertFalse(account.is_superuser)

    def test_weak_password_is_rejected_before_save(self):
        with patch.object(Account, "save") as save:
            with self.assertRaises(ValidationError):
                Account.objects.create_user("2026-12345", password="short")
        save.assert_not_called()

    def test_absent_password_is_unusable(self):
        with patch.object(Account, "save"):
            account = Account.objects.create_user("2026-12345")
        self.assertFalse(account.has_usable_password())

    def test_email_is_optional(self):
        for email in (None, "", "   "):
            with self.subTest(email=email), patch.object(Account, "save"):
                account = Account.objects.create_user("2026-12345", email=email)
            self.assertIsNone(account.email)

    def test_email_is_not_unique_and_domain_is_normalized(self):
        with patch.object(Account, "save") as save:
            first = Account.objects.create_user("2026-12345", "Person@EXAMPLE.COM")
            second = Account.objects.create_user("2026-54321", "Person@example.com")
        self.assertEqual(save.call_count, 2)
        self.assertEqual(first.email, "Person@example.com")
        self.assertEqual(second.email, first.email)
        self.assertFalse(Account._meta.get_field("email").unique)

    def test_invalid_identity_inputs_are_rejected_before_save(self):
        cases = [
            {"school_id": ""},
            {"school_id": "   "},
            {"school_id": None},
            {"school_id": "x" * 51},
            {"school_id": "2026-12345", "email": "invalid-email"},
        ]
        for values in cases:
            with self.subTest(values=values), patch.object(Account, "save") as save:
                with self.assertRaises((ValueError, ValidationError)):
                    Account.objects.create_user(**values)
                save.assert_not_called()

    def test_server_managed_fields_cannot_be_supplied_to_create_user(self):
        values = {
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
            "request_status": "Approved",
            "requested_role_id": 1,
            "reviewed_by": Account(account_id=1),
            "reviewed_by_id": 1,
            "reviewed_at": "2026-11-06T00:00:00Z",
            "rejection_reason": "Injected review",
            "created_at": "2026-11-06T00:00:00Z",
            "account_id": 1,
            "password_hash": "injected hash",
            "password_reset_token": "injected token",
            "password_reset_token_expires": "2026-11-07T00:00:00Z",
        }
        for field, value in values.items():
            with self.subTest(field=field), patch.object(Account, "save") as save:
                with self.assertRaises(ValueError):
                    Account.objects.create_user("2026-12345", **{field: value})
                save.assert_not_called()

    def test_superuser_creation_is_framework_only(self):
        with (
            patch(
                "apps.accounts.models.transaction.atomic",
                return_value=nullcontext(),
            ),
            patch.object(Account, "save") as save,
        ):
            account = Account.objects.create_superuser(
                school_id="IT-ADMIN-001",
                password=self.password,
            )

        self.assertTrue(account.is_staff)
        self.assertTrue(account.is_superuser)
        self.assertTrue(account.is_active)

        self.assertEqual(account.request_status, "Approved")
        self.assertIsNone(account.requested_role_id)

        self.assertTrue(account.check_password(self.password))
        self.assertEqual(save.call_count, 2)


    def test_superuser_cannot_bypass_workspace_permissions(self):
        account = Account(
            school_id="IT-ADMIN-001",
            is_staff=True,
            is_superuser=True,
            is_active=True,
            request_status="Approved",
        )

        with patch(
            "apps.access_control.services.has_permission",
            return_value=False,
        ):
            self.assertFalse(
                account.has_perm("access_control.role_permissions.manage")
            )

        self.assertFalse(account.has_module_perms("accounts"))

    def test_authorization_fails_closed(self):
        account = Account(request_status="Approved", is_active=True)
        self.assertFalse(account.has_perm("accounts.change_account"))
        self.assertFalse(account.has_module_perms("accounts"))


class RequestedRoleTests(SimpleTestCase):
    def test_active_student_and_instructor_requests_remain_pending(self):
        for name in ("Student", "Instructor"):
            with self.subTest(name=name):
                persisted_role = Role(role_id=7, role_name=name, is_active=True)
                supplied_role = Role(role_id=7, role_name="Untrusted client label")
                with (
                    patch.object(Role._default_manager, "db_manager") as db_manager,
                    patch.object(Account, "save") as save,
                ):
                    db_manager.return_value.get.return_value = persisted_role
                    account = Account.objects.db_manager("provisioning").create_user(
                        "2026-12345", requested_role=supplied_role
                    )
                db_manager.assert_called_once_with("provisioning")
                db_manager.return_value.get.assert_called_once_with(pk=7, is_active=True)
                save.assert_called_once_with(using="provisioning")
                self.assertIs(account.requested_role, persisted_role)
                self.assertEqual(account.request_status, "Pending")
                self.assertFalse(account.is_active)
                self.assertFalse(account.is_staff)

    def test_forged_student_label_does_not_allow_admin_or_treasurer_request(self):
        for name in ("Admin", "Treasurer"):
            with self.subTest(name=name):
                supplied_role = Role(role_id=7, role_name="Student", is_active=True)
                persisted_role = Role(role_id=7, role_name=name, is_active=True)
                with (
                    patch.object(Role._default_manager, "db_manager") as db_manager,
                    patch.object(Account, "save") as save,
                ):
                    db_manager.return_value.get.return_value = persisted_role
                    with self.assertRaisesMessage(ValueError, "Only Student or Instructor"):
                        Account.objects.create_user("2026-12345", requested_role=supplied_role)
                save.assert_not_called()

    def test_missing_or_inactive_role_is_rejected_by_active_lookup(self):
        for supplied_role in (
            Role(role_id=7, role_name="Student", is_active=False),
            Role(role_id=999, role_name="Student", is_active=True),
        ):
            with self.subTest(role_id=supplied_role.pk):
                with (
                    patch.object(Role._default_manager, "db_manager") as db_manager,
                    patch.object(Account, "save") as save,
                ):
                    db_manager.return_value.get.side_effect = Role.DoesNotExist
                    with self.assertRaisesMessage(ValueError, "active and exist"):
                        Account.objects.create_user("2026-12345", requested_role=supplied_role)
                db_manager.return_value.get.assert_called_once_with(
                    pk=supplied_role.pk, is_active=True
                )
                save.assert_not_called()

    def test_unsaved_or_wrong_type_role_is_rejected_without_lookup(self):
        for supplied_role in (Role(role_name="Student"), 7, "Student"):
            with self.subTest(role=repr(supplied_role)):
                with (
                    patch.object(Role._default_manager, "db_manager") as db_manager,
                    patch.object(Account, "save") as save,
                ):
                    with self.assertRaisesMessage(ValueError, "existing Role"):
                        Account.objects.create_user("2026-12345", requested_role=supplied_role)
                db_manager.assert_not_called()
                save.assert_not_called()


class NativeAuthenticationFieldTests(SimpleTestCase):
    mysql = SimpleNamespace(vendor="mysql")

    def test_enum_preserves_values_order_and_defaults_when_cloned(self):
        field = Account._meta.get_field("request_status")
        clone = field.clone()
        self.assertIsInstance(clone, MySQLEnumField)
        self.assertEqual(clone.db_type(self.mysql), "enum('Pending','Approved','Rejected')")
        self.assertEqual(clone.default, "Pending")
        self.assertEqual(clone.db_default, "Pending")
        self.assertEqual(clone.deconstruct()[1:], field.deconstruct()[1:])

    def test_enum_rejects_values_that_cannot_be_safely_embedded(self):
        for choices in ([], [("Pending'", "Unsafe")], [(1, "Non-string")]):
            with self.subTest(choices=choices):
                field = MySQLEnumField(max_length=8, choices=choices)
                with self.assertRaises(ValueError):
                    field.db_type(self.mysql)

    def test_timestamp_clone_preserves_native_type_default_and_datetime_conversion(self):
        field = Account._meta.get_field("created_at")
        clone = field.clone()
        self.assertIsInstance(clone, MySQLTimestampField)
        self.assertEqual(clone.db_type(self.mysql), "timestamp")
        self.assertEqual(clone.get_internal_type(), "DateTimeField")
        self.assertIsInstance(clone.db_default, CurrentTimestamp)
        self.assertEqual(clone.deconstruct()[1:], field.deconstruct()[1:])

    def test_native_fields_do_not_silently_fall_back_on_other_backends(self):
        for vendor in ("sqlite", "postgresql"):
            for name in ("request_status", "created_at"):
                with self.subTest(vendor=vendor, field=name):
                    with self.assertRaises(NotSupportedError):
                        Account._meta.get_field(name).db_type(SimpleNamespace(vendor=vendor))

    def test_current_timestamp_expression_has_no_fractional_precision(self):
        connection = SimpleNamespace(ops=Mock())
        compiler = Mock()
        expression = CurrentTimestamp()
        self.assertEqual(expression.as_sql(compiler, connection), ("CURRENT_TIMESTAMP", ()))
        self.assertTrue(expression.allowed_default)
        compiler.compile.assert_not_called()


class NativeEnumMigrationTests(SimpleTestCase):
    """Check ENUM migration decisions entirely in memory, without schema operations."""

    def setUp(self):
        super().setUp()
        self.connection = DatabaseWrapper(
            {
                "ENGINE": "django.db.backends.mysql",
                "NAME": "",
                "OPTIONS": {},
                "TIME_ZONE": None,
            },
            alias="offline_enum_review",
        )
        self.connection.mysql_is_mariadb = False
        self.ensure_connection = self.enterContext(
            patch.object(
                self.connection,
                "ensure_connection",
                side_effect=AssertionError("ENUM migration tests cannot connect to a database."),
            )
        )
        self.cursor = self.enterContext(
            patch.object(
                self.connection,
                "cursor",
                side_effect=AssertionError("ENUM migration tests cannot execute SQL."),
            )
        )
        self.editor = self.connection.schema_editor(collect_sql=True, atomic=False)

    def tearDown(self):
        self.ensure_connection.assert_not_called()
        self.cursor.assert_not_called()
        self.assertIsNone(self.connection.connection)
        super().tearDown()

    def request_status_field(self, choices):
        field = Account._meta.get_field("request_status").clone()
        field.choices = choices
        field.set_attributes_from_name("request_status")
        field.model = Account
        return field

    def assert_enum_alter_required(self, choices):
        old_field = self.request_status_field(Account.REQUEST_STATUS_CHOICES)
        new_field = self.request_status_field(choices)
        self.assertEqual(old_field.max_length, new_field.max_length)
        self.assertEqual(old_field.default, new_field.default)
        self.assertEqual(old_field.db_default, new_field.db_default)
        self.assertNotEqual(
            old_field.db_type(self.connection), new_field.db_type(self.connection)
        )
        self.assertTrue(self.editor._field_should_be_altered(old_field, new_field))

    def test_adding_enum_value_requires_alter_without_length_or_default_change(self):
        self.assert_enum_alter_required(
            [*Account.REQUEST_STATUS_CHOICES, ("Dormant", "Dormant")]
        )

    def test_removing_enum_value_requires_alter_without_length_or_default_change(self):
        self.assert_enum_alter_required(Account.REQUEST_STATUS_CHOICES[:-1])

    def test_reordering_enum_values_requires_alter(self):
        self.assert_enum_alter_required(list(reversed(Account.REQUEST_STATUS_CHOICES)))

    def test_unchanged_enum_is_noop_and_retains_exact_sql_type(self):
        old_field = self.request_status_field(Account.REQUEST_STATUS_CHOICES)
        new_field = self.request_status_field(list(Account.REQUEST_STATUS_CHOICES))
        self.assertFalse(self.editor._field_should_be_altered(old_field, new_field))
        self.assertEqual(
            new_field.db_type(self.connection), "enum('Pending','Approved','Rejected')"
        )

    def test_enum_migration_writer_round_trip_preserves_schema_configuration(self):
        for choices in (
            Account.REQUEST_STATUS_CHOICES,
            [*Account.REQUEST_STATUS_CHOICES, ("Dormant", "Dormant")],
            list(reversed(Account.REQUEST_STATUS_CHOICES)),
        ):
            with self.subTest(choices=choices):
                field = self.request_status_field(choices)
                serialized, imports = MigrationWriter.serialize(field)
                namespace = {}
                for statement in imports:
                    exec(statement, namespace)
                restored = eval(serialized, namespace)
                self.assertIsInstance(restored, MySQLEnumField)
                self.assertEqual(restored.choices, field.choices)
                self.assertEqual(restored.max_length, field.max_length)
                self.assertEqual(restored.default, field.default)
                self.assertEqual(restored.db_default, field.db_default)
                self.assertEqual(
                    restored.db_type(self.connection), field.db_type(self.connection)
                )
