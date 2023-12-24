# Generated by Django 4.2 on 2023-12-24 17:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="enrollment",
            name="certificate_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="enrollment",
            name="display_on_leaderboard",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="enrollment",
            name="display_name",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
