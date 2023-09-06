from fingerprint.models import RequestFingerprint, BrowserFingerprint, UserSession
from django.utils.timezone import now
from datetime import timedelta


def test__request__anonymous(client, db):
    assert not RequestFingerprint.objects.exists()
    assert not BrowserFingerprint.objects.exists()

    response = client.get('/request-test')
    assert response.status_code == 200

    assert UserSession.objects.exists()
    user_session = UserSession.objects.first()
    assert not user_session.user

    assert not BrowserFingerprint.objects.exists()

    assert RequestFingerprint.objects.count() == 1
    fingerprint = RequestFingerprint.objects.first()
    assert fingerprint.ip == '127.0.0.1'
    assert fingerprint.user_agent == ''
    assert now() - timedelta(seconds=5) <= fingerprint.created < now()
    assert fingerprint.user_session == user_session
    assert fingerprint.url.value == 'http://testserver/request-test'


def test__request__user_session__user_not_capture(client, db):
    UserSession.objects.all().delete()

    response = client.get('/session-test')
    assert response.status_code == 200

    assert not UserSession.objects.exists()


def test__request__user_session__user_capture(user, user_client, db):
    UserSession.objects.all().delete()

    response = user_client.get('/session-test')
    assert response.status_code == 200

    assert UserSession.objects.count() == 1
    user_session = UserSession.objects.first()
    assert user_session.user == user


def test__builtin_view__anonymous(client, db):
    assert not RequestFingerprint.objects.exists()
    UserSession.objects.all().delete()

    response = client.get('/_/')
    assert response.status_code == 200
    assert RequestFingerprint.objects.count() == 1

    assert UserSession.objects.exists()
    user_session = UserSession.objects.first()
    assert not user_session.user


def test__builtin_view__logged_in(user, user_client, db):
    assert not RequestFingerprint.objects.exists()
    UserSession.objects.all().delete()

    response = user_client.get('/_/')
    assert response.status_code == 200
    assert RequestFingerprint.objects.count() == 1

    assert UserSession.objects.count() == 1
    user_session = UserSession.objects.first()
    assert user_session.user == user


def test__browser__post_request(client, db):
    assert not RequestFingerprint.objects.exists()
    assert not BrowserFingerprint.objects.exists()

    response = client.post('/_/', {'id': '12345'}, **{'HTTP_REFERER': 'http://localhost/somepath'})
    assert response.status_code == 200

    assert not RequestFingerprint.objects.exists()
    assert BrowserFingerprint.objects.count() == 1
    fingerprint = BrowserFingerprint.objects.first()

    assert fingerprint.visitor_id == '12345'
    assert now() - timedelta(seconds=5) <= fingerprint.created < now()
    assert fingerprint.url.value == 'http://localhost/somepath'


def test__user_session__auto_creation(db, client, user):
    assert not UserSession.objects.exists()

    client.force_login(user)
    assert UserSession.objects.count() == 1
    user_session = UserSession.objects.first()
    assert user_session.user == user
