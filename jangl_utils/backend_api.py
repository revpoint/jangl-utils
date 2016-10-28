import logging
import urllib
from types import MethodType
from cachetools.keys import hashkey
from django.conf import settings as django_settings
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import six
from django.utils.timezone import now as tz_now, pytz
from json import dumps as to_json
import requests
from jangl_utils import settings
from jangl_utils.etc.json import _datetime_decoder


logger = logging.getLogger(__name__)


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

        cid = ' [{}]'.format(self.session_cid) if self.session_cid else ''
        logger.info('{0}{1} API REQUEST - {2} {3}'.format(tz_now(), cid,
                                                          method.upper(), url))
        if data:
            logger.debug(data)

        response = super(BackendAPISession, self).request(method, url, params, data, headers, cookies,
                                                          files, auth, timeout, allow_redirects, proxies,
                                                          hooks, stream, verify, cert, json)

        logger.info('{0}{1} API RESPONSE - {2} {3}'.format(tz_now(), cid,
                                                           response.status_code, response.url))
        if response.text:
            logger.debug(response.text)

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


class CachedBackendAPISession(BackendAPISession):
    def get_request(self, *args, **kwargs):
        return super(CachedBackendAPISession, self).request(*args, **kwargs)

    def request(self, *args, **kwargs):
        cache_seconds = kwargs.pop('cache_seconds', 0)
        if cache_seconds:
            backend_api_cache = getattr(django_settings, 'BACKEND_API_CACHE', 'default')
            cache = django_settings.CACHES.get(backend_api_cache)
            if cache:
                cache_key = get_hash_key(self.get_host_headers(), self.cookies.get_dict(), *args, **kwargs)
                result = cache.get(cache_key)
                if result is not None:
                    return result
                result = self.get_request(*args, **kwargs)
                cache.set(cache_key, result, cache_seconds)
                return result
        return self.get_request(*args, **kwargs)

    def get_host_headers(self):
        return {
            'site_id': self.headers.get('X-Site-ID'),
            'host': self.headers.get('Host'),
            'auth': self.headers.get('Authorization'),
        }


def get_backend_api_session(**kwargs):
    api_session = CachedBackendAPISession()
    api_session.headers['Content-Type'] = 'application/json'
    api_session.update_session_headers(**kwargs)
    return api_session


def get_hash_key(*args, **kwargs):
    args = [a.items() if isinstance(a, dict) else a for a in args]
    kwargs = dict([(k, sorted(v.items())) if isinstance(v, dict) else (k, v) for (k, v) in kwargs.iteritems()])
    return hashkey(*args, **kwargs)
