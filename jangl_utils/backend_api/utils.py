import urllib
from jangl_utils import settings, VERSION


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


def make_hashable(value):
    if hasattr(value, 'iteritems'):
        return tuple(sorted([(k, make_hashable(v)) for k, v in value.iteritems()]))
    if isinstance(value, (list, tuple)):
        return tuple([make_hashable(v) for v in value])
    return value
