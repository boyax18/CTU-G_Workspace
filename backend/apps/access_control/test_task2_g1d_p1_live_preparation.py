"""G1D-P1 live PREPARATION contracts; all INSERTS use disposable test MySQL.

No real role creation is authorized. Tested HMACs are synthetic proof shapes,
not verified independent institutional authority or a durable ticket ledger.
"""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.test import SimpleTestCase, TestCase, override_settings

from apps.accounts.models import Account
from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission,
)
from apps.access_control.tests_support.g1d_p1_signed_evidence_test_only import (
    ACTION, POLICY, ROLE_DESCRIPTION, ROLE_NAME, FictionalRoleRequest,
    FictionalSignedApproval, FictionalIndependentEvidence,
    canonical_request_sha256, fictional_approval_signature,
    fictional_independent_approval_issues,
)
from apps.access_control.tests_support.g1d_p1_provisioning_transaction_test_only import (
    P1TestOnlyRefused, create_dormant_role_and_audit_test_only,
    current_pre_state_sha256_test_only,
)


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("G1D-P1 preparation tests require --settings=config.test_settings.")


class P1EvidenceFixture:
    NOW = datetime(2026, 11, 13, 2, 0, tzinfo=timezone.utc)
    KEYS = {"institution_a": ("institutional", 101, b"F" * 32),
            "custodian_b": ("technical", 102, b"G" * 32)}

    def request(self, *, actor_id=1, **changes):
        base = FictionalRoleRequest(
            operation=ACTION,
            target_schema=settings.REGISTRATION_TEST_DATABASE,
            executor_account_id=actor_id,
            role_name=ROLE_NAME, description=ROLE_DESCRIPTION, is_active=False,
            backup_sha256="a" * 64, before_sha256="b" * 64,
            ticket_nonce="nonce_0123456789abcdef",
            issued_at=self.NOW - timedelta(minutes=2),
            expires_at=self.NOW + timedelta(minutes=10),
            policy=POLICY,
        )
        return replace(base, **changes)

    def signed(self, req, signer_id):
        duty, signer_account_id, key = self.KEYS[signer_id]
        digest = canonical_request_sha256(req)
        return FictionalSignedApproval(
            duty=duty, signer_id=signer_id, signer_account_id=signer_account_id,
            request_sha256=digest,
            signature_hex=fictional_approval_signature(
                digest, duty=duty, signer_id=signer_id,
                signer_account_id=signer_account_id, test_key=key,
            ),
        )

    def evidence(self, *, actor_id=1, request=None):
        req = request if request is not None else self.request(actor_id=actor_id)
        return FictionalIndependentEvidence(
            req, (self.signed(req, "institution_a"), self.signed(req, "custodian_b")),
        )

    def issues(self, evidence, *, actor_id=1, **changes):
        params = dict(
            now=self.NOW, expected_schema=settings.REGISTRATION_TEST_DATABASE,
            expected_executor_id=actor_id, trusted_test_signers=self.KEYS,
        )
        params.update(changes)
        return fictional_independent_approval_issues(evidence, **params)


