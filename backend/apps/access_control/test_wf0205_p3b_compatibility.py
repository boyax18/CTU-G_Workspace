"""WF-02.05 stage 3A: P3B/P4 rollback compatibility with the governed school-account rows (Option A).

Run: python manage.py test apps.access_control.test_wf0205_p3b_compatibility --settings=config.test_settings
Disposable MySQL ONLY. Every state is produced by the real P1, P2, P4 and WF-02.05 code paths; P4
compensation is executed for real where it is permitted and its actual results are checked.
"""

import threading
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections
from django.test import TransactionTestCase, override_settings

from apps.access_control.management.commands import (
    exercise_registration_review_activation_recovery_test_only as p3b,
    init_registration_review_inactive_bindings_local_dev as p2,
    init_registration_review_metadata_local_dev as p1,
    provision_school_accounts_local_dev as s3,
    release_registration_review_local_dev_p4 as p4,
    report_registration_review_release_gates_p3e as p3e,
    transition_registration_review_p3d as p3d,
)
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.services import get_effective_permissions
from apps.accounts.models import Account

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("P3B compatibility tests require the disposable MySQL test settings.")

SCHOOL = set(s3.CODES)
REGISTRATION = set(p1.PERMISSION_CODES)


class P3BCompatibilityTests(TransactionTestCase):
    def setUp(self):
        self.roles = {n: Role.objects.create(role_name=n, is_active=True) for n in ("Admin", "Student")}
        self.actor = self.account("TEST-3A-ADMIN", "Admin")
        self.student = self.account("7270001", "Student")
        self.scope = str(self.actor.pk)

    def tearDown(self):
        connections.close_all()

    def account(self, school_id, *roles):
        account = Account(school_id=school_id, request_status="Approved", is_active=True)
        account.set_unusable_password()
        account.save()
        for role in roles:
            AccountRole.objects.create(account=account, role=self.roles[role])
        return account

    # -- real code paths -------------------------------------------------------------------------
    def p1_p2(self):
        call_command("init_registration_review_metadata_local_dev", apply=True, actor_account_id=self.actor.pk,
                     confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO())
        call_command("init_registration_review_inactive_bindings_local_dev", apply=True, actor_account_id=self.actor.pk,
                     confirm_local_dev_phase2=p2.TEST_CONFIRM, stdout=StringIO())

    def p4(self, mode, fingerprint=None):
        if mode == "activate" and fingerprint is None:
            fingerprint = p3e.inspect_release_gates(actor_account_id=self.actor.pk,
                                                    expected_admin_account_ids=self.scope)["fingerprint"]
        with patch.object(p4, "_local_target", return_value=connections["default"]):
            return p4._perform(mode=mode, actor_id=self.actor.pk, expected_ids=self.scope,
                               fingerprint=fingerprint, confirmation=p4.LOCAL_CONFIRM)

    def release(self):
        self.p1_p2()
        self.assertEqual(self.p4("activate"), "LOCAL_ACTIVATED")

    def provision(self, *phases):
        for phase in phases:
            call_command("provision_school_accounts_local_dev", phase=phase, actor_account_id=self.actor.pk,
                         apply=True, confirm=s3.TEST_CONFIRM[phase], stdout=StringIO())

    # -- observed state ---------------------------------------------------------------------------
    def school_state(self):
        return (list(Permission.objects.filter(permission_code__in=SCHOOL).order_by("pk").values()),
                list(RolePermission.objects.filter(permission__permission_code__in=SCHOOL).order_by("pk").values()),
                list(AccessAuditLog.objects.filter(action__in=s3.EVENTS.values()).order_by("pk").values()))

    def everything(self):
        return (list(Service.objects.order_by("pk").values()), list(Permission.objects.order_by("pk").values()),
                list(RolePermission.objects.order_by("pk").values()), AccessAuditLog.objects.count(),
                list(Account.objects.order_by("pk").values("pk", "is_active")))

    def assert_compensated(self, school_before):
        # Original P4 rollback result, unchanged in scope:
        self.assertEqual(Service.objects.filter(is_active=True).count(), 0)
        self.assertFalse(RolePermission.objects.filter(permission__permission_code__in=REGISTRATION, is_active=True).exists())
        self.assertEqual(AccessAuditLog.objects.filter(action=p3b.SERVICE_DEACTIVATE).count(), 2)
        self.assertEqual(AccessAuditLog.objects.filter(action=p3b.BINDING_DEACTIVATE).count(), 3)
        for log in AccessAuditLog.objects.filter(action=p3b.BINDING_DEACTIVATE):
            self.assertIn(log.permission.permission_code, REGISTRATION)  # never a school-account row
        # The governed school-account rows and receipts are preserved exactly:
        self.assertEqual(self.school_state(), school_before)
        # Fail-closed: nobody keeps any registration or school-account authority (shared services off).
        for account in Account.objects.all():
            self.assertFalse(get_effective_permissions(account) & (REGISTRATION | SCHOOL), account.school_id)

    def refused_compensation(self):
        before = self.everything()
        with self.assertRaises((p4.LocalReleaseRefused, p3b.ActivationExerciseRefused)):
            self.p4("compensate")
        self.assertEqual(self.everything(), before)

    # -- 1 / 14 -----------------------------------------------------------------------------------
    def test_original_compensation_without_school_accounts(self):
        self.release()
        self.assertEqual(self.p4("compensate"), "LOCAL_COMPENSATED")
        self.assert_compensated(([], [], []))

    # -- 2 to 5 / 15 ------------------------------------------------------------------------------
    def compensate_after(self, *phases):
        self.release()
        self.provision(*phases)
        with patch.object(p4, "_local_target", return_value=connections["default"]):
            p3d._check_compensation_preview(actor_account_id=self.actor.pk, expected_admin_account_ids=self.scope)
        before = self.school_state()
        self.assertEqual(len(before[0]), 3)
        self.assertEqual(len(before[1]), 0 if phases == ("metadata",) else 3)
        self.assertEqual(len(before[2]), 3 * len(phases))  # three receipts per completed phase
        self.assertEqual(SCHOOL <= set(get_effective_permissions(self.actor)), "activate" in phases)
        self.assertFalse(get_effective_permissions(self.student) & SCHOOL)
        self.assertEqual(self.p4("compensate"), "LOCAL_COMPENSATED")
        self.assert_compensated(before)
        with self.assertRaises(CommandError):
            self.provision("metadata")  # the companion refuses once a compensation exists
        self.assertEqual(self.school_state(), before)

    def test_compensation_after_school_account_definitions(self):
        self.compensate_after("metadata")

    def test_compensation_after_inactive_school_account_bindings(self):
        self.compensate_after("metadata", "bindings")

    def test_compensation_after_activated_school_account_bindings(self):
        self.compensate_after("metadata", "bindings", "activate")

    # -- 6 to 10 ----------------------------------------------------------------------------------
    def refused_after_tamper(self, tamper):
        self.release()
        self.provision("metadata", "bindings", "activate")
        tamper()
        self.refused_compensation()

    def test_unauthorized_fourth_permission_is_refused(self):
        self.refused_after_tamper(lambda: Permission.objects.create(
            service=Service.objects.get(service_code="accounts"), permission_code="accounts.school_accounts.provision",
            permission_name="x", module_name="school_accounts", action_name="provision", description="x"))

    def test_unauthorized_role_binding_is_refused(self):
        self.refused_after_tamper(lambda: RolePermission.objects.create(
            role=self.roles["Student"], is_active=True,
            permission=Permission.objects.get(permission_code="accounts.school_accounts.read")))

    def test_modified_definition_is_refused(self):
        self.refused_after_tamper(lambda: Permission.objects.filter(
            permission_code="accounts.school_accounts.suspend").update(permission_name="Changed"))

    def test_forged_receipt_is_refused(self):
        def forge():
            log = AccessAuditLog.objects.filter(action=s3.EVENTS["bindings"]).first()
            AccessAuditLog.objects.filter(pk=log.pk).update(new_value={**log.new_value, "is_active": True})
        self.refused_after_tamper(forge)

    def test_missing_receipt_is_refused(self):
        self.refused_after_tamper(lambda: AccessAuditLog.objects.filter(
            pk=AccessAuditLog.objects.filter(action=s3.EVENTS["activate"]).first().pk).delete())

    def test_inconsistent_receipt_is_refused(self):
        self.refused_after_tamper(lambda: AccessAuditLog.objects.filter(
            pk=AccessAuditLog.objects.filter(action=s3.EVENTS["metadata"]).first().pk
        ).update(actor_account_id=self.student.pk))

    def test_partially_active_bindings_are_refused(self):
        self.refused_after_tamper(lambda: RolePermission.objects.filter(
            pk=RolePermission.objects.filter(permission__permission_code__in=SCHOOL).first().pk).update(is_active=False))

    def test_partial_or_unattributed_rows_are_refused(self):
        self.release()
        Permission.objects.create(service=Service.objects.get(service_code="accounts"),
                                  permission_code="accounts.school_accounts.read", permission_name="Read eligible school accounts",
                                  module_name="school_accounts", action_name="read", description="no receipt")
        self.refused_compensation()  # partial and without receipts

    def test_school_account_rows_can_never_precede_the_release(self):
        self.p1_p2()
        # Fingerprint taken while the catalogue is still clean, so the refusal below is P4/P3B's own.
        fingerprint = p3e.inspect_release_gates(actor_account_id=self.actor.pk,
                                                expected_admin_account_ids=self.scope)["fingerprint"]
        Permission.objects.create(service=Service.objects.get(service_code="accounts"),
                                  permission_code="accounts.school_accounts.read", permission_name="x",
                                  module_name="school_accounts", action_name="read", description="x")
        before = self.everything()
        with self.assertRaises((p4.LocalReleaseRefused, p3b.ActivationExerciseRefused)):
            self.p4("activate", fingerprint=fingerprint)
        self.assertEqual(self.everything(), before)
        self.assertEqual(Service.objects.filter(is_active=True).count(), 0)
        with self.assertRaises(p2.InactiveBindingRefused):  # and the P3E gate itself refuses too
            p3e.inspect_release_gates(actor_account_id=self.actor.pk, expected_admin_account_ids=self.scope)

    # -- 11 / 12 ----------------------------------------------------------------------------------
    def test_repeated_provisioning_is_idempotent_and_compensation_still_works(self):
        self.release()
        self.provision("metadata", "bindings", "activate")
        self.provision("metadata", "bindings", "activate")  # re-runs only verify
        before = self.school_state()
        self.assertEqual(len(before[2]), 9)
        self.assertEqual(self.p4("compensate"), "LOCAL_COMPENSATED")
        self.assert_compensated(before)

    def test_concurrent_governance_operations_are_serialized_by_the_shared_lock(self):
        self.release()
        holder_ready, release_holder = threading.Event(), threading.Event()

        def hold():
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SELECT GET_LOCK(%s, 10)", [p1.LOCK_NAME])
                    holder_ready.set()
                    release_holder.wait(timeout=20)
                    cursor.execute("SELECT RELEASE_LOCK(%s)", [p1.LOCK_NAME])
            finally:
                connections.close_all()
        thread = threading.Thread(target=hold)
        thread.start()
        try:
            self.assertTrue(holder_ready.wait(timeout=20))
            before = self.everything()
            with self.assertRaises(CommandError):
                self.provision("metadata")
            with self.assertRaises((p4.LocalReleaseRefused, p3b.ActivationExerciseRefused)):
                self.p4("compensate")
            self.assertEqual(self.everything(), before)
        finally:
            release_holder.set()
            thread.join(timeout=20)
        self.provision("metadata")
        self.assertEqual(Permission.objects.filter(permission_code__in=SCHOOL).count(), 3)

    # -- 13 ---------------------------------------------------------------------------------------
    def test_account_level_overrides_still_block_compensation(self):
        self.release()
        self.provision("metadata", "bindings", "activate")
        AccountPermission.objects.create(account=self.actor, effect="Deny",
                                         permission=Permission.objects.get(permission_code="accounts.school_accounts.suspend"))
        self.refused_compensation()  # original P3B rule: overrides are outside the rollback scope

    # -- 16 ---------------------------------------------------------------------------------------
    def test_compensation_is_refused_while_it_would_strand_a_deactivated_account(self):
        from apps.accounts.account_status import activate_account, suspend_account
        self.release()
        self.provision("metadata", "bindings", "activate")
        status_on = override_settings(WORKSPACE_ACCOUNT_STATUS_ENABLED=True, WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False)
        with status_on:  # only the WF-02.05 operation itself; governance tooling runs under the real test settings
            suspend_account(actor=self.actor, target_id=self.student.pk, expected_active=True)
        self.refused_compensation()
        with status_on:
            activate_account(actor=self.actor, target_id=self.student.pk, expected_active=False)
        before = self.school_state()
        self.assertEqual(self.p4("compensate"), "LOCAL_COMPENSATED")  # nothing stranded any more
        self.assert_compensated(before)
        after = self.everything()
        with self.assertRaises((p4.LocalReleaseRefused, p3b.ActivationExerciseRefused, p2.InactiveBindingRefused)):
            self.p4("activate")  # no re-activation after a compensation (refused at the gates or by P4)
        self.assertEqual(self.everything(), after)
