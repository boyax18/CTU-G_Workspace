"""Django request-level contract for Option A proxy-only backend access.

Requires Django environment, but does not create or mutate DB records.
"""
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from apps.accounts.lan_dev_proxy_guard import LANDevLoopbackProxyGuard


class LANDevProxyGuardTests(SimpleTestCase):
    def setUp(self):
        self.guard = LANDevLoopbackProxyGuard(lambda request: HttpResponse(status=204))
        self.factory = RequestFactory()

    def test_vite_loopback_proxy_allowed(self):
        for client in ("127.0.0.1", "::1"):
            with self.subTest(client=client):
                request = self.factory.get("/api/v1/auth/session/", REMOTE_ADDR=client)
                self.assertEqual(self.guard(request).status_code, 204)

    def test_direct_lan_backend_denied(self):
        request = self.factory.post("/api/v1/auth/role-context/", REMOTE_ADDR="192.168.100.25")
        self.assertEqual(self.guard(request).status_code, 403)

    def test_forwarded_for_cannot_bypass(self):
        request = self.factory.post(
            "/api/v1/auth/role-context/", REMOTE_ADDR="192.168.100.25",
            HTTP_X_FORWARDED_FOR="127.0.0.1", HTTP_X_FORWARDED_PROTO="https",
        )
        self.assertEqual(self.guard(request).status_code, 403)

    def test_non_loopback_denied_for_admin_too(self):
        request = self.factory.get("/admin/", REMOTE_ADDR="192.168.100.25")
        self.assertEqual(self.guard(request).status_code, 403)
