# WF-03.01 SR-1 Stage A (owner-authorized 19 Nov 2026): persistent per-account session-revocation counter.
# AUTHORED ONLY. Applied to disposable MySQL test databases; NOT applied to ctug_workspace (that needs a separate
# owner authorization, a controlled deployment and the authoritative ERD update). Adds one column; existing rows
# receive 0 through the database default. Reversible: unapplying drops the column (see the runbook before doing so).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_student_registration_otp'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='session_revocation_version',
            field=models.PositiveBigIntegerField(db_default=0, default=0, editable=False),
        ),
    ]
