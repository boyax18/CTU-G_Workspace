"""Synthetic LAN profile contract: registry, environment and launcher independence.

No database required. Run: python -m unittest config.test_dev_lan_profile
"""
import importlib
import re
import unittest
from pathlib import Path

from config import dev_features as registry
from config.dev_lan_environment import (
    DevLanEnvironmentError, LAN_IP_VARIABLE, neutralized_flags, prepare_environment,
)
from config.lan_role_context import LAN_ACK, SYNTHETIC_LAN_DATABASE

REPO = Path(__file__).resolve().parents[2]
SECRETS = {"DJANGO_SECRET_KEY": "synthetic-test-key", "WORKSPACE_OUTBOX_KEK_V1_B64": "c3ludGhldGlj"}
LAN = registry.LAN_SYNTHETIC


class RegistryIntegrityTests(unittest.TestCase):
    def test_keys_unique_and_references_known(self):
        keys = [f.key for f in registry.FEATURES]
        self.assertEqual(len(keys), len(set(keys)))
        for item in registry.FEATURES:
            with self.subTest(item=item.key):
                self.assertTrue(set(item.requires) <= set(keys))
                self.assertTrue(set(item.prerequisites) <= registry.PREREQUISITES)
                self.assertTrue(item.profiles <= registry.PROFILES)
                self.assertTrue(all(name.startswith("VITE_WORKSPACE_") for name in item.frontend_flags))
                self.assertTrue(all(name.startswith("WORKSPACE_") for name, _ in item.settings))
                for _prefix, module in item.routes:
                    importlib.util.find_spec(module)  # must be an importable URLconf module

    def test_every_frontend_flag_exists_in_frontend_source(self):
        source = "\n".join(p.read_text(encoding="utf-8") for p in (REPO / "frontend" / "src").rglob("*.ts"))
        for item in registry.FEATURES:
            for name in item.frontend_flags:
                with self.subTest(flag=name):
                    self.assertIn(name, source)

    def test_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):
            registry.approved_keys("production")


class ProfileGatingTests(unittest.TestCase):
    def test_wf02_development_features_approved(self):
        self.assertEqual(registry.approved_keys(LAN), {
            "wf02.applicant_reviews", "wf02.applicant_decisions", "wf02.bulk_decisions", "wf02.account_directory"})
        values = registry.profile_settings(LAN)
        for name in ("WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED", "WORKSPACE_REGISTRATION_REVIEW_API_ENABLED",
                     "WORKSPACE_REGISTRATION_APPROVAL_ENABLED", "WORKSPACE_REGISTRATION_OUTBOX_ENABLED",
                     "WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED", "WORKSPACE_ACCOUNT_DIRECTORY_ENABLED"):
            self.assertIs(values[name], True, name)
        self.assertIs(values["WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED"], False)

    def test_unapproved_and_protected_gates_forced_off(self):
        values = registry.profile_settings(LAN)
        for name in ("WORKSPACE_ACCOUNT_STATUS_ENABLED", "WORKSPACE_ROLE_ASSIGNMENT_ENABLED",
                     "WORKSPACE_WF0302_ROLE_PERMISSION_MUTATIONS_ENABLED",
                     "WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED",
                     "WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED"):
            self.assertIs(values[name], False, name)

    def test_routes_only_from_approved_features(self):
        self.assertEqual(registry.profile_routes(LAN), (
            ("api/v1/admin/registration-requests/", "apps.accounts.registration_review_urls"),))

    def test_failed_prerequisite_propagates_to_dependents(self):
        available = registry.available_keys(LAN, {"wf02.applicant_decisions": ["no key"]})
        self.assertNotIn("wf02.applicant_decisions", available)
        self.assertNotIn("wf02.bulk_decisions", available)
        self.assertIn("wf02.applicant_reviews", available)
        flags = registry.frontend_environment(available)
        self.assertEqual(flags["VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED"], "0")
        self.assertEqual(flags["VITE_WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED"], "0")
        self.assertEqual(flags["VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED"], "1")
        self.assertEqual(flags["VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED"], "0")

    def test_dependency_on_unapproved_feature_is_not_approved(self):
        original = registry.FEATURES
        try:
            extra = registry.Feature(key="future.module", workflow="WF-99", title="x", profiles=frozenset({LAN}),
                                     requires=("wf02.account_status_changes",),
                                     settings=(("WORKSPACE_FUTURE_ENABLED", True),))
            registry.FEATURES = (*original, extra)
            registry._BY_KEY[extra.key] = extra
            self.assertNotIn("future.module", registry.approved_keys(LAN))
            self.assertIs(registry.profile_settings(LAN)["WORKSPACE_FUTURE_ENABLED"], False)
        finally:
            registry.FEATURES = original
            registry._BY_KEY.pop("future.module", None)


