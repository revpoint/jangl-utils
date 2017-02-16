import hashlib
import logging
import urllib
from types import MethodType

import gevent
from cachetools.keys import _HashedTuple
from django.conf import settings as django_settings
from django.core.cache import caches
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import six
from django.utils.timezone import now as tz_now, pytz
from json import dumps as to_json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3 import Retry
from jangl_utils import settings, VERSION
from jangl_utils.etc.json import _datetime_decoder


logger = logging.getLogger(__name__)

BACKEND_USER_AGENT = 'JanglBackendAPI/{}'.format(VERSION)
BACKEND_CONTENT_TYPE = 'application/json'

MAX_ASYNC_POOLS = 100
MAX_ASYNC_POOL_CONNECTIONS = 100
MAX_RETRIES = Retry(3, backoff_factor=0.1)


def get_service_url(service, *args, **kwargs):
    service_url = 'http://{0}:{1}/{2}'.format(settings.SERVICES_BACKEND_HOST,
                                              settings.SERVICES_BACKEND_PORT,
                                              service)

    trailing_slash = kwargs.get('trailing_slash', True) and '/' or ''
    query_string = kwargs.get('query_string')
    if isinstance(query_string, dict):
        query_string = urllib.urlencode(query_string)
    query_string = '?' + query_string if query_string else ''

    url_path = ('/' + '/'.join(map(str, args))) if args else ''
    return ''.join((service_url, url_path, trailing_slash, query_string))


class BackendAPIJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        try:
            return super(BackendAPIJSONEncoder, self).default(o)
        except TypeError:
            return str(o)


def decode_json(r, *args, **kwargs):
    def json(self, **kwargs):
        kwargs['object_hook'] = _datetime_decoder
        return self._json(**kwargs)

    r._json = r.json
    r.json = MethodType(json, r, type(r))
    return r


class BackendAPISession(requests.Session):

    def __init__(self):
        super(BackendAPISession, self).__init__()
        self.hooks.setdefault('response', []).append(decode_json)

    @property
    def session_cid(self):
        return self.headers.get(settings.CID_HEADER_NAME)

    def request(self, method, url, params=None, data=None, headers=None, cookies=None, files=None, auth=None,
                timeout=None, allow_redirects=True, proxies=None, hooks=None, stream=None, verify=None, cert=None,
                json=None, **kwargs):
        site_id = kwargs.pop('site_id', None)
        force_json = kwargs.pop('force_json', True)

        if isinstance(url, (tuple, list)):
            url = get_service_url(url[0], *url[1:], **kwargs)
        if data:
            if isinstance(data, unicode):
                data = data.encode('utf-8')
            elif force_json and not isinstance(data, six.string_types):
                data = to_json(data, cls=BackendAPIJSONEncoder)

        if site_id:
            if headers is None:
                headers = {}
            headers['X-Site-ID'] = str(site_id)

        self._log('request', method.upper(), url)
        self._debug(data)

        response = super(BackendAPISession, self).request(method, url, params, data, headers, cookies,
                                                          files, auth, timeout, allow_redirects, proxies,
                                                          hooks, stream, verify, cert, json)

        self._log('response', response.status_code, response.url)
        self._debug(response.text)

        return response

    def update_session_headers(self, cid=None, site_id=None, host=None, authorization=None,
                               api_token=None, twilio_signature=None, cookies=None):
        if cid:
            self.headers[settings.CID_HEADER_NAME] = str(cid)

        if site_id:
            self.headers['X-Site-ID'] = str(site_id)
        elif host:
            self.headers['Host'] = str(host)

        if authorization:
            self.headers['Authorization'] = authorization
        elif api_token:
            self.headers['Authorization'] = '{0} {1}'.format('JWT', api_token)

        if twilio_signature:
            self.headers['X-Twilio-Signature'] = twilio_signature

        if cookies:
            requests.utils.add_dict_to_cookiejar(self.cookies, cookies)

    def _log(self, log_type, *args):
        cid = '[{}] '.format(self.session_cid) if self.session_cid else ''
        logger.info('{}API {} - {}'.format(cid, log_type.upper(), ' '.join(args)))

    def _debug(self, data):
        if data:
            logger.debug(data)


DISABLE_BACKEND_API_CACHE = getattr(django_settings, 'DISABLE_BACKEND_API_CACHE', settings.DISABLE_BACKEND_API_CACHE)
if not DISABLE_BACKEND_API_CACHE:
    BACKEND_API_CACHE = getattr(django_settings, 'BACKEND_API_CACHE', 'default')
    cache = caches[BACKEND_API_CACHE]


