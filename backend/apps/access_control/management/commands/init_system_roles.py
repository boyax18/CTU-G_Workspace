from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections, transaction

from apps.access_control.models import Role


SYSTEM_ROLES = (
    ("Student", "System role for student accounts."),
    ("Instructor", "System role for instructor accounts."),
    ("Treasurer", "Restricted system role for treasury accounts."),
    ("Admin", "Restricted system role for administrator accounts."),
)


class Command(BaseCommand):
    help = "Create missing canonical system roles without changing existing roles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            choices=tuple(connections),
            help="Database alias to initialize (default: default).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report existing and missing roles without writing any records.",
        )

    @staticmethod
    def _check_name(role, canonical_name):
        if role.role_name != canonical_name:
            raise CommandError(
                f"Conflicting role name {role.role_name!r} matches "
                f"{canonical_name!r}. Resolve the conflict explicitly; "
                "no roles were renamed."
            )

    def _plan(self, database):
        plan = []
        for name, description in SYSTEM_ROLES:
            try:
                role = Role.objects.using(database).get(role_name=name)
            except Role.DoesNotExist:
                role = None
            except Role.MultipleObjectsReturned as exc:
                raise CommandError(f"Multiple roles match {name!r}; initialization stopped.") from exc
            if role is not None:
                self._check_name(role, name)
            plan.append((name, description, role))
        return plan

    def handle(self, *args, **options):
        database = options["database"]
        try:
            plan = self._plan(database)
            if options["dry_run"]:
                for name, _description, role in plan:
                    if role is None:
                        self.stdout.write(f"Would create {name} (active).")
                    else:
                        status = "active" if role.is_active else "inactive"
                        self.stdout.write(f"Exists {name} ({status}; unchanged).")
                self.stdout.write("Dry run complete. No database changes made.")
                return

            results = []
            with transaction.atomic(using=database):
                for name, description, _role in plan:
                    role, created = Role.objects.using(database).get_or_create(
                        role_name=name,
                        defaults={"description": description},
                    )
                    # Recheck after get_or_create: another initializer may have raced.
                    self._check_name(role, name)
                    results.append((role, created))
        except DatabaseError as exc:
            raise CommandError(
                "System role initialization failed; no role changes were committed."
            ) from exc

        # Report successful creation only after the transaction has committed.
        for role, created in results:
            status = "active" if role.is_active else "inactive"
            if created:
                self.stdout.write(f"Created {role.role_name} ({status}).")
            else:
                self.stdout.write(f"Exists {role.role_name} ({status}; unchanged).")
        created_count = sum(created for _role, created in results)
        self.stdout.write(
            self.style.SUCCESS(
                f"System roles initialized: {created_count} created, "
                f"{len(results) - created_count} existing."
            )
        )
