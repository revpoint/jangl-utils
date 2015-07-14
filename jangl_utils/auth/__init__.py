import inspect
from django.contrib.auth import _clean_credentials, _get_backends
from django.core.exceptions import PermissionDenied
from django.middleware.csrf import rotate_token
from jangl_utils.auth.models import User, AnonymousUser
from jangl_utils.auth.signals import user_logged_in, user_logged_out, user_login_failed


AUTH_SESSION_KEY = '_user_token'
AUTH_CURRENT_ACCOUNT_COOKIE = 'auth_account'


# User

def get_user(request, token):
    if token is not None:
        user_request = request.backend_api.get(('accounts', 'user'))

        if user_request.ok:
            return User(**user_request.json())

    return AnonymousUser()


def get_session_key(request):
    return request.session.get(AUTH_SESSION_KEY)


def get_user_from_request(request):
    # Try to get the auth from the user session first, so someone can't change users if they have a session.
    token = get_session_key(request)

    # If there is no session, then accept header authorization
    auth = request.META.get('HTTP_AUTHORIZATION')
    if not token and auth:
        split_auth = auth.split(' ')
        if split_auth[0] == 'JWT' and len(split_auth) == 2:
            token = split_auth[1]

    return get_user(request, token)


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
    user_login_failed.send(sender=__name__,
            credentials=_clean_credentials(credentials))


def login(request, token):
    if AUTH_SESSION_KEY in request.session:
        if request.session[AUTH_SESSION_KEY] != token:
            request.session.flush()
    else:
        request.session.cycle_key()

    request.session[AUTH_SESSION_KEY] = token
    user = get_user(request, token)

    if hasattr(request, 'user'):
        request.user = user
    rotate_token(request)
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


# Account

class AccountNotFound(Exception):
    pass


class CurrentAccount(object):
    def __init__(self, user, account):
        type_id = account.split('-')
        self.type = type_id[0]
        self.id = type_id[1] if len(type_id) > 1 else None
        self.account = self._get_account(user)

    def __str__(self):
        return '-'.join((self.type, self.id)) if self.id is not None else self.type

    def __getattr__(self, item):
        if self.account is not None:
            return self.account.get(item)

    def _get_by_id(self, list, id):
        results = filter(lambda x: x['id'] == int(id), list)
        if len(results):
            return results[0]

    def _get_account(self, user):
        if self.type == 'signup':
            return

        account = None
        if self.type == 'staff':
            account = user.staff
        elif self.type == 'buyer':
            account = self._get_by_id(user.buyers, self.id)
        elif self.type == 'vendor':
            account = self._get_by_id(user.vendors, self.id)

        if account is None:
            raise AccountNotFound

        return account


def get_default_account(user):
    if user.staff:
        return 'staff'
    if len(user.buyers):
        return 'buyer-{0}'.format(user.buyers[0]['id'])
    if len(user.vendors):
        return 'vendor-{0}'.format(user.vendors[0]['id'])
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

def get_site_from_request(request):
    site_request = request.backend_api.get(('accounts', 'site'))
    site_request.raise_for_status()
    return site_request.json()['preferences']
