from fingerprint.admin import UserFingerprintAdmin
from django.contrib import admin
from django.contrib.auth import get_user_model


admin.site.unregister(get_user_model())


@admin.register(get_user_model())
class UserAdmin(UserFingerprintAdmin):
    list_display = (
        'pk', 'email', 'date_joined',
        'sessions',
        'num_browser_fingerprints', 'browser_fingerprints',
        'num_request_fingerprints', 'request_fingerprints',
    )
