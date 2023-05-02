from django.contrib import admin

from .models import UserSession, RequestFingerprint, BrowserFingerprint


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = 'session_key', 'user', 'created',
    list_filter = 'created',
    search_fields = 'user__username', 'session_key',
    ordering = '-created',

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


class FingerprintUserMixin(admin.ModelAdmin):
    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        user_sessions = (
            UserSession.objects
            .filter(session_key__in=qs.values_list('session_key', flat=True))
            .select_related('user')
            .only('session_key', 'user')
        )
        self.session_key_to_user = {session.session_key: session.user for session in user_sessions}
        return qs

    def get_user(self, obj):
        return self.session_key_to_user.get(obj.session_key, '')
    get_user.short_description = 'User'


@admin.register(BrowserFingerprint)
class BrowserFingerprintAdmin(FingerprintUserMixin):
    list_display = 'session_key', 'get_user', 'visitor_id', 'created',
    list_filter = 'created',
    search_fields = 'visitor_id', 'session_key',
    ordering = '-created',


@admin.register(RequestFingerprint)
class RequestFingerprintAdmin(FingerprintUserMixin):
    list_display = 'session_key', 'get_user', 'ip', 'user_agent', 'created',
    list_filter = 'created',
    search_fields = 'ip', 'user_agent', 'accept', 'content_encoding', 'content_language', 'session_key',
    ordering = '-created',
