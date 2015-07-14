from django.http import HttpResponseRedirect
from django.utils.functional import SimpleLazyObject
from requests import HTTPError
from jangl_utils.auth import get_user_from_request, get_account_from_request, set_current_account_cookie, \
    get_site_from_request, logout

EXPIRED_ERROR = "Signature has expired."


def get_cached_user(request):
    if not hasattr(request, '_cached_user'):
        request._cached_user = get_user_from_request(request)
    return request._cached_user


def get_cached_account(request):
    if not hasattr(request, '_cached_account'):
        request._cached_account = get_account_from_request(request)
    return request._cached_account


def get_cached_site(request):
    if not hasattr(request, '_cached_site'):
        request._cached_site = get_site_from_request(request)
    return request._cached_site


class AuthMiddleware(object):
    def process_request(self, request):
        request.user = SimpleLazyObject(lambda: get_cached_user(request))
        request.account = SimpleLazyObject(lambda: get_cached_account(request))
        request.site = SimpleLazyObject(lambda: get_cached_site(request))

    def process_response(self, request, response):
        if hasattr(request, '_set_current_account_cookie'):
            current_account = request._set_current_account_cookie
            set_current_account_cookie(response, current_account)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, HTTPError):
            print exception.response.status_code
            print exception.response.json()
            if (exception.response.status_code == 401 and
                        exception.response.json()['detail'] == EXPIRED_ERROR):
                logout(request)
                return HttpResponseRedirect('')
