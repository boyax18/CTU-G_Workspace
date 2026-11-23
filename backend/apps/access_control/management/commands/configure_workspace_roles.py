"""WF-03.01 protected Django-Superuser role configuration (interactive console only).

    manage.py configure_workspace_roles --operation grant-technical-super-admin --target-account-id 42
    manage.py configure_workspace_roles --operation grant-technical-super-admin --target-account-id 42 \
        --apply --confirm <the exact confirmation printed without --apply>

Without --apply nothing is read or written: the exact confirmation is printed (database-bound,
`ctug_workspace:WF-03.01:<operation>:<id>`, for the local development target). With --apply an
interactive terminal is required; the designated framework operator's CTU-G ID and password are
read from the console (never from arguments, environment or files) and are never printed or stored.
The procedure itself (apps.access_control.framework_roles) enforces every rule: the disposable MySQL
test database, or the local development database only when every D-93/D-95 gate condition holds
(including WORKSPACE_ROLE_CONFIGURATION_OPERATORS set in the process environment, never in .env).
"""
import getpass
import sys

from django.core.management.base import BaseCommand, CommandError

from apps.access_control.framework_roles import OPERATIONS, configure_role, confirmation_for
from apps.access_control.role_management import RoleChangeConflict, RoleChangeDenied, RoleChangeUnavailable


class Command(BaseCommand):
    help = "WF-03.01: Django-Superuser-exclusive School Admin / Technical Super Admin grant or revoke (protected)."

    def add_arguments(self, parser):
        parser.add_argument("--operation", choices=OPERATIONS, required=True)
        parser.add_argument("--target-account-id", type=int, required=True)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--confirm", default="")

    def handle(self, *args, **options):
        operation, target_id = options["operation"], options["target_account_id"]
        expected = confirmation_for(operation, target_id)
        if not options["apply"]:
            self.stdout.write(f"REVIEW ONLY. Nothing was read or changed. To apply, add --apply --confirm {expected}")
            return
        if options["confirm"] != expected:
            raise CommandError("The exact confirmation for this operation and account is required.")
        if not sys.stdin.isatty():
            raise CommandError("An interactive terminal is required for the operator's re-authentication.")
        operator = input("Designated framework operator CTU-G ID: ").strip()
        password = getpass.getpass("Operator password: ")
        try:
            result = configure_role(operation=operation, operator_school_id=operator, operator_password=password,
                                    target_id=target_id, confirmation=options["confirm"])
        except RoleChangeConflict as exc:
            raise CommandError(f"Refused ({exc.reason}); nothing was changed.") from None
        except (RoleChangeDenied, RoleChangeUnavailable) as exc:
            raise CommandError(f"Refused: {exc} Nothing was changed.") from None
        except Exception:
            raise CommandError("Refused or rolled back; nothing was changed. Inspect the current state before retrying.") from None
        finally:
            password = None  # noqa: F841 — drop the reference promptly
        self.stdout.write(f"Committed: {result['operation']} for account {result['account_id']}. "
                          "The account's existing sessions have ended.")
