from prettyconf import config

DEBUG = config('DEBUG', default=True)

JANGL_EPOCH = config('JANGL_EPOCH', default=1420070400)

CID_HEADER_NAME = config('CID_HEADER_NAME', default='CID')
