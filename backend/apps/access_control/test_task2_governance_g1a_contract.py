"""G1-G5 read-only/test-only contract checks. Never run with real DB settings."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase

from apps.accounts.models import Account
from apps.access_control.models import (
    AccountPermission, AccountRole, Permission, Role, RolePermission, Service,
)
from apps.access_control.services import has_permission
from apps.access_control.tests_support.governance_g1a_test_only import (
    SimulatedApprovalEvidence,
    eligible_core_operator_ids_test_only,
    evidence_matches_test_only,
    preserves_operator_floor_test_only,
    protected_action_preview_test_only,
)


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured(
        "G1A security tests refuse every non-disposable database. Use --settings=config.test_settings."
    )


class G0IsolationTests(SimpleTestCase):
    def test_readonly_inventory_refuses_disposable_test_settings(self):
        with self.assertRaises(CommandError):
            call_command(
                "report_technical_governance_g0",
                expected_db="ctug_workspace", ack="READ_ONLY_G0",
            )

    def test_test_helper_exposes_no_operational_write_methods(self):
        import apps.access_control.tests_support.governance_g1a_test_only as helper
        for name in ("bootstrap", "promote", "revoke", "assign_role", "grant_permission", "apply", "save", "consume"):
            self.assertFalse(hasattr(helper, name))


class G1AGovernanceContractTests(TestCase):
    """Only disposable MySQL roles/accounts created in test setup, never main DB."""

    CORE = (
        "access_control.catalogue.read",
        "access_control.admin_assignments.manage",
    )
    NOW = datetime(2026, 11, 12, 13, 0, tzinfo=timezone.utc)
    DIGEST = "a" * 64
    POLICY = "G1-G5-DRAFT-2026-11-12"
    ACTION = "assign_technical_role"

    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("G1A fixture destination differs from disposable MySQL schema.")

        cls.service = Service.objects.create(
            service_code="access_control", service_name="G1A fixture governance",
        )
        cls.permission_read = Permission.objects.create(
            service=cls.service, permission_code=cls.CORE[0],
            permission_name="G1A catalogue read", module_name="access_control", action_name="read",
        )
        cls.permission_assign = Permission.objects.create(
            service=cls.service, permission_code=cls.CORE[1],
            permission_name="G1A assignment manage", module_name="access_control", action_name="manage",
        )
        cls.admin_role = Role.objects.create(role_name="Admin")
        cls.technical_role = Role.objects.create(role_name="Technical Super Admin")
        RolePermission.objects.create(role=cls.technical_role, permission=cls.permission_read)
        RolePermission.objects.create(role=cls.technical_role, permission=cls.permission_assign)

        def make_account(school_id, roles=(), framework=False):
            account = Account(
                school_id=school_id, request_status="Approved", is_active=True,
                is_superuser=framework, is_staff=framework,
            )
            account.set_unusable_password()
            account.save()
            for role in roles:
                AccountRole.objects.create(account=account, role=role)
            return account

        cls.operator_1 = make_account("G1A-DUAL-1", (cls.admin_role, cls.technical_role))
        cls.operator_2 = make_account("G1A-DUAL-2", (cls.admin_role, cls.technical_role))
        cls.normal_admin = make_account("G1A-NORMAL", (cls.admin_role,))
        cls.technical_only = make_account("G1A-TECH-ONLY", (cls.technical_role,))
        cls.framework_superuser = make_account("G1A-FRAMEWORK", framework=True)
        cls.target = make_account("G1A-TARGET")

    def evidence(self, **changes):
        fixture = SimulatedApprovalEvidence(
            request_id="G1A-FICTIONAL-001",
            action=self.ACTION,
            target_account_id=self.target.pk,
            before_digest=self.DIGEST,
            policy_version=self.POLICY,
            institutional_approver_id=991,
            technical_custodian_id=992,
            executor_id=self.operator_1.pk,
            issued_at=self.NOW - timedelta(minutes=1),
            expires_at=self.NOW + timedelta(minutes=10),
        )
        return replace(fixture, **changes)

    def check_evidence(self, fixture, **overrides):
        expected = dict(
            action=self.ACTION,
            target_account_id=self.target.pk,
            before_digest=self.DIGEST,
            policy_version=self.POLICY,
            now=self.NOW,
        )
        expected.update(overrides)
        return evidence_matches_test_only(fixture, **expected)

    def operators(self, core=None):
        accounts = (
            self.operator_1, self.operator_2, self.normal_admin,
            self.technical_only, self.framework_superuser,
        )
        return eligible_core_operator_ids_test_only(accounts, core or self.CORE)

    def test_complete_dual_role_and_core_permissions_are_required(self):
        self.assertEqual(self.operators(), frozenset((self.operator_1.pk, self.operator_2.pk)))

    def test_technical_only_holds_code_but_cannot_be_effective_operator(self):
        self.assertTrue(has_permission(self.technical_only, self.permission_assign.permission_code))
        self.assertNotIn(self.technical_only.pk, self.operators())

    def test_normal_admin_and_framework_superuser_are_not_effective_technical_operators(self):
        self.assertNotIn(self.normal_admin.pk, self.operators())
        self.assertNotIn(self.framework_superuser.pk, self.operators())

    def test_deny_override_removes_effective_operator(self):
        AccountPermission.objects.create(
            account=self.operator_1, permission=self.permission_assign, effect="Deny",
        )
        self.assertEqual(self.operators(), frozenset((self.operator_2.pk,)))

    def test_inactive_technical_role_removes_every_eligible_operator(self):
        Role.objects.filter(pk=self.technical_role.pk).update(is_active=False)
        self.assertEqual(self.operators(), frozenset())

    def test_inactive_governance_service_removes_every_effective_operator(self):
        Service.objects.filter(pk=self.service.pk).update(is_active=False)
        self.assertEqual(self.operators(), frozenset())

    def test_inactive_or_rejected_account_fails_core_operator_check(self):
        Account.objects.filter(pk=self.operator_1.pk).update(is_active=False)
        Account.objects.filter(pk=self.operator_2.pk).update(request_status="Rejected")
        self.assertEqual(self.operators(), frozenset())

    def test_missing_core_code_fails_closed(self):
        self.assertEqual(
            self.operators(self.CORE + ("access_control.unapproved.permission",)), frozenset()
        )

    def test_empty_or_non_governance_core_is_not_an_authority(self):
        self.assertEqual(eligible_core_operator_ids_test_only((self.operator_1,), ()), frozenset())
        self.assertEqual(eligible_core_operator_ids_test_only((self.operator_1,), ("other.read",)), frozenset())

    def test_simulated_independent_current_exact_approval_matches(self):
        self.assertTrue(self.check_evidence(self.evidence()))

    def test_simulated_evidence_expires_and_single_use_fixture_fails(self):
        self.assertFalse(self.check_evidence(self.evidence(expires_at=self.NOW)))
        self.assertFalse(self.check_evidence(self.evidence(consumed=True)))

    def test_simulated_evidence_rejects_future_issuance_and_overlong_validity(self):
        self.assertFalse(self.check_evidence(self.evidence(issued_at=self.NOW + timedelta(minutes=1))))
        self.assertFalse(self.check_evidence(self.evidence(expires_at=self.NOW + timedelta(days=1))))

    def test_simulated_evidence_does_not_cross_target_or_action(self):
        fixture = self.evidence()
        self.assertFalse(self.check_evidence(fixture, target_account_id=self.normal_admin.pk))
        self.assertFalse(self.check_evidence(fixture, action="revoke_technical_role"))

    def test_simulated_evidence_rejects_stale_before_digest_and_policy(self):
        fixture = self.evidence()
        self.assertFalse(self.check_evidence(fixture, before_digest="b" * 64))
        self.assertFalse(self.check_evidence(fixture, policy_version="UNAPPROVED"))
        self.assertFalse(self.check_evidence(fixture, before_digest="short"))

    def test_simulated_evidence_requires_two_distinct_external_reviewers(self):
        self.assertFalse(self.check_evidence(self.evidence(technical_custodian_id=991)))
        self.assertFalse(self.check_evidence(self.evidence(institutional_approver_id=self.target.pk)))
        self.assertFalse(self.check_evidence(self.evidence(technical_custodian_id=self.operator_1.pk)))

    def test_invalid_or_missing_evidence_does_not_match(self):
        self.assertFalse(self.check_evidence(None))
        self.assertFalse(self.check_evidence(self.evidence(request_id="")))
        self.assertFalse(self.check_evidence(self.evidence(before_digest="A" * 64)))

    def test_simulated_protected_preview_accepts_complete_fixture_without_writing(self):
        before = self.operators()
        self.assertTrue(protected_action_preview_test_only(
            self.operator_1, action_permission=self.permission_assign.permission_code,
            target_account_id=self.target.pk, evidence=self.evidence(),
            action=self.ACTION, before_digest=self.DIGEST,
            policy_version=self.POLICY, now=self.NOW,
        ))
        self.assertEqual(self.operators(), before)
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())

    def test_preview_denies_normal_admin_technical_only_and_framework_superuser(self):
        for actor in (self.normal_admin, self.technical_only, self.framework_superuser):
            self.assertFalse(protected_action_preview_test_only(
                actor, action_permission=self.permission_assign.permission_code,
                target_account_id=self.target.pk, evidence=self.evidence(),
                action=self.ACTION, before_digest=self.DIGEST,
                policy_version=self.POLICY, now=self.NOW,
            ))

    def test_preview_denies_self_target_and_mismatched_executor(self):
        self.assertFalse(protected_action_preview_test_only(
            self.operator_1, action_permission=self.permission_assign.permission_code,
            target_account_id=self.operator_1.pk, evidence=self.evidence(),
            action=self.ACTION, before_digest=self.DIGEST,
            policy_version=self.POLICY, now=self.NOW,
        ))
        self.assertFalse(protected_action_preview_test_only(
            self.operator_2, action_permission=self.permission_assign.permission_code,
            target_account_id=self.target.pk, evidence=self.evidence(),
            action=self.ACTION, before_digest=self.DIGEST,
            policy_version=self.POLICY, now=self.NOW,
        ))

    def test_preview_denies_active_account_override(self):
        AccountPermission.objects.create(
            account=self.operator_1, permission=self.permission_assign, effect="Deny",
        )
        self.assertFalse(protected_action_preview_test_only(
            self.operator_1, action_permission=self.permission_assign.permission_code,
            target_account_id=self.target.pk, evidence=self.evidence(),
            action=self.ACTION, before_digest=self.DIGEST,
            policy_version=self.POLICY, now=self.NOW,
        ))

    def test_last_effective_operator_must_survive_simulated_mutation(self):
        before = frozenset((self.operator_1.pk,))
        self.assertFalse(preserves_operator_floor_test_only(before, frozenset()))
        self.assertTrue(preserves_operator_floor_test_only(before, before))

    def test_recommended_two_operator_floor_blocks_routine_single_remaining(self):
        before = frozenset((self.operator_1.pk, self.operator_2.pk))
        after = frozenset((self.operator_2.pk,))
        self.assertFalse(preserves_operator_floor_test_only(before, after, minimum_remaining=2))
        self.assertTrue(preserves_operator_floor_test_only(before, after, minimum_remaining=1))

    def test_unbootstrapped_empty_state_cannot_be_called_routine_revocation(self):
        self.assertFalse(preserves_operator_floor_test_only(frozenset(), frozenset()))
        self.assertFalse(preserves_operator_floor_test_only(frozenset(), frozenset((9,))))

    def test_two_independent_stale_views_are_not_real_concurrency_protection(self):
        before = frozenset((self.operator_1.pk, self.operator_2.pk))
        # Both independent un-locked snapshots would separately allow removal
        # of a different operator at floor=1. We assert this documented risk;
        # execution therefore MUST wait for the separately approved lock design.
        self.assertTrue(preserves_operator_floor_test_only(
            before, frozenset((self.operator_1.pk,)), minimum_remaining=1
        ))
        self.assertTrue(preserves_operator_floor_test_only(
            before, frozenset((self.operator_2.pk,)), minimum_remaining=1
        ))
        self.assertFalse(preserves_operator_floor_test_only(before, frozenset()))
