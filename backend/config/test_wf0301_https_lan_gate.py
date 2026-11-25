"""Pure stdlib tests; independent of Django DB and network."""
import unittest

from config.https_lan_role_context import HTTPS_ACK, validate_https_lan_dev_role_context


class HTTPSLANRoleContextTests(unittest.TestCase):
    def setUp(self):
        self.ips = ("192.168.100.46", "192.168.1.239")
        self.env = {
            "CTUG_ROLE_CONTEXT_HTTPS_LAN_DEV_ACK": HTTPS_ACK,
            "CTUG_ROLE_CONTEXT_HTTPS_LAN_IPS": ",".join(self.ips),
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "WORKSPACE_DEPLOYMENT_PROFILE": "local",
            "WORKSPACE_DEPLOYMENT_SETTINGS": "0",
            "WORKSPACE_HTTPS": "1",
            "WORKSPACE_TRUST_PROXY_SSL_HEADER": "1",
            "WORKSPACE_PUBLIC_BASE_URL": "https://192.168.100.46:5173",
        }
        self.kwargs = {
            "debug": True,
            "allowed_hosts": ["localhost", "127.0.0.1", "[::1]", *self.ips],
            "database": {"ENGINE": "django.db.backends.mysql", "NAME": "ctug_workspace", "HOST": "127.0.0.1"},
            "csrf_origins": [f"https://{ip}:5173" for ip in self.ips],
            "session_secure": True,
            "csrf_secure": True,
            "ssl_redirect": False,
            "proxy_ssl_header": ("HTTP_X_FORWARDED_PROTO", "https"),
            "hsts_seconds": 0,
        }

    def invoke(self, **overrides):
        return validate_https_lan_dev_role_context(self.env, **(self.kwargs | overrides))

    def test_default_off(self):
        del self.env["CTUG_ROLE_CONTEXT_HTTPS_LAN_DEV_ACK"]
        self.assertIsNone(self.invoke())

    def test_valid_two_ip_configuration(self):
        self.assertEqual(self.invoke(), self.ips)

    def test_valid_one_ip_configuration(self):
        self.env["CTUG_ROLE_CONTEXT_HTTPS_LAN_IPS"] = self.ips[0]
        self.assertEqual(self.invoke(allowed_hosts=["localhost", self.ips[0]],
                                     csrf_origins=[f"https://{self.ips[0]}:5173"]), (self.ips[0],))

    def test_reject_invalid_ack(self):
        self.env["CTUG_ROLE_CONTEXT_HTTPS_LAN_DEV_ACK"] = "1"
        with self.assertRaisesRegex(ValueError, "acknowledgment"):
            self.invoke()

    def test_http_and_local_ack_exclusive(self):
        for key, value in (
            ("CTUG_ROLE_CONTEXT_LAN_DEV_ACK", "LAN_HTTP_SYNTHETIC_ONLY_WF0301_A"),
            ("CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK", "LOCAL_ONLY_WF0301_D116"),
        ):
            with self.subTest(key=key):
                self.env[key] = value
                with self.assertRaisesRegex(ValueError, "mutually exclusive"):
                    self.invoke()
                del self.env[key]

    def test_dev_and_debug_guards(self):
        with self.assertRaisesRegex(ValueError, "DEBUG-only"):
            self.invoke(debug=False)
        for key, value in (
            ("DJANGO_SETTINGS_MODULE", "config.test_settings"),
            ("WORKSPACE_DEPLOYMENT_PROFILE", "production"),
            ("WORKSPACE_DEPLOYMENT_SETTINGS", "1"),
        ):
            with self.subTest(key=key):
                old = self.env[key]
                self.env[key] = value
                with self.assertRaisesRegex(ValueError, "DEBUG-only"):
                    self.invoke()
                self.env[key] = old

    def test_https_proxy_cookie_and_hsts_guards(self):
        for key in ("WORKSPACE_HTTPS", "WORKSPACE_TRUST_PROXY_SSL_HEADER"):
            with self.subTest(key=key):
                self.env[key] = "0"
                with self.assertRaisesRegex(ValueError, "Secure cookies"):
                    self.invoke()
                self.env[key] = "1"
        for key, value in (
            ("session_secure", False),
            ("csrf_secure", False),
            ("ssl_redirect", True),
            ("proxy_ssl_header", None),
            ("hsts_seconds", 30),
        ):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "Secure cookies"):
                    self.invoke(**{key: value})

    def test_database_guard(self):
        for delta in ({"HOST": "192.168.100.46"}, {"NAME": "other"}, {"ENGINE": "django.db.backends.sqlite3"}):
            with self.subTest(delta=delta):
                with self.assertRaisesRegex(ValueError, "local ctug_workspace"):
                    self.invoke(database=self.kwargs["database"] | delta)

    def test_host_allowlist(self):
        for hosts in (
            ["localhost", "127.0.0.1", self.ips[0]],
            [*self.kwargs["allowed_hosts"], "*"],
            [*self.kwargs["allowed_hosts"], "192.168.33.33"],
            [*self.kwargs["allowed_hosts"], self.ips[0]],
        ):
            with self.subTest(hosts=hosts):
                with self.assertRaisesRegex(ValueError, "ALLOWED_HOSTS"):
                    self.invoke(allowed_hosts=hosts)

    def test_csrf_exact_origins(self):
        for origins in (
            [f"https://{self.ips[0]}:5173"],
            [*self.kwargs["csrf_origins"], "http://localhost:5173"],
            [*self.kwargs["csrf_origins"], "https://evil.example:5173"],
            [*self.kwargs["csrf_origins"], self.kwargs["csrf_origins"][0]],
        ):
            with self.subTest(origins=origins):
                with self.assertRaisesRegex(ValueError, "CSRF origins"):
                    self.invoke(csrf_origins=origins)

    def test_public_base_url(self):
        for url in ("http://192.168.100.46:5173", "https://192.168.1.239:5173",
                    "https://192.168.100.46:8000", "https://192.168.100.46:5173/extra"):
            with self.subTest(url=url):
                self.env["WORKSPACE_PUBLIC_BASE_URL"] = url
                with self.assertRaisesRegex(ValueError, "PUBLIC_BASE_URL"):
                    self.invoke()

    def test_invalid_noncanonical_public_duplicate_or_unassigned_shapes(self):
        # Interface assignment is separately checked by the Windows launchers.
        for value in ("", "8.8.8.8", "127.0.0.1", "100.104.163.5", "169.254.18.130",
                      "192.168.100.46,192.168.100.46", "192.168.100.046", "192.168.100.46,",
                      "192.168.100.46,192.168.1.239,10.0.0.2,10.0.0.3,10.0.0.4"):
            with self.subTest(value=value):
                self.env["CTUG_ROLE_CONTEXT_HTTPS_LAN_IPS"] = value
                with self.assertRaises(ValueError):
                    self.invoke()

    def test_protected_mutations_remain_off(self):
        for key in (
            "WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER",
            "WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED",
            "WORKSPACE_ROLE_ASSIGNMENT_ENABLED",
            "WORKSPACE_WF0302_ROLE_PERMISSION_MUTATIONS_ENABLED",
            "WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED",
            "WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED",
        ):
            with self.subTest(key=key):
                self.env[key] = "1"
                with self.assertRaisesRegex(ValueError, "Protected executor"):
                    self.invoke()
                del self.env[key]


if __name__ == "__main__":
    unittest.main()
