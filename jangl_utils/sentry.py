from contextlib import contextmanager

from django.conf import settings

sentry_client = None
try:
    from raven.contrib.django.models import get_client
    if getattr(settings, 'SENTRY_URL'):
        sentry_client = get_client()
except ImportError:
    pass


def captureException(*args, **kwargs):
    if sentry_client:
        sentry_client.captureException(*args, **kwargs)


@contextmanager
def capture_on_error(raise_error=True):
    try:
        yield
    except Exception:
        captureException()
        if raise_error:
            raise
