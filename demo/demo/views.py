from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from fingerprint.views import fingerprint, remember_user_session


@method_decorator(fingerprint, name="get")
class HomeView(TemplateView):
    template_name = "demo/home.html"


@remember_user_session
def remember_session_test_view(request):
    return HttpResponse("all ok")


@fingerprint
def request_fingerprint_test_view(request):
    return HttpResponse("all good")
