"""AR-3B2B2: isolated MySQL read-only planner safety/regression tests.

Run only with config.test_settings and config.test_runner.IsolatedMySQLRunner.
Never point tests at a development or production database.
"""

from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from unittest.mock import patch

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import Account
from .catalogue.planner import CataloguePlanningError
from .catalogue.planner_v2 import build_plan_v2
from .catalogue.validation_v2 import (
    CatalogueV2ValidationError, PINS, ROOT, read_manifest,
)
from .models import (
    AccessAuditLog, AccountPermission, Permission, Role, RolePermission, Service,
)


class CatalogueV2PlannerTests(TransactionTestCase):
    def setUp(self):
        expected = getattr(settings, "REGISTRATION_TEST_DATABASE", None)
        if not expected:
            raise ImproperlyConfigured("Only isolated MySQL test settings may run these tests.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != expected:
                raise ImproperlyConfigured("Catalogue v2 tests refused a non-disposable database.")
        self.data = read_manifest()

    def service(self, code, **changes):
        candidate = next(row for row in self.data["services"] if row["service_code"] == code)
        fields = {key: candidate[key] for key in ("service_code", "service_name", "description")}
        fields.update(is_active=False, **changes)
        return Service.objects.create(**fields)

    def permission(self, code, service=None, **changes):
        candidate = next(row for row in self.data["permissions"] if row["permission_code"] == code)
        fields = {key: candidate[key] for key in (
            "permission_code", "permission_name", "module_name", "action_name", "description"
        )}
        fields.update(changes)
        return Permission.objects.create(service=service or self.service(candidate["service_code"]), **fields)

    def role(self, name):
        candidate = next(row for row in self.data["roles"] if row["role_name"] == name)
        return Role.objects.create(role_name=name, description=candidate["description"])

    def record(self, plan, kind, key):
        return next(row for row in plan["records"] if row["kind"] == kind and row["key"] == key)

    def snapshot(self):
        models = (Account, Service, Permission, Role, RolePermission, AccountPermission, AccessAuditLog)
        return {model._meta.label: list(model.objects.order_by("pk").values()) for model in models}

    def test_empty_database_is_only_a_proposal(self):
        plan = build_plan_v2()
        self.assertEqual(plan["proposed"], {
            "services": 10, "permissions": 95, "roles": 6,
            "role_bindings": 106, "retired_tombstones": 1,
        })
        self.assertEqual(len(plan["records"]), 217)
        self.assertEqual(plan["database_modifications"], 0)
        self.assertFalse(plan["application_approved"])
        self.assertEqual(self.record(plan, "role", "Technical Super Admin")["classification"], "DEFER")
        self.assertEqual(self.record(plan, "role", "SSG Advisor")["classification"], "DEFER")
        self.assertTrue(all(row["classification"] == "DEFER"
                            for row in plan["records"] if row["kind"] == "role_binding"))

    def test_exact_metadata_and_existing_active_binding_match_without_approval(self):
        service = self.service("accounts")
        permission = self.permission("accounts.profile.self.read", service=service)
        role = self.role("Student")
        RolePermission.objects.create(role=role, permission=permission, is_active=True)
        plan = build_plan_v2()
        self.assertEqual(self.record(plan, "service", "accounts")["classification"], "MATCH")
        self.assertEqual(self.record(plan, "permission", permission.permission_code)["classification"], "MATCH")
        binding = self.record(plan, "role_binding", f"Student -> {permission.permission_code}")
        self.assertEqual(binding["classification"], "MATCH")
        self.assertFalse(binding["application_approved"])

    def test_revised_c1_metadata_requires_explicit_transition(self):
        baseline = json.loads((ROOT / PINS["c1_manifest"][0]).read_text(encoding="utf-8"))
        code = "access_control.technical_accounts.provision"
        original = next(p for p in baseline["permissions"] if p["permission_code"] == code)
        service = self.service("access_control")
        Permission.objects.create(service=service, **{k: original[k] for k in (
            "permission_code", "permission_name", "module_name", "action_name", "description"
        )})
        plan = build_plan_v2()
        result = self.record(plan, "permission", code)
        self.assertEqual(result["classification"], "CONFLICT")
        self.assertEqual(result["origin"], "REVISE")

    def test_inactive_grant_conflicts_and_is_not_reactivated(self):
        service = self.service("academic")
        permission = self.permission("academic.advisees.read", service=service)
        role = self.role("Instructor")
        grant = RolePermission.objects.create(role=role, permission=permission, is_active=False)
        before = self.snapshot()
        plan = build_plan_v2()
        self.assertEqual(self.record(plan, "role_binding", f"Instructor -> {permission.permission_code}")["classification"], "CONFLICT")
        self.assertEqual(before, self.snapshot())
        grant.refresh_from_db()
        self.assertFalse(grant.is_active)

    def test_retired_active_role_grant_is_separate_conflict(self):
        service = self.service("access_control")
        original = self.data["historical_retirements"][0]["original_definition"]
        retired = Permission.objects.create(service=service, **{k: original[k] for k in (
            "permission_code", "permission_name", "module_name", "action_name", "description"
        )})
        RolePermission.objects.create(role=self.role("Student"), permission=retired, is_active=True)
        before = self.snapshot()
        plan = build_plan_v2()
        self.assertEqual(len(plan["retirement_review"]), 1)
        self.assertEqual(plan["retirement_review"][0]["classification"], "CONFLICT")
        self.assertEqual(plan["retirement_review"][0]["active_role_grants"], 1)
        self.assertEqual(before, self.snapshot())

    def test_retired_active_account_override_is_separate_conflict(self):
        service = self.service("access_control")
        original = self.data["historical_retirements"][0]["original_definition"]
        retired = Permission.objects.create(service=service, **{k: original[k] for k in (
            "permission_code", "permission_name", "module_name", "action_name", "description"
        )})
        account = Account(school_id="V2-OVERRIDE", request_status="Approved", is_active=True)
        account.set_unusable_password()
        account.save()
        AccountPermission.objects.create(account=account, permission=retired, effect="Grant")
        plan = build_plan_v2()
        self.assertEqual(plan["retirement_review"][0]["active_account_overrides"], 1)
        self.assertEqual(plan["account_override_review"][0]["classification"], "CONFLICT")
        self.assertNotIn("account_id", plan["account_override_review"][0])

    def test_active_blocked_permission_grant_is_reported_not_removed(self):
        service = self.service("accounts")
        permission = self.permission("accounts.school_accounts.provision", service=service)
        grant = RolePermission.objects.create(role=self.role("Student"), permission=permission)
        plan = build_plan_v2()
        self.assertTrue(any(row["existing_id"] == grant.pk and row["classification"] == "CONFLICT"
                            for row in plan["unexpected"] if row["kind"] == "role_binding"))
        self.assertTrue(RolePermission.objects.filter(pk=grant.pk).exists())

    def test_readonly_replay_produces_identical_json_and_no_writes(self):
        self.role("Student")
        service = self.service("academic")
        self.permission("academic.catalogue.read", service=service)
        before = self.snapshot()
        outputs = []
        with CaptureQueriesContext(connection) as queries:
            for _ in range(2):
                stream = StringIO()
                call_command("plan_permission_catalogue_v2", format="json", stdout=stream)
                outputs.append(json.loads(stream.getvalue()))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(before, self.snapshot())
        self.assertEqual(AccessAuditLog.objects.count(), 0)
        for item in queries.captured_queries:
            self.assertRegex(item["sql"], r"\A(?:SELECT|SET TRANSACTION|START TRANSACTION|ROLLBACK)\b")

    def test_fails_closed_inside_caller_transaction(self):
        with transaction.atomic():
            with self.assertRaisesRegex(CataloguePlanningError, "caller transaction"):
                build_plan_v2()

    def test_validation_failure_cannot_query_database(self):
        with patch("apps.access_control.catalogue.planner_v2.validate_manifest",
                   side_effect=CatalogueV2ValidationError("bad pinned source")):
            with self.assertNumQueries(0), self.assertRaises(CatalogueV2ValidationError):
                build_plan_v2()

    def test_conflict_command_exits_nonzero_after_json_output(self):
        self.service("academic", description="wrong metadata")
        stream = StringIO()
        with self.assertRaises(CommandError) as raised:
            call_command("plan_permission_catalogue_v2", format="json", stdout=stream)
        self.assertEqual(raised.exception.returncode, 2)
        self.assertGreater(json.loads(stream.getvalue())["totals"]["CONFLICT"], 0)

    def test_command_exposes_no_write_options(self):
        for keyword in ("apply", "seed", "activate", "actor_account_id", "database"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                call_command("plan_permission_catalogue_v2", **{keyword: True})
