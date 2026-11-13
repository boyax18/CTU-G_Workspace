"""Pure synthetic root-endorsement tests; never load production settings or DB."""

from dataclasses import replace
import secrets
from unittest import TestCase
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from apps.access_control.tests_support import g1d_p1_authorization_design_test_only as auth
from apps.access_control.tests_support import g1d_p3a_root_endorsed_registry_test_only as roots


class RootEndorsedRegistryContracts(TestCase):
    NOW = 1_794_535_200

    def setUp(self):
        self.root_private = {
            duty: Ed25519PrivateKey.generate()
            for duty in ("institutional_root", "technical_root")
        }
        self.identity_private = {
            duty: Ed25519PrivateKey.generate()
            for duty in ("institutional", "technical", "executor", "issuer")
        }
        self.pins = tuple(roots.RootPin(
            key_id="test_" + duty,
            person_id=str(uuid4()),
            duty=duty,
            public_key=key.public_key().public_bytes_raw(),
        ) for duty, key in self.root_private.items())
        self.trust = auth.SyntheticTrust(
            schema="test_ctug_registration_0123456789abcdef",
            incarnation=str(uuid4()),
            epoch=3,
            identities=tuple(auth.TestPublicIdentity(
                key_id="test_" + duty,
                person_id=str(uuid4()),
                duty=duty,
                public_key=key.public_key().public_bytes_raw(),
                account_id=15 if duty == "executor" else 0,
            ) for duty, key in self.identity_private.items()),
        )

    def signed(self, trust=None, *, issued_at=None, expires_at=None):
        trust = self.trust if trust is None else trust
        manifest = roots.make_unsigned_manifest(
            trust,
            issued_at=self.NOW - 60 if issued_at is None else issued_at,
            expires_at=self.NOW + 600 if expires_at is None else expires_at,
        )
        endorsements = tuple(roots.RootEndorsement(
            key_id=pin.key_id, person_id=pin.person_id, duty=pin.duty,
            signature=self.root_private[pin.duty].sign(roots.DOMAIN + manifest),
        ) for pin in self.pins)
        return roots.RootEndorsedRegistry(manifest, trust, endorsements)

    def verify(self, registry=None, pins=None, **changes):
        options = dict(
            expected_schema=self.trust.schema,
            expected_incarnation=self.trust.incarnation,
            minimum_epoch=2,
            now=self.NOW,
        )
        options.update(changes)
        return roots.verify_root_endorsed_registry(
            self.signed() if registry is None else registry,
            self.pins if pins is None else pins,
            **options,
        )

    def rejected(self, registry=None, pins=None, **changes):
        with self.assertRaises(auth.ContractRefused):
            self.verify(registry, pins, **changes)

    def test_two_independent_root_signatures_accept_synthetic_roster(self):
        self.assertEqual(self.verify(), self.trust)

    def test_one_signature_is_not_two_approvals(self):
        signed = self.signed()
        self.rejected(replace(signed, endorsements=signed.endorsements[:1]))
        self.rejected(replace(signed, endorsements=signed.endorsements * 2))

    def test_duplicate_root_duty_refused(self):
        self.rejected(pins=(self.pins[0], replace(self.pins[1], duty=self.pins[0].duty)))

    def test_same_person_as_both_roots_refused(self):
        self.rejected(pins=(self.pins[0], replace(self.pins[1], person_id=self.pins[0].person_id)))

    def test_same_public_key_as_both_roots_refused(self):
        self.rejected(pins=(self.pins[0], replace(self.pins[1], public_key=self.pins[0].public_key)))

    def test_key_substitution_in_root_pin_refused(self):
        alien = Ed25519PrivateKey.generate()
        self.rejected(pins=(replace(self.pins[0], public_key=alien.public_key().public_bytes_raw()), self.pins[1]))

    def test_signer_claim_cannot_replace_pin(self):
        signed = self.signed()
        forged = replace(signed.endorsements[0], key_id=self.pins[1].key_id)
        self.rejected(replace(signed, endorsements=(forged, signed.endorsements[1])))

    def test_root_signature_tamper_refused(self):
        signed = self.signed()
        bad = replace(signed.endorsements[0], signature=b"\0" * 64)
        self.rejected(replace(signed, endorsements=(bad, signed.endorsements[1])))

    def test_one_root_signature_cannot_be_reused_as_other_duty(self):
        signed = self.signed()
        other = replace(signed.endorsements[0], duty="technical_root", key_id=self.pins[1].key_id,
                        person_id=self.pins[1].person_id)
        self.rejected(replace(signed, endorsements=(signed.endorsements[0], other)))

    def test_revoked_root_refused(self):
        self.rejected(pins=(replace(self.pins[0], revoked=True), self.pins[1]))

    def test_root_expiration_exact_boundary_refused(self):
        self.rejected(pins=(replace(self.pins[0], valid_until=self.NOW), self.pins[1]))

    def test_revocation_types_cannot_be_truthy_strings(self):
        self.rejected(pins=(replace(self.pins[0], revoked="False"), self.pins[1]))

    def test_manifest_expired_refused(self):
        self.rejected(self.signed(expires_at=self.NOW))

    def test_manifest_issued_in_future_refused(self):
        self.rejected(self.signed(issued_at=self.NOW + 1))

    def test_manifest_lifetime_over_24_hours_refused(self):
        self.rejected(self.signed(expires_at=self.NOW + 86400))

    def test_epoch_rollback_refused_even_with_valid_old_signatures(self):
        self.rejected(minimum_epoch=self.trust.epoch + 1)

    def test_wrong_schema_or_environment_refused(self):
        self.rejected(expected_schema="ctug_workspace")
        self.rejected(expected_schema="test_ctug_registration_ffffffffffffffff")

    def test_wrong_incarnation_refused(self):
        self.rejected(expected_incarnation=str(uuid4()))

    def test_roster_key_replacement_refused_even_with_valid_root_signatures(self):
        signed = self.signed()
        alien = Ed25519PrivateKey.generate()
        identities = list(self.trust.identities)
        identities[0] = replace(identities[0], public_key=alien.public_key().public_bytes_raw())
        self.rejected(replace(signed, trust=replace(self.trust, identities=tuple(identities))))

    def test_roster_person_substitution_refused(self):
        signed = self.signed()
        identities = list(self.trust.identities)
        identities[0] = replace(identities[0], person_id=str(uuid4()))
        self.rejected(replace(signed, trust=replace(self.trust, identities=tuple(identities))))

    def test_roster_root_person_overlap_refused(self):
        identities = list(self.trust.identities)
        identities[0] = replace(identities[0], person_id=self.pins[0].person_id)
        trust = replace(self.trust, identities=tuple(identities))
        self.rejected(self.signed(trust))

    def test_same_person_cannot_hold_two_active_roster_duties(self):
        identities = list(self.trust.identities)
        identities[1] = replace(identities[1], person_id=identities[0].person_id)
        self.rejected(self.signed(replace(self.trust, identities=tuple(identities))))

    def test_missing_active_executor_refused(self):
        identities = list(self.trust.identities)
        identities[2] = replace(identities[2], revoked=True)
        self.rejected(self.signed(replace(self.trust, identities=tuple(identities))))

    def test_expired_active_issuer_refused(self):
        identities = list(self.trust.identities)
        identities[3] = replace(identities[3], valid_until=self.NOW)
        self.rejected(self.signed(replace(self.trust, identities=tuple(identities))))

    def test_unknown_policy_refused_even_when_signed(self):
        signed = self.signed()
        manifest = auth.parse(signed.manifest, roots.MANIFEST_FIELDS)
        manifest["policy"] = "LIVE"
        new_bytes = auth.canonical(manifest)
        new_endorsements = tuple(replace(e, signature=self.root_private[e.duty].sign(roots.DOMAIN + new_bytes))
                                 for e in signed.endorsements)
        self.rejected(replace(signed, manifest=new_bytes, endorsements=new_endorsements))

    def test_valid_signature_over_other_domain_refused(self):
        signed = self.signed()
        wrong = tuple(replace(e, signature=self.root_private[e.duty].sign(b"WRONG\0" + signed.manifest))
                      for e in signed.endorsements)
        self.rejected(replace(signed, endorsements=wrong))

    def test_unknown_fields_and_duplicate_keys_refused(self):
        signed = self.signed()
        self.rejected(replace(signed, manifest=signed.manifest[:-1] + b',"extra":1}'))
        self.rejected(replace(signed, manifest=signed.manifest[:-1] + b',"policy":"again"}'))

    def test_no_implicit_live_schema_acceptance(self):
        self.rejected(expected_schema="ctug_workspace")
        self.rejected(expected_schema="production")

    def test_invalid_enrollment_identity_format_refused(self):
        identities = list(self.trust.identities)
        identities[0] = replace(identities[0], key_id="not_a_test_key")
        self.rejected(replace(self.signed(), trust=replace(self.trust, identities=tuple(identities))))

    def test_roster_encoding_stable_across_identity_order(self):
        reordered = replace(self.trust, identities=tuple(reversed(self.trust.identities)))
        self.assertEqual(roots.roster_bytes(self.trust), roots.roster_bytes(reordered))
        self.assertEqual(self.verify(self.signed(reordered)), reordered)

    def test_public_keys_are_never_generated_by_verifier(self):
        # This verifier imports only Ed25519PublicKey; private keys live in these tests.
        self.assertNotIn("Ed25519PrivateKey", roots.__dict__)

    def test_root_endorsed_registry_interoperates_with_existing_bundle_verifier(self):
        verified_trust = self.verify()
        actor_id = 15
        challenge = secrets.token_hex(32)
        executor = next(i for i in self.trust.identities if i.duty == "executor")
        request = {
            "request_id": str(uuid4()), "idempotency_key": secrets.token_hex(32),
            "operation": auth.ACTION, "role_name": auth.ROLE_NAME,
            "description": auth.ROLE_DESCRIPTION, "is_active": False,
            "target_schema": verified_trust.schema, "environment": auth.ENVIRONMENT,
            "incarnation": verified_trust.incarnation, "policy": auth.POLICY,
            "executor_account_id": actor_id, "executor_person": executor.person_id,
            "executor_key": executor.key_id, "trust_epoch": verified_trust.epoch,
            "before_sha256": "b" * 64, "backup_sha256": "a" * 64,
            "release_sha256": "c" * 64,
            "issued_at": self.NOW - 5, "expires_at": self.NOW + 600,
        }
        request_body = auth.canonical(request)
        request_hash = auth.digest(request_body)

        def sign(duty, purpose, payload):
            body = auth.canonical(payload)
            signature = self.identity_private[duty].sign(auth.signature_message(purpose, body))
            return auth.SignedTestProof(body, signature)

        approvals = []
        for duty in ("institutional", "technical"):
            identity = next(i for i in verified_trust.identities if i.duty == duty)
            approvals.append(sign(duty, "approval", {
                "approval_id": str(uuid4()), "key_id": identity.key_id,
                "person_id": identity.person_id, "duty": duty,
                "request_sha256": request_hash, "decision": "approve",
                "trust_epoch": verified_trust.epoch,
                "issued_at": self.NOW - 3, "expires_at": self.NOW + 600,
            }))
        issuer = next(i for i in verified_trust.identities if i.duty == "issuer")
        ticket_nonce = secrets.token_hex(32)
        ticket = sign("issuer", "ticket", {
            "key_id": issuer.key_id, "person_id": issuer.person_id,
            "request_sha256": request_hash,
            "institutional_sha256": auth.proof_digest(approvals[0]),
            "technical_sha256": auth.proof_digest(approvals[1]),
            "nonce": ticket_nonce, "executor_account_id": actor_id,
            "release_sha256": request["release_sha256"],
            "trust_epoch": verified_trust.epoch,
            "issued_at": self.NOW - 2, "expires_at": self.NOW + 120,
        })
        executor_proof = sign("executor", "executor", {
            "key_id": executor.key_id, "person_id": executor.person_id,
            "request_sha256": request_hash, "nonce": ticket_nonce,
            "executor_account_id": actor_id, "release_sha256": request["release_sha256"],
            "challenge": challenge, "trust_epoch": verified_trust.epoch,
            "issued_at": self.NOW - 1, "expires_at": self.NOW + 60,
        })
        bundle = auth.SyntheticBundle(request_body, tuple(approvals), ticket, executor_proof)
        self.assertEqual(auth.verify_bundle(
            bundle, verified_trust, now=self.NOW,
            expected_actor_id=actor_id, expected_challenge=challenge,
        ), request)
