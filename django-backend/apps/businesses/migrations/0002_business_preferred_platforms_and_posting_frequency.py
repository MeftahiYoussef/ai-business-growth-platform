from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("businesses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="business",
            name="preferred_platforms",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="business",
            name="posting_frequency",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
