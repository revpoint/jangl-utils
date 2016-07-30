try:
    from django.conf import settings
except ImportError:
    settings = None

from prettyconf import config


BROKER_URL = getattr(settings, 'KAFKA_BROKER_URL',
                     config('KAFKA_BROKER_URL', default=None))
ZOOKEEPER_URL = getattr(settings, 'KAFKA_ZOOKEEPER_URL',
                        config('KAFKA_ZOOKEEPER_URL', default=None))
SCHEMA_REGISTRY_URL = getattr(settings, 'KAFKA_SCHEMA_REGISTRY_URL',
                              config('KAFKA_SCHEMA_REGISTRY_URL', default=None))
SCHEMA_MICROSERVICE = getattr(settings, 'KAFKA_SCHEMA_MICROSERVICE',
                              config('KAFKA_SCHEMA_MICROSERVICE', default=None))
