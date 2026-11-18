"""WF-03.01 D-103 Option A: runtime behaviour of the Permission Catalogue v2.2 overlay, disposable MySQL only.

Run: python manage.py test apps.access_control.test_wf0301_d103_catalogue_v22_runtime --settings=config.test_settings --noinput
The overlay is a validated specification, not provisioning: these tests load the effective v2.2 (or v2.1)
catalogue into the disposable test database only and check the unchanged evaluator. No consumer is switched
to v2.2, no route, navigation item or audit screen is added, and nothing is written to ctug_workspace.
"""

from io import StringIO
from pathlib import Path
import re
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings

from apps.access_control import framework_roles
from apps.access_control.catalogue import validation_v2_1 as v21
from apps.access_control.catalogue import validation_v2_2 as v22
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
    raise ImproperlyConfigured("D-103 runtime tests require the disposable MySQL test settings.")

TSA = "Technical Super Admin"
INSPECT = "access_control.school_access.inspect"
SCHOOL_AUDIT = "access_control.audit.school.read"
MOVED = frozenset({INSPECT, SCHOOL_AUDIT})
WF02 = frozenset({"accounts.school_accounts.read", "accounts.school_accounts.suspend", "accounts.school_accounts.activate",
                  "accounts.registration_requests.read", "accounts.authentication_events.school.read"})
V22 = v22.validate_catalogue().data
V21 = v21.validate_catalogue().data
ROOT = Path(v22.ROOT)


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


def make(roles, school_id, *names, **state):
    account = Account(school_id=school_id, request_status=state.get("status", "Approved"), is_active=state.get("active", True))
    account.set_unusable_password()
    account.save()
    UserProfile.objects.create(account=account, first_name="Ana", last_name=school_id.title())
    for name in names:
        AccountRole.objects.create(account=account, role=roles[name])
    return Account.objects.get(pk=account.pk)


