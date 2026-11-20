
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import Resolver404, resolve


class RegistrationReviewRoutingSafetyTests(TestCase):

  def test_review_feature_flags_default_off(self):
    self.assertFalse(
      getattr(settings, "WORKSPACE_REGISTRATION_REVIEW_API_ENABLED", False)
    )
    self.assertFalse(
      getattr(settings, "WORKSPACE_REGISTRATION_APPROVAL_ENABLED", False)
    )

  def test_pending_list_is_not_live(self):
    with self.assertRaises(Resolver404):
      resolve("/api/v1/registration-requests/", urlconf="config.urls")

  def test_approve_route_is_not_live(self):
    with self.assertRaises(Resolver404):
      resolve(
        "/api/v1/registration-requests/1/approve/",
        urlconf="config.urls",
      )

  def test_reject_route_is_not_live(self):
    with self.assertRaises(Resolver404):
      resolve(
        "/api/v1/registration-requests/1/reject/",
        urlconf="config.urls",
      )

  @override_settings(
    WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True,
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
  )
  def test_feature_flags_alone_do_not_publish_routes(self):
    with self.assertRaises(Resolver404):
      resolve("/api/v1/registration-requests/", urlconf="config.urls")

  def test_isolated_candidate_routes_resolve(self):
    routes = {
      "/": "registration-review-pending",
      "/1/approve/": "registration-review-approve",
      "/1/reject/": "registration-review-reject",
    }

    for route, expected_name in routes.items():
      with self.subTest(route=route):
        match = resolve(
          route,
          urlconf="apps.accounts.registration_review_urls",
        )
        self.assertEqual(match.url_name, expected_name)

  def test_wf0201_only_the_read_only_list_is_mounted(self):
    # D-31: the pending list is the only review route in config.urls.
    match = resolve("/api/v1/admin/registration-requests/", urlconf="config.urls")
    self.assertEqual(match.url_name, "registration-review-pending")
    self.assertEqual(match.func.view_class.http_method_names, ["get", "head", "options"])
    for route in (
      "/api/v1/admin/registration-requests/1/approve/",
      "/api/v1/admin/registration-requests/1/reject/",
      "/api/v1/admin/registration-requests/bulk/",
    ):
      with self.subTest(route=route), self.assertRaises(Resolver404):
        resolve(route, urlconf="config.urls")

  def test_wf0201_list_gate_defaults_off(self):
    # Checked in source so a developer's backend/.env cannot change the result.
    from pathlib import Path
    source = (Path(settings.BASE_DIR) / "config" / "settings.py").read_text(encoding="utf-8")
    self.assertIn(
      'WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED = os.environ.get(\n'
      '    "WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED", "0"\n) == "1"',
      source,
    )
    self.assertIsInstance(settings.WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED, bool)

  def test_existing_authentication_route_remains_available(self):
    match = resolve(
      "/api/v1/auth/session/",
      urlconf="config.urls",
    )
    self.assertEqual(match.url_name, "workspace-session")
