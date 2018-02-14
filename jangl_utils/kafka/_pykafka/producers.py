from confluent.schemaregistry.client import CachedSchemaRegistryClient
from confluent.schemaregistry.serializers import MessageSerializer
from datetime import datetime
from django.utils.timezone import now as tz_now
import gevent
import signal
from time import mktime

from pykafka import KafkaClient
from pykafka.partitioners import RandomPartitioner, hashing_partitioner

from jangl_utils import logger, sentry
from jangl_utils.backend_api import get_service_url
from jangl_utils.kafka import settings, utils
from jangl_utils.kafka.schemas import Schema


__all__ = ['Producer', 'HashedPartitionProducer']


class Producer(object):
    """Kafka message producer with avro schema registry support

    Requires the following configuration:
    - topic_name: The kafka topic name which to produce the messages
    - key_schema: The Avro schema file to encode the message key
    - value_schema: The Avro schema file to encode the message value

    Optional:
    - producer_name: The group name used for monitoring the producer
    - producer_settings: A dict of kafka settings to overwrite the defaults
    - has_key: Whether or not the topic has a key
    - async: Messages are queued if async is True, otherwise messages send immediately
    - poll_wait: The amount of time to wait for a response if queue is full

    Methods:
    - send_message: Sends a single message to Kafka
        send_message(key, message)
        send_message(message)

    - send_messages: Sends a batch of messages to Kafka
        send_messages([(key1, message1), (key2, message2)])
        send_messages([message1, message2])

    - get_timestamp: Will return a kafka-ready timestamp integer, defaults to now
    """
    topic_name = None
    key_schema = None
    value_schema = None
    producer_name = None
    producer_settings = {}
    has_key = False
    async = True
    poll_wait = 1

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        client = KafkaClient(**self.get_client_settings())
        topic = client.topics[self.get_topic_name()]
        self.producer = topic.get_producer(**self.get_producer_settings())
        self.serializer = self.get_message_serializer()
        self.key_schema = self.get_key_schema()
        self.value_schema = self.get_value_schema()
        gevent.signal(signal.SIGTERM, self.stop)

    def get_client_settings(self):
        return {
            'hosts': utils.get_broker_url(),
            'use_greenlets': True,
        }

    def get_producer_settings(self):
        initial_settings = {
            'partitioner': self.get_partitioner(),
            'retry_backoff_ms': 100,
            'required_acks': 1,
            'ack_timeout_ms': 5000,
            'max_queued_messages': 100000,
            'min_queued_messages': 1000,
            'linger_ms': 250,
            'block_on_queue_full': True,
            'max_request_size': 1000012,
            'sync': not self.async,
        }
        initial_settings.update(self.producer_settings)
        return initial_settings

    def get_partitioner(self):
        return RandomPartitioner()

    def get_topic_name(self):
        topic_name = self.kwargs.get('topic_name') or self.topic_name
        if topic_name is None:
            raise NotImplementedError
        return topic_name

    def get_broker_url(self):
        broker_url = self.kwargs.get('broker_url') or settings.BROKER_URL
        if broker_url is None:
            raise NotImplementedError
        return broker_url

    def get_producer_name(self):
        producer_name = self.kwargs.get('producer_name') or self.producer_name
        if producer_name is None:
            producer_name = self.__class__.__name__
        return producer_name

    def get_message_serializer(self):
        schema_registry_url = self.get_schema_registry_url()
        logger.debug('loading schema registry: ' + schema_registry_url)
        schema_client = CachedSchemaRegistryClient(url=schema_registry_url)
        return MessageSerializer(schema_client)

    def get_schema_registry_url(self):
        schema_microservice = self.kwargs.get('schema_registry_microservice') or settings.SCHEMA_MICROSERVICE
        if schema_microservice:
            return get_service_url(schema_microservice)

        schema_registry_url = self.kwargs.get('schema_registry_url') or settings.SCHEMA_REGISTRY_URL
        if schema_registry_url is None:
            raise NotImplementedError
        return schema_registry_url

    def get_key_schema(self):
        if self.has_key:
            return Schema(self, self.get_key_schema_name(), self.key_schema)

    def get_value_schema(self):
        return Schema(self, self.get_value_schema_name(), self.value_schema)

    def get_key_schema_name(self):
        return self.kwargs.get('key_schema') or (self.get_topic_name() + '-key')

    def get_value_schema_name(self):
        return self.kwargs.get('value_schema') or (self.get_topic_name() + '-value')

    def get_timestamp(self, timestamp=None):
        if timestamp is None:
            timestamp = tz_now()
        if isinstance(timestamp, datetime):
            timestamp = mktime(timestamp.timetuple()) + (timestamp.microsecond / 1e6)
        return timestamp

    def send_messages(self, messages, **kwargs):
        """ Send a batch of messages to kafka

        If the topic has a key, this method will accept only a list of (key, message) tuples:
        - self.send_message([(key, message), (key, message), ...], **kwargs)

        If the topic does not have a key, this method will only accept a list of messages:
        - self.send_message([message, message, ...], **kwargs)

        Accepts the following kwargs:
        - async: If async is False, producer will send the batch of messages immediately
        - partition: The partition id to produce to
        - callback: Delivery callback with signature on_delivery(err,msg)
        """
        for message in messages:
            self.send_message(message, **kwargs)

    def send_message(self, *args, **kwargs):
        """ Send a message to kafka

        If the topic has a key, this method accepts the following signatures:
        - self.send_message(key, message, **kwargs)
        - self.send_message((key, message), **kwargs)
        - self.send_message(key='', message='', **kwargs)

        If the topic does not have a key, this method accepts:
        - self.send_message(message, **kwargs)

        Accepts the following kwargs:
        - async: If async is False, producer will send message immediately
        - partition: The partition id to produce to
        - callback: Delivery callback with signature on_delivery(err,msg)
        """
        if self.has_key:
            if len(args) == 0:
                key = kwargs.pop('key')
                message = kwargs.pop('message')
            elif len(args) == 1:  # [(key, message)]
                key, message = args[0]
            elif len(args) == 2:  # [key, message]
                key, message = args
            else:
                raise ValueError('Invalid message format')

            logger.info('### Sending kafka message ###\n'
                        'key: {}\n'
                        'message: {}'.format(key, message))

            encoded_key = self.key_schema.encode_message(key)
            encoded_message = self.value_schema.encode_message(message)

            logger.debug('key encoded w/ schema #{}: {}'.format(self.key_schema.schema_id, encoded_key))
            logger.debug('message encoded w/ schema #{}: {}'.format(self.value_schema.schema_id, encoded_message))

            self.produce(encoded_message, key=encoded_key, **kwargs)

        elif len(args) == 1:
            message = args[0]
            logger.info('### Sending kafka message ###\n'
                        'message: {}'.format(message))

            encoded_message = self.value_schema.encode_message(message)
            logger.debug('message encoded w/ schema #{}: {}'.format(self.value_schema.schema_id, encoded_message))

            self.produce(encoded_message, **kwargs)

        else:
            raise ValueError('Invalid message format')

    def produce(self, value, key=None, timestamp=None):
        self.producer.produce(value, key, timestamp)

    def stop(self, *args):
        self.producer.stop()


class HashedPartitionProducer(Producer):
    has_key = True

    def get_partitioner(self):
        return hashing_partitioner
