"""Approved D1-D6 synthetic/disposable prototype. D7 NEVER authorized here."""

from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import secrets
from threading import Barrier, Event, Lock
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, IntegrityError, OperationalError, connection, connections, transaction
from django.test import SimpleTestCase, TransactionTestCase, override_settings

from apps.accounts.models import Account
from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.tests_support import g1d_p1_authorization_design_test_only as auth
from apps.access_control.tests_support import g1d_p1_ledger_transaction_test_only as ledger


if settings.SETTINGS_MODULE != "config.test_settings" or not auth.SCHEMA.fullmatch(getattr(settings, "REGISTRATION_TEST_DATABASE", "")):
    raise ImproperlyConfigured("D1-D6 prototype tests require exact disposable MySQL settings.")


class SyntheticFixture:
    NOW = 1_794_535_200

    def identities(self, actor_id):
        self.private = {duty: Ed25519PrivateKey.generate() for duty in ("institutional", "technical", "executor", "issuer")}
        identities = tuple(auth.TestPublicIdentity(
            "test_" + duty, str(uuid4()), duty, key.public_key().public_bytes_raw(),
            account_id=actor_id if duty == "executor" else 0,
        ) for duty, key in self.private.items())
        self.trust = auth.SyntheticTrust(settings.REGISTRATION_TEST_DATABASE, str(uuid4()), 1, identities)
        self.actor_id = actor_id
        self.challenge = secrets.token_hex(32)

    def identity(self, duty):
        return next(i for i in self.trust.identities if i.duty == duty)

    def sign(self, duty, purpose, payload):
        body = auth.canonical(payload)
        return auth.SignedTestProof(body, self.private[duty].sign(auth.signature_message(purpose, body)))

    def bundle(self, *, before="b" * 64, request_changes=None, approval_changes=None, ticket_changes=None, executor_changes=None):
        executor = self.identity("executor")
        request = dict(request_id=str(uuid4()), idempotency_key=secrets.token_hex(32), operation=auth.ACTION,
            role_name=auth.ROLE_NAME, description=auth.ROLE_DESCRIPTION, is_active=False,
            target_schema=self.trust.schema, environment=auth.ENVIRONMENT, incarnation=self.trust.incarnation,
            policy=auth.POLICY, executor_account_id=self.actor_id, executor_person=executor.person_id,
            executor_key=executor.key_id, trust_epoch=self.trust.epoch, before_sha256=before,
            backup_sha256="a" * 64, release_sha256="c" * 64, issued_at=self.NOW - 5, expires_at=self.NOW + 600)
        request.update(request_changes or {})
        body = auth.canonical(request)
        request_hash = auth.digest(body)
        approvals = []
        for duty in ("institutional", "technical"):
            identity = self.identity(duty)
            payload = dict(approval_id=str(uuid4()), key_id=identity.key_id, person_id=identity.person_id,
                duty=duty, request_sha256=request_hash, decision="approve", trust_epoch=self.trust.epoch,
                issued_at=self.NOW - 3, expires_at=self.NOW + 600)
            payload.update((approval_changes or {}).get(duty, {}))
            approvals.append(self.sign(duty, "approval", payload))
        issuer = self.identity("issuer")
        ticket = dict(key_id=issuer.key_id, person_id=issuer.person_id, request_sha256=request_hash,
            institutional_sha256=auth.proof_digest(approvals[0]), technical_sha256=auth.proof_digest(approvals[1]),
            nonce=secrets.token_hex(32), executor_account_id=self.actor_id, release_sha256=request["release_sha256"],
            trust_epoch=self.trust.epoch, issued_at=self.NOW - 2, expires_at=self.NOW + 120)
        ticket.update(ticket_changes or {})
        proof = dict(key_id=executor.key_id, person_id=executor.person_id, request_sha256=request_hash,
            nonce=ticket["nonce"], executor_account_id=self.actor_id, release_sha256=request["release_sha256"],
            challenge=self.challenge, trust_epoch=self.trust.epoch, issued_at=self.NOW - 1, expires_at=self.NOW + 60)
        proof.update(executor_changes or {})
        return auth.SyntheticBundle(body, tuple(approvals), self.sign("issuer", "ticket", ticket), self.sign("executor", "executor", proof))

    def verify(self, bundle, **changes):
        params = dict(now=self.NOW, expected_actor_id=self.actor_id, expected_challenge=self.challenge)
        params.update(changes)
        return auth.verify_bundle(bundle, self.trust, **params)

    def cancellation(self, bundle, duty="institutional", now=None):
        now = self.NOW if now is None else now
        identity = self.identity(duty)
        return self.sign(duty, "cancel", dict(key_id=identity.key_id, person_id=identity.person_id,
            request_sha256=auth.digest(bundle.request), decision="cancel", trust_epoch=self.trust.epoch,
            issued_at=now - 1, expires_at=now + 30))