class P1StaticEvidenceTests(P1EvidenceFixture, SimpleTestCase):
    def test_exact_two_admin_levels_not_three(self):
        self.assertEqual(ROLE_NAME, "Technical Super Admin")

    def test_fixture_valid_structure_does_not_grant_live_authorization(self):
        self.assertEqual(self.issues(self.evidence()), ())

    def test_request_digest_is_stable(self):
        self.assertEqual(canonical_request_sha256(self.request()), canonical_request_sha256(self.request()))

    def test_fingerprint_changes_with_actor(self):
        self.assertNotEqual(canonical_request_sha256(self.request()), canonical_request_sha256(self.request(actor_id=2)))

    def test_fingerprint_changes_with_backup(self):
        self.assertNotEqual(canonical_request_sha256(self.request()), canonical_request_sha256(self.request(backup_sha256="c" * 64)))

    def test_fingerprint_changes_with_before_state(self):
        self.assertNotEqual(canonical_request_sha256(self.request()), canonical_request_sha256(self.request(before_sha256="c" * 64)))

    def test_fingerprint_changes_with_nonce(self):
        self.assertNotEqual(canonical_request_sha256(self.request()), canonical_request_sha256(self.request(ticket_nonce="different_nonce_0123456789")))

    def test_bad_role_name_refused(self):
        self.assertIsNone(canonical_request_sha256(self.request(role_name="Super Admin")))

    def test_active_role_refused(self):
        self.assertIsNone(canonical_request_sha256(self.request(is_active=True)))

    def test_other_description_refused(self):
        self.assertIsNone(canonical_request_sha256(self.request(description="Give all grants")))

    def test_real_database_refused(self):
        self.assertIsNone(canonical_request_sha256(self.request(target_schema="ctug_workspace")))

    def test_wrong_backup_hash_refused(self):
        self.assertIsNone(canonical_request_sha256(self.request(backup_sha256="bad")))

    def test_wrong_policy_refused(self):
        self.assertIsNone(canonical_request_sha256(self.request(policy="LIVE")))

    def test_overlong_ticket_refused(self):
        self.assertIsNone(canonical_request_sha256(self.request(expires_at=self.NOW + timedelta(hours=1))))

    def test_future_ticket_refused(self):
        self.assertIn("expired-or-invalid-ticket", self.issues(self.evidence(), now=self.NOW - timedelta(minutes=5)))

    def test_expired_ticket_refused(self):
        self.assertIn("expired-or-invalid-ticket", self.issues(self.evidence(), now=self.NOW + timedelta(minutes=10)))

    def test_wrong_executor_refused(self):
        self.assertIn("wrong-executor", self.issues(self.evidence(), actor_id=55))

    def test_wrong_schema_refused(self):
        self.assertIn("wrong-schema", self.issues(self.evidence(), expected_schema="ctug_workspace"))

    def test_wrong_signature_refused(self):
        b = self.evidence()
        tampered = replace(b.approvals[0], signature_hex="f" * 64)
        self.assertIn("bad-test-signature", self.issues(replace(b, approvals=(tampered, b.approvals[1]))))

    def test_wrong_signing_key_refused(self):
        changed = dict(self.KEYS)
        changed["institution_a"] = ("institutional", 101, b"Z" * 32)
        self.assertIn("bad-test-signature", self.issues(self.evidence(), trusted_test_signers=changed))

    def test_approval_for_other_request_refused(self):
        b = self.evidence()
        wrong = replace(b.approvals[0], request_sha256="e" * 64)
        self.assertIn("approval-invalid", self.issues(replace(b, approvals=(wrong, b.approvals[1]))))

    def test_rejection_refused(self):
        b = self.evidence()
        self.assertIn("approval-invalid", self.issues(replace(b, approvals=(replace(b.approvals[0], decision="reject"), b.approvals[1]))))

    def test_missing_technical_approver_refused(self):
        b = self.evidence()
        self.assertIn("incorrect-approval-set", self.issues(replace(b, approvals=(b.approvals[0],))))

    def test_duplicate_duty_refused(self):
        b = self.evidence()
        self.assertIn("incorrect-duties", self.issues(replace(b, approvals=(b.approvals[0], b.approvals[0]))))

    def test_same_signer_person_refused(self):
        b = self.evidence()
        forged = replace(b.approvals[1], signer_account_id=101)
        self.assertIn("separation-failed", self.issues(replace(b, approvals=(b.approvals[0], forged))))

    def test_signer_is_executor_refused(self):
        b = self.evidence()
        forged = replace(b.approvals[0], signer_account_id=b.request.executor_account_id)
        self.assertIn("separation-failed", self.issues(replace(b, approvals=(forged, b.approvals[1]))))

    def test_untrusted_signer_refused(self):
        self.assertIn("untrusted-signer", self.issues(self.evidence(), trusted_test_signers={}))

    def test_no_trust_registry_refused(self):
        self.assertIn("missing-test-trust-registry", self.issues(self.evidence(), trusted_test_signers=None))

    def test_live_apply_command_always_refuses(self):
        with self.assertRaises(CommandError):
            call_command(
                "prepare_g1d_p1_protected_role", expected_db="ctug_workspace",
                ack="G1D_P1_PREPARATION_ONLY", apply=True,
            )

    def test_command_refuses_real_preview_under_disposable_settings(self):
        with self.assertRaises(CommandError):
            call_command(
                "prepare_g1d_p1_protected_role", expected_db="ctug_workspace",
                ack="G1D_P1_PREPARATION_ONLY",
            )

    def test_helper_refuses_wrong_ack_before_database(self):
        with self.assertRaises(P1TestOnlyRefused):
            create_dormant_role_and_audit_test_only(
                actor=None, evidence=None, trusted_test_signers=None, ack="LIVE",
            )


