import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Count


def rebuild_hit_counts(apps, schema_editor, chunk_size=1000):
    RequestFingerprint = apps.get_model("fingerprint", "RequestFingerprint")
    RequestHitCount = apps.get_model("fingerprint", "RequestHitCount")
    last_id = 0
    while url_ids := list(
        RequestFingerprint.objects.filter(url_id__gt=last_id)
        .values_list("url_id", flat=True)
        .distinct()
        .order_by("url_id")[:chunk_size]
    ):
        last_id = url_ids[-1]
        rows = (
            RequestFingerprint.objects.filter(url_id__in=url_ids)
            .values("url")
            .annotate(hits=Count("user_session", distinct=True))
            .values_list("url", "hits")
        )
        RequestHitCount.objects.bulk_create(
            [RequestHitCount(url_id=url_id, hits=hits) for url_id, hits in rows],
            update_conflicts=True,
            unique_fields=["url"],
            update_fields=["hits"],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("fingerprint", "0007_alter_url_value"),
    ]

    operations = [
        migrations.CreateModel(
            name="RequestHitCount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hits", models.PositiveIntegerField(default=0)),
                (
                    "url",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="request_hit_count",
                        to="fingerprint.url",
                    ),
                ),
            ],
        ),
        migrations.RunPython(rebuild_hit_counts, migrations.RunPython.noop),
    ]