class EnvironmentTests(unittest.TestCase):
    def prepare(self, env=None, names=(), secrets=SECRETS):
        return prepare_environment(env or {}, dotenv_names=list(names), local_secrets=secrets)

    def test_synthetic_database_and_dedicated_secrets(self):
        values = self.prepare({"DB_NAME": "ctug_workspace", "DJANGO_SECRET_KEY": "real"}, ["DB_NAME"])
        self.assertEqual(values["DB_NAME"], SYNTHETIC_LAN_DATABASE)
        self.assertEqual(values["DJANGO_SECRET_KEY"], "synthetic-test-key")
        self.assertEqual(values["WORKSPACE_EMAIL_SMTP_ENABLED"], "0")
        self.assertEqual(values["WORKSPACE_OUTBOX_WORKER_ENABLED"], "0")

    def test_env_feature_flags_and_acks_neutralized(self):
        names = ["WORKSPACE_ACCOUNT_STATUS_ENABLED", "CTUG_REVIEW_LOCAL_ACK", "WORKSPACE_ROLE_ASSIGNMENT_ENABLED",
                 "CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK", "CTUG_ROLE_CONTEXT_HTTPS_LAN_DEV_ACK"]
        values = self.prepare({name: "1" for name in names}, names)
        self.assertEqual(values["WORKSPACE_ACCOUNT_STATUS_ENABLED"], "0")
        self.assertEqual(values["WORKSPACE_ROLE_ASSIGNMENT_ENABLED"], "0")
        self.assertEqual(values["CTUG_REVIEW_LOCAL_ACK"], "")
        self.assertEqual(values["CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK"], "")
        self.assertEqual(values["CTUG_ROLE_CONTEXT_HTTPS_LAN_DEV_ACK"], "")
        self.assertEqual(neutralized_flags(["WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER"])[
            "WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER"], "0")

    def test_detected_ip_configures_option_a_exactly(self):
        values = self.prepare({LAN_IP_VARIABLE: "192.168.7.20", "CTUG_ROLE_CONTEXT_LAN_DEV_IPS": "192.168.0.239"})
        self.assertEqual(values["CTUG_ROLE_CONTEXT_LAN_DEV_ACK"], LAN_ACK)
        self.assertEqual(values["CTUG_ROLE_CONTEXT_LAN_DEV_IPS"], "192.168.7.20")
        self.assertEqual(values["CTUG_ROLE_CONTEXT_LAN_DEV_IP"], "")
        self.assertEqual(values["WORKSPACE_ALLOWED_HOSTS"], "localhost,127.0.0.1,[::1],192.168.7.20")
        self.assertIn("http://192.168.7.20:5173", values["WORKSPACE_CSRF_TRUSTED_ORIGINS"].split(","))
        self.assertNotIn("192.168.0.239", " ".join(values.values()))

    def test_without_ip_profile_is_loopback_only(self):
        values = self.prepare()
        self.assertEqual(values["CTUG_ROLE_CONTEXT_LAN_DEV_ACK"], "")
        self.assertEqual(values["WORKSPACE_ALLOWED_HOSTS"], "localhost,127.0.0.1,[::1]")

    def test_public_or_invalid_ip_refused(self):
        for raw in ("8.8.8.8", "169.254.18.130", "100.100.1.1", "0.0.0.0", "hostname", "::1"):
            with self.subTest(raw=raw), self.assertRaises(DevLanEnvironmentError):
                self.prepare({LAN_IP_VARIABLE: raw})

    def test_missing_secrets_or_deployment_settings_refused(self):
        with self.assertRaisesRegex(DevLanEnvironmentError, "Initialize"):
            self.prepare(secrets={})
        with self.assertRaises(DevLanEnvironmentError):
            self.prepare({"WORKSPACE_DEPLOYMENT_SETTINGS": "1"})


class LauncherIndependenceTests(unittest.TestCase):
    """Rule: finishing a module must never require editing the launcher."""

    def test_launcher_names_no_feature_flag_route_or_workflow(self):
        text = (REPO / "Start-CTUG-LAN.ps1").read_text(encoding="utf-8")
        self.assertTrue(text.isascii(), "Windows PowerShell 5.1 reads BOM-less scripts as ANSI")
        forbidden = [r"VITE_WORKSPACE_", r"WORKSPACE_\w+_ENABLED", r"\bWF-?\d", r"registration-requests",
                     r"school-accounts/[a-z]", r"finance|clearance|group_rating|announcement"]
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, text, re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()
