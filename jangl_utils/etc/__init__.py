from django.core.exceptions import ImproperlyConfigured

try:
    from django.core.cache import cache
except ImproperlyConfigured:
    cache = None
