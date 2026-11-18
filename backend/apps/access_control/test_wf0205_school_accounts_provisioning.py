"""WF-02.05 stage 3: governed provisioning of the three school-account codes, in disposable MySQL ONLY.

Run: python manage.py test apps.access_control.test_wf0205_school_accounts_provisioning --settings=config.test_settings
The registration-review release is built with the real P1, P2 and P4 code paths first, then the
companion phases run; the end-to-end test uses ONLY rows created by the governed command.
"""

import json
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient

from apps.access_control.management.commands import (
    init_registration_review_inactive_bindings_local_dev as p2,
    init_registration_review_metadata_local_dev as p1,
    provision_school_accounts_local_dev as s3,
    release_registration_review_local_dev_p4 as p4,
    report_registration_review_release_gates_p3e as p3e,
)
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.services import get_effective_permissions, has_permission
from apps.accounts.models import Account

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("WF-02.05 provisioning tests require the disposable MySQL test settings.")

PASSWORD = "Harbor!Lantern5821"
CODES = set(s3.CODES)


class ProvisioningTests(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.roles = {n: Role.objects.create(role_name=n, is_active=True)
                      for n in ("Admin", "Student", "Instructor", "Treasurer", "Technical Super Admin")}
        self.actor = self.account("TEST-S3-ADMIN", "Admin")
        self.student = self.account("7260001", "Student")
        self.tsa_only = self.account("TEST-S3-TSA", "Technical Super Admin")
        self.tsa_admin = self.account("TEST-S3-TSA-ADMIN", "Admin", "Technical Super Admin")

    def account(self, school_id, *roles):
        account = Account(school_id=school_id, request_status="Approved", is_active=True)
        account.set_password(PASSWORD)
        account.save()
        for role in roles:
            AccountRole.objects.create(account=account, role=self.roles[role])
        return account

    def release_registration_review(self):
        call_command("init_registration_review_metadata_local_dev", apply=True, actor_account_id=self.actor.pk,
                     confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO())
        call_command("init_registration_review_inactive_bindings_local_dev", apply=True, actor_account_id=self.actor.pk,
                     confirm_local_dev_phase2=p2.TEST_CONFIRM, stdout=StringIO())
        scope = ",".join(str(pk) for pk in sorted([self.actor.pk, self.tsa_admin.pk]))
        fingerprint = p3e.inspect_release_gates(actor_account_id=self.actor.pk, expected_admin_account_ids=scope)["fingerprint"]
        with patch.object(p4, "_local_target", return_value=connections["default"]):
            self.assertEqual(p4._perform(mode="activate", actor_id=self.actor.pk, expected_ids=scope,
                                         fingerprint=fingerprint, confirmation=p4.LOCAL_CONFIRM), "LOCAL_ACTIVATED")
        self.scope = scope

    def phase(self, phase, confirm=None, actor=None):
        out = StringIO()
        call_command("provision_school_accounts_local_dev", phase=phase, actor_account_id=(actor or self.actor).pk,
                     apply=phase != "verify", confirm=s3.TEST_CONFIRM.get(phase, "") if confirm is None else confirm, stdout=out)
        return out.getvalue()

    def refused(self, phase, **kwargs):
        before = (AccessAuditLog.objects.count(), Permission.objects.count(), RolePermission.objects.count())
        with self.assertRaises(CommandError):
            self.phase(phase, **kwargs)
        self.assertEqual((AccessAuditLog.objects.count(), Permission.objects.count(), RolePermission.objects.count()), before)

    def scope_state(self):
        return (sorted(Permission.objects.filter(permission_code__in=CODES).values_list("permission_code", flat=True)),
                sorted(RolePermission.objects.filter(permission__permission_code__in=CODES)
                       .values_list("role__role_name", "is_active")))

    def test_full_sequence_creates_exact_definitions_bindings_and_receipts(self):
        self.release_registration_review()
        unrelated_before = (list(Service.objects.values_list("pk", "is_active")), list(Role.objects.values_list("pk", "is_active")),
                            list(AccountRole.objects.values_list("pk", "account_id", "role_id")),
                            list(RolePermission.objects.values_list("pk", "is_active")))
        self.assertIn("metadata: CREATED", self.phase("metadata"))
        self.assertEqual(self.scope_state(), (sorted(CODES), []))
        self.assertIn("bindings: CREATED", self.phase("bindings"))
        self.assertEqual(self.scope_state()[1], [("Admin", False)] * 3)
        self.assertFalse(CODES & set(get_effective_permissions(self.actor)))  # inactive bindings grant nothing
        self.assertIn("activate: ACTIVATED", self.phase("activate"))
        self.assertEqual(self.scope_state()[1], [("Admin", True)] * 3)
        definitions = s3.catalogue_definitions()
        accounts = Service.objects.get(service_code="accounts")
        for permission in Permission.objects.filter(permission_code__in=CODES):
            d = definitions[permission.permission_code]
            self.assertEqual((permission.service_id, permission.permission_name, permission.module_name,
                              permission.action_name, permission.description),
                             (accounts.pk, d["permission_name"], d["module_name"], d["action_name"], d["description"]))
        for binding in RolePermission.objects.filter(permission__permission_code__in=CODES):
            self.assertEqual((binding.role_id, binding.granted_by_id), (self.roles["Admin"].pk, self.actor.pk))
        for event in s3.EVENTS.values():
            logs = AccessAuditLog.objects.filter(action=event)
            self.assertEqual(logs.count(), 3, event)
            self.assertEqual(set(logs.values_list("actor_account_id", flat=True)), {self.actor.pk})
        # Effective authority: Admin and Admin+Technical Super Admin only.
        self.assertTrue(CODES <= set(get_effective_permissions(self.actor)))
        self.assertTrue(CODES <= set(get_effective_permissions(self.tsa_admin)))
        self.assertFalse(CODES & set(get_effective_permissions(self.tsa_only)))
        self.assertFalse(CODES & set(get_effective_permissions(self.student)))
        self.assertFalse(any(c.startswith("access_control.") for c in get_effective_permissions(self.actor)))
        # Nothing outside the three codes changed (the three new bindings are the only RolePermission additions).
        self.assertEqual(list(Service.objects.values_list("pk", "is_active")), unrelated_before[0])
        self.assertEqual(list(Role.objects.values_list("pk", "is_active")), unrelated_before[1])
        self.assertEqual(list(AccountRole.objects.values_list("pk", "account_id", "role_id")), unrelated_before[2])
        self.assertEqual([r for r in RolePermission.objects.values_list("pk", "is_active")
                          if r[0] in {x[0] for x in unrelated_before[3]}], unrelated_before[3])
        self.assertFalse(AccountPermission.objects.exists())
        # Re-runs only verify.
        for phase in s3.PHASES:
            self.assertIn("ALREADY_COMPLETE", self.phase(phase))
        self.assertIn("verify: VERIFIED", self.phase("verify"))
        self.assertEqual(sum(AccessAuditLog.objects.filter(action=e).count() for e in s3.EVENTS.values()), 9)

    def test_deny_precedence_is_preserved(self):
        self.release_registration_review()
        for phase in s3.PHASES:
            self.phase(phase)
        suspend = Permission.objects.get(permission_code="accounts.school_accounts.suspend")
        AccountPermission.objects.create(account=self.tsa_admin, permission=suspend, effect="Deny")
        self.assertFalse(has_permission(self.tsa_admin, "accounts.school_accounts.suspend"))
        self.assertTrue(has_permission(self.tsa_admin, "accounts.school_accounts.read"))
        self.assertIn("VERIFIED", self.phase("verify"))  # a Deny is allowed; only Grants are refused
        AccountPermission.objects.create(account=self.student, permission=suspend, effect="Grant")
        self.refused("verify")

    def test_stage3c_role_coverage_school_admin_deny_and_protected_writer(self):
        """Stage 3C: the cases ctug_workspace has no accounts for (Instructor, Treasurer, a School
        Admin's own Deny), plus the protected-writer refusal once the governed rows are active."""
        from apps.access_control.writer_boundary import WriterBoundaryUnavailable
        from apps.accounts.account_status import suspend_account

        instructor = self.account("TEST-S3C-INSTRUCTOR", "Instructor")
        treasurer = self.account("TEST-S3C-TREASURER", "Treasurer")
        student_treasurer = self.account("7260002", "Student", "Treasurer")
        self.release_registration_review()
        for phase in s3.PHASES:
            self.phase(phase)
        for account in (self.actor, self.tsa_admin):
            self.assertEqual(CODES & set(get_effective_permissions(account)), CODES)
        for account in (self.tsa_only, self.student, instructor, treasurer, student_treasurer):
            self.assertFalse(CODES & set(get_effective_permissions(account)), account.school_id)
            self.assertFalse(any(has_permission(account, code) for code in CODES), account.school_id)
        # A School Admin's own account-level Deny takes precedence over the active Admin binding.
        read = Permission.objects.get(permission_code="accounts.school_accounts.read")
        AccountPermission.objects.create(account=self.actor, permission=read, effect="Deny")
        self.assertFalse(has_permission(self.actor, "accounts.school_accounts.read"))
        self.assertTrue(has_permission(self.actor, "accounts.school_accounts.suspend"))
        self.assertTrue(has_permission(self.tsa_admin, "accounts.school_accounts.read"))
        # The protected writer still refuses account-status changes, before any change or audit.
        audits = AccessAuditLog.objects.count()
        with override_settings(WORKSPACE_ACCOUNT_STATUS_ENABLED=True, WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):
            with self.assertRaises(WriterBoundaryUnavailable):
                suspend_account(actor=self.tsa_admin, target_id=self.student.pk, expected_active=True)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)
        self.assertEqual(AccessAuditLog.objects.count(), audits)

    def test_preconditions_order_and_confirmations(self):
        self.refused("metadata")  # no registration-review release yet
        call_command("init_registration_review_metadata_local_dev", apply=True, actor_account_id=self.actor.pk,
                     confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO())
        call_command("init_registration_review_inactive_bindings_local_dev", apply=True, actor_account_id=self.actor.pk,
                     confirm_local_dev_phase2=p2.TEST_CONFIRM, stdout=StringIO())
        self.refused("metadata")  # P4 activation missing
        self.release_registration_review_after_p2()
        self.refused("bindings")  # metadata first
        self.refused("activate")
        for wrong in ("", "WF-02.05:DISPOSABLE-TEST:S3:BINDINGS", s3.DEV_CONFIRM["metadata"], p1.TEST_CONFIRM):
            with self.subTest(confirm=wrong):
                self.refused("metadata", confirm=wrong)
        with self.assertRaises(CommandError):  # no --apply
            call_command("provision_school_accounts_local_dev", phase="metadata", actor_account_id=self.actor.pk,
                         confirm=s3.TEST_CONFIRM["metadata"], stdout=StringIO())
        self.refused("metadata", actor=self.student)  # not an Admin
        self.refused("metadata", actor=self.tsa_admin)  # an Admin, but not the attributed operator
        with override_settings(WORKSPACE_ACCOUNT_STATUS_ENABLED=True):
            self.refused("metadata")
        self.phase("metadata")
        self.refused("activate")  # bindings must be staged first
        self.assertEqual(self.scope_state()[1], [])

    def release_registration_review_after_p2(self):
        scope = ",".join(str(pk) for pk in sorted([self.actor.pk, self.tsa_admin.pk]))
        fingerprint = p3e.inspect_release_gates(actor_account_id=self.actor.pk, expected_admin_account_ids=scope)["fingerprint"]
        with patch.object(p4, "_local_target", return_value=connections["default"]):
            p4._perform(mode="activate", actor_id=self.actor.pk, expected_ids=scope,
                        fingerprint=fingerprint, confirmation=p4.LOCAL_CONFIRM)
        self.scope = scope

    def test_conflicting_or_partial_state_is_refused_without_repair(self):
        self.release_registration_review()
        foreign = Permission.objects.create(service=Service.objects.get(service_code="accounts"),
                                            permission_code="accounts.school_accounts.read", permission_name="Forged",
                                            module_name="school_accounts", action_name="read", description="Forged")
        self.refused("metadata")  # a pre-existing, unattributed, differing row
        RolePermission.objects.create(role=self.roles["Student"], permission=foreign, is_active=False)
        self.refused("verify")
        self.assertEqual(Permission.objects.filter(permission_code__in=CODES).count(), 1)

    def test_bindings_to_another_role_or_partial_activation_are_refused(self):
        self.release_registration_review()
        self.phase("metadata")
        self.phase("bindings")
        extra = RolePermission.objects.create(role=self.roles["Student"],
                                              permission=Permission.objects.get(permission_code="accounts.school_accounts.read"))
        self.refused("activate")
        extra.delete()
        first = RolePermission.objects.filter(permission__permission_code__in=CODES).order_by("pk").first()
        RolePermission.objects.filter(pk=first.pk).update(is_active=True)
        self.refused("activate")
        self.refused("verify")

    def test_end_to_end_http_with_governed_rows_only(self):
        from apps.accounts.test_wf0204_release_settings import local_review
        from apps.accounts.test_wf0205_stage2 import mode_settings
        self.release_registration_review()
        for phase in s3.PHASES:
            self.phase(phase)
        self.assertFalse(Permission.objects.filter(permission_code__in=CODES).exclude(
            pk__in=AccessAuditLog.objects.filter(action=s3.EVENTS["metadata"]).values("permission_id")).exists())
        cfg = local_review()
        with override_settings(**mode_settings(cfg)):
            def browser(account):
                client = APIClient(enforce_csrf_checks=True)
                token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
                status = client.post("/api/v1/auth/login/", {"school_id": account.school_id, "password": PASSWORD},
                                     format="json", HTTP_X_CSRFTOKEN=token).status_code
                client.token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
                client.login_status = status
                return client

            def change(client, action, expected):
                return client.post(f"/api/v1/admin/school-accounts/{self.student.pk}/{action}/",
                                   data=json.dumps({"expected_active": expected}), content_type="application/json",
                                   HTTP_X_CSRFTOKEN=client.token)

            def signed_in(client):
                return client.get("/api/v1/auth/session/").json()["authenticated"]

            admin, tsa, tsa_only = browser(self.actor), browser(self.tsa_admin), browser(self.tsa_only)
            first, second = browser(self.student), browser(self.student)
            self.assertEqual(admin.get("/api/v1/admin/school-accounts/").status_code, 200)
            self.assertEqual(tsa_only.login_status, 200)
            self.assertEqual(change(tsa_only, "suspend", True).status_code, 403)  # no Admin role
            self.assertEqual(change(first, "suspend", True).status_code, 403)  # Student
            self.assertEqual(change(tsa, "suspend", True).status_code, 200)  # inherited through Admin
            self.assertFalse(signed_in(first) or signed_in(second))
            self.assertEqual(change(admin, "activate", False).status_code, 200)
            self.assertFalse(signed_in(first) or signed_in(second))
            self.assertTrue(signed_in(browser(self.student)))
            self.assertEqual(change(admin, "activate", False).status_code, 409)  # stale
        self.assertEqual(AccessAuditLog.objects.filter(action__startswith="account.status.").count(), 2)
