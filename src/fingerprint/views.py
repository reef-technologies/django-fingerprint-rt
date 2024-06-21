from datetime import timedelta
from functools import wraps
from typing import Optional

from django.core.exceptions import BadRequest, DisallowedRedirect
from django.http.response import HttpResponse
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.decorators import method_decorator
from django.utils.encoding import iri_to_uri
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from ipware import get_client_ip

from .models import BrowserFingerprint, RequestFingerprint, Url, UserSession


def get_or_create_session_key(request) -> str:
    if not request.session or not request.session.session_key:
        request.session.create()
    return request.session.session_key


def fingerprint(fn):
    """A decorator which creates a backend Fingerprint object for the current request."""

    max_length = {
        field_name: RequestFingerprint._meta.get_field(field_name).max_length
        for field_name in ("user_agent", "accept", "content_encoding", "content_language", "referer", "cf_ipcountry")
    }
    max_length["url"] = Url._meta.get_field("value").max_length

    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        session_key = get_or_create_session_key(request)
        RequestFingerprint.objects.create(
            user_session=UserSession.objects.get_or_create(session_key=session_key)[0],
            url=Url.from_value(request.build_absolute_uri()[: max_length["url"]]),
            ip=get_client_ip(request)[0],
            user_agent=request.META.get("HTTP_USER_AGENT", "")[: max_length["user_agent"]],
            accept=request.META.get("HTTP_ACCEPT", "")[: max_length["accept"]],
            content_encoding=request.META.get("HTTP_CONTENT_ENCODING", "")[: max_length["content_encoding"]],
            content_language=request.META.get("HTTP_CONTENT_LANGUAGE", "")[: max_length["content_language"]],
            referer=request.META.get("HTTP_REFERER", "")[: max_length["referer"]],
            cf_ipcountry=request.META.get("HTTP_CF_IPCOUNTRY", "")[: max_length["cf_ipcountry"]],
        )
        return fn(request, *args, **kwargs)

    return wrapper


def remember_user_session(fn):
    """
    A decorator to match a user to a session.

    When database session backend is used, this is not necessary, as UserSession creation
    is triggered by Session's post_save signal. However, with other session backends this
    signal may not be triggered, thus we decorate some view with this decorator, and it
    remembers UserSession if user is logged in.
    """

    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            UserSession.objects.update_or_create(
                session_key=get_or_create_session_key(request),
                defaults=dict(user=request.user),
            )
        return fn(request, *args, **kwargs)

    return wrapper


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(remember_user_session, name="get")
@method_decorator(fingerprint, name="get")
class FingerprintView(TemplateView):
    """
    Multi-purpose fingerprinting view.

    If user makes a GET request to this page, a page with both a server and browser fingerprinting is displayed.
    Server fingerprinting is done when processing GET request in the view (by using @fingerprint decorator),
    and browser fingerprinting is done by javascript code in the template. Javascript code calculates visitor_id
    based on browser fingerprint, and then sends it to this view via POST request.

    If there is `next` parameter in the query string, user is redirected to that page after fingerprinting. Otherwise
    user will be redirected to main page.

    If user sends POST request to this page, it is assumed that the request is coming from javascript code and
    contains `id` post parameter, which is effectively a browser fingerprint (visitor_id).

    If redirect to other domains is required, then this view should be subclassed and
    `allowed_hosts` class variable should contain a set of allowed domains, say, `{'google.com'}`.
    By default only relative paths are allowed.
    """

    template_name = "fingerprint/fingerprint.html"
    redirect_in = timedelta(seconds=3)
    allowed_hosts: Optional[set] = None

    def get_context_data(self, **kwargs):
        redirect_url = iri_to_uri(self.request.GET.get("next", "/"))
        if not url_has_allowed_host_and_scheme(redirect_url, self.allowed_hosts):
            raise DisallowedRedirect()

        return {
            "redirect_in": self.redirect_in,
            "redirect_url": redirect_url,
        }

    def post(self, request, *args, **kwargs):
        try:
            visitor_id = request.POST["id"]
        except MultiValueDictKeyError:
            raise BadRequest()

        session_key = get_or_create_session_key(request)
        url_max_length = Url._meta.get_field("value").max_length
        BrowserFingerprint.objects.create(
            user_session=UserSession.objects.get_or_create(session_key=session_key)[0],
            url=Url.from_value(request.META.get("HTTP_REFERER", "")[:url_max_length]),
            visitor_id=visitor_id,
        )
        return HttpResponse(status=200)
