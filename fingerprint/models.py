from typing import Optional

from django.conf import settings
from django.contrib.sessions.models import Session
from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model


class UserSession(models.Model):
    # by default, django stores session data in database; however, we cannot rely on it,
    # since other session backends may be used, plus django doesn't store user-session
    # mapping, so we need to have additional table for that

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True, related_name='sessions')
    session_key = models.CharField(max_length=40)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.session_key

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['session_key', 'user'], name='unique_user_session'),
        ]
        indexes = [
            models.Index(fields=['user', '-created']),
        ]

    def get_value_display(self) -> str:
        return self.session_key[:8]


@receiver(post_save, sender=Session)
def connect_user_to_session(sender, instance, created, **kwargs):
    if user_id := instance.get_decoded().get('_auth_user_id'):
        UserSession.objects.update_or_create(
            session_key=instance.session_key,
            defaults=dict(user_id=user_id),
        )


class AbstractFingerprint(models.Model):
    user_session = models.ForeignKey(UserSession, on_delete=models.CASCADE, related_name='%(model_name)ss')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['user_session', '-created']),
        ]

    @property
    def user(self) -> Optional[AbstractBaseUser]:
        return self.user_session.user


class BrowserFingerprint(AbstractFingerprint):
    visitor_id = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.visitor_id

    class Meta(AbstractFingerprint.Meta):
        indexes = [
            *AbstractFingerprint.Meta.indexes,
            models.Index(fields=['visitor_id', '-created']),
        ]

    def get_value_display(self) -> str:
        return self.visitor_id[:8]


class RequestFingerprint(AbstractFingerprint):
    ip = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True)
    accept = models.CharField(max_length=255, blank=True)
    content_encoding = models.CharField(max_length=255, blank=True)
    content_language = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'{self.ip} {self.user_agent}'

    class Meta(AbstractFingerprint.Meta):
        indexes = [
            *AbstractFingerprint.Meta.indexes,
            models.Index(fields=['ip', '-created']),
            models.Index(fields=['user_agent', '-created']),
        ]

    def get_value_display(self) -> str:
        return self.user_agent[:24] + '...'


class UserFingerprint(get_user_model()):
    """ This is just a proxy model for admin site, since django doesn't allow to register two admins for the same model. """
    class Meta:
        proxy = True
