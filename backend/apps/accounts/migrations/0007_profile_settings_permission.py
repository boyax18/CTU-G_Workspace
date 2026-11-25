from django.db import migrations


def seed_profile_settings_permission(apps, schema_editor):
    Service = apps.get_model("access_control", "Service")
    Permission = apps.get_model("access_control", "Permission")
    Role = apps.get_model("access_control", "Role")
    RolePermission = apps.get_model("access_control", "RolePermission")

    service, _ = Service.objects.get_or_create(
        service_code="accounts",
        defaults={"service_name": "Accounts", "is_active": True},
    )
    permission, _ = Permission.objects.get_or_create(
        permission_code="accounts.profile.self.update",
        defaults={
            "service": service,
            "permission_name": "Update own profile",
            "module_name": "Accounts",
            "action_name": "update",
        },
    )
    role = Role.objects.filter(role_name="Student", is_active=True).first()
    if role:
        RolePermission.objects.get_or_create(role=role, permission=permission)


def reverse_seed(apps, schema_editor):
    RolePermission = apps.get_model("access_control", "RolePermission")
    RolePermission.objects.filter(
        role__role_name="Student",
        permission__permission_code="accounts.profile.self.update",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_account_session_revocation_version"),
        ("access_control", "0003_remaining_access_control"),
    ]

    operations = [
        migrations.RunPython(seed_profile_settings_permission, reverse_seed),
    ]
