from prettyconf import config, casts

ENVIRONMENT = config('ENVIRONMENT', default='develop')
DEBUG = config('DEBUG', default=True, cast=casts.Boolean())

JANGL_EPOCH = config('JANGL_EPOCH', default=1420070400)

CID_HEADER_NAME = config('CID_HEADER_NAME', default='X-CID')

SERVICES_BACKEND_HOST = config('PRODUCTION_BACKEND_HOST', default=config('HOST', default='localhost'))
SERVICES_BACKEND_PORT = config('PRODUCTION_BACKEND_PORT', default='8008')
