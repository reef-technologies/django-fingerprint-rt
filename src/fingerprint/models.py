from __future__ import annotations

import typing
from collections import Counter
from contextlib import suppress

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import IntegrityError, models, transaction
from django.db.models import Count, Exists, F, Model, OuterRef
from django.db.models.signals import post_save
from django.dispatch import receiver

from .fields import TruncatedCharField

if typing.TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser
    from django.http import HttpRequest
    from django.shortcuts import SupportsGetAbsoluteUrl


class UserSession(models.Model):
    # by default, django stores session data in database; however, we cannot rely on it,
    # since other session backends may be used, plus django doesn't store user-session
    # mapping, so we need to have additional table for that

    user: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True, related_name="sessions"
    )
    session_key: models.CharField = models.CharField(max_length=40)
    created: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    referer: models.CharField = TruncatedCharField(max_length=2047, blank=True)

    # Urchin Tracking Module (UTM) parameters
    utm_source: models.CharField = TruncatedCharField(max_length=255, blank=True)
    utm_medium: models.CharField = TruncatedCharField(max_length=255, blank=True)
    utm_campaign: models.CharField = TruncatedCharField(max_length=255, blank=True)
    utm_content: models.CharField = TruncatedCharField(max_length=255, blank=True)
    utm_term: models.CharField = TruncatedCharField(max_length=255, blank=True)

    def __str__(self):
        return self.session_key

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session_key", "user"], name="unique_user_session"),
        ]
        indexes = [
            models.Index(fields=["user", "-created"]),
        ]

    def get_value_display(self) -> str:
        return self.session_key[:8]


@receiver(post_save, sender=Session)
def connect_user_to_session(sender, instance, created, **kwargs):
    if user_id := instance.get_decoded().get("_auth_user_id"):
        UserSession.objects.update_or_create(
            session_key=instance.session_key,
            defaults=dict(user_id=user_id),
        )


class UrlQuerySet(models.QuerySet):
    def get_get_or_create(self, defaults: dict = {}, **query) -> tuple[Model, bool]:
        """
        Try to retrieve an object using simple `get()` query, and fallback to `get_or_create()`
        if the object is not found.

        This is required for django-cacheops to be able to cache the `get()` query, since it
        cannot cache `get_or_create` queries.
        """
        with suppress(self.model.DoesNotExist):
            return self.get(**query), False

        with transaction.atomic():
            try:
                return self.create(**{**query, **defaults}), True
            except IntegrityError:
                return self.get(**query), False


class Url(models.Model):
    value = TruncatedCharField(max_length=2048, unique=True)

    objects = UrlQuerySet.as_manager()

    def __str__(self) -> str:
        return self.value


class RequestHitCount(models.Model):
    url = models.OneToOneField(Url, on_delete=models.CASCADE, related_name="request_hit_count")
    hits = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.url_id}: {self.hits}"

    @classmethod
    def inc(cls, url: Url) -> None:
        updated = cls.objects.filter(url=url).update(hits=F("hits") + 1)
        if not updated:
            try:
                cls.objects.create(url=url, hits=1)
            except IntegrityError:
                cls.objects.filter(url=url).update(hits=F("hits") + 1)

    @classmethod
    def set(cls, url: Url, hits: int) -> None:
        cls.objects.update_or_create(url=url, defaults={"hits": hits})

    @classmethod
    def rebuild_hit_counts(cls, chunk_size: int = 1000) -> None:
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
            cls.objects.bulk_create(
                [cls(url_id=url_id, hits=hits) for url_id, hits in rows],
                update_conflicts=True,
                unique_fields=["url"],
                update_fields=["hits"],
            )

        stale = cls.objects.filter(~Exists(RequestFingerprint.objects.filter(url_id=OuterRef("url_id"))))
        while pks := list(stale.order_by("pk").values_list("pk", flat=True)[:chunk_size]):
            cls.objects.filter(pk__in=pks).delete()


class AbstractFingerprint(models.Model):
    user_session: models.ForeignKey = models.ForeignKey(
        UserSession, on_delete=models.CASCADE, related_name="%(model_name)ss"
    )
    url: models.ForeignKey = models.ForeignKey(Url, on_delete=models.CASCADE, related_name="%(model_name)ss")
    created: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["user_session", "-created"]),
            models.Index(fields=["url", "user_session"]),
        ]

    @property
    def user(self) -> AbstractBaseUser | None:
        return self.user_session.user


class BrowserFingerprint(AbstractFingerprint):
    visitor_id: models.CharField = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.visitor_id

    class Meta(AbstractFingerprint.Meta):  # noqa: D106
        indexes = [
            *AbstractFingerprint.Meta.indexes,
            models.Index(fields=["visitor_id", "-created"]),
        ]

    def get_value_display(self) -> str:
        return self.visitor_id[:8]


class RequestFingerprint(AbstractFingerprint):
    ip: models.GenericIPAddressField = models.GenericIPAddressField(blank=True, null=True)
    user_agent: models.CharField = TruncatedCharField(max_length=255, blank=True)
    accept: models.CharField = TruncatedCharField(max_length=255, blank=True)
    content_encoding: models.CharField = TruncatedCharField(max_length=255, blank=True)
    content_language: models.CharField = TruncatedCharField(max_length=255, blank=True)
    referer: models.CharField = TruncatedCharField(max_length=2047, blank=True)
    cf_ipcountry: models.CharField = TruncatedCharField(max_length=16, blank=True)

    def __str__(self):
        return f"{self.ip} {self.user_agent}"

    class Meta(AbstractFingerprint.Meta):  # noqa: D106
        indexes = [
            *AbstractFingerprint.Meta.indexes,
            models.Index(fields=["ip", "-created"]),
            models.Index(fields=["user_agent", "-created"]),
        ]

    def get_value_display(self) -> str:
        return self.user_agent[:24] + "..."

    def is_unique(self) -> bool:
        return (
            not self.__class__.objects.filter(
                url_id=self.url_id,
                user_session_id=self.user_session_id,
            )
            .exclude(pk=self.pk)
            .exists()
        )

    @classmethod
    def get_count_for_urls(cls, urls: list[str]) -> Counter[str]:
        existing_urls = dict(Url.objects.filter(value__in=urls).values_list("id", "value"))
        ids_and_hits = RequestHitCount.objects.filter(url_id__in=existing_urls).values_list("url_id", "hits")
        counter = Counter({existing_urls[id_]: hits for id_, hits in ids_and_hits})
        max_length = Url._meta.get_field("value").max_length
        counter.update({url: counter[url[:max_length]] for url in urls if len(url) > max_length})
        return counter

    @classmethod
    def get_count_for_objects(
        cls, request: HttpRequest, objects: list[SupportsGetAbsoluteUrl]
    ) -> Counter[SupportsGetAbsoluteUrl]:
        url_to_object = {request.build_absolute_uri(obj.get_absolute_url()): obj for obj in objects}
        counter = cls.get_count_for_urls(set(url_to_object.keys()))
        return Counter({obj: counter[url] for url, obj in url_to_object.items()})


class UserFingerprint(get_user_model()):  # type: ignore
    """Proxy model for admin site, since django doesn't allow to register two admins for the same model."""

    class Meta:  # noqa: D106
        proxy = True
