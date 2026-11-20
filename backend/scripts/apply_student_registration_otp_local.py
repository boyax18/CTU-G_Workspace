"""One-time WF-01.01 local development release; preserves all legacy row values.

Run from backend with --apply-local-student-otp. This handles ONLY the observed
local state: exact 0004 email index already present, accounts ledger at 0003.
It does not infer that migration 0004 was historically executed. It explicitly
reconciles that index-only migration after verifying its entire expected effect.
Other states require normal reviewed Django migration deployment.
"""
import hashlib
import hmac
import importlib
import json
import os
from pathlib import Path
import secrets
import sys
from datetime import datetime, timezone


def main():
    if sys.argv[1:] != ["--apply-local-student-otp"]:
        raise SystemExit("Exact local development release acknowledgement required.")
    backend = Path(__file__).resolve().parents[1]
    if Path.cwd().resolve() != backend:
        raise SystemExit("Run from backend/.")
    sys.path.insert(0, str(backend))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if os.environ["DJANGO_SETTINGS_MODULE"] != "config.settings":
        raise SystemExit("This helper supports only the local development settings.")
    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    def require(condition):
        if not condition:
            raise RuntimeError("Local release preflight differs from the reviewed state; stop and inspect.")

    require(connection.vendor == "mysql")
    require(connection.settings_dict["HOST"] in {"127.0.0.1", "localhost", "::1"})
    require(not getattr(settings, "WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER", False))
    snapshot = {}
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        require(cursor.fetchone()[0] == "ctug_workspace")
        cursor.execute("SELECT name FROM django_migrations WHERE app='accounts' ORDER BY name")
        require([r[0] for r in cursor.fetchall()] == [
            "0001_initial", "0002_account_is_staff_account_is_superuser", "0003_registration_notification_outbox",
        ])
        cursor.execute("SELECT INDEX_NAME,NON_UNIQUE,COLUMN_NAME,SEQ_IN_INDEX,SUB_PART FROM information_schema.STATISTICS "
                       "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='accounts' AND INDEX_NAME='accounts_email_200aa879_uniq'")
        require(cursor.fetchall() == (("accounts_email_200aa879_uniq", 0, "email", 1, None),))
        cursor.execute("SELECT COLUMN_TYPE,IS_NULLABLE,COLLATION_NAME FROM information_schema.COLUMNS "
                       "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='accounts' AND COLUMN_NAME='email'")
        require(cursor.fetchone() == ("varchar(150)", "YES", "utf8mb4_unicode_ci"))
        cursor.execute("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='student_registration_staging'")
        require(cursor.fetchone()[0] == 0)
        cursor.execute("SELECT COUNT(*) FROM accounts WHERE request_status='Pending'")
        require(cursor.fetchone()[0] == 0)
        for table in ("accounts", "users", "django_migrations"):
            cursor.execute("SHOW CREATE TABLE `" + table + "`")
            ddl = cursor.fetchone()[1]
            cursor.execute("SELECT * FROM `" + table + "` ORDER BY 1")
            snapshot[table] = {"ddl": ddl, "columns": [d[0] for d in cursor.description], "rows": cursor.fetchall()}

    old_apps = MigrationExecutor(connection).loader.project_state([("accounts", "0003_registration_notification_outbox")]).apps
    with connection.schema_editor() as editor:
        importlib.import_module("apps.accounts.migrations.0004_account_email_unique").require_reconciled_emails(old_apps, editor)

    raw = json.dumps(snapshot, default=str, sort_keys=True).encode()
    key = hmac.new(settings.SECRET_KEY.encode(), b"ctug:wf01.01:recovery-snapshot:v1", hashlib.sha256).digest()
    nonce, aad = secrets.token_bytes(12), b"ctug:wf01.01:pre-otp-schema:v1"
    blob = nonce + AESGCM(key).encrypt(nonce, raw, aad)
    require(AESGCM(key).decrypt(blob[:12], blob[12:], aad) == raw)
    directory = backend.parent / ".local" / "recovery"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (directory / ("wf01.01-pre-otp-" + stamp + ".aesgcm")).write_bytes(blob)
    print("Encrypted recovery snapshot saved under .local/recovery; no account data or key printed.")
    # The original 0004 operation adds only the verified existing unique index,
    # after its SELECT-only data preflight. Record reconciliation, not repeat DDL.
    call_command("migrate", "accounts", "0004_account_email_unique", fake=True, interactive=False)
    call_command("migrate", "accounts", "0005_student_registration_otp", interactive=False)
    with connection.cursor() as cursor:
        for table in ("accounts", "users"):
            columns = snapshot[table]["columns"]
            cursor.execute("SELECT " + ",".join("`" + name + "`" for name in columns) + " FROM `" + table + "` ORDER BY 1")
            require(cursor.fetchall() == snapshot[table]["rows"])
        cursor.execute("SELECT COUNT(*) FROM accounts WHERE email_verified_at IS NOT NULL OR email_verified_address IS NOT NULL")
        require(cursor.fetchone()[0] == 0)
        cursor.execute("SELECT name FROM django_migrations WHERE app='accounts' ORDER BY name")
        print("Account migration names:", [r[0] for r in cursor.fetchall()])
    print("Development OTP schema ready; legacy account/profile values preserved and no legacy verification invented.")


if __name__ == "__main__":
    main()
