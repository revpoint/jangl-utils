from contextlib import contextmanager

sentry_sdk = None
try:
    import sentry_sdk
except ImportError:
    pass


def captureException(*args, **kwargs):
    if sentry_sdk:
        return sentry_sdk.capture_exception(*args, **kwargs)


@contextmanager
def capture_on_error(raise_error=True):
    try:
        yield
    except Exception:
        captureException()
        if raise_error:
            raise
