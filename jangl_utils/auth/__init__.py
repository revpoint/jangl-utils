import inspect
from django.contrib.auth import _clean_credentials, _get_backends
from django.core.exceptions import PermissionDenied
from django.middleware.csrf import rotate_token
from rest_framework.authentication import BaseAuthentication
from jangl_utils.auth.models import User, AnonymousUser, CurrentAccount, AccountNotFound, Site
from jangl_utils.auth.signals import user_logged_in, user_logged_out, user_login_failed

AUTH_SESSION_KEY = '_user_token'
AUTH_CURRENT_ACCOUNT_COOKIE = 'auth_account'


# User

def get_user(request, token, use_cache=True):
    if token is not None:
        request.backend_api.update_session_headers(api_token=token)
        cache_args = dict(cache_seconds=3600, cache_refresh=30) if use_cache else {}
        user_request = request.backend_api.get(('accounts', 'user'), **cache_args)

        if user_request.ok:
            return User(**user_request.json())

    return AnonymousUser()


def get_token_from_request(request):
    token = None

    # Try to get the auth from the user session first, so someone can't change users if they have a session.
    if hasattr(request, 'session'):
        token = request.session.get(AUTH_SESSION_KEY)

    # If there is no session, then accept header authorization
    auth = request.META.get('HTTP_AUTHORIZATION')
    if not token and auth:
        split_auth = auth.split(' ')
        if split_auth[0] == 'JWT' and len(split_auth) == 2:
            token = split_auth[1]

    return token


def get_user_from_request(request, use_cache=True):
    token = get_token_from_request(request)
    return get_user(request, token, use_cache)


class JWTJanglAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = get_token_from_request(request)
        user = get_user(request, token)
        return (user, token)


def authenticate(**credentials):
    """
    If the given credentials are valid, return a User object.
    """
    for backend, backend_path in _get_backends(return_tuples=True):
        try:
            inspect.getcallargs(backend.authenticate, **credentials)
        except TypeError:
            # This backend doesn't accept these credentials as arguments. Try the next one.
            continue

        try:
            user = backend.authenticate(**credentials)
        except PermissionDenied:
            # This backend says to stop in our tracks - this user should not be allowed in at all.
            return None
        if user is None:
            continue
        # Annotate the user object with the path of the backend.
        return user

    # The credentials supplied are invalid to all backends, fire signal
    user_login_failed.send(sender=__name__, request=credentials.get('request'), email=credentials.get('email'))


def login(request, token, send_signal=True):
    if AUTH_SESSION_KEY in request.session:
        if request.session[AUTH_SESSION_KEY] != token:
            request.session.flush()
    else:
        request.session.cycle_key()

    request.session[AUTH_SESSION_KEY] = token
    user = get_user(request, token)

    if hasattr(request, 'user'):
        request.user = user
        request.account = get_account_from_request(request)
    rotate_token(request)
    if send_signal:
        user_logged_in.send(sender=user.__class__, request=request, user=user)


def logout(request):
    user = getattr(request, 'user', None)
    if hasattr(user, 'is_authenticated') and not user.is_authenticated():
        user = None

    user_logged_out.send(sender=user.__class__, request=request, user=user)
    request.session.flush()

    if hasattr(request, 'user'):
        from jangl_utils.auth.models import AnonymousUser
        request.user = AnonymousUser()
        request.account = get_account_from_request(request)


# Account


def get_default_account(user):
    if user.staff:
        return 'staff'
    if len(user.buyers):
        return 'buyer-{0}'.format(user.buyers[0]['id'])
    if len(user.vendors):
        return 'vendor-{0}'.format(user.vendors[0]['id'])
    if len(user.affiliates):
        return 'affiliate-{0}'.format(user.affiliates[0]['id'])
    return 'signup'


def get_account_from_request(request):
    user = request.user
    if user.is_anonymous():
        current_account = 'signup'
    else:
        current_account = request.COOKIES.get(AUTH_CURRENT_ACCOUNT_COOKIE)
        if current_account is None:
            current_account = get_default_account(user)
            set_current_account(request, current_account)

    try:
        return CurrentAccount(user, current_account)
    except AccountNotFound:
        current_account = get_default_account(user)
        set_current_account(request, current_account)
        return CurrentAccount(user, current_account)


def set_current_account(request, current_account):
    request._set_current_account_cookie = current_account


def set_current_account_cookie(response, current_account):
    max_age = 365 * 24 * 60 * 60  # one year
    response.set_cookie(AUTH_CURRENT_ACCOUNT_COOKIE, current_account,
                        max_age=max_age, httponly=True)


# Site

def get_site_from_request(request, site_id=None, use_cache=True):
    cache_args = dict(cache_seconds=3600, cache_refresh=60, cache_use_headers=['host', 'site_id']) if use_cache else {}

    site_request = request.backend_api.get(('accounts', 'site'), site_id=site_id, **cache_args)
    site_request.raise_for_status()
    return Site(site_request.json(), image_fields=['logo', 'retina_logo', 'hero_image'])


# Superuser

def get_superuser_from_request(request, use_cache=True):
    cache_args = dict(cache_seconds=3600, cache_refresh=600) if use_cache else {}
    superuser_request = request.backend_api.get(('accounts', 'is_superuser'), **cache_args)
    return superuser_request.ok
