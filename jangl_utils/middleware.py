import logging
import types
from django.http import HttpResponse
from django.utils import timezone
import pytz as pytz
from jangl_utils import settings
from jangl_utils.auth import get_token_from_request
from jangl_utils.backend_api import get_backend_api_session
from jangl_utils.unique_id import get_unique_id


logger = logging.getLogger(__name__)


class HealthCheckMiddleware(object):
    def process_request(self, request):
        if request.path_info == '/_hc':
            return HttpResponse(content_type='text/plain')


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

        api_session = get_backend_api_session(cid=request.cid,
                                              site_id=request.META.get('HTTP_X_SITE_ID'),
                                              host=request.get_host(),
                                              api_token=get_token_from_request(request),
                                              twilio_signature=request.META.get('HTTP_X_TWILIO_SIGNATURE'),
                                              cookies=request.COOKIES)

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


class AccountNamesMiddleware(object):
    def process_request(self, request):
        request.buyer_names = self.get_buyer_names(request)
        request.vendor_names = self.get_vendor_names(request)

        def get_buyer_name(self, id):
            if self.buyer_names:
                for buyer in self.buyer_names:
                    if str(buyer['id']) == str(id):
                        return buyer['name']
            return '-'

        def get_vendor_name(self, id):
            if self.vendor_names:
                for vendor in self.vendor_names:
                    if str(vendor['id']) == str(id):
                        return vendor['name']
            return '-'

        request.get_buyer_name = types.MethodType(get_buyer_name, request, request.__class__)
        request.get_vendor_name = types.MethodType(get_vendor_name, request, request.__class__)

    def get_buyer_names(self, request):
        if hasattr(request, 'account') and request.account.is_staff:
            response = request.backend_api.get(('accounts', 'buyers', 'names'))
            if response.ok:
                return response.json()

    def get_vendor_names(self, request):
        if hasattr(request, 'account') and request.account.is_staff:
            response = request.backend_api.get(('accounts', 'vendors', 'names'))
            if response.ok:
                return response.json()
