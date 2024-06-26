# Generated by Django 4.2 on 2023-05-02 10:22

import django.contrib.auth.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserFingerprint",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("auth.user",),
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name="UserSession",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("session_key", models.CharField(max_length=40)),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RequestFingerprint",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("ip", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=255)),
                ("accept", models.CharField(blank=True, max_length=255)),
                ("content_encoding", models.CharField(blank=True, max_length=255)),
                ("content_language", models.CharField(blank=True, max_length=255)),
                (
                    "user_session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(model_name)ss",
                        to="fingerprint.usersession",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="BrowserFingerprint",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("visitor_id", models.CharField(max_length=255)),
                (
                    "user_session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(model_name)ss",
                        to="fingerprint.usersession",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="usersession",
            index=models.Index(fields=["user", "-created"], name="fingerprint_user_id_b99b01_idx"),
        ),
        migrations.AddConstraint(
            model_name="usersession",
            constraint=models.UniqueConstraint(fields=("session_key", "user"), name="unique_user_session"),
        ),
        migrations.AddIndex(
            model_name="requestfingerprint",
            index=models.Index(
                fields=["user_session", "-created"],
                name="fingerprint_user_se_1d7864_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="requestfingerprint",
            index=models.Index(fields=["ip", "-created"], name="fingerprint_ip_56a800_idx"),
        ),
        migrations.AddIndex(
            model_name="requestfingerprint",
            index=models.Index(fields=["user_agent", "-created"], name="fingerprint_user_ag_5d70f2_idx"),
        ),
        migrations.AddIndex(
            model_name="browserfingerprint",
            index=models.Index(
                fields=["user_session", "-created"],
                name="fingerprint_user_se_480add_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="browserfingerprint",
            index=models.Index(fields=["visitor_id", "-created"], name="fingerprint_visitor_af9597_idx"),
        ),
    ]
