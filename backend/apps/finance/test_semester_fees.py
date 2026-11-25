"""Semester organizational fee configuration: Draft, approval, revisions, HDAC and WF-11.01 integration.

Run: python manage.py test apps.finance.test_semester_fees --settings=config.test_settings --noinput
Disposable MySQL only. The pinned v2.2 default (Treasurer -> finance.fee_schedule.manage) is reproduced;
the success path uses an EXPLICIT test-only Admin -> finance.fee_schedule.manage binding created in the
throwaway database (``grant_admin_fee``). It is never an application grant.
"""

import threading
from decimal import Decimal
from unittest.mock import patch

from django.apps import apps as django_apps
from django.core.cache import cache
from django.db import IntegrityError, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.academic import configuration as cfg
from apps.academic import lifecycle, services
from apps.academic.models import Semester
from apps.academic.test_academic_configuration import CONFIG, ConfigWorld, build_plan
from apps.academic.test_wf1101_http import post, signed_in
from apps.access_control.models import AccountPermission, AccountRole, Permission, RolePermission, Service
from apps.accounts.active_role_context import bind_role_scope

from . import fees
from .models import FinanceAuditLog, SemesterFeeRevision, SemesterFeeSchedule

FEES = dict(CONFIG, WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED=True, WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED=True)
REASON = "Student council resolution revised the semester fee."
CODE = "finance.fee_schedule.manage"


class FeeWorld(ConfigWorld):
    """ConfigWorld + finance service and the PINNED v2.2 binding: Treasurer -> finance.fee_schedule.manage."""

    def __init__(self):
        super().__init__()
        self.finance = Service.objects.create(service_code="finance", service_name="SSG Finance")
        self.fee_perm = Permission.objects.create(service=self.finance, permission_code=CODE, permission_name=CODE,
                                                  module_name="fee_schedule", action_name="manage")
        RolePermission.objects.create(role=self.roles["Treasurer"], permission=self.fee_perm)  # pinned default
        self.treasurer = self.account("WF1101-TREAS", "Treasurer")

    def grant_admin_fee(self):
        """TEST ONLY (throwaway database): the binding a reviewed post-v2.2 overlay would add."""
        return RolePermission.objects.get_or_create(role=self.roles["Admin"], permission=self.fee_perm)[0]


def other_counts():
    """Every installed model outside academic/finance: no participation, obligation, clearance or payment rows."""
    return {m._meta.label: m.objects.count() for m in django_apps.get_models()
            if m._meta.app_label not in ("academic", "finance") and m._meta.managed}


