import logging
from django.utils import timezone
import pytz as pytz
from jangl_utils import settings
from jangl_utils.auth import get_token_from_request
from jangl_utils.backend_api import get_backend_api_session
from jangl_utils.unique_id import get_unique_id


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


class BackendAPIMiddleware(object):
    def process_request(self, request):
        assert hasattr(request, 'cid'), (
            'Make sure to insert "jangl_utils.middleware.CorrelationIDMiddleware"'
            'before "jangl_utils.middleware.BackendAPIMiddleware" in your'
            'middleware settings.'
        )

        api_session = get_backend_api_session(host=request.get_host(),
                                              cid=request.cid,
                                              api_token=get_token_from_request(request),
                                              twilio_signature=request.META.get('HTTP_X_TWILIO_SIGNATURE'))

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
