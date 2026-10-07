import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="company",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="customer",
            name="job_title",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="customer",
            name="status",
            field=models.CharField(
                choices=[
                    ("lead", "Lead"),
                    ("contacted", "Contacted"),
                    ("qualified", "Qualified"),
                    ("customer", "Customer"),
                    ("inactive", "Inactive"),
                ],
                default="lead",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="customer",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="customers_owned",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="Activity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("call", "Call"),
                            ("email", "Email"),
                            ("meeting", "Meeting"),
                            ("note", "Note"),
                            ("status", "Status change"),
                        ],
                        default="call",
                        max_length=20,
                        verbose_name="type",
                    ),
                ),
                ("subject", models.CharField(max_length=200)),
                ("details", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="activities",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activities",
                        to="customers.customer",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "verbose_name_plural": "activities",
            },
        ),
    ]
