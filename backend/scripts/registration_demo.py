"""Run registration against disposable MySQL. Ctrl+C removes the test database.

Never use this helper as a deployment entry point. The normal development
database is excluded by config.test_settings and the guarded test runner.
"""

import argparse
import json
import os
import socket
from pathlib import Path
import sys
import threading
import time
from wsgiref.simple_server import WSGIServer, make_server

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.test_settings"

import django

django.setup()

from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.db import connections
from config.test_runner import IsolatedMySQLRunner
from apps.accounts.models import Account, UserProfile
from apps.access_control.models import AccountRole, Role


class ExclusiveDemoServer(WSGIServer):
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=300)
    args = parser.parse_args()
    runner = IsolatedMySQLRunner(interactive=False, verbosity=1)
    old_config = runner.setup_databases(aliases={"default"})
    server = None
    try:
        for name in ("Student", "Instructor"):
            Role.objects.create(role_name=name)
        application = get_wsgi_application()

        def observed_application(environ, start_response):
            response_status = []

            def observe(status, headers, exc_info=None):
                response_status.append(status)
                headers.append(("X-Registration-Demo-Database", settings.REGISTRATION_TEST_DATABASE))
                return start_response(status, headers, exc_info)

            result = application(environ, observe)
            if environ.get("PATH_INFO") == "/api/v1/auth/register/" and response_status == ["202 Accepted"]:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SELECT DATABASE()")
                    assert cursor.fetchone()[0] == settings.REGISTRATION_TEST_DATABASE
                accounts = list(Account.objects.all())
                print(json.dumps({
                    "database": settings.REGISTRATION_TEST_DATABASE,
                    "accounts": len(accounts), "profiles": UserProfile.objects.count(),
                    "all_pending": all(a.request_status == "Pending" for a in accounts),
                    "all_inactive": all(not a.is_active for a in accounts),
                    "all_passwords_hashed": all(a.password.startswith("pbkdf2_sha256$") for a in accounts),
                    "role_assignments": AccountRole.objects.count(),
                }), flush=True)
            return result

        server = make_server("127.0.0.1", 8765, observed_application, server_class=ExclusiveDemoServer)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print("Disposable registration backend: http://127.0.0.1:8765; Ctrl+C cleans up.", flush=True)
        deadline = time.monotonic() + max(1, min(args.seconds, 1800))
        while time.monotonic() < deadline:
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        if server:
            server.shutdown()
            server.server_close()
        connections.close_all()
        runner.teardown_databases(old_config)


if __name__ == "__main__":
    main()
