from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.functional import SimpleLazyObject
from requests import HTTPError
from jangl_utils.auth import get_user_from_request, get_account_from_request, set_current_account_cookie, \
    get_site_from_request, logout, get_superuser_from_request

EXPIRED_ERROR = "Signature has expired."

AUTH_MIDDLEWARE_ATTACH_USER = getattr(settings, 'AUTH_MIDDLEWARE_ATTACH_USER', True)
AUTH_MIDDLEWARE_ATTACH_ACCOUNT = getattr(settings, 'AUTH_MIDDLEWARE_ATTACH_ACCOUNT', True)
AUTH_MIDDLEWARE_ATTACH_SITE = getattr(settings, 'AUTH_MIDDLEWARE_ATTACH_SITE', True)
AUTH_MIDDLEWARE_ATTACH_SUPERUSER = getattr(settings, 'AUTH_MIDDLEWARE_ATTACH_SUPERUSER', False)


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


def get_cached_superuser(request):
    if not hasattr(request, '_cached_superuser'):
        request._cached_superuser = get_superuser_from_request(request)
    return request._cached_superuser


class AuthMiddleware(object):
    def process_request(self, request):
        if AUTH_MIDDLEWARE_ATTACH_USER:
            request.user = SimpleLazyObject(lambda: get_cached_user(request))
        if AUTH_MIDDLEWARE_ATTACH_ACCOUNT:
            request.account = SimpleLazyObject(lambda: get_cached_account(request))
        if AUTH_MIDDLEWARE_ATTACH_SITE:
            request.site = SimpleLazyObject(lambda: get_cached_site(request))
        if AUTH_MIDDLEWARE_ATTACH_SUPERUSER:
            request.is_superuser = SimpleLazyObject(lambda: get_cached_superuser(request))

    def process_response(self, request, response):
        if hasattr(request, '_set_current_account_cookie'):
            current_account = request._set_current_account_cookie
            set_current_account_cookie(response, current_account)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, HTTPError):
            if (exception.response.status_code == 401 and
                        exception.response.json()['detail'] == EXPIRED_ERROR):
                logout(request)
                return HttpResponseRedirect('')
