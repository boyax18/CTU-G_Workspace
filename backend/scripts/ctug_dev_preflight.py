"""Read-only startup preflight for Start-CTUG-LAN.ps1. Prints ONE JSON object.

    python scripts/ctug_dev_preflight.py --mode lan --lan-ip 192.168.1.5
    python scripts/ctug_dev_preflight.py --mode local

Builds the launch environment from config/dev_features.py, loads Django with it
(so the existing settings gates validate it) and checks the configured database.
It never writes: no migrations are applied, no rows are created, and no secret,
password or personal field is printed (aggregate counts only).
"""

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True)
    parser.add_argument("--lan-ip", default="")
    args = parser.parse_args()
    report = {"ok": False, "errors": [], "warnings": []}
    try:
        from config import dev_features
        launch = dev_features.mode_environment(args.mode, lan_ip=args.lan_ip,
                                               env=dev_features.dotenv_environment(BACKEND))
        report.update(launch)
        os.environ.update(launch["backend_env"])
        import django
        django.setup()
        from django.conf import settings
        from django.core import checks
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        db = settings.DATABASES["default"]
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            connected = cursor.fetchone()[0]
        report["database"] = db["NAME"]
        report["database_connected"] = connected
        if connected != db["NAME"]:
            report["errors"].append("The connected schema differs from the configured database.")
        errors = [str(m) for m in checks.run_checks() if m.level >= checks.ERROR]
        report["errors"] += errors[:5]
        executor = MigrationExecutor(connection)
        pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
        report["pending_migrations"] = [f"{m.app_label}.{m.name}" for m, _backwards in pending]
        if pending:
            report["warnings"].append(
                f"{len(pending)} migration(s) are not applied to {db['NAME']}; the launcher never applies them. "
                "Features that need those tables stay unavailable until an approved migration step.")
        if launch.get("workers"):
            from apps.accounts.outbox_worker import due_job_count
            earlier = due_job_count()
            report["warnings"].append(
                "Email delivery is ON: notifications queued from now on are emailed automatically"
                + (f"; {earlier} earlier queued notification(s) are NOT sent automatically"
                   " (deliver them deliberately with: manage.py process_registration_outbox --deliver)." if earlier else "."))
        from apps.accounts.models import Account
        report["pending_applicants"] = Account.objects.filter(request_status="Pending", is_active=False).count()
        report["approved_accounts"] = Account.objects.filter(request_status="Approved").count()
        report["role_context"] = bool(getattr(settings, "WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED", False))
        report["lan_ip"] = getattr(settings, "WORKSPACE_ROLE_CONTEXT_LAN_DEV_IP", None)
        report["email"] = "smtp" if "smtp" in settings.EMAIL_BACKEND else settings.EMAIL_BACKEND.rsplit(".", 2)[-2]
    except Exception as exc:  # report the reason only; never credentials or tracebacks with values
        name = exc.__class__.__name__
        if name == "OperationalError":
            report["errors"].append("Database connection failed. Is MySQL running and is backend/.env correct?")
        else:
            message = str(exc) if name in ("ImproperlyConfigured", "ValueError") else ""
            report["errors"].append(f"{name}: {message}".rstrip(": "))
    report["ok"] = not report["errors"]
    print(json.dumps(report, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