class SyntheticSignatureContracts(SyntheticFixture, SimpleTestCase):
    def setUp(self):
        self.identities(1)

    def test_real_ed25519_verification_with_synthetic_identities(self):
        self.assertEqual(self.verify(self.bundle())["role_name"], "Technical Super Admin")

    def test_request_mutations_rejected_even_when_resigned(self):
        for field, value in (("role_name", "Super Admin"), ("is_active", True), ("description", "changed"),
            ("target_schema", "ctug_workspace"), ("environment", "live"), ("policy", "live"),
            ("before_sha256", "bad"), ("backup_sha256", "bad"), ("executor_account_id", True),
            ("incarnation", str(uuid4())), ("trust_epoch", 2), ("operation", "grant")):
            with self.subTest(field=field), self.assertRaises(auth.ContractRefused):
                self.verify(self.bundle(request_changes={field: value}))

    def test_missing_or_duplicate_approval_refused(self):
        bundle = self.bundle()
        for approvals in ((bundle.approvals[0],), (bundle.approvals[0], bundle.approvals[0])):
            with self.subTest(count=len(approvals)), self.assertRaises(auth.ContractRefused):
                self.verify(replace(bundle, approvals=approvals))

    def test_forged_signature_refused(self):
        bundle = self.bundle()
        bad = replace(bundle.approvals[0], signature=b"\0" * 64)
        with self.assertRaises(auth.ContractRefused):
            self.verify(replace(bundle, approvals=(bad, bundle.approvals[1])))

    def test_unknown_key_refused(self):
        with self.assertRaises(auth.ContractRefused):
            self.verify(self.bundle(approval_changes={"institutional": {"key_id": "test_unknown"}}))

    def test_revoked_or_expired_key_refused(self):
        bundle = self.bundle()
        original = self.trust
        for changes in ({"revoked": True}, {"valid_until": self.NOW}):
            self.trust = replace(original, identities=(replace(original.identities[0], **changes), *original.identities[1:]))
            with self.subTest(changes=changes), self.assertRaises(auth.ContractRefused):
                self.verify(bundle)

    def test_same_person_using_two_keys_refused(self):
        identities = list(self.trust.identities)
        identities[1] = replace(identities[1], person_id=identities[0].person_id)
        self.trust = replace(self.trust, identities=tuple(identities))
        with self.assertRaises(auth.ContractRefused):
            self.verify(self.bundle())

    def test_executor_cannot_also_approve(self):
        identities = list(self.trust.identities)
        identities[0] = replace(identities[0], person_id=self.identity("executor").person_id)
        self.trust = replace(self.trust, identities=tuple(identities))
        with self.assertRaises(auth.ContractRefused):
            self.verify(self.bundle())

    def test_one_public_key_cannot_represent_two_people(self):
        identities = list(self.trust.identities)
        identities[1] = replace(identities[1], public_key=identities[0].public_key)
        self.trust = replace(self.trust, identities=tuple(identities))
        with self.assertRaises(auth.ContractRefused):
            self.verify(self.bundle())

    def test_wrong_request_approval_rejected(self):
        with self.assertRaises(auth.ContractRefused):
            self.verify(self.bundle(approval_changes={"technical": {"request_sha256": "f" * 64}}))

    def test_rejection_or_wrong_duty_refused(self):
        for changes in ({"decision": "reject"}, {"duty": "institutional"}):
            with self.subTest(changes=changes), self.assertRaises(auth.ContractRefused):
                self.verify(self.bundle(approval_changes={"technical": changes}))

    def test_ticket_is_bound_to_both_approval_envelopes(self):
        with self.assertRaises(auth.ContractRefused):
            self.verify(self.bundle(ticket_changes={"technical_sha256": "e" * 64}))

    def test_ticket_scope_mutations_refused(self):
        for changes in ({"executor_account_id": 99}, {"release_sha256": "e" * 64}, {"nonce": "bad"},
                        {"request_sha256": "e" * 64}, {"trust_epoch": 2}):
            with self.subTest(changes=changes), self.assertRaises(auth.ContractRefused):
                self.verify(self.bundle(ticket_changes=changes))

    def test_signature_purpose_confusion_refused(self):
        bundle = self.bundle()
        with self.assertRaises(auth.ContractRefused):
            self.verify(replace(bundle, executor=bundle.ticket))

    def test_wrong_executor_or_challenge_refused(self):
        bundle = self.bundle()
        for changes in ({"expected_actor_id": 99}, {"expected_challenge": "d" * 64}):
            with self.subTest(changes=changes), self.assertRaises(auth.ContractRefused):
                self.verify(bundle, **changes)

    def test_executor_registry_account_binding_required(self):
        bundle = self.bundle()
        self.trust = replace(self.trust, identities=tuple(replace(i, account_id=99) if i.duty == "executor" else i for i in self.trust.identities))
        with self.assertRaises(auth.ContractRefused):
            self.verify(bundle)

    def test_expiration_exact_boundary_and_future_refused(self):
        for now in (self.NOW - 10, self.NOW + 60):
            with self.subTest(now=now), self.assertRaises(auth.ContractRefused):
                self.verify(self.bundle(), now=now)

    def test_overlong_or_expired_lifetimes_refused(self):
        variants = (
            self.bundle(request_changes={"expires_at": self.NOW + 86401}),
            self.bundle(approval_changes={"institutional": {"expires_at": self.NOW - 1}}),
            self.bundle(ticket_changes={"expires_at": self.NOW + 901}),
            self.bundle(executor_changes={"expires_at": self.NOW + 301}),
        )
        for bundle in variants:
            with self.subTest(request=auth.digest(bundle.request)), self.assertRaises(auth.ContractRefused):
                self.verify(bundle)

    def test_noncanonical_duplicate_and_unknown_fields_refused(self):
        for blob in (b'{"a":1,"a":2}', b'{ "a":1}', b'{"a":1.0}', b'{"a":NaN}', b'{"a":null}', b'{"a":"\\u00e9"}'):
            with self.subTest(blob=blob), self.assertRaises(auth.ContractRefused):
                auth.parse(blob, {"a"})
        bundle = self.bundle()
        data = auth.parse(bundle.request, auth.REQUEST_FIELDS)
        with self.assertRaises(auth.ContractRefused):
            self.verify(replace(bundle, request=auth.canonical({**data, "extra": 1})))

    def test_oversized_and_unsafe_values_refused(self):
        for value in (1.1, -1, 9_007_199_254_740_992, "\u0430", {"nested": True}, "x" * 8193):
            with self.subTest(kind=type(value).__name__), self.assertRaises(auth.ContractRefused):
                auth.canonical({"a": value})

    def test_restricted_canonical_encoding_known_vector(self):
        self.assertEqual(auth.canonical({"z": False, "a": 'quote"', "n": 17}), b'{"a":"quote\\\"","n":17,"z":false}')

    def test_stored_bundle_round_trip_and_tamper(self):
        bundle = self.bundle()
        self.assertEqual(auth.decode_bundle(auth.encode_bundle(bundle)), bundle)
        with self.assertRaises(auth.ContractRefused):
            auth.decode_bundle(b'{}')

    def test_disposable_guard_refuses_live_settings_before_database(self):
        with override_settings(SETTINGS_MODULE="config.settings"), self.assertRaises(ledger.LedgerRefused):
            ledger.DisposableLedger(ack=ledger.ACK)

    def test_disposable_guard_refuses_wrong_ack(self):
        with self.assertRaises(ledger.LedgerRefused):
            ledger.DisposableLedger(ack="live")

    def test_disposable_guard_refuses_live_schema_label(self):
        with override_settings(REGISTRATION_TEST_DATABASE="ctug_workspace"), self.assertRaises(ledger.LedgerRefused):
            ledger.DisposableLedger(ack=ledger.ACK)

    def test_disposable_guard_checks_actual_schema(self):
        factory = MagicMock()
        fake = SimpleNamespace(settings_dict=settings.DATABASES["default"], cursor=factory, vendor="mysql")
        with patch.object(ledger, "connection", fake):
            cursor = factory.return_value.__enter__.return_value
            cursor.fetchone.return_value = ("ctug_workspace", "READ-COMMITTED")
            with self.assertRaises(ledger.LedgerRefused):
                ledger.DisposableLedger(ack=ledger.ACK)
            self.assertEqual(cursor.execute.call_count, 1)
            self.assertTrue(cursor.execute.call_args.args[0].startswith("SELECT"))

    def test_disposable_guard_rejects_routers_and_secondary_aliases(self):
        redirector = SimpleNamespace(db_for_write=lambda *args, **kwargs: "unexpected")
        with override_settings(DATABASE_ROUTERS=[redirector]), self.assertRaises(ledger.LedgerRefused):
            ledger.DisposableLedger(ack=ledger.ACK)
        # Patch only the settings proxy: do not register/connect another alias.
        configs = {**settings.DATABASES, "unexpected": dict(settings.DATABASES["default"], NAME="ctug_workspace")}
        with patch.object(ledger.settings, "DATABASES", configs), self.assertRaises(ledger.LedgerRefused):
            ledger.DisposableLedger(ack=ledger.ACK)

    def test_live_apply_remains_unavailable(self):
        with self.assertRaises(CommandError):
            call_command("prepare_g1d_p1_protected_role", expected_db="ctug_workspace", ack="G1D_P1_PREPARATION_ONLY", apply=True)


