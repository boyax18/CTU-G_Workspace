"""Offline cryptographic negatives and release-denial contracts."""

from copy import deepcopy
from dataclasses import replace
from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from .checks import protected_executor_release_checks
from .protected_requests import ProtectedRequestRefused, canonical, verify_request
from .tests_support.task2_signed_fixture_test_only import request_fixture, sign_fixture, trust_fixture


class ProtectedRequestTests(SimpleTestCase):
    def setUp(self):
        self.now = 1_800_000_000
        self.trust, self.keys = trust_fixture("test_ctug_registration_0123456789abcdef", 1, self.now)
        self.bundle = request_fixture(self.trust, self.keys, 1, now=self.now, before_hash="a" * 64)

    def verify(self, bundle=None, trust=None, now=None):
        return verify_request(self.bundle if bundle is None else bundle,
                              self.trust if trust is None else trust,
                              now=self.now if now is None else now)

    def test_three_independent_signatures_verify(self):
        self.assertEqual(self.bundle["request"], self.verify())

    def test_result_detaches_mutable_input(self):
        result = self.verify()
        self.bundle["request"]["permission_codes"].clear()
        self.assertEqual(6, len(result["permission_codes"]))

    def test_tampered_signed_fields_are_refused(self):
        for field, value in (("actor_id", 2), ("before_hash", "b" * 64),
                             ("nonce", "b" * 64), ("request_id", "b" * 64)):
            with self.subTest(field=field), self.assertRaises(ProtectedRequestRefused):
                bundle = deepcopy(self.bundle)
                bundle["request"][field] = value
                self.verify(bundle)

    def test_even_resigned_untrusted_context_is_refused(self):
        for field, value in (("schema", "ctug_workspace"), ("epoch", 2),
                             ("incarnation", "b" * 64), ("release_hash", "b" * 64),
                             ("fence_hash", "b" * 64), ("recovery_hash", "b" * 64)):
            request = {**self.bundle["request"], field: value}
            with self.subTest(field=field), self.assertRaises(ProtectedRequestRefused):
                self.verify(sign_fixture(request, self.trust, self.keys))

    def test_missing_or_extra_fields_are_refused(self):
        for change in ("delete", "extra"):
            bundle = deepcopy(self.bundle)
            if change == "delete":
                del bundle["request"]["nonce"]
            else:
                bundle["request"]["public_key"] = "request-controlled-key"
            with self.assertRaises(ProtectedRequestRefused):
                self.verify(bundle)

    def test_unknown_operation_is_refused_even_when_signed(self):
        request = {**self.bundle["request"], "operation": "technical_admin.recover"}
        with self.assertRaises(ProtectedRequestRefused):
            self.verify(sign_fixture(request, self.trust, self.keys))

    def test_permission_expansion_or_reordering_is_refused(self):
        for codes in ([], ["access_control.everything"], list(reversed(self.bundle["request"]["permission_codes"]))):
            with self.assertRaises(ProtectedRequestRefused):
                self.verify(sign_fixture({**self.bundle["request"], "permission_codes": codes}, self.trust, self.keys))

    def test_exact_expiry_is_refused(self):
        with self.assertRaises(ProtectedRequestRefused):
            self.verify(now=self.now + 60)

    def test_future_issued_request_is_refused(self):
        with self.assertRaises(ProtectedRequestRefused):
            self.verify(now=self.now - 1)

    def test_extended_lifetime_is_refused(self):
        request = {**self.bundle["request"], "expires_at": self.now + 121}
        with self.assertRaises(ProtectedRequestRefused):
            self.verify(sign_fixture(request, self.trust, self.keys))

    def test_stale_trust_refused(self):
        with self.assertRaises(ProtectedRequestRefused):
            self.verify(trust=replace(self.trust, valid_until=self.now))

    def test_long_lived_trust_refused(self):
        with self.assertRaises(ProtectedRequestRefused):
            self.verify(trust=replace(self.trust, valid_until=self.now + 301))

    def test_epoch_revocation_refused(self):
        with self.assertRaises(ProtectedRequestRefused):
            self.verify(trust=replace(self.trust, epoch=2))

    def test_removed_key_refused(self):
        with self.assertRaises(ProtectedRequestRefused):
            self.verify(trust=replace(self.trust, signers=self.trust.signers[:-1]))

    def test_duplicate_person_or_public_key_refused(self):
        for field in ("person_id", "public_key", "key_id"):
            signers = (self.trust.signers[0], replace(self.trust.signers[1], **{field: getattr(self.trust.signers[0], field)}), self.trust.signers[2])
            with self.subTest(field=field), self.assertRaises(ProtectedRequestRefused):
                self.verify(trust=replace(self.trust, signers=signers))

    def test_missing_duplicate_and_extra_signatures_refused(self):
        for signatures in (self.bundle["signatures"][:2], self.bundle["signatures"] * 2,
                           [self.bundle["signatures"][0]] * 3):
            with self.assertRaises(ProtectedRequestRefused):
                self.verify({**self.bundle, "signatures": signatures})

    def test_actor_key_is_bound_to_account(self):
        signers = (replace(self.trust.signers[0], account_id=2), *self.trust.signers[1:])
        with self.assertRaises(ProtectedRequestRefused):
            self.verify(trust=replace(self.trust, signers=signers))

    def test_substituted_key_and_invalid_signature_refused(self):
        bundle = deepcopy(self.bundle)
        bundle["signatures"][0]["signature"] = "0" * 128
        with self.assertRaises(ProtectedRequestRefused):
            self.verify(bundle)

    def test_booleans_are_not_integer_identifiers_or_epochs(self):
        for field in ("actor_id", "version", "epoch", "issued_at", "expires_at"):
            with self.subTest(field=field), self.assertRaises(ProtectedRequestRefused):
                self.verify(sign_fixture({**self.bundle["request"], field: True}, self.trust, self.keys))

    def test_oversized_and_non_json_evidence_refused(self):
        for value in ({"padding": "a" * 32769}, {"nan": float("nan")}, {"object": object()}):
            with self.assertRaises(ProtectedRequestRefused):
                canonical(value)

    def test_bootstrap_self_target_and_provision_target_refused(self):
        for operation in ("technical_role.provision", "technical_admin.bootstrap"):
            request = {**self.bundle["request"], "operation": operation, "target_id": 1}
            with self.assertRaises(ProtectedRequestRefused):
                self.verify(sign_fixture(request, self.trust, self.keys))

    def test_error_does_not_include_submitted_evidence(self):
        with self.assertRaises(ProtectedRequestRefused) as caught:
            self.verify({"secret": "DO-NOT-EXPOSE"})
        self.assertNotIn("DO-NOT-EXPOSE", str(caught.exception))


class ReleaseAcceptanceTests(SimpleTestCase):
    def test_offline_report_cannot_claim_release(self):
        output = StringIO()
        call_command("report_task2_acceptance", stdout=output)
        self.assertIn('"verdict": "INCOMPLETE"', output.getvalue())
        with self.assertRaises(CommandError):
            call_command("report_task2_acceptance", require_release=True, stdout=StringIO())

    @override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True)
    def test_gate_alone_cannot_pass_deployment(self):
        self.assertEqual(["access_control.E202"], [e.id for e in protected_executor_release_checks(None)])

    def test_default_and_malformed_gate_block_deployment(self):
        for value in (False, "true", 1, None):
            with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=value):
                self.assertEqual(["access_control.E201", "access_control.E202"],
                                 [e.id for e in protected_executor_release_checks(None)])
