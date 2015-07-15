from prettyconf import config


DEFAULT_FILE_STORAGE = 'jangl_utils.s3_storage.MediaRootS3BotoStorage'
STATICFILES_STORAGE = 'jangl_utils.s3_storage.StaticRootS3BotoStorage'

AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_QUERYSTRING_AUTH = False

STORAGE_DOMAIN = config('STORAGE_DOMAIN', default='https://{0}.s3.amazonaws.com'.format(AWS_STORAGE_BUCKET_NAME))
