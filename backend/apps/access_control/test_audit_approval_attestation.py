"""WF-02.03 D-45: the account-approval audit event's attestation contract (owner-authorized, narrow).

Only "account.registration.approve" may, and must, carry the four flat attestation fields, with a
consistent subject/source pair and an applicant target. Every other event and every old_value keep
the original allowlist. Disposable MySQL only.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.test import TestCase

from .audit import APPROVAL_ACTION, AuditValidationError, record_access_audit
from .models import AccessAuditLog
from .test_audit import fixtures

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Audit tests require --settings=config.test_settings; development data must never be used.")

STUDENT = {
    "email_evidence": "verified", "eligibility_confirmed": True,
    "eligibility_subject": "enrollment", "eligibility_source": "ctu_main_system_records",
}
INSTRUCTOR = {
    "email_evidence": "verified", "eligibility_confirmed": True,
    "eligibility_subject": "employment", "eligibility_source": "institutional_employment_records",
}


class ApprovalAttestationAuditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor, cls.target, cls.role, cls.service, cls.permission = fixtures()

    def snapshot(self, attestation, **extra):
        return {"account_id": self.target.pk, "request_status": "Approved", "role_id": self.role.pk,
                "is_active": True, **attestation, **extra}

    def record(self, action=APPROVAL_ACTION, target="default", **kwargs):
        return record_access_audit(actor=self.actor, action=action,
                                   target=self.target if target == "default" else target, **kwargs)

    def assert_invalid(self, **kwargs):
        with self.assertRaises(AuditValidationError) as captured:
            with transaction.atomic():
                self.record(**kwargs)
        self.assertEqual(AccessAuditLog.objects.count(), 0)
        return str(captured.exception)

    def test_valid_student_and_instructor_attestations_are_recorded(self):
        for attestation in (STUDENT, INSTRUCTOR):
            with self.subTest(source=attestation["eligibility_source"]), transaction.atomic():
                self.record(old_value={"account_id": self.target.pk, "request_status": "Pending"},
                            new_value=self.snapshot(attestation))
        rows = list(AccessAuditLog.objects.order_by("pk"))
        self.assertEqual([r.new_value["eligibility_source"] for r in rows],
                         ["ctu_main_system_records", "institutional_employment_records"])
        for row in rows:
            # Reviewer identity = actor, applicant = target, time = the existing created_at default.
            self.assertEqual(row.actor_account_id, self.actor.pk)
            self.assertEqual(row.target_account_id, self.target.pk)
            self.assertIsNotNone(row.created_at)
            self.assertIs(row.new_value["eligibility_confirmed"], True)
            self.assertEqual(row.new_value["email_evidence"], "verified")

    def test_missing_attestation_or_any_single_field_is_rejected(self):
        self.assert_invalid(new_value=None)
        self.assert_invalid(new_value=self.snapshot({}))
        for field in STUDENT:
            partial = {k: v for k, v in STUDENT.items() if k != field}
            with self.subTest(missing=field):
                self.assertIn("complete eligibility attestation", self.assert_invalid(new_value=self.snapshot(partial)))

    def test_approval_requires_the_applicant_target(self):
        self.assert_invalid(target=None, new_value=self.snapshot(STUDENT))

    def test_malformed_or_forged_values_are_rejected(self):
        forged = [
            ("eligibility_confirmed", False), ("eligibility_confirmed", 1), ("eligibility_confirmed", "true"),
            ("eligibility_confirmed", None), ("email_evidence", "no_proof"), ("email_evidence", "VERIFIED"),
            ("email_evidence", True), ("eligibility_subject", "Enrollment"), ("eligibility_subject", "residency"),
            ("eligibility_source", "applicant_upload"), ("eligibility_source", "Ctu_Main_System_Records"),
            ("eligibility_source", ["ctu_main_system_records"]),
            ("eligibility_source", {"source": "ctu_main_system_records"}),
        ]
        for field, value in forged:
            with self.subTest(field=field, value=value):
                self.assert_invalid(new_value=self.snapshot({**STUDENT, field: value}))

    def test_mismatched_subject_and_source_pairs_are_rejected(self):
        self.assert_invalid(new_value=self.snapshot({**STUDENT, "eligibility_subject": "employment"}))
        self.assert_invalid(new_value=self.snapshot({**INSTRUCTOR, "eligibility_subject": "enrollment"}))

    def test_unrelated_free_text_nested_or_personal_fields_are_rejected(self):
        for extra in ({"attested_at": "2026-11-17T00:00:00"}, {"eligibility_attestation": {"confirmed": True}},
                      {"verified_by_workspace": False}, {"reviewer_note": "checked"}, {"student_number": "123"},
                      {"document_id": 7}, {"email": "a@example.edu"}):
            with self.subTest(extra=next(iter(extra))):
                self.assertIn("unsupported fields", self.assert_invalid(new_value=self.snapshot(STUDENT, **extra)))

    def test_attestation_fields_are_rejected_on_every_other_event(self):
        for action in ("account.registration.reject", "test.audit.record", "access.role.assign"):
            with self.subTest(action=action):
                self.assert_invalid(action=action, new_value=self.snapshot(STUDENT))
        for field, value in STUDENT.items():
            with self.subTest(field=field):
                self.assert_invalid(action="account.registration.reject", new_value={field: value})

    def test_attestation_fields_are_rejected_in_old_value_even_for_approval(self):
        self.assert_invalid(old_value={"request_status": "Pending", **STUDENT}, new_value=self.snapshot(STUDENT))

    def test_other_events_keep_their_original_contract(self):
        with transaction.atomic():
            self.record(action="account.registration.reject",
                        old_value={"request_status": "Pending"},
                        new_value={"request_status": "Rejected", "rejection_code": "incomplete_submission"})
            self.record(action="test.audit.record", target=None, new_value={"is_active": True})
        self.assertEqual(AccessAuditLog.objects.count(), 2)
