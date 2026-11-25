"""Request-level HTTPS transport guard tests; no database mutations."""
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from apps.accounts.https_lan_proxy_guard import HTTPSLANProxyGuard


class HTTPSLANProxyGuardTests(SimpleTestCase):
    def setUp(self):
        self.guard = HTTPSLANProxyGuard(lambda request: HttpResponse(status=204))
        self.factory = RequestFactory()

    def test_loopback_proxy_marked_https_accepted(self):
        for addr in ("127.0.0.1", "::1"):
            with self.subTest(addr=addr):
                request = self.factory.get('/api/v1/auth/session/', REMOTE_ADDR=addr,
                                           HTTP_X_FORWARDED_PROTO='https')
                self.assertEqual(self.guard(request).status_code, 204)

    def test_direct_remote_connection_rejected(self):
        request = self.factory.post('/api/v1/auth/role-context/',
                                    REMOTE_ADDR='192.168.100.27', HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(self.guard(request).status_code, 403)

    def test_insecure_loopback_request_rejected(self):
        request = self.factory.post('/api/v1/auth/role-context/', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(self.guard(request).status_code, 403)

    def test_spoofed_client_headers_do_not_authorize_remote(self):
        request = self.factory.post('/api/v1/auth/role-context/',
                                    REMOTE_ADDR='192.168.100.27', HTTP_X_FORWARDED_FOR='127.0.0.1',
                                    HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(self.guard(request).status_code, 403)

    def test_unexpected_proxy_header_rejected(self):
        for value in ('http', 'https,http', 'HTTPS', 'http,https', ''):
            with self.subTest(value=value):
                request = self.factory.get('/api/v1/auth/session/', REMOTE_ADDR='127.0.0.1',
                                           HTTP_X_FORWARDED_PROTO=value)
                self.assertEqual(self.guard(request).status_code, 403)
