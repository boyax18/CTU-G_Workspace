"""WF-03.01 D-93/D-95 development-database gate for the protected Django-Superuser procedure (19 Nov 2026).

Run: python manage.py test apps.access_control.test_wf0301_d93_development_gate --settings=config.test_settings --noinput
Disposable MySQL ONLY. The development target is SIMULATED on this run's disposable database by pointing the
gate's DEVELOPMENT_DATABASE constant at it (test-only patch); every other condition is the real check. Nothing
here connects to, reads or writes ctug_workspace, and no MySQL account, grant or trigger is touched.
"""

import contextlib
import os
import tempfile
import threading
import warnings
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError, connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings

from apps.access_control import framework_roles
from apps.access_control.models import Role
from apps.access_control.framework_roles import parse_operator_allowlist
from apps.access_control.role_management import RoleChangeConflict, RoleChangeDenied, RoleChangeUnavailable

from .test_wf0301_role_assignment import PASSWORD, ROOT, URLCONF, World, roles_of, state

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("D-93/D-95 gate tests require --settings=config.test_settings.")

# The development target has NO operator setting (it comes only from the environment): () here.
DEVELOPMENT = dict(DEBUG=True, REGISTRATION_TEST_DATABASE=None, WORKSPACE_ROLE_CONFIGURATION_OPERATORS=(),
                   WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False, WORKSPACE_ROLE_ASSIGNMENT_ENABLED=False,
                   WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=False, WORKSPACE_REGISTRATION_APPROVAL_ENABLED=False,
                   ROOT_URLCONF="config.urls")


class DevelopmentGateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.test_db = settings.REGISTRATION_TEST_DATABASE
        assert cls.test_db != "ctug_workspace"
        cls.w = World()
        cls.instructor = cls.w.account("0093001", "Instructor")
        cls.student = cls.w.account("7393001", "Student")
        cls.pending = cls.w.account("0093002", "Instructor", status="Pending", active=False)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.env_file = Path(directory.name) / ".env"
        self.env_file.write_text("DB_NAME=placeholder\n", encoding="utf-8")  # an .env WITHOUT the allowlist key

    @contextlib.contextmanager
    def development(self, *, database=None, env=None, drop=(), **overrides):
        """The exact development target, simulated on the disposable database; overrides break one condition."""
        environ = {"DJANGO_SETTINGS_MODULE": "config.settings", "WORKSPACE_ROLE_CONFIGURATION_OPERATORS": ROOT,
                   **(env or {})}
        with patch.object(framework_roles, "DEVELOPMENT_DATABASE", database or self.test_db), \
                patch.dict(os.environ, environ), \
                patch.object(framework_roles, "_env_file", return_value=self.env_file), \
                override_settings(**{**DEVELOPMENT, **overrides}):
            for key in drop:
                os.environ.pop(key, None)
            yield

    def configure(self, operation, target, *, operator=ROOT, password=PASSWORD, confirmation=None):
        return framework_roles.configure_role(
            operation=operation, operator_school_id=operator, operator_password=password, target_id=target.pk,
            confirmation=framework_roles.confirmation_for(operation, target.pk) if confirmation is None else confirmation)

    def refused(self, exc_type, operation="grant-technical-super-admin", target=None, **kwargs):
        before = state()
        with self.assertRaises(exc_type) as caught:
            self.configure(operation, target or self.instructor, **kwargs)
        self.assertEqual(state(), before, "a refused call must write nothing")
        return caught.exception

    # -- acceptance ------------------------------------------------------------------------------------------
    def test_the_exact_development_target_runs_the_protected_grant_with_a_database_bound_confirmation(self):
        with self.development():
            confirmation = framework_roles.confirmation_for("grant-technical-super-admin", self.instructor.pk)
            self.assertEqual(confirmation, f"{self.test_db}:WF-03.01:grant-technical-super-admin:{self.instructor.pk}")
            self.refused(RoleChangeUnavailable,
                         confirmation=f"WF-03.01:grant-technical-super-admin:{self.instructor.pk}")  # unbound form
            result = self.configure("grant-technical-super-admin", self.instructor)
        self.assertEqual(result, {"account_id": self.instructor.pk, "operation": "grant-technical-super-admin"})
        self.assertEqual(roles_of(self.instructor), ["Admin", "Instructor", "Technical Super Admin"])
        self.assertEqual(Role.objects.filter(role_name="Technical Super Admin").count(), 1)

    def test_the_real_constants_name_only_ctug_workspace_and_no_bypass_flag_exists(self):
        self.assertEqual(framework_roles.DEVELOPMENT_DATABASE, "ctug_workspace")
        self.assertEqual(framework_roles.DEVELOPMENT_SETTINGS_MODULE, "config.settings")
        self.assertFalse(hasattr(framework_roles, "DEVELOPMENT_DATABASE_APPROVED"))
        self.assertEqual(framework_roles.confirmation_for("grant-school-admin", 5), "WF-03.01:grant-school-admin:5")

    # -- every refusal (default deny) -------------------------------------------------------------------------
    def test_each_unmet_development_condition_refuses_before_any_write(self):
        connection.ensure_connection()
        cases = {
            "settings module": dict(env={"DJANGO_SETTINGS_MODULE": "config.review_local_settings"}),
            "DEBUG off": dict(DEBUG=False),
            "test database configured": dict(REGISTRATION_TEST_DATABASE=self.test_db),
            "database name": dict(database="ctug_workspace"),
            "role-assignment API flag": dict(WORKSPACE_ROLE_ASSIGNMENT_ENABLED=True),
            "review API flag": dict(WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True),
            "approval flag": dict(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True),
            "unexpected URL configuration": dict(ROOT_URLCONF=URLCONF),
            "allowlist missing from the environment": dict(drop=("WORKSPACE_ROLE_CONFIGURATION_OPERATORS",)),
            "allowlist also defined in a settings module": dict(WORKSPACE_ROLE_CONFIGURATION_OPERATORS=(ROOT,)),
            "empty allowlist": dict(env={"WORKSPACE_ROLE_CONFIGURATION_OPERATORS": " "}),
            "malformed allowlist": dict(env={"WORKSPACE_ROLE_CONFIGURATION_OPERATORS": f"{ROOT}, bad id!"}),
            "duplicated allowlist": dict(env={"WORKSPACE_ROLE_CONFIGURATION_OPERATORS": f"{ROOT},{ROOT}"}),
        }
        for label, kwargs in cases.items():
            with self.subTest(condition=label), self.development(**kwargs):
                self.refused(RoleChangeUnavailable)
        with self.subTest(condition="protected writer"), self.development(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):
            self.refused(Exception)  # the gate (or the writer refusal behind it) refuses; nothing is written
        for label, change in (("remote host", {"HOST": "10.0.0.5"}), ("port", {"PORT": "3399"})):
            with self.subTest(condition=label), self.development(), patch.dict(connection.settings_dict, change):
                self.refused(RoleChangeUnavailable)
        with self.subTest(condition="isolation level"), self.development(), \
                patch.object(connection, "isolation_level", "repeatable read"):
            self.refused(RoleChangeUnavailable)
        with self.subTest(condition="extra database alias"), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with self.development(DATABASES={**settings.DATABASES, "other": dict(settings.DATABASES["default"])}):
                self.refused(RoleChangeUnavailable)

    def test_the_allowlist_must_never_come_from_backend_env(self):
        for line in ("WORKSPACE_ROLE_CONFIGURATION_OPERATORS=" + ROOT, "  export WORKSPACE_ROLE_CONFIGURATION_OPERATORS = x"):
            with self.subTest(line=line):
                self.env_file.write_text(f"DB_NAME=placeholder\n{line}\n", encoding="utf-8")
                with self.development():
                    error = self.refused(RoleChangeUnavailable)
                self.assertIn("backend/.env", str(error))

    def test_operator_designation_reauthentication_confirmation_and_eligibility_still_apply(self):
        with self.development(env={"WORKSPACE_ROLE_CONFIGURATION_OPERATORS": "SOMEONE-ELSE"}):
            self.refused(RoleChangeDenied)  # a real superuser that is not designated in the environment
        with self.development():
            self.refused(RoleChangeDenied, password="Wrong!Password000")
            for wrong in (f"{self.test_db}:WF-03.01:grant-technical-super-admin:{self.student.pk}",
                          f"{self.test_db}:WF-03.01:grant-school-admin:{self.instructor.pk}", "", "ctug_workspace"):
                with self.subTest(confirmation=wrong):
                    self.refused(RoleChangeUnavailable, confirmation=wrong)
            self.refused(RoleChangeConflict, target=self.student)  # no Instructor role
            self.refused(RoleChangeDenied, target=self.pending)  # not Approved and active

    def test_the_review_only_command_prints_the_database_bound_confirmation_and_apply_needs_it(self):
        with self.development():
            out = StringIO()
            call_command("configure_workspace_roles", operation="grant-school-admin",
                         target_account_id=self.instructor.pk, stdout=out)
            self.assertIn(f"--confirm {self.test_db}:WF-03.01:grant-school-admin:{self.instructor.pk}", out.getvalue())
            with self.assertRaises(CommandError):
                call_command("configure_workspace_roles", operation="grant-school-admin",
                             target_account_id=self.instructor.pk, apply=True,
                             confirm=f"WF-03.01:grant-school-admin:{self.instructor.pk}", stdout=StringIO())

    def test_role_management_route_detection(self):
        self.assertEqual(framework_roles._mounted_role_management_routes("config.urls"), [])
        self.assertTrue(framework_roles._mounted_role_management_routes(URLCONF))

    def test_operator_allowlist_parser_fails_closed(self):
        self.assertEqual(parse_operator_allowlist("D85-ROOT"), ("D85-ROOT",))
        self.assertEqual(parse_operator_allowlist(" A1 , b.2 "), ("A1", "b.2"))
        for bad in ("", "   ", None, 7, "A1,A1", "A1,", "bad id", "x" * 51, "A1;B2", "-lead"):
            with self.subTest(raw=bad):
                self.assertEqual(parse_operator_allowlist(bad), ())

    # -- bypass resistance -----------------------------------------------------------------------------------
    def test_the_low_level_mutators_refuse_outside_the_protected_procedure(self):
        role = Role.objects.get(role_name="Admin")
        services = {"access_control": None}
        before = state()
        for call in (lambda: framework_roles._add(self.w.root, self.instructor, role),
                     lambda: framework_roles._remove(self.w.root, self.instructor, role, None),
                     lambda: framework_roles._ensure_governance(self.w.root, services)):
            with self.subTest(call=call), self.assertRaises(RoleChangeUnavailable):
                call()
            with self.subTest(call=call, inside="atomic"), self.assertRaises(RoleChangeUnavailable), transaction.atomic():
                call()
        self.assertEqual(state(), before)

    def test_authorization_never_outlives_or_leaks_from_a_successful_call(self):
        with self.development():
            self.configure("grant-school-admin", self.instructor)
        self.assertIsNone(framework_roles._AUTHORIZED.get())
        role = Role.objects.get(role_name="Admin")
        before = state()
        with self.assertRaises(RoleChangeUnavailable), transaction.atomic():
            framework_roles._add(self.w.root, self.student, role)
        self.assertEqual(state(), before)

    def test_the_authorization_is_bound_to_the_operator_and_target_of_the_call(self):
        role = Role.objects.get(role_name="Admin")
        token = framework_roles._AUTHORIZED.set({"operator": self.w.root.pk, "target": self.instructor.pk})
        self.addCleanup(framework_roles._AUTHORIZED.reset, token)
        with self.assertRaises(RoleChangeUnavailable), transaction.atomic():
            framework_roles._add(self.w.root, self.student, role)  # a different target than authorized
        with self.assertRaises(RoleChangeUnavailable), transaction.atomic():
            framework_roles._add(self.instructor, self.instructor, role)  # a different operator
        self.assertEqual(roles_of(self.student), ["Student"])


