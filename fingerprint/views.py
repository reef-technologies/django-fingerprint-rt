from functools import wraps
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.http.response import HttpResponse
from django.core.exceptions import BadRequest
from django.utils.datastructures import MultiValueDictKeyError
from datetime import timedelta

from ipware import get_client_ip

from .models import RequestFingerprint, BrowserFingerprint, UserSession


def get_or_create_session_key(request) -> str:
    if not request.session or not request.session.session_key:
        request.session.create()
    return request.session.session_key


def fingerprint(fn):
    """ A decorator which creates a backend Fingerprint object for the current request. """

    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        RequestFingerprint.objects.create(
            session_key=get_or_create_session_key(request),
            ip=get_client_ip(request)[0],
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            accept=request.META.get('HTTP_ACCEPT', ''),
            content_encoding=request.META.get('HTTP_CONTENT_ENCODING', ''),
            content_language=request.META.get('HTTP_CONTENT_LANGUAGE', ''),
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
            UserSession.objects.get_or_create(
                user=request.user,
                session_key=get_or_create_session_key(request),
            )
        return fn(request, *args, **kwargs)

    return wrapper


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(remember_user_session, name='dispatch')
@method_decorator(fingerprint, name='dispatch')
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
    """

    template_name = 'fingerprint.html'
    redirect_in = timedelta(seconds=3)

    def get_context_data(self, **kwargs):
        redirect_url = self.request.build_absolute_uri(self.request.GET.get('next', '/'))
        return {
            'redirect_in': self.redirect_in,
            'redirect_url': redirect_url,
        }

    def post(self, request, *args, **kwargs):
        try:
            visitor_id = request.POST['id']
        except MultiValueDictKeyError:
            raise BadRequest()

        BrowserFingerprint.objects.create(
            session_key=get_or_create_session_key(request),
            visitor_id=visitor_id,
        )
        return HttpResponse(status=200)
