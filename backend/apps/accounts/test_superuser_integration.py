"""AR-4A: Django framework-admin checks on an isolated test database.

Place at backend/apps/accounts/test_superuser_integration.py.
Run only with config.test_settings, never with production/development settings.
"""

from django.test import TestCase
from django.urls import reverse

from apps.access_control.models import AccountRole
from apps.accounts.models import Account


class FrameworkSuperuserIntegrationTests(TestCase):
    password = "Z8!qV4#mN7@rL2$w"

    def create_framework_admin(self):
        return Account.objects.create_superuser(
            school_id="FRAMEWORK-TEST-001",
            email="framework-test@example.invalid",
            password=self.password,
        )

    def test_superuser_persists_without_workspace_roles(self):
        account = self.create_framework_admin()
        saved = Account.objects.get(pk=account.pk)

        self.assertTrue(saved.is_active)
        self.assertTrue(saved.is_staff)
        self.assertTrue(saved.is_superuser)
        self.assertEqual(saved.request_status, "Approved")
        self.assertIsNone(saved.requested_role_id)
        self.assertTrue(saved.check_password(self.password))
        self.assertFalse(AccountRole.objects.filter(account=saved).exists())

        # Django framework privilege must not become application privilege.
        self.assertFalse(
            saved.has_perm("access_control.role_permissions.manage")
        )
        self.assertFalse(saved.has_module_perms("access_control"))

    def test_framework_admin_can_log_in_to_django_admin(self):
        account = self.create_framework_admin()
        response = self.client.post(
            reverse("admin:login"),
            data={
                "username": account.school_id,
                "password": self.password,
                "next": reverse("admin:index"),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.pk, account.pk)
        self.assertTrue(response.wsgi_request.user.is_staff)

    def test_ordinary_school_account_cannot_access_django_admin(self):
        account = Account.objects.create_user(
            school_id="STUDENT-TEST-001",
            password=self.password,
        )
        account.is_active = True
        account.request_status = "Approved"
        account.save(update_fields=["is_active", "request_status"])

        # Valid Django authentication alone must not open /admin/.
        self.assertTrue(
            self.client.login(
                school_id=account.school_id,
                password=self.password,
            )
        )
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response["Location"])

    def test_inactive_framework_admin_cannot_log_in(self):
        account = self.create_framework_admin()
        account.is_active = False
        account.save(update_fields=["is_active"])

        self.assertFalse(
            self.client.login(
                school_id=account.school_id,
                password=self.password,
            )
        )
