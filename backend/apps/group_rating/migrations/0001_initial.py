from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RatingSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("deadline", models.DateTimeField()),
                ("criteria", models.JSONField(default=list)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published"), ("closed", "Closed"), ("released", "Released")], default="draft", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_rating_sessions", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="RatingGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("leader", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="led_rating_groups", to=settings.AUTH_USER_MODEL)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="groups", to="group_rating.ratingsession")),
            ],
        ),
        migrations.CreateModel(
            name="RatingMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rating_memberships", to=settings.AUTH_USER_MODEL)),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="members", to="group_rating.ratinggroup")),
            ],
        ),
        migrations.CreateModel(
            name="RatingSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ratings", models.JSONField(default=dict)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="submissions", to="group_rating.ratinggroup")),
                ("rater", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rating_submissions", to=settings.AUTH_USER_MODEL)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="submissions", to="group_rating.ratingsession")),
            ],
        ),
        migrations.CreateModel(
            name="IndividualResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scores", models.JSONField(default=dict)),
                ("final_score", models.DecimalField(decimal_places=2, max_digits=7)),
                ("released_at", models.DateTimeField(null=True, blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="group_rating.ratinggroup")),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="group_rating.ratingsession")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="individual_rating_results", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="RatingActivity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=100)),
                ("detail", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rating_activity", to=settings.AUTH_USER_MODEL)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="activity", to="group_rating.ratingsession")),
            ],
        ),
        migrations.AddConstraint(model_name="ratinggroup", constraint=models.UniqueConstraint(fields=("session", "leader"), name="rating_session_leader_unique")),
        migrations.AddConstraint(model_name="ratingmember", constraint=models.UniqueConstraint(fields=("group", "account"), name="rating_group_member_unique")),
        migrations.AddConstraint(model_name="ratingsubmission", constraint=models.UniqueConstraint(fields=("session", "rater", "group"), name="rating_submission_unique")),
        migrations.AddConstraint(model_name="individualresult", constraint=models.UniqueConstraint(fields=("session", "student", "group"), name="individual_rating_result_unique")),
    ]
