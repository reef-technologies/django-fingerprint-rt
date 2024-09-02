from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from fingerprint.views import FingerprintView

from .views import RequestFingerprintTestView, remember_session_test_view

urlpatterns = [
    path("", TemplateView.as_view(template_name="demo/home.html"), name="home"),
    path("admin/", admin.site.urls),
    path("_/", FingerprintView.as_view(), name="fingerprint"),
    path("__debug__/", include("debug_toolbar.urls")),
    path("request-test", RequestFingerprintTestView.as_view()),
    path("session-test", remember_session_test_view),
]