class P1DisposableMySQLTests(P1EvidenceFixture, TestCase):
    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("P1 tests refuse writes outside generated test schema.")
        cls.admin_role = Role.objects.create(role_name="Admin", is_active=True)
        cls.student_role = Role.objects.create(role_name="Student", is_active=True)
        cls.instructor_role = Role.objects.create(role_name="Instructor", is_active=True)
        cls.treasurer_role = Role.objects.create(role_name="Treasurer", is_active=True)

        def account(label, *, status="Approved", active=True, superuser=False):
            obj = Account(
                school_id=label, request_status=status, is_active=active,
                is_staff=superuser, is_superuser=superuser,
            )
            obj.set_unusable_password()
            obj.save()
            return obj

        cls.actor = account("G1D-P1-LIVE-PREP-EXECUTOR")
        AccountRole.objects.create(account=cls.actor, role=cls.admin_role)
        cls.outsider = account("G1D-P1-LIVE-PREP-OUTSIDER", superuser=True)

    def execute(self, *, actor=None, evidence=None, ack="G1D_P1_ATOMIC_DISPOSABLE_ONLY", **extras):
        a = self.actor if actor is None else actor
        if evidence is None:
            before = current_pre_state_sha256_test_only(executor_account_id=a.pk)
            req = self.request(actor_id=a.pk, before_sha256=before)
            e = self.evidence(request=req)
        else:
            e = evidence
        return create_dormant_role_and_audit_test_only(
            actor=a, evidence=e, trusted_test_signers=self.KEYS,
            ack=ack, now=self.NOW, **extras,
        )

    def test_missing_approval_refuses_without_writing(self):
        with self.assertRaises(P1TestOnlyRefused):
            self.execute(evidence="no-approval")
        self.assertFalse(Role.objects.filter(role_name=ROLE_NAME).exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_bad_institutional_fixture_signature_refuses_without_writing(self):
        before = current_pre_state_sha256_test_only(executor_account_id=self.actor.pk)
        bundle = self.evidence(request=self.request(actor_id=self.actor.pk, before_sha256=before))
        forged = replace(bundle.approvals[0], signature_hex="0" * 64)
        with self.assertRaises(P1TestOnlyRefused):
            self.execute(evidence=replace(bundle, approvals=(forged, bundle.approvals[1])))
        self.assertFalse(Role.objects.filter(role_name=ROLE_NAME).exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_exact_one_role_and_one_audit_atomic_receipt(self):
        prior_roles = Role.objects.count()
        prior_audits = AccessAuditLog.objects.count()
        receipt = self.execute()
        role = Role.objects.get(pk=receipt.role_id)
        audit = AccessAuditLog.objects.get(pk=receipt.audit_id)
        self.assertEqual(Role.objects.count(), prior_roles + 1)
        self.assertEqual(AccessAuditLog.objects.count(), prior_audits + 1)
        self.assertEqual(role.role_name, ROLE_NAME)
        self.assertEqual(role.description, ROLE_DESCRIPTION)
        self.assertFalse(role.is_active)
        self.assertEqual(audit.actor_account_id, self.actor.pk)
        self.assertEqual(audit.role_id, role.pk)
        self.assertEqual(audit.action, "technical_admin.role_metadata.create")
        self.assertEqual(audit.new_value, {"role_id": role.pk, "is_active": False})

    def test_no_account_assignments_or_grants(self):
        receipt = self.execute()
        self.assertFalse(AccountRole.objects.filter(role_id=receipt.role_id).exists())
        self.assertFalse(RolePermission.objects.filter(role_id=receipt.role_id).exists())
        self.assertFalse(Permission.objects.exists())
        self.assertFalse(AccountPermission.objects.exists())

    def test_second_execution_is_refused_not_upserted(self):
        self.execute()
        with self.assertRaises(P1TestOnlyRefused):
            self.execute()
        self.assertEqual(Role.objects.filter(role_name=ROLE_NAME).count(), 1)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_existing_alias_is_refused(self):
        Role.objects.create(role_name="Super Admin", is_active=False)
        with self.assertRaises(P1TestOnlyRefused):
            self.execute()
        self.assertFalse(Role.objects.filter(role_name=ROLE_NAME).exists())

    def test_inactive_admin_baseline_is_refused(self):
        Role.objects.filter(pk=self.admin_role.pk).update(is_active=False)
        with self.assertRaises(P1TestOnlyRefused):
            self.execute()

    def test_wrong_executor_is_refused(self):
        with self.assertRaises(P1TestOnlyRefused):
            self.execute(actor=self.outsider)
        self.assertFalse(Role.objects.filter(role_name=ROLE_NAME).exists())

    def test_inactive_actor_refused(self):
        Account.objects.filter(pk=self.actor.pk).update(is_active=False)
        with self.assertRaises(P1TestOnlyRefused):
            self.execute()

    def test_unapproved_actor_refused(self):
        Account.objects.filter(pk=self.actor.pk).update(request_status="Pending")
        with self.assertRaises(P1TestOnlyRefused):
            self.execute()

    def test_wrong_signed_actor_refused(self):
        bad = self.evidence(actor_id=self.outsider.pk)
        with self.assertRaises(P1TestOnlyRefused):
            self.execute(evidence=bad)

    def test_expired_fictional_ticket_refused(self):
        bad = self.evidence(request=self.request(actor_id=self.actor.pk,
            issued_at=self.NOW - timedelta(minutes=14), expires_at=self.NOW - timedelta(minutes=1)))
        with self.assertRaises(P1TestOnlyRefused):
            self.execute(evidence=bad)

    def test_audit_exception_rolls_back_role(self):
        prior = AccessAuditLog.objects.count()
        with patch(
            "apps.access_control.tests_support.g1d_p1_provisioning_transaction_test_only.record_access_audit_receipt",
            side_effect=RuntimeError("simulated audit storage failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.execute()
        self.assertFalse(Role.objects.filter(role_name=ROLE_NAME).exists())
        self.assertEqual(AccessAuditLog.objects.count(), prior)

    def test_bad_receipt_validation_rolls_back_role_and_audit(self):
        prior = AccessAuditLog.objects.count()

        def insert_then_return_invalid_receipt(**kwargs):
            audit_id = record_access_audit_receipt(**kwargs)
            self.assertTrue(AccessAuditLog.objects.filter(pk=audit_id).exists())
            return -1

        # Verify rollback after a real audit INSERT, not only a mocked receipt.
        with patch(
            "apps.access_control.tests_support.g1d_p1_provisioning_transaction_test_only.record_access_audit_receipt",
            side_effect=insert_then_return_invalid_receipt,
        ):
            with self.assertRaises(P1TestOnlyRefused):
                self.execute()
        self.assertFalse(Role.objects.filter(role_name=ROLE_NAME).exists())
        self.assertEqual(AccessAuditLog.objects.count(), prior)

    def test_nested_transaction_refused_before_role_or_audit_write(self):
        # A receipt must not escape an ordinary caller-owned uncommitted block.
        with transaction.atomic():
            with self.assertRaises(RuntimeError):
                self.execute()
        self.assertFalse(Role.objects.filter(role_name=ROLE_NAME).exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_wrong_live_schema_label_is_refused(self):
        with override_settings(REGISTRATION_TEST_DATABASE="ctug_workspace"):
            with self.assertRaises(P1TestOnlyRefused):
                self.execute()
        self.assertFalse(Role.objects.filter(role_name=ROLE_NAME).exists())

    def test_stale_catalogue_refuses_role_creation(self):
        from apps.access_control.models import Service
        service = Service.objects.create(service_code="access_control", service_name="Test governance")
        Permission.objects.create(
            service=service, permission_code="access_control.catalogue.read",
            permission_name="test", module_name="catalogue", action_name="read",
        )
        with self.assertRaises(P1TestOnlyRefused):
            self.execute()

    def test_existing_active_governance_override_refuses(self):
        from apps.access_control.models import Service
        service = Service.objects.create(service_code="access_control", service_name="Test governance")
        perm = Permission.objects.create(
            service=service, permission_code="access_control.test.privilege",
            permission_name="test", module_name="test", action_name="privilege",
        )
        AccountPermission.objects.create(account=self.actor, permission=perm,
            effect="Grant", is_active=True)
        with self.assertRaises(P1TestOnlyRefused):
            self.execute()

    def test_stale_before_state_refuses_without_role_or_audit(self):
        before = current_pre_state_sha256_test_only(executor_account_id=self.actor.pk)
        evidence = self.evidence(request=self.request(
            actor_id=self.actor.pk, before_sha256=before
        ))
        Role.objects.create(role_name="NewTestRole", is_active=True)
        with self.assertRaises(P1TestOnlyRefused):
            self.execute(evidence=evidence)
        self.assertFalse(Role.objects.filter(role_name=ROLE_NAME).exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_no_framework_superuser_bypass(self):
        self.assertTrue(self.outsider.is_superuser)
        self.assertFalse(AccountRole.objects.filter(account=self.outsider, role=self.admin_role).exists())
        with self.assertRaises(P1TestOnlyRefused):
            self.execute(actor=self.outsider)

    def test_no_grants_or_accounts_created_by_our_service(self):
        before_accounts = Account.objects.count()
        before_assignments = AccountRole.objects.count()
        before_grants = RolePermission.objects.count()
        self.execute()
        self.assertEqual(Account.objects.count(), before_accounts)
        self.assertEqual(AccountRole.objects.count(), before_assignments)
        self.assertEqual(RolePermission.objects.count(), before_grants)