class ColdConnectionGateTests(TransactionTestCase):
    """Regression (fix of 20 Nov 2026): the gate must work from a NEVER-OPENED connection, as in a fresh
    manage.py process. Each check runs in a worker thread, whose Django connection is new and unconnected (asserted),
    so it lacks connection-dependent state such as isolation_level until the gate establishes it."""

    development = DevelopmentGateTests.development
    configure = DevelopmentGateTests.configure

    def setUp(self):
        self.test_db = settings.REGISTRATION_TEST_DATABASE
        assert self.test_db != "ctug_workspace"
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.env_file = Path(directory.name) / ".env"
        self.env_file.write_text("DB_NAME=placeholder\n", encoding="utf-8")
        self.w = World()
        self.instructor = self.w.account("0093101", "Instructor")

    def tearDown(self):
        connections.close_all()

    def cold(self, fn):
        out = {}

        def target():
            try:
                out["cold_before"] = connection.connection is None and not hasattr(connection, "isolation_level")
                out["value"] = fn()
            except Exception as exc:  # returned to the test
                out["value"] = exc
            finally:
                out["connected_after"] = connection.connection is not None
                connections.close_all()
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(60)
        self.assertFalse(thread.is_alive(), "the worker did not finish")
        self.assertTrue(out["cold_before"], "the worker must start with a never-opened connection")
        return out

    def test_the_gate_establishes_a_cold_connection_and_recognizes_the_development_target(self):
        with self.development():
            out = self.cold(framework_roles._require_approved_target)
        self.assertEqual(out["value"], "development")  # no AttributeError
        self.assertTrue(out["connected_after"])

    def test_the_protected_grant_succeeds_from_a_cold_connection(self):
        with self.development():
            out = self.cold(lambda: self.configure("grant-school-admin", self.instructor))
        self.assertEqual(out["value"], {"account_id": self.instructor.pk, "operation": "grant-school-admin"})
        self.assertEqual(roles_of(self.instructor), ["Admin", "Instructor"])

    def test_cold_refusals_write_nothing_and_a_wrong_target_is_never_connected(self):
        for label, kwargs, connects in (("database name", dict(database="ctug_workspace"), False),
                                        ("DEBUG off", dict(DEBUG=False), False),
                                        ("missing allowlist", dict(drop=("WORKSPACE_ROLE_CONFIGURATION_OPERATORS",)), True),
                                        ("review flag", dict(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True), True)):
            with self.subTest(condition=label):
                before = state()
                with self.development(**kwargs):
                    out = self.cold(lambda: self.configure("grant-technical-super-admin", self.instructor))
                self.assertIsInstance(out["value"], RoleChangeUnavailable)
                self.assertEqual(out["connected_after"], connects)  # configuration refusals connect to nothing
                self.assertEqual(state(), before)

    def test_unauthorized_operator_and_wrong_confirmation_are_refused_from_a_cold_connection(self):
        before = state()
        with self.development(env={"WORKSPACE_ROLE_CONFIGURATION_OPERATORS": "SOMEONE-ELSE"}):
            denied = self.cold(lambda: self.configure("grant-technical-super-admin", self.instructor))
        with self.development():
            wrong = self.cold(lambda: self.configure(
                "grant-technical-super-admin", self.instructor,
                confirmation=f"WF-03.01:grant-technical-super-admin:{self.instructor.pk}"))
        self.assertIsInstance(denied["value"], RoleChangeDenied)
        self.assertIsInstance(wrong["value"], RoleChangeUnavailable)
        self.assertEqual(state(), before)

    def test_a_connection_failure_is_a_fixed_refusal_without_details(self):
        failure = OperationalError(1045, "Access denied for user 'secret-user'@'db-host' (using password: YES)")

        def attempt():
            with patch.object(connection, "ensure_connection", side_effect=failure):
                return framework_roles._require_approved_target()
        with self.development():
            out = self.cold(attempt)
        error = out["value"]
        self.assertIsInstance(error, RoleChangeUnavailable)
        self.assertIn("could not be established", str(error))
        for secret in ("Access denied", "secret-user", "db-host", "password"):
            self.assertNotIn(secret, str(error))
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)  # the driver error is not chained

    def test_the_low_level_mutators_refuse_from_a_cold_connection(self):
        role = Role.objects.get(role_name="Admin")
        before = state()
        out = self.cold(lambda: framework_roles._add(self.w.root, self.instructor, role))
        self.assertIsInstance(out["value"], RoleChangeUnavailable)
        self.assertEqual(state(), before)
