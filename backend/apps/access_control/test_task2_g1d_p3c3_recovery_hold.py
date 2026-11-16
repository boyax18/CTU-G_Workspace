"""G1D-P3C3 no-DB, synthetic crash/restore hold tests."""

from dataclasses import replace
from unittest import TestCase
from uuid import uuid4

from apps.access_control.tests_support.g1d_p3c3_recovery_hold_test_only import (
    OPERATIONAL_EVIDENCE, RecoveryRefused, SyntheticRecoveryFacts,
    operational_release_triage, triage_recovery,
)


class RecoveryHoldContractTests(TestCase):
    def setUp(self):
        self.clean = SyntheticRecoveryFacts(
            schema="test_ctug_registration_0123456789abcdef",
            incarnation=str(uuid4()), request_id=str(uuid4()),
            status="Ready", resolution="NOT_COMMITTED",
            execution_reservations=0, consumption_events=0,
            attached_role_ids=(), attached_audit_ids=(),
            role_is_inactive=None, before_state_matches=True,
            after_state_matches=None, independent_receipt_matches=None,
            trust_epoch_consistent=True,
        )

    def check_hold(self, facts, issue=None):
        decision = triage_recovery(facts)
        self.assertEqual(decision.release_status, "BLOCKED")
        self.assertFalse(decision.allow_retry)
        self.assertFalse(decision.allow_provisioning)
        if issue:
            self.assertIn(issue, decision.issues)
        return decision

    def test_no_mutation_observed_never_grants_retry(self):
        self.assertEqual(self.check_hold(self.clean).classification, "SYNTHETIC_NO_MUTATION_OBSERVED")

    def test_attempted_not_committed_never_grants_retry(self):
        facts = replace(self.clean, status="Attempted", execution_reservations=1)
        self.check_hold(facts, "ATTEMPTED_OUTCOME_REQUIRES_RECONCILIATION")

    def test_unknown_commit_must_hold(self):
        self.check_hold(replace(self.clean, resolution="UNKNOWN"), "TRANSACTION_OUTCOME_UNKNOWN")

    def test_attempted_unknown_even_with_matching_before_state_holds(self):
        self.check_hold(replace(self.clean, status="Attempted", execution_reservations=1,
                                resolution="UNKNOWN"), "EXECUTION_RESERVED_NEVER_RETRY")

    def test_valid_synthetic_consumed_observation_cannot_authorize(self):
        committed = replace(self.clean, status="Consumed", resolution="COMMITTED",
                            execution_reservations=1, consumption_events=1,
                            attached_role_ids=(16,), attached_audit_ids=(4,),
                            role_is_inactive=True, before_state_matches=None,
                            after_state_matches=True, independent_receipt_matches=True)
        decision = self.check_hold(committed, "EXECUTION_RESERVED_NEVER_RETRY")
        self.assertEqual(decision.classification, "SYNTHETIC_COMMIT_COHERENT")

    def test_committed_requires_consumption_event(self):
        self.check_hold(replace(self.clean, status="Consumed", resolution="COMMITTED",
                                execution_reservations=1), "COMMITTED_REFERENCES_INCOMPLETE")

    def test_committed_requires_inactive_role(self):
        self.check_hold(replace(self.clean, status="Consumed", resolution="COMMITTED",
                                execution_reservations=1, consumption_events=1,
                                attached_role_ids=(1,), attached_audit_ids=(2,),
                                role_is_inactive=False, after_state_matches=True,
                                independent_receipt_matches=True), "COMMITTED_POSTCONDITIONS_UNVERIFIED")

    def test_committed_requires_independent_receipt(self):
        self.check_hold(replace(self.clean, status="Consumed", resolution="COMMITTED",
                                execution_reservations=1, consumption_events=1,
                                attached_role_ids=(1,), attached_audit_ids=(2,),
                                role_is_inactive=True, after_state_matches=True), "INDEPENDENT_RECEIPT_UNVERIFIED")

    def test_committed_conflict_with_not_committed(self):
        self.check_hold(replace(self.clean, status="Consumed"), "CONSUMED_RESOLUTION_CONFLICT")

    def test_nonconsumed_conflict_with_committed(self):
        self.check_hold(replace(self.clean, resolution="COMMITTED"), "CONSUMED_RESOLUTION_CONFLICT")

    def test_nonconsumed_role_reference_refused(self):
        self.check_hold(replace(self.clean, attached_role_ids=(4,)), "UNCONSUMED_REFERENCES_PRESENT")

    def test_nonconsumed_audit_reference_refused(self):
        self.check_hold(replace(self.clean, attached_audit_ids=(4,)), "UNCONSUMED_REFERENCES_PRESENT")

    def test_nonconsumed_receipt_conflict_refused(self):
        self.check_hold(replace(self.clean, independent_receipt_matches=True), "UNCONSUMED_RECEIPT_CONFLICT")

    def test_nonconsumed_postconditions_conflict_refused(self):
        self.check_hold(replace(self.clean, role_is_inactive=True), "UNCONSUMED_POSTCONDITION_CONFLICT")

    def test_before_state_not_verified_holds(self):
        self.check_hold(replace(self.clean, before_state_matches=None), "BEFORE_STATE_NOT_VERIFIED")

    def test_expired_trust_epoch_holds(self):
        self.check_hold(replace(self.clean, trust_epoch_consistent=False), "TRUST_EPOCH_NOT_VERIFIED")

    def test_unknown_trust_epoch_holds(self):
        self.check_hold(replace(self.clean, trust_epoch_consistent=None), "TRUST_EPOCH_NOT_VERIFIED")

    def test_attempted_without_reservation_refused(self):
        self.check_hold(replace(self.clean, status="Attempted"), "ATTEMPTED_RESERVATION_MISSING")

    def test_cancelled_but_reserved_refused(self):
        self.check_hold(replace(self.clean, status="Cancelled", execution_reservations=1), "RESERVATION_STATE_CONFLICT")

    def test_stale_schema_rejected(self):
        with self.assertRaises(RecoveryRefused):
            triage_recovery(replace(self.clean, schema="ctug_workspace"))

    def test_wrong_incarnation_format_rejected(self):
        with self.assertRaises(RecoveryRefused):
            triage_recovery(replace(self.clean, incarnation="production"))

    def test_wrong_request_uuid_rejected(self):
        with self.assertRaises(RecoveryRefused):
            triage_recovery(replace(self.clean, request_id="001"))

    def test_unknown_status_rejected(self):
        with self.assertRaises(RecoveryRefused):
            triage_recovery(replace(self.clean, status="Retried"))

    def test_bool_cannot_be_int_count(self):
        with self.assertRaises(RecoveryRefused):
            triage_recovery(replace(self.clean, execution_reservations=True))

    def test_negative_count_rejected(self):
        with self.assertRaises(RecoveryRefused):
            triage_recovery(replace(self.clean, consumption_events=-1))

    def test_unbounded_count_rejected(self):
        with self.assertRaises(RecoveryRefused):
            triage_recovery(replace(self.clean, execution_reservations=2))

    def test_multiple_role_references_rejected(self):
        with self.assertRaises(RecoveryRefused):
            triage_recovery(replace(self.clean, attached_role_ids=(1, 2)))

    def test_string_boolean_rejected(self):
        with self.assertRaises(RecoveryRefused):
            triage_recovery(replace(self.clean, independent_receipt_matches="True"))

    def test_nondata_object_refused(self):
        with self.assertRaises(RecoveryRefused):
            triage_recovery({"status": "Ready"})

    def test_operational_missing_all_remains_blocked(self):
        result = operational_release_triage({name: False for name in OPERATIONAL_EVIDENCE})
        self.assertEqual(len(result["missing_evidence_categories"]), len(OPERATIONAL_EVIDENCE))
        self.assertEqual(result["release_status"], "BLOCKED")

    def test_operational_partial_evidence_remains_blocked(self):
        inputs = {name: False for name in OPERATIONAL_EVIDENCE}
        inputs[OPERATIONAL_EVIDENCE[0]] = True
        result = operational_release_triage(inputs)
        self.assertEqual(result["claimed_complete_count"], 1)
        self.assertEqual(result["release_status"], "BLOCKED")

    def test_operational_all_self_reported_still_blocked(self):
        result = operational_release_triage({name: True for name in OPERATIONAL_EVIDENCE})
        self.assertEqual(result["claimed_complete_count"], len(OPERATIONAL_EVIDENCE))
        self.assertEqual(result["release_status"], "BLOCKED")
        self.assertFalse(result["independent_attestation_verified"])

    def test_operational_missing_key_rejected(self):
        with self.assertRaises(RecoveryRefused):
            operational_release_triage({})

    def test_operational_unknown_key_rejected(self):
        with self.assertRaises(RecoveryRefused):
            operational_release_triage({**{name: True for name in OPERATIONAL_EVIDENCE}, "oops": True})

    def test_operational_string_flag_rejected(self):
        with self.assertRaises(RecoveryRefused):
            operational_release_triage({name: "true" for name in OPERATIONAL_EVIDENCE})

    def test_structures_provide_no_write_permission(self):
        decision = self.check_hold(self.clean)
        self.assertNotIn(True, (decision.allow_retry, decision.allow_provisioning))
        self.assertEqual("BLOCKED", decision.release_status)
