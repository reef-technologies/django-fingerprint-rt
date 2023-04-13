from typing import Optional

from django.conf import settings
from django.contrib.sessions.models import Session
from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save


class UserSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} - {self.session_key}'

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['session_key', 'user'], name='unique_user_session'),
        ]


@receiver(post_save, sender=Session)
def connect_user_to_session(sender, instance, created, **kwargs):
    if user_id := instance.get_decoded().get('_auth_user_id'):
        UserSession.objects.get_or_create(
            user_id=user_id,
            session_key=instance.session_key,
        )


class AbstractFingerprint(models.Model):
    session_key = models.CharField(max_length=40)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['session_key', '-created']),
        ]

    @property
    def user(self) -> Optional[AbstractBaseUser]:
        session = UserSession.objects.filter(session_key=self.session_key).first()
        if session:
            return session.user


class BrowserFingerprint(AbstractFingerprint):
    visitor_id = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.visitor_id

    class Meta(AbstractFingerprint.Meta):
        indexes = [
            *AbstractFingerprint.Meta.indexes,
            models.Index(fields=['visitor_id', '-created']),
        ]


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