class CatalogueV22RuntimeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.services, cls.permissions, cls.roles = load(V22)
        cls.school_admin = make(cls.roles, "0039001", "Instructor", "Admin")
        cls.technical = make(cls.roles, "0039002", "Instructor", "Admin", TSA)
        cls.technical_only = make(cls.roles, "0039003", TSA)
        cls.legacy = make(cls.roles, "D103-LEGACY", "Admin")
        cls.pending = make(cls.roles, "0039004", "Instructor", "Admin", TSA, status="Pending")
        cls.inactive = make(cls.roles, "0039005", "Instructor", "Admin", TSA, active=False)
        cls.superuser = Account.objects.create_superuser(school_id="D103-ROOT", password="Harbor!Lantern5821")

    def test_school_admin_has_no_access_control_permission_and_keeps_wf02(self):
        for account in (self.school_admin, self.legacy):
            with self.subTest(account=account.school_id):
                granted = get_effective_permissions(account)
                self.assertEqual({c for c in granted if c.startswith("access_control.")}, set())
                self.assertFalse(has_permission(account, INSPECT) or has_permission(account, SCHOOL_AUDIT))
                self.assertTrue(WF02 <= granted)
                self.assertFalse(has_technical_authority(account, INSPECT))
        self.assertEqual(get_effective_permissions(self.school_admin), defaults(V22, "Instructor") | defaults(V22, "Admin"))

    def test_technical_super_admin_receives_both_through_valid_composition(self):
        granted = get_effective_permissions(self.technical)
        self.assertTrue(MOVED <= granted)
        self.assertTrue(all(has_technical_authority(self.technical, code) for code in MOVED))
        self.assertEqual(granted, defaults(V22, "Instructor") | defaults(V22, "Admin") | defaults(V22, TSA))
        self.assertTrue(defaults(V22, "Admin") <= granted)  # School Admin operations through Admin membership
        self.assertTrue(WF02 <= granted)

    def test_invalid_compositions_do_not_confer_technical_authority(self):
        self.assertTrue(MOVED <= get_effective_permissions(self.technical_only))  # role binding alone ...
        self.assertFalse(any(has_technical_authority(self.technical_only, code) for code in MOVED))  # ... is not the profile
        for account in (self.pending, self.inactive):
            with self.subTest(account=account.school_id):
                self.assertEqual(get_effective_permissions(account), frozenset())
                self.assertFalse(has_technical_authority(account, INSPECT))

    def test_deny_precedence(self):
        AccountPermission.objects.create(account=self.technical, permission=self.permissions[INSPECT], effect="Deny")
        self.assertFalse(has_permission(self.technical, INSPECT))
        self.assertFalse(has_technical_authority(self.technical, INSPECT))
        self.assertTrue(has_permission(self.technical, SCHOOL_AUDIT))
        override = AccountPermission.objects.create(account=self.school_admin, permission=self.permissions[SCHOOL_AUDIT],
                                                    effect="Grant")
        self.assertTrue(has_permission(self.school_admin, SCHOOL_AUDIT))  # an explicit account Grant (existing semantics)
        self.assertFalse(has_technical_authority(self.school_admin, SCHOOL_AUDIT))  # never the technical profile
        AccountPermission.objects.filter(pk=override.pk).update(effect="Deny")
        self.assertFalse(has_permission(self.school_admin, SCHOOL_AUDIT))

    def test_disabled_service_and_inactive_roles_restrict(self):
        Service.objects.filter(service_code="access_control").update(is_active=False)
        self.assertFalse(any(c.startswith("access_control.") for c in get_effective_permissions(self.technical)))
        self.assertTrue(WF02 <= get_effective_permissions(self.school_admin))
        Service.objects.filter(service_code="access_control").update(is_active=True)
        Role.objects.filter(role_name=TSA).update(is_active=False)
        self.assertFalse(MOVED & get_effective_permissions(self.technical))
        Role.objects.filter(role_name="Admin").update(is_active=False)
        self.assertFalse(WF02 & get_effective_permissions(self.school_admin))

    def test_no_django_superuser_or_name_bypass(self):
        self.assertEqual(get_effective_permissions(self.superuser), frozenset())
        self.assertFalse(has_technical_authority(self.superuser, INSPECT))
        Account.objects.filter(pk=self.school_admin.pk).update(is_staff=True, is_superuser=True)
        flagged = Account.objects.get(pk=self.school_admin.pk)
        self.assertFalse(has_permission(flagged, INSPECT) or has_permission(flagged, SCHOOL_AUDIT))
        for value in (INSPECT.upper(), INSPECT + " ", "access_control.*", "access_control.audit.*"):
            self.assertFalse(has_permission(self.technical, value), value)

    def test_no_route_navigation_or_audit_screen_uses_the_moved_codes(self):
        """WF-12: a default binding never exposes an audit interface; nothing references the two codes."""
        sources = [p for base in ("backend/apps", "backend/config", "frontend/src") for p in (ROOT / base).rglob("*")
                   if p.suffix in {".py", ".ts", ".tsx"} and "catalogue" not in p.parts and not p.name.startswith("test_")
                   and ".test." not in p.name and "tests_support" not in p.parts]
        self.assertGreater(len(sources), 50)
        hits = [str(p.relative_to(ROOT)) for p in sources
                if re.search(r"access_control\.(school_access\.inspect|audit\.school\.read)", p.read_text(encoding="utf-8"))]
        self.assertEqual(hits, [])
        navigation = (ROOT / "frontend/src/features/dashboard/navigation.ts").read_text(encoding="utf-8")
        self.assertNotIn("audit.school", navigation)


class CatalogueV21ContrastTests(TestCase):
    def test_v21_grants_school_admin_both_codes_and_v22_does_not(self):
        _, _, roles = load(V21)
        account = make(roles, "0039011", "Instructor", "Admin")
        self.assertTrue(MOVED <= get_effective_permissions(account))
        self.assertEqual(defaults(V21, "Admin") - defaults(V22, "Admin"), MOVED)
        self.assertEqual(defaults(V22, TSA) - defaults(V21, TSA), MOVED)


