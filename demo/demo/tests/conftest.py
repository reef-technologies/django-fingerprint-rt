import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.core.cache import caches


@pytest.fixture
def user(db):
    return get_user_model().objects.create(
        username='test',
    )


@pytest.fixture
def user_client(client, user) -> Client:
    client.force_login(user)
    return client


@pytest.fixture(autouse=True)
def clear_cache(settings):
    yield

    for cache in settings.CACHES.keys():
        caches[cache].clear()
