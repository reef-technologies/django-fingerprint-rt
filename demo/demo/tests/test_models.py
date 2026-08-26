from collections import Counter
from datetime import timedelta
from unittest.mock import Mock

from django.core.management import call_command
from django.db import IntegrityError
from django.utils.timezone import now
from freezegun import freeze_time

from fingerprint.models import RequestFingerprint, RequestHitCount, Url, UserSession


def test__models__get_count_for_urls__logic(db, client, user):
    url1 = "/request-test"
    url2 = "/request-test?param=1"

    absolute_url1 = f"http://testserver{url1}"
    absolute_url2 = f"http://testserver{url2}"

    assert RequestFingerprint.get_count_for_urls([]) == Counter()
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter()

    client.get(url1)
    assert RequestFingerprint.get_count_for_urls([]) == Counter()
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 1})

    client.get(url2)
    assert RequestFingerprint.get_count_for_urls([]) == Counter()
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 1})
    assert RequestFingerprint.get_count_for_urls([absolute_url1, absolute_url2]) == Counter(
        {absolute_url1: 1, absolute_url2: 1}
    )

    for _ in range(10):
        client.get(url1)
        assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 1})

    client.force_login(user)

    for _ in range(5):
        client.get(url1)
        assert RequestFingerprint.get_count_for_urls([absolute_url1, absolute_url2]) == Counter(
            {absolute_url1: 2, absolute_url2: 1}
        )

    client.logout()

    for _ in range(5):
        client.get(url1)
        assert RequestFingerprint.get_count_for_urls([absolute_url1, absolute_url2]) == Counter(
            {absolute_url1: 3, absolute_url2: 1}
        )


def test__models__get_count_for_urls__num_queries(db, client, django_assert_num_queries):
    url1 = "/request-test"
    url2 = "/request-test?param=1"

    absolute_url1 = f"http://testserver{url1}"
    absolute_url2 = f"http://testserver{url2}"

    client.get(url1)
    client.get(url2)

    with django_assert_num_queries(2):
        RequestFingerprint.get_count_for_urls([absolute_url1, absolute_url2])


def test__models__set_hits(db):
    url = Url.objects.create(value="http://testserver/set-hits")
    RequestHitCount.set(url, 42)
    assert RequestFingerprint.get_count_for_urls([url.value]) == Counter({url.value: 42})
    RequestHitCount.set(url, 7)
    assert RequestFingerprint.get_count_for_urls([url.value]) == Counter({url.value: 7})


def test__models__inc(db):
    url = Url.objects.create(value="http://testserver/inc")
    RequestHitCount.inc(url)
    assert RequestFingerprint.get_count_for_urls([url.value]) == Counter({url.value: 1})
    RequestHitCount.inc(url)
    assert RequestFingerprint.get_count_for_urls([url.value]) == Counter({url.value: 2})


def test__models__inc__integrity_error(db, monkeypatch):
    url = Url.objects.create(value="http://testserver/inc-race")

    def create_conflict(**kwargs):
        RequestHitCount(url=url, hits=3).save()
        raise IntegrityError

    monkeypatch.setattr(RequestHitCount.objects, "create", create_conflict)
    RequestHitCount.inc(url)
    assert RequestHitCount.objects.get(url=url).hits == 4


def test__models__is_unique(db):
    url = Url.objects.create(value="http://testserver/fp")
    session = UserSession.objects.create(session_key="sess-1")
    fp = RequestFingerprint.objects.create(url=url, user_session=session)
    assert fp.is_unique()

    duplicate = RequestFingerprint.objects.create(url=url, user_session=session)
    assert not fp.is_unique()
    assert not duplicate.is_unique()

    other_session = UserSession.objects.create(session_key="sess-2")
    assert RequestFingerprint.objects.create(url=url, user_session=other_session).is_unique()

    other_url = Url.objects.create(value="http://testserver/fp-other")
    assert RequestFingerprint.objects.create(url=other_url, user_session=session).is_unique()


def test__models__rebuild_hit_counts(db, client, user):
    url1 = "/request-test"
    url2 = "/request-test?param=1"
    absolute_url1 = f"http://testserver{url1}"
    absolute_url2 = f"http://testserver{url2}"

    client.get(url1)
    client.get(url2)
    client.force_login(user)
    client.get(url1)

    RequestHitCount.set(Url.objects.get(value=absolute_url1), 99)
    stale = Url.objects.create(value="http://testserver/stale")
    RequestHitCount.set(stale, 10)
    RequestHitCount.rebuild_hit_counts(chunk_size=1)
    assert RequestFingerprint.get_count_for_urls([absolute_url1, absolute_url2]) == Counter(
        {absolute_url1: 2, absolute_url2: 1}
    )
    assert not RequestHitCount.objects.filter(url=stale).exists()

    RequestHitCount.rebuild_hit_counts(chunk_size=1)
    assert RequestFingerprint.get_count_for_urls([absolute_url1, absolute_url2]) == Counter(
        {absolute_url1: 2, absolute_url2: 1}
    )


def test__management__rebuild_hit_counts(db, client):
    url = "/request-test"
    absolute_url = f"http://testserver{url}"
    client.get(url)
    RequestHitCount.objects.all().delete()
    call_command("rebuild_hit_counts", chunk_size=1)
    assert RequestFingerprint.get_count_for_urls([absolute_url]) == Counter({absolute_url: 1})


def test__models__hit_count__unique_across_debounce(db, client, settings):
    settings.FINGERPRINT_DEBOUNCE_PERIOD = timedelta(seconds=10)
    url = "/request-test"
    absolute_url = f"http://testserver{url}"

    client.get(url)
    assert RequestFingerprint.get_count_for_urls([absolute_url]) == Counter({absolute_url: 1})

    with freeze_time(now() + timedelta(minutes=1)):
        client.get(url)
        assert RequestFingerprint.objects.filter(url__value=absolute_url).count() == 2
        assert RequestFingerprint.get_count_for_urls([absolute_url]) == Counter({absolute_url: 1})


def test__models__get_count_for_urls__truncated(db):
    max_length = Url._meta.get_field("value").max_length
    long_url = "http://testserver/" + "x" * max_length
    url = Url.objects.create(value=long_url)
    RequestHitCount.set(url, 5)
    assert RequestFingerprint.get_count_for_urls([long_url])[long_url] == 5


def test__models__get_count_for_objects(db, client):
    hit, miss = Mock(), Mock()
    hit.get_absolute_url.return_value = "/request-test"
    miss.get_absolute_url.return_value = "/other"
    response = client.get(hit.get_absolute_url())
    assert RequestFingerprint.get_count_for_objects(response.wsgi_request, [hit, miss]) == Counter({hit: 1, miss: 0})
    assert RequestFingerprint.get_count_for_objects(response.wsgi_request, []) == Counter()
