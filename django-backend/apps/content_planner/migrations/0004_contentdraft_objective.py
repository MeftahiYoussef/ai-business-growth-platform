from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content_planner", "0003_contentdraft_content_pla_busines_2c30d0_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="contentdraft",
            name="objective",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
