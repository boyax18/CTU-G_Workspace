"""Deferred WF-03.06 regressions. Do not run until consolidated WF-03 testing."""
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import URLPattern, URLResolver
from rest_framework import exceptions

from .access_audit_api import (
    AuditHistoryListView, AuditHistoryDetailView, _filters, _safe_snapshot,
)
from .access_audit_urls import urlpatterns


class _Params(dict):
    def getlist(self, key):
        return [self[key]] if key in self else []


class WF0306AuditHistorySafety(SimpleTestCase):
    def test_isolated_routes_only(self):
        self.assertEqual({str(p.pattern):p.callback.cls for p in urlpatterns if isinstance(p,URLPattern)}, {
            'events/':AuditHistoryListView,
            'events/<int:audit_id>/':AuditHistoryDetailView,
        })
        from config.urls import urlpatterns as normal
        self.assertFalse(any(isinstance(p,URLResolver) and str(p.pattern)=='api/v1/admin/access-audit/' for p in normal))
        from config.review_local_urls import urlpatterns as local
        from config.review_sandbox_urls import urlpatterns as sandbox
        for routes in (local,sandbox):
            self.assertEqual(sum(isinstance(p,URLResolver) and str(p.pattern)=='api/v1/admin/access-audit/' for p in routes),1)

    @override_settings(WORKSPACE_WF0306_AUDIT_HISTORY_ENABLED=False)
    def test_feature_default_off(self):
        self.assertFalse(AuditHistoryListView().review_gate_open())

    @override_settings(WORKSPACE_WF0306_AUDIT_HISTORY_ENABLED=True,
                       WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True)
    def test_protected_executor_rejected(self):
        from apps.accounts.registration_review_api import ReviewAPIUnavailable
        with patch('apps.access_control.access_audit_api.executor_enabled',return_value=True):
            with self.assertRaises(ReviewAPIUnavailable):
                AuditHistoryListView().initial(None)

    def test_filters_reject_unknown_repeated_and_malformed_fields(self):
        with self.assertRaises(exceptions.ValidationError): _filters(_Params({'bogus':'value'}))
        with self.assertRaises(exceptions.ValidationError): _filters(_Params({'page':'1001'}))
        with self.assertRaises(exceptions.ValidationError): _filters(_Params({'from':'2026-02-30'}))
        with self.assertRaises(exceptions.ValidationError): _filters(_Params({'action':'space in action'}))
        self.assertEqual(_filters(_Params({'page':'2','actor':'DEV-100'}))['page'],2)

    def test_untrusted_legacy_snapshots_are_redacted(self):
        self.assertEqual(_safe_snapshot({'password':'a-secret'},'account.role.assign'),(None,True))
        self.assertEqual(_safe_snapshot({'is_active':False},'account.role.assign'),({'is_active':False},False))
        self.assertEqual(_safe_snapshot(None,'account.role.assign'),(None,False))
