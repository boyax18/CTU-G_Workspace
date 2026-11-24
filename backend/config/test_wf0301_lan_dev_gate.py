"""WF-03.01 Option A fail-closed settings contract; no database required.

Run: python -m unittest config.test_wf0301_lan_dev_gate
"""
import unittest

from config.lan_role_context import LAN_ACK, validate_lan_dev_role_context


class LANDevRoleContextGateTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "CTUG_ROLE_CONTEXT_LAN_DEV_ACK": LAN_ACK,
            "CTUG_ROLE_CONTEXT_LAN_DEV_IP": "192.168.100.46",
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "WORKSPACE_DEPLOYMENT_PROFILE": "local",
            "WORKSPACE_HTTPS": "0",
            "WORKSPACE_TRUST_PROXY_SSL_HEADER": "0",
        }
        self.allowed = ["localhost", "127.0.0.1", "[::1]", "192.168.100.46"]
        self.db = {"ENGINE": "django.db.backends.mysql", "NAME": "ctug_workspace", "HOST": "127.0.0.1"}
        self.origins = ["http://192.168.100.46:5173"]

    def gate(self, **overrides):
        kwargs = dict(env=self.env, debug=True, allowed_hosts=self.allowed,
                      database=self.db, csrf_origins=self.origins,
                      session_secure=False, csrf_secure=False)
        kwargs.update(overrides)
        return validate_lan_dev_role_context(**kwargs)

    def test_explicit_single_private_lan_ip_succeeds(self):
        self.assertEqual(self.gate(), "192.168.100.46")

    def test_default_off(self):
        self.env.pop("CTUG_ROLE_CONTEXT_LAN_DEV_ACK")
        self.assertIsNone(self.gate())

    def test_invalid_ack_fail_closed(self):
        self.env["CTUG_ROLE_CONTEXT_LAN_DEV_ACK"] = "1"
        with self.assertRaisesRegex(ValueError, "Invalid"):
            self.gate()

    def test_existing_localhost_mode_cannot_be_combined(self):
        self.env["CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK"] = "LOCAL_ONLY_WF0301_D116"
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            self.gate()

    def test_debug_required(self):
        with self.assertRaisesRegex(ValueError, "DEBUG"):
            self.gate(debug=False)

    def test_reject_review_sandbox_and_deployment_profiles(self):
        for env_name, value in (
            ("DJANGO_SETTINGS_MODULE", "config.review_local_settings"),
            ("WORKSPACE_DEPLOYMENT_PROFILE", "production"),
            ("WORKSPACE_DEPLOYMENT_SETTINGS", "1"),
        ):
            with self.subTest(env_name=env_name):
                self.env[env_name] = value
                with self.assertRaisesRegex(ValueError, "settings"):
                    self.gate()
                self.env.pop(env_name)
                if env_name == "DJANGO_SETTINGS_MODULE": self.env[env_name] = "config.settings"
                if env_name == "WORKSPACE_DEPLOYMENT_PROFILE": self.env[env_name] = "local"

    def test_only_loopback_database_accepted(self):
        for change in (
            {"NAME": "ctug_production"},
            {"ENGINE": "django.db.backends.sqlite3"},
            {"HOST": "192.168.100.46"},
        ):
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError, "MySQL"):
                    self.gate(database={**self.db, **change})

    def test_reject_public_and_non_rfc1918_ips(self):
        for ip in ("8.8.8.8", "127.0.0.1", "169.254.1.1", "100.100.1.1", "0.0.0.0", "::1", "hostname"):
            with self.subTest(ip=ip):
                self.env["CTUG_ROLE_CONTEXT_LAN_DEV_IP"] = ip
                with self.assertRaises(ValueError):
                    self.gate()

    def test_reject_missing_and_unapproved_hosts(self):
        for hosts in (
            ["localhost", "127.0.0.1"],
            [*self.allowed, "192.168.1.239"],
            [*self.allowed, "*"],
            [*self.allowed, "192.168.100.46"],
        ):
            with self.subTest(hosts=hosts):
                with self.assertRaisesRegex(ValueError, "ALLOWED_HOSTS"):
                    self.gate(allowed_hosts=hosts)

    def test_reject_unapproved_csrf_origins(self):
        with self.assertRaisesRegex(ValueError, "CSRF"):
            self.gate(csrf_origins=["http://192.168.1.239:5173"])

    def test_reject_https_secure_cookies_and_proxy_header(self):
        for name in ("WORKSPACE_HTTPS", "WORKSPACE_TRUST_PROXY_SSL_HEADER"):
            with self.subTest(name=name):
                self.env[name] = "1"
                with self.assertRaisesRegex(ValueError, "Option A"):
                    self.gate()
                self.env[name] = "0"
        for option in ("session_secure", "csrf_secure"):
            with self.subTest(option=option):
                with self.assertRaisesRegex(ValueError, "Option A"):
                    self.gate(**{option: True})

    def test_reject_protected_write_activation(self):
        for name in (
            "WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER",
            "WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED",
            "WORKSPACE_ROLE_ASSIGNMENT_ENABLED",
            "WORKSPACE_WF0302_ROLE_PERMISSION_MUTATIONS_ENABLED",
            "WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED",
            "WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED",
        ):
            with self.subTest(name=name):
                self.env[name] = "1"
                with self.assertRaisesRegex(ValueError, "Protected"):
                    self.gate()
                self.env.pop(name)


