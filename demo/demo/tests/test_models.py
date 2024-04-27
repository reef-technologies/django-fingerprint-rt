from collections import Counter
from fingerprint.models import RequestFingerprint


def test__models__get_count_for_urls__logic(db, client, user):
    url1 = '/request-test'
    url2 = '/request-test?param=1'

    absolute_url1 = f'http://testserver{url1}'
    absolute_url2 = f'http://testserver{url2}'

    assert RequestFingerprint.get_count_for_urls([]) == Counter()
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter()

    client.get(url1)
    assert RequestFingerprint.get_count_for_urls([]) == Counter()
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 1})

    client.get(url2)
    assert RequestFingerprint.get_count_for_urls([]) == Counter()
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 1})
    assert RequestFingerprint.get_count_for_urls([absolute_url1, absolute_url2]) == Counter({absolute_url1: 1, absolute_url2: 1})

    for _ in range(10):
        client.get(url1)
        assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 1})

    client.force_login(user)

    for _ in range(5):
        client.get(url1)
        assert RequestFingerprint.get_count_for_urls([absolute_url1, absolute_url2]) == Counter({absolute_url1: 2, absolute_url2: 1})

    client.logout()

    for _ in range(5):
        client.get(url1)
        assert RequestFingerprint.get_count_for_urls([absolute_url1, absolute_url2]) == Counter({absolute_url1: 3, absolute_url2: 1})


def test__models__get_count_for_urls__num_queries(db, client, django_assert_num_queries):
    url1 = '/request-test'
    url2 = '/request-test?param=1'

    absolute_url1 = f'http://testserver{url1}'
    absolute_url2 = f'http://testserver{url2}'

    client.get(url1)
    client.get(url2)

    with django_assert_num_queries(4):
        RequestFingerprint.get_count_for_urls([absolute_url1, absolute_url2])
