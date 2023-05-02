from fingerprint.models import RequestFingerprint, BrowserFingerprint, UserSession
from django.utils.timezone import now
from datetime import timedelta


def test__request__anonymous(client, db):
    assert not RequestFingerprint.objects.exists()
    assert not BrowserFingerprint.objects.exists()

    response = client.get('/request-test')
    assert response.status_code == 200

    assert not BrowserFingerprint.objects.exists()

    assert RequestFingerprint.objects.count() == 1
    fingerprint = RequestFingerprint.objects.first()

    assert fingerprint.ip == '127.0.0.1'
    assert fingerprint.user_agent == ''
    assert now() - timedelta(seconds=5) <= fingerprint.created < now()
    assert fingerprint.session_key

    assert not UserSession.objects.exists()


def test__request__user_session__not_creation(user, user_client, db):
    UserSession.objects.all().delete()

    response = user_client.get('/request-test')
    assert response.status_code == 200

    assert not UserSession.objects.exists()


def test__request__user_session__creation(user, user_client, db):
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

    assert not UserSession.objects.exists()


def test__builtin_view__logged_in(user_client, db):
    assert not RequestFingerprint.objects.exists()
    UserSession.objects.all().delete()

    response = user_client.get('/_/')
    assert response.status_code == 200
    assert RequestFingerprint.objects.count() == 1

    assert UserSession.objects.count() == 1


def test__browser__post_request(client, db):
    assert not RequestFingerprint.objects.exists()
    assert not BrowserFingerprint.objects.exists()

    response = client.post('/_/', {'id': '12345'})
    assert response.status_code == 200

    assert not RequestFingerprint.objects.exists()
    assert BrowserFingerprint.objects.count() == 1
    fingerprint = BrowserFingerprint.objects.first()

    assert fingerprint.visitor_id == '12345'
    assert now() - timedelta(seconds=5) <= fingerprint.created < now()


def test__user_session__auto_creation(db, client, user):
    assert not UserSession.objects.exists()

    client.force_login(user)
    assert UserSession.objects.count() == 1
    user_session = UserSession.objects.first()
    assert user_session.user == user
