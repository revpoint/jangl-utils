import logging
from types import MethodType
import urllib
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import six
from django.utils import timezone
from django.utils.timezone import now as tz_now, pytz
from json import dumps as to_json
import requests
from jangl_utils import settings
from jangl_utils.etc.json import _datetime_decoder
from jangl_utils.unique_id import get_unique_id
from jangl_utils.auth import get_token_from_request


logger = logging.getLogger(__name__)


class SetRemoteAddrFromForwardedFor(object):
    def process_request(self, request):
        try:
            real_ip = request.META['HTTP_X_FORWARDED_FOR']
        except KeyError:
            pass
        else:
            # HTTP_X_FORWARDED_FOR can be a comma-separated list of IPs.
            # Take just the first one.
            real_ip = real_ip.split(",")[0]
            request.META['REMOTE_ADDR'] = real_ip


def get_correlation_id(request):
    return request.META.get('HTTP_' + settings.CID_HEADER_NAME.replace('-', '_'))


class CorrelationIDMiddleware(object):
    def process_request(self, request):
        # If this is a downstream request, use existing CID and return in response header
        cid = get_correlation_id(request)
        if cid:
            request.cid = cid
            request.propagate_response = True

        # Otherwise create a new CID and don't return in header
        else:
            request.cid = get_unique_id()
            request.propagate_response = False

    def process_response(self, request, response):
        if hasattr(request, 'propagate_response') and request.propagate_response:
            response[settings.CID_HEADER_NAME] = request.cid
        return response


def get_service_url(service, *args, **kwargs):
    if settings.ENVIRONMENT == 'develop':
        service_url = settings.LOCAL_SERVICES[service]
    else:
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
        return self.headers.get(settings.CID_HEADER_NAME, '-')

    def request(self, method, url, params=None, data=None, headers=None, cookies=None, files=None, auth=None,
                timeout=None, allow_redirects=True, proxies=None, hooks=None, stream=None, verify=None, cert=None,
                json=None, **kwargs):
        if isinstance(url, (tuple, list)):
            url = get_service_url(url[0], *url[1:], **kwargs)
        if data and not isinstance(data, six.string_types):
            data = to_json(data, cls=BackendAPIJSONEncoder)

        logger.info('{0} [{1}] API REQUEST - {2} {3}'.format(tz_now(), self.session_cid,
                                                             method.upper(), url))
        if data:
            logger.debug(data)

        response = super(BackendAPISession, self).request(method, url, params, data, headers, cookies,
                                                          files, auth, timeout, allow_redirects, proxies,
                                                          hooks, stream, verify, cert, json)

        logger.info('{0} [{1}] API RESPONSE - {2} {3}'.format(tz_now(), self.session_cid,
                                                              response.status_code, response.url))
        if response.text:
            logger.debug(response.text)

        return response


class BackendAPIMiddleware(object):
    def process_request(self, request):
        assert hasattr(request, 'cid'), (
            'Make sure to insert "jangl_utils.middleware.CorrelationIDMiddleware"'
            'before "jangl_utils.middleware.BackendAPIMiddleware" in your'
            'middleware settings.'
        )

        api_session = BackendAPISession()
        api_session.headers.update({
            'Content-Type': 'application/json',
            'Host': request.get_host(),
            settings.CID_HEADER_NAME: request.cid,
        })
        if 'HTTP_X_TWILIO_SIGNATURE' in request.META:
            api_session.headers['X-Twilio-Signature'] = request.META['HTTP_X_TWILIO_SIGNATURE']
        api_token = get_token_from_request(request)
        if api_token:
            api_session.headers['Authorization'] = '{0} {1}'.format('JWT', api_token)

        request.backend_api = api_session


class TimezoneMiddleware(object):
    def process_request(self, request):
        try:
            tz = request.account.get('timezone', request.site.get('timezone'))
        except AttributeError:
            tz = 'US/Eastern'
        if tz:
            timezone.activate(pytz.timezone(tz))
        else:
            timezone.deactivate()
