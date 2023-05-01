# django-fingerprint-rt
When you need to know your users a bit better.

This app uncludes browser (== frontend) and request (== backend) fingerprinting of users.

This may be helpful for better understanding users of the application, for example by knowing which and how many devices they use, where are they from etc.

# Setup

Add `fingerprint` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'fingerprint',
]
```

## All-in-one setup

A special redirect page is provided, which will make user's fingerprint and then redirect him to next location. In order to host it, add it to your `urls.py` (for this example we use path `/redirect/`):

```python
urlpatterns = [
    # ...
    path('redirect/', FingerprintView.as_view(), name='fingerprint'),
]
```

Now you can make users visit any page through this redirect:

```html
<a href="{% url 'home' %}">Go to home page directly (without fingerprinting)</a>
<a href="{% url 'fingerprint' %}?next={% url 'home' %}">Go to home page through fingerprinting</a>
```

> TODO: maybe add `| urlencode` for `next` parameter.

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

This will make a browser fingerprint and send it to fingerprinting endpoint via POST request.

> Please note that user can always disable javascript or block certain scripts, plus browser fingerprinting is not 100% accurate; thus browser fingerprinting should not be considered as reliable.

This method uses FingerprintJS library developed by FingerprintJS, Inc.

## Request fingerprinting

Request fingerprinting may be enabled separately for every view. It's not seen by user in any way and is hard to bypass, so it should be considered as primary fingerprinting method.

In order to enable it for some view:

```python
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from fingerprint.views import fingerprint

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

# TODOs:

* more params in BrowserFingerprint - visitor id is not enough
* tests

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