@override_settings(**FEES)
class FeeServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = FeeWorld()
        cls.w.grant_admin_fee()

    def setUp(self):
        year = services.create_school_year(actor=self.w.admin, start_year=2026)
        self.first, self.second = (s["semester_id"] for s in year["semesters"])

    def draft(self, amount="1500.00", expected=None, reason=None, semester=None):
        return fees.save_draft(actor=self.w.admin, semester_id=semester or self.first, amount=amount,
                               expected_draft_version=expected, change_reason=reason)

    def approve(self, semester=None, zero=False, **overrides):
        preview = fees.approval_preview(actor=self.w.admin, semester_id=semester or self.first)
        current = preview["current_approved"]
        kwargs = dict(actor=self.w.admin, semester_id=semester or self.first, revision_id=preview["proposed"]["revision_id"],
                      expected_version=preview["proposed"]["version"],
                      expected_current_approved_revision_id=current["revision_id"] if current else None,
                      acknowledged_warnings=preview["warnings"], confirmed=True, confirm_zero_amount=zero)
        kwargs.update(overrides)
        return fees.approve(**kwargs)

    def conflict(self, expected_reason, fn, *args, **kwargs):
        before = (list(SemesterFeeRevision.objects.values().order_by("pk")), FinanceAuditLog.objects.count())
        with self.assertRaises(fees.FeeConflict) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, expected_reason)
        self.assertEqual(before, (list(SemesterFeeRevision.objects.values().order_by("pk")), FinanceAuditLog.objects.count()))

    def readiness(self, semester=None):
        return fees.fee_readiness(Semester.objects.get(pk=semester or self.first)).as_dict()

    def test_draft_is_saved_exactly_and_never_approves(self):
        others = other_counts()
        self.assertEqual(self.readiness(), {"key": "approved_fee", "status": "missing", "reason": "no_fee_configured"})
        state = self.draft("1500.5")
        self.assertEqual((state["state"], state["draft"]["amount"], state["draft"]["currency"], state["current_approved"]),
                         ("draft", "1500.50", "PHP", None))
        self.assertEqual(self.readiness()["reason"], "fee_awaiting_approval")
        audit = FinanceAuditLog.objects.get()
        self.assertEqual((audit.actor_account_id, audit.action, audit.semester_id, audit.new_value["amount"]),
                         (self.w.admin.pk, "finance.semester_fee.draft.create", self.first, "1500.50"))
        self.conflict("draft_exists", self.draft, "1600.00")
        self.conflict("stale_version", self.draft, "1600.00", expected=9)
        self.conflict("no_change", self.draft, "1500.50", expected=1)
        state = self.draft("1600", expected=1)
        self.assertEqual((state["draft"]["amount"], state["draft"]["version"]), ("1600.00", 2))
        self.assertEqual(other_counts(), others)  # no obligation, clearance or payment record of any kind

    def test_amount_validation_is_exact_and_bounded(self):
        for bad in ("-1", "1500.001", "abc", "1,500", "1e3", " ", "", None, 1.5, True, "1000000", "100000.01", ["1"]):
            with self.subTest(amount=bad), self.assertRaises(services.AcademicPeriodInvalid) as caught:
                self.draft(bad)
            self.assertIn("amount", caught.exception.fields)
        self.assertEqual(SemesterFeeRevision.objects.count(), 0)
        self.assertEqual(self.draft("100000.00")["draft"]["amount"], "100000.00")
        self.assertEqual(self.draft(0, semester=self.second)["draft"]["amount"], "0.00")  # zero is a value, not "missing"

    def test_database_enforces_one_schedule_one_approved_and_bounds(self):
        self.draft("500")
        schedule = SemesterFeeSchedule.objects.get()
        with self.assertRaises(IntegrityError), transaction.atomic():
            SemesterFeeSchedule.objects.create(semester_id=self.first, created_by=self.w.admin)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SemesterFeeRevision.objects.create(schedule=schedule, revision_number=2, amount=Decimal("1.00"), draft_slot=1,
                                               configured_by=self.w.admin)  # a second open Draft
        with self.assertRaises(IntegrityError), transaction.atomic():
            SemesterFeeRevision.objects.filter(schedule=schedule).update(amount=Decimal("-1.00"))
        with self.assertRaises(IntegrityError), transaction.atomic():  # a Draft claiming approval
            SemesterFeeRevision.objects.filter(schedule=schedule).update(approved_at=timezone.now(), approved_by=self.w.admin)
        self.approve()
        with self.assertRaises(IntegrityError), transaction.atomic():
            SemesterFeeRevision.objects.create(schedule=schedule, revision_number=3, amount=Decimal("1.00"), status="Approved",
                                               approved_slot=1, approved_at=timezone.now(), approved_by=self.w.admin,
                                               configured_by=self.w.admin)  # a second current approved rate

    def test_explicit_approval_and_zero_requires_its_own_confirmation(self):
        self.draft("1500")
        preview = fees.approval_preview(actor=self.w.admin, semester_id=self.first)
        self.assertEqual((preview["can_confirm"], preview["warnings"], preview["impact"]["status"]),
                         (True, [], "not_applicable"))
        self.conflict("confirmation_required", self.approve, confirmed="yes")
        self.conflict("stale_version", self.approve, expected_version=7)
        self.conflict("warnings_changed", self.approve, acknowledged_warnings=["zero_amount"])
        self.conflict("approved_changed", self.approve, expected_current_approved_revision_id=99)
        state = self.approve()
        self.assertEqual((state["state"], state["current_approved"]["amount"], state["current_approved"]["approved_by"]),
                         ("approved", "1500.00", "You"))
        self.assertEqual(self.readiness(), {"key": "approved_fee", "status": "ready", "reason": ""})
        self.assertEqual(Semester.objects.get(pk=self.first).status, "Draft")  # approval never activates
        # ₱0.00 is valid only when entered AND approved explicitly.
        self.draft("0.00", semester=self.second)
        self.assertIn("zero_amount", fees.approval_preview(actor=self.w.admin, semester_id=self.second)["warnings"])
        self.conflict("zero_confirmation_required", self.approve, semester=self.second)
        self.approve(semester=self.second, zero=True)
        self.assertEqual(self.readiness(self.second)["status"], "ready")
        audit = FinanceAuditLog.objects.filter(action="finance.semester_fee.approve", semester_id=self.second).get()
        self.assertIs(audit.new_value["zero_amount_confirmed"], True)

    def test_revisions_keep_history_and_need_a_reason(self):
        self.draft("1500")
        first = self.approve()["current_approved"]
        self.conflict("reason_required", self.draft, "1750")
        self.conflict("no_change", self.draft, "1500", reason=REASON)
        self.draft("1750", reason=REASON)
        self.assertEqual(self.readiness()["status"], "ready")  # the approved rate stays current while drafting
        preview = fees.approval_preview(actor=self.w.admin, semester_id=self.first)
        self.assertEqual((preview["current_approved"]["amount"], preview["proposed"]["amount"]), ("1500.00", "1750.00"))
        self.assertEqual(preview["impact"], {"status": "not_applicable", "count": None, "reason": "semester_never_active"})
        state = self.approve()
        self.assertEqual([(r["revision_number"], r["amount"], r["status"]) for r in state["revisions"]],
                         [(2, "1750.00", "Approved"), (1, "1500.00", "Superseded")])
        old = SemesterFeeRevision.objects.get(pk=first["revision_id"])
        self.assertEqual((old.amount, old.status, old.approved_by_id), (Decimal("1500.00"), "Superseded", self.w.admin.pk))
        self.assertEqual(SemesterFeeRevision.objects.filter(status="Approved").count(), 1)
        self.assertEqual(SemesterFeeSchedule.objects.get().current_approved_revision_id, state["current_approved"]["revision_id"])

    def test_withdrawn_drafts_are_kept_and_closed_periods_are_refused(self):
        self.draft("900")
        state = fees.withdraw_draft(actor=self.w.admin, semester_id=self.first, expected_draft_version=1)
        self.assertEqual((state["state"], state["revisions"][0]["status"]), ("not_configured", "Withdrawn"))
        self.assertEqual(self.readiness()["reason"], "no_fee_configured")
        self.draft("950")  # a new Draft revision number 2
        self.assertEqual(SemesterFeeRevision.objects.order_by("revision_number").values_list("revision_number", "status")[1],
                         (2, "Draft"))
        Semester.objects.filter(pk=self.second).update(status="Closed", activated_at=timezone.now(), closed_at=timezone.now(),
                                                       start_date="2027-01-11", end_date="2027-05-28")
        self.conflict("period_closed", self.draft, "100", semester=self.second)
        with self.assertRaises(services.AcademicPeriodNotFound):
            self.draft("100", semester=999_999)

    def test_failed_approval_rolls_back_state_and_audit(self):
        self.draft("1500")
        before = (list(SemesterFeeRevision.objects.values().order_by("pk")), list(SemesterFeeSchedule.objects.values()))
        with patch.object(fees, "_audit", side_effect=RuntimeError("audit down")), self.assertRaises(RuntimeError):
            self.approve()
        self.assertEqual(before, (list(SemesterFeeRevision.objects.values().order_by("pk")), list(SemesterFeeSchedule.objects.values())))
        self.assertEqual(self.readiness()["reason"], "fee_awaiting_approval")

    def test_gates_and_finance_service(self):
        import config.settings as base
        self.assertIs(base.WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED, False)
        self.assertIs(base.WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED, False)
        self.draft("1500")
        with override_settings(WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED=False):
            preview = fees.approval_preview(actor=self.w.admin, semester_id=self.first)
            self.assertEqual((preview["feature_enabled"], preview["can_confirm"]), (False, False))
            with self.assertRaises(services.AcademicPeriodFeatureDisabled):
                self.approve()
        with override_settings(WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED=False):
            with self.assertRaises(services.AcademicPeriodUnavailable):
                fees.list_semester_fees(actor=self.w.admin)
            self.assertEqual(self.readiness()["reason"], "fee_source_disabled")
        self.assertFalse(lifecycle.transitions_enabled())  # fee switches never enable transitions
        Service.objects.filter(pk=self.w.finance.pk).update(is_active=False)
        self.assertEqual(self.readiness()["reason"], "finance_service_inactive")
        with self.assertRaises(services.AcademicPeriodDenied):  # inactive service: the code is not effective
            fees.get_semester_fee(actor=self.w.admin, semester_id=self.first)

    def test_inconsistent_approval_evidence_is_never_ready(self):
        self.draft("1500")
        self.approve()
        SemesterFeeSchedule.objects.update(current_approved_revision=None)
        self.assertEqual(self.readiness()["reason"], "no_fee_configured")
        revision = SemesterFeeRevision.objects.get()
        SemesterFeeSchedule.objects.update(current_approved_revision=revision)
        with patch.object(fees, "_validated_current", return_value=None):
            self.assertEqual(self.readiness(), {"key": "approved_fee", "status": "unavailable",
                                                "reason": "approved_fee_inconsistent"})


