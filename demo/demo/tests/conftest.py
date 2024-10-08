import pytest
from cacheops import invalidate_all
from django.contrib.auth import get_user_model
from django.test import Client


@pytest.fixture
def user(db):
    return get_user_model().objects.create(
        username="test",
    )


@pytest.fixture
def user_client(client, user) -> Client:
    client.force_login(user)
    return client


@pytest.fixture
def nocache(settings) -> None:
    settings.CACHEOPS_ENABLED = False


@pytest.fixture(autouse=True)
def clear_cache():
    yield
    invalidate_all()
