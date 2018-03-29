import types

from django.http import HttpResponse
from django.utils import timezone
import pytz as pytz
from django.utils.functional import SimpleLazyObject

from jangl_utils import settings
from jangl_utils.auth import get_token_from_request
from jangl_utils.backend_api import get_backend_api_session
from jangl_utils.etc.mixins import MiddlewareMixin
from jangl_utils.unique_id import get_unique_id

try:
    import uwsgi
except ImportError:
    uwsgi = None


class HealthCheckMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path_info == '/_hc':
            if uwsgi and hasattr(uwsgi, 'set_logvar'):
                uwsgi.set_logvar('cid', 'null')
            return HttpResponse(content_type='text/plain')


class SetRemoteAddrFromForwardedFor(MiddlewareMixin):
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


class CorrelationIDMiddleware(MiddlewareMixin):
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
        if uwsgi and hasattr(uwsgi, 'set_logvar'):
            uwsgi.set_logvar('cid', str(request.cid))

    def process_response(self, request, response):
        if hasattr(request, 'propagate_response') and request.propagate_response:
            response[settings.CID_HEADER_NAME] = request.cid
        return response


class BackendAPIMiddleware(MiddlewareMixin):
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

    def process_response(self, request, response):
        if hasattr(request, 'backend_api'):
            try:
                request.backend_api.close()
            finally:
                pass
        return response


class TimezoneMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        try:
            tz = request.account.get('timezone', request.site.get('timezone'))
        except AttributeError:
            tz = 'US/Eastern'
        if tz:
            timezone.activate(pytz.timezone(tz))
        else:
            timezone.deactivate()


class AccountNamesMiddleware(MiddlewareMixin):

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.buyer_names = SimpleLazyObject(lambda: self.get_buyer_names(request))
        request.vendor_names = SimpleLazyObject(lambda: self.get_vendor_names(request))
        request.affiliate_names = SimpleLazyObject(lambda: self.get_affiliate_names(request))

        def get_buyer_name(self, buyer_id):
            if buyer_id in self.buyer_names:
                return self.buyer_names[buyer_id]['name']

        def get_vendor_name(self, vendor_id):
            if vendor_id in self.vendor_names:
                return self.vendor_names[vendor_id]['name']

        def get_affiliate_name(self, affiliate_id):
            if affiliate_id in self.affiliate_names:
                return self.affiliate_names[affiliate_id]['name']

        request.get_buyer_name = types.MethodType(get_buyer_name, request)
        request.get_vendor_name = types.MethodType(get_vendor_name, request)
        request.get_affiliate_name = types.MethodType(get_affiliate_name, request)

    def get_buyer_names(self, request):
        return self.get_names(request, 'buyers')

    def get_vendor_names(self, request):
        return self.get_names(request, 'vendors')

    def get_affiliate_names(self, request):
        return self.get_names(request, 'affiliates')

    def get_names(self, request, account_type):
        if hasattr(request, 'account') and request.account.is_staff:
            response = request.backend_api.get(('accounts', account_type, 'names'),
                                               cache_seconds=3600, cache_refresh=30)
            if response.ok:
                return {a['id']: a for a in response.json()}
        return {}