@override_settings(**FEES)
class FeeAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = FeeWorld()

    def setUp(self):
        year = services.create_school_year(actor=self.w.admin, start_year=2026)
        self.first = year["semesters"][0]["semester_id"]

    def denied(self, actor, reason="access_denied"):
        with self.assertRaises(services.AcademicPeriodDenied) as caught:
            fees.save_draft(actor=actor, semester_id=self.first, amount="1500", expected_draft_version=None)
        self.assertEqual(caught.exception.reason, reason)
        with self.assertRaises(services.AcademicPeriodDenied):
            fees.get_semester_fee(actor=actor, semester_id=self.first)
        self.assertEqual((SemesterFeeRevision.objects.count(), FinanceAuditLog.objects.count()), (0, 0))

    def test_pinned_defaults_refuse_school_admin_and_treasurer(self):
        self.denied(self.w.admin)        # no Admin -> fee binding in the pinned catalogue
        self.denied(self.w.treasurer)    # Treasurer holds the legacy default but is not School Admin
        dual = self.w.account("WF1101-FDUAL", "Treasurer", "Admin")
        self.denied(dual)                # the code reaches it only through the Treasurer role
        for role in ("Student", "Instructor"):
            self.denied(self.w.account(f"WF1101-F{role[:3].upper()}", role))

    def test_direct_grant_alone_never_authorizes(self):
        AccountPermission.objects.create(account=self.w.admin, permission=self.w.fee_perm, effect="Grant")
        self.denied(self.w.admin)

    def test_admin_binding_succeeds_and_deny_wins(self):
        self.w.grant_admin_fee()
        fees.save_draft(actor=self.w.admin, semester_id=self.first, amount="1500", expected_draft_version=None)
        AccountPermission.objects.create(account=self.w.admin, permission=self.w.fee_perm, effect="Deny")
        with self.assertRaises(services.AcademicPeriodDenied):
            fees.get_semester_fee(actor=self.w.admin, semester_id=self.first)

    def test_technical_super_admin_only_through_a_genuine_admin_assignment(self):
        self.w.grant_admin_fee()
        tsa = self.w.account("WF1101-FTSA", "Technical Super Admin")
        RolePermission.objects.create(role=self.w.roles["Technical Super Admin"], permission=self.w.fee_perm)
        self.denied(tsa)
        AccountRole.objects.create(account=tsa, role=self.w.roles["Admin"])
        fees.save_draft(actor=tsa, semester_id=self.first, amount="1500", expected_draft_version=None)

    @override_settings(WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True)
    def test_selected_admin_context_is_required(self):
        self.w.grant_admin_fee()
        dual = self.w.account("WF1101-FCTX", "Treasurer", "Admin")
        for role_id in (self.w.roles["Treasurer"].pk, None, 999_999):
            with self.subTest(role_id=role_id), bind_role_scope(dual.pk, role_id):
                self.denied(dual, reason="admin_context_required")
        with bind_role_scope(self.w.admin.pk, self.w.roles["Admin"].pk):
            self.denied(dual, reason="admin_context_required")  # another account's scope
        with bind_role_scope(dual.pk, self.w.roles["Admin"].pk):
            fees.save_draft(actor=dual, semester_id=self.first, amount="1500", expected_draft_version=None)
        self.assertEqual(FinanceAuditLog.objects.get().acting_role_id, self.w.roles["Admin"].pk)

    def test_permission_revoked_between_precheck_and_lock_is_refused(self):
        binding = self.w.grant_admin_fee()
        real = services.authorize
        calls = []

        def revoke(actor, *args, **kwargs):
            result = real(actor, *args, **kwargs)
            calls.append(1)
            if len(calls) == 1:
                RolePermission.objects.filter(pk=binding.pk).update(is_active=False)
            return result

        with patch.object(services, "authorize", side_effect=revoke):
            with self.assertRaises(services.AcademicPeriodDenied):
                fees.save_draft(actor=self.w.admin, semester_id=self.first, amount="1500", expected_draft_version=None)
        self.assertEqual(SemesterFeeRevision.objects.count(), 0)

    def test_readiness_needs_only_the_activation_permission(self):
        # The academic activation actor reads readiness without holding any fee-setting authority.
        result = fees.readiness_for_activation(actor=self.w.admin, semester_id=self.first)
        self.assertEqual(result["readiness"]["reason"], "no_fee_configured")
        with self.assertRaises(services.AcademicPeriodDenied):
            fees.readiness_for_activation(actor=self.w.treasurer, semester_id=self.first)


