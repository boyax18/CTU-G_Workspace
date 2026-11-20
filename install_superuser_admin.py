"""Guarded preview/apply for CTU-G Workspace framework superuser read-only Admin."""

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys

BASE = Path(__file__).resolve().parent
PATCH = BASE / "patch"
REPLACE_IF_PLACEHOLDER = {
    "backend/apps/accounts/admin.py",
    "backend/apps/access_control/admin.py",
}


def is_placeholder(text):
    lines = [line.strip() for line in text.replace("\r", "").splitlines()]
    lines = [line for line in lines if line and not line.startswith("#")]
    return lines == ["from django.contrib import admin"]


def main():
    parser = ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    project = Path(args.project).resolve()
    if not (project / "backend/manage.py").is_file():
        parser.error("--project must be the CTU-G Workspace repository root")
    entries = sorted(
        path for path in PATCH.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    planned = []
    blockers = []
    print(f"Project: {project}")
    for src in entries:
        rel = src.relative_to(PATCH)
        dst = project / rel
        data = src.read_bytes()
        if dst.exists():
            if dst.read_bytes() == data:
                verdict = "ALREADY INSTALLED"
            elif rel.as_posix() in REPLACE_IF_PLACEHOLDER and is_placeholder(dst.read_text(encoding="utf-8-sig")):
                verdict = "REPLACE PLACEHOLDER"
                planned.append((src, dst, True))
            else:
                verdict = "BLOCKED: existing file differs; manual review needed"
                blockers.append(str(rel))
        else:
            verdict = "NEW"
            planned.append((src, dst, False))
        print(f"  {verdict:<26} {rel}")
    if blockers:
        print("ABORTED. No files were written. Existing custom code must be reviewed.")
        return 2
    if not args.apply:
        print("DRY RUN ONLY. No files changed. Apply after reviewing with --apply.")
        return 0
    if not planned:
        print("All patch files already installed. Nothing to change.")
        return 0
    backup = Path.home() / "Documents" / "CTUG-Private-Backups" / (
        "readonly-framework-admin-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    for src, dst, replacing in planned:
        if replacing:
            out = backup / dst.relative_to(project)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, out)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print(f"APPLIED: {len(planned)} files. Existing replacements backed up under {backup if backup.exists() else '(none needed)'}")
    print("No models, migrations, database records, permission grants, or routes changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
