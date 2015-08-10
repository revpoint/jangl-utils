from simpleflake import simpleflake
from . import settings


def get_unique_id(**kwargs):
    kwargs.setdefault('epoch', settings.JANGL_EPOCH)
    return simpleflake(**kwargs)
