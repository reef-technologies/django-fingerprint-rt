from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from functools import wraps
from itertools import chain, islice
from typing import Callable

from django.contrib import admin
from django.db.models import Count, Max, Prefetch, Q
from django.urls import reverse
from django.utils.html import format_html
from django.utils.timezone import now

from .models import BrowserFingerprint, RequestFingerprint, UserFingerprint, UserSession

try:
    from itertools import pairwise
except ImportError:

    def pairwise(items):  # type: ignore
        return zip(items, items[1:])


class html_objects_list:
    def __init__(self, format_string: str, max_items: int = 10):
        self.format_string = format_string
        self.max_items = max_items

    def __call__(self, fn: Callable) -> Callable:
        @wraps(fn)
        def wrapped(*args, **kwargs):
            results = list(islice(fn(*args, **kwargs), self.max_items))
            return format_html("<br>".join(self.format_string for _ in results), *chain.from_iterable(results))

        return wrapped


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = (
        "session_key",
        "user",
        "browser_fingerprints",
        "request_fingerprints",
        "created",
    )
    list_filter = ("created",)
    search_fields = (
        "user__username",
        "session_key",
    )
    ordering = ("-created",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related(
                Prefetch(
                    "browserfingerprints",
                    queryset=BrowserFingerprint.objects.order_by("visitor_id", "-created").distinct("visitor_id"),
                ),
                Prefetch(
                    "requestfingerprints",
                    queryset=RequestFingerprint.objects.order_by("user_session", "user_agent", "-created").distinct(
                        "user_session", "user_agent"
                    ),
                ),
            )
        )

    @html_objects_list('{} &nbsp;&nbsp; <a href="{}"><code>{}</code></a>')
    def browser_fingerprints(self, instance) -> Iterator[tuple]:
        for fingerprint in instance.browserfingerprints.all():
            yield (
                fingerprint.created.date(),
                reverse("admin:fingerprint_browserfingerprint_changelist") + f"?user_session={instance.id}",
                fingerprint.get_value_display(),
            )

    @html_objects_list('{} &nbsp;&nbsp; <a href="{}"><code>{}</code></a>')
    def request_fingerprints(self, instance) -> Iterator[tuple]:
        for fingerprint in instance.requestfingerprints.all():
            yield (
                fingerprint.created.date(),
                reverse("admin:fingerprint_requestfingerprint_changelist") + f"?user_session={instance.id}",
                fingerprint.get_value_display(),
            )


