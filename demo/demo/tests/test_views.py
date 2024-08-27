from datetime import timedelta

from django.utils.timezone import now
from freezegun import freeze_time
from fingerprint.models import BrowserFingerprint, RequestFingerprint, UserSession


def test__request__anonymous(client, db):
    assert not RequestFingerprint.objects.exists()
    assert not BrowserFingerprint.objects.exists()

    response = client.get("/request-test")
    assert response.status_code == 200

    assert UserSession.objects.exists()
    user_session = UserSession.objects.first()
    assert not user_session.user

    assert not BrowserFingerprint.objects.exists()

    assert RequestFingerprint.objects.count() == 1
    fingerprint = RequestFingerprint.objects.first()
    assert fingerprint.ip == "127.0.0.1"
    assert fingerprint.user_agent == ""
    assert now() - timedelta(seconds=5) <= fingerprint.created < now()
    assert fingerprint.user_session == user_session
    assert fingerprint.url.value == "http://testserver/request-test"


def test__request__user_session__user_not_capture(client, db):
    UserSession.objects.all().delete()

    response = client.get("/session-test")
    assert response.status_code == 200

    assert not UserSession.objects.exists()


def test__request_fingerprint__header_fields(client, db):
    headers = {
        "HTTP_USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",  # noqa: E501
        "HTTP_ACCEPT": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "HTTP_CONTENT_ENCODING": "gzip, deflate, br",
        "HTTP_CONTENT_LANGUAGE": "en-US",
        "HTTP_REFERER": "http://localhost/somepath",
        "HTTP_CF_IPCOUNTRY": "US",
    }

    response = client.get("/request-test", **headers)
    assert response.status_code == 200

    fingerprint = RequestFingerprint.objects.get()

    assert fingerprint.user_agent == headers["HTTP_USER_AGENT"]
    assert fingerprint.accept == headers["HTTP_ACCEPT"]
    assert fingerprint.content_encoding == headers["HTTP_CONTENT_ENCODING"]
    assert fingerprint.content_language == headers["HTTP_CONTENT_LANGUAGE"]
    assert fingerprint.referer == headers["HTTP_REFERER"]
    assert fingerprint.cf_ipcountry == headers["HTTP_CF_IPCOUNTRY"]


def test__request__fingerprint__header_fields_overflow(client, db):
    headers = {
        "HTTP_USER_AGENT": "a" * 300,
        "HTTP_ACCEPT": "b" * 300,
        "HTTP_CONTENT_ENCODING": "c" * 300,
        "HTTP_CONTENT_LANGUAGE": "d" * 300,
        "HTTP_REFERER": "e" * 2050,
        "HTTP_CF_IPCOUNTRY": "f" * 300,
    }

    response = client.get("/request-test", **headers)
    assert response.status_code == 200

    fingerprint = RequestFingerprint.objects.get()

    assert fingerprint.user_agent == headers["HTTP_USER_AGENT"][:255]
    assert fingerprint.accept == headers["HTTP_ACCEPT"][:255]
    assert fingerprint.content_encoding == headers["HTTP_CONTENT_ENCODING"][:255]
    assert fingerprint.content_language == headers["HTTP_CONTENT_LANGUAGE"][:255]
    assert fingerprint.referer == headers["HTTP_REFERER"][:2047]
    assert fingerprint.cf_ipcountry == headers["HTTP_CF_IPCOUNTRY"][:16]


def test__request__user_session__user_capture(user, user_client, db):
    UserSession.objects.all().delete()

    response = user_client.get("/session-test")
    assert response.status_code == 200

    assert UserSession.objects.count() == 1
    user_session = UserSession.objects.first()
    assert user_session.user == user


def test__builtin_view__anonymous(client, db):
    assert not RequestFingerprint.objects.exists()
    UserSession.objects.all().delete()

    response = client.get("/_/")
    assert response.status_code == 200
    assert RequestFingerprint.objects.count() == 1

    assert UserSession.objects.exists()
    user_session = UserSession.objects.first()
    assert not user_session.user


def test__builtin_view__logged_in(user, user_client, db):
    assert not RequestFingerprint.objects.exists()
    UserSession.objects.all().delete()

    response = user_client.get("/_/")
    assert response.status_code == 200
    assert RequestFingerprint.objects.count() == 1

    assert UserSession.objects.count() == 1
    user_session = UserSession.objects.first()
    assert user_session.user == user


def test__browser__post_request(client, db):
    assert not RequestFingerprint.objects.exists()
    assert not BrowserFingerprint.objects.exists()

    response = client.post("/_/", {"id": "12345"}, **{"HTTP_REFERER": "http://localhost/somepath"})
    assert response.status_code == 200

    assert not RequestFingerprint.objects.exists()
    assert BrowserFingerprint.objects.count() == 1
    fingerprint = BrowserFingerprint.objects.first()

    assert fingerprint.visitor_id == "12345"
    assert now() - timedelta(seconds=5) <= fingerprint.created < now()
    assert fingerprint.url.value == "http://localhost/somepath"


def test__user_session__auto_creation(db, client, user):
    assert not UserSession.objects.exists()

    client.force_login(user)
    assert UserSession.objects.count() == 1
    user_session = UserSession.objects.first()
    assert user_session.user == user


def test__request_fingerprint__debounce(db, user_client, settings):
    settings.FINGERPRINT_DEBOUNCE_PERIOD = timedelta(minutes=10)

    assert not RequestFingerprint.objects.exists()

    assert user_client.get("/request-test").status_code == 200
    assert RequestFingerprint.objects.count() == 1

    assert user_client.get("/request-test").status_code == 200
    assert RequestFingerprint.objects.count() == 1

    with freeze_time(now() + timedelta(minutes=11)):
        assert user_client.get("/request-test").status_code == 200
        assert RequestFingerprint.objects.count() == 2

        assert user_client.get("/request-test").status_code == 200
        assert RequestFingerprint.objects.count() == 2

    with freeze_time(now() + timedelta(minutes=20)):
        assert user_client.get("/request-test").status_code == 200
        assert RequestFingerprint.objects.count() == 2

    with freeze_time(now() + timedelta(minutes=21)):
        assert user_client.get("/request-test").status_code == 200
        assert RequestFingerprint.objects.count() == 3

        assert user_client.get("/request-test").status_code == 200
        assert RequestFingerprint.objects.count() == 3
