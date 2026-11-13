"""C2A planning tests. Fixtures are restricted to fresh disposable MySQL."""

from copy import deepcopy
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import re
from unittest.mock import Mock, patch

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, transaction
from django.test import SimpleTestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import Account
from .catalogue import validation
from .catalogue.planner import CataloguePlanningError, build_plan, readonly_snapshot, select_only
from .catalogue.validation import CatalogueValidationError, read_manifest, validate_manifest
from .management.commands.init_system_roles import SYSTEM_ROLES
from .models import AccessAuditLog, AccountPermission, Permission, Role, RolePermission, Service

if not re.fullmatch(r"test_ctug_registration_[0-9a-f]{16}", getattr(settings, "REGISTRATION_TEST_DATABASE", "")):
    raise ImproperlyConfigured("Catalogue tests require the guarded config.test_settings; development fixtures forbidden.")


class ManifestTests(SimpleTestCase):
    def setUp(self):
        self.data = read_manifest()

    def invalid(self, match=None):
        with self.assertRaisesRegex(CatalogueValidationError, match or "."):
            validate_manifest(self.data)

    def test_exact_baseline_and_readiness(self):
        data = validate_manifest().data
        self.assertEqual([len(data[k]) for k in ("services", "permissions", "default_bindings", "roles")], [10, 82, 96, 5])
        self.assertEqual({r: sum(p["readiness"] == r for p in data["permissions"]) for r in "FPB"}, dict(F=9, P=62, B=11))

    def test_manifest_pins_exact_relocated_original_and_unchanged_digest(self):
        expected_source = {
            "path": "docs/implementation/access-control/phase1h-c1-permission-catalogue-governance-proposal.md",
            "sha256": "02eb308db5aff1491ea2d024f5f7f1074125e3a7b9bb02dbd1409f6a6170a99e",
        }
        self.assertEqual(self.data["source"], expected_source)
        source_bytes = (validation.ROOT / expected_source["path"]).read_bytes()
        self.assertEqual(sha256(source_bytes).hexdigest(), expected_source["sha256"])

    def test_validator_reads_only_exact_relocated_source(self):
        with patch("pathlib.Path.read_bytes", autospec=True, side_effect=Path.read_bytes) as read:
            validate_manifest(self.data)
        read.assert_called_once_with(
            validation.ROOT / "docs/implementation/access-control/phase1h-c1-permission-catalogue-governance-proposal.md"
        )

    def test_stale_or_arbitrary_manifest_path_is_rejected_before_source_io(self):
        for source in ("docs/phase1h-c1-permission-catalogue-governance-proposal.md", "docs/replacement.md"):
            with self.subTest(source=source), patch("pathlib.Path.read_bytes") as read:
                self.data["source"]["path"] = source
                self.invalid("Source revision")
                read.assert_not_called()

    def test_validated_result_is_deeply_immutable(self):
        validated = validate_manifest(self.data)
        self.data["services"][0]["service_name"] = "changed"
        self.assertEqual(validated.data["services"][0]["service_name"], "Accounts and Profiles")
        with self.assertRaises(TypeError):
            validated.data["services"][0]["service_name"] = "changed"

    def test_duplicate_services(self):
        self.data["services"].append(deepcopy(self.data["services"][0]))
        self.invalid("duplicate")

    def test_duplicate_permissions(self):
        self.data["permissions"].append(deepcopy(self.data["permissions"][0]))
        self.invalid("duplicate")

    def test_static_equivalent_service_names(self):
        self.data["services"][1]["service_name"] = "Accóunts and Profiles"
        self.invalid("equivalent")

    def test_noncanonical_codes_and_wildcards(self):
        original = deepcopy(self.data)
        for key, field, value in (("services", "service_code", "Academic"), ("permissions", "permission_code", "accounts.*"), ("permissions", "permission_code", "Accounts.profile.read")):
            with self.subTest(value=value):
                self.data = deepcopy(original)
                self.data[key][0][field] = value
                self.invalid("canonical")

    def test_invalid_permission_service(self):
        self.data["permissions"][0]["service_code"] = "missing"
        self.invalid("service")

    def test_invalid_binding_role(self):
        self.data["default_bindings"][0]["role_name"] = "Superuser"
        self.invalid("invalid role")

    def test_invalid_binding_permission(self):
        self.data["default_bindings"][0]["permission_code"] = "missing.permission"
        self.invalid("invalid role/permission")

    def test_all_database_field_lengths(self):
        baseline = deepcopy(self.data)
        for group, limits in (("roles", {"role_name": 50, "description": 255}), ("services", {"service_code": 100, "service_name": 100, "description": 255}), ("permissions", {"permission_code": 150, "permission_name": 100, "module_name": 100, "action_name": 50, "description": 255})):
            for field, limit in limits.items():
                with self.subTest(group=group, field=field):
                    self.data = deepcopy(baseline)
                    self.data[group][0][field] = "x" * (limit + 1)
                    self.invalid("field length")

    def test_invalid_readiness(self):
        self.data["permissions"][0]["readiness"] = "READY"
        self.invalid("readiness")

    def test_blocked_default(self):
        code = next(p["permission_code"] for p in self.data["permissions"] if p["readiness"] == "B")
        self.data["default_bindings"].append(dict(role_name="Admin", permission_code=code))
        self.invalid("Blocked")

    def test_delegation_default(self):
        self.data["default_bindings"].append(dict(role_name="Technical Super Admin", permission_code="access_control.delegate.academic"))
        self.invalid("Delegation permissions")

    def test_technical_role_has_no_business_defaults(self):
        baseline = deepcopy(self.data)
        for service in ("academic", "finance", "clearance", "group_rating", "reports"):
            with self.subTest(service=service):
                self.data = deepcopy(baseline)
                code = next(p["permission_code"] for p in self.data["permissions"] if p["service_code"] == service and p["readiness"] == "P")
                self.data["default_bindings"].append(dict(role_name="Technical Super Admin", permission_code=code))
                self.invalid("business default")

    def test_duplicate_binding(self):
        self.data["default_bindings"].append(deepcopy(self.data["default_bindings"][0]))
        self.invalid("Duplicate role binding")

    def test_same_total_but_changed_matrix_is_rejected(self):
        self.data["default_bindings"][0]["role_name"] = "Instructor"
        self.invalid()

    def test_b2_management_contract(self):
        row = next(p for p in self.data["permissions"] if p["permission_code"] == "access_control.role_permissions.manage")
        row["permission_code"] = "access_control.role_permissions.edit"
        self.invalid()

    def test_delegation_family_contract(self):
        row = next(p for p in self.data["permissions"] if p["permission_code"] == "access_control.delegate.academic")
        row["permission_code"] = "access_control.delegate.accounts"
        self.invalid("family")

    def test_unsafe_cartesian_product(self):
        scope = next(s for s in self.data["delegation_candidates"] if s["service_code"] == "finance")
        scope["role_names"].append("Student")
        self.invalid("Cartesian product")

    def test_reserved_delegation_recipient(self):
        scope = next(s for s in self.data["delegation_candidates"] if s["service_code"] == "announcements")
        scope["role_names"].append("Admin")
        self.invalid("Cartesian product")

    def test_changed_narrow_candidate_even_if_role_is_eligible(self):
        scope = next(s for s in self.data["delegation_candidates"] if s["service_code"] == "academic")
        scope["permission_codes"].remove("academic.advisees.read")
        self.invalid("narrow C1")

    def test_scope_must_remain_off(self):
        self.data["delegation_candidates"][0]["status"] = "ON"
        self.invalid("OFF")

    def test_invalid_scope_permission(self):
        self.data["delegation_candidates"][0]["permission_codes"].append("finance.payments.record")
        self.invalid("delegation permission")

    def test_unsupported_governance_stays_blocked(self):
        self.data["blocked_contracts"][0]["status"] = "RESOLVED"
        self.invalid("blocked")

    def test_missing_policy_markers(self):
        self.data["permissions"][0]["policy_markers"] = []
        self.invalid("policy marker")

    def test_decisions_remain_open(self):
        self.data["decisions"][0]["state"] = "APPROVED"
        self.invalid("Unapproved")

    def test_unknown_decision_reference(self):
        self.data["permissions"][0]["decision_refs"] = ["D99"]
        self.invalid("references")

    def test_no_implicit_superuser_fields(self):
        self.data["roles"][-1]["is_superuser"] = True
        self.invalid("privilege fields")

    def test_proposal_digest_mismatch(self):
        with patch("pathlib.Path.read_bytes", return_value=b"changed source"):
            self.invalid("content digest")

    def test_source_missing(self):
        with patch("pathlib.Path.read_bytes", side_effect=OSError):
            self.invalid("unavailable")

    def test_duplicate_json_keys(self):
        with patch("pathlib.Path.read_text", return_value='{"planning_only":true,"planning_only":false}'):
            with self.assertRaisesRegex(CatalogueValidationError, "duplicate JSON"):
                read_manifest()

    def test_unknown_and_malformed_structures(self):
        baseline = deepcopy(self.data)
        for group, field in (("permissions", "service_code"), ("permissions", "readiness"), ("default_bindings", "role_name"), ("delegation_candidates", "role_names"), ("blocked_contracts", "id")):
            with self.subTest(group=group, field=field):
                self.data = deepcopy(baseline)
                self.data[group][0][field] = {}
                self.invalid()