@override_settings(**FEES, WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED=True)
class ActivationIntegrationTests(TestCase):
    """Real records end to end: dates + real offering + real approved fee -> real activation."""

    @classmethod
    def setUpTestData(cls):
        cls.w = FeeWorld()
        cls.w.grant_admin_fee()

    def setUp(self):
        self.p = build_plan(self.w)
        self.first = self.p["first"]
        services.update_semester_dates(actor=self.w.admin, semester_id=self.first, start_date="2026-08-10",
                                       end_date="2026-12-18", expected_version=1)
        cfg.create_offering(actor=self.w.admin, semester_id=self.first, section_id=self.p["section"]["section_id"],
                            curriculum_subject_id=self.p["entries"]["MATH 101"])

    def prerequisites(self):
        preview = lifecycle.activation_preview(actor=self.w.admin, semester_id=self.first)
        return preview, {c["key"]: (c["status"], c["reason"]) for c in preview["prerequisites"]}

    def approve_fee(self, amount, zero=False):
        fees.save_draft(actor=self.w.admin, semester_id=self.first, amount=amount, expected_draft_version=None)
        preview = fees.approval_preview(actor=self.w.admin, semester_id=self.first)
        fees.approve(actor=self.w.admin, semester_id=self.first, revision_id=preview["proposed"]["revision_id"],
                     expected_version=preview["proposed"]["version"], expected_current_approved_revision_id=None,
                     acknowledged_warnings=preview["warnings"], confirmed=True, confirm_zero_amount=zero)

    def activate(self, preview):
        return lifecycle.activate_semester(actor=self.w.admin, semester_id=self.first,
                                           expected_version=preview["semester"]["version"], expected_active_semester_id=None,
                                           acknowledged_warnings=preview["warnings"], confirmed=True)

    def test_missing_and_draft_fees_block_activation(self):
        preview, checks = self.prerequisites()
        self.assertEqual(checks["approved_fee"], ("missing", "no_fee_configured"))
        self.assertEqual(checks["academic_offerings"], ("ready", ""))
        fees.save_draft(actor=self.w.admin, semester_id=self.first, amount="1500", expected_draft_version=None)
        preview, checks = self.prerequisites()
        self.assertEqual(checks["approved_fee"], ("missing", "fee_awaiting_approval"))
        with self.assertRaises(lifecycle.TransitionRefused) as caught:
            self.activate(preview)
        self.assertEqual(caught.exception.missing, ("approved_fee",))

    def test_approved_fee_and_real_offerings_allow_a_real_activation(self):
        others = other_counts()
        self.approve_fee("1500.00")
        self.assertEqual(Semester.objects.get(pk=self.first).status, "Draft")  # approval alone never activates
        preview, checks = self.prerequisites()
        self.assertEqual(set(checks.values()), {("ready", "")})
        self.assertTrue(preview["can_confirm"], preview)
        result = self.activate(preview)  # no substitute dependency bundle: real persisted sources only
        self.assertEqual(result["status"], "Active")
        self.assertEqual(other_counts(), others)  # no participation, obligation, clearance or receipt created

    def test_approved_zero_fee_satisfies_the_fee_prerequisite(self):
        self.approve_fee("0", zero=True)
        _preview, checks = self.prerequisites()
        self.assertEqual(checks["approved_fee"], ("ready", ""))

    def test_offerings_remain_required_with_an_approved_fee(self):
        self.approve_fee("1500")
        cfg.set_section_status(actor=self.w.admin, section_id=self.p["section"]["section_id"], status="Inactive",
                               expected_version=1)
        _preview, checks = self.prerequisites()
        self.assertEqual((checks["approved_fee"][0], checks["academic_offerings"][0]), ("ready", "missing"))

    def test_consequential_revision_of_an_active_semester_fails_closed(self):
        self.approve_fee("1500")
        preview, _checks = self.prerequisites()
        self.activate(preview)
        state = fees.save_draft(actor=self.w.admin, semester_id=self.first, amount="1800", expected_draft_version=None,
                                change_reason=REASON)  # a Draft is still safe to save
        self.assertEqual(state["state"], "approved_with_draft")
        fee_preview = fees.approval_preview(actor=self.w.admin, semester_id=self.first)
        self.assertIn("impact_unavailable", fee_preview["blockers"])
        self.assertEqual(fee_preview["impact"]["status"], "unavailable")  # never reported as zero
        with self.assertRaises(fees.FeeConflict) as caught:
            fees.approve(actor=self.w.admin, semester_id=self.first, revision_id=fee_preview["proposed"]["revision_id"],
                         expected_version=fee_preview["proposed"]["version"],
                         expected_current_approved_revision_id=fee_preview["current_approved"]["revision_id"],
                         acknowledged_warnings=fee_preview["warnings"], confirmed=True)
        self.assertEqual(caught.exception.reason, "impact_unavailable")

        class Assessed:
            def evaluate(self, semester, current):
                return {"status": "evaluated", "count": 12, "reason": ""}

        with fees.isolated_impact(Assessed()):
            self.assertIn("obligations_assessed", fees.approval_preview(actor=self.w.admin, semester_id=self.first)["blockers"])
        self.assertEqual(SemesterFeeRevision.objects.get(status="Approved").amount, Decimal("1500.00"))


