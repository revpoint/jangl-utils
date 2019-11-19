import six

from jangl_utils import logger
from jangl_utils.backend_api import get_service_url
from jangl_utils.kafka import settings
from jangl_utils.unique_id import get_unique_id


def generate_client_settings(initial_settings, user_settings):
    settings = initial_settings.copy()
    for key, val in six.iteritems(user_settings):
        if val is None:
            continue
        logger.debug('using kafka setting {}: {}'.format(key, val))
        if key.startswith('topic.'):
            settings['default.topic.config'][key[6:]] = val
        else:
            settings[key] = val
    return settings


def generate_random_consumer_name():
    return '{}-{}'.format(settings.CONSUMER_BASE_NAME, get_unique_id())


def get_broker_url():
    return settings.BROKER_URL or config_missing('broker url')


def get_schema_registry_url():
    if settings.SCHEMA_MICROSERVICE:
        schema_registry_url = get_service_url(settings.SCHEMA_MICROSERVICE)
    else:
        schema_registry_url = settings.SCHEMA_REGISTRY_URL

    return schema_registry_url or config_missing('schema registry url')


def config_missing(field_name):
    raise NotImplementedError('Config for {} is missing'.format(field_name))
