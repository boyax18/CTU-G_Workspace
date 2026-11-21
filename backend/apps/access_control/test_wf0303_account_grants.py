"""Deferred WF-03.03 guard checks. Do not run until WF-03 test phase."""
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from django.urls import URLPattern, URLResolver

from .account_grant_api import AccountGrantChangeView, AccountGrantDetailView, AccountGrantSearchView
from .account_grant_urls import urlpatterns as account_grant_urls
from .mutations import AccountGrantStateConflict, grant_account_permission_for_role


class WF0303RouteContracts(SimpleTestCase):
    def test_exact_grant_routes(self):
        self.assertEqual({str(item.pattern): item.callback.cls for item in account_grant_urls
            if isinstance(item, URLPattern)}, {
            'accounts/': AccountGrantSearchView,
            'accounts/<int:account_id>/grants/': AccountGrantDetailView,
            'accounts/<int:account_id>/grants/<int:permission_id>/': AccountGrantChangeView,
        })

    def test_never_mounted_in_normal_configuration(self):
        from config.urls import urlpatterns
        self.assertFalse(any(isinstance(item, URLResolver) and
            str(item.pattern) == 'api/v1/admin/account-grants/' for item in urlpatterns))

    def test_both_isolated_routes_mounted(self):
        from config.review_local_urls import urlpatterns as local
        from config.review_sandbox_urls import urlpatterns as sandbox
        for patterns in (local, sandbox):
            self.assertEqual(sum(isinstance(item, URLResolver) and
                str(item.pattern) == 'api/v1/admin/account-grants/' for item in patterns), 1)

    @override_settings(WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED=False)
    def test_gate_off_by_default(self):
        self.assertFalse(AccountGrantSearchView().review_gate_open())

    @override_settings(WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED=True)
    def test_protected_executor_refuses_reads(self):
        with patch('apps.access_control.account_grant_api.executor_enabled', return_value=True):
            from apps.accounts.registration_review_api import ReviewAPIUnavailable
            with self.assertRaises(ReviewAPIUnavailable):
                AccountGrantDetailView().initial(None)

    def test_mutation_reference_present_for_deferred_integration(self):
        self.assertTrue(callable(grant_account_permission_for_role))
        self.assertTrue(issubclass(AccountGrantStateConflict, Exception))
