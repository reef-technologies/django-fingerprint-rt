# Generated by Django 5.0.4 on 2024-04-26 19:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fingerprint", "0003_alter_browserfingerprint_url_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="requestfingerprint",
            name="cf_ipcountry",
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name="requestfingerprint",
            name="referer",
            field=models.CharField(blank=True, max_length=2047),
        ),
    ]
