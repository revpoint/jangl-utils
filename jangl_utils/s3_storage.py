from django.contrib.staticfiles.storage import CachedFilesMixin
from storages.backends.s3boto3 import S3Boto3Storage


class CachedS3Storage(CachedFilesMixin, S3Boto3Storage):
    pass


StaticRootS3BotoStorage = lambda: CachedS3Storage(location='static')
MediaRootS3BotoStorage = lambda: S3Boto3Storage(location='media')
