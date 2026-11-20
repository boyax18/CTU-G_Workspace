"""WF-03.01 D-89: runtime behaviour of the Permission Catalogue v2.1 overlay, disposable MySQL only.

Run: python manage.py test apps.access_control.test_wf0301_d89_catalogue_v21_runtime --settings=config.test_settings --noinput
The overlay is a validated specification, not provisioning: these tests load the effective v2.1 (or the
original v2) catalogue into the disposable test database only, then check the unchanged evaluator. No
consumer is switched to v2.1 and nothing is written to ctug_workspace.
"""

from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings

from apps.access_control import framework_roles
from apps.access_control.catalogue import validation_v2 as v2
from apps.access_control.catalogue import validation_v2_1 as v21
from apps.access_control.management.commands import (
    exercise_registration_review_activation_recovery_test_only as p3b,
    init_registration_review_inactive_bindings_local_dev as p2,
    init_registration_review_metadata_local_dev as p1,
    release_registration_review_local_dev_p4 as p4,
    report_registration_review_release_gates_p3e as p3e,
)
from apps.access_control.models import AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.services import get_effective_permissions, has_permission
from apps.access_control.technical_admin import has_technical_authority
from apps.accounts.models import Account, UserProfile

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("D-89 runtime tests require the disposable MySQL test settings.")

TSA = "Technical Super Admin"
ORDINARY = "access_control.role_assignments.ordinary.manage"
V21 = v21.validate_catalogue().data
V2 = v2.validate_manifest().data
GOVERNANCE = frozenset(V21["composition"]["application_super_admin"]["required_effective_permissions"])


