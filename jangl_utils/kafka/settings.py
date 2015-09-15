from prettyconf import config, casts
from jangl_utils.backend_api import get_service_url


ENABLE_KAFKA = config('ENABLE_KAFKA', default=True, cast=casts.Boolean())
KAFKA_URL = config('KAFKA_URL', default='192.168.99.100:9092')
SCHEMA_REGISTRY_URL = config('SCHEMA_REGISTRY_URL', default='http://192.168.99.100:8081')

KAFKA_SCHEMA_MICROSERVICE = config('KAFKA_SCHEMA_MICROSERVICE', default=None)
if KAFKA_SCHEMA_MICROSERVICE:
    KAFKA_SCHEMA_REGISTRY_URL = get_service_url(KAFKA_SCHEMA_MICROSERVICE)