class FingerprintBaseAdmin(admin.ModelAdmin):
    list_display: tuple[str, ...] = (
        "id",
        "user_session",
        "get_user",
    )
    list_filter: tuple[str, ...] = ("created",)
    ordering: tuple[str, ...] = ("-created",)
    search_fields: tuple[str, ...] = (
        "user_session__session_key",
        "user_session__user__email",
        "user_session__user__username",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user_session__user")

    @admin.display(description="user")
    def get_user(self, instance):
        return instance.user_session.user


@admin.register(BrowserFingerprint)
class BrowserFingerprintAdmin(FingerprintBaseAdmin):
    list_display = (
        *FingerprintBaseAdmin.list_display,
        "visitor_id",
        "created",
    )
    search_fields = (
        "visitor_id",
        *FingerprintBaseAdmin.search_fields,
    )


@admin.register(RequestFingerprint)
class RequestFingerprintAdmin(FingerprintBaseAdmin):
    list_display = (
        *FingerprintBaseAdmin.list_display,
        "ip",
        "user_agent",
        "created",
    )

    search_fields = (
        "ip",
        "user_agent",
        "accept",
        "content_encoding",
        "content_language",
        *FingerprintBaseAdmin.search_fields,
    )


class NumFingerprintsListFilter(admin.SimpleListFilter):
    groups = list(pairwise((1, 4, 6, 11, 21, 10_001)))
    query_parameter: str

    def lookups(self, request, model_admin):
        return [(i, f"{min_}-{max_-1}") for i, (min_, max_) in enumerate(self.groups)]

    def queryset(self, request, queryset):
        if not (value := self.value()):
            return

        try:
            min_, max_ = self.groups[int(value)]
        except (KeyError, ValueError):
            return

        return queryset.filter(
            **{
                f"{self.query_parameter}__gte": min_,
                f"{self.query_parameter}__lt": max_,
            }
        )


class NumBrowserFingerprintsListFilter(NumFingerprintsListFilter):
    title = "unique browser fingerprints"
    parameter_name = "num_browser_fingerprints_group"
    query_parameter = "num_browser_fingerprints"


class NumRequestFingerprintsListFilter(NumFingerprintsListFilter):
    title = "unique request fingerprints"
    parameter_name = "num_request_fingerprints_group"
    query_parameter = "num_request_fingerprints"


class LastFingerprintCreatedListFilter(admin.SimpleListFilter):
    title = "last fingerprint capture"
    parameter_name = "fingerprint_captured_days"

    def lookups(self, request, model_admin):
        return [
            (1, "1 day"),
            (7, "1 week"),
            (30, "1 month"),
            (90, "3 months"),
            (365, "12 months"),
        ]

    def queryset(self, request, queryset):
        if not (value := self.value()):
            return

        try:
            days = timedelta(days=int(value))
        except ValueError:
            return

        since = now() - days
        return queryset.annotate(
            last_browser_fingerprint=Max("sessions__browserfingerprints__created"),
            last_request_fingerprint=Max("sessions__requestfingerprints__created"),
        ).filter(Q(last_browser_fingerprint__gte=since) | Q(last_request_fingerprint__gte=since))


@admin.register(UserFingerprint)
class UserFingerprintAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "sessions",
        "num_browser_fingerprints",
        "browser_fingerprints",
        "num_request_fingerprints",
        "request_fingerprints",
    )
    list_filter = (
        LastFingerprintCreatedListFilter,
        NumBrowserFingerprintsListFilter,
        NumRequestFingerprintsListFilter,
    )
    search_fields = (
        "username",
        "email",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                Prefetch("sessions", queryset=UserSession.objects.all().order_by("-created")),
                Prefetch(
                    "sessions__browserfingerprints",
                    queryset=BrowserFingerprint.objects.order_by("visitor_id", "-created").distinct("visitor_id"),
                ),
                Prefetch(
                    "sessions__requestfingerprints",
                    queryset=RequestFingerprint.objects.order_by("user_session", "user_agent", "-created").distinct(
                        "user_session", "user_agent"
                    ),
                ),
            )
            .annotate(
                num_browser_fingerprints=Count("sessions__browserfingerprints__visitor_id", distinct=True),
                num_request_fingerprints=Count("sessions__requestfingerprints__user_agent", distinct=True),
            )
        )

    @admin.display(description="#")
    def num_browser_fingerprints(self, instance):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:fingerprint_browserfingerprint_changelist") + f"?q={instance.email}",
            instance.num_browser_fingerprints,
        )

    @admin.display(description="#")
    def num_request_fingerprints(self, instance):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:fingerprint_requestfingerprint_changelist") + f"?q={instance.email}",
            instance.num_request_fingerprints,
        )

    @admin.display(description="last sessions")
    @html_objects_list('{} &nbsp;&nbsp; <a href="{}"><code>{}</code></a>')
    def sessions(self, instance) -> Iterator[tuple]:
        for session in instance.sessions.all():
            yield (
                session.created.date(),
                reverse("admin:fingerprint_usersession_changelist") + f"?id={instance.id}",
                session.get_value_display(),
            )

    @admin.display(description="last browsers")
    @html_objects_list('{} &nbsp;&nbsp; <a href="{}"><code>{}</code></a>')
    def browser_fingerprints(self, instance) -> Iterator[tuple]:
        for session in instance.sessions.all():
            for fingerprint in session.browserfingerprints.all():
                yield (
                    fingerprint.created.date(),
                    reverse("admin:fingerprint_browserfingerprint_changelist") + f"?id={fingerprint.id}",
                    fingerprint.get_value_display(),
                )

    @admin.display(description="last requests")
    @html_objects_list('{} &nbsp;&nbsp; <a href="{}"><code>{}</code></a>')
    def request_fingerprints(self, instance) -> Iterator[tuple]:
        for session in instance.sessions.all():
            for fingerprint in session.requestfingerprints.all():
                yield (
                    fingerprint.created.date(),
                    reverse("admin:fingerprint_requestfingerprint_changelist") + f"?id={fingerprint.id}",
                    fingerprint.get_value_display(),
                )
