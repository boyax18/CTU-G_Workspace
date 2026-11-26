"""WF-11.01 catalogue v2.3 provisioning command (disposable MySQL only).

Run: python manage.py test apps.access_control.test_academic_v2_3_provisioning --settings=config.test_settings --noinput
The recorded independent approval is replaced by a stand-in ONLY inside these disposable-database tests
(approved()); the real constant stays None until the genuine sign-off exists. The full sequence runs on the
owner's real local-development authorization record, which never counts as independent approval.
"""

from contextlib import nullcontext
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.access_control.catalogue import validation_v2_3 as v23
from apps.access_control.management.commands import provision_academic_settings_phase1_local_dev as phase1
from apps.access_control.management.commands import provision_academic_settings_phase2_local_dev as phase2
from apps.access_control.management.commands import provision_academic_settings_v2_3_local_dev as cmd
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.services import has_permission
from apps.accounts.active_role_context import bind_role_scope
from apps.accounts.models import Account

PASSWORD = "Harbor!Lantern5821"
NEW_CODES = (cmd.VERIFY, cmd.ONBOARD, cmd.HISTORY)


def approved():
    return patch.object(v23, "require_independent_approval", return_value={})  # disposable-test stand-in only


class V23ProvisioningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.roles = {name: Role.objects.create(role_name=name) for name in ("Student", "Instructor", "Treasurer", "Admin")}
        cls.admin = cls.account("V23-ADMIN", "Admin")
        cls.admin2 = cls.account("V23-ADMIN2", "Admin")
        cls.student = cls.account("V23-STU", "Student")
        cls.treasurer = cls.account("V23-TRE", "Treasurer")
        cls.dual = cls.account("V23-DUAL", "Student", "Admin")

    @classmethod
    def account(cls, school_id, *roles):
        account = Account.objects.create_user(school_id=school_id, password=PASSWORD, requested_role=cls.roles["Student"])
        Account.objects.filter(pk=account.pk).update(request_status="Approved", is_active=True)
        for role in roles:
            AccountRole.objects.create(account=account, role=cls.roles[role])
        return Account.objects.get(pk=account.pk)

    def prior(self, phases=(phase1, phase2)):
        for module in phases:
            for phase in module.PHASES:
                module.run(phase=phase, actor_account_id=self.admin.pk, confirmation=module.TEST_CONFIRM[phase], apply=True)

    def run3(self, phase, confirmation=None, apply=True, actor=None):
        return cmd.run(phase=phase, actor_account_id=(actor or self.admin).pk,
                       confirmation=cmd.TEST_CONFIRM[phase] if confirmation is None and phase != "verify" else confirmation,
                       apply=apply)

    def state(self):
        return (list(Service.objects.values()), list(Permission.objects.values()), list(RolePermission.objects.values()),
                list(AccountPermission.objects.values()), AccessAuditLog.objects.count())

    def refused(self, *args, **kwargs):
        before = self.state()
        with self.assertRaises(cmd.AcademicV23Refused):
            self.run3(*args, **kwargs)
        self.assertEqual(before, self.state())

    def complete(self):
        for phase in cmd.PHASES:
            self.run3(phase)

    def test_nothing_is_provisioned_without_independent_approval_or_the_owner_local_authorization(self):
        self.prior()
        self.assertIsNone(v23.INDEPENDENT_APPROVAL)
        with patch.object(v23, "OWNER_LOCAL_AUTHORIZATION", None):
            for phase in cmd.PHASES + ("verify",):
                with self.subTest(phase=phase):
                    self.refused(phase)
        pins = {"delta_sha256": v23.DELTA_SHA256, "addendum_sha256": v23.ADDENDUM_SHA256}
        with tempfile.TemporaryDirectory() as root:
            record = Path(root) / "docs" / "security" / "v23_sign_off.md"
            record.parent.mkdir(parents=True)
            text = f"{v23.DELTA_SHA256}\n{v23.ADDENDUM_SHA256}\n" + "\n".join(v23.SIGN_OFF_DECISIONS) + "\n"
            for forged in ({"status": "APPROVED"}, dict(pins, delta_sha256="0" * 64, sign_off="docs/security/v23_sign_off.md"),
                           dict(pins, sign_off="review_only/v23_sign_off.md"), dict(pins, sign_off="docs/security/../x.md"),
                           dict(pins, sign_off="docs/security/missing.md")):
                with self.subTest(forged=forged), patch.object(v23, "INDEPENDENT_APPROVAL", forged), \
                        patch.object(v23, "SIGN_OFF_ROOT", Path(root)), self.assertRaises(v23.CatalogueV23ValidationError):
                    v23.require_independent_approval()
            for incomplete in (text.replace(v23.SIGN_OFF_DECISIONS[0], "v2.1 decision: PENDING"),
                               text.replace(v23.DELTA_SHA256, "")):
                record.write_text(incomplete, encoding="utf-8")
                with patch.object(v23, "INDEPENDENT_APPROVAL", dict(pins, sign_off="docs/security/v23_sign_off.md")), \
                        patch.object(v23, "SIGN_OFF_ROOT", Path(root)), self.assertRaises(v23.CatalogueV23ValidationError):
                    v23.require_independent_approval()
            record.write_text(text, encoding="utf-8")  # a complete sign-off for exactly these pins is accepted
            with patch.object(v23, "INDEPENDENT_APPROVAL", dict(pins, sign_off="docs/security/v23_sign_off.md")), \
                    patch.object(v23, "SIGN_OFF_ROOT", Path(root)):
                self.assertEqual(v23.require_independent_approval()["sign_off"], "docs/security/v23_sign_off.md")

    def test_the_owner_local_authorization_is_never_independent_approval_and_is_local_only(self):
        self.assertEqual(v23.require_local_development_authorization()["record"], v23.OWNER_LOCAL_AUTHORIZATION["record"])
        with self.assertRaises(v23.CatalogueV23ValidationError):
            v23.require_independent_approval()  # the owner record never satisfies independent approval
        self.assertEqual(cmd.authorization_basis(), "owner_local_development_authorization")
        for module, profile in (("config.test_settings", "production"), ("config.production", "local")):
            fake = SimpleNamespace(SETTINGS_MODULE=module, WORKSPACE_DEPLOYMENT_PROFILE=profile)
            with self.subTest(module=module, profile=profile), patch.object(cmd, "settings", fake), \
                    self.assertRaises(cmd.AcademicV23Refused):
                cmd.authorization_basis()
        real = dict(v23.OWNER_LOCAL_AUTHORIZATION)
        with tempfile.TemporaryDirectory() as root:
            record = Path(root) / "docs" / "security" / "owner.md"
            record.parent.mkdir(parents=True)
            text = "\n".join((v23.DELTA_SHA256, v23.ADDENDUM_SHA256, *v23.OWNER_LOCAL_LINES)) + "\n"
            local = dict(real, record="docs/security/owner.md")
            for forged, body in ((dict(local, delta_sha256="0" * 64), text), (dict(real, record="review_only/owner.md"), text),
                                 (local, text.replace("Scope: local development only", "")),
                                 (local, text + v23.SIGN_OFF_DECISIONS[2] + "\n")):
                record.write_text(body, encoding="utf-8")
                with self.subTest(forged=forged), patch.object(v23, "OWNER_LOCAL_AUTHORIZATION", forged), \
                        patch.object(v23, "SIGN_OFF_ROOT", Path(root)), self.assertRaises(v23.CatalogueV23ValidationError):
                    v23.require_local_development_authorization()
            record.write_text(text, encoding="utf-8")  # the same record, correctly formed, is accepted
            with patch.object(v23, "OWNER_LOCAL_AUTHORIZATION", local), patch.object(v23, "SIGN_OFF_ROOT", Path(root)):
                self.assertEqual(v23.require_local_development_authorization()["record"], "docs/security/owner.md")

    def test_phases_one_and_two_are_required(self):
        with approved():
            self.refused("metadata")
            self.prior(phases=(phase1,))
            self.refused("metadata")

    def test_full_sequence_provisions_exactly_the_approved_scope(self):
        self.prior()
        with nullcontext():  # the owner's real local-development authorization record; no stand-in
            self.assertEqual(self.run3("verify"), "NOT_STARTED")
            for phase in ("restate", "bindings", "activate"):
                self.refused(phase)  # strict order
            self.refused("metadata", confirmation=phase2.TEST_CONFIRM["metadata"])
            self.refused("metadata", apply=False)
            self.refused("metadata", actor=self.student)
            self.assertEqual(self.run3("metadata"), "CREATED")
            self.assertEqual(self.run3("verify"), "INCOMPLETE")
            self.assertFalse(Service.objects.get(service_code="finance").is_active)
            self.refused("bindings")  # restatements first
            self.assertEqual(self.run3("restate"), "RESTATED")
            self.assertEqual(phase1.run(phase="verify", actor_account_id=self.admin.pk), "VERIFIED")
            self.assertEqual(phase2.run(phase="verify", actor_account_id=self.admin.pk), "VERIFIED")
            self.assertEqual(self.run3("bindings"), "CREATED")
            self.assertFalse(has_permission(self.admin, cmd.FEE))  # staged only
            self.assertEqual(self.run3("activate"), "ACTIVATED")
            self.assertEqual(self.run3("verify"), "VERIFIED")
            self.assertEqual(self.run3("activate"), "ALREADY_COMPLETE")
            self.assertEqual(phase1.run(phase="verify", actor_account_id=self.admin.pk), "VERIFIED")
        for account in (self.admin, self.admin2):
            for code in (cmd.FEE, cmd.VERIFY, cmd.HISTORY):
                self.assertTrue(has_permission(account, code), (account.school_id, code))
            self.assertFalse(has_permission(account, cmd.ONBOARD))
        self.assertTrue(has_permission(self.student, cmd.ONBOARD))
        self.assertTrue(has_permission(self.student, cmd.PROFILE_READ))
        for code in (cmd.FEE, cmd.VERIFY, cmd.HISTORY):
            self.assertFalse(has_permission(self.student, code))
            self.assertFalse(has_permission(self.treasurer, code))  # Treasurer never receives fee configuration
        self.assertFalse(RolePermission.objects.filter(role=self.roles["Treasurer"], permission__permission_code=cmd.FEE).exists())
        _, definitions, restatements = cmd.catalogue()
        for code in cmd.RESTATED:
            self.assertEqual(Permission.objects.get(permission_code=code).description, restatements[code][1])
        self.assertEqual(AccessAuditLog.objects.filter(action__startswith="workspace.academic_settings.v23.").count(), 19)
        self.assertFalse(AccountPermission.objects.exists())  # no account override created
        with approved():  # a partial or tampered restatement is never repaired or accepted
            Permission.objects.filter(permission_code="academic.periods.manage").update(description="Changed.")
            with self.assertRaises(phase1.AcademicPhase1Refused):
                phase1.run(phase="verify", actor_account_id=self.admin.pk)
            with self.assertRaises(cmd.AcademicV23Refused):
                self.run3("verify")

    def test_selected_role_context_and_every_deny_keep_precedence(self):
        self.prior()
        legacy = Permission.objects.create(service=Service.objects.get(service_code="clearance"),
                                           permission_code="clearance.requests.self.submit", permission_name="Legacy",
                                           module_name="m", action_name="a")  # disposable fixture only
        predecessor = AccountPermission.objects.create(account=self.student, permission=legacy, effect="Deny")
        with approved():
            self.run3("metadata")
            fee_deny = AccountPermission.objects.create(account=self.admin2, permission=Permission.objects.get(
                permission_code=cmd.FEE), effect="Deny")
            for phase in ("restate", "bindings", "activate"):
                self.run3(phase)
        with override_settings(WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True):
            with bind_role_scope(self.student.pk, self.roles["Student"].pk):
                self.assertFalse(has_permission(self.student, cmd.ONBOARD))  # Deny-only predecessor still wins
                self.assertTrue(has_permission(self.student, cmd.PROFILE_READ))
            with bind_role_scope(self.admin2.pk, self.roles["Admin"].pk):
                self.assertFalse(has_permission(self.admin2, cmd.FEE))  # own Deny wins
                self.assertTrue(has_permission(self.admin2, cmd.VERIFY))
            with bind_role_scope(self.dual.pk, self.roles["Student"].pk):
                self.assertTrue(has_permission(self.dual, cmd.ONBOARD))
                for code in (cmd.FEE, cmd.VERIFY, cmd.HISTORY):
                    self.assertFalse(has_permission(self.dual, code))  # Admin codes, Student context
            with bind_role_scope(self.dual.pk, self.roles["Admin"].pk):
                self.assertFalse(has_permission(self.dual, cmd.ONBOARD))
                for code in (cmd.FEE, cmd.VERIFY, cmd.HISTORY):
                    self.assertTrue(has_permission(self.dual, code))
            with bind_role_scope(self.treasurer.pk, self.roles["Treasurer"].pk):
                self.assertFalse(has_permission(self.treasurer, cmd.FEE))
        for row in (predecessor, fee_deny):
            row.refresh_from_db()
            self.assertEqual((row.effect, row.is_active), ("Deny", True))  # Denies are never changed

    def test_foreign_rows_and_grants_are_refused(self):
        self.prior()
        with approved():
            self.run3("metadata")
            self.run3("restate")
            verify = Permission.objects.get(permission_code=cmd.VERIFY)
            grant = AccountPermission.objects.create(account=self.admin2, permission=verify, effect="Grant")
            self.refused("bindings")
            grant.delete()
            foreign = RolePermission.objects.create(role=self.roles["Treasurer"],
                                                    permission=Permission.objects.get(permission_code=cmd.FEE), is_active=False)
            self.refused("bindings")  # the pinned v2.2 Treasurer fee default is never provisioned
            foreign.delete()
            self.assertEqual(self.run3("bindings"), "CREATED")
            stray = RolePermission.objects.create(role=self.roles["Instructor"], permission=verify, is_active=False)
            self.refused("activate")
            stray.delete()
            self.assertEqual(self.run3("activate"), "ACTIVATED")
        self.assertEqual(set(NEW_CODES) & set(Permission.objects.values_list("permission_code", flat=True)), set(NEW_CODES))
