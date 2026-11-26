"""Test-only entry point; never selects the development database or launcher profile."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def test_environment():
    from dotenv import load_dotenv
    load_dotenv(BACKEND / ".env")
    # Empty values must survive dotenv (PowerShell 5 removes empty environment values).
    for name in ("CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK", "CTUG_ROLE_CONTEXT_LAN_DEV_ACK",
                 "CTUG_ROLE_CONTEXT_HTTPS_LAN_ACK"):
        os.environ[name] = ""
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.test_settings"
    # Also replace NAME before importing the base settings; test_settings replaces it again.
    os.environ["DB_NAME"] = "test_ctug_registration_" + __import__("secrets").token_hex(8)


if __name__ == "__main__":
    test_environment()
    labels = sys.argv[1:]
    if "--candidate" in labels:
        raise SystemExit("The v2.3 patch is applied (owner local-development authorization, 27 Nov 2026); "
                         "run the suites directly without --candidate.")
    os.chdir(BACKEND)  # path labels (apps/...) resolve against the real backend; disposable MySQL only
    if not labels:
        labels = ["candidate_runtime_tests"]
    from django.core.management import execute_from_command_line
    execute_from_command_line([str(BACKEND / "manage.py"), "test", *labels,
                               "--settings=config.test_settings", "--noinput"])
