from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_job_current_step"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="gpu_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
