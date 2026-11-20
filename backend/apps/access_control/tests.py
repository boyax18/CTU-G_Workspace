import re
from io import StringIO
from unittest import SkipTest
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, models
from django.db.backends.mysql.base import DatabaseWrapper
from django.db.migrations.writer import MigrationWriter
from django.db.models.query import QuerySet
from django.db.models.signals import post_save
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext

from apps.accounts.fields import CurrentTimestamp, MySQLEnumField, MySQLTimestampField
from apps.accounts.models import Account, UserProfile

from .models import (
    AccessAuditLog,
    AccountPermission,
    AccountRole,
    Permission,
    Role,
    RolePermission,
    Service,
)


class AccountRoleTests(SimpleTestCase):
    """Verify assignment mappings and boundaries without writing records."""

    def setUp(self):
        super().setUp()
        self.connection = DatabaseWrapper(
            {
                "ENGINE": "django.db.backends.mysql",
                "NAME": "",
                "OPTIONS": {},
                "TIME_ZONE": None,
            },
            alias="offline_account_role_review",
        )
        self.connection.mysql_is_mariadb = False
        self.ensure_connection = self.enterContext(
            patch.object(
                self.connection,
                "ensure_connection",
                side_effect=AssertionError("AccountRole tests cannot connect to a database."),
            )
        )
        self.cursor = self.enterContext(
            patch.object(
                self.connection,
                "cursor",
                side_effect=AssertionError("AccountRole tests cannot execute SQL."),
            )
        )
        self.editor = self.connection.schema_editor(collect_sql=True, atomic=False)

    def tearDown(self):
        self.ensure_connection.assert_not_called()
        self.cursor.assert_not_called()
        self.assertIsNone(self.connection.connection)
        super().tearDown()

    def test_table_has_only_the_five_approved_columns_and_integer_primary_key(self):
        self.assertEqual(AccountRole._meta.db_table, "account_roles")
        self.assertEqual(
            {field.column for field in AccountRole._meta.local_fields},
            {"account_role_id", "account_id", "role_id", "assigned_by", "assigned_at"},
        )
        primary_key = AccountRole._meta.pk
        self.assertEqual(primary_key.name, "account_role_id")
        self.assertIsInstance(primary_key, models.AutoField)
        self.assertEqual(primary_key.db_type(self.connection), "integer AUTO_INCREMENT")
        self.assertFalse(primary_key.null)

    def test_foreign_keys_target_the_approved_keys_with_protect_deletion(self):
        definitions = [
            ("account", Account, "account_id", "account_id", False),
            ("role", Role, "role_id", "role_id", False),
            ("assigned_by", Account, "assigned_by", "account_id", True),
        ]
        for name, target, column, target_key, nullable in definitions:
            with self.subTest(field=name):
                field = AccountRole._meta.get_field(name)
                self.assertIsInstance(field, models.ForeignKey)
                self.assertIs(field.remote_field.model, target)
                self.assertEqual(field.column, column)
                self.assertEqual(field.target_field.column, target_key)
                self.assertEqual(field.null, nullable)
                self.assertEqual(field.blank, nullable)
                self.assertFalse(field.unique)
                self.assertIs(field.remote_field.on_delete, models.PROTECT)
        self.assertFalse(AccountRole._meta.get_field("assigned_by").editable)

    def test_account_and_role_are_unique_as_a_pair_not_individually(self):
        self.assertEqual(len(AccountRole._meta.constraints), 1)
        constraint = AccountRole._meta.constraints[0]
        self.assertIsInstance(constraint, models.UniqueConstraint)
        self.assertEqual(constraint.fields, ("account", "role"))
        self.assertEqual(constraint.name, "account_roles_account_role_unique")
        self.assertIsNone(constraint.condition)
        sql = str(constraint.constraint_sql(AccountRole, self.editor))
        self.assertIn("UNIQUE (`account_id`, `role_id`)", sql)

    def test_assigned_at_is_native_timestamp_with_database_current_time_default(self):
        field = AccountRole._meta.get_field("assigned_at")
        self.assertIsInstance(field, MySQLTimestampField)
        self.assertFalse(field.null)
        self.assertFalse(field.editable)
        self.assertFalse(field.has_default())
        self.assertIsInstance(field.db_default, CurrentTimestamp)
        sql, params = self.editor.column_sql(AccountRole, field)
        self.assertEqual(sql, "timestamp DEFAULT (CURRENT_TIMESTAMP) NOT NULL")
        self.assertEqual(params, [])

    def test_fields_and_unique_constraint_serialize_and_reconstruct_in_memory(self):
        values = [*AccountRole._meta.local_fields, *AccountRole._meta.constraints]
        for value in values:
            with self.subTest(value=value.name):
                source, imports = MigrationWriter.serialize(value)
                namespace = {}
                for statement in sorted(imports):
                    exec(statement, namespace)
                reconstructed = eval(source, namespace)
                self.assertEqual(MigrationWriter.serialize(reconstructed), (source, imports))

    def test_reverse_relationships_keep_requests_assignments_and_actors_separate(self):
        self.assertIs(Account.role_assignments.rel.field, AccountRole._meta.get_field("account"))
        self.assertIs(
            Account.role_assignments_made.rel.field,
            AccountRole._meta.get_field("assigned_by"),
        )
        self.assertIs(Role.account_assignments.rel.field, AccountRole._meta.get_field("role"))
        self.assertIs(
            Role.requesting_accounts.rel.field, Account._meta.get_field("requested_role")
        )

    def test_registration_request_does_not_create_a_role_assignment(self):
        role = Role(role_id=7, role_name="Student", is_active=True)

        def simulate_account_save(instance, **kwargs):
            instance.account_id = 1
            post_save.send(
                sender=Account,
                instance=instance,
                created=True,
                raw=False,
                using=kwargs.get("using") or "default",
                update_fields=None,
            )

        with (
            patch.object(Role._default_manager, "db_manager") as role_manager,
            patch.object(
                Account, "save", autospec=True, side_effect=simulate_account_save
            ) as account_save,
            patch.object(AccountRole._default_manager, "create") as assignment_create,
            patch.object(AccountRole, "save") as assignment_save,
        ):
            role_manager.return_value.get.return_value = role
            account = Account.objects.create_user("2026-12345", requested_role=role)
        account_save.assert_called_once_with(account, using=None)
        assignment_create.assert_not_called()
        assignment_save.assert_not_called()
        self.assertIs(account.requested_role, role)
        self.assertEqual(account.request_status, "Pending")
        self.assertFalse(account.is_active)
        self.assertFalse(account.is_staff)
        self.assertFalse(account.has_perm("access_control.add_accountrole"))

    def test_registration_rejects_client_supplied_assignment_actor(self):
        actor = Account(account_id=99, school_id="actor")
        with patch.object(Account, "save") as save:
            with self.assertRaises(ValueError):
                Account.objects.create_user("2026-12345", assigned_by=actor)
        save.assert_not_called()

    def test_assignment_actor_metadata_does_not_establish_administrator_authorization(self):
        account = Account(account_id=1, school_id="student")
        actor = Account(account_id=2, school_id="actor")
        assignment = AccountRole(
            account=account,
            role=Role(role_id=3, role_name="Admin"),
            assigned_by=actor,
        )
        self.assertIs(assignment.assigned_by, actor)
        self.assertFalse(account.is_staff)
        self.assertFalse(account.is_superuser)
        self.assertFalse(actor.is_staff)
        self.assertFalse(actor.is_superuser)
        self.assertFalse(account.has_perm("access_control.add_accountrole"))
        self.assertFalse(actor.has_perm("access_control.add_accountrole"))


