"""Test-only root-bound ledger adapter; isolated disposable MySQL ONLY."""

from dataclasses import replace
from unittest.mock import patch
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import TransactionTestCase

from apps.accounts.models import Account
from apps.access_control.models import AccessAuditLog, AccountRole, Role, Service
from apps.access_control.test_task2_g1d_p1_production_authorization_contract import SyntheticFixture
from apps.access_control.tests_support import g1d_p1_authorization_design_test_only as auth
from apps.access_control.tests_support import g1d_p1_ledger_transaction_test_only as ledger
from apps.access_control.tests_support import g1d_p3a_root_endorsed_registry_test_only as roots
from apps.access_control.tests_support import g1d_p3b_root_bound_executor_test_only as p3b
from apps.access_control.tests_support import g1d_p3b_root_bound_ledger_test_only as adapter

if settings.SETTINGS_MODULE != "config.test_settings" or not auth.SCHEMA.fullmatch(getattr(settings, "REGISTRATION_TEST_DATABASE", "")):
    raise ImproperlyConfigured("G1D-P3B integration requires isolated MySQL test settings")


class RootBoundLedgerContracts(SyntheticFixture, TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        ledger.disposable_only(ledger.ACK)
        admin = Role.objects.create(role_name="Admin", is_active=True)
        for name in ("Student", "Instructor", "Treasurer"):
            Role.objects.create(role_name=name)
        Service.objects.create(service_code="access_control", service_name="Disposable governance")
        self.actor = Account.objects.create(
            school_id="SYNTHETIC-P3B-EXECUTOR", request_status="Approved",
            is_active=True, password="!",
        )
        AccountRole.objects.create(account=self.actor, role=admin)
        self.identities(self.actor.pk)
        self.db = ledger.DisposableLedger(ack=ledger.ACK)
        self.db.create(self.trust)
        self.addCleanup(self.db.drop)
        self.root_private = {duty: Ed25519PrivateKey.generate() for duty in ("institutional_root", "technical_root")}
        self.pins = tuple(roots.RootPin(
            key_id="test_" + duty, person_id=str(uuid4()), duty=duty,
            public_key=key.public_key().public_bytes_raw(),
        ) for duty, key in self.root_private.items())
        manifest = roots.make_unsigned_manifest(self.trust, issued_at=self.NOW - 60, expires_at=self.NOW + 600)
        self.registry = roots.RootEndorsedRegistry(manifest, self.trust, tuple(
            roots.RootEndorsement(pin.key_id, pin.person_id, pin.duty,
                                  self.root_private[pin.duty].sign(roots.DOMAIN + manifest)) for pin in self.pins
        ))

    def stage(self, **changes):
        bundle = self.bundle(before=self.db.before_hash(self.actor.pk))
        req = auth.parse(bundle.request, auth.REQUEST_FIELDS)
        ticket = auth.parse(bundle.ticket.payload, auth.TICKET_FIELDS)
        expected = p3b.IndependentTestExpectation(
            self.trust.schema, self.trust.incarnation, self.trust.epoch,
            auth.digest(roots.roster_bytes(self.trust)), self.actor.pk, self.challenge,
            auth.digest(bundle.request), auth.digest(auth.encode_bundle(bundle)), ticket["nonce"],
            req["before_sha256"], req["backup_sha256"], req["release_sha256"],
        )
        if changes:
            expected = replace(expected, **changes)
        operator = adapter.RootBoundDisposableLedger(
            self.db, registry=self.registry, pinned_roots=self.pins, expected=expected,
        )
        return bundle, operator

    def count_requests(self):
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {ledger.REQUESTS}")
            return cursor.fetchone()[0]

    def admitted_claim(self):
        bundle, operator = self.stage()
        request_id = operator.admit(bundle, now=self.NOW)
        claim = operator.claim(bundle, now=self.NOW)
        return bundle, operator, request_id, claim

    def test_root_bound_commit_is_inactive_and_audited(self):
        bundle, op, request_id, claim = self.admitted_claim()
        role_id, audit_id = op.execute(bundle, claim, clock=lambda: self.NOW, simulate_fenced_writers=True)
        connection.close()
        self.assertEqual(op.reconcile(request_id, now=self.NOW), "COMMITTED")
        self.assertFalse(Role.objects.get(pk=role_id).is_active)
        self.assertEqual(Role.objects.get(pk=role_id).role_name, auth.ROLE_NAME)
        self.assertEqual(AccessAuditLog.objects.get(pk=audit_id).actor_account_id, self.actor.pk)
        self.assertEqual(AccountRole.objects.count(), 1)

    def test_replay_does_not_create_duplicate_audit(self):
        bundle, op, _, claim = self.admitted_claim()
        op.execute(bundle, claim, clock=lambda: self.NOW, simulate_fenced_writers=True)
        with self.assertRaises(ledger.LedgerRefused):
            op.execute(bundle, claim, clock=lambda: self.NOW, simulate_fenced_writers=True)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_claim_single_use_survives_new_connection(self):
        bundle, op, _, _ = self.admitted_claim()
        connection.close()
        with self.assertRaises(ledger.LedgerRefused):
            op.claim(bundle, now=self.NOW)

    def test_independent_release_hash_refuses_before_admission(self):
        bundle, op = self.stage(release_sha256="e" * 64)
        with self.assertRaises(auth.ContractRefused):
            op.admit(bundle, now=self.NOW)
        self.assertEqual(self.count_requests(), 0)

    def test_independent_roster_hash_refuses_before_admission(self):
        bundle, op = self.stage(roster_sha256="e" * 64)
        with self.assertRaises(auth.ContractRefused):
            op.admit(bundle, now=self.NOW)
        self.assertEqual(self.count_requests(), 0)

    def test_forged_root_refuses_before_admission(self):
        bundle, op = self.stage()
        forged = replace(self.registry.endorsements[0], signature=b"\0" * 64)
        op.registry = replace(self.registry, endorsements=(forged, self.registry.endorsements[1]))
        with self.assertRaises(auth.ContractRefused):
            op.admit(bundle, now=self.NOW)
        self.assertEqual(self.count_requests(), 0)

    def test_root_revocation_after_claim_fails_closed(self):
        bundle, op, _, claim = self.admitted_claim()
        op.pinned_roots = (replace(self.pins[0], revoked=True), self.pins[1])
        with self.assertRaises(auth.ContractRefused):
            op.execute(bundle, claim, clock=lambda: self.NOW, simulate_fenced_writers=True)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_ledger_epoch_revocation_after_claim_fails_closed(self):
        bundle, op, _, claim = self.admitted_claim()
        self.db.revoke_epoch_test_fixture(now=self.NOW)
        with self.assertRaises(ledger.LedgerRefused):
            op.execute(bundle, claim, clock=lambda: self.NOW, simulate_fenced_writers=True)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_no_implicit_writer_fence(self):
        bundle, op, _, claim = self.admitted_claim()
        with self.assertRaises(ledger.LedgerRefused):
            op.execute(bundle, claim, clock=lambda: self.NOW)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_executor_deactivation_after_claim_fails_closed(self):
        bundle, op, _, claim = self.admitted_claim()
        Account.objects.filter(pk=self.actor.pk).update(is_active=False)
        with self.assertRaises(ledger.LedgerRefused):
            op.execute(bundle, claim, clock=lambda: self.NOW, simulate_fenced_writers=True)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_ambiguous_commit_reconciles_without_retry(self):
        bundle, op, request_id, claim = self.admitted_claim()
        def lose_ack(stage):
            if stage == "after_commit":
                raise OSError("synthetic acknowledgment lost")
        with patch.object(ledger, "_fault_point", side_effect=lose_ack), self.assertRaises(ledger.ExecutionUnknown):
            op.execute(bundle, claim, clock=lambda: self.NOW, simulate_fenced_writers=True)
        connection.close()
        self.assertEqual(op.reconcile(request_id, now=self.NOW), "COMMITTED")
        self.assertEqual(AccessAuditLog.objects.count(), 1)
