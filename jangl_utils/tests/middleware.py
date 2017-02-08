from jangl_utils.tests import auth


class SuperuserAuthMiddleware(object):
    def process_request(self, request):
        request.user = auth.TEST_SUPERUSER_USER
        request.account = None
        request.site = None
        request.is_superuser = True


class StaffAuthMiddleware(object):
    def process_request(self, request):
        request.user = auth.TEST_STAFF_USER
        request.account = auth.TEST_STAFF_ACCOUNT
        request.site = auth.TEST_SITE
        request.is_superuser = False


class BuyerAuthMiddleware(object):
    def process_request(self, request):
        request.user = auth.TEST_BUYER_USER
        request.account = auth.TEST_BUYER_ACCOUNT
        request.site = auth.TEST_SITE
        request.is_superuser = False


class VendorAuthMiddleware(object):
    def process_request(self, request):
        request.user = auth.TEST_VENDOR_USER
        request.account = auth.TEST_VENDOR_ACCOUNT
        request.site = auth.TEST_SITE
        request.is_superuser = False
