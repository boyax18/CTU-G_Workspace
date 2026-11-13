"""G1D-P3B pure offline Ed25519/root-bound contract tests; no database."""

from dataclasses import replace
import secrets
from unittest import TestCase
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from apps.access_control.tests_support import g1d_p1_authorization_design_test_only as auth
from apps.access_control.tests_support import g1d_p3a_root_endorsed_registry_test_only as roots
from apps.access_control.tests_support import g1d_p3b_root_bound_executor_test_only as p3b


class RootBoundExecutorTests(TestCase):
    NOW = 1_794_535_200
    ACTOR = 15
    SCHEMA = "test_ctug_registration_0123456789abcdef"

    def setUp(self):
        self.root_priv = {
            duty: Ed25519PrivateKey.generate()
            for duty in ("institutional_root", "technical_root")
        }
        self.signer_priv = {
            duty: Ed25519PrivateKey.generate()
            for duty in ("institutional", "technical", "issuer", "executor")
        }
        self.pins = tuple(
            roots.RootPin(
                key_id="test_" + duty, person_id=str(uuid4()), duty=duty,
                public_key=key.public_key().public_bytes_raw(),
            ) for duty, key in self.root_priv.items()
        )
        self.trust = auth.SyntheticTrust(
            schema=self.SCHEMA, incarnation=str(uuid4()), epoch=7,
            identities=tuple(
                auth.TestPublicIdentity(
                    key_id="test_" + duty, person_id=str(uuid4()), duty=duty,
                    public_key=key.public_key().public_bytes_raw(),
                    account_id=self.ACTOR if duty == "executor" else 0,
                ) for duty, key in self.signer_priv.items()
            ),
        )
        self.registry = self.registry_for(self.trust)
        self.challenge = secrets.token_hex(32)
        self.nonce = secrets.token_hex(32)
        self.bundle = self.make_bundle()
        self.expected = self.expectation_for(self.bundle)

    def identity(self, duty):
        return next(i for i in self.trust.identities if i.duty == duty)

    def sign(self, duty, purpose, payload):
        body = auth.canonical(payload)
        return auth.SignedTestProof(
            body, self.signer_priv[duty].sign(auth.signature_message(purpose, body)),
        )

    def registry_for(self, trust):
        manifest = roots.make_unsigned_manifest(
            trust, issued_at=self.NOW - 60, expires_at=self.NOW + 600,
        )
        endorsements = tuple(
            roots.RootEndorsement(
                key_id=pin.key_id, person_id=pin.person_id, duty=pin.duty,
                signature=self.root_priv[pin.duty].sign(roots.DOMAIN + manifest),
            ) for pin in self.pins
        )
        return roots.RootEndorsedRegistry(manifest, trust, endorsements)

    def make_bundle(self, *, release="c" * 64, before="b" * 64, backup="a" * 64, nonce=None, challenge=None):
        nonce = self.nonce if nonce is None else nonce
        challenge = self.challenge if challenge is None else challenge
        executor = self.identity("executor")
        request = {
            "request_id": str(uuid4()), "idempotency_key": secrets.token_hex(32),
            "operation": auth.ACTION, "role_name": auth.ROLE_NAME,
            "description": auth.ROLE_DESCRIPTION, "is_active": False,
            "target_schema": self.trust.schema, "environment": auth.ENVIRONMENT,
            "incarnation": self.trust.incarnation, "policy": auth.POLICY,
            "executor_account_id": self.ACTOR, "executor_person": executor.person_id,
            "executor_key": executor.key_id, "trust_epoch": self.trust.epoch,
            "before_sha256": before, "backup_sha256": backup,
            "release_sha256": release,
            "issued_at": self.NOW - 5, "expires_at": self.NOW + 600,
        }
        body = auth.canonical(request)
        request_hash = auth.digest(body)
        approvals = []
        for duty in ("institutional", "technical"):
            signer = self.identity(duty)
            approvals.append(self.sign(duty, "approval", {
                "approval_id": str(uuid4()), "key_id": signer.key_id,
                "person_id": signer.person_id, "duty": duty,
                "request_sha256": request_hash, "decision": "approve",
                "trust_epoch": self.trust.epoch, "issued_at": self.NOW - 3,
                "expires_at": self.NOW + 600,
            }))
        issuer = self.identity("issuer")
        ticket = self.sign("issuer", "ticket", {
            "key_id": issuer.key_id, "person_id": issuer.person_id,
            "request_sha256": request_hash,
            "institutional_sha256": auth.proof_digest(approvals[0]),
            "technical_sha256": auth.proof_digest(approvals[1]),
            "nonce": nonce, "executor_account_id": self.ACTOR,
            "release_sha256": release, "trust_epoch": self.trust.epoch,
            "issued_at": self.NOW - 2, "expires_at": self.NOW + 120,
        })
        proof = self.sign("executor", "executor", {
            "key_id": executor.key_id, "person_id": executor.person_id,
            "request_sha256": request_hash, "nonce": nonce,
            "executor_account_id": self.ACTOR, "release_sha256": release,
            "challenge": challenge, "trust_epoch": self.trust.epoch,
            "issued_at": self.NOW - 1, "expires_at": self.NOW + 60,
        })
        return auth.SyntheticBundle(body, tuple(approvals), ticket, proof)

    def expectation_for(self, bundle):
        request = auth.parse(bundle.request, auth.REQUEST_FIELDS)
        ticket = auth.parse(bundle.ticket.payload, auth.TICKET_FIELDS)
        return p3b.IndependentTestExpectation(
            schema=self.trust.schema, incarnation=self.trust.incarnation,
            minimum_epoch=self.trust.epoch,
            roster_sha256=auth.digest(roots.roster_bytes(self.trust)),
            actor_id=self.ACTOR, challenge=self.challenge,
            request_sha256=auth.digest(bundle.request),
            bundle_sha256=auth.digest(auth.encode_bundle(bundle)),
            ticket_nonce=ticket["nonce"],
            before_sha256=request["before_sha256"],
            backup_sha256=request["backup_sha256"],
            release_sha256=request["release_sha256"],
        )

    def verify(self, *, registry=None, bundle=None, pins=None, expected=None, now=None):
        return p3b.verify_root_bound_executor(
            self.registry if registry is None else registry,
            self.pins if pins is None else pins,
            self.bundle if bundle is None else bundle,
            expected=self.expected if expected is None else expected,
            now=self.NOW if now is None else now,
        )

    def refused(self, **params):
        with self.assertRaises(auth.ContractRefused):
            self.verify(**params)

    def test_valid_root_registry_and_fully_signed_executor(self):
        receipt = self.verify()
        req = auth.parse(self.bundle.request, auth.REQUEST_FIELDS)
        self.assertEqual(receipt.actor_id, self.ACTOR)
        self.assertEqual(receipt.request_id, req["request_id"])
        self.assertEqual(receipt.trust_epoch, self.trust.epoch)
        self.assertEqual(receipt.bundle_sha256, self.expected.bundle_sha256)

    def test_receipt_is_not_a_live_permission(self):
        receipt = self.verify()
        self.assertEqual(set(vars(receipt)), {
            "request_id", "actor_id", "request_sha256", "bundle_sha256", "ticket_nonce",
            "roster_sha256", "trust_epoch", "ticket_expires_at",
        })
        self.assertNotIn("approved_for_live", vars(receipt))

    def test_independent_release_hash_mismatch_refused(self):
        self.refused(expected=replace(self.expected, release_sha256="d" * 64))

    def test_independent_backup_hash_mismatch_refused(self):
        self.refused(expected=replace(self.expected, backup_sha256="d" * 64))

    def test_independent_before_hash_mismatch_refused(self):
        self.refused(expected=replace(self.expected, before_sha256="d" * 64))

    def test_exact_request_hash_mismatch_refused(self):
        self.refused(expected=replace(self.expected, request_sha256="d" * 64))

    def test_exact_bundle_hash_mismatch_refused(self):
        self.refused(expected=replace(self.expected, bundle_sha256="d" * 64))

    def test_exact_ticket_nonce_mismatch_refused(self):
        self.refused(expected=replace(self.expected, ticket_nonce="d" * 64))

    def test_challenge_mismatch_refused(self):
        self.refused(expected=replace(self.expected, challenge="d" * 64))

    def test_wrong_expected_actor_refused(self):
        self.refused(expected=replace(self.expected, actor_id=self.ACTOR + 1))

    def test_wrong_schema_refused(self):
        self.refused(expected=replace(self.expected, schema="test_ctug_registration_ffffffffffffffff"))
        self.refused(expected=replace(self.expected, schema="ctug_workspace"))

    def test_wrong_incarnation_refused(self):
        self.refused(expected=replace(self.expected, incarnation=str(uuid4())))

    def test_old_root_epoch_refused(self):
        self.refused(expected=replace(self.expected, minimum_epoch=self.trust.epoch + 1))

    def test_roster_hash_mismatch_refused(self):
        self.refused(expected=replace(self.expected, roster_sha256="d" * 64))

    def test_different_valid_signed_bundle_same_scope_refused(self):
        new_bundle = self.make_bundle()
        self.refused(bundle=new_bundle)

    def test_alternate_signed_release_refused(self):
        new_bundle = self.make_bundle(release="d" * 64)
        self.refused(bundle=new_bundle)

    def test_alternate_signed_nonce_refused(self):
        new_bundle = self.make_bundle(nonce="e" * 64)
        self.refused(bundle=new_bundle)

    def test_wrong_executor_challenge_rejected_by_signature_contract(self):
        self.refused(bundle=self.make_bundle(challenge="d" * 64))

    def test_forged_executor_signature_refused(self):
        forged = replace(self.bundle.executor, signature=b"\0" * 64)
        self.refused(bundle=replace(self.bundle, executor=forged))

    def test_revoked_executor_in_root_signed_registry_refused(self):
        roster = replace(self.trust, identities=tuple(
            replace(identity, revoked=True) if identity.duty == "executor" else identity
            for identity in self.trust.identities
        ))
        self.refused(registry=self.registry_for(roster))

    def test_same_person_multiple_duties_with_fresh_signatures_refused(self):
        institutional = self.identity("institutional")
        roster = replace(self.trust, identities=tuple(
            replace(identity, person_id=institutional.person_id) if identity.duty == "executor" else identity
            for identity in self.trust.identities
        ))
        self.refused(registry=self.registry_for(roster))

    def test_forged_root_signature_refused(self):
        forged = replace(self.registry.endorsements[0], signature=b"\0" * 64)
        self.refused(registry=replace(self.registry, endorsements=(forged, self.registry.endorsements[1])))

    def test_root_pin_substitution_refused(self):
        alien = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        self.refused(pins=(replace(self.pins[0], public_key=alien), self.pins[1]))

    def test_expired_executor_evidence_refused(self):
        self.refused(now=self.NOW + 60)

    def test_expired_manifest_refused(self):
        self.refused(now=self.NOW + 600)

    def test_invalid_expected_hash_type_refused(self):
        self.refused(expected=replace(self.expected, backup_sha256=123))
        self.refused(expected=replace(self.expected, roster_sha256=True))

    def test_invalid_actor_bool_refused(self):
        self.refused(expected=replace(self.expected, actor_id=True))

    def test_invalid_epoch_floor_refused(self):
        self.refused(expected=replace(self.expected, minimum_epoch=0))
        self.refused(expected=replace(self.expected, minimum_epoch=True))

    def test_unsupported_expectation_type_refused(self):
        self.refused(expected={"actor_id": self.ACTOR})
