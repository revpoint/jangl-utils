from prettyconf import config, casts

try:
    from django.conf import settings as django_settings
except ImportError:
    django_settings = None


ENVIRONMENT = getattr(django_settings, 'ENVIRONMENT', config('ENVIRONMENT', default='develop'))
DEBUG = getattr(django_settings, 'DEBUG', config('DEBUG', default=True, cast=casts.Boolean()))

JANGL_EPOCH = getattr(django_settings, 'JANGL_EPOCH', config('JANGL_EPOCH', default=1420070400))

CID_HEADER_NAME = getattr(django_settings, 'CID_HEADER_NAME', config('CID_HEADER_NAME', default='X-CID'))
SITE_ID_HEADER_NAME = getattr(django_settings, 'SITE_ID_HEADER_NAME',
                              config('SITE_ID_HEADER_NAME', default='X-Site-ID'))

SERVICES_BACKEND_HOST = getattr(django_settings, 'SERVICES_BACKEND_HOST',
                                config('PRODUCTION_BACKEND_HOST', default=config('HOST', default='localhost')))
SERVICES_BACKEND_PORT = getattr(django_settings, 'SERVICES_BACKEND_PORT',
                                config('PRODUCTION_BACKEND_PORT', default='8008'))

# Deprecated, use enable
DISABLE_BACKEND_API_CACHE = getattr(django_settings, 'DISABLE_BACKEND_API_CACHE',
                                    config('DISABLE_BACKEND_API_CACHE', default=False, cast=casts.Boolean()))

ENABLE_BACKEND_API_CACHE = getattr(django_settings, 'ENABLE_BACKEND_API_CACHE',
                                   config('ENABLE_BACKEND_API_CACHE', default=(not DISABLE_BACKEND_API_CACHE),
                                          cast=casts.Boolean()))

USE_NEW_BACKEND_API = getattr(django_settings, 'USE_NEW_BACKEND_API',
                              config('USE_NEW_BACKEND_API', default=False, cast=casts.Boolean()))

BACKEND_API_CACHE = getattr(django_settings, 'BACKEND_API_CACHE', 'default')
BACKEND_API_CACHE_VERSION = getattr(django_settings, 'BACKEND_API_CACHE_VERSION',
                                    config('BACKEND_API_CACHE_VERSION', default='1'))
BACKEND_API_VERBOSE_LOG_LEVEL = getattr(django_settings, 'BACKEND_API_VERBOSE_LOG_LEVEL',
                                        config('BACKEND_API_VERBOSE_LOG_LEVEL', default='DEBUG'))
