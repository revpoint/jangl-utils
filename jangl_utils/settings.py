from prettyconf import config, casts

ENVIRONMENT = config('ENVIRONMENT', default='develop')
DEBUG = config('DEBUG', default=True, cast=casts.Boolean())

JANGL_EPOCH = config('JANGL_EPOCH', default=1420070400)

CID_HEADER_NAME = config('CID_HEADER_NAME', default='CID')

PRODUCTION_BACKEND_URL = config('PRODUCTION_BACKEND_URL', default=config('HOST', default='http://localhost:8008'))

LOCAL_SERVICES = {
    'accounts': config('SERVICES_ACCOUNTS_URI', default='http://localhost:8001'),
    'caps': config('SERVICES_CAPS_URI', default='http://localhost:8005'),
    'calls': config('SERVICES_CALLS_URI', default='http://localhost:8003'),
    'location': config('SERVICES_GEO_URI', default='http://localhost:8006'),
    'leads': config('SERVICES_LEADS_URI', default='http://localhost:8004'),
    'prefs': config('SERVICES_PREFS_URI', default='http://localhost:8002'),
}