class FeeConcurrencyTests(TransactionTestCase):
    def tearDown(self):
        connections.close_all()

    def race(self, *calls):
        barrier = threading.Barrier(len(calls))
        results = [None] * len(calls)

        def run(index, fn):
            try:
                barrier.wait(5)
                results[index] = ("ok", fn())
            except Exception as exc:  # noqa: BLE001 - reported to the test
                results[index] = ("error", exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=run, args=(i, fn)) for i, fn in enumerate(calls)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
        return results

    @override_settings(**FEES)
    def test_concurrent_drafts_and_approvals_leave_one_current_rate(self):
        w = FeeWorld()
        w.grant_admin_fee()
        semester = services.create_school_year(actor=w.admin, start_year=2026)["semesters"][0]["semester_id"]
        results = self.race(*[
            (lambda amount=amount: fees.save_draft(actor=w.admin, semester_id=semester, amount=amount,
                                                   expected_draft_version=None)) for amount in ("1000", "2000")])
        self.assertEqual(sum(r[0] == "ok" for r in results), 1, results)
        self.assertTrue(all(isinstance(r[1], fees.FeeConflict) and r[1].reason == "draft_exists"
                            for r in results if r[0] == "error"))
        preview = fees.approval_preview(actor=w.admin, semester_id=semester)
        approve = lambda: fees.approve(actor=w.admin, semester_id=semester, revision_id=preview["proposed"]["revision_id"],  # noqa: E731
                                       expected_version=preview["proposed"]["version"],
                                       expected_current_approved_revision_id=None,
                                       acknowledged_warnings=preview["warnings"], confirmed=True)
        results = self.race(approve, approve)
        self.assertEqual(sum(r[0] == "ok" for r in results), 1, results)
        self.assertEqual(SemesterFeeRevision.objects.filter(status="Approved").count(), 1)
        self.assertEqual(FinanceAuditLog.objects.filter(action="finance.semester_fee.approve").count(), 1)


