from datetime import datetime
import logging
from confluent.schemaregistry.client import CachedSchemaRegistryClient
from confluent.schemaregistry.serializers import MessageSerializer
from pykafka import KafkaClient
from pytz import utc
from jangl_utils.backend_api import get_service_url
from jangl_utils.kafka import settings
from jangl_utils.workers import BaseWorker

logger = logging.getLogger(__name__)


class KafkaConsumerWorker(BaseWorker):
    client_settings = {'use_greenlets': True}
    topic_name = None
    consumer_name = None
    consumer_settings = {}
    commit_on_complete = True
    timestamp_fields = ['timestamp']

    def setup(self):
        # Set kafka url and client
        self.broker_url = self.get_broker_url()
        logger.debug('connecting to kafka with url: ' + self.broker_url)
        self.kafka_client = KafkaClient(hosts=self.broker_url, **self.client_settings)

        # Set topic name
        self.topic_name = self.get_topic_name()
        logger.debug('set kafka topic to: ' + self.topic_name)

        # Set topic
        assert self.topic_name in self.kafka_client.topics, \
            'Cannot find kafka topic "{0}". Please create topic.'.format(self.topic_name)
        self.topic = self.kafka_client.topics[self.topic_name]

        # Set consumer
        consumer_name = self.get_consumer_name()
        logger.debug('loading consumer: ' + consumer_name)
        self.consumer = self.topic.get_balanced_consumer(consumer_name, managed=True,
                                                         **self.consumer_settings)

        # Set schema registry
        schema_registry_url = self.get_schema_registry_url()
        logger.debug('loading schema registry with url: ' + schema_registry_url)
        self.schema_client = CachedSchemaRegistryClient(url=schema_registry_url)
        self.serializer = MessageSerializer(self.schema_client)

    def teardown(self):
        self.consumer.stop()

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

    def get_schema_registry_url(self):
        schema_microservice = settings.SCHEMA_MICROSERVICE
        if schema_microservice:
            schema_registry_url = get_service_url(schema_microservice)
        else:
            schema_registry_url = settings.SCHEMA_REGISTRY_URL
        if schema_registry_url is None:
            raise NotImplementedError
        return schema_registry_url

    def handle(self):
        message = self.consumer.consume()
        if message is not None:
            offset = message.offset
            message = OffsetMessage(self.serializer.decode_message(message.value))
            message.offset = offset
            message = self.parse_message(message)

            self.consume_message(message)

            if self.commit_on_complete:
                self.commit()
        else:
            self.wait()

    def parse_message(self, message):
        for field in self.timestamp_fields:
            if field in message:
                try:
                    message[field] = datetime.fromtimestamp(message[field], utc)
                except TypeError:
                    pass
        return message

    def commit(self):
        if not self.consumer_settings.get('auto_commit_enable'):
            self.consumer.commit_offsets()

    def consume_message(self, message):
        pass


class OffsetMessage(dict):
    offset = None