class InitSystemRolesTests(TestCase):
    """Exercise actual MySQL uniqueness and rollback only in an isolated test DB."""

    canonical_names = {"Student", "Instructor", "Treasurer", "Admin"}
    write_sql = re.compile(
        r"^\s*(?:INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP|TRUNCATE)\b",
        re.IGNORECASE,
    )

    @classmethod
    def setUpClass(cls):
        database_name = str(connection.settings_dict.get("NAME", ""))
        if database_name == "ctug_workspace" or not database_name.startswith("test_"):
            raise RuntimeError("Role initialization tests require an isolated test_ database.")
        if connection.vendor != "mysql":
            raise SkipTest("Native MySQL collation and transaction tests require MySQL.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            actual_database = cursor.fetchone()[0]
        if actual_database != database_name:
            raise RuntimeError("The connected database differs from the isolated test database.")
        super().setUpClass()

    def run_command(self, *, dry_run=False, stdout=None):
        stdout = stdout if stdout is not None else StringIO()
        call_command(
            "init_system_roles",
            database="default",
            dry_run=dry_run,
            stdout=stdout,
            stderr=StringIO(),
            no_color=True,
        )
        return stdout.getvalue()

    def role_state(self):
        return list(
            Role.objects.order_by("role_id").values_list(
                "role_id", "role_name", "description", "is_active"
            )
        )

    def assert_no_writes(self, queries):
        writes = [query["sql"] for query in queries if self.write_sql.match(query["sql"])]
        self.assertEqual(writes, [])

    def assert_conflict_is_rejected(self, stored_name, *, dry_run=False):
        existing = Role.objects.create(
            role_name=stored_name, description="Preserve this existing role.", is_active=False
        )
        # This checks the database's real collation, rather than simulating equality.
        self.assertEqual(Role.objects.get(role_name="Student").pk, existing.pk)
        before = self.role_state()
        stdout = StringIO()
        with CaptureQueriesContext(connection) as queries:
            with self.assertRaises(CommandError):
                self.run_command(dry_run=dry_run, stdout=stdout)
        self.assertEqual(self.role_state(), before)
        self.assert_no_writes(queries.captured_queries)
        self.assertNotIn("Created", stdout.getvalue())

    def test_initial_execution_creates_only_the_four_canonical_active_roles(self):
        from .management.commands.init_system_roles import SYSTEM_ROLES

        output = self.run_command()

        self.assertEqual({name for name, _description in SYSTEM_ROLES}, self.canonical_names)
        self.assertEqual(Role.objects.count(), 4)
        for name, description in SYSTEM_ROLES:
            with self.subTest(role=name):
                role = Role.objects.get(role_name=name)
                self.assertEqual(role.description, description)
                self.assertTrue(description)
                self.assertLessEqual(len(description), 255)
                self.assertTrue(role.is_active)
                self.assertIn(name, output)
        self.assertEqual(output.count("Created"), 4)

    def test_role_creation_does_not_assume_fixed_primary_keys(self):
        unrelated = Role.objects.create(role_id=41, role_name="Existing unrelated role")

        self.run_command()

        self.assertEqual(Role.objects.get(pk=unrelated.pk).role_name, unrelated.role_name)
        self.assertEqual(Role.objects.count(), 5)
        self.assertTrue(
            all(
                role_id > unrelated.pk
                for role_id in Role.objects.filter(role_name__in=self.canonical_names)
                .values_list("role_id", flat=True)
            )
        )

    def test_repeated_execution_keeps_existing_rows_and_performs_no_updates(self):
        self.run_command()
        before = self.role_state()

        with CaptureQueriesContext(connection) as queries:
            output = self.run_command()

        self.assertEqual(self.role_state(), before)
        self.assertEqual(Role.objects.count(), 4)
        self.assert_no_writes(queries.captured_queries)
        self.assertEqual(output.count("Exists"), 4)
        self.assertNotIn("Created", output)

    def test_existing_custom_and_null_descriptions_are_preserved(self):
        student = Role.objects.create(role_name="Student", description="Local description")
        instructor = Role.objects.create(role_name="Instructor", description=None)

        self.run_command()

        student.refresh_from_db()
        instructor.refresh_from_db()
        self.assertEqual(student.description, "Local description")
        self.assertIsNone(instructor.description)
        self.assertEqual(Role.objects.get(role_name="Student").pk, student.pk)
        self.assertEqual(Role.objects.get(role_name="Instructor").pk, instructor.pk)

    def test_existing_inactive_role_is_preserved_and_reported(self):
        treasurer = Role.objects.create(
            role_name="Treasurer", description="Disabled by an operator", is_active=False
        )

        output = self.run_command()

        treasurer.refresh_from_db()
        self.assertFalse(treasurer.is_active)
        self.assertEqual(treasurer.description, "Disabled by an operator")
        self.assertEqual(Role.objects.get(role_name="Treasurer").pk, treasurer.pk)
        self.assertRegex(output, r"Exists[^\n]*Treasurer[^\n]*inactive")

    def test_case_equivalent_role_name_is_rejected_without_writes(self):
        self.assert_conflict_is_rejected("student")

    def test_accent_equivalent_role_name_is_rejected_without_writes(self):
        self.assert_conflict_is_rejected("Studént")

    def test_trailing_space_equivalent_role_name_is_rejected_without_writes(self):
        self.assert_conflict_is_rejected("Student ")

    def test_failure_after_an_insert_rolls_back_the_entire_initialization(self):
        original_get_or_create = QuerySet.get_or_create
        observed_partial_insert = []

        def fail_after_student(queryset, *args, **kwargs):
            if queryset.model is Role and kwargs.get("role_name") == "Instructor":
                observed_partial_insert.append(Role.objects.filter(role_name="Student").exists())
                raise DatabaseError("Injected initialization failure")
            return original_get_or_create(queryset, *args, **kwargs)

        stdout = StringIO()
        with patch.object(QuerySet, "get_or_create", autospec=True, side_effect=fail_after_student):
            with self.assertRaises(CommandError):
                self.run_command(stdout=stdout)

        self.assertEqual(observed_partial_insert, [True])
        self.assertEqual(Role.objects.count(), 0)
        self.assertNotIn("Created", stdout.getvalue())

    def test_collation_conflict_detected_after_preflight_also_rolls_back(self):
        original_get_or_create = QuerySet.get_or_create
        injected_conflict = []

        def insert_conflicting_name(queryset, *args, **kwargs):
            if queryset.model is Role and kwargs.get("role_name") == "Student":
                Role.objects.create(role_name="student", description="Concurrent name conflict")
                injected_conflict.append(True)
            return original_get_or_create(queryset, *args, **kwargs)

        with patch.object(
            QuerySet, "get_or_create", autospec=True, side_effect=insert_conflicting_name
        ):
            with self.assertRaises(CommandError):
                self.run_command()

        self.assertEqual(injected_conflict, [True])
        self.assertEqual(Role.objects.count(), 0)

    def test_dry_run_reports_all_missing_roles_without_writes(self):
        with CaptureQueriesContext(connection) as queries:
            output = self.run_command(dry_run=True)

        self.assertEqual(Role.objects.count(), 0)
        self.assert_no_writes(queries.captured_queries)
        self.assertEqual(output.count("Would create"), 4)
        for name in self.canonical_names:
            self.assertIn(name, output)

    def test_dry_run_preserves_existing_inactive_roles_and_reports_missing_roles(self):
        Role.objects.create(role_name="Student", description="Custom", is_active=False)
        Role.objects.create(role_name="Admin", description=None)
        before = self.role_state()

        with CaptureQueriesContext(connection) as queries:
            output = self.run_command(dry_run=True)

        self.assertEqual(self.role_state(), before)
        self.assert_no_writes(queries.captured_queries)
        self.assertEqual(output.count("Exists"), 2)
        self.assertEqual(output.count("Would create"), 2)
        self.assertRegex(output, r"Exists[^\n]*Student[^\n]*inactive")

    def test_dry_run_rejects_collation_conflicts_without_writes(self):
        self.assert_conflict_is_rejected("student", dry_run=True)

    def test_initialization_never_creates_accounts_profiles_or_assignments(self):
        with (
            patch.object(Account, "save", side_effect=AssertionError("No account creation")),
            patch.object(UserProfile, "save", side_effect=AssertionError("No profile creation")),
            patch.object(AccountRole, "save", side_effect=AssertionError("No assignment creation")),
            CaptureQueriesContext(connection) as queries,
        ):
            self.run_command()

        self.assertEqual(Account.objects.count(), 0)
        self.assertEqual(UserProfile.objects.count(), 0)
        self.assertEqual(AccountRole.objects.count(), 0)
        writes = [query["sql"] for query in queries if self.write_sql.match(query["sql"])]
        self.assertEqual(len(writes), 4)
        for sql in writes:
            self.assertRegex(sql, r"^INSERT INTO `roles`")


class RemainingAccessControlModelTests(SimpleTestCase):
    """Check approved mappings and MySQL declarations without database access."""

    definitions = {
        Service: (
            "services",
            "service_id",
            {"service_id", "service_name", "service_code", "description", "is_active"},
            {"description"},
        ),
        Permission: (
            "permissions",
            "permission_id",
            {
                "permission_id", "service_id", "permission_code", "permission_name",
                "module_name", "action_name", "description", "created_at",
            },
            {"description"},
        ),
        RolePermission: (
            "role_permissions",
            "role_permission_id",
            {"role_permission_id", "role_id", "permission_id", "is_active", "granted_by", "granted_at"},
            {"granted_by"},
        ),
        AccountPermission: (
            "account_permissions",
            "account_permission_id",
            {
                "account_permission_id", "account_id", "permission_id", "effect",
                "is_active", "assigned_by", "created_at", "updated_at",
            },
            {"assigned_by", "updated_at"},
        ),
        AccessAuditLog: (
            "access_audit_logs",
            "access_audit_log_id",
            {
                "access_audit_log_id", "actor_account_id", "target_account_id", "role_id",
                "permission_id", "action", "old_value", "new_value", "reason", "created_at",
            },
            {"target_account_id", "role_id", "permission_id", "old_value", "new_value", "reason"},
        ),
    }

    def setUp(self):
        super().setUp()
        self.connection = DatabaseWrapper(
            {
                "ENGINE": "django.db.backends.mysql",
                "NAME": "",
                "OPTIONS": {},
                "TIME_ZONE": None,
            },
            alias="offline_remaining_access_control_review",
        )
        self.connection.mysql_is_mariadb = False
        self.ensure_connection = self.enterContext(
            patch.object(
                self.connection,
                "ensure_connection",
                side_effect=AssertionError("Mapping tests cannot connect to a database."),
            )
        )
        self.cursor = self.enterContext(
            patch.object(
                self.connection,
                "cursor",
                side_effect=AssertionError("Mapping tests cannot execute SQL."),
            )
        )
        self.editor = self.connection.schema_editor(collect_sql=True, atomic=False)

    def tearDown(self):
        self.ensure_connection.assert_not_called()
        self.cursor.assert_not_called()
        self.assertIsNone(self.connection.connection)
        super().tearDown()

    def test_table_and_column_sets_have_no_unapproved_persistent_fields(self):
        for model, (table, _key, columns, _nullable) in self.definitions.items():
            with self.subTest(model=model.__name__):
                self.assertEqual(model._meta.db_table, table)
                self.assertEqual({field.column for field in model._meta.local_fields}, columns)
                self.assertEqual(model._meta.local_many_to_many, [])

    def test_primary_keys_are_explicit_32_bit_auto_increment_integers(self):
        for model, (_table, key, _columns, _nullable) in self.definitions.items():
            with self.subTest(model=model.__name__):
                field = model._meta.pk
                self.assertEqual(field.name, key)
                self.assertEqual(field.column, key)
                self.assertIs(type(field), models.AutoField)
                self.assertEqual(field.db_type(self.connection), "integer AUTO_INCREMENT")
                self.assertFalse(field.null)

    def test_nullability_and_optional_form_fields_match_the_erd(self):
        for model, (_table, _key, _columns, nullable) in self.definitions.items():
            with self.subTest(model=model.__name__):
                self.assertEqual(
                    {field.column for field in model._meta.local_fields if field.null}, nullable
                )
                for field in model._meta.local_fields:
                    if not field.primary_key:
                        self.assertEqual(field.blank, field.null, field.name)

    def test_text_lengths_and_individual_uniqueness_match_the_erd(self):
        lengths = {
            Service: {"service_name": 100, "service_code": 100, "description": 255},
            Permission: {
                "permission_code": 150, "permission_name": 100, "module_name": 100,
                "action_name": 50, "description": 255,
            },
            AccessAuditLog: {"action": 50, "reason": 255},
        }
        for model, fields in lengths.items():
            for name, length in fields.items():
                with self.subTest(model=model.__name__, field=name):
                    field = model._meta.get_field(name)
                    self.assertIs(type(field), models.CharField)
                    self.assertEqual(field.max_length, length)
                    self.assertEqual(field.db_type(self.connection), f"varchar({length})")
        for model in self.definitions:
            with self.subTest(model=model.__name__):
                expected = {Service: {"service_name", "service_code"}, Permission: {"permission_code"}}.get(model, set())
                self.assertEqual(
                    {field.name for field in model._meta.local_fields if field.unique and not field.primary_key},
                    expected,
                )

    def test_foreign_keys_use_the_approved_columns_targets_and_protect_policy(self):
        definitions = [
            (Permission, "service", Service, "service_id", False),
            (RolePermission, "role", Role, "role_id", False),
            (RolePermission, "permission", Permission, "permission_id", False),
            (RolePermission, "granted_by", Account, "granted_by", True),
            (AccountPermission, "account", Account, "account_id", False),
            (AccountPermission, "permission", Permission, "permission_id", False),
            (AccountPermission, "assigned_by", Account, "assigned_by", True),
            (AccessAuditLog, "actor_account", Account, "actor_account_id", False),
            (AccessAuditLog, "target_account", Account, "target_account_id", True),
            (AccessAuditLog, "role", Role, "role_id", True),
            (AccessAuditLog, "permission", Permission, "permission_id", True),
        ]
        for model, name, target, column, nullable in definitions:
            with self.subTest(model=model.__name__, field=name):
                field = model._meta.get_field(name)
                self.assertIsInstance(field, models.ForeignKey)
                self.assertIs(field.remote_field.model, target)
                self.assertEqual(field.column, column)
                self.assertIs(field.target_field, target._meta.pk)
                self.assertIs(field.remote_field.on_delete, models.PROTECT)
                self.assertEqual(field.null, nullable)
                self.assertFalse(field.unique)
                self.assertTrue(field.db_constraint)

    def test_reverse_names_distinguish_permission_subjects_from_recorded_actors(self):
        definitions = [
            (Service, "permissions", Permission, "service"),
            (Role, "permission_grants", RolePermission, "role"),
            (Permission, "role_grants", RolePermission, "permission"),
            (Account, "role_permission_grants_made", RolePermission, "granted_by"),
            (Account, "permission_overrides", AccountPermission, "account"),
            (Permission, "account_overrides", AccountPermission, "permission"),
            (Account, "permission_overrides_made", AccountPermission, "assigned_by"),
            (Account, "access_audit_actions", AccessAuditLog, "actor_account"),
            (Account, "access_audit_entries", AccessAuditLog, "target_account"),
            (Role, "access_audit_entries", AccessAuditLog, "role"),
            (Permission, "access_audit_entries", AccessAuditLog, "permission"),
        ]
        for target, accessor, model, field_name in definitions:
            with self.subTest(accessor=f"{target.__name__}.{accessor}"):
                self.assertIs(getattr(target, accessor).rel.field, model._meta.get_field(field_name))

    def test_composite_constraints_are_unconditional_unique_pairs(self):
        definitions = [
            (RolePermission, ("role", "permission"), "role_permissions_role_permission_unique", "role_id"),
            (AccountPermission, ("account", "permission"), "account_permissions_account_permission_unique", "account_id"),
        ]
        for model, fields, name, subject_column in definitions:
            with self.subTest(model=model.__name__):
                self.assertEqual(len(model._meta.constraints), 1)
                constraint = model._meta.constraints[0]
                self.assertIsInstance(constraint, models.UniqueConstraint)
                self.assertEqual(constraint.fields, fields)
                self.assertEqual(constraint.name, name)
                self.assertIsNone(constraint.condition)
                self.assertIn(
                    f"UNIQUE (`{subject_column}`, `permission_id`)",
                    str(constraint.constraint_sql(model, self.editor)),
                )
        for model in (Service, Permission, AccessAuditLog):
            self.assertEqual(model._meta.constraints, [])

    def test_active_flags_have_both_python_and_database_true_defaults(self):
        for model in (Service, RolePermission, AccountPermission):
            with self.subTest(model=model.__name__):
                field = model._meta.get_field("is_active")
                self.assertIs(type(field), models.BooleanField)
                self.assertIs(field.default, True)
                self.assertIs(field.db_default, True)
                self.assertFalse(field.null)
                sql, params = self.editor.column_sql(model, field)
                self.assertEqual(sql, "bool DEFAULT %s NOT NULL")
                self.assertEqual(params, [True])
        self.assertNotIn("is_active", {field.name for field in Permission._meta.local_fields})

    def test_effect_is_a_required_native_enum_with_no_implicit_grant(self):
        field = AccountPermission._meta.get_field("effect")
        self.assertIsInstance(field, MySQLEnumField)
        self.assertEqual(list(field.flatchoices), [("Grant", "Grant"), ("Deny", "Deny")])
        self.assertEqual(field.max_length, 5)
        self.assertFalse(field.null)
        self.assertFalse(field.blank)
        self.assertFalse(field.has_default())
        self.assertFalse(field.has_db_default())
        self.assertNotIn("choices", field.non_db_attrs)
        self.assertEqual(field.db_type(self.connection), "enum('Grant','Deny')")
        sql, params = self.editor.column_sql(AccountPermission, field)
        self.assertEqual(sql, "enum('Grant','Deny') NOT NULL")
        self.assertEqual(params, [])
        with self.assertRaisesMessage(ValidationError, "valid choice"):
            field.clean("Allow", None)

    def test_creation_timestamps_are_native_and_use_only_database_current_time(self):
        definitions = [
            (Permission, "created_at"),
            (RolePermission, "granted_at"),
            (AccountPermission, "created_at"),
            (AccessAuditLog, "created_at"),
        ]
        for model, name in definitions:
            with self.subTest(model=model.__name__, field=name):
                field = model._meta.get_field(name)
                self.assertIsInstance(field, MySQLTimestampField)
                self.assertFalse(field.null)
                self.assertFalse(field.editable)
                self.assertFalse(field.has_default())
                self.assertIsInstance(field.db_default, CurrentTimestamp)
                self.assertFalse(field.auto_now)
                self.assertFalse(field.auto_now_add)
                sql, params = self.editor.column_sql(model, field)
                self.assertEqual(sql, "timestamp DEFAULT (CURRENT_TIMESTAMP) NOT NULL")
                self.assertEqual(params, [])

    def test_updated_at_is_nullable_without_automatic_updates_or_defaults(self):
        field = AccountPermission._meta.get_field("updated_at")
        self.assertIsInstance(field, MySQLTimestampField)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertFalse(field.auto_now)
        self.assertFalse(field.auto_now_add)
        self.assertFalse(field.has_default())
        self.assertFalse(field.has_db_default())
        sql, params = self.editor.column_sql(AccountPermission, field)
        self.assertEqual(sql, "timestamp NULL")
        self.assertEqual(params, [])

    def test_audit_old_and_new_values_are_nullable_native_json_with_no_default_payload(self):
        payload = {"role": "Student", "is_active": False, "permission_codes": ["course.view"]}
        for name in ("old_value", "new_value"):
            with self.subTest(field=name):
                field = AccessAuditLog._meta.get_field(name)
                self.assertIs(type(field), models.JSONField)
                self.assertTrue(field.null)
                self.assertTrue(field.blank)
                self.assertFalse(field.has_default())
                self.assertFalse(field.has_db_default())
                self.assertEqual(field.db_type(self.connection), "json")
                prepared = field.get_db_prep_value(payload, self.connection)
                self.assertEqual(field.from_db_value(prepared, None, self.connection), payload)
                self.assertIsNone(field.from_db_value(None, None, self.connection))

    def test_fields_constraints_and_models_serialize_and_reconstruct_in_memory(self):
        from django.db.migrations.state import ModelState

        for model in self.definitions:
            values = [*model._meta.local_fields, *model._meta.constraints]
            for value in values:
                with self.subTest(model=model.__name__, value=value.name):
                    source, imports = MigrationWriter.serialize(value)
                    namespace = {}
                    for statement in sorted(imports):
                        exec(statement, namespace)
                    reconstructed = eval(source, namespace)
                    self.assertEqual(MigrationWriter.serialize(reconstructed), (source, imports))
            state = ModelState.from_model(model)
            clone = state.clone()
            self.assertEqual(clone, state)
            self.assertEqual(clone.options["db_table"], model._meta.db_table)

    def test_creating_service_and_permission_records_has_no_automatic_assignment_side_effects(self):
        def simulate_save(instance, **kwargs):
            instance.pk = 101
            post_save.send(
                sender=type(instance), instance=instance, created=True, raw=False,
                using=kwargs.get("using") or "default", update_fields=None,
            )

        with (
            patch.object(Service, "save", autospec=True, side_effect=simulate_save),
            patch.object(Permission, "save", autospec=True, side_effect=simulate_save),
            patch.object(RolePermission, "save") as role_permission_save,
            patch.object(AccountPermission, "save") as account_permission_save,
            patch.object(AccountRole, "save") as account_role_save,
            patch.object(AccessAuditLog, "save") as audit_save,
        ):
            service = Service.objects.create(service_name="Academic", service_code="academic")
            Permission.objects.create(
                service=service, permission_code="course.view", permission_name="View course",
                module_name="course", action_name="view",
            )
        role_permission_save.assert_not_called()
        account_permission_save.assert_not_called()
        account_role_save.assert_not_called()
        audit_save.assert_not_called()

    def test_recorded_grants_and_actors_do_not_automatically_authorize_an_account(self):
        actor = Account(account_id=1, school_id="actor")
        subject = Account(account_id=2, school_id="subject")
        permission = Permission(permission_id=3, permission_code="accounts.manage")
        override = AccountPermission(account=subject, permission=permission, effect="Grant", assigned_by=actor)
        grant = RolePermission(role=Role(role_id=4, role_name="Admin"), permission=permission, granted_by=actor)
        self.assertIs(override.assigned_by, actor)
        self.assertIs(grant.granted_by, actor)
        self.assertFalse(subject.has_perm(permission.permission_code))
        self.assertFalse(actor.has_perm(permission.permission_code))
        self.assertFalse(subject.is_staff)
        self.assertFalse(subject.is_superuser)