class LANDevMultipleIPTests(LANDevRoleContextGateTests):
    """Repeat legacy tests in multi-IP mode, including all fail-closed guards."""

    def setUp(self):
        super().setUp()
        self.env.pop("CTUG_ROLE_CONTEXT_LAN_DEV_IP")
        self.env["CTUG_ROLE_CONTEXT_LAN_DEV_IPS"] = "192.168.100.46,192.168.1.239"
        self.allowed = [*self.allowed, "192.168.1.239"]
        self.origins = [*self.origins, "http://192.168.1.239:5173"]

    def test_approved_two_ips_succeed(self):
        self.assertEqual(self.gate(), "192.168.100.46")

    def test_legacy_and_multi_opt_ins_cannot_mix(self):
        self.env["CTUG_ROLE_CONTEXT_LAN_DEV_IP"] = "192.168.100.46"
        with self.assertRaisesRegex(ValueError, "only one"):
            self.gate()

    def test_missing_multi_ip_is_denied(self):
        self.env.pop("CTUG_ROLE_CONTEXT_LAN_DEV_IPS")
        with self.assertRaisesRegex(ValueError, "explicit"):
            self.gate()

    def test_duplicate_multi_ip_is_denied(self):
        self.env["CTUG_ROLE_CONTEXT_LAN_DEV_IPS"] = "192.168.100.46,192.168.100.46"
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.gate()

    def test_empty_multi_ip_is_denied(self):
        self.env["CTUG_ROLE_CONTEXT_LAN_DEV_IPS"] = "192.168.100.46,"
        with self.assertRaisesRegex(ValueError, "Empty"):
            self.gate()

    def test_too_many_multi_ips_is_denied(self):
        self.env["CTUG_ROLE_CONTEXT_LAN_DEV_IPS"] = ",".join(f"192.168.100.{i}" for i in range(1, 6))
        with self.assertRaisesRegex(ValueError, "four"):
            self.gate()

    def test_unapproved_public_or_wildcard_host_is_denied(self):
        for replacement in ("0.0.0.0", "100.104.163.5", "169.254.18.130", "8.8.8.8", "*.lan"):
            with self.subTest(replacement=replacement):
                self.env["CTUG_ROLE_CONTEXT_LAN_DEV_IPS"] = f"192.168.100.46,{replacement}"
                with self.assertRaises(ValueError):
                    self.gate()
        # WSL's 172.31.x addresses are RFC1918. Physical-adapter enforcement
        # is provided by the Windows launchers, not Python's IP parser.

    def test_missing_second_host_is_denied(self):
        with self.assertRaisesRegex(ValueError, "ALLOWED_HOSTS"):
            self.gate(allowed_hosts=self.allowed[:-1])

    def test_unapproved_extra_host_is_denied(self):
        with self.assertRaisesRegex(ValueError, "ALLOWED_HOSTS"):
            self.gate(allowed_hosts=[*self.allowed, "192.168.6.3"])

    def test_missing_second_csrf_origin_is_denied(self):
        with self.assertRaisesRegex(ValueError, "CSRF"):
            self.gate(csrf_origins=self.origins[:-1])

    def test_extra_csrf_origin_is_denied(self):
        with self.assertRaisesRegex(ValueError, "CSRF"):
            self.gate(csrf_origins=[*self.origins, "http://192.168.6.3:5173"])

    def test_three_addresses_in_any_private_range(self):
        self.env["CTUG_ROLE_CONTEXT_LAN_DEV_IPS"] = "10.1.2.3,172.16.5.10,192.168.0.239"
        hosts = ["localhost", "127.0.0.1", "[::1]", "10.1.2.3", "172.16.5.10", "192.168.0.239"]
        origins = ["http://10.1.2.3:5173", "http://172.16.5.10:5173", "http://192.168.0.239:5173"]
        self.assertEqual(self.gate(allowed_hosts=hosts, csrf_origins=origins), "10.1.2.3")


if __name__ == "__main__":
    unittest.main()
