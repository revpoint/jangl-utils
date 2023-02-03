import os
try:
    from urllib import parse as urllib
except ImportError:
    import urllib

import six

from jangl_utils import settings, VERSION


def get_service_url_base(service):
    explicit_url = 'JANGL_{}_URL'.format(service.upper())
    if os.environ.get(explicit_url):
        return os.environ[explicit_url]
    return settings.SERVICES_URL_TEMPLATE.format(
        HOST=settings.SERVICES_BACKEND_HOST,
        PORT=settings.SERVICES_BACKEND_PORT,
        SERVICE=service
    )


def get_service_url(service, *args, **kwargs):
    service_url = get_service_url_base(service)

    trailing_slash = kwargs.get('trailing_slash', True) and '/' or ''
    query_string = kwargs.get('query_string')
    if isinstance(query_string, dict):
        query_string = urllib.urlencode(query_string)
    query_string = '?' + query_string if query_string else ''

    url_path = ('/' + '/'.join(map(str, args))) if args else ''
    return ''.join((service_url, url_path, trailing_slash, query_string))


def make_hashable(value):
    if hasattr(value, 'iteritems') or hasattr(value, 'items'):
        return tuple(sorted([(k, make_hashable(v)) for k, v in six.iteritems(value)]))
    if isinstance(value, (list, tuple)):
        return tuple([make_hashable(v) for v in value])
    return value
