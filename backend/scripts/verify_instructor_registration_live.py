"""WF-01.02 real browser/API/MySQL acceptance; disposable test database only.

Run from backend: .venv/Scripts/python.exe scripts/verify_instructor_registration_live.py
Uses the existing guarded runner, installed Node/Edge and frontend dependencies.
No development routes, records, review gates or permissions are modified.
"""

import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.test_settings"

import django

django.setup()

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.http import JsonResponse
from django.test import Client, LiveServerTestCase, override_settings
from django.urls import include, path

from apps.access_control.models import (
    AccessAuditLog, AccountRole, Permission, Role, RolePermission, Service,
)
from apps.accounts.models import Account, StudentRegistrationStage, UserProfile
from apps.accounts.outbox_models import RegistrationNotificationOutbox
from apps.accounts.registration_review_api import PendingRegistrationRequestsView
from config.test_runner import IsolatedMySQLRunner


if not re.fullmatch(r"test_ctug_registration_[0-9a-f]{16}", settings.REGISTRATION_TEST_DATABASE):
    raise ImproperlyConfigured("Live registration acceptance requires guarded disposable settings.")

RUN_ID = secrets.token_hex(16)


def isolated_probe(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
            raise ImproperlyConfigured("Refusing live acceptance against an unexpected database.")
    return JsonResponse({"database": settings.REGISTRATION_TEST_DATABASE, "run_id": RUN_ID,
                         "permanent_records": Account.objects.count() + UserProfile.objects.count(),
                         "stages": StudentRegistrationStage.objects.count(), "mail_messages": len(mail.outbox)})


# These routes exist only in this script's test URLconf, never config.urls.
# Only the review read view is mounted; no approval/rejection route is provided.
urlpatterns = [
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("__wf0102__/probe/", isolated_probe),
    path("__wf0102__/review/", PendingRegistrationRequestsView.as_view()),
]


@override_settings(
    ROOT_URLCONF=__name__,
    WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True,
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
    WORKSPACE_REGISTRATION_SUPPORT_CONTACT="",
    WORKSPACE_PASSWORD_RESET_ENABLED=False,
)
class InstructorRegistrationLiveAcceptance(LiveServerTestCase):
    host = "127.0.0.1"

    def test_real_form_duplicates_and_authorized_pending_handoff(self):
        cache.clear()
        Role.objects.create(role_name="Student")
        instructor = Role.objects.create(role_name="Instructor")
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            self.assertEqual(cursor.fetchone()[0], settings.REGISTRATION_TEST_DATABASE)

        # Frontend/browser subprocesses receive no database, SMTP or app secrets.
        environment = {
            key: value for key, value in os.environ.items()
            if key.upper() in {
                "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE",
                "LOCALAPPDATA", "APPDATA", "PATHEXT", "COMSPEC",
                "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432", "HOMEDRIVE", "HOMEPATH",
                "PLAYWRIGHT_EXECUTABLE_PATH", "CTUG_TEST_BROWSER_CHANNEL",
            }
        }
        environment.update({
            "CTUG_WF0102_TEST_BACKEND": self.live_server_url,
            "CTUG_WF0102_TEST_DATABASE": settings.REGISTRATION_TEST_DATABASE,
            "CTUG_WF0102_TEST_RUN": RUN_ID,
            "CTUG_WF0102_TEST_CODE": "314159",  # Synthetic RNG fixture, never real mail.
        })
        node = shutil.which("node")
        if node is None:
            raise ImproperlyConfigured("Installed Node is required for real browser acceptance.")
        frontend = Path(__file__).resolve().parents[2] / "frontend"
        with patch("apps.accounts.registration_staging.secrets.randbelow", return_value=314159):
            result = subprocess.run(
                [node, "tests/browser/instructor-registration-live.mjs"],
                cwd=frontend, env=environment, capture_output=True, text=True,
                timeout=100, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        browser = json.loads(result.stdout.strip())
        self.assertEqual(browser["registration_posts"], 4)
        self.assertEqual(browser["successful_verifications"], 1)
        self.assertEqual(browser["conflicts"], 2)
        self.assertEqual(browser["same_browser_resumes"], 1)
        self.assertEqual(browser["pre_otp_permanent_records"], 0)
        self.assertTrue(browser["confirmation_focused"])

        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)
        applicant = Account.objects.get()
        self.assertEqual(applicant.school_id, "0054321")
        self.assertEqual(applicant.email, "instructor.integration@example.edu")
        self.assertEqual(applicant.requested_role_id, instructor.pk)
        self.assertEqual(applicant.request_status, "Pending")
        self.assertFalse(applicant.is_active)
        self.assertFalse(applicant.is_staff)
        self.assertFalse(applicant.is_superuser)
        self.assertTrue(applicant.check_password("Copper!River7392"))
        self.assertIsNone(applicant.reviewed_at)
        self.assertIsNone(applicant.reviewed_by_id)
        self.assertIsNotNone(applicant.email_verified_at)
        self.assertEqual(applicant.email_verified_address, applicant.email)
        profile = applicant.profile
        self.assertEqual((profile.first_name, profile.middle_name, profile.last_name, profile.suffix),
                         ("Test", "Q.", "Instructor", "Jr."))
        self.assertFalse(AccountRole.objects.exists())
        self.assertFalse(StudentRegistrationStage.objects.exists())
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())
        self.assertEqual(len(mail.outbox), 1)
        before = Account.objects.values().get(pk=applicant.pk)

        # Exercise the real read view with disposable permissions/sessions only.
        # Merely naming a reviewer Admin must not grant visibility.
        service = Service.objects.create(service_code="accounts", service_name="Accounts")
        Service.objects.create(service_code="access_control", service_name="Access Control")
        admin = Role.objects.create(role_name="Admin")
        reviewer = Account.objects.create_user("TEST-REVIEWER", password="Research!Brick7294")
        reviewer.request_status, reviewer.is_active = "Approved", True
        reviewer.save(update_fields=["request_status", "is_active"])
        AccountRole.objects.create(account=reviewer, role=admin)
        review = Client(enforce_csrf_checks=True)
        self.assertEqual(review.get("/__wf0102__/review/").status_code, 401)
        review.force_login(applicant)
        self.assertEqual(review.get("/__wf0102__/review/").status_code, 401)
        review.force_login(reviewer)
        self.assertEqual(review.get("/__wf0102__/review/").status_code, 403)
        permission = Permission.objects.create(
            service=service, permission_code="accounts.registration_requests.read",
            permission_name="Read registration requests", module_name="registration_requests",
            action_name="read",
        )
        RolePermission.objects.create(role=admin, permission=permission)
        response = review.get("/__wf0102__/review/")
        self.assertEqual(response.status_code, 200, response.content)
        rows = response.json()["results"]
        self.assertEqual([row["account_id"] for row in rows], [applicant.pk])
        self.assertEqual(rows[0]["requested_role"], "Instructor")
        self.assertEqual(set(rows[0]), {"account_id", "school_id", "requested_role", "created_at"})
        self.assertIn("no-store", response["Cache-Control"])
        with override_settings(WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=False):
            self.assertEqual(review.get("/__wf0102__/review/").status_code, 503)
        self.assertEqual(Account.objects.values().get(pk=applicant.pk), before)
        self.assertFalse(AccountRole.objects.filter(account=applicant).exists())
        print("WF-01.02 real browser -> owned staging/OTP -> atomic email proof -> authorized Pending list passed; no applicant activation or assigned role.")


if __name__ == "__main__":
    failures = IsolatedMySQLRunner(interactive=False, verbosity=1).run_tests([
        "__main__.InstructorRegistrationLiveAcceptance",
    ])
    sys.exit(bool(failures))
