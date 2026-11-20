"""WF-03.01 Stage D, D-85: P3B/P4 compensation compatibility with the Technical Super Admin governance rows.

Run: python manage.py test apps.access_control.test_wf0301_d85_p3b_compatibility --settings=config.test_settings --noinput
Disposable MySQL ONLY; synthetic accounts. Every state is produced by the real P1, P2, P4, WF-02.05 and
Django-Superuser (framework_roles.configure_role) code paths; tampering uses direct ORM writes inside a
rolled-back transaction, and P4 compensation is executed for real where it is permitted (TC-035).
"""

import threading
import time
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connections, transaction
from django.test import TransactionTestCase, override_settings

from apps.access_control import framework_roles
from apps.access_control.catalogue.validation_v2 import validate_manifest
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
from apps.access_control.role_management import RoleChangeUnavailable
from apps.access_control.services import get_effective_permissions
from apps.access_control.technical_admin import has_technical_authority
from apps.access_control.writer_boundary import WriterBoundaryUnavailable
from apps.accounts.models import Account, UserProfile

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("D-85 compatibility tests require the disposable MySQL test settings.")

PASSWORD = "Harbor!Lantern5821"
ROOT = "D85-ROOT"
GATES = dict(WORKSPACE_ROLE_CONFIGURATION_OPERATORS=(ROOT,), WORKSPACE_ROLE_ASSIGNMENT_ENABLED=True,
             WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False)
TSA = "Technical Super Admin"
GOVERNANCE = frozenset(validate_manifest().data["composition"]["application_super_admin"]["required_effective_permissions"])
SCHOOL = frozenset(s3.CODES)
REGISTRATION = frozenset(p1.PERMISSION_CODES)

EFFECTIVE = "An effective Technical Super Admin exists"
ASSIGNED = "A Technical Super Admin assignment exists"
SHARED = "The governance profile depends on the shared access_control service"
DEFINITIONS = "governance definitions are partial or differ"
BINDINGS = "governance bindings are partial, foreign or inactive"
COUNTS = "Governance receipts are missing or duplicated"
OPERATOR = "Governance receipts are not from one framework operator"
MISMATCH = "Governance receipts do not match the governance rows"
ORDER = "Governance receipts are out of order or precede the registration release"
ORPHAN = "Governance evidence or bindings exist without their definitions"


