"""WF-03.03 staged role-scoped Grant mapping. NO DATA MIGRATION.

Owner-authorized DB change and consolidated verification are required before
migrate is run on real ctug_workspace. Existing override rows stay untouched.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("access_control", "0004_ordinary_appointments")]

    operations = [
        migrations.CreateModel(
            name="AccountPermissionRoleScope",
            fields=[
                ("account_permission", models.OneToOneField(
                    db_column="account_permission_id", primary_key=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="role_scope", serialize=False,
                    to="access_control.accountpermission",
                )),
                ("role", models.ForeignKey(
                    db_column="role_id", on_delete=django.db.models.deletion.PROTECT,
                    related_name="account_permission_scopes", to="access_control.role",
                )),
            ],
            options={"db_table": "account_permission_role_scopes"},
        ),
    ]
