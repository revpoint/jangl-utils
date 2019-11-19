from confluent.schemaregistry.client import CachedSchemaRegistryClient
from confluent.schemaregistry.serializers import MessageSerializer
from confluent_kafka import Consumer, KafkaError, KafkaException
from datetime import datetime
import decimal
from pytz import utc
from jangl_utils import logger
from jangl_utils.backend_api import get_service_url
from jangl_utils.kafka import settings
from jangl_utils.kafka.utils import generate_client_settings
from jangl_utils.workers import BaseWorker


class KafkaConsumerWorker(BaseWorker):
    topic_name = None
    consumer_name = None
    consumer_settings = {}
    commit_on_complete = True
    async_commit = True
    poll_timeout = 0.01
    sleep_time = 0.05
    timestamp_fields = ['timestamp']
    decimal_fields = []
    boolean_fields = []

    def setup(self):
        self.consumer = Consumer(**self.get_consumer_settings())
        self.serializer = self.get_message_serializer()
        self.set_topic()

    def teardown(self):
        self.consumer.close()

    def get_topic_name(self):
        if self.topic_name is None:
            raise NotImplementedError
        return self.topic_name

    def get_consumer_name(self):
        if self.consumer_name is None:
            raise NotImplementedError
        return self.consumer_name

    def get_broker_url(self):
        broker_url = settings.BROKER_URL
        if broker_url is None:
            raise NotImplementedError
        return broker_url

    def get_zookeeper_url(self):
        zookeeper_url = settings.ZOOKEEPER_URL
        if zookeeper_url is None:
            raise NotImplementedError
        return zookeeper_url

    def get_consumer_settings(self):
        broker_url = self.get_broker_url()
        logger.debug('connecting to kafka: ' + broker_url)

        consumer_name = self.get_consumer_name()
        logger.debug('using group id: ' + consumer_name)

        initial_settings = {
            'api.version.request': True,
            'broker.version.fallback': '0.9.0',
            'client.id': 'JanglConsumer',
            'bootstrap.servers': broker_url,
            'group.id': consumer_name,
            'default.topic.config': {'auto.offset.reset': 'earliest'},
            'enable.auto.commit': False,
            'on_commit': self.on_commit,
            'session.timeout.ms': 10000,
            'heartbeat.interval.ms': 1000,
        }
        return generate_client_settings(initial_settings, self.consumer_settings)

    def get_message_serializer(self):
        schema_registry_url = self.get_schema_registry_url()
        logger.debug('loading schema registry: ' + schema_registry_url)
        schema_client = CachedSchemaRegistryClient(url=schema_registry_url)
        return MessageSerializer(schema_client)

    def get_schema_registry_url(self):
        schema_microservice = settings.SCHEMA_MICROSERVICE
        if schema_microservice:
            schema_registry_url = get_service_url(schema_microservice)
        else:
            schema_registry_url = settings.SCHEMA_REGISTRY_URL
        if schema_registry_url is None:
            raise NotImplementedError
        return schema_registry_url

    def set_topic(self):
        topic_name = self.get_topic_name()
        logger.debug('set kafka topic: ' + topic_name)
        self.consumer.subscribe([topic_name], on_assign=self.on_assign, on_revoke=self.on_revoke)

    def on_assign(self, consumer, partitions):
        logger.debug('partitions assigned: {}'.format(partitions))
        consumer.assign(partitions)

    def on_revoke(self, consumer, partitions):
        logger.debug('partitions revoked: {}'.format(partitions))
        try:
            consumer.commit(asynchronous=False)
        except KafkaException:
            pass
        consumer.unassign()

    def on_commit(self, err, partitions):
        if err is None:
            logger.debug('commit done: {}'.format(partitions))
        else:
            logger.error('commit error: {} - {}'.format(err, partitions))

    def handle(self):
        message = self.consumer.poll(timeout=self.poll_timeout)

        if message is not None:
            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    logger.info('%% %s [%d] reached end at offset %d\n' %
                                (message.topic(), message.partition(), message.offset()))
                elif message.error():
                    raise KafkaException(message.error())
            else:
                message = DecodedMessage(self.serializer, message)
                message = self.parse_message(message)

                self.consume_message(message)

                if self.commit_on_complete:
                    self.commit()
            self.done()
        else:
            self.wait()

    def parse_message(self, message):
        for field in self.timestamp_fields:
            if field in message:
                try:
                    message[field] = datetime.fromtimestamp(message[field], utc)
                except ValueError:
                    try:
                        message[field] = datetime.fromtimestamp(message[field]/1000, utc)
                    except TypeError:
                        pass
                except TypeError:
                    pass
        for field in self.decimal_fields:
            if field in message:
                try:
                    message[field] = decimal.Decimal(message[field])
                except (TypeError, decimal.InvalidOperation):
                    pass
        for field in self.boolean_fields:
            if field in message:
                try:
                    message[field] = bool(message[field])
                except TypeError:
                    pass
        return message

    def commit(self):
        if not self.consumer_settings.get('enable.auto.commit'):
            self.consumer.commit(asynchronous=self.async_commit)

    def consume_message(self, message):
        pass


class DecodedMessage(dict):
    key = None
    offset = None
    partition = None
    topic = None
    value = None

    def __init__(self, serializer, message):
        self.key = message.key()
        self.offset = message.offset()
        self.partition = message.partition()
        self.topic = message.topic()
        self.value = message.value()
        super(DecodedMessage, self).__init__(serializer.decode_message(self.value))
