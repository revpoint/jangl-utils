import logging
from confluent.schemaregistry.client import CachedSchemaRegistryClient
from confluent.schemaregistry.serializers import MessageSerializer
from confluent_kafka import Producer as _Producer, KafkaError, KafkaException
from datetime import datetime
from django.utils.timezone import now as tz_now
import signal
from time import mktime
from jangl_utils import sentry
from jangl_utils.backend_api import get_service_url
from jangl_utils.kafka import settings
from jangl_utils.kafka.schemas import Schema
from jangl_utils.kafka.utils import generate_client_settings

logger = logging.getLogger(__name__)


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
        self.producer = _Producer(**self.get_producer_settings())
        self.serializer = self.get_message_serializer()
        self.topic_name = self.get_topic_name()
        self.key_schema = self.get_key_schema()
        self.value_schema = self.get_value_schema()
        signal.signal(signal.SIGTERM, self._flush)

    def get_producer_settings(self):
        broker_url = self.get_broker_url()
        logger.debug('connecting to kafka with url: ' + broker_url)

        producer_name = self.get_producer_name()
        logger.debug('using group id: ' + producer_name)

        initial_settings = {
            'api.version.request': True,
            'broker.version.fallback': '0.9.0',
            'client.id': 'JanglProducer',
            'bootstrap.servers': broker_url,
            'group.id': producer_name,
            'default.topic.config': {
                'request.required.acks': 1,
                'request.timeout.ms': 5000,
                'message.timeout.ms': 60000,
                'produce.offset.report': False,
            },
            'queue.buffering.max.messages': 100000,
            'queue.buffering.max.ms': 1000,
            'message.send.max.retries': 2,
            'retry.backoff.ms': 100,
            'compression.codec': 'none',
            'batch.num.messages': 1000,
            'delivery.report.only.error': False,
        }
        return generate_client_settings(initial_settings, self.producer_settings)

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
        async = kwargs.pop('async', self.async)
        try:
            for message in messages:
                self.send_message(message, async=True, **kwargs)
        finally:
            if not async:
                self._flush()

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
        async = kwargs.pop('async', self.async)

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

            self._produce(encoded_message, key=encoded_key, **kwargs)

        elif len(args) == 1:
            message = args[0]
            logger.info('### Sending kafka message ###\n'
                        'message: {}'.format(message))

            encoded_message = self.value_schema.encode_message(message)
            logger.debug('message encoded w/ schema #{}: {}'.format(self.value_schema.schema_id, encoded_message))

            self._produce(encoded_message, **kwargs)

        else:
            raise ValueError('Invalid message format')

        if not async:
            self._flush()

    def _produce(self, value, key=None, **kwargs):
        try:
            self.producer.produce(self.topic_name, value, key, **kwargs)
        except KafkaException as exc:
            logger.error('producer failed: {}'.format(exc))
            sentry.captureException()
        except BufferError:
            self.producer.poll(self.poll_wait)
            self._produce(value, key, **kwargs)

    def _flush(self):
        self.producer.flush()


class HashedPartitionProducer(Producer):
    has_key = True
