from collections import Counter

from fingerprint.models import RequestFingerprint


def test__utils__get_num_sessions(db, client, user):
    url1 = "/request-test"
    url2 = "/request-test?param=1"

    absolute_url1 = f"http://testserver{url1}"
    absolute_url2 = f"http://testserver{url2}"

    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter()
    assert RequestFingerprint.get_count_for_urls([absolute_url2]) == Counter()

    response = client.get(url1)
    assert response.status_code == 200, response.content
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 1})
    assert RequestFingerprint.get_count_for_urls([absolute_url2]) == Counter()

    assert client.get(url1)
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 1})
    assert RequestFingerprint.get_count_for_urls([absolute_url2]) == Counter()

    client.get(url2)
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 1})
    assert RequestFingerprint.get_count_for_urls([absolute_url2]) == Counter({absolute_url2: 1})

    client.force_login(user)

    client.get(url2)
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 1})
    assert RequestFingerprint.get_count_for_urls([absolute_url2]) == Counter({absolute_url2: 2})

    client.get(url2)
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 1})
    assert RequestFingerprint.get_count_for_urls([absolute_url2]) == Counter({absolute_url2: 2})

    client.get(url1)
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 2})
    assert RequestFingerprint.get_count_for_urls([absolute_url2]) == Counter({absolute_url2: 2})

    client.logout()

    client.get(url1)
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 3})
    assert RequestFingerprint.get_count_for_urls([absolute_url2]) == Counter({absolute_url2: 2})

    client.get(url1)
    assert RequestFingerprint.get_count_for_urls([absolute_url1]) == Counter({absolute_url1: 3})
    assert RequestFingerprint.get_count_for_urls([absolute_url2]) == Counter({absolute_url2: 2})
