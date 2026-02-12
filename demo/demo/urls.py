from django.contrib import admin
from django.urls import include, path

from fingerprint.views import FingerprintView

from .views import HomeView, remember_session_test_view, request_fingerprint_test_view

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("admin/", admin.site.urls),
    path("_/", FingerprintView.as_view(), name="fingerprint"),
    path("__debug__/", include("debug_toolbar.urls")),
    path("request-test", request_fingerprint_test_view),
    path("session-test", remember_session_test_view),
]