class DisposableLedgerContracts(SyntheticFixture, TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        ledger.disposable_only(ledger.ACK)  # before ANY fixture write
        self.admin = Role.objects.create(role_name="Admin", description="Original Admin", is_active=True)
        for name in ("Student", "Instructor", "Treasurer"):
            Role.objects.create(role_name=name)
        self.service = Service.objects.create(service_code="access_control", service_name="Synthetic governance baseline")
        self.actor = Account.objects.create(school_id="SYNTHETIC-EXECUTOR", request_status="Approved", is_active=True, password="!")
        AccountRole.objects.create(account=self.actor, role=self.admin)
        self.outsider = Account.objects.create(school_id="SYNTHETIC-FRAMEWORK-ONLY", request_status="Approved", is_active=True, is_superuser=True, password="!")
        self.identities(self.actor.pk)
        self.db = ledger.DisposableLedger(ack=ledger.ACK)
        self.db.create(self.trust)
        self.addCleanup(self.db.drop)

    def admit(self, **changes):
        bundle = self.bundle(before=self.db.before_hash(self.actor.pk), **changes)
        request_id = self.db.admit(bundle, self.trust, now=self.NOW, actor_id=self.actor.pk, challenge=self.challenge)
        return bundle, request_id

    def claim(self, request_id):
        return self.db.claim(request_id, self.trust, now=self.NOW)

    def execute(self, claim, **changes):
        params = dict(clock=lambda: self.NOW, simulate_fenced_writers=True)
        params.update(changes)
        return self.db.execute(claim, self.trust, **params)

    def state(self, request_id):
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT status,role_id,audit_id FROM {ledger.REQUESTS} WHERE request_id=%s", (request_id,))
            return cursor.fetchone()

    def assert_unconsumed(self, request_id, status="Attempted"):
        self.assertEqual(self.state(request_id), (status, None, None))
        self.assertFalse(Role.objects.filter(role_name=auth.ROLE_NAME).exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_success_real_commit_and_exact_atomic_receipt(self):
        before_assignments = list(AccountRole.objects.values_list("pk", "account_id", "role_id"))
        _, request_id = self.admit()
        role_id, audit_id = self.execute(self.claim(request_id))
        connection.close()  # committed results must survive a new physical connection
        self.assertEqual(self.state(request_id), ("Consumed", role_id, audit_id))
        role = Role.objects.get(pk=role_id)
        self.assertEqual((role.role_name, role.description, role.is_active), (auth.ROLE_NAME, auth.ROLE_DESCRIPTION, False))
        self.assertEqual(AccessAuditLog.objects.get(pk=audit_id).actor_account_id, self.actor.pk)
        self.assertEqual(self.db.resolve(request_id, self.trust), "COMMITTED")
        self.assertEqual(list(AccountRole.objects.values_list("pk", "account_id", "role_id")), before_assignments)
        self.assertFalse(RolePermission.objects.exists())
        self.assertFalse(Permission.objects.exists())
        self.assertFalse(AccountPermission.objects.exists())
        self.admin.refresh_from_db()
        self.assertEqual((self.admin.description, self.admin.is_active), ("Original Admin", True))

    def test_four_shared_innodb_tables_and_retention(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT TABLE_NAME,ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME IN (%s,%s,%s,%s)", ledger.TABLES)
            self.assertEqual(set(cursor.fetchall()), {(table, "InnoDB") for table in ledger.TABLES})
            cursor.execute(f"SELECT retention_code FROM {ledger.CONTROL}")
            self.assertEqual(cursor.fetchone()[0], "TEST_RUN_ONLY")

    def test_identical_admission_is_idempotent_status_only(self):
        bundle, request_id = self.admit()
        self.assertEqual(self.db.admit(bundle, self.trust, now=self.NOW, actor_id=self.actor.pk, challenge=self.challenge), request_id)
        self.assert_unconsumed(request_id, "Ready")
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {ledger.APPROVALS}")
            self.assertEqual(cursor.fetchone()[0], 2)

    def test_identical_admission_after_commit_is_status_only(self):
        bundle, request_id = self.admit()
        result = self.execute(self.claim(request_id))
        self.assertEqual(self.db.admit(bundle, self.trust, now=self.NOW, actor_id=self.actor.pk, challenge=self.challenge), request_id)
        self.assertEqual(self.state(request_id), ("Consumed", *result))
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_duplicate_id_with_changed_payload_refused(self):
        bundle, request_id = self.admit()
        request = auth.parse(bundle.request, auth.REQUEST_FIELDS)
        with self.assertRaises(ledger.LedgerRefused):
            self.admit(request_changes={"request_id": request_id, "backup_sha256": "d" * 64})
        self.assert_unconsumed(request_id, "Ready")

    def test_database_uniqueness_for_idempotency_and_nonce(self):
        bundle, request_id = self.admit()
        request = auth.parse(bundle.request, auth.REQUEST_FIELDS)
        ticket = auth.parse(bundle.ticket.payload, auth.TICKET_FIELDS)
        for changes in ({"request_changes": {"idempotency_key": request["idempotency_key"]}}, {"ticket_changes": {"nonce": ticket["nonce"]}}):
            with self.subTest(changes=changes), self.assertRaises(IntegrityError):
                self.admit(**changes)
        self.assert_unconsumed(request_id, "Ready")

    def test_request_nonce_and_digest_database_constraints(self):
        _, request_id = self.admit()
        with connection.cursor() as cursor:
            with self.assertRaises(IntegrityError):
                cursor.execute(f"UPDATE {ledger.REQUESTS} SET nonce=NULL WHERE request_id=%s", (request_id,))
            with self.assertRaises(IntegrityError):
                cursor.execute(f"UPDATE {ledger.REQUESTS} SET status='Consumed' WHERE request_id=%s", (request_id,))
        self.assert_unconsumed(request_id, "Ready")

    def test_approval_uniqueness_and_restrictive_fk(self):
        _, request_id = self.admit()
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {ledger.APPROVALS} LIMIT 1")
            values = list(cursor.fetchone())
            values[0] = str(uuid4())
            values[4] = "e" * 64
            with self.assertRaises(IntegrityError):
                cursor.execute(f"INSERT INTO {ledger.APPROVALS} VALUES (%s,%s,%s,%s,%s,%s,%s)", values)
            with self.assertRaises(IntegrityError):
                cursor.execute(f"DELETE FROM {ledger.REQUESTS} WHERE request_id=%s", (request_id,))

    def test_bad_signature_admission_writes_no_evidence(self):
        bundle = self.bundle(before=self.db.before_hash(self.actor.pk))
        bundle = replace(bundle, executor=replace(bundle.executor, signature=b"\0" * 64))
        with self.assertRaises(auth.ContractRefused):
            self.db.admit(bundle, self.trust, now=self.NOW, actor_id=self.actor.pk, challenge=self.challenge)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {ledger.REQUESTS}")
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_claim_is_durable_and_cannot_be_reissued(self):
        _, request_id = self.admit()
        self.claim(request_id)
        connection.close()
        self.assert_unconsumed(request_id)
        with self.assertRaises(ledger.LedgerRefused):
            self.claim(request_id)

    def test_claim_secret_cannot_be_substituted(self):
        _, request_id = self.admit()
        self.claim(request_id)
        with self.assertRaises(ledger.LedgerRefused):
            self.execute(ledger.TestClaim(request_id, b"x" * 32))
        self.assert_unconsumed(request_id)

    def test_replay_after_success_never_writes_again(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)
        self.execute(claim)
        for operation in (lambda: self.execute(claim), lambda: self.claim(request_id)):
            with self.assertRaises(ledger.LedgerRefused):
                operation()
        self.assertEqual(Role.objects.filter(role_name=auth.ROLE_NAME).count(), 1)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_fence_simulation_is_required(self):
        _, request_id = self.admit()
        with self.assertRaises(ledger.LedgerRefused):
            self.execute(self.claim(request_id), simulate_fenced_writers=False)
        self.assert_unconsumed(request_id)

    def test_expired_evidence_after_claim_refused(self):
        _, request_id = self.admit()
        with self.assertRaises(auth.ContractRefused):
            self.execute(self.claim(request_id), clock=lambda: self.NOW + 60)
        self.assert_unconsumed(request_id)

    def test_expiration_rechecked_before_consumption(self):
        _, request_id = self.admit()
        ticks = iter((self.NOW, self.NOW, self.NOW + 60))
        with self.assertRaises(auth.ContractRefused):
            self.execute(self.claim(request_id), clock=lambda: next(ticks))
        self.assert_unconsumed(request_id)

    def test_cancellation_retains_signed_evidence_and_prevents_claim(self):
        bundle, request_id = self.admit()
        proof = self.cancellation(bundle)
        self.db.cancel(request_id, proof, self.trust, now=self.NOW)
        with self.assertRaises(ledger.LedgerRefused):
            self.claim(request_id)
        self.assert_unconsumed(request_id, "Cancelled")
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT evidence FROM {ledger.EVENTS} WHERE event_type='cancelled'")
            self.assertEqual(bytes(cursor.fetchone()[0]), proof.payload + proof.signature)

    def test_unrelated_issuer_cannot_cancel(self):
        bundle, request_id = self.admit()
        with self.assertRaises(ledger.LedgerRefused):
            self.db.cancel(request_id, self.cancellation(bundle, duty="issuer"), self.trust, now=self.NOW)
        self.assert_unconsumed(request_id, "Ready")

    def test_expired_request_record_preserved(self):
        bundle, request_id = self.admit()
        now = self.NOW + 121
        self.db.cancel(request_id, self.cancellation(bundle, now=now), self.trust, now=now, expire=True)
        self.assert_unconsumed(request_id, "Expired")

    def test_cancel_after_claim_or_after_commit(self):
        bundle, request_id = self.admit()
        claim = self.claim(request_id)
        self.db.cancel(request_id, self.cancellation(bundle), self.trust, now=self.NOW)
        with self.assertRaises(ledger.LedgerRefused):
            self.execute(claim)
        self.assert_unconsumed(request_id, "Cancelled")

    def test_revocation_epoch_halts_existing_claim(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)
        self.db.revoke_epoch_test_fixture(now=self.NOW)
        with self.assertRaises(ledger.LedgerRefused):
            self.execute(claim)
        self.assert_unconsumed(request_id)

    def test_stored_approval_tamper_detected(self):
        _, request_id = self.admit()
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE {ledger.APPROVALS} SET signature=%s WHERE duty='technical'", (b"\0" * 64,))
        with self.assertRaises(ledger.LedgerRefused):
            self.claim(request_id)
        self.assert_unconsumed(request_id, "Ready")

    def test_stale_role_description_detected(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)
        Role.objects.filter(pk=self.admin.pk).update(description="Changed after approval")
        with self.assertRaises(ledger.LedgerRefused):
            self.execute(claim)
        self.assert_unconsumed(request_id)

    def test_missing_or_inactive_admin_refused(self):
        _, request_id = self.admit()
        Role.objects.filter(pk=self.admin.pk).update(is_active=False)
        with self.assertRaises(ledger.LedgerRefused):
            self.claim(request_id)
        self.assert_unconsumed(request_id, "Ready")
        Role.objects.filter(pk=self.admin.pk).update(is_active=True, role_name="FormerAdmin")
        with self.assertRaises(ledger.LedgerRefused):
            self.claim(request_id)

    def test_missing_or_inactive_governance_service_refused(self):
        _, request_id = self.admit()
        self.service.is_active = False
        self.service.save(update_fields=["is_active"])
        with self.assertRaises(ledger.LedgerRefused):
            self.claim(request_id)
        self.service.delete()
        with self.assertRaises(ledger.LedgerRefused):
            self.claim(request_id)

    def test_inactive_unapproved_or_unassigned_executor_refused(self):
        _, request_id = self.admit()
        for changes in ({"is_active": False}, {"is_active": True, "request_status": "Pending"}):
            Account.objects.filter(pk=self.actor.pk).update(**changes)
            with self.subTest(changes=changes), self.assertRaises(ledger.LedgerRefused):
                self.claim(request_id)
        Account.objects.filter(pk=self.actor.pk).update(is_active=True, request_status="Approved")
        AccountRole.objects.filter(account=self.actor).delete()
        with self.assertRaises(ledger.LedgerRefused):
            self.claim(request_id)

    def test_framework_superuser_alone_does_not_authorize(self):
        self.actor_id = self.outsider.pk
        self.trust = replace(self.trust, identities=tuple(replace(i, account_id=self.outsider.pk) if i.duty == "executor" else i for i in self.trust.identities))
        bundle = self.bundle(before=self.db.before_hash(self.outsider.pk))
        request_id = self.db.admit(bundle, self.trust, now=self.NOW, actor_id=self.outsider.pk, challenge=self.challenge)
        with self.assertRaises(ledger.LedgerRefused):
            self.claim(request_id)
        self.assert_unconsumed(request_id, "Ready")

    def test_existing_role_and_lookalikes_refused(self):
        for name in (auth.ROLE_NAME, "Super Admin", "TECHNICAL SUPER ADMIN", "Technical Super \u0410dmin"):
            role = Role.objects.create(role_name=name, is_active=False)
            _, request_id = self.admit()
            with self.subTest(name=name), self.assertRaises(ledger.LedgerRefused):
                self.claim(request_id)
            Role.objects.filter(pk=role.pk).delete()
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_core_k_or_governance_override_refused(self):
        permission = Permission.objects.create(service=self.service, permission_code="access_control.catalogue.read", permission_name="Synthetic", module_name="catalogue", action_name="read")
        _, request_id = self.admit()
        with self.assertRaises(ledger.LedgerRefused):
            self.claim(request_id)
        permission.permission_code = "access_control.synthetic.read"
        permission.save(update_fields=["permission_code"])
        AccountPermission.objects.create(account=self.actor, permission=permission, effect="Grant", is_active=True)
        _, next_id = self.admit()
        with self.assertRaises(ledger.LedgerRefused):
            self.claim(next_id)

    def test_audit_failure_rolls_back_role_and_retains_claim(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)
        with patch.object(ledger, "record_access_audit_receipt", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.execute(claim)
        self.assert_unconsumed(request_id)
        self.assertEqual(self.db.resolve(request_id, self.trust), "NOT_COMMITTED")

    def test_invalid_receipt_after_real_audit_insert_rolls_back_both(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)

        def invalid_receipt(**kwargs):
            self.assertTrue(AccessAuditLog.objects.filter(pk=record_access_audit_receipt(**kwargs)).exists())
            return -1

        with patch.object(ledger, "record_access_audit_receipt", side_effect=invalid_receipt):
            with self.assertRaises(ledger.LedgerRefused):
                self.execute(claim)
        self.assert_unconsumed(request_id)

    def test_failure_after_consumption_rolls_back_entire_protected_transaction(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)

        def fail(stage):
            if stage == "after_consumption":
                raise RuntimeError("synthetic post-consumption failure")

        with patch.object(ledger, "_fault_point", side_effect=fail), self.assertRaises(RuntimeError):
            self.execute(claim)
        self.assert_unconsumed(request_id)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {ledger.EVENTS} WHERE event_type='consumed'")
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_unexpected_assignment_rolls_back_with_role(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)

        def inject(stage):
            if stage == "after_role":
                AccountRole.objects.create(account=self.actor, role=Role.objects.get(role_name=auth.ROLE_NAME))

        with patch.object(ledger, "_fault_point", side_effect=inject), self.assertRaises(ledger.LedgerRefused):
            self.execute(claim)
        self.assert_unconsumed(request_id)
        self.assertEqual(AccountRole.objects.count(), 1)

    def test_nested_outer_transaction_refused(self):
        _, request_id = self.admit()
        with transaction.atomic(), self.assertRaises(RuntimeError):
            self.claim(request_id)
        self.assert_unconsumed(request_id, "Ready")

    def test_commit_failure_is_unknown_then_reconciled_not_committed(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)
        original_commit = connection.commit
        commits = []

        def fail_protected_commit():
            commits.append(True)
            if len(commits) == 1:  # durable execution reservation
                return original_commit()
            raise OperationalError("synthetic protected COMMIT failure")

        with patch.object(connection, "commit", side_effect=fail_protected_commit):
            with self.assertRaises(ledger.ExecutionUnknown):
                self.execute(claim)
        connection.close()
        self.assert_unconsumed(request_id)
        self.assertEqual(self.db.resolve(request_id, self.trust), "NOT_COMMITTED")
        with self.assertRaises(ledger.LedgerRefused):
            self.claim(request_id)
        with self.assertRaises(ledger.LedgerRefused):
            self.execute(claim)  # durable execution reservation prevents re-entry

    def test_crash_after_execution_reservation_cannot_resume(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)

        def crash(stage):
            if stage == "after_execution_reservation":
                raise OSError("synthetic process exit before protected transaction")

        with patch.object(ledger, "_fault_point", side_effect=crash), self.assertRaises(OSError):
            self.execute(claim)
        self.assert_unconsumed(request_id)
        self.assertEqual(self.db.resolve(request_id, self.trust), "NOT_COMMITTED")
        with self.assertRaises(ledger.LedgerRefused):
            self.execute(ledger.TestClaim(request_id, claim.secret))

    def test_ambiguous_execution_reservation_never_starts_role_write(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)
        original_commit = connection.commit

        def commit_then_lose_ack():
            original_commit()
            raise OperationalError("synthetic reservation acknowledgment lost")

        with patch.object(connection, "commit", side_effect=commit_then_lose_ack), self.assertRaises(ledger.ExecutionUnknown):
            self.execute(claim)
        connection.close()
        self.assert_unconsumed(request_id)
        self.assertEqual(self.db.resolve(request_id, self.trust), "NOT_COMMITTED")
        with self.assertRaises(ledger.LedgerRefused):
            self.execute(claim)

    def test_commit_succeeded_but_acknowledgment_lost_is_not_retried(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)
        original_commit = connection.commit
        commits = []

        def commit_then_lose_ack():
            original_commit()
            commits.append(True)
            if len(commits) == 2:  # protected commit, after reservation commit
                raise OperationalError("synthetic lost acknowledgment after real commit")

        with patch.object(connection, "commit", side_effect=commit_then_lose_ack):
            with self.assertRaises(ledger.ExecutionUnknown):
                self.execute(claim)
        connection.close()
        self.assertEqual(self.db.resolve(request_id, self.trust), "COMMITTED")
        with self.assertRaises(ledger.LedgerRefused):
            self.execute(claim)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_postcommit_reporting_failure_preserves_consumption(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)

        def fail(stage):
            if stage == "after_commit":
                raise OSError("synthetic report failure")

        with patch.object(ledger, "_fault_point", side_effect=fail), self.assertRaises(ledger.ExecutionUnknown):
            self.execute(claim)
        self.assertEqual(self.db.resolve(request_id, self.trust), "COMMITTED")

    def test_receipt_corruption_is_unknown_not_retryable(self):
        _, request_id = self.admit()
        _, audit_id = self.execute(self.claim(request_id))
        AccessAuditLog.objects.filter(pk=audit_id).update(new_value={"is_active": True})
        self.assertEqual(self.db.resolve(request_id, self.trust), "UNKNOWN")

    def test_consumption_event_corruption_is_unknown(self):
        _, request_id = self.admit()
        self.execute(self.claim(request_id))
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE {ledger.EVENTS} SET evidence=%s WHERE event_type='consumed'", (b"wrong",))
        self.assertEqual(self.db.resolve(request_id, self.trust), "UNKNOWN")

    def test_unique_success_scope_is_enforced_by_mysql(self):
        _, first = self.admit()
        _, second = self.admit()
        self.execute(self.claim(first))
        role = Role.objects.create(role_name="Synthetic other role", is_active=False)
        with transaction.atomic():
            audit_id = record_access_audit_receipt(actor=self.actor, role=role, action="synthetic.constraint.check", reason="policy_enforcement")
        with connection.cursor() as cursor, self.assertRaises(IntegrityError):
            cursor.execute(f"UPDATE {ledger.REQUESTS} SET status='Consumed',claim_sha256=%s,claimed_at=%s,role_id=%s,audit_id=%s,consumed_at=%s,success_scope=%s WHERE request_id=%s",
                ("a" * 64, self.NOW, role.pk, audit_id, self.NOW, ledger.SCOPE, second))
        self.assertEqual(self.state(second), ("Ready", None, None))

    def test_unavailable_primary_is_unknown(self):
        _, request_id = self.admit()
        with patch.object(self.db, "guard", side_effect=OperationalError("synthetic primary unavailable")):
            self.assertEqual(self.db.resolve(request_id, self.trust), "UNKNOWN")

    def test_cancel_consumed_request_is_refused(self):
        bundle, request_id = self.admit()
        self.execute(self.claim(request_id))
        with self.assertRaises(ledger.LedgerRefused):
            self.db.cancel(request_id, self.cancellation(bundle), self.trust, now=self.NOW)
        self.assertEqual(self.db.resolve(request_id, self.trust), "COMMITTED")

    def workers(self, operations):
        barrier = Barrier(len(operations))
        connection_ids, id_lock = [], Lock()

        def worker(operation):
            try:
                ledger.disposable_only(ledger.ACK)  # verifies THIS thread's physical connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT CONNECTION_ID()")
                    with id_lock:
                        connection_ids.append(cursor.fetchone()[0])
                barrier.wait(timeout=10)
                return operation()
            except ledger.LedgerRefused:
                return "REFUSED"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            futures = [pool.submit(worker, operation) for operation in operations]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(len(set(connection_ids)), len(operations))
        return results

    def test_concurrent_claims_of_same_request_have_one_winner(self):
        _, request_id = self.admit()
        results = self.workers([lambda: self.claim(request_id), lambda: self.claim(request_id)])
        self.assertEqual(sum(type(result) is ledger.TestClaim for result in results), 1)
        self.assertEqual(results.count("REFUSED"), 1)

    def test_concurrent_consumption_same_claim_has_one_commit(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)
        results = self.workers([lambda: self.execute(claim), lambda: self.execute(claim)])
        self.assertEqual(sum(type(result) is tuple for result in results), 1)
        self.assertEqual(results.count("REFUSED"), 1)
        self.assertEqual(self.db.resolve(request_id, self.trust), "COMMITTED")
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_different_requests_compete_for_single_resource(self):
        _, first = self.admit()
        _, second = self.admit()
        claims = [self.claim(first), self.claim(second)]
        results = self.workers([lambda c=c: self.execute(c) for c in claims])
        self.assertEqual(sum(type(result) is tuple for result in results), 1)
        self.assertEqual(results.count("REFUSED"), 1)
        self.assertEqual(Role.objects.filter(role_name=auth.ROLE_NAME).count(), 1)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_uncooperative_writer_is_not_protected_by_control_row_lock(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)
        inserted = Event()

        def raw_writer():
            try:
                ledger.disposable_only(ledger.ACK)
                Role.objects.create(role_name="Super Admin", is_active=False)
                inserted.set()
            finally:
                connections.close_all()

        def locked_hook(stage):
            if stage == "control_locked":
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(raw_writer)
                    self.assertTrue(inserted.wait(timeout=5))
                    future.result(timeout=5)

        with patch.object(ledger, "_fault_point", side_effect=locked_hook), self.assertRaises(ledger.LedgerRefused):
            self.execute(claim)
        self.assert_unconsumed(request_id)
        self.assertTrue(Role.objects.filter(role_name="Super Admin").exists())

    def test_resolver_waits_for_inflight_transaction_before_classification(self):
        _, request_id = self.admit()
        claim = self.claim(request_id)
        entered, release, resolving, completed = Event(), Event(), Event(), Event()

        def pause(stage):
            if stage == "before_commit":
                entered.set()
                if not release.wait(timeout=10):
                    raise RuntimeError("test synchronization timeout")

        def run():
            try:
                return self.execute(claim)
            finally:
                connections.close_all()

        def resolve():
            try:
                ledger.disposable_only(ledger.ACK)
                resolving.set()
                return self.db.resolve(request_id, self.trust)
            finally:
                completed.set()
                connections.close_all()

        with patch.object(ledger, "_fault_point", side_effect=pause), ThreadPoolExecutor(max_workers=2) as pool:
            execution = pool.submit(run)
            try:
                self.assertTrue(entered.wait(timeout=5))
                resolution = pool.submit(resolve)
                self.assertTrue(resolving.wait(timeout=5))
                self.assertFalse(completed.wait(timeout=0.1))
            finally:
                release.set()
            execution.result(timeout=10)
            self.assertEqual(resolution.result(timeout=10), "COMMITTED")