class D85ProtectionTests(TransactionTestCase):
    """D-85 unchanged under v2.2: compensation refuses while the governance profile exists, and provisioning the two
    moved codes on Technical Super Admin fails closed until a separately approved D-102 implementation."""

    ROOT_ID = "D103-OPERATOR"
    PASSWORD = "Harbor!Lantern5821"
    GATES = dict(WORKSPACE_ROLE_CONFIGURATION_OPERATORS=(ROOT_ID,), WORKSPACE_ROLE_ASSIGNMENT_ENABLED=True,
                 WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False)

    def tearDown(self):
        connections.close_all()

    def test_compensation_still_refuses_and_extra_v22_rows_fail_closed(self):
        roles = {name: Role.objects.create(role_name=name, is_active=True) for name in ("Admin", "Instructor")}
        actor = make(roles, "D103-ADMIN", "Admin")
        Account.objects.create_superuser(school_id=self.ROOT_ID, password=self.PASSWORD)
        call_command("init_registration_review_metadata_local_dev", apply=True, actor_account_id=actor.pk,
                     confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO())
        call_command("init_registration_review_inactive_bindings_local_dev", apply=True, actor_account_id=actor.pk,
                     confirm_local_dev_phase2=p2.TEST_CONFIRM, stdout=StringIO())
        scope = str(actor.pk)
        fingerprint = p3e.inspect_release_gates(actor_account_id=actor.pk, expected_admin_account_ids=scope)["fingerprint"]
        with patch.object(p4, "_local_target", return_value=connections["default"]):
            self.assertEqual(p4._perform(mode="activate", actor_id=actor.pk, expected_ids=scope, fingerprint=fingerprint,
                                         confirmation=p4.LOCAL_CONFIRM), "LOCAL_ACTIVATED")
        holder = make(roles, "0039021", "Instructor")
        with override_settings(**self.GATES):
            framework_roles.configure_role(
                operation="grant-technical-super-admin", operator_school_id=self.ROOT_ID, operator_password=self.PASSWORD,
                target_id=holder.pk, confirmation=framework_roles.confirmation_for("grant-technical-super-admin", holder.pk))
        full = ",".join(str(i) for i in sorted([actor.pk, holder.pk]))

        def refusal(tamper=None):
            with transaction.atomic():
                if tamper:
                    tamper()
                try:
                    with transaction.atomic():
                        p3b._snapshot(actor_id=actor.pk, expected_ids=p3b._expected_ids(full), active=True)
                    result = None
                except p3b.ActivationExerciseRefused as exc:
                    result = str(exc)
                transaction.set_rollback(True)
            return result

        self.assertIn("An effective Technical Super Admin exists", refusal())
        definitions = {p["permission_code"]: p for p in V22["permissions"]}

        def provision(codes):
            def apply():
                for code in codes:
                    d = definitions[code]
                    permission = Permission.objects.create(
                        service=Service.objects.get(service_code="access_control"), permission_code=code,
                        permission_name=d["permission_name"], module_name=d["module_name"], action_name=d["action_name"],
                        description=d["description"])
                    RolePermission.objects.create(role=Role.objects.get(role_name=TSA), permission=permission, is_active=True)
            return apply

        for codes in ((INSPECT,), (SCHOOL_AUDIT,), (INSPECT, SCHOOL_AUDIT)):
            with self.subTest(codes=codes):
                self.assertIn("governance bindings are partial, foreign or inactive", refusal(provision(codes)) or "")
        with patch.object(p4, "_local_target", return_value=connections["default"]), \
                self.assertRaisesRegex(p3b.ActivationExerciseRefused, "An effective Technical Super Admin exists"):
            p4._perform(mode="compensate", actor_id=actor.pk, expected_ids=full, fingerprint=None,
                        confirmation=p4.LOCAL_CONFIRM)
        self.assertEqual(Service.objects.filter(is_active=True).count(), 2)
        self.assertFalse(Permission.objects.filter(permission_code__in=MOVED).exists())
