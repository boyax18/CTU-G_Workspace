"""Offline trust/transport security contracts; actual SQL proof is a separate server run."""
from copy import deepcopy
from pathlib import Path
import secrets
import tempfile
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.test import SimpleTestCase, override_settings

from .executor import protocol as p
from .executor.engine import evidence
from .executor.trust import DOMAIN, TrustStore
from .protected_requests import ProtectedRequestRefused, canonical, digest
from .tests_support.task2_signed_fixture_test_only import trust_fixture


class ExecutorProtocolTests(SimpleTestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.peer = secrets.token_hex(32)
        self.proof = p.issue_proof(self.key, actor_id=1, peer=self.peer, epoch=1, issued=1800000000)

    def actor(self, proof=None, **kwargs):
        return p.actor_from_proof(proof or self.proof, (self.key.public_key(),), peer=self.peer, epoch=1, at=1800000001, **kwargs)

    def test_authenticator_proves_actor_key_possession_without_runtime_secret(self):
        self.assertEqual(1, self.actor())

    def test_runtime_cannot_mint_actor_by_editing_id(self):
        proof = deepcopy(self.proof)
        proof["payload"]["actor_id"] = 2
        with self.assertRaises(ProtectedRequestRefused):
            self.actor(proof)

    def test_peer_bound_proof_cannot_be_transferred_to_other_client_certificate(self):
        with self.assertRaises(ProtectedRequestRefused):
            p.actor_from_proof(self.proof, (self.key.public_key(),), peer="b" * 64, epoch=1, at=1800000001)

    def test_epoch_revokes_old_proof(self):
        with self.assertRaises(ProtectedRequestRefused):
            p.actor_from_proof(self.proof, (self.key.public_key(),), peer=self.peer, epoch=2, at=1800000001)

    def test_exact_expiry_refuses_actor_proof(self):
        with self.assertRaises(ProtectedRequestRefused):
            p.actor_from_proof(self.proof, (self.key.public_key(),), peer=self.peer, epoch=1, at=1800000300)

    def test_untrusted_issuer_is_refused(self):
        with self.assertRaises(ProtectedRequestRefused):
            p.actor_from_proof(self.proof, (Ed25519PrivateKey.generate().public_key(),), peer=self.peer, epoch=1, at=1800000001)

    def test_duplicate_json_fields_refused(self):
        with self.assertRaises(ProtectedRequestRefused):
            p.decode(b'{"operation":"registration.approve","operation":"technical_admin.bootstrap"}')

    def test_non_json_and_oversize_refused(self):
        for data in (b"NaN", b"[", b"x" * 32769):
            with self.assertRaises(ProtectedRequestRefused):
                p.decode(data)

    def test_fixed_dispatch_refuses_unknown_operations(self):
        value = p.request("raw.sql", {"sql": "UPDATE accounts SET is_superuser=1"})
        with self.assertRaises(ProtectedRequestRefused):
            p.validate_request(value, "ordinary")

    def test_ordinary_cannot_dispatch_protected_operation(self):
        with self.assertRaises(ProtectedRequestRefused):
            p.validate_request(p.request("technical_admin.bootstrap", {}), "ordinary")

    def test_actor_proof_boolean_id_refused(self):
        proof = p.issue_proof(self.key, actor_id=True, peer=self.peer, epoch=1, issued=1800000000)
        with self.assertRaises(ProtectedRequestRefused):
            self.actor(proof)

    def test_evidence_never_persists_passwords_or_link_secrets_or_fast_hashes(self):
        value = {"payload": {"password": "neverpersist", "data": {"password_confirmation": "neverpersist"}, "token": "neverpersist"}}
        self.assertNotIn("neverpersist", canonical(evidence(value)).decode())

    @override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True)
    def test_runtime_has_no_local_fallback_when_executor_configuration_is_missing(self):
        from .executor.client import remote_call
        from .writer_boundary import WriterBoundaryUnavailable
        with self.assertRaises(WriterBoundaryUnavailable) as caught:
            remote_call("registration.approve", {"actor_id": 1, "target_id": 2})
        self.assertEqual(64, len(caught.exception.request_id))
        self.assertEqual(64, len(caught.exception.request_hash))


class RootRosterTests(SimpleTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Ed25519PrivateKey.generate()
        trust, _ = trust_fixture("fixture_schema", 1, p.now())
        self.payload = {k: getattr(trust, k) for k in ("schema", "incarnation", "epoch", "release_hash", "fence_hash", "recovery_hash")}
        self.payload.update(server_uuid="fictional", issued=p.now(), expires=p.now() + 120,
            policy_hash=digest({"delegation": {}, "ordinary_assignment": {}}),
            signers=[{**s.__dict__, "public_key": s.public_key.hex()} for s in trust.signers],
            issuers=[Ed25519PrivateKey.generate().public_key().public_bytes_raw().hex()], peers={"a" * 64: ["ordinary"]})
        self.file = Path(self.directory.name) / "roster.json"
        self.config = {"schema": "fixture_schema", "server_uuid": "fictional", "minimum_epoch": 1,
                       "policy_hash": self.payload["policy_hash"],
                       "roster": str(self.file), "root_public_key": self.root.public_key().public_bytes_raw().hex()}
        self.write()

    def write(self):
        self.file.write_bytes(canonical({"payload": self.payload, "signature": self.root.sign(DOMAIN + canonical(self.payload)).hex()}))

    def test_root_authenticated_roster_loads(self):
        self.assertEqual(1, TrustStore(self.config).load()[1].epoch)

    def test_request_owned_root_does_not_replace_pinned_root(self):
        self.config["root_public_key"] = Ed25519PrivateKey.generate().public_key().public_bytes_raw().hex()
        with self.assertRaises(ProtectedRequestRefused):
            TrustStore(self.config).load()

    def test_external_epoch_floor_rejects_restored_stale_roster(self):
        self.config["minimum_epoch"] = 2
        with self.assertRaises(ProtectedRequestRefused):
            TrustStore(self.config).load()

    def test_expired_root_roster_refuses_even_valid_signature(self):
        self.payload["expires"] = p.now()
        self.write()
        with self.assertRaises(ProtectedRequestRefused):
            TrustStore(self.config).load()

    def test_server_identity_substitution_refused(self):
        self.config["server_uuid"] = "another-server"
        with self.assertRaises(ProtectedRequestRefused):
            TrustStore(self.config).load()

    def test_unendorsed_delegation_policy_hash_refused(self):
        self.config["policy_hash"] = "0" * 64
        with self.assertRaises(ProtectedRequestRefused):
            TrustStore(self.config).load()
