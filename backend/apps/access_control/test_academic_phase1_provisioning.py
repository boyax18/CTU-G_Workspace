"""WF-11.01 Academic Settings phase-one provisioning command (disposable MySQL only).

Run: python manage.py test apps.access_control.test_academic_phase1_provisioning --settings=config.test_settings --noinput
"""

from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.access_control.management.commands import provision_academic_settings_phase1_local_dev as cmd
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service,
)
from apps.access_control.services import has_permission
from apps.accounts.models import Account

PASSWORD = "Harbor!Lantern5821"


def confirm(phase):
    return cmd.TEST_CONFIRM[phase]


class Phase1ProvisioningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.roles = {name: Role.objects.create(role_name=name) for name in ("Student", "Instructor", "Treasurer", "Admin")}
        cls.other_service = Service.objects.create(service_code="accounts", service_name="Accounts")
        cls.other_perm = Permission.objects.create(service=cls.other_service, permission_code="accounts.profile.self.read",
                                                   permission_name="read", module_name="profile", action_name="read")
        RolePermission.objects.create(role=cls.roles["Student"], permission=cls.other_perm)
        cls.admin = cls.account("PH1-ADMIN", "Admin")
        cls.admin2 = cls.account("PH1-ADMIN2", "Admin")
        cls.student = cls.account("PH1-STU", "Student")
        cls.other_deny = AccountPermission.objects.create(account=cls.student, permission=cls.other_perm, effect="Deny")

    @classmethod
    def account(cls, school_id, *roles):
        account = Account.objects.create_user(school_id=school_id, password=PASSWORD, requested_role=cls.roles["Student"])
        Account.objects.filter(pk=account.pk).update(request_status="Approved", is_active=True)
        for role in roles:
            AccountRole.objects.create(account=account, role=cls.roles[role])
        return Account.objects.get(pk=account.pk)

    def run_phase(self, phase, actor=None, confirmation=None, apply=True):
        return cmd.run(phase=phase, actor_account_id=(actor or self.admin).pk,
                       confirmation=confirm(phase) if confirmation is None and phase != "verify" else confirmation,
                       apply=apply)

    def refused(self, *args, **kwargs):
        before = (list(Service.objects.values()), list(Permission.objects.values()), list(RolePermission.objects.values()),
                  AccessAuditLog.objects.count())
        with self.assertRaises(cmd.AcademicPhase1Refused):
            self.run_phase(*args, **kwargs)
        self.assertEqual(before, (list(Service.objects.values()), list(Permission.objects.values()),
                                  list(RolePermission.objects.values()), AccessAuditLog.objects.count()))

    def outside(self):
        return (list(Service.objects.exclude(service_code__in=cmd.SERVICE_CODES).values()),
                list(Permission.objects.exclude(permission_code__in=cmd.CODES).values()),
                list(RolePermission.objects.exclude(permission__permission_code__in=cmd.CODES).values()),
                list(AccountRole.objects.values()), list(AccountPermission.objects.values()))

    def test_the_three_phases_provision_exactly_the_reviewed_minimum(self):
        outside = self.outside()
        self.refused("verify")  # nothing to verify yet: refuse, never repair
        self.assertEqual(self.run_phase("metadata"), "CREATED")
        services = {s.service_code: s for s in Service.objects.filter(service_code__in=cmd.SERVICE_CODES)}
        self.assertEqual({c: s.is_active for c, s in services.items()}, {"academic": False, "clearance": False})
        self.assertEqual(services["academic"].service_name, "Academic Administration")
        perms = {p.permission_code: p for p in Permission.objects.filter(permission_code__in=cmd.CODES)}
        self.assertEqual(set(perms), set(cmd.CODES))
        self.assertEqual(perms["clearance.subjects.manage"].service_id, services["clearance"].pk)
        self.assertEqual(self.run_phase("metadata"), "ALREADY_COMPLETE")
        self.assertEqual(self.run_phase("bindings"), "CREATED")
        self.assertFalse(any(has_permission(self.admin, code) for code in cmd.CODES))  # staged, not active
        self.assertEqual(self.run_phase("activate"), "ACTIVATED")
        self.assertEqual(self.run_phase("verify"), "VERIFIED")
        self.assertEqual(self.run_phase("activate"), "ALREADY_COMPLETE")
        bindings = RolePermission.objects.filter(permission__permission_code__in=cmd.CODES)
        self.assertEqual({(b.role_id, b.is_active, b.granted_by_id) for b in bindings},
                         {(self.roles["Admin"].pk, True, self.admin.pk)})
        self.assertEqual(bindings.count(), 5)
        for code in cmd.CODES:
            self.assertTrue(has_permission(self.admin, code), code)
            self.assertTrue(has_permission(self.admin2, code), code)  # every genuine Admin, no account change
            self.assertFalse(has_permission(self.student, code), code)  # catalogue.read is Admin-only in phase 1
        self.assertEqual(AccessAuditLog.objects.filter(action__startswith="workspace.academic_settings.").count(), 19)
        self.assertEqual(self.outside(), outside)  # other services, definitions, bindings, assignments, Grants, Denies

    def test_refusals_leave_no_trace(self):
        self.refused("metadata", confirmation="ctug_workspace:WF-11.01:PHASE1:METADATA")  # the dev phrase in test settings
        self.refused("metadata", confirmation=confirm("bindings"))
        self.refused("metadata", apply=False)
        self.refused("metadata", actor=self.student)
        self.refused("bindings")  # metadata first
        with override_settings(WORKSPACE_ACADEMIC_PERIODS_ENABLED=True):
            self.refused("metadata")  # switches stay off while provisioning
        with patch.object(cmd.MigrationRecorder, "applied_migrations", return_value={}):
            self.refused("metadata")  # the seven migrations must be applied first
        with self.assertRaises(CommandError):
            call_command("provision_academic_settings_phase1_local_dev", phase="metadata", actor_account_id=self.admin.pk)
        self.assertFalse(Service.objects.filter(service_code__in=cmd.SERVICE_CODES).exists())

    def test_foreign_rows_and_account_grants_are_never_repaired(self):
        self.run_phase("metadata")
        catalogue = Permission.objects.get(permission_code="academic.catalogue.read")
        foreign = RolePermission.objects.create(role=self.roles["Student"], permission=catalogue, is_active=False)
        self.refused("bindings")
        foreign.delete()
        grant = AccountPermission.objects.create(account=self.student, permission=catalogue, effect="Grant")
        self.refused("bindings")
        grant.delete()
        self.assertEqual(self.run_phase("bindings"), "CREATED")

    def test_an_existing_deny_is_preserved_and_still_wins(self):
        self.run_phase("metadata")
        periods = Permission.objects.get(permission_code="academic.periods.manage")
        deny = AccountPermission.objects.create(account=self.admin2, permission=periods, effect="Deny")
        self.run_phase("bindings")
        self.run_phase("activate")
        self.assertFalse(has_permission(self.admin2, "academic.periods.manage"))
        self.assertTrue(has_permission(self.admin2, "academic.courses.manage"))
        deny.refresh_from_db()
        self.assertEqual((deny.effect, deny.is_active), ("Deny", True))
        self.other_deny.refresh_from_db()
        self.assertTrue(self.other_deny.is_active)
