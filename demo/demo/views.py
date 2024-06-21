from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.generic import View
from fingerprint.views import fingerprint, remember_user_session


@method_decorator(fingerprint, name="get")
class RequestFingerprintTestView(View):
    def get(self, request):
        return HttpResponse("all ok")


@remember_user_session
def remember_session_test_view(request):
    return HttpResponse("all ok")
