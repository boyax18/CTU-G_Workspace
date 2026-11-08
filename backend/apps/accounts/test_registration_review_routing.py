
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

  def test_existing_authentication_route_remains_available(self):
    match = resolve(
      "/api/v1/auth/session/",
      urlconf="config.urls",
    )
    self.assertEqual(match.url_name, "workspace-session")
