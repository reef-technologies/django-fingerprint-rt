# django-fingerprint-rt
&nbsp;[![Continuous Integration](https://github.com/reef-technologies/django-fingerprint-rt/workflows/Continuous%20Integration/badge.svg)](https://github.com/reef-technologies/django-fingerprint-rt/actions?query=workflow%3A%22Continuous+Integration%22)&nbsp;[![License](https://img.shields.io/pypi/l/django-fingerprint-rt.svg?label=License)](https://pypi.python.org/pypi/django-fingerprint-rt)&nbsp;[![python versions](https://img.shields.io/pypi/pyversions/django-fingerprint-rt.svg?label=python%20versions)](https://pypi.python.org/pypi/django-fingerprint-rt)&nbsp;[![PyPI version](https://img.shields.io/pypi/v/django-fingerprint-rt.svg?label=PyPI%20version)](https://pypi.python.org/pypi/django-fingerprint-rt)

When you need to know your users a bit better.

This app includes browser (== frontend) and request (== backend) fingerprinting of users.

This may be helpful for better understanding users of the application, for example by knowing which and how many devices they use, where are they from etc.

![Screenshot_2023-05-02_16-02-02](https://user-images.githubusercontent.com/73276794/235674052-5c5150be-e1c3-4a85-9646-244c939db0fb.jpg)



## Usage

> [!IMPORTANT]
> This package uses [ApiVer](#versioning), make sure to import `fingerprint.v1`.

Add `fingerprint` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'fingerprint',
]
```

## All-in-one setup via redirect url

A special redirect page is provided. It is needed to accept internal POST requests from javascript code, but it also has a nice feature: if user visits this page, the page will capture user's fingerprint and then redirect him to next location. In order to host this page, add it to your `urls.py` (for this example we use path `/redirect/`):

```python
urlpatterns = [
    # ...
    path('redirect/', FingerprintView.as_view(), name='fingerprint'),
]
```

Now you can make users visit any page through this redirect:

```html
<a href="{% url 'home' %}">Go to home page directly (without fingerprinting)</a>
{% url 'home' as next %}
<a href="{% url 'fingerprint' %}?next={{ next | urlencode }}">Go to home page through fingerprinting</a>
```


When user visits this fingerprinting page
1) his GET request is fingerprinted and recorder to the database
2) his browser runs a javascript code which fingreprints the browser and sends fingerprint via POST request to this page; if everything succeeds, user is redirected immediately to url from `next` query parameter
3) even if javascript code was blocked or didn't complete in time, the page contains redirect tag, so within few seconds user will be redirected to url from `next` query parameter

> Please remember that database record will be created each time user visits this page, so it can produce a significant load on the database if misused. Same applies to other methods described below.

## Browser fingerprinting

Browser fingerprinting may be triggered by including javascript code in any page:

```html
...
<body>
    ...
    {% include "fingerprint/include/script.html" %}
</body>
```

This will make a browser fingerprint and send it to fingerprinting endpoint (described in previous step) via POST request.

> Please note that user can always disable javascript or block certain scripts, plus browser fingerprinting is not 100% accurate; thus browser fingerprinting should not be considered as reliable.

This method uses FingerprintJS library developed by FingerprintJS, Inc.

## Request fingerprinting

Request fingerprinting may be enabled separately for every view. It's not seen by user in any way and is hard to bypass, so it should be considered as primary fingerprinting method.

In order to enable it for some view:

```python
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from src.fingerprint.views import fingerprint

@fingerprint
def my_view(request):
    # ...


@method_decorator(fingerprint, name='dispatch')
class MyClassBasedView(TemplateView):
    # ...
```

# Matching session to user

Django doesn't store connection between Session and corresponding User, and fingerprinting app uses sessions under the hood. In order to match fingerprint to a user, there is a model `fingerprint.models.UserSession`. To get all session keys for user, perform this query:

```python
user.sessions.values_list('session_key', flat=True)
```

By default, Django stores sessions in your database. Fingerprinting app has a signal, so when a session is created, it's immediately associated with a user, so no need for manual actions here. However, **if non-database session backend is used**, then the signal is not emitted and user-session record is not created. To fix this, you should decorate some view with `@remember_user_session` decorator like this:

```python
@remember_user_session
@fingerprint
def my_view(request):
    # ...
```

This decorator will remember that current session key is associated with current user.

# Hit counts

As a side effect, views which are decorated with `@fingerprint` decorator will have statistics about how many times they were visited by unique users (unique sessions, to be precise - so if user logs out and logs in, it's a new session).

This may be used to show "hit count" for any particular page. Please note that in current implementation urls are counted as absolute url with query parameters, like this: `https://example.com/?param1=value1&param2=value2`. This means that if you have two urls which result in the same page, they will be counted separately. All these are different urls:
* `https://example.com/?param1=value1&param2=value2`
* `https://example.com/?param1=value1`
* `http://example.com/?param1=value1&param2=value2`
* `https://example.com/`
* `https://example.com`
* `http://example.com/`
* `http://example.com`


## Usage

There is a helper template tag which will show hit count for any url: `hit_count`. Again, it accepts absolute url, so the template could look like this:

```html
{% load hit_count %}

{% hit_count request.build_absolute_uri %} views registered for this page
```

One downside of this approach is that it will make a database query for each invocation.
So this tag is handy for `DetailView` where only one object is present, but for bulk views (like `ListView`),
it is recommended to use `get_count_for_urls` or `get_count_for_objects` class methods.

Following will return a `collections.Counter` object with number of hits for each url, making a single database query:
```python
RequestFingerprint.get_count_for_urls([absolute_url1, absolute_url2])
# Counter({absolute_url1: 1, absolute_url2: 4})
```

If model has a properly defined `get_absolute_url` method, then following will return a `collections.Counter` object with number of hits for each object, making a single database query:
```python
RequestFingerprint.get_count_for_objects(request, [instance1, instance2])
# Counter({instance1_url: 1, instance2_url: 4})
```

So in a `ListView` one could add hit count to all objects like this:
```python
class MyView(ListView):
    # ...
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        hit_counts = RequestFingerprint.get_count_for_objects(self.request, context['object_list'])
        for obj, count in hit_counts.items():
            obj.hit_count = count

        return context
```

# URL caching

In order to reduce database load, there is a caching mechanism for URL model. It's enabled be default and will use Django's **default** cache backend. To use a custom cache backend, add this to your settings:

```python
FINGERPRINT_CACHE = 'memcached'  # this has to be a valid key from settings.CACHES
```

To disable caching, set this to `None`:

```python 
FINGERPRINT_CACHE = None
```

# Included licenses

```
Copyright (c) 2023 FingerprintJS, Inc

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```


## Versioning

This package uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
TL;DR you are safe to use [compatible release version specifier](https://packaging.python.org/en/latest/specifications/version-specifiers/#compatible-release) `~=MAJOR.MINOR` in your `pyproject.toml` or `requirements.txt`.

Additionally, this package uses [ApiVer](https://www.youtube.com/watch?v=FgcoAKchPjk) to further reduce the risk of breaking changes.
This means, the public API of this package is explicitly versioned, e.g. `fingerprint.v1`, and will not change in a backwards-incompatible way even when `fingerprint.v2` is released.

Internal packages, i.e. prefixed by `fingerprint._` do not share these guarantees and may change in a backwards-incompatible way at any time even in patch releases.


## Development


Pre-requisites:
- [pdm](https://pdm.fming.dev/)
- [nox](https://nox.thea.codes/en/stable/)
- [docker](https://www.docker.com/) and [docker compose plugin](https://docs.docker.com/compose/)


Ideally, you should run `nox -t format lint` before every commit to ensure that the code is properly formatted and linted.
Before submitting a PR, make sure that tests pass as well, you can do so using:
```
nox -t check # equivalent to `nox -t format lint test`
```

If you wish to install dependencies into `.venv` so your IDE can pick them up, you can do so using:
```
pdm install --dev
```

### Release process

Run `nox -s make_release -- X.Y.Z` where `X.Y.Z` is the version you're releasing and follow the printed instructions.
