"""WF-03.04 deferred; run only in consolidated authorized WF-03 testing."""
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from django.urls import URLPattern, URLResolver
from .account_restriction_api import (
    RestrictionSearchView, RestrictionDetailView, RestrictionChangeView,
)
from .account_restriction_urls import urlpatterns
from .mutations import AccountRestrictionStateConflict, change_account_restriction


class WF0304APIGates(SimpleTestCase):
    def test_exact_isolated_routes(self):
        self.assertEqual({str(x.pattern): x.callback.cls for x in urlpatterns
            if isinstance(x, URLPattern)}, {
            "accounts/": RestrictionSearchView,
            "accounts/<int:account_id>/overrides/": RestrictionDetailView,
            "accounts/<int:account_id>/overrides/<int:permission_id>/": RestrictionChangeView,
        })

    def test_no_normal_url_mount(self):
        from config.urls import urlpatterns as main
        self.assertFalse(any(isinstance(x, URLResolver) and
            str(x.pattern) == "api/v1/admin/account-restrictions/" for x in main))

    def test_mounted_in_both_isolated_configs(self):
        from config.review_local_urls import urlpatterns as local
        from config.review_sandbox_urls import urlpatterns as sandbox
        for entries in (local, sandbox):
            self.assertEqual(sum(isinstance(x, URLResolver) and
                str(x.pattern) == "api/v1/admin/account-restrictions/" for x in entries), 1)

    @override_settings(WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED=False)
    def test_default_off(self):
        self.assertFalse(RestrictionSearchView().review_gate_open())

    @override_settings(WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED=True)
    def test_executor_prevents_reads(self):
        from apps.accounts.registration_review_api import ReviewAPIUnavailable
        with patch("apps.access_control.account_restriction_api.executor_enabled", return_value=True):
            with self.assertRaises(ReviewAPIUnavailable):
                RestrictionDetailView().initial(None)

    def test_action_writer_available_for_disposable_database_tests(self):
        self.assertTrue(callable(change_account_restriction))
        self.assertTrue(issubclass(AccountRestrictionStateConflict, Exception))
