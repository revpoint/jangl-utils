from django.conf import settings as django_settings
from django.utils import six
from json import dumps as to_json
import requests
from jangl_utils.settings import CID_HEADER_NAME, DEBUG, PRODUCTION_BACKEND_URL
from jangl_utils.unique_id import get_unique_id
from jangl_utils.auth import get_token_from_request


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
    return request.META.get('HTTP_' + CID_HEADER_NAME)


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
        if request.propagate_response:
            response[CID_HEADER_NAME] = request.cid
        return response


def get_service_url(service, *args, **kwargs):
    if DEBUG:
        if not hasattr(django_settings, 'SERVICES'):
            raise NotImplementedError('Add SERVICES mapping to settings file.')
        service_url = django_settings.SERVICES[service]
    else:
        service_url = ','.join((PRODUCTION_BACKEND_URL, service))

    trailing_slash = kwargs.get('trailing_slash', True) and '/' or ''
    query_string = kwargs.get('query_string')
    query_string = '?' + query_string if query_string else ''

    url_path = ('/' + '/'.join(map(str, args))) if args else ''
    return ''.join((service_url, url_path, trailing_slash, query_string))


class BackendAPISession(requests.Session):
    def request(self, method, url, params=None, data=None, headers=None, cookies=None, files=None, auth=None,
                timeout=None, allow_redirects=True, proxies=None, hooks=None, stream=None, verify=None, cert=None,
                json=None, **kwargs):
        if isinstance(url, (tuple, list)):
            url = get_service_url(url[0], *url[1:], **kwargs)
        if not isinstance(data, six.string_types):
            data = to_json(data)
        response = super(BackendAPISession, self).request(method, url, params, data, headers, cookies,
                                                          files, auth, timeout, allow_redirects, proxies,
                                                          hooks, stream, verify, cert, json)
        # print response.status_code
        # print response.url
        # try:
        #     print response.json()
        # except:
        #     print response.text
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
            'CID': request.cid,
        })
        api_token = get_token_from_request(request)
        if api_token:
            api_session.headers['Authorization'] = '{0} {1}'.format('JWT', api_token)

        request.backend_api = api_session
