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
        import shutil
        import tempfile
        from prepare_runtime_patch import proposed_files
        labels.remove("--candidate")
        scratch = Path(tempfile.mkdtemp(prefix="wf11-v23-source-", dir=ROOT / ".local")).resolve()
        if not scratch.is_relative_to((ROOT / ".local").resolve()):
            raise RuntimeError("Invalid isolated source destination.")
        for folder in ("backend/apps", "backend/config", "backend/scripts", "docs", "review_only/academic_settings_v2_3"):
            shutil.copytree(ROOT / folder, scratch / folder,
                            ignore=shutil.ignore_patterns("__pycache__", "*.docx", "*.pdf"))
        for relative, content in proposed_files().items():
            target = scratch / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
        sys.path.remove(str(BACKEND))
        sys.path.insert(0, str(scratch / "backend"))
        os.chdir(scratch / "backend")
        if not labels:
            labels = ["candidate_runtime_tests"]
        print("Proposed patch in isolated source copy only:", scratch, flush=True)
    from django.core.management import execute_from_command_line
    execute_from_command_line([str(BACKEND / "manage.py"), "test", *labels,
                               "--settings=config.test_settings", "--noinput"])