@override_settings(**FEES)
class FeeHTTPTests(TestCase):
    ROOT = "/api/v1/finance/semester-fees/"

    @classmethod
    def setUpTestData(cls):
        cls.w = FeeWorld()
        cls.w.grant_admin_fee()

    def setUp(self):
        cache.clear()
        self.client = signed_in(self.w.admin)
        self.first = services.create_school_year(actor=self.w.admin, start_year=2026)["semesters"][0]["semester_id"]

    def test_draft_preview_approval_history_and_readiness_over_http(self):
        listing = self.client.get(self.ROOT)
        self.assertEqual(listing.status_code, 200, listing.content)
        self.assertEqual(listing.json()["features"], {"configuration": True, "approval": True})
        reply = post(self.client, f"{self.ROOT}{self.first}/draft/", {"amount": "1500.00", "expected_draft_version": None})
        self.assertEqual(reply.status_code, 200, reply.content)
        preview = self.client.get(f"{self.ROOT}{self.first}/approval/").json()
        reply = post(self.client, f"{self.ROOT}{self.first}/approval/", {
            "revision_id": preview["proposed"]["revision_id"], "expected_version": preview["proposed"]["version"],
            "expected_current_approved_revision_id": None, "acknowledged_warnings": preview["warnings"], "confirmed": True})
        self.assertEqual((reply.status_code, reply.json()["state"]), (200, "approved"), reply.content)
        history = self.client.get(f"{self.ROOT}{self.first}/history/").json()["results"]
        self.assertEqual([h["event"] for h in history], ["finance.semester_fee.approve", "finance.semester_fee.draft.create"])
        self.assertNotIn(self.w.admin.school_id, str(history))
        self.assertEqual(self.client.get(f"{self.ROOT}{self.first}/readiness/").json()["readiness"]["status"], "ready")

    def test_errors_and_refusals(self):
        reply = post(self.client, f"{self.ROOT}{self.first}/draft/", {"amount": "", "expected_draft_version": None})
        self.assertEqual(reply.json()["error"]["fields"], {"amount": ["Enter the fee amount. ₱0.00 must be entered explicitly."]})
        reply = post(self.client, f"{self.ROOT}{self.first}/draft/", {"amount": 1500.5, "expected_draft_version": None})
        self.assertEqual(reply.status_code, 400)
        self.assertEqual(post(self.client, f"{self.ROOT}{self.first}/draft/", {"amount": "1"}).status_code, 400)
        post(self.client, f"{self.ROOT}{self.first}/draft/", {"amount": "1", "expected_draft_version": None})
        reply = post(self.client, f"{self.ROOT}{self.first}/draft/", {"amount": "2", "expected_draft_version": None})
        self.assertEqual((reply.status_code, reply.json()["error"]["reason"]), (409, "draft_exists"))
        self.assertEqual(self.client.get(f"{self.ROOT}999999/").status_code, 404)
        treasurer = signed_in(self.w.treasurer)
        self.assertEqual(treasurer.get(self.ROOT).status_code, 403)
        self.assertEqual(post(treasurer, f"{self.ROOT}{self.first}/draft/",
                              {"amount": "1", "expected_draft_version": 1}).status_code, 403)
        self.assertEqual(post(self.client, f"{self.ROOT}{self.first}/draft/", {"amount": "1", "expected_draft_version": 1},
                              csrf=False).status_code, 403)
        with override_settings(WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED=False):
            reply = post(self.client, f"{self.ROOT}{self.first}/approval/", {
                "revision_id": 1, "expected_version": 1, "expected_current_approved_revision_id": None,
                "acknowledged_warnings": [], "confirmed": True})
            self.assertEqual((reply.status_code, reply.json()["error"]["code"]), (503, "feature_disabled"))
        with override_settings(WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED=False, WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED=False):
            for path in ("", f"{self.first}/", f"{self.first}/approval/", f"{self.first}/history/", f"{self.first}/readiness/"):
                reply = self.client.get(self.ROOT + path)
                self.assertEqual((reply.status_code, reply.json()["error"]["code"]), (503, "semester_fees_unavailable"), path)
