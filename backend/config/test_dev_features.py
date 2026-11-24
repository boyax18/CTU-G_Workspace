"""Development launcher registry contract; no database required.

Run: python -m unittest config.test_dev_features
"""
import re
import unittest
from pathlib import Path

from config import dev_features as registry
from config.lan_role_context import LAN_ACK, validate_lan_dev_role_context

REPO = Path(__file__).resolve().parents[2]
KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="  # 32 bytes, test-only


class ModeEnvironmentTests(unittest.TestCase):
    def test_lan_mode_uses_normal_settings_and_option_a_for_detected_ip(self):
        result = registry.mode_environment("lan", lan_ip="192.168.7.20", env={"CTUG_ROLE_CONTEXT_LAN_DEV_IPS": "10.0.0.9"})
        backend = result["backend_env"]
        self.assertEqual(backend["DJANGO_SETTINGS_MODULE"], "config.settings")
        self.assertEqual(backend["CTUG_ROLE_CONTEXT_LAN_DEV_ACK"], LAN_ACK)
        self.assertEqual(backend["CTUG_ROLE_CONTEXT_LAN_DEV_IPS"], "192.168.7.20")
        self.assertEqual(backend["CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK"], "")
        self.assertEqual(result["url"], "http://192.168.7.20:5173")
        self.assertNotIn("DB_NAME", backend)  # the database always comes from backend/.env
        # The produced environment satisfies the unchanged Option A gate for ctug_workspace.
        hosts = backend["WORKSPACE_ALLOWED_HOSTS"].split(",")
        origins = backend["WORKSPACE_CSRF_TRUSTED_ORIGINS"].split(",")
        self.assertEqual(validate_lan_dev_role_context(
            {**backend, "WORKSPACE_DEPLOYMENT_PROFILE": "local"}, debug=True, allowed_hosts=hosts,
            database={"ENGINE": "django.db.backends.mysql", "NAME": "ctug_workspace", "HOST": "127.0.0.1"},
            csrf_origins=origins, session_secure=False, csrf_secure=False), "192.168.7.20")

    def test_lan_mode_never_offers_decisions(self):
        result = registry.mode_environment("lan", lan_ip="192.168.7.20", env={"WORKSPACE_OUTBOX_KEK_V1_B64": KEY})
        flags = result["frontend_env"]
        self.assertEqual(flags["VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED"], "1")
        self.assertEqual(flags["VITE_WORKSPACE_ACCOUNT_DIRECTORY_ENABLED"], "1")
        for name in ("VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED", "VITE_WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED",
                     "VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED", "VITE_WORKSPACE_ROLE_ASSIGNMENT_ENABLED"):
            self.assertEqual(flags[name], "0", name)
        self.assertNotIn("WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED", result["backend_env"])

    def test_local_mode_uses_existing_loopback_decision_profile(self):
        result = registry.mode_environment("local", env={"WORKSPACE_OUTBOX_KEK_V1_B64": KEY})
        backend = result["backend_env"]
        self.assertEqual(backend["DJANGO_SETTINGS_MODULE"], "config.review_decision_local_settings")
        self.assertEqual(backend["CTUG_REVIEW_LOCAL_ACK"], "LOCAL_REVIEW_ONLY")
        self.assertEqual(backend["CTUG_ROLE_CONTEXT_LAN_DEV_ACK"], "")
        self.assertEqual(backend["WORKSPACE_ALLOWED_HOSTS"], "localhost,127.0.0.1,[::1]")
        self.assertEqual(backend["WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED"], "1")
        self.assertEqual(result["frontend_env"]["VITE_WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED"], "1")
        self.assertIn("127.0.0.1", result["frontend_args"])

    def test_missing_outbox_key_blocks_decisions_and_dependents(self):
        result = registry.mode_environment("local", env={})
        status = {f["key"]: f["status"] for f in result["features"]}
        self.assertEqual(status["wf02.applicant_decisions"], "blocked")
        self.assertEqual(status["wf02.bulk_decisions"], "blocked")
        self.assertEqual(result["frontend_env"]["VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED"], "0")
        self.assertNotIn("WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED", result["backend_env"])

    def test_invalid_mode_or_ip_refused(self):
        with self.assertRaises(ValueError):
            registry.mode_environment("production")
        for raw in ("8.8.8.8", "169.254.1.1", "0.0.0.0", "", "host"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                registry.mode_environment("lan", lan_ip=raw, env={})


class RegistryTests(unittest.TestCase):
    def test_flags_exist_in_frontend_and_requirements_known(self):
        source = "\n".join(p.read_text(encoding="utf-8") for p in (REPO / "frontend" / "src").rglob("*.ts"))
        keys = [f.key for f in registry.FEATURES]
        self.assertEqual(len(keys), len(set(keys)))
        for item in registry.FEATURES:
            self.assertTrue(set(item.requires) <= set(keys[:keys.index(item.key)]), item.key)
            self.assertTrue(item.modes <= registry.MODES)
            for flag in item.frontend_flags:
                self.assertIn(flag, source)

    def test_launcher_is_feature_agnostic_and_ascii(self):
        text = (REPO / "Start-CTUG-LAN.ps1").read_text(encoding="utf-8")
        self.assertTrue(text.isascii(), "Windows PowerShell 5.1 reads BOM-less scripts as ANSI")
        for pattern in (r"VITE_WORKSPACE_", r"WORKSPACE_\w+_ENABLED", r"\bWF-?\d", r"registration-requests",
                        r"synthetic", r"ctug_lan", r"migrate"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, text, re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()