class CachedBackendAPISession(BackendAPISession):
    cache_methods = ['GET', 'OPTIONS', 'HEAD']
    cache_use_headers = ['auth', 'cookies', 'host', 'site_id']

    def request(self, *args, **kwargs):
        is_cachable, cache_key, cache_seconds, cache_refresh = self.get_cache_vars(args, kwargs)
        if is_cachable:
            response = cache.get(cache_key)

            # If cache miss, refresh cache
            if response is None:
                response = self.refresh_cache(cache_key, cache_seconds, *args, **kwargs)

            else:
                self._log('cache hit', response.url)
                self._debug(response.text)

                # If cache hit and passed refresh timer, refresh cache in background
                cache_ttl = cache.ttl(cache_key) or 0
                if cache_refresh is not None and cache_refresh < (cache_seconds - cache_ttl):
                    self._log('cache refresh', 'TTL:', cache_ttl)
                    gevent.spawn(self.refresh_cache, cache_key, cache_seconds, *args, **kwargs)

            return response
        return super(CachedBackendAPISession, self).request(*args, **kwargs)

    def get_cache_vars(self, args, kwargs):
        cache_seconds = kwargs.pop('cache_seconds', 0)
        cache_refresh = kwargs.pop('cache_refresh', None)
        cache_methods = kwargs.pop('cache_methods', None)
        use_headers = kwargs.pop('cache_use_headers', None)
        extra_headers = kwargs.pop('cache_extra_headers', {})

        if cache_methods is None:
            cache_methods = self.cache_methods
        if use_headers is None:
            use_headers = self.cache_use_headers
        if extra_headers is None:
            extra_headers = {}

        method = args[0].upper()

        is_cachable = not DISABLE_BACKEND_API_CACHE and method in cache_methods and cache_seconds
        if is_cachable:
            cache_headers = self.get_cache_headers(use_headers, **extra_headers)
            cache_key = self.get_cache_key(cache_headers, *args, **kwargs)
        else:
            cache_key = None
        return is_cachable, cache_key, cache_seconds, cache_refresh

    def refresh_cache(self, cache_key, cache_seconds, *args, **kwargs):
        response = super(CachedBackendAPISession, self).request(*args, **kwargs)
        if response.ok:
            cache.set(cache_key, response, cache_seconds)
        return response

    def get_cache_key(self, *args, **kwargs):
        args = make_hashable(args)
        kwargs = dict(make_hashable(kwargs))
        hash_key = '{}'.format(_HashedTuple(args + sum(sorted(kwargs.items()), (None,))))
        hashed = hashlib.sha1(hash_key).hexdigest()
        return 'backend_api:{}'.format(hashed)

    def get_cache_headers(self, use_headers, **extra_headers):
        headers = {
            'auth': self.headers.get('Authorization'),
            'cookies': self.cookies.get_dict(),
            'host': self.headers.get('Host'),
            'site_id': self.headers.get('X-Site-ID'),
        }
        headers.update(extra_headers)
        return dict(((k, v) for k, v in headers.iteritems() if k in use_headers))


def get_backend_api_session(cached=True, **kwargs):
    if cached:
        api_session = CachedBackendAPISession()
    else:
        api_session = BackendAPISession()

    adapter = HTTPAdapter(pool_connections=kwargs.pop('max_async_pools', MAX_ASYNC_POOLS),
                          pool_maxsize=kwargs.pop('max_async_pool_connections', MAX_ASYNC_POOL_CONNECTIONS),
                          max_retries=kwargs.pop('max_retries', MAX_RETRIES))
    api_session.mount('http://', adapter)
    api_session.mount('https://', adapter)
    api_session.headers.update({
        'Content-Type': kwargs.pop('backend_content_type', BACKEND_CONTENT_TYPE),
        'User-Agent': kwargs.pop('backend_user_agent', BACKEND_USER_AGENT),
    })
    api_session.update_session_headers(**kwargs)
    return api_session


def make_hashable(value):
    if hasattr(value, 'iteritems'):
        return tuple(sorted([(k, make_hashable(v)) for k, v in value.iteritems()]))
    if isinstance(value, (list, tuple)):
        return tuple([make_hashable(v) for v in value])
    return value