class D85CompatibilityTests(TransactionTestCase):
    def setUp(self):
        self.roles = {n: Role.objects.create(role_name=n, is_active=True) for n in ("Admin", "Student", "Instructor")}
        self.actor = self.account("D85-ADMIN", "Admin")
        self.student = self.account("7285001", "Student")
        self.root = Account.objects.create_superuser(school_id=ROOT, password=PASSWORD)

    def tearDown(self):
        connections.close_all()

    def account(self, school_id, *roles):
        account = Account(school_id=school_id, request_status="Approved", is_active=True)
        account.set_unusable_password()
        account.save()
        UserProfile.objects.create(account=account, first_name="Ana", last_name=school_id.title())
        for role in roles:
            AccountRole.objects.create(account=account, role=self.roles[role])
        return Account.objects.get(pk=account.pk)

    # -- real code paths -------------------------------------------------------------------------
    def scope(self, *accounts):
        return ",".join(str(a.pk) for a in sorted((self.actor, *accounts), key=lambda a: a.pk))

    def release(self, *phases):
        call_command("init_registration_review_metadata_local_dev", apply=True, actor_account_id=self.actor.pk,
                     confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO())
        call_command("init_registration_review_inactive_bindings_local_dev", apply=True, actor_account_id=self.actor.pk,
                     confirm_local_dev_phase2=p2.TEST_CONFIRM, stdout=StringIO())
        scope = self.scope()
        fingerprint = p3e.inspect_release_gates(actor_account_id=self.actor.pk, expected_admin_account_ids=scope)["fingerprint"]
        self.assertEqual(self.p4("activate", scope, fingerprint), "LOCAL_ACTIVATED")
        for phase in phases:
            call_command("provision_school_accounts_local_dev", phase=phase, actor_account_id=self.actor.pk,
                         apply=True, confirm=s3.TEST_CONFIRM[phase], stdout=StringIO())

    def p4(self, mode, scope, fingerprint=None):
        with patch.object(p4, "_local_target", return_value=connections["default"]):
            return p4._perform(mode=mode, actor_id=self.actor.pk, expected_ids=scope, fingerprint=fingerprint,
                               confirmation=p4.LOCAL_CONFIRM)

    def preview(self, scope):
        with patch.object(p4, "_local_target", return_value=connections["default"]):
            return p3d._check_compensation_preview(actor_account_id=self.actor.pk, expected_admin_account_ids=scope)

    def configure(self, operation, target):
        with override_settings(**GATES):  # only the superuser procedure; P1/P2/P4 run under the real test settings
            return framework_roles.configure_role(
                operation=operation, operator_school_id=ROOT, operator_password=PASSWORD, target_id=target.pk,
                confirmation=framework_roles.confirmation_for(operation, target.pk))

    def governed(self, *phases):
        """Registration release (+ optional school-account phases) + one real Technical Super Admin grant."""
        self.release(*phases)
        holder = self.account("0038501", "Instructor")
        self.configure("grant-technical-super-admin", holder)
        self.assertTrue(all(has_technical_authority(holder, code) for code in GOVERNANCE))
        return holder

    # -- observed state ---------------------------------------------------------------------------
    def everything(self):
        return (list(Service.objects.order_by("pk").values()), list(Role.objects.order_by("pk").values()),
                list(Permission.objects.order_by("pk").values()), list(RolePermission.objects.order_by("pk").values()),
                list(AccountRole.objects.order_by("pk").values()), list(AccessAuditLog.objects.order_by("pk").values()),
                list(Account.objects.order_by("pk").values("pk", "is_active")))

    def governance_state(self):
        return (list(Permission.objects.filter(permission_code__in=GOVERNANCE).order_by("pk").values()),
                list(RolePermission.objects.filter(role__role_name=TSA).order_by("pk").values()),
                list(AccessAuditLog.objects.filter(action__in=(framework_roles.ROLE_CREATE, framework_roles.PERMISSION_CREATE,
                                                               framework_roles.BINDING_CREATE)).order_by("pk").values()))

    def refused(self, scope, message):
        """Both the read-only P3D preview and a real P4 compensation refuse with this reason; nothing changes."""
        before = self.everything()
        with self.assertRaisesRegex(p3b.ActivationExerciseRefused, message):
            self.preview(scope)
        with self.assertRaisesRegex(p3b.ActivationExerciseRefused, message):
            self.p4("compensate", scope)
        self.assertEqual(self.everything(), before)
        self.assertEqual(Service.objects.filter(is_active=True).count(), 2)

    def refusal(self, scope, tamper=None):
        """The exact compensation pre-check refusal after an optional tamper; the tamper is always rolled back."""
        before = self.everything()
        with transaction.atomic():
            if tamper is not None:
                tamper()
            try:
                with transaction.atomic():
                    p3b._snapshot(actor_id=self.actor.pk, expected_ids=p3b._expected_ids(scope), active=True)
                result = None
            except p3b.ActivationExerciseRefused as exc:
                result = str(exc)
            transaction.set_rollback(True)
        self.assertEqual(self.everything(), before)
        return result

    def assert_compensated(self, preserved):
        self.assertEqual(Service.objects.filter(is_active=True).count(), 0)
        self.assertFalse(RolePermission.objects.filter(permission__permission_code__in=REGISTRATION, is_active=True).exists())
        self.assertEqual(AccessAuditLog.objects.filter(action=p3b.SERVICE_DEACTIVATE).count(), 2)
        self.assertEqual(AccessAuditLog.objects.filter(action=p3b.BINDING_DEACTIVATE).count(), 3)
        for log in AccessAuditLog.objects.filter(action=p3b.BINDING_DEACTIVATE):
            self.assertIn(log.permission.permission_code, REGISTRATION)
        self.assertEqual(self.governance_state(), preserved)
        for account in Account.objects.all():
            self.assertFalse(get_effective_permissions(account) & (REGISTRATION | SCHOOL | GOVERNANCE), account.school_id)

    # -- 1. permitted compensation is unchanged --------------------------------------------------
    def test_registration_only_compensation(self):
        self.release()
        self.assertEqual(self.preview(self.scope()), 1)
        self.assertEqual(self.p4("compensate", self.scope()), "LOCAL_COMPENSATED")
        self.assert_compensated(([], [], []))

    def test_registration_and_school_account_compensation(self):
        self.release("metadata", "bindings", "activate")
        school = list(RolePermission.objects.filter(permission__permission_code__in=SCHOOL).order_by("pk").values())
        self.assertEqual(len(school), 3)
        self.assertEqual(self.p4("compensate", self.scope()), "LOCAL_COMPENSATED")
        self.assert_compensated(([], [], []))
        self.assertEqual(list(RolePermission.objects.filter(permission__permission_code__in=SCHOOL).order_by("pk").values()),
                         school)

    def test_additional_school_admin_requires_the_exact_scope(self):
        self.release("metadata", "bindings", "activate")
        second = self.account("0038502", "Instructor")
        self.configure("grant-school-admin", second)
        self.refused(self.scope(), "Eligible Admin accounts differ")
        self.assertEqual(self.preview(self.scope(second)), 2)
        self.assertEqual(self.p4("compensate", self.scope(second)), "LOCAL_COMPENSATED")
        self.assert_compensated(([], [], []))
        self.assertEqual(sorted(AccountRole.objects.filter(account=second).values_list("role__role_name", flat=True)),
                         ["Admin", "Instructor"])

    def test_a_bare_inactive_technical_role_row_is_still_tolerated(self):
        self.release()
        Role.objects.create(role_name=TSA, is_active=False)  # e.g. the dormant protected-executor fixture
        self.assertEqual(self.p4("compensate", self.scope()), "LOCAL_COMPENSATED")

    def test_role_assignments_without_the_governance_profile_keep_the_original_behaviour(self):
        # WF-02.05 fixtures hold a bare Technical Super Admin role (no governance permissions), one holder
        # inside the Admin scope. With no governance rows nobody can be effective: activation and
        # compensation behave exactly as before D-85 (this check also runs on P4's post-activation snapshot).
        self.roles[TSA] = Role.objects.create(role_name=TSA, is_active=True)
        both = self.account("D85-TSA-ADMIN", "Admin", TSA)
        self.account("D85-TSA-ONLY", TSA)
        call_command("init_registration_review_metadata_local_dev", apply=True, actor_account_id=self.actor.pk,
                     confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO())
        call_command("init_registration_review_inactive_bindings_local_dev", apply=True, actor_account_id=self.actor.pk,
                     confirm_local_dev_phase2=p2.TEST_CONFIRM, stdout=StringIO())
        scope = self.scope(both)
        fingerprint = p3e.inspect_release_gates(actor_account_id=self.actor.pk, expected_admin_account_ids=scope)["fingerprint"]
        self.assertEqual(self.p4("activate", scope, fingerprint), "LOCAL_ACTIVATED")
        self.assertEqual(self.preview(scope), 2)
        self.assertEqual(self.p4("compensate", scope), "LOCAL_COMPENSATED")
        self.assert_compensated(([], [], []))

    # -- 2. the exact governance profile is recognized, and compensation refuses ------------------
    def test_six_valid_governance_permissions_are_verified_exactly_and_compensation_refuses(self):
        holder = self.governed("metadata", "bindings", "activate")
        scope = self.scope(holder)
        with transaction.atomic():
            services = {s.service_code: s for s in Service.objects.select_for_update()}
            released = AccessAuditLog.objects.filter(action=p3b.BINDING_ACTIVATE).order_by("-pk").first().pk
            rows, bindings = p3b._governed_governance_profile(
                permission_rows=list(Permission.objects.order_by("pk")), binding_rows=list(RolePermission.objects.order_by("pk")),
                services=services, released=released)
            self.assertEqual(set(rows), GOVERNANCE)
            self.assertEqual(len(bindings), 6)
            self.assertTrue(all(b.is_active and b.role.role_name == TSA for b in bindings))
            p3b._assert_effective_permissions(p3b._expected_ids(scope), active=True)  # governance only for the holder
        self.assertEqual(self.refusal(scope), EFFECTIVE + "; compensation refused.")
        self.refused(scope, EFFECTIVE)
        self.assertEqual(Permission.objects.count(), 3 + 3 + 6)
        self.assertEqual(AccessAuditLog.objects.filter(action=framework_roles.ROLE_CREATE).count(), 1)
        self.assertEqual(AccessAuditLog.objects.filter(action=framework_roles.PERMISSION_CREATE).count(), 6)
        self.assertEqual(AccessAuditLog.objects.filter(action=framework_roles.BINDING_CREATE).count(), 6)
        # WF-02.05 safeguards unchanged: the companion verification still passes and its rows are untouched.
        call_command("provision_school_accounts_local_dev", phase="verify", actor_account_id=self.actor.pk, stdout=StringIO())
        self.assertTrue(all(has_technical_authority(holder, code) for code in GOVERNANCE))

    def test_governance_without_school_accounts_reaches_the_technical_refusal(self):
        holder = self.governed()
        self.refused(self.scope(holder), EFFECTIVE)
        self.refused(self.scope(), "Eligible Admin accounts differ")  # the holder is also a School Admin

    def test_any_assignment_or_the_profile_alone_refuses_compensation(self):
        holder = self.governed("metadata", "bindings", "activate")
        tsa = Role.objects.get(role_name=TSA)
        admin = self.roles["Admin"]
        # Not effective (Admin removed), but assigned: still refused (race-safe, stricter than effective).
        self.assertEqual(self.refusal(self.scope(), lambda: AccountRole.objects.filter(account=holder, role=admin).delete()),
                         ASSIGNED + "; compensation refused.")
        # Not effective (deactivated account), but assigned: refused.
        self.assertEqual(self.refusal(self.scope(), lambda: Account.objects.filter(pk=holder.pk).update(is_active=False)),
                         ASSIGNED + "; compensation refused.")
        # No holder at all: the profile still depends on the shared access_control service.
        self.assertEqual(self.refusal(self.scope(holder), lambda: AccountRole.objects.filter(role=tsa).delete()),
                         SHARED + "; compensation refused.")
        # A Deny on the holder: refused by the unchanged account-override safeguard.
        self.assertIn("Account-level overrides", self.refusal(self.scope(holder), lambda: AccountPermission.objects.create(
            account=holder, permission=Permission.objects.get(permission_code="access_control.audit.read"), effect="Deny")))
        self.refused(self.scope(holder), EFFECTIVE)

    # -- 3. tampered definitions, bindings and receipts -------------------------------------------
    def test_tampered_definitions_and_bindings_are_refused(self):
        holder = self.governed("metadata", "bindings", "activate")
        scope = self.scope(holder)
        tsa = Role.objects.get(role_name=TSA)
        gov = {p.permission_code: p for p in Permission.objects.filter(permission_code__in=GOVERNANCE)}
        audit = gov["access_control.audit.read"]
        services = {s.service_code: s for s in Service.objects.all()}

        def missing():
            RolePermission.objects.filter(permission=audit).delete()
            AccessAuditLog.objects.filter(permission=audit).delete()
            Permission.objects.filter(pk=audit.pk).delete()

        def extra_bound():
            extra = Permission.objects.create(service=services["access_control"], permission_code="access_control.extra.read",
                                              permission_name="Extra", module_name="extra", action_name="read")
            RolePermission.objects.create(role=tsa, permission=extra, granted_by=self.root)

        cases = {
            "missing code": (missing, DEFINITIONS),
            "unexpected unbound code": (lambda: Permission.objects.create(
                service=services["access_control"], permission_code="access_control.extra.read", permission_name="Extra",
                module_name="extra", action_name="read"), "Unexpected or missing catalogue rows"),
            "unexpected code bound to the technical role": (extra_bound, BINDINGS),
            "altered description": (lambda: Permission.objects.filter(pk=audit.pk).update(description="Changed"), DEFINITIONS),
            "altered name": (lambda: Permission.objects.filter(pk=audit.pk).update(permission_name="Changed"), DEFINITIONS),
            "wrong service": (lambda: Permission.objects.filter(pk=audit.pk).update(service=services["accounts"]), DEFINITIONS),
            "inactive role": (lambda: Role.objects.filter(pk=tsa.pk).update(is_active=False), DEFINITIONS),
            "altered role description": (lambda: Role.objects.filter(pk=tsa.pk).update(description="Changed"), DEFINITIONS),
            "foreign binding": (lambda: RolePermission.objects.create(role=self.roles["Admin"], permission=audit,
                                                                      granted_by=self.root), BINDINGS),
            "inactive binding": (lambda: RolePermission.objects.filter(permission=audit).update(is_active=False), BINDINGS),
            "missing binding": (lambda: RolePermission.objects.filter(permission=audit).delete(), BINDINGS),
        }
        for name, (tamper, message) in cases.items():
            with self.subTest(name):
                self.assertIn(message, self.refusal(scope, tamper) or "")
        self.refused(scope, EFFECTIVE)

    def test_tampered_receipts_are_refused(self):
        holder = self.governed("metadata", "bindings", "activate")
        scope = self.scope(holder)
        fr = framework_roles
        receipts = lambda action: AccessAuditLog.objects.filter(action=action).order_by("pk")  # noqa: E731
        first_binding = receipts(fr.BINDING_CREATE).first()

        def copy(log, **changes):
            fields = {f.attname: getattr(log, f.attname) for f in AccessAuditLog._meta.concrete_fields
                      if not f.primary_key}
            fields.update(changes)
            return AccessAuditLog.objects.create(**fields)

        def reordered():
            role_receipt = receipts(fr.ROLE_CREATE).get()
            copy(role_receipt)
            AccessAuditLog.objects.filter(pk=role_receipt.pk).delete()

        def forged_with_a_deleted_original():
            log = receipts(fr.PERMISSION_CREATE).first()
            AccessAuditLog.objects.filter(pk=log.pk).delete()
            copy(log, new_value={"permission_id": log.permission_id, "service_id": log.new_value["service_id"] + 1000})

        cases = {
            "missing role receipt": (lambda: receipts(fr.ROLE_CREATE).delete(), COUNTS),
            "missing permission receipt": (lambda: AccessAuditLog.objects.filter(
                pk=receipts(fr.PERMISSION_CREATE).last().pk).delete(), COUNTS),
            "missing binding receipt": (lambda: AccessAuditLog.objects.filter(pk=first_binding.pk).delete(), COUNTS),
            "duplicated permission receipt": (lambda: copy(receipts(fr.PERMISSION_CREATE).first()), COUNTS),
            "duplicated binding receipt": (lambda: copy(first_binding), COUNTS),
            "forged binding identity": (lambda: receipts(fr.BINDING_CREATE).filter(pk=first_binding.pk).update(
                new_value={**first_binding.new_value, "role_permission_id": first_binding.new_value["role_permission_id"] + 1000}),
                MISMATCH),
            "forged permission subject": (forged_with_a_deleted_original, MISMATCH),
            "binding receipt for another permission": (lambda: receipts(fr.BINDING_CREATE).filter(pk=first_binding.pk).update(
                permission=Permission.objects.get(permission_code="accounts.school_accounts.read")), MISMATCH),
            "receipt with a target account": (lambda: receipts(fr.ROLE_CREATE).update(target_account=holder), MISMATCH),
            "receipt with a prior value": (lambda: receipts(fr.ROLE_CREATE).update(old_value={"is_active": False}), MISMATCH),
            "receipt with another reason": (lambda: receipts(fr.ROLE_CREATE).update(reason="assignment_change"), MISMATCH),
            "receipt/DB disagreement (granted_by)": (lambda: RolePermission.objects.filter(
                pk=first_binding.new_value["role_permission_id"]).update(granted_by=self.actor), MISMATCH),
            "one receipt from another actor": (lambda: receipts(fr.ROLE_CREATE).update(actor_account=self.actor), OPERATOR),
            "all receipts from a non-framework actor": (lambda: AccessAuditLog.objects.filter(action__in=(
                fr.ROLE_CREATE, fr.PERMISSION_CREATE, fr.BINDING_CREATE)).update(actor_account=self.actor), OPERATOR),
            "framework operator holding a role": (lambda: AccountRole.objects.create(
                account=self.root, role=Role.objects.get(role_name=TSA)), OPERATOR),
            "reordered role receipt": (reordered, ORDER),
        }
        for name, (tamper, message) in cases.items():
            with self.subTest(name):
                self.assertIn(message, self.refusal(scope, tamper) or "")
        # Stale: evidence that does not follow the registration P4 activation.
        with transaction.atomic():
            for released in (None, AccessAuditLog.objects.order_by("-pk").first().pk):
                with self.subTest(released=released), self.assertRaisesRegex(p3b.ActivationExerciseRefused, ORDER):
                    p3b._governed_governance_profile(
                        permission_rows=list(Permission.objects.order_by("pk")),
                        binding_rows=list(RolePermission.objects.order_by("pk")),
                        services={s.service_code: s for s in Service.objects.all()}, released=released)
        self.refused(scope, EFFECTIVE)

    def test_governance_evidence_without_definitions_is_refused(self):
        self.release("metadata", "bindings", "activate")
        registration = Permission.objects.get(permission_code=sorted(REGISTRATION)[0])
        self.assertIn(ORPHAN, self.refusal(self.scope(), lambda: AccessAuditLog.objects.create(
            actor_account=self.root, permission=registration, action=framework_roles.PERMISSION_CREATE,
            new_value={"permission_id": registration.pk, "service_id": registration.service_id}, reason="permission_change")))

        def bound_bare_role():
            role = Role.objects.create(role_name=TSA, is_active=True)
            RolePermission.objects.create(role=role, permission=Permission.objects.get(permission_code=sorted(SCHOOL)[0]),
                                          granted_by=self.root)
        self.assertIn(ORPHAN, self.refusal(self.scope(), bound_bare_role))
        self.assertEqual(self.p4("compensate", self.scope()), "LOCAL_COMPENSATED")

    def test_governance_codes_are_effective_only_for_the_composite_holder(self):
        holder = self.governed()
        scope = p3b._expected_ids(self.scope(holder))
        code = Permission.objects.get(permission_code="access_control.audit.read")
        for name, account in (("School Admin actor", self.actor), ("student", self.student)):
            with self.subTest(name), transaction.atomic():
                AccountPermission.objects.create(account=account, permission=code, effect="Grant")
                with self.assertRaisesRegex(p3b.ActivationExerciseRefused, "Unexpected effective permission"):
                    p3b._assert_effective_permissions(scope, active=True)
                transaction.set_rollback(True)
        with transaction.atomic():
            p3b._assert_effective_permissions(scope, active=True)

    # -- 4. concurrency, rollback and the protected writer ----------------------------------------
    def run_in_thread(self, fn, results, key):
        def target():
            try:
                results[key] = fn()
            except Exception as exc:  # recorded and asserted by the caller
                results[key] = exc
            finally:
                connections.close_all()
        thread = threading.Thread(target=target)
        thread.start()
        return thread

    def test_a_grant_waits_for_compensation_and_then_finds_the_services_inactive(self):
        self.release("metadata", "bindings", "activate")
        holder = self.account("0038503", "Instructor")
        self.configure("grant-school-admin", holder)
        scope = self.scope(holder)
        locked, go, results = threading.Event(), threading.Event(), {}
        original = p3b._assert_no_governance_profile

        def paused():
            original()
            locked.set()
            go.wait(30)

        with patch.object(p3b, "_assert_no_governance_profile", paused):
            comp = self.run_in_thread(lambda: self.p4("compensate", scope), results, "compensate")
            self.assertTrue(locked.wait(30))
            grant = self.run_in_thread(lambda: self.configure("grant-technical-super-admin", holder), results, "grant")
            time.sleep(1.5)
            self.assertTrue(grant.is_alive(), "the grant must wait for the compensation's service-row locks")
            go.set()
            comp.join(60)
            grant.join(60)
        self.assertEqual(results["compensate"], "LOCAL_COMPENSATED")
        self.assertIsInstance(results["grant"], RoleChangeUnavailable)
        self.assert_compensated(([], [], []))
        self.assertFalse(Role.objects.filter(role_name=TSA).exists())

    def test_compensation_waits_for_a_grant_and_then_refuses(self):
        self.release("metadata", "bindings", "activate")
        holder = self.account("0038504", "Instructor")
        self.configure("grant-school-admin", holder)
        scope = self.scope(holder)
        locked, go, results = threading.Event(), threading.Event(), {}
        original = framework_roles._ensure_governance

        def paused(operator, services):
            value = original(operator, services)
            locked.set()
            go.wait(30)
            return value

        with patch.object(framework_roles, "_ensure_governance", paused):
            grant = self.run_in_thread(lambda: self.configure("grant-technical-super-admin", holder), results, "grant")
            self.assertTrue(locked.wait(30))
            comp = self.run_in_thread(lambda: self.p4("compensate", scope), results, "compensate")
            time.sleep(1.5)
            self.assertTrue(comp.is_alive(), "the compensation must wait for the grant's locks")
            go.set()
            grant.join(60)
            comp.join(60)
        self.assertEqual(results["grant"], {"account_id": holder.pk, "operation": "grant-technical-super-admin"})
        self.assertIsInstance(results["compensate"], p3b.ActivationExerciseRefused)
        self.assertIn(EFFECTIVE, str(results["compensate"]))
        self.assertEqual(Service.objects.filter(is_active=True).count(), 2)
        self.assertFalse(AccessAuditLog.objects.filter(action__in=(p3b.SERVICE_DEACTIVATE, p3b.BINDING_DEACTIVATE)).exists())
        self.assertTrue(all(has_technical_authority(holder, code) for code in GOVERNANCE))

    def test_a_failure_after_the_compensation_writes_rolls_everything_back(self):
        self.release("metadata", "bindings", "activate")
        before = self.everything()
        calls = []
        original = p3b._assert_effective_permissions

        def fail_after_writes(scope, *, active):
            calls.append(active)
            if not active:
                raise p3b.ActivationExerciseRefused("injected failure after the writes")
            return original(scope, active=active)

        with patch.object(p3b, "_assert_effective_permissions", fail_after_writes), \
                self.assertRaisesRegex(p3b.ActivationExerciseRefused, "injected"):
            self.p4("compensate", self.scope())
        self.assertEqual(calls, [True, False])
        self.assertEqual(self.everything(), before)
        self.assertEqual(self.p4("compensate", self.scope()), "LOCAL_COMPENSATED")

    def test_the_protected_writer_refuses_the_grant_and_nothing_changes(self):
        self.release()
        holder = self.account("0038505", "Instructor")
        before = self.everything()
        with override_settings(**{**GATES, "WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER": True}), \
                self.assertRaises(WriterBoundaryUnavailable):
            framework_roles.configure_role(
                operation="grant-technical-super-admin", operator_school_id=ROOT, operator_password=PASSWORD,
                target_id=holder.pk, confirmation=framework_roles.confirmation_for("grant-technical-super-admin", holder.pk))
        self.assertEqual(self.everything(), before)
        self.assertEqual(self.p4("compensate", self.scope()), "LOCAL_COMPENSATED")
