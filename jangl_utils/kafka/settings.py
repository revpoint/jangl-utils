from prettyconf import config

BROKER_URL = config('KAFKA_BROKER_URL', default=None)
ZOOKEEPER_URL = config('KAFKA_ZOOKEEPER_URL', default=None)
SCHEMA_REGISTRY_URL = config('KAFKA_SCHEMA_REGISTRY_URL', default=None)
SCHEMA_MICROSERVICE = config('KAFKA_SCHEMA_MICROSERVICE', default=None)
