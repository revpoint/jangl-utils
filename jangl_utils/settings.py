from prettyconf import config

DEBUG = config('DEBUG', default=True)

JANGL_EPOCH = config('JANGL_EPOCH', default=1420070400)

CID_HEADER_NAME = config('CID_HEADER_NAME', default='CID')

PRODUCTION_BACKEND_URL = config('PRODUCTION_BACKEND_URL', default='http://localhost:8008')
