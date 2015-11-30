import logging
from time import mktime
from confluent.schemaregistry.client import CachedSchemaRegistryClient
from confluent.schemaregistry.serializers import MessageSerializer
from datetime import datetime
from pykafka import KafkaClient
from pykafka.partitioners import hashing_partitioner, random_partitioner
from pytz import utc
from jangl_utils.backend_api import get_service_url
from jangl_utils.kafka import settings, exceptions
from jangl_utils.kafka.schemas import Schema

logger = logging.getLogger(__name__)


def tz_now():
    return datetime.utcnow().replace(tzinfo=utc)


class Producer(object):
    topic_name = None
    has_key = False
    partitioner = lambda self, *args: random_partitioner(*args)
    key_schema = None
    value_schema = None
    async = True

    def __init__(self, **kwargs):
        # Set topic name
        self.topic_name = kwargs.get('topic_name') or self.get_topic_name()
        logger.debug('set kafka topic to: ' + self.topic_name)

        # Set kafka url and client
        self.broker_url = kwargs.get('broker_url') or self.get_broker_url()
        logger.debug('connecting to kafka with url: ' + self.broker_url)
        self.kafka_client = KafkaClient(hosts=self.broker_url)

        # Set topic
        assert self.topic_name in self.kafka_client.topics, \
            'Cannot find kafka topic "{0}". Please create topic.'.format(self.topic_name)
        self.topic = self.kafka_client.topics[self.topic_name]

        # Set producer
        self.partitioner = kwargs.get('partitioner') or self.get_partitioner()

        # Set schema registry
        schema_registry_url = kwargs.get('schema_registry_url') or self.get_schema_registry_url()
        logger.debug('loading schema registry with url: ' + schema_registry_url)
        self.schema_client = CachedSchemaRegistryClient(url=schema_registry_url)
        self.serializer = MessageSerializer(self.schema_client)

        # Set key schema
        if self.has_key:
            key_schema = kwargs.get('key_schema', self.get_key_schema())
            self.key_schema = Schema(self, self.get_key_schema_name(), key_schema)

        # Set value schema
        value_schema = kwargs.get('value_schema', self.get_value_schema())
        self.value_schema = Schema(self, self.get_value_schema_name(), value_schema)

    def get_topic_name(self):
        if self.topic_name is None:
            raise NotImplementedError
        return self.topic_name

    def get_broker_url(self):
        broker_url = settings.BROKER_URL
        if broker_url is None:
            raise NotImplementedError
        return broker_url

    def get_schema_registry_url(self):
        schema_microservice = settings.SCHEMA_MICROSERVICE
        if schema_microservice:
            schema_registry_url = get_service_url(schema_microservice)
        else:
            schema_registry_url = settings.SCHEMA_REGISTRY_URL
        if schema_registry_url is None:
            raise NotImplementedError
        return schema_registry_url

    def get_key_schema_name(self):
        return self.topic_name + '-key'

    def get_value_schema_name(self):
        return self.topic_name + '-value'

    def get_key_schema(self):
        return self.key_schema

    def get_value_schema(self):
        return self.value_schema

    def get_partitioner(self):
        partitioner = self.partitioner
        return lambda *args: partitioner(*args)

    def get_timestamp(self, timestamp=None):
        if timestamp is None:
            timestamp = tz_now()
        if isinstance(timestamp, datetime):
            timestamp = mktime(timestamp.timetuple()) + (timestamp.microsecond / 1e6)
        return timestamp

    def get_producer(self):
        producer = self.topic.get_producer if self.async else self.topic.get_sync_producer
        return producer(partitioner=self.partitioner)

    def produce(self, *args, **kwargs):
        if not hasattr(self, '_producer') or not self._producer._running:
            self._producer = self.get_producer()
        self._producer.produce(*args, **kwargs)

    def send_message(self, *args, **kwargs):
        """ Send a message to kafka

        If the topic has a key, this method accepts the following signatures:
        - self.send_message(key, message)
        - self.send_message((key, message))
        - self.send_message([key, message])
        - self.send_message(key='', message='')

        If the topic does not have a key, this method accepts:
        - self.send_message(message)

        """
        if self.has_key:
            if len(args) == 2:
                key, message = args
            elif len(args) == 1:
                try:
                    key, message = args[0]
                except ValueError:
                    raise exceptions.MissingKeyError
            elif 'key' in kwargs and 'message' in kwargs:
                key = kwargs['key']
                message = kwargs['message']
            else:
                raise exceptions.InvalidDataError

            logger.debug('key: ' + str(key))
            logger.debug('message: ' + str(message))

            encoded_key = self.key_schema.encode_message(key)
            encoded_message = self.value_schema.encode_message(message)

            logger.debug('encoded key: ' + str(encoded_key))
            logger.debug('encoded message: ' + str(encoded_message))

            self.produce(encoded_message, partition_key=encoded_key)

        elif len(args) == 1:
            message = args[0]
            logger.debug('message: ' + str(message))

            encoded_message = self.value_schema.encode_message(message)
            logger.debug('encoded message: ' + str(encoded_message))

            self.produce(encoded_message)

        else:
            raise exceptions.InvalidDataError


class HashedPartitionProducer(Producer):
    has_key = True
    partitioner = hashing_partitioner
