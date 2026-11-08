"""Local, console-only, one-time first Workspace Admin provisioning command."""

import getpass
import sys

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.admin_bootstrap import (
    BootstrapRefused,
    bootstrap_preflight,
    provision_first_workspace_admin,
)


class Command(BaseCommand):
    help = "Read-only first Admin preflight (default); --apply requires authenticated operator."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Explicitly attempt the one-time Admin creation (disabled by default).",
        )

    def handle(self, *args, **options):
        try:
            result = bootstrap_preflight()
        except BootstrapRefused as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write("CTU-G Workspace first Admin bootstrap preflight:")
        for field, value in result.items():
            self.stdout.write(f"  {field}: {value}")
        if not options["apply"]:
            self.stdout.write("READ-ONLY: no account, role assignment or audit record was created.")
            return

        if not sys.stdin.isatty():
            raise CommandError("--apply requires an interactive console; piped input is refused.")
        if not result["admin_role_exists_and_active"]:
            raise CommandError("The active Admin role is missing.")
        if result["existing_admin_assignments"] or result["previous_bootstrap_events"]:
            raise CommandError("Initial Admin already exists or bootstrap was already recorded.")
        if result["framework_operators"] != 1:
            raise CommandError("Exactly one active, approved Django Superuser operator is required.")

        self.stdout.write(self.style.WARNING(
            "This operation creates a NEW approved Workspace Admin, not a Django Superuser."
        ))
        self.stdout.write("Pending Student/Instructor registrations remain unchanged.")
        operator_id = input("Existing Django Superuser school ID: ").strip()
        operator_password = getpass.getpass("Django Superuser password (hidden): ")
        new_school_id = input("NEW Workspace Admin school ID: ").strip()
        new_email = input("NEW Workspace Admin email: ").strip()
        new_password = getpass.getpass("NEW Workspace Admin password (hidden): ")
        password_confirmation = getpass.getpass("Confirm NEW Admin password (hidden): ")
        if new_password != password_confirmation:
            raise CommandError("New Admin passwords do not match; no changes made.")
        confirmation = input("Type CREATE FIRST WORKSPACE ADMIN to confirm: ").strip()
        if confirmation != "CREATE FIRST WORKSPACE ADMIN":
            raise CommandError("Confirmation was not exact; no changes made.")
        try:
            account_id = provision_first_workspace_admin(
                operator_school_id=operator_id,
                operator_password=operator_password,
                new_school_id=new_school_id,
                new_email=new_email,
                new_password=new_password,
            )
        except BootstrapRefused as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"First Workspace Admin provisioned and audited (account ID {account_id})."
        ))
        self.stdout.write("No services, permissions or role defaults were activated.")
