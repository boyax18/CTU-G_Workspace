"""WF-03.01 appointment registry: schema only, no permissions/roles/appointments seeded.

Do not apply to ctug_workspace until a separate owner-approved migration window.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("access_control", "0003_remaining_access_control"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OrdinaryAppointment",
            fields=[
                ("appointment_id", models.AutoField(primary_key=True, serialize=False)),
                ("role_name", models.CharField(choices=[("Treasurer", "Treasurer"), ("SSG Advisor", "SSG Advisor")], max_length=50)),
                ("document_sha256", models.CharField(max_length=64)),
                ("valid_from", models.DateTimeField()),
                ("valid_until", models.DateTimeField()),
                ("status", models.CharField(choices=[("Submitted", "Submitted"), ("Verified", "Verified"), ("Rejected", "Rejected"), ("Revoked", "Revoked")], default="Submitted", max_length=10)),
                ("submitted_at", models.DateTimeField(auto_now_add=True, editable=False)),
                ("reviewed_at", models.DateTimeField(blank=True, editable=False, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, editable=False, null=True)),
                ("account", models.ForeignKey(db_column="account_id", on_delete=django.db.models.deletion.PROTECT, related_name="ordinary_appointments", to=settings.AUTH_USER_MODEL)),
                ("submitted_by", models.ForeignKey(db_column="submitted_by", editable=False, on_delete=django.db.models.deletion.PROTECT, related_name="ordinary_appointments_submitted", to=settings.AUTH_USER_MODEL)),
                ("reviewed_by", models.ForeignKey(blank=True, db_column="reviewed_by", editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ordinary_appointments_reviewed", to=settings.AUTH_USER_MODEL)),
                ("revoked_by", models.ForeignKey(blank=True, db_column="revoked_by", editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ordinary_appointments_revoked", to=settings.AUTH_USER_MODEL)),
                ("submission_receipt", models.ForeignKey(blank=True, db_column="submission_receipt_id", editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="submitted_appointment_evidence", to="access_control.accessauditlog")),
                ("review_receipt", models.ForeignKey(blank=True, db_column="review_receipt_id", editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reviewed_appointment_evidence", to="access_control.accessauditlog")),
                ("revocation_receipt", models.ForeignKey(blank=True, db_column="revocation_receipt_id", editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="revoked_appointment_evidence", to="access_control.accessauditlog")),
            ],
            options={"db_table": "ordinary_appointments"},
        ),
        migrations.AddConstraint(model_name="ordinaryappointment", constraint=models.UniqueConstraint(fields=("account", "role_name", "document_sha256"), name="ordinary_appt_document_unique")),
        migrations.AddIndex(model_name="ordinaryappointment", index=models.Index(fields=["account", "role_name", "status"], name="ordinary_appt_lookup")),
        migrations.AddIndex(model_name="ordinaryappointment", index=models.Index(fields=["status", "valid_until"], name="ordinary_appt_expiry")),
    ]
