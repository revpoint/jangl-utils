from django.core.cache import get_cache


def get_local_cache(cache_name):
    return get_cache('django.core.cache.backends.locmem.LocMemCache', **{
        'LOCATION': cache_name,
    })
