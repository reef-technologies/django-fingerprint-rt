from django.core.management.base import BaseCommand

from fingerprint.models import RequestHitCount


class Command(BaseCommand):
    help = "Rebuild request fingerprint hit counts from fingerprint rows."

    def add_arguments(self, parser):
        parser.add_argument("--chunk-size", type=int, default=1000)

    def handle(self, *args, **options):
        RequestHitCount.rebuild_hit_counts(chunk_size=options["chunk_size"])
        self.stdout.write(self.style.SUCCESS("Hit counts rebuilt"))
