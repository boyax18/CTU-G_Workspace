"""AR-6C7D.7 P1: disposable-MySQL tests for the local-dev metadata entrypoint."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase, override_settings

from apps.accounts.models import Account
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service,
)
from apps.access_control.management.commands import init_registration_review_metadata_local_dev as p1


class LocalDevelopmentMetadataTests(TransactionTestCase):
    def setUp(self):
        self.admin = Role.objects.create(role_name="Admin", is_active=True)
        self.actor = Account(school_id="p1-fixture-admin", request_status="Approved", is_active=True)
        self.actor.set_unusable_password()
        self.actor.save()
        AccountRole.objects.create(account=self.actor, role=self.admin, assigned_by=None)

    def apply(self, *, account_id=None, confirmation=p1.TEST_CONFIRM):
        output = StringIO()
        call_command(
            "init_registration_review_metadata_local_dev", apply=True,
            actor_account_id=self.actor.pk if account_id is None else account_id,
            confirm_local_dev_phase1=confirmation, stdout=output,
        )
        return output.getvalue()

    def test_exact_metadata_and_audits_are_created_without_grants(self):
        self.assertIn("CREATED", self.apply())
        self.assertEqual(set(Service.objects.values_list("service_code", flat=True)), set(p1.SERVICE_CODES))
        self.assertFalse(Service.objects.filter(is_active=True).exists())
        self.assertEqual(set(Permission.objects.values_list("permission_code", flat=True)), set(p1.PERMISSION_CODES))
        self.assertEqual(RolePermission.objects.count(), 0)
        self.assertEqual(AccountPermission.objects.count(), 0)
        self.assertEqual(AccessAuditLog.objects.filter(action__in=(p1.SERVICE_EVENT, p1.PERMISSION_EVENT)).count(), 5)

    def test_exact_second_run_is_idempotent(self):
        self.apply()
        self.assertIn("ALREADY_COMPLETE", self.apply())
        self.assertEqual(Service.objects.count(), 2)
        self.assertEqual(Permission.objects.count(), 3)
        self.assertEqual(AccessAuditLog.objects.filter(action__in=(p1.SERVICE_EVENT, p1.PERMISSION_EVENT)).count(), 5)

    def test_refuses_missing_confirmation_before_writes(self):
        with self.assertRaises(CommandError):
            self.apply(confirmation="incorrect")
        self.assertEqual(Service.objects.count(), 0)

    def test_no_implicit_execution(self):
        with self.assertRaises(CommandError):
            call_command("init_registration_review_metadata_local_dev", stdout=StringIO())
        self.assertEqual(Service.objects.count(), 0)

    def test_refuses_non_admin_actor(self):
        another = Account(school_id="p1-non-admin", request_status="Approved", is_active=True)
        another.set_unusable_password()
        another.save()
        with self.assertRaises(CommandError):
            self.apply(account_id=another.pk)
        self.assertFalse(Service.objects.exists())

    def test_refuses_django_framework_staff_actor(self):
        self.actor.is_staff = True
        self.actor.save(update_fields=["is_staff"])
        with self.assertRaises(CommandError):
            self.apply()
        self.assertFalse(Service.objects.exists())

    @override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True)
    def test_refuses_enabled_review_gate(self):
        with self.assertRaises(CommandError):
            self.apply()
        self.assertFalse(Service.objects.exists())

    def test_refuses_partial_metadata_without_auto_repair(self):
        src, _ = p1._expected()
        d = src["accounts"]
        Service.objects.create(service_code="accounts", service_name=d["service_name"],
                               description=d["description"], is_active=False)
        with self.assertRaises(CommandError):
            self.apply()
        self.assertEqual(Service.objects.count(), 1)
        self.assertEqual(Permission.objects.count(), 0)

    def test_rollback_on_audit_failure(self):
        with patch.object(p1, "record_access_audit_receipt", side_effect=RuntimeError("test-audit-failure")):
            with self.assertRaises(CommandError):
                self.apply()
        self.assertEqual(Service.objects.count(), 0)
        self.assertEqual(Permission.objects.count(), 0)
        self.assertEqual(AccessAuditLog.objects.filter(action__in=(p1.SERVICE_EVENT, p1.PERMISSION_EVENT)).count(), 0)

    def test_refuses_foreign_existing_grants(self):
        other = Service.objects.create(service_code="other", service_name="Other", is_active=False)
        permission = Permission.objects.create(service=other, permission_code="other.read", permission_name="Read",
                                               module_name="other", action_name="read")
        RolePermission.objects.create(role=self.admin, permission=permission, is_active=False)
        with self.assertRaises(CommandError):
            self.apply()
        self.assertEqual(RolePermission.objects.count(), 1)

    def test_refuses_unattributed_prior_audit(self):
        self.apply()
        audit = AccessAuditLog.objects.filter(action=p1.SERVICE_EVENT).first()
        audit.reason = "correction"
        audit.save(update_fields=["reason"])
        with self.assertRaises(CommandError):
            self.apply()
        self.assertEqual(Service.objects.count(), 2)
        self.assertEqual(AccessAuditLog.objects.filter(action__in=(p1.SERVICE_EVENT, p1.PERMISSION_EVENT)).count(), 5)

    def test_refuses_changed_pinned_catalogue(self):
        with patch.object(p1, "load_local", side_effect=ValueError("source changed")):
            with self.assertRaises(CommandError):
                self.apply()
        self.assertFalse(Service.objects.exists())
