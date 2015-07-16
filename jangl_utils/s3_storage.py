from django.contrib.staticfiles.storage import CachedFilesMixin
from storages.backends.s3boto import S3BotoStorage


class FixedS3BotoStorage(S3BotoStorage):
    def url(self, name):
        url = super(FixedS3BotoStorage, self).url(name)
        if name.endswith('/') and not url.endswith('/'):
            url += '/'
        return url


class CachedS3Storage(CachedFilesMixin, FixedS3BotoStorage):
    pass


StaticRootS3BotoStorage = lambda: CachedS3Storage(location='static')
MediaRootS3BotoStorage = lambda: FixedS3BotoStorage(location='media')
