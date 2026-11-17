"""G1B test-only catalogue/bootstrap contracts. Run ONLY with config.test_settings."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from io import StringIO

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase

from apps.accounts.models import Account
from apps.access_control.delegation import is_governance_permission, is_reserved_role
from apps.access_control.models import (
    AccountPermission, AccountRole, Permission, Role, RolePermission, Service,
)
from apps.access_control.services import has_permission
from apps.access_control.tests_support.technical_super_admin_test_only import (
    composed_profile_test_only, simulated_governance_boundary_test_only,
)
from apps.access_control.tests_support.g1b_catalogue_test_only import (
    CORE_K_CODES, CORE_K_DEFINITIONS, EXCLUDED_CORE_CODES, RETIRED_CODE,
    SimulatedBootstrapBlueprint, bootstrap_blueprint_matches_test_only,
    load_pinned_proposal_test_only, validate_catalogue_subset_test_only,
)


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured(
        "G1B tests require --settings=config.test_settings and disposable MySQL."
    )


class G1BStaticCatalogueContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.source = load_pinned_proposal_test_only()

    def report(self, manifest=None):
        return validate_catalogue_subset_test_only(self.source if manifest is None else manifest)

    def test_existing_pinned_v2_contract_is_exact(self):
        self.assertEqual(self.report(), ())

    def test_only_six_core_k_codes(self):
        self.assertEqual(len(CORE_K_CODES), 6)
        self.assertEqual(len(set(CORE_K_CODES)), 6)

    def test_definitions_stay_governance_scoped(self):
        definitions = [p for p in self.source["permissions"] if p["permission_code"] in CORE_K_CODES]
        self.assertEqual(len(definitions), 6)
        self.assertTrue(all(p["scope"] == "GOV" and p["grant_protection"] == "GOV" for p in definitions))

    def test_two_manage_codes_are_not_blanket_protected_grants(self):
        manage = [p for p in self.source["permissions"] if p["permission_code"] in (
            "access_control.role_permissions.manage", "access_control.account_permissions.manage",
        )]
        self.assertEqual(len(manage), 2)
        self.assertTrue(all("only with separate approved service delegation" in p["description"] for p in manage))

    def test_six_planned_bindings_only_to_technical_role(self):
        bindings = [(b["role_name"], b["permission_code"]) for b in self.source["default_bindings"]]
        for code in CORE_K_CODES:
            self.assertEqual([b for b in bindings if b[1] == code], [("Technical Super Admin", code)])

    def test_optional_diagnostics_not_core(self):
        self.assertNotIn("access_control.diagnostics.read", CORE_K_CODES)
        self.assertTrue(set(CORE_K_CODES).isdisjoint(EXCLUDED_CORE_CODES))

    def test_retired_identifier_is_not_selectable(self):
        self.assertNotIn(RETIRED_CODE, [p["permission_code"] for p in self.source["permissions"]])
        self.assertNotIn(RETIRED_CODE, [b["permission_code"] for b in self.source["default_bindings"]])

    def test_invalid_manifest_is_rejected(self):
        self.assertIn("invalid-manifest", self.report([]))

    def test_non_planning_manifest_is_rejected(self):
        draft = deepcopy(self.source)
        draft["planning_only"] = False
        self.assertIn("manifest-header-mismatch", self.report(draft))

    def test_version_drift_is_rejected(self):
        draft = deepcopy(self.source)
        draft["source_revision"] = "unapproved-next"
        self.assertIn("manifest-header-mismatch", self.report(draft))

    def test_missing_core_definition_is_rejected(self):
        draft = deepcopy(self.source)
        draft["permissions"] = [p for p in draft["permissions"] if p["permission_code"] != CORE_K_CODES[0]]
        self.assertIn("core-code-collision-or-missing", self.report(draft))

    def test_case_collation_variant_is_rejected(self):
        draft = deepcopy(self.source)
        alias = deepcopy(next(p for p in draft["permissions"] if p["permission_code"] == CORE_K_CODES[0]))
        alias["permission_code"] = alias["permission_code"].upper()
        draft["permissions"].append(alias)
        self.assertIn("core-code-collision-or-missing", self.report(draft))

    def test_format_alias_is_rejected(self):
        draft = deepcopy(self.source)
        alias = deepcopy(next(p for p in draft["permissions"] if p["permission_code"] == CORE_K_CODES[0]))
        alias["permission_code"] = alias["permission_code"].replace(".", "_")
        draft["permissions"].append(alias)
        self.assertIn("core-code-collision-or-missing", self.report(draft))

    def test_wrong_service_is_rejected(self):
        draft = deepcopy(self.source)
        entry = next(p for p in draft["permissions"] if p["permission_code"] == CORE_K_CODES[0])
        entry["service_code"] = "accounts"
        self.assertIn("core-metadata-mismatch", self.report(draft))

    def test_wrong_module_or_action_is_rejected(self):
        draft = deepcopy(self.source)
        entry = next(p for p in draft["permissions"] if p["permission_code"] == CORE_K_CODES[0])
        entry["action_name"] = "manage"
        self.assertIn("core-metadata-mismatch", self.report(draft))

    def test_description_change_is_rejected(self):
        draft = deepcopy(self.source)
        entry = next(p for p in draft["permissions"] if p["permission_code"] == CORE_K_CODES[0])
        entry["description"] = "Unrestricted access"
        self.assertIn("core-metadata-mismatch", self.report(draft))

    def test_readiness_change_is_rejected(self):
        draft = deepcopy(self.source)
        entry = next(p for p in draft["permissions"] if p["permission_code"] == CORE_K_CODES[0])
        entry["readiness"] = "ACTIVE"
        self.assertIn("core-metadata-mismatch", self.report(draft))

    def test_admin_core_default_is_rejected(self):
        draft = deepcopy(self.source)
        draft["default_bindings"].append({"role_name": "Admin", "permission_code": CORE_K_CODES[0]})
        self.assertIn("core-default-binding-mismatch", self.report(draft))

    def test_missing_technical_default_is_rejected(self):
        draft = deepcopy(self.source)
        draft["default_bindings"] = [b for b in draft["default_bindings"] if b["permission_code"] != CORE_K_CODES[0]]
        self.assertIn("core-default-binding-mismatch", self.report(draft))

    def test_blocked_default_is_rejected(self):
        for blocked_code in ("access_control.governance_grants.manage", "ACCESS_CONTROL.GOVERNANCE_GRANTS.MANAGE"):
            draft = deepcopy(self.source)
            draft["default_bindings"].append({"role_name": "Technical Super Admin", "permission_code": blocked_code})
            self.assertIn("blocked-default-binding", self.report(draft))

    def test_retired_permission_cannot_be_reintroduced(self):
        draft = deepcopy(self.source)
        draft["permissions"].append({"permission_code": RETIRED_CODE})
        self.assertIn("retired-code-selectable", self.report(draft))

    def test_reserved_role_spelling_alias_rejected(self):
        draft = deepcopy(self.source)
        draft["roles"].append({"role_name": "Technical-Super-Admin"})
        self.assertIn("protected-role-name-mismatch", self.report(draft))

    def test_invalid_sections_fail_closed(self):
        draft = deepcopy(self.source)
        draft["permissions"] = None
        self.assertIn("invalid-sections", self.report(draft))

    def test_static_report_command_success_without_database(self):
        out = StringIO()
        call_command("report_g1b_catalogue_static", ack="STATIC_G1B_ONLY", stdout=out)
        self.assertIn("STATIC-ONLY CATALOGUE CONTRACT PASSED", out.getvalue())
        self.assertIn("No metadata installation", out.getvalue())

    def test_static_report_requires_acknowledgement(self):
        with self.assertRaises(CommandError):
            call_command("report_g1b_catalogue_static", ack="UNAPPROVED")

    def test_helpers_expose_no_privileged_write_entrypoints(self):
        import apps.access_control.tests_support.g1b_catalogue_test_only as helper
        for method in ("bootstrap", "promote", "grant", "seed", "migrate", "activate", "save", "revoke", "consume"):
            self.assertFalse(hasattr(helper, method))


class G1BBootstrapBlueprintTests(SimpleTestCase):
    NOW = datetime(2026, 11, 13, 0, 0, tzinfo=timezone.utc)
    POLICY = "G1B-PLANNING-V1"
    DIGEST = "a" * 64

    def blueprint(self, **overrides):
        props = {
            "beneficiary_id": 101,
            "beneficiary_approved_active_admin": True,
            "institutional_approver_id": 201,
            "technical_custodian_id": 202,
            "executor_id": 203,
            "target_database": settings.REGISTRATION_TEST_DATABASE,
            "policy_version": self.POLICY,
            "proposed_roles": ("Admin", "Technical Super Admin"),
            "proposed_governance_codes": CORE_K_CODES,
            "before_digest": self.DIGEST,
            "request_id": "G1B-FICTIONAL-001",
            "issued_at": self.NOW - timedelta(minutes=1),
            "expires_at": self.NOW + timedelta(minutes=10),
            "existing_technical_operator_count": 0,
            "consumed": False,
        }
        props.update(overrides)
        return SimulatedBootstrapBlueprint(**props)

    def accepted(self, request, **overrides):
        context = dict(now=self.NOW, test_database=settings.REGISTRATION_TEST_DATABASE,
                       before_digest=self.DIGEST, policy_version=self.POLICY)
        context.update(overrides)
        return bootstrap_blueprint_matches_test_only(request, **context)

    def test_complete_fictional_blueprint_matches(self):
        self.assertTrue(self.accepted(self.blueprint()))

    def test_main_database_never_matches_simulation(self):
        self.assertFalse(self.accepted(self.blueprint(target_database="ctug_workspace")))

    def test_beneficiary_requires_explicit_approved_active_admin_assertion(self):
        self.assertFalse(self.accepted(self.blueprint(beneficiary_approved_active_admin=False)))

    def test_self_approval_is_rejected(self):
        self.assertFalse(self.accepted(self.blueprint(institutional_approver_id=101)))

    def test_reviewers_and_executor_must_be_distinct(self):
        self.assertFalse(self.accepted(self.blueprint(technical_custodian_id=201)))
        self.assertFalse(self.accepted(self.blueprint(executor_id=201)))

    def test_repeat_bootstrap_rejected(self):
        self.assertFalse(self.accepted(self.blueprint(existing_technical_operator_count=1)))

    def test_consumed_or_expired_request_rejected(self):
        self.assertFalse(self.accepted(self.blueprint(consumed=True)))
        self.assertFalse(self.accepted(self.blueprint(expires_at=self.NOW)))

    def test_stale_digest_rejected(self):
        self.assertFalse(self.accepted(self.blueprint(), before_digest="b" * 64))

    def test_wrong_permission_delta_rejected(self):
        self.assertFalse(self.accepted(self.blueprint(proposed_governance_codes=CORE_K_CODES[:-1])))

    def test_wrong_role_delta_rejected(self):
        self.assertFalse(self.accepted(self.blueprint(proposed_roles=("Technical Super Admin",))))

    def test_unapproved_policy_revision_rejected(self):
        self.assertFalse(self.accepted(self.blueprint(policy_version="UNREVIEWED")))

    def test_overlong_validity_rejected(self):
        self.assertFalse(self.accepted(self.blueprint(expires_at=self.NOW + timedelta(hours=1))))

    def test_future_issuance_rejected(self):
        self.assertFalse(self.accepted(self.blueprint(issued_at=self.NOW + timedelta(seconds=1))))

    def test_wrong_type_rejected(self):
        self.assertFalse(self.accepted(None))
        self.assertFalse(self.accepted(self.blueprint(beneficiary_id="101")))


class G1BDisposableMySQLPermissionsTests(TestCase):
    """All fixture rows are created in and deleted with the isolated test schema."""

    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("G1B fixtures refuse non-disposable MySQL databases.")
        service = Service.objects.create(service_code="access_control", service_name="G1B fixture only")
        cls.permissions = tuple(Permission.objects.create(
            service=service, permission_code=code, permission_name=name,
            module_name=module, action_name=action, description=description,
        ) for code, name, module, action, description, readiness, origin in CORE_K_DEFINITIONS)
        cls.admin = Role.objects.create(role_name="Admin")
        cls.technical = Role.objects.create(role_name="Technical Super Admin")
        cls.student = Role.objects.create(role_name="Student")
        for perm in cls.permissions:
            RolePermission.objects.create(role=cls.technical, permission=perm)

        def account(school_id, roles=(), *, framework=False):
            user = Account(school_id=school_id, request_status="Approved", is_active=True,
                           is_superuser=framework, is_staff=framework)
            user.set_unusable_password()
            user.save()
            for role in roles:
                AccountRole.objects.create(account=user, role=role)
            return user

        cls.dual = account("G1B-DUAL", (cls.admin, cls.technical))
        cls.normal = account("G1B-ADMIN", (cls.admin,))
        cls.tech_only = account("G1B-TECH-ONLY", (cls.technical,))
        cls.student_user = account("G1B-STUDENT", (cls.student,))
        cls.framework = account("G1B-FRAMEWORK", framework=True)

    def test_dual_profile_holds_only_explicit_six_k_permissions(self):
        self.assertTrue(composed_profile_test_only(self.dual))
        self.assertTrue(all(has_permission(self.dual, code) for code in CORE_K_CODES))
        self.assertFalse(has_permission(self.dual, "access_control.governance_grants.manage"))

    def test_normal_admin_student_and_framework_superuser_do_not_gain_core_k(self):
        for actor in (self.normal, self.student_user, self.framework):
            self.assertFalse(composed_profile_test_only(actor))
            self.assertFalse(any(has_permission(actor, code) for code in CORE_K_CODES))

    def test_technical_only_has_evaluator_permissions_but_not_complete_governance_profile(self):
        self.assertTrue(has_permission(self.tech_only, CORE_K_CODES[0]))
        self.assertFalse(composed_profile_test_only(self.tech_only))
        self.assertFalse(simulated_governance_boundary_test_only(self.tech_only, CORE_K_CODES[0]))

    def test_direct_grant_cannot_replace_missing_technical_role(self):
        AccountPermission.objects.create(account=self.normal, permission=self.permissions[0], effect="Grant")
        self.assertTrue(has_permission(self.normal, CORE_K_CODES[0]))
        self.assertFalse(composed_profile_test_only(self.normal))
        self.assertFalse(simulated_governance_boundary_test_only(self.normal, CORE_K_CODES[0]))

    def test_direct_deny_overrides_technical_role_grant(self):
        AccountPermission.objects.create(account=self.dual, permission=self.permissions[0], effect="Deny")
        self.assertFalse(has_permission(self.dual, CORE_K_CODES[0]))
        self.assertFalse(simulated_governance_boundary_test_only(self.dual, CORE_K_CODES[0]))

    def test_inactive_service_denies_all_core_codes(self):
        Service.objects.filter(pk=self.permissions[0].service_id).update(is_active=False)
        self.assertFalse(any(has_permission(self.dual, code) for code in CORE_K_CODES))

    def test_ordinary_delegation_marks_technical_roles_and_permissions_protected(self):
        self.assertTrue(is_reserved_role("Technical Super Admin"))
        self.assertTrue(is_reserved_role("Admin"))
        self.assertTrue(all(is_governance_permission(p) for p in self.permissions))

    def test_pending_account_cannot_pass_composite_governance(self):
        Account.objects.filter(pk=self.dual.pk).update(request_status="Pending", is_active=False)
        self.assertFalse(composed_profile_test_only(self.dual))
        self.assertFalse(has_permission(self.dual, CORE_K_CODES[0]))