class PlannerTests(TransactionTestCase):
    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("Refusing catalogue fixtures on a non-disposable database.")
        self.data = read_manifest()

    def service(self, code="academic", **changes):
        proposed = next(s for s in self.data["services"] if s["service_code"] == code)
        fields = {key: proposed[key] for key in ("service_code", "service_name", "description")}
        fields.update(is_active=False, **changes)
        return Service.objects.create(**fields)

    def permission(self, code="academic.catalogue.read", service=None, **changes):
        proposed = next(p for p in self.data["permissions"] if p["permission_code"] == code)
        fields = {key: proposed[key] for key in ("permission_code", "permission_name", "module_name", "action_name", "description")}
        fields.update(changes)
        return Permission.objects.create(service=service or self.service(proposed["service_code"]), **fields)

    def roles(self):
        return {name: Role.objects.create(role_name=name, description=description) for name, description in SYSTEM_ROLES}

    def record(self, report, kind, key):
        return next(r for r in report["records"] if r["kind"] == kind and r["key"] == key)

    def snapshot(self):
        return {model._meta.label: list(model.objects.order_by("pk").values()) for model in apps.get_models()}

    def test_missing_metadata_create_and_grants_defer(self):
        report = build_plan()
        self.assertEqual(report["totals"], dict(CREATE=96, MATCH=0, CONFLICT=0, DEFER=97))
        self.assertEqual(self.record(report, "service", "academic")["classification"], "CREATE")
        self.assertEqual(self.record(report, "permission", "academic.catalogue.read")["classification"], "CREATE")

    def test_four_roles_and_missing_technical_role(self):
        self.roles()
        report = build_plan()
        self.assertEqual(report["totals"], dict(CREATE=92, MATCH=4, CONFLICT=0, DEFER=97))
        self.assertEqual(self.record(report, "role", "Technical Super Admin")["classification"], "DEFER")
        technical = [r for r in report["records"] if r["kind"] == "role_binding" and r["key"].startswith("Technical Super Admin ->")]
        self.assertEqual(len(technical), 8)
        self.assertTrue(all(r["classification"] == "DEFER" for r in technical))
        self.assertIn("FIRST_OPERATOR", {b["id"] for b in report["blocked_dependencies"]})
        self.assertEqual(Role.objects.count(), 4)

    def test_exact_metadata_and_binding_match_preserve_primary_keys(self):
        role = self.roles()["Instructor"]
        service = self.service()
        permission = self.permission(service=service)
        grant = RolePermission.objects.create(role=role, permission=permission)
        report = build_plan()
        for kind, key, pk in (("service", "academic", service.pk), ("permission", permission.permission_code, permission.pk), ("role_binding", f"Instructor -> {permission.permission_code}", grant.pk)):
            with self.subTest(kind=kind):
                row = self.record(report, kind, key)
                self.assertEqual(row["classification"], "MATCH")
                self.assertEqual(row["existing_id"], pk)

    def test_permission_metadata_conflict(self):
        permission = self.permission(description="different")
        report = build_plan()
        self.assertEqual(self.record(report, "permission", permission.permission_code)["classification"], "CONFLICT")
        permission.refresh_from_db()
        self.assertEqual(permission.description, "different")

    def test_wrong_service_relationship_conflict(self):
        permission = self.permission(service=self.service("finance"))
        self.assertEqual(self.record(build_plan(), "permission", permission.permission_code)["classification"], "CONFLICT")

    def test_service_unique_name_conflict(self):
        self.service(service_code="other")
        self.assertEqual(self.record(build_plan(), "service", "academic")["classification"], "CONFLICT")

    def test_active_service_is_protected(self):
        service = self.service()
        Service.objects.filter(pk=service.pk).update(is_active=True)
        self.assertEqual(self.record(build_plan(), "service", "academic")["classification"], "CONFLICT")
        service.refresh_from_db()
        self.assertTrue(service.is_active)

    def test_inactive_role_conflict_no_reactivation(self):
        role = self.roles()["Student"]
        Role.objects.filter(pk=role.pk).update(is_active=False)
        self.assertEqual(self.record(build_plan(), "role", "Student")["classification"], "CONFLICT")
        role.refresh_from_db()
        self.assertFalse(role.is_active)

    def test_inactive_grant_conflict_no_reactivation_or_timestamp_refresh(self):
        role = self.roles()["Instructor"]
        permission = self.permission()
        grant = RolePermission.objects.create(role=role, permission=permission, is_active=False)
        before = self.snapshot()
        report = build_plan()
        self.assertEqual(self.record(report, "role_binding", f"Instructor -> {permission.permission_code}")["classification"], "CONFLICT")
        self.assertEqual(before, self.snapshot())
        grant.refresh_from_db()
        self.assertFalse(grant.is_active)

    def test_mysql_case_equivalent_permission_conflict(self):
        self.permission(permission_code="Academic.Catalogue.Read")
        self.assertEqual(self.record(build_plan(), "permission", "academic.catalogue.read")["classification"], "CONFLICT")

    def test_mysql_accent_equivalent_service_code_conflict(self):
        self.service(service_code="acádémic", service_name="Unrelated unique name")
        self.assertEqual(self.record(build_plan(), "service", "academic")["classification"], "CONFLICT")

    def test_mysql_trailing_space_equivalent_permission_conflict(self):
        self.permission(permission_code="academic.catalogue.read ")
        self.assertEqual(self.record(build_plan(), "permission", "academic.catalogue.read")["classification"], "CONFLICT")

    def test_mysql_accent_equivalent_role_conflict(self):
        Role.objects.create(role_name="Stúdent")
        self.assertEqual(self.record(build_plan(), "role", "Student")["classification"], "CONFLICT")

    def test_reserved_role_format_alias_conflict(self):
        Role.objects.create(role_name="Technical_Super_Admin")
        self.assertEqual(self.record(build_plan(), "role", "Technical Super Admin")["classification"], "CONFLICT")

    def test_unknown_existing_records_and_overrides_preserved(self):
        service = Service.objects.create(service_code="unknown", service_name="Unknown", is_active=False)
        permission = Permission.objects.create(service=service, permission_code="unknown.read", permission_name="Unknown", module_name="unknown", action_name="read")
        role = Role.objects.create(role_name="Other role")
        RolePermission.objects.create(role=role, permission=permission)
        account = Account(school_id="CATALOGUE-OVERRIDE", request_status="Approved", is_active=True)
        account.set_unusable_password()
        account.save()
        AccountPermission.objects.create(account=account, permission=permission, effect="Deny")
        before = self.snapshot()
        report = build_plan()
        self.assertEqual(len(report["unexpected"]), 4)
        self.assertEqual(report["account_override_review"][0]["effect"], "Deny")
        self.assertEqual(report["account_override_review"][0]["count"], 1)
        self.assertNotIn("account_id", report["account_override_review"][0])
        self.assertEqual(before, self.snapshot())

    def test_repeated_command_no_state_changes_or_dml_ddl_audit(self):
        self.roles()
        self.permission()
        before = self.snapshot()
        outputs = []
        with CaptureQueriesContext(connection) as queries:
            for _ in range(2):
                out = StringIO()
                call_command("plan_permission_catalogue", format="json", stdout=out)
                outputs.append(json.loads(out.getvalue()))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0]["database_modifications"], 0)
        for query in queries.captured_queries:
            self.assertRegex(query["sql"], r"\A(?:SELECT|SET TRANSACTION|START TRANSACTION|ROLLBACK)\b")
        self.assertEqual(before, self.snapshot())
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_sql_guard_blocks_all_mutations_before_execution(self):
        execute = Mock()
        for sql in ("INSERT INTO services VALUES (1)", "UPDATE services SET is_active=1", "DELETE FROM services", "CREATE TABLE forbidden (id int)", "ALTER TABLE services ADD forbidden int", "DROP TABLE services", "TRUNCATE services", "REPLACE INTO services VALUES (1)", "SELECT 1; DELETE FROM services", "SELECT 1 INTO OUTFILE 'x'", "SELECT * FROM services FOR UPDATE", "WITH x AS (SELECT 1) DELETE FROM services"):
            with self.subTest(sql=sql), self.assertRaises(CataloguePlanningError):
                select_only(execute, sql, None, False, {})
        execute.assert_not_called()

    def test_mysql_transaction_independently_refuses_dml(self):
        # Bypass only the Python guard in this test, proving MySQL itself refuses
        # a persistent-table write. Fixtures still exist only in disposable DB.
        self.service()
        with patch("apps.access_control.catalogue.planner.select_only", side_effect=lambda execute, sql, params, many, context: execute(sql, params, many, context)):
            with readonly_snapshot():
                with self.assertRaises(DatabaseError):
                    with connection.cursor() as cursor:
                        cursor.execute("UPDATE services SET is_active = 1")
        self.assertFalse(Service.objects.get().is_active)

    def test_caller_transaction_refused(self):
        with transaction.atomic():
            with self.assertRaisesRegex(CataloguePlanningError, "caller transaction"):
                build_plan()

    def test_isolation_restored_after_readonly_transaction(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT @@transaction_isolation")
            before = cursor.fetchone()[0]
        build_plan()
        with connection.cursor() as cursor:
            cursor.execute("SELECT @@transaction_isolation")
            self.assertEqual(cursor.fetchone()[0], before)

    def test_failed_comparison_rolls_back(self):
        with patch("apps.access_control.catalogue.planner._compare", side_effect=DatabaseError("private connection details")):
            with CaptureQueriesContext(connection) as queries:
                with self.assertRaises(DatabaseError):
                    build_plan()
        self.assertTrue(any(q["sql"] == "ROLLBACK" for q in queries.captured_queries))
        self.assertTrue(connection.get_autocommit())

    def test_validation_failure_performs_no_queries(self):
        with patch("apps.access_control.catalogue.planner.validate_manifest", side_effect=CatalogueValidationError("invalid baseline")):
            with self.assertNumQueries(0), self.assertRaises(CatalogueValidationError):
                build_plan()

    def test_command_validation_failure_and_connection_error_safe(self):
        for error in (CatalogueValidationError("invalid baseline"), DatabaseError("secret-password"), CataloguePlanningError("unsupported engine")):
            with self.subTest(error=type(error).__name__), patch("apps.access_control.management.commands.plan_permission_catalogue.build_plan", side_effect=error):
                out = StringIO()
                with self.assertRaises(CommandError) as caught:
                    call_command("plan_permission_catalogue", stdout=out)
                self.assertNotIn("secret-password", str(caught.exception))
                self.assertEqual(out.getvalue(), "")

    def test_command_conflicts_exit_nonzero_after_structured_report(self):
        self.permission(description="conflicting definition")
        out = StringIO()
        with self.assertRaises(CommandError) as caught:
            call_command("plan_permission_catalogue", format="json", stdout=out)
        self.assertEqual(caught.exception.returncode, 2)
        self.assertGreater(json.loads(out.getvalue())["totals"]["CONFLICT"], 0)

    def test_command_has_no_apply_seed_or_database_override(self):
        for option in ("apply", "seed", "activate", "database", "actor_account_id"):
            with self.subTest(option=option), self.assertNumQueries(0), self.assertRaises(TypeError):
                call_command("plan_permission_catalogue", **{option: True})

    def test_text_output_and_open_policies(self):
        self.roles()
        out = StringIO()
        call_command("plan_permission_catalogue", stdout=out)
        text = out.getvalue()
        self.assertIn("MODE: READ-ONLY PLANNING", text)
        self.assertIn("96 proposed, NOT approved for application", text)
        self.assertIn("DEFER role Technical Super Admin", text)
        self.assertIn("Technical Super Admin -> access_control.role_permissions.manage", text)
        self.assertIn("OPEN D18", text)
        self.assertIn("BLOCKED G8", text)
        self.assertIn("No DML, DDL or audit writes", text)
