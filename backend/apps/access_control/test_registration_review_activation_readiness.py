"""AR-6C7D.9 P3A READ-ONLY inspector tests; disposable MySQL ONLY."""

from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase, override_settings

from apps.accounts.models import Account
from apps.access_control.management.commands import (
    init_registration_review_metadata_local_dev as p1,
    init_registration_review_inactive_bindings_local_dev as p2,
)
from apps.access_control.models import (
    AccountPermission, AccountRole, AccessAuditLog, Permission, Role,
    RolePermission, Service,
)

if settings.SETTINGS_MODULE != "config.test_settings":
    raise ImproperlyConfigured("AR-6C7D.9 tests require --settings=config.test_settings.")


class ActivationReadinessTests(TransactionTestCase):
    def setUp(self):
        self.admin = Role.objects.create(role_name="Admin", is_active=True)
        self.actor = Account(
            school_id="TEST-P3A-ADMIN", request_status="Approved", is_active=True,
        )
        self.actor.set_unusable_password()
        self.actor.save()
        AccountRole.objects.create(account=self.actor, role=self.admin)

    def prepare(self):
        call_command(
            "init_registration_review_metadata_local_dev",
            apply=True, actor_account_id=self.actor.pk,
            confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO(),
        )
        call_command(
            "init_registration_review_inactive_bindings_local_dev",
            apply=True, actor_account_id=self.actor.pk,
            confirm_local_dev_phase2=p2.TEST_CONFIRM, stdout=StringIO(),
        )

    def inspect(self, actor_id=None):
        out = StringIO()
        call_command(
            "report_registration_review_activation_readiness",
            actor_account_id=self.actor.pk if actor_id is None else actor_id,
            stdout=out,
        )
        return out.getvalue()

    def test_valid_p2_state_is_read_only_and_activation_blocked(self):
        self.prepare()
        before_services = list(Service.objects.values_list("pk", "is_active"))
        before_bindings = list(RolePermission.objects.values_list("pk", "is_active"))
        before_audits = list(AccessAuditLog.objects.values_list("pk", "action"))
        output = self.inspect()
        self.assertIn("DATABASE INSPECTION PASSED (READ ONLY)", output)
        self.assertIn("ACTIVATION: BLOCKED (NO WRITES EXECUTED)", output)
        self.assertIn("Admin accounts affected by future grants: 1", output)
        self.assertEqual(before_services, list(Service.objects.values_list("pk", "is_active")))
        self.assertEqual(before_bindings, list(RolePermission.objects.values_list("pk", "is_active")))
        self.assertEqual(before_audits, list(AccessAuditLog.objects.values_list("pk", "action")))

    def test_missing_p1_is_refused(self):
        with self.assertRaises(CommandError):
            self.inspect()

    def test_missing_p2_is_refused(self):
        call_command(
            "init_registration_review_metadata_local_dev",
            apply=True, actor_account_id=self.actor.pk,
            confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO(),
        )
        with self.assertRaises(CommandError):
            self.inspect()

    def test_active_service_is_refused(self):
        self.prepare()
        Service.objects.filter(service_code="accounts").update(is_active=True)
        with self.assertRaises(CommandError):
            self.inspect()

    def test_active_binding_is_refused(self):
        self.prepare()
        RolePermission.objects.filter(permission__permission_code=p1.PERMISSION_CODES[0]).update(is_active=True)
        with self.assertRaises(CommandError):
            self.inspect()

    def test_tampered_p1_audit_is_refused(self):
        self.prepare()
        row = AccessAuditLog.objects.filter(action=p1.SERVICE_EVENT).first()
        row.reason = "correction"
        row.save(update_fields=["reason"])
        with self.assertRaises(CommandError):
            self.inspect()

    def test_tampered_p2_audit_is_refused(self):
        self.prepare()
        row = AccessAuditLog.objects.filter(action=p2.EVENT).first()
        row.reason = "correction"
        row.save(update_fields=["reason"])
        with self.assertRaises(CommandError):
            self.inspect()

    def test_actor_mismatch_is_refused(self):
        self.prepare()
        other = Account(school_id="TEST-P3A-SECOND-ADMIN", request_status="Approved", is_active=True)
        other.set_unusable_password()
        other.save()
        AccountRole.objects.create(account=other, role=self.admin)
        with self.assertRaises(CommandError):
            self.inspect(actor_id=other.pk)

    def test_account_override_is_refused(self):
        self.prepare()
        code = Permission.objects.get(permission_code=p1.PERMISSION_CODES[0])
        AccountPermission.objects.create(account=self.actor, permission=code,
                                         effect="Deny", is_active=True)
        with self.assertRaises(CommandError):
            self.inspect()

    def test_api_flag_enabled_is_refused(self):
        self.prepare()
        with override_settings(WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True):
            with self.assertRaises(CommandError):
                self.inspect()

    def test_approval_flag_enabled_is_refused(self):
        self.prepare()
        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True):
            with self.assertRaises(CommandError):
                self.inspect()

    def test_source_digest_change_is_refused(self):
        self.prepare()
        with patch.object(p1, "load_local", side_effect=ValueError("drift")):
            with self.assertRaises(CommandError):
                self.inspect()

    def test_admin_scope_counts_all_eligible_admins(self):
        self.prepare()
        other = Account(school_id="TEST-P3A-OTHER-ADMIN", request_status="Approved", is_active=True)
        other.set_unusable_password()
        other.save()
        AccountRole.objects.create(account=other, role=self.admin)
        output = self.inspect()
        self.assertIn("Admin accounts affected by future grants: 2", output)
        self.assertFalse(RolePermission.objects.filter(is_active=True).exists())

    def test_missing_actor_id_rejected_by_argparse(self):
        with self.assertRaises(CommandError):
            call_command("report_registration_review_activation_readiness", stdout=StringIO())
