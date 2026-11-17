"""G1C planning and disposable test-only contracts. NOT a bootstrap implementation."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from io import StringIO

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, TransactionTestCase

from apps.accounts.models import Account
from apps.access_control.audit import record_access_audit
from apps.access_control.models import AccountPermission, AccountRole, AccessAuditLog, Permission, Role, RolePermission, Service
from apps.access_control.services import has_permission
from apps.access_control.tests_support.g1b_catalogue_test_only import CORE_K_CODES
from apps.access_control.tests_support.technical_super_admin_test_only import composed_profile_test_only
from apps.access_control.tests_support.g1c_evidence_test_only import (
    FictionalApproval, FictionalBundle, FictionalLedgerReceipt, FictionalOperator,
    FictionalRequest, FictionalTicket, PROFILE, POLICY, MANIFEST,
    canonical_request_digest_test_only, effective_operator_ids_test_only,
    floor_transition_issues_test_only, proposed_ledger_conflicts_test_only,
    static_contract_issues_test_only, structural_evidence_issues_test_only,
)

# Strong fail-closed settings and actual schema checks before ANY test fixture writes.
if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("G1C tests require --settings=config.test_settings and a disposable MySQL database.")


class G1CStaticPlanningTests(SimpleTestCase):
    ENV = "test_ctug_registration_0123456789abcdef"
    NOW = datetime(2026, 11, 13, 3, 0, tzinfo=timezone.utc)
    BEFORE = "a" * 64

    def request(self, **changes):
        base = FictionalRequest(
            request_id="G1C-TEST-001", idempotency_key="idempotency_0123456789abcdef",
            operation="first_bootstrap", target_account_id=101,
            environment=self.ENV, before_digest=self.BEFORE,
            proposed_roles=PROFILE, proposed_core_codes=CORE_K_CODES,
            policy_version=POLICY, catalogue_revision=MANIFEST,
        )
        return replace(base, **changes)

    def bundle(self, **changes):
        request = changes.pop("request", self.request())
        digest = canonical_request_digest_test_only(request)
        approvals = (
            FictionalApproval("institutional", 201, digest, "approve"),
            FictionalApproval("technical", 202, digest, "approve"),
        )
        ticket = FictionalTicket(digest, "ticket_nonce_0123456789abcdef", self.NOW - timedelta(minutes=2), self.NOW + timedelta(minutes=10))
        base = FictionalBundle(request, approvals, ticket, 203)
        return replace(base, **changes)

    def issues(self, bundle, **extra):
        context = dict(now=self.NOW, expected_environment=self.ENV, expected_before_digest=self.BEFORE)
        context.update(extra)
        return structural_evidence_issues_test_only(bundle, **context)

    def test_two_application_admin_levels_only(self):
        self.assertEqual(PROFILE, ("Admin", "Technical Super Admin"))

    def test_static_contract_has_no_drift(self):
        self.assertEqual(static_contract_issues_test_only(), ())

    def test_static_management_command_succeeds_without_database(self):
        out = StringIO()
        call_command("report_g1c_bootstrap_static", ack="G1C_STATIC_ONLY", stdout=out)
        self.assertIn("STATIC-ONLY BOOTSTRAP AND EVIDENCE CONTRACT PASSED", out.getvalue())
        self.assertIn("UNIMPLEMENTED", out.getvalue())

    def test_static_command_refuses_wrong_ack(self):
        with self.assertRaises(CommandError):
            call_command("report_g1c_bootstrap_static", ack="LIVE_BOOTSTRAP")

    def test_canonical_fingerprint_is_deterministic(self):
        self.assertEqual(canonical_request_digest_test_only(self.request()), canonical_request_digest_test_only(self.request()))
        self.assertEqual(len(canonical_request_digest_test_only(self.request())), 64)

    def test_fingerprint_changes_for_target(self):
        self.assertNotEqual(canonical_request_digest_test_only(self.request()), canonical_request_digest_test_only(self.request(target_account_id=102)))

    def test_fingerprint_changes_for_state_digest(self):
        self.assertNotEqual(canonical_request_digest_test_only(self.request()), canonical_request_digest_test_only(self.request(before_digest="b" * 64)))

    def test_fingerprint_changes_for_nonce_and_action(self):
        digest = canonical_request_digest_test_only(self.request())
        self.assertNotEqual(digest, canonical_request_digest_test_only(self.request(idempotency_key="othernonce_0123456789abcdef")))
        self.assertNotEqual(digest, canonical_request_digest_test_only(self.request(operation="technical_role_change")))

    def test_request_refuses_real_database(self):
        self.assertIsNone(canonical_request_digest_test_only(self.request(environment="ctug_workspace")))

    def test_request_refuses_invented_or_unapproved_admin_role(self):
        self.assertIsNone(canonical_request_digest_test_only(self.request(proposed_roles=("Admin", "School Super Admin"))))

    def test_request_refuses_changed_core_k(self):
        self.assertIsNone(canonical_request_digest_test_only(self.request(proposed_core_codes=CORE_K_CODES[:-1])))

    def test_request_refuses_unapproved_version(self):
        self.assertIsNone(canonical_request_digest_test_only(self.request(policy_version="G1C-PRODUCTION")))
        self.assertIsNone(canonical_request_digest_test_only(self.request(catalogue_revision="v3")))

    def test_request_refuses_invalid_ids(self):
        self.assertIsNone(canonical_request_digest_test_only(self.request(target_account_id=0)))
        self.assertIsNone(canonical_request_digest_test_only(self.request(target_account_id=True)))

    def test_request_refuses_bad_hash_or_request_id(self):
        self.assertIsNone(canonical_request_digest_test_only(self.request(before_digest="not-a-hash")))
        self.assertIsNone(canonical_request_digest_test_only(self.request(request_id="")))

    def test_fictional_complete_evidence_is_only_structurally_consistent(self):
        # Empty issues is NOT signer verification, authority, or a DB write command.
        self.assertEqual(self.issues(self.bundle()), ())

    def test_bundle_refuses_wrong_object(self):
        self.assertEqual(self.issues(None), ("invalid-bundle",))

    def test_bundle_refuses_wrong_environment(self):
        self.assertIn("wrong-environment", self.issues(self.bundle(), expected_environment="ctug_workspace"))

    def test_bundle_refuses_stale_before_state(self):
        self.assertIn("stale-before-state", self.issues(self.bundle(), expected_before_digest="b" * 64))

    def test_bundle_refuses_self_execution(self):
        self.assertIn("invalid-executor", self.issues(self.bundle(executor_id=101)))

    def test_bundle_refuses_missing_duty(self):
        b = self.bundle()
        self.assertIn("invalid-approvers", self.issues(replace(b, approvals=b.approvals[:1])))

    def test_bundle_refuses_duplicate_duties(self):
        b = self.bundle()
        self.assertIn("invalid-duties", self.issues(replace(b, approvals=(b.approvals[0], b.approvals[0]))))

    def test_bundle_refuses_same_person_as_both_approvers(self):
        b = self.bundle()
        self.assertIn("separation-failed", self.issues(replace(b, approvals=(b.approvals[0], replace(b.approvals[1], claimed_person_id=201)))))

    def test_bundle_refuses_approver_as_executor(self):
        self.assertIn("separation-failed", self.issues(self.bundle(executor_id=201)))

    def test_bundle_refuses_approver_as_beneficiary(self):
        b = self.bundle()
        self.assertIn("separation-failed", self.issues(replace(b, approvals=(replace(b.approvals[0], claimed_person_id=101), b.approvals[1]))))

    def test_bundle_refuses_approval_for_different_request(self):
        b = self.bundle()
        self.assertIn("approval-mismatch", self.issues(replace(b, approvals=(replace(b.approvals[0], request_digest="b" * 64), b.approvals[1]))))

    def test_bundle_refuses_rejection(self):
        b = self.bundle()
        self.assertIn("approval-mismatch", self.issues(replace(b, approvals=(replace(b.approvals[0], decision="reject"), b.approvals[1]))))

    def test_bundle_refuses_ticket_nonce_mismatch(self):
        b = self.bundle()
        self.assertIn("ticket-scope-mismatch", self.issues(replace(b, ticket=replace(b.ticket, nonce="short"))))

    def test_bundle_refuses_ticket_for_old_request(self):
        b = self.bundle()
        self.assertIn("ticket-scope-mismatch", self.issues(replace(b, ticket=replace(b.ticket, request_digest="b" * 64))))

    def test_bundle_refuses_consumed_ticket(self):
        b = self.bundle()
        self.assertIn("ticket-spent", self.issues(replace(b, ticket=replace(b.ticket, consumed=True))))

    def test_bundle_refuses_expired_ticket(self):
        b = self.bundle()
        self.assertIn("ticket-expired-or-invalid", self.issues(replace(b, ticket=replace(b.ticket, expires_at=self.NOW))))

    def test_bundle_refuses_more_than_15_minutes(self):
        b = self.bundle()
        self.assertIn("ticket-expired-or-invalid", self.issues(replace(b, ticket=replace(b.ticket, expires_at=self.NOW + timedelta(hours=1)))))

    def test_bundle_refuses_ticket_not_yet_issued(self):
        b = self.bundle()
        self.assertIn("ticket-expired-or-invalid", self.issues(replace(b, ticket=replace(b.ticket, issued_at=self.NOW + timedelta(minutes=1)))))

    def test_bundle_refuses_naive_time(self):
        self.assertIn("invalid-ticket-time", self.issues(self.bundle(), now=datetime(2026, 11, 13, 3, 0)))

    def test_structural_evidence_cannot_establish_real_signer_identity(self):
        b = self.bundle()
        fake = replace(b, approvals=(replace(b.approvals[0], claimed_person_id=999), b.approvals[1]))
        self.assertEqual(self.issues(fake), ())  # demonstrates unverified identity risk
        self.assertFalse(hasattr(fake, "verified_identity"))

    def test_structural_evidence_does_not_contain_a_signed_attestation(self):
        self.assertFalse(hasattr(self.bundle().approvals[0], "cryptographic_signature"))

    def test_new_receipt_has_no_conflict_on_empty_snapshot(self):
        receipt = FictionalLedgerReceipt("G1C-TEST-001", "idempotency_0123456789abcdef", "ticket_nonce_0123456789abcdef")
        self.assertEqual(proposed_ledger_conflicts_test_only((), receipt), ())

    def test_in_memory_ledger_detects_request_replay(self):
        a = FictionalLedgerReceipt("G1C-TEST-001", "idempotency_0123456789abcdef", "ticket_nonce_0123456789abcdef")
        b = replace(a, idempotency_key="different_0123456789abcdef", nonce="different_nonce_0123456789abcdef")
        self.assertIn("duplicate-request", proposed_ledger_conflicts_test_only((a,), b))

    def test_in_memory_ledger_detects_idempotency_reuse(self):
        a = FictionalLedgerReceipt("G1C-TEST-001", "idempotency_0123456789abcdef", "ticket_nonce_0123456789abcdef")
        b = replace(a, request_id="G1C-TEST-002", nonce="different_nonce_0123456789abcdef")
        self.assertIn("duplicate-idempotency", proposed_ledger_conflicts_test_only((a,), b))

    def test_in_memory_ledger_detects_nonce_replay(self):
        a = FictionalLedgerReceipt("G1C-TEST-001", "idempotency_0123456789abcdef", "ticket_nonce_0123456789abcdef")
        b = replace(a, request_id="G1C-TEST-002", idempotency_key="different_0123456789abcdef")
        self.assertIn("replayed-nonce", proposed_ledger_conflicts_test_only((a,), b))

    def test_snapshot_uniqueness_cannot_stop_concurrent_acceptance(self):
        a = FictionalLedgerReceipt("G1C-TEST-001", "idempotency_0123456789abcdef", "ticket_nonce_0123456789abcdef")
        self.assertEqual(proposed_ledger_conflicts_test_only((), a), ())
        self.assertEqual(proposed_ledger_conflicts_test_only((), a), ())
        # Both stale checks accepted: real DB UNIQUE constraints are mandatory.

    def operator(self, *, account_id=101, approved=True, active=True, roles=None, codes=None, session_usable=True):
        return FictionalOperator(account_id, approved, active, frozenset(PROFILE) if roles is None else roles,
                                 frozenset(CORE_K_CODES) if codes is None else codes, session_usable)

    def test_dual_role_operator_with_usable_session_is_counted(self):
        self.assertEqual(effective_operator_ids_test_only((self.operator(),)), frozenset({101}))

    def test_normal_admin_and_technical_only_are_not_counted(self):
        normal = self.operator(account_id=102, roles=frozenset({"Admin"}))
        tech_only = self.operator(account_id=103, roles=frozenset({"Technical Super Admin"}))
        self.assertEqual(effective_operator_ids_test_only((normal, tech_only)), frozenset())

    def test_session_unusable_removes_operator_from_floor(self):
        self.assertFalse(effective_operator_ids_test_only((self.operator(session_usable=False),)))

    def test_missing_core_code_removes_operator(self):
        self.assertFalse(effective_operator_ids_test_only((self.operator(codes=frozenset(CORE_K_CODES[:-1])),)))

    def test_inactive_or_rejected_operator_is_not_counted(self):
        self.assertFalse(effective_operator_ids_test_only((self.operator(active=False), self.operator(account_id=102, approved=False))))

    def test_routine_last_operator_removal_fails(self):
        self.assertEqual(floor_transition_issues_test_only((self.operator(),), ()), ("operator-floor-lost",))

    def test_routine_two_operator_target_can_be_required(self):
        before = (self.operator(), self.operator(account_id=102))
        after = (self.operator(account_id=102),)
        self.assertEqual(floor_transition_issues_test_only(before, after, minimum_remaining=2), ("operator-floor-lost",))
        self.assertEqual(floor_transition_issues_test_only(before, after, minimum_remaining=1), ())

    def test_bootstrap_zero_to_one_never_authorized_by_floor_preview(self):
        self.assertEqual(floor_transition_issues_test_only((), (self.operator(),), routine=False), ("bootstrap-requires-separate-approval",))

    def test_routine_change_before_bootstrap_fails(self):
        self.assertEqual(floor_transition_issues_test_only((), (self.operator(),)), ("not-bootstrapped",))

    def test_two_stale_readers_can_approve_opposite_removals(self):
        a, b = self.operator(), self.operator(account_id=102)
        self.assertEqual(floor_transition_issues_test_only((a, b), (a,)), ())
        self.assertEqual(floor_transition_issues_test_only((a, b), (b,)), ())
        self.assertEqual(floor_transition_issues_test_only((a, b), ()), ("operator-floor-lost",))


class G1CDisposableMySQLContracts(TestCase):
    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("G1C fixture schema is not the disposable test database.")
        service = Service.objects.create(service_code="access_control", service_name="G1C test-only service")
        perm = Permission.objects.create(service=service, permission_code=CORE_K_CODES[0], permission_name="Fixture catalogue read", module_name="catalogue", action_name="read")
        cls.perm = perm
        cls.admin_role = Role.objects.create(role_name="Admin")
        cls.technical_role = Role.objects.create(role_name="Technical Super Admin")
        RolePermission.objects.create(role=cls.technical_role, permission=perm)

        def account(sid, roles=(), *, framework=False):
            obj = Account(school_id=sid, request_status="Approved", is_active=True, is_superuser=framework, is_staff=framework)
            obj.set_unusable_password()
            obj.save()
            for role in roles:
                AccountRole.objects.create(account=obj, role=role)
            return obj

        cls.dual = account("G1C-DUAL", (cls.admin_role, cls.technical_role))
        cls.normal = account("G1C-NORMAL", (cls.admin_role,))
        cls.tech_only = account("G1C-TECHONLY", (cls.technical_role,))
        cls.framework = account("G1C-FRAMEWORK", framework=True)

    def test_dual_role_requires_exact_permission(self):
        self.assertTrue(composed_profile_test_only(self.dual))
        self.assertTrue(has_permission(self.dual, self.perm.permission_code))
        self.assertFalse(has_permission(self.dual, "access_control.unapproved"))

    def test_normal_admin_cannot_gain_governance_by_role_name(self):
        self.assertFalse(composed_profile_test_only(self.normal))
        self.assertFalse(has_permission(self.normal, self.perm.permission_code))

    def test_technical_only_permission_requires_separate_composition_gate(self):
        self.assertTrue(has_permission(self.tech_only, self.perm.permission_code))
        self.assertFalse(composed_profile_test_only(self.tech_only))

    def test_direct_grant_does_not_complete_admin_profile(self):
        AccountPermission.objects.create(account=self.normal, permission=self.perm, effect="Grant")
        self.assertTrue(has_permission(self.normal, self.perm.permission_code))
        self.assertFalse(composed_profile_test_only(self.normal))

    def test_direct_deny_overrides_dual_role(self):
        AccountPermission.objects.create(account=self.dual, permission=self.perm, effect="Deny")
        self.assertFalse(has_permission(self.dual, self.perm.permission_code))

    def test_django_superuser_flag_does_not_grant_app_authority(self):
        self.assertTrue(self.framework.is_superuser)
        self.assertFalse(composed_profile_test_only(self.framework))
        self.assertFalse(has_permission(self.framework, self.perm.permission_code))

    def test_inactive_service_blocks_governance(self):
        Service.objects.filter(pk=self.perm.service_id).update(is_active=False)
        self.assertFalse(has_permission(self.dual, self.perm.permission_code))

    def test_rolled_back_audit_does_not_persist_receipt(self):
        before = AccessAuditLog.objects.count()
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                record_access_audit(actor=self.dual, action="g1c.test.rollback", reason="assignment_change")
                raise RuntimeError("simulated failure before commit")
        self.assertEqual(AccessAuditLog.objects.count(), before)


class G1CDisposableMySQLTemporaryUniquenessTests(TransactionTestCase):
    """TEMPORARY MySQL table ONLY inside Django's isolated test schema.

    Tests a proposed uniqueness mechanism without creating a canonical model,
    production ledger, migration, or table in the developer's main database.
    """

    def test_disposable_temp_table_rejects_same_request_key_or_nonce(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("G1C temporary ledger fixture refuses non-test schema.")
            cursor.execute("""
                CREATE TEMPORARY TABLE g1c_unique_fixture (
                    request_id VARCHAR(80) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
                    idem_key VARCHAR(80) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
                    nonce VARCHAR(80) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
                    PRIMARY KEY (request_id), UNIQUE KEY uq_idem (idem_key), UNIQUE KEY uq_nonce (nonce)
                ) ENGINE=InnoDB
            """)
            try:
                cursor.execute("INSERT INTO g1c_unique_fixture VALUES (%s, %s, %s)", ("G1C-TEST-001", "idem_1111111111111111", "nonce_1111111111111111"))
                cases = (
                    ("G1C-TEST-001", "idem_2222222222222222", "nonce_2222222222222222"),
                    ("G1C-TEST-002", "idem_1111111111111111", "nonce_2222222222222222"),
                    ("G1C-TEST-002", "idem_2222222222222222", "nonce_1111111111111111"),
                )
                for values in cases:
                    with self.subTest(values=values):
                        with self.assertRaises(IntegrityError):
                            cursor.execute("INSERT INTO g1c_unique_fixture VALUES (%s, %s, %s)", values)
                cursor.execute("SELECT COUNT(*) FROM g1c_unique_fixture")
                self.assertEqual(cursor.fetchone()[0], 1)
            finally:
                cursor.execute("DROP TEMPORARY TABLE IF EXISTS g1c_unique_fixture")
