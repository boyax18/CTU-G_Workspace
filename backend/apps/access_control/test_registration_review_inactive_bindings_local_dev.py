"""AR-6C7D.8 P2: isolated transactional tests; never run under development settings."""

from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase, override_settings

from apps.accounts.models import Account
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission,
    Role, RolePermission, Service,
)
from apps.access_control.services import get_effective_permissions
from apps.access_control.management.commands import (
    init_registration_review_metadata_local_dev as p1,
    init_registration_review_inactive_bindings_local_dev as p2,
)

if settings.SETTINGS_MODULE != "config.test_settings":
    raise ImproperlyConfigured("AR-6C7D.8 tests require --settings=config.test_settings.")


class LocalDevelopmentInactiveBindingTests(TransactionTestCase):
    def setUp(self):
        self.admin = Role.objects.create(role_name="Admin", is_active=True)
        self.actor = Account(
            school_id="TEST-P2-OWNER-ADMIN", request_status="Approved", is_active=True,
        )
        self.actor.set_unusable_password()
        self.actor.save()
        AccountRole.objects.create(account=self.actor, role=self.admin)

    def prepare_p1(self):
        call_command(
            "init_registration_review_metadata_local_dev",
            apply=True, actor_account_id=self.actor.pk,
            confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO(),
        )

    def apply(self, *, actor_id=None, confirm=p2.TEST_CONFIRM):
        output = StringIO()
        call_command(
            "init_registration_review_inactive_bindings_local_dev",
            apply=True, actor_account_id=self.actor.pk if actor_id is None else actor_id,
            confirm_local_dev_phase2=confirm, stdout=output,
        )
        return output.getvalue()

    def test_three_inactive_bindings_with_three_attributed_audits(self):
        self.prepare_p1()
        self.assertIn("CREATED", self.apply())
        self.assertEqual(RolePermission.objects.count(), 3)
        self.assertFalse(RolePermission.objects.filter(is_active=True).exists())
        self.assertTrue(all(row.granted_by_id == self.actor.pk for row in RolePermission.objects.all()))
        self.assertFalse(Service.objects.filter(is_active=True).exists())
        self.assertEqual(AccessAuditLog.objects.filter(action=p2.EVENT).count(), 3)
        self.assertEqual(AccessAuditLog.objects.filter(action__in=(p1.SERVICE_EVENT, p1.PERMISSION_EVENT)).count(), 5)
        self.assertFalse(AccountPermission.objects.exists())
        self.assertFalse(get_effective_permissions(self.actor))

    def test_exact_repeat_does_not_duplicate_rows_or_audits(self):
        self.prepare_p1()
        self.apply()
        self.assertIn("ALREADY_COMPLETE", self.apply())
        self.assertEqual(RolePermission.objects.count(), 3)
        self.assertEqual(AccessAuditLog.objects.filter(action=p2.EVENT).count(), 3)

    def test_missing_apply_is_refused(self):
        self.prepare_p1()
        with self.assertRaises(CommandError):
            call_command("init_registration_review_inactive_bindings_local_dev", stdout=StringIO())
        self.assertFalse(RolePermission.objects.exists())

    def test_wrong_confirmation_is_refused(self):
        self.prepare_p1()
        with self.assertRaises(CommandError):
            self.apply(confirm="wrong")
        self.assertFalse(RolePermission.objects.exists())

    def test_missing_p1_is_refused(self):
        with self.assertRaises(CommandError):
            self.apply()
        self.assertFalse(RolePermission.objects.exists())

    def test_non_admin_actor_is_refused(self):
        self.prepare_p1()
        another = Account(school_id="TEST-P2-NO-ROLE", request_status="Approved", is_active=True)
        another.set_unusable_password()
        another.save()
        with self.assertRaises(CommandError):
            self.apply(actor_id=another.pk)
        self.assertFalse(RolePermission.objects.exists())

    def test_staff_actor_is_refused(self):
        self.prepare_p1()
        self.actor.is_staff = True
        self.actor.save(update_fields=["is_staff"])
        with self.assertRaises(CommandError):
            self.apply()
        self.assertFalse(RolePermission.objects.exists())

    def test_different_admin_cannot_reattribute_original_p1(self):
        self.prepare_p1()
        other = Account(school_id="TEST-P2-OTHER-ADMIN", request_status="Approved", is_active=True)
        other.set_unusable_password()
        other.save()
        AccountRole.objects.create(account=other, role=self.admin)
        with self.assertRaises(CommandError):
            self.apply(actor_id=other.pk)
        self.assertFalse(RolePermission.objects.exists())

    def test_inactive_service_is_required(self):
        self.prepare_p1()
        Service.objects.filter(service_code="accounts").update(is_active=True)
        with self.assertRaises(CommandError):
            self.apply()
        self.assertFalse(RolePermission.objects.exists())

    def test_tampered_p1_permission_definition_is_refused(self):
        self.prepare_p1()
        Permission.objects.filter(permission_code=p1.PERMISSION_CODES[0]).update(permission_name="Changed")
        with self.assertRaises(CommandError):
            self.apply()
        self.assertFalse(RolePermission.objects.exists())

    def test_tampered_p1_audit_is_refused(self):
        self.prepare_p1()
        row = AccessAuditLog.objects.filter(action=p1.SERVICE_EVENT).first()
        row.reason = "correction"
        row.save(update_fields=["reason"])
        with self.assertRaises(CommandError):
            self.apply()
        self.assertFalse(RolePermission.objects.exists())

    def test_partial_binding_does_not_get_auto_repaired(self):
        self.prepare_p1()
        one = Permission.objects.get(permission_code=p1.PERMISSION_CODES[0])
        RolePermission.objects.create(role=self.admin, permission=one,
                                      is_active=False, granted_by=self.actor)
        with self.assertRaises(CommandError):
            self.apply()
        self.assertEqual(RolePermission.objects.count(), 1)
        self.assertEqual(AccessAuditLog.objects.filter(action=p2.EVENT).count(), 0)

    def test_orphaned_p2_audit_is_refused(self):
        self.prepare_p1()
        AccessAuditLog.objects.create(
            actor_account=self.actor, action=p2.EVENT,
            reason="permission_change",
        )
        with self.assertRaises(CommandError):
            self.apply()
        self.assertFalse(RolePermission.objects.exists())

    def test_audit_exception_rolls_back_all_three_bindings(self):
        self.prepare_p1()
        actual = p2.record_access_audit_receipt
        counter = [0]

        def fail_second(**kwargs):
            counter[0] += 1
            if counter[0] == 2:
                raise RuntimeError("deliberate test audit failure")
            return actual(**kwargs)

        with patch.object(p2, "record_access_audit_receipt", side_effect=fail_second):
            with self.assertRaises(CommandError):
                self.apply()
        self.assertEqual(RolePermission.objects.count(), 0)
        self.assertEqual(AccessAuditLog.objects.filter(action=p2.EVENT).count(), 0)
        self.assertEqual(AccessAuditLog.objects.filter(action__in=(p1.SERVICE_EVENT, p1.PERMISSION_EVENT)).count(), 5)

    def test_active_binding_is_refused(self):
        self.prepare_p1()
        self.apply()
        RolePermission.objects.filter(permission__permission_code=p1.PERMISSION_CODES[0]).update(is_active=True)
        with self.assertRaises(CommandError):
            self.apply()
        self.assertEqual(AccessAuditLog.objects.filter(action=p2.EVENT).count(), 3)

    def test_tampered_p2_audit_is_refused(self):
        self.prepare_p1()
        self.apply()
        audit = AccessAuditLog.objects.filter(action=p2.EVENT).first()
        audit.reason = "correction"
        audit.save(update_fields=["reason"])
        with self.assertRaises(CommandError):
            self.apply()
        self.assertEqual(RolePermission.objects.count(), 3)

    def test_account_override_is_refused(self):
        self.prepare_p1()
        one = Permission.objects.get(permission_code=p1.PERMISSION_CODES[0])
        AccountPermission.objects.create(account=self.actor, permission=one,
                                         effect="Deny", is_active=True)
        with self.assertRaises(CommandError):
            self.apply()
        self.assertFalse(RolePermission.objects.exists())

    def test_live_approval_gate_refuses_p2(self):
        self.prepare_p1()

        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True):
            with self.assertRaises(CommandError):
                self.apply()

        self.assertFalse(RolePermission.objects.exists())

    def test_frozen_catalogue_mismatch_is_refused(self):
        self.prepare_p1()
        with patch.object(p1, "load_local", side_effect=ValueError("changed draft")):
            with self.assertRaises(CommandError):
                self.apply()
        self.assertFalse(RolePermission.objects.exists())
