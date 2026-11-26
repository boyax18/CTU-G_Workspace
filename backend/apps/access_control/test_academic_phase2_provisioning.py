"""WF-11.01 Academic Settings phase-two provisioning command (disposable MySQL only).

Run: python manage.py test apps.access_control.test_academic_phase2_provisioning --settings=config.test_settings --noinput
"""

from django.test import TestCase, override_settings

from apps.access_control.management.commands import provision_academic_settings_phase1_local_dev as phase1
from apps.access_control.management.commands import provision_academic_settings_phase2_local_dev as phase2
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.services import has_permission
from apps.accounts.active_role_context import bind_role_scope
from apps.accounts.models import Account

PASSWORD = "Harbor!Lantern5821"


class Phase2ProvisioningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.roles = {name: Role.objects.create(role_name=name) for name in ("Student", "Instructor", "Treasurer", "Admin")}
        cls.admin = cls.account("PH2-ADMIN", "Admin")
        cls.student = cls.account("PH2-STU", "Student")
        cls.instructor = cls.account("PH2-INS", "Instructor")
        cls.treasurer = cls.account("PH2-TRE", "Treasurer")
        cls.dual = cls.account("PH2-DUAL", "Student", "Admin")

    @classmethod
    def account(cls, school_id, *roles):
        account = Account.objects.create_user(school_id=school_id, password=PASSWORD, requested_role=cls.roles["Student"])
        Account.objects.filter(pk=account.pk).update(request_status="Approved", is_active=True)
        for role in roles:
            AccountRole.objects.create(account=account, role=cls.roles[role])
        return Account.objects.get(pk=account.pk)

    def phase_one(self):
        for phase in phase1.PHASES:
            phase1.run(phase=phase, actor_account_id=self.admin.pk, confirmation=phase1.TEST_CONFIRM[phase], apply=True)

    def run2(self, phase, confirmation=None, apply=True, actor=None):
        return phase2.run(phase=phase, actor_account_id=(actor or self.admin).pk,
                          confirmation=phase2.TEST_CONFIRM[phase] if confirmation is None and phase != "verify" else confirmation,
                          apply=apply)

    def refused(self, *args, **kwargs):
        before = (list(Permission.objects.values()), list(RolePermission.objects.values()), AccessAuditLog.objects.count())
        with self.assertRaises(phase2.AcademicPhase2Refused):
            self.run2(*args, **kwargs)
        self.assertEqual(before, (list(Permission.objects.values()), list(RolePermission.objects.values()),
                                  AccessAuditLog.objects.count()))

    def test_phase_two_needs_phase_one_and_provisions_exactly_the_pinned_defaults(self):
        self.refused("metadata")  # phase 1 not complete
        self.phase_one()
        services = list(Service.objects.values())
        self.refused("bindings")  # definition first
        self.refused("metadata", confirmation=phase1.TEST_CONFIRM["metadata"])
        self.refused("metadata", apply=False)
        self.refused("metadata", actor=self.student)
        self.assertEqual(self.run2("metadata"), "CREATED")
        self.assertEqual(self.run2("bindings"), "CREATED")
        self.assertFalse(has_permission(self.student, "academic.catalogue.read"))  # staged only
        self.assertEqual(self.run2("activate"), "ACTIVATED")
        self.assertEqual(self.run2("verify"), "VERIFIED")
        self.assertEqual(self.run2("activate"), "ALREADY_COMPLETE")
        # Phase 1 still verifies: it recognises exactly the receipted phase-two bindings.
        self.assertEqual(phase1.run(phase="verify", actor_account_id=self.admin.pk), "VERIFIED")
        for account in (self.student, self.instructor, self.treasurer, self.admin):
            self.assertTrue(has_permission(account, "academic.catalogue.read"), account.school_id)
        self.assertTrue(has_permission(self.admin, "clearance.teaching_assignments.manage"))
        for account in (self.student, self.instructor, self.treasurer):
            self.assertFalse(has_permission(account, "clearance.teaching_assignments.manage"))
            for code in ("academic.periods.manage", "academic.courses.manage", "clearance.subjects.manage"):
                self.assertFalse(has_permission(account, code))  # no management authority for other roles
        self.assertEqual(list(Service.objects.values()), services)  # no service created or changed
        self.assertFalse(Permission.objects.filter(permission_code__in=(
            "finance.fee_schedule.manage", "academic.enrollment_verifications.record",
            "academic.semester_onboarding.self.submit", "academic.historical_participation.correct")).exists())
        self.assertEqual(AccessAuditLog.objects.filter(action__startswith="workspace.academic_settings.p2.").count(), 9)

    def test_selected_role_context_and_deny_still_apply(self):
        self.phase_one()
        self.run2("metadata")
        catalogue = Permission.objects.get(permission_code="academic.catalogue.read")
        deny = AccountPermission.objects.create(account=self.treasurer, permission=catalogue, effect="Deny")
        self.run2("bindings")
        self.run2("activate")
        with override_settings(WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True):
            self.assert_context_rules()
        deny.refresh_from_db()
        self.assertEqual((deny.effect, deny.is_active), ("Deny", True))

    def assert_context_rules(self):
        with bind_role_scope(self.treasurer.pk, self.roles["Treasurer"].pk):
            self.assertFalse(has_permission(self.treasurer, "academic.catalogue.read"))  # the Deny wins
        with bind_role_scope(self.dual.pk, self.roles["Student"].pk):
            self.assertTrue(has_permission(self.dual, "academic.catalogue.read"))
            self.assertFalse(has_permission(self.dual, "clearance.teaching_assignments.manage"))  # Admin code, Student context
        with bind_role_scope(self.dual.pk, self.roles["Admin"].pk):
            self.assertTrue(has_permission(self.dual, "clearance.teaching_assignments.manage"))

    def test_foreign_rows_and_grants_are_refused(self):
        self.phase_one()
        self.run2("metadata")
        teaching = Permission.objects.get(permission_code="clearance.teaching_assignments.manage")
        grant = AccountPermission.objects.create(account=self.instructor, permission=teaching, effect="Grant")
        self.refused("bindings")
        grant.delete()
        foreign = RolePermission.objects.create(role=self.roles["Instructor"], permission=teaching, is_active=False)
        self.refused("bindings")
        foreign.delete()
        courses = Permission.objects.get(permission_code="academic.courses.manage")
        stray = RolePermission.objects.create(role=self.roles["Student"], permission=courses, is_active=False)
        with self.assertRaises(phase1.AcademicPhase1Refused):  # phase 1 accepts only the receipted phase-two set
            phase1.run(phase="verify", actor_account_id=self.admin.pk)
        stray.delete()
        self.assertEqual(self.run2("bindings"), "CREATED")
        self.assertEqual(phase1.run(phase="verify", actor_account_id=self.admin.pk), "VERIFIED")