def load(data):
    """Disposable test database only: every service, permission, role and default binding of one catalogue."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        assert cursor.fetchone()[0] == settings.REGISTRATION_TEST_DATABASE
    services = {s["service_code"]: Service.objects.create(service_code=s["service_code"], service_name=s["service_name"],
                                                          description=s.get("description") or "", is_active=True)
                for s in data["services"]}
    permissions = {p["permission_code"]: Permission.objects.create(
        service=services[p["service_code"]], permission_code=p["permission_code"], permission_name=p["permission_name"],
        module_name=p["module_name"], action_name=p["action_name"], description=p["description"])
        for p in data["permissions"]}
    roles = {r["role_name"]: Role.objects.create(role_name=r["role_name"], description=r["description"], is_active=True)
             for r in data["roles"]}
    for b in data["default_bindings"]:
        RolePermission.objects.create(role=roles[b["role_name"]], permission=permissions[b["permission_code"]], is_active=True)
    return services, permissions, roles


def defaults(data, role):
    return frozenset(b["permission_code"] for b in data["default_bindings"] if b["role_name"] == role)


class CatalogueV21RuntimeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.services, cls.permissions, cls.roles = load(V21)
        cls.school_admin = cls.account("0038901", "Instructor", "Admin")
        cls.technical = cls.account("0038902", "Instructor", "Admin", TSA)
        cls.technical_only = cls.account("0038903", TSA)
        cls.legacy = cls.account("D89-LEGACY", "Admin")
        cls.instructor = cls.account("0038904", "Instructor")
        cls.superuser = Account.objects.create_superuser(school_id="D89-ROOT", password="Harbor!Lantern5821")

    @classmethod
    def account(cls, school_id, *roles):
        account = Account(school_id=school_id, request_status="Approved", is_active=True)
        account.set_unusable_password()
        account.save()
        UserProfile.objects.create(account=account, first_name="Ana", last_name=school_id.title())
        for role in roles:
            AccountRole.objects.create(account=account, role=cls.roles[role])
        return Account.objects.get(pk=account.pk)

    def test_school_admin_does_not_inherit_ordinary_role_management(self):
        granted = get_effective_permissions(self.school_admin)
        self.assertFalse(has_permission(self.school_admin, ORDINARY))
        self.assertEqual({c for c in granted if c.startswith("access_control.") and c.endswith(".manage")}, set())
        self.assertEqual(granted, defaults(V21, "Instructor") | defaults(V21, "Admin"))
        self.assertFalse(has_technical_authority(self.school_admin, ORDINARY))
        self.assertFalse(has_permission(self.legacy, ORDINARY))  # the legacy Admin-only account: unchanged, no new authority
        self.assertEqual(get_effective_permissions(self.legacy), defaults(V21, "Admin"))

    def test_technical_super_admin_receives_it_through_the_binding_and_keeps_admin_operations(self):
        granted = get_effective_permissions(self.technical)
        self.assertTrue(has_permission(self.technical, ORDINARY))
        self.assertTrue(has_technical_authority(self.technical, ORDINARY))
        self.assertEqual(granted, defaults(V21, "Instructor") | defaults(V21, "Admin") | defaults(V21, TSA))
        self.assertTrue(defaults(V21, "Admin") <= granted)  # School Admin operations through Admin membership
        self.assertTrue(GOVERNANCE <= granted)
        # The role alone is not the composite profile: no Admin, no technical authority.
        self.assertTrue(has_permission(self.technical_only, ORDINARY))
        self.assertFalse(has_technical_authority(self.technical_only, ORDINARY))
        self.assertFalse(defaults(V21, "Admin") - defaults(V21, TSA) & get_effective_permissions(self.technical_only))

    def test_deny_precedence(self):
        AccountPermission.objects.create(account=self.technical, permission=self.permissions[ORDINARY], effect="Deny")
        self.assertFalse(has_permission(self.technical, ORDINARY))
        self.assertFalse(has_technical_authority(self.technical, ORDINARY))
        self.assertTrue(has_permission(self.technical, "access_control.admin_assignments.manage"))
        # A Grant to a School Admin is an account override (existing semantics), still beaten by a Deny.
        AccountPermission.objects.create(account=self.school_admin, permission=self.permissions[ORDINARY], effect="Grant")
        self.assertTrue(has_permission(self.school_admin, ORDINARY))
        self.assertFalse(has_technical_authority(self.school_admin, ORDINARY))
        AccountPermission.objects.filter(account=self.school_admin).update(effect="Deny")
        self.assertFalse(has_permission(self.school_admin, ORDINARY))

    def test_disabled_service_and_inactive_role_deny(self):
        Service.objects.filter(service_code="access_control").update(is_active=False)
        granted = get_effective_permissions(self.technical)
        self.assertFalse(any(c.startswith("access_control.") for c in granted))
        self.assertTrue({c for c in defaults(V21, "Admin") if c.startswith("accounts.")} <= granted)
        Service.objects.filter(service_code="access_control").update(is_active=True)
        Role.objects.filter(role_name=TSA).update(is_active=False)
        self.assertFalse(has_permission(self.technical, ORDINARY))
        self.assertEqual(get_effective_permissions(self.technical), defaults(V21, "Instructor") | defaults(V21, "Admin"))

    def test_no_role_name_or_framework_bypass(self):
        self.assertEqual(get_effective_permissions(self.superuser), frozenset())
        self.assertFalse(has_permission(self.superuser, ORDINARY))
        self.assertFalse(has_technical_authority(self.superuser, ORDINARY))
        self.assertEqual(get_effective_permissions(self.instructor), defaults(V21, "Instructor"))
        Account.objects.filter(pk=self.instructor.pk).update(is_staff=True, is_superuser=True)
        self.assertFalse(has_permission(Account.objects.get(pk=self.instructor.pk), ORDINARY))
        for value in (ORDINARY.upper(), ORDINARY + " ", "access_control.*", "access_control.role_assignments.*"):
            self.assertFalse(has_permission(self.technical, value), value)

    def test_wf01_wf02_permissions_are_exactly_preserved(self):
        from apps.access_control.management.commands import provision_school_accounts_local_dev as s3
        preserved = set(p1.PERMISSION_CODES) | set(s3.CODES) | {c for c in self.permissions if c.startswith("accounts.")}
        for code in preserved:
            with self.subTest(code=code):
                self.assertEqual({b["role_name"] for b in V21["default_bindings"] if b["permission_code"] == code},
                                 {b["role_name"] for b in V2["default_bindings"] if b["permission_code"] == code})
                school = defaults(V21, "Instructor") | defaults(V21, "Admin")
                self.assertEqual(has_permission(self.school_admin, code), code in school)
                self.assertEqual(has_permission(self.technical, code), code in school | defaults(V21, TSA))

    def test_d85_reads_the_same_governance_profile_under_v21(self):
        codes, definitions, role = framework_roles._governance_definitions()  # still catalogue v2 (no consumer switched)
        self.assertEqual(frozenset(codes), GOVERNANCE)
        v21_permissions = {p["permission_code"]: p for p in V21["permissions"]}
        self.assertEqual({c: dict(definitions[c]) for c in codes}, {c: _thaw(v21_permissions[c]) for c in codes})
        self.assertEqual(dict(role), _thaw(next(r for r in V21["roles"] if r["role_name"] == TSA)))
        bound = {}
        for b in V21["default_bindings"]:
            bound.setdefault(b["permission_code"], set()).add(b["role_name"])
        self.assertTrue(all(bound[c] == {TSA} for c in codes))


class CatalogueV2BaselineContrastTests(TestCase):
    """The original v2 bindings, loaded the same way, still give School Admin the ordinary-role code: the
    overlay, not a runtime change, is what removes it."""

    def test_v2_grants_and_v21_does_not(self):
        _, _, roles = load(V2)
        account = Account(school_id="0038911", request_status="Approved", is_active=True)
        account.set_unusable_password()
        account.save()
        for name in ("Instructor", "Admin"):
            AccountRole.objects.create(account=account, role=roles[name])
        self.assertTrue(has_permission(account, ORDINARY))
        self.assertEqual(defaults(V2, "Admin") - defaults(V21, "Admin"), {ORDINARY})
        self.assertEqual(defaults(V21, TSA) - defaults(V2, TSA), {ORDINARY})


class D85ProtectionTests(TransactionTestCase):
    """D-85 unchanged: compensation refuses while the governance profile exists, even with no effective
    holder, and any provisioned row outside the exact profile (such as the v2.1 ordinary-role code bound to
    the Technical Super Admin role) still fails closed. Provisioning that code is NOT authorized (D-93/D-100)."""

    ROOT = "D89-ROOT"
    PASSWORD = "Harbor!Lantern5821"
    GATES = dict(WORKSPACE_ROLE_CONFIGURATION_OPERATORS=(ROOT,), WORKSPACE_ROLE_ASSIGNMENT_ENABLED=True,
                 WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False)

    def tearDown(self):
        connections.close_all()

    def make(self, school_id, *roles):
        account = Account(school_id=school_id, request_status="Approved", is_active=True)
        account.set_unusable_password()
        account.save()
        UserProfile.objects.create(account=account, first_name="Ana", last_name=school_id.title())
        for role in roles:
            AccountRole.objects.create(account=account, role=Role.objects.get(role_name=role))
        return account

    def test_compensation_refuses_with_the_profile_and_with_any_row_outside_it(self):
        for name in ("Admin", "Instructor"):
            Role.objects.create(role_name=name, is_active=True)
        actor = self.make("D89-ADMIN", "Admin")
        Account.objects.create_superuser(school_id=self.ROOT, password=self.PASSWORD)
        call_command("init_registration_review_metadata_local_dev", apply=True, actor_account_id=actor.pk,
                     confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO())
        call_command("init_registration_review_inactive_bindings_local_dev", apply=True, actor_account_id=actor.pk,
                     confirm_local_dev_phase2=p2.TEST_CONFIRM, stdout=StringIO())
        scope = str(actor.pk)
        fingerprint = p3e.inspect_release_gates(actor_account_id=actor.pk, expected_admin_account_ids=scope)["fingerprint"]
        with patch.object(p4, "_local_target", return_value=connections["default"]):
            self.assertEqual(p4._perform(mode="activate", actor_id=actor.pk, expected_ids=scope, fingerprint=fingerprint,
                                         confirmation=p4.LOCAL_CONFIRM), "LOCAL_ACTIVATED")
        holder = self.make("0038921", "Instructor")
        with override_settings(**self.GATES):
            framework_roles.configure_role(
                operation="grant-technical-super-admin", operator_school_id=self.ROOT, operator_password=self.PASSWORD,
                target_id=holder.pk, confirmation=framework_roles.confirmation_for("grant-technical-super-admin", holder.pk))
        full = ",".join(str(i) for i in sorted([actor.pk, holder.pk]))

        def refusal(tamper=None, scope_ids=full):
            with transaction.atomic():
                if tamper:
                    tamper()
                try:
                    with transaction.atomic():
                        p3b._snapshot(actor_id=actor.pk, expected_ids=p3b._expected_ids(scope_ids), active=True)
                    result = None
                except p3b.ActivationExerciseRefused as exc:
                    result = str(exc)
                transaction.set_rollback(True)
            return result

        self.assertIn("An effective Technical Super Admin exists", refusal())
        self.assertIn("A Technical Super Admin assignment exists",
                      refusal(lambda: AccountRole.objects.filter(account=holder, role__role_name="Admin").delete(), scope))
        self.assertIn("The governance profile depends on the shared access_control service",
                      refusal(lambda: AccountRole.objects.filter(role__role_name=TSA).delete()))

        def provision_ordinary_code():
            d = next(p for p in V21["permissions"] if p["permission_code"] == ORDINARY)
            permission = Permission.objects.create(
                service=Service.objects.get(service_code="access_control"), permission_code=ORDINARY,
                permission_name=d["permission_name"], module_name=d["module_name"], action_name=d["action_name"],
                description=d["description"])
            RolePermission.objects.create(role=Role.objects.get(role_name=TSA), permission=permission, is_active=True)

        self.assertIn("governance bindings are partial, foreign or inactive", refusal(provision_ordinary_code) or "")
        with patch.object(p4, "_local_target", return_value=connections["default"]), \
                self.assertRaises(p3b.ActivationExerciseRefused):
            p4._perform(mode="compensate", actor_id=actor.pk, expected_ids=full, fingerprint=None,
                        confirmation=p4.LOCAL_CONFIRM)
        self.assertEqual(Service.objects.filter(is_active=True).count(), 2)
        self.assertFalse(Permission.objects.filter(permission_code=ORDINARY).exists())


def _thaw(value):
    if type(value).__name__ == "mappingproxy" or isinstance(value, dict):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value
