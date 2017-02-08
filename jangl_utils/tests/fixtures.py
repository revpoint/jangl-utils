from rest_framework.test import APIClient
import pytest

from jangl_utils.tests import auth, middleware, utils

__all__ = ['superuser_client', 'staff_client', 'buyer_client', 'vendor_client']


@pytest.fixture
def superuser_client(settings):
    settings.MIDDLEWARE_CLASSES = utils.replace_auth_middleware(settings.MIDDLEWARE_CLASSES,
                                                                middleware.SuperuserAuthMiddleware)
    client = APIClient()
    client.force_authenticate(user=auth.TEST_SUPERUSER_USER)
    return client


@pytest.fixture
def staff_client(settings):
    settings.MIDDLEWARE_CLASSES = utils.replace_auth_middleware(settings.MIDDLEWARE_CLASSES,
                                                                middleware.StaffAuthMiddleware)
    client = APIClient()
    client.force_authenticate(user=auth.TEST_STAFF_USER)
    return client


@pytest.fixture
def buyer_client(settings):
    settings.MIDDLEWARE_CLASSES = utils.replace_auth_middleware(settings.MIDDLEWARE_CLASSES,
                                                                middleware.BuyerAuthMiddleware)
    client = APIClient()
    client.force_authenticate(user=auth.TEST_BUYER_USER)
    return client


@pytest.fixture
def vendor_client(settings):
    settings.MIDDLEWARE_CLASSES = utils.replace_auth_middleware(settings.MIDDLEWARE_CLASSES,
                                                                middleware.VendorAuthMiddleware)
    client = APIClient()
    client.force_authenticate(user=auth.TEST_VENDOR_USER)
    return client
