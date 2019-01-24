import gevent
import hashlib

from cachetools.keys import _HashedTuple
from jangl_utils import settings
from jangl_utils.backend_api.base import BackendAPISession
from jangl_utils.backend_api.utils import make_hashable

try:
    from django.core.cache import caches, InvalidCacheBackendError
except ImportError:
    caches = None
    InvalidCacheBackendError = type('InvalidCacheBackendError', (Exception,), {})


def can_use_cache():
    try:
        caches[settings.BACKEND_API_CACHE]
    except (TypeError, InvalidCacheBackendError):
        return False
    else:
        return True


class CachedBackendAPISession(BackendAPISession):
    cache_methods = ['GET', 'OPTIONS', 'HEAD']
    cache_use_headers = ['auth', 'cookies', 'host', 'site_id']

    def request(self, *args, **kwargs):
        is_cachable, cache_key, cache_seconds, cache_refresh = self.get_cache_vars(args, kwargs)
        if is_cachable:
            response = self.cache.get(cache_key, version=settings.BACKEND_API_CACHE_VERSION)

            # If cache miss, refresh cache
            if response is None:
                response = self.refresh_cache(cache_key, cache_seconds, *args, **kwargs)

            else:
                self._log('cache hit', response.url)
                self._debug(response.text)

                # If cache hit and passed refresh timer, refresh cache in background
                cache_ttl = self.cache.ttl(cache_key, version=settings.BACKEND_API_CACHE_VERSION) or 0
                if cache_refresh is not None and cache_refresh < (cache_seconds - cache_ttl):
                    self._log('cache refresh', 'TTL:', cache_ttl)
                    gevent.spawn(self.refresh_cache, cache_key, cache_seconds, *args, **kwargs)

            return response
        return super(CachedBackendAPISession, self).request(*args, **kwargs)

    @property
    def cache(self):
        return caches[settings.BACKEND_API_CACHE]

    def get_cache_vars(self, args, kwargs):
        cache_seconds = kwargs.pop('cache_seconds', 0)
        cache_refresh = kwargs.pop('cache_refresh', None)
        cache_methods = kwargs.pop('cache_methods', None)
        use_headers = kwargs.pop('cache_use_headers', None)
        extra_headers = kwargs.pop('cache_extra_headers', {})

        if cache_methods is None:
            cache_methods = self.cache_methods
        if use_headers is None:
            use_headers = self.cache_use_headers
        if extra_headers is None:
            extra_headers = {}

        method = args[0].upper()

        is_cachable = method in cache_methods and cache_seconds
        if is_cachable:
            cache_headers = self.get_cache_headers(use_headers, **extra_headers)
            cache_key = self.get_cache_key(cache_headers, *args, **kwargs)
        else:
            cache_key = None
        return is_cachable, cache_key, cache_seconds, cache_refresh

    def refresh_cache(self, cache_key, cache_seconds, *args, **kwargs):
        response = super(CachedBackendAPISession, self).request(*args, **kwargs)
        if response.ok:
            self.cache.set(cache_key, response, cache_seconds, version=settings.BACKEND_API_CACHE_VERSION)
        return response

    def get_cache_key(self, *args, **kwargs):
        args = make_hashable(args)
        kwargs = dict(make_hashable(kwargs))
        hash_key = '{}'.format(_HashedTuple(args + sum(sorted(kwargs.items()), (None,))))
        hashed = hashlib.sha1(hash_key).hexdigest()
        return 'backend_api:{}'.format(hashed)

    def get_cache_headers(self, use_headers, **extra_headers):
        headers = {
            'auth': self.headers.get('Authorization'),
            'cookies': self.cookies.get_dict(),
            'host': self.headers.get('Host'),
            'site_id': self.headers.get('X-Site-ID'),
        }
        headers.update(extra_headers)
        return dict(((k, v) for k, v in headers.iteritems() if k in use_headers))
