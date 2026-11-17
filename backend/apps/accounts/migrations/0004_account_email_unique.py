"""Reviewed nullable unique email change; apply only through the DBA release.

No account data is rewritten. Quiesce all account writers before preflight/DDL;
MySQL DDL cannot be rolled back with the surrounding Django transaction.
"""

from django.db import migrations, models
from django.db.models import Count


def require_reconciled_emails(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        raise RuntimeError("Account email uniqueness requires reviewed MySQL semantics.")
    Account = apps.get_model("accounts", "Account")
    accounts = Account.objects.using(connection.alias)
    # Freeze the policy here rather than importing mutable application code.
    seen = set()
    for email in accounts.exclude(email=None).values_list("email", flat=True).iterator():
        normalized = email.strip().lower() or None
        if normalized is None or email != normalized or normalized in seen:
            raise RuntimeError(
                "Account emails require owner reconciliation: blank, noncanonical "
                "or duplicate values exist. No account data was changed."
            )
        seen.add(normalized)
    # GROUP BY uses the actual column collation, including its accent semantics.
    if (accounts.exclude(email=None).values("email").annotate(n=Count("pk"))
            .filter(n__gt=1).exists()):
        raise RuntimeError("Duplicate account emails exist under the MySQL collation; reconcile first.")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COLLATION_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='accounts' AND COLUMN_NAME='email'"
        )
        row = cursor.fetchone()
    if not row or not row[0] or not row[0].endswith("_ci"):
        raise RuntimeError("Review a case-insensitive MySQL email collation before applying uniqueness.")


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_registration_notification_outbox")]

    operations = [
        migrations.RunPython(require_reconciled_emails, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="account",
            name="email",
            field=models.EmailField(blank=True, max_length=150, null=True, unique=True),
        ),
    ]
