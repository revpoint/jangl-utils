from confluent_kafka import KafkaError, KafkaException
from confluent_kafka.avro import AvroConsumer
from datetime import datetime
import decimal
import gipc
import logging
from pytz import utc

from jangl_utils.backend_api import get_service_url
from jangl_utils.kafka import settings, utils
from jangl_utils.workers import BaseWorker

logger = logging.getLogger(__name__)


class KafkaConsumerLoop(object):
    @classmethod
    def spawn(cls, *args, **kwargs):
        loop = cls(*args, **kwargs)
        try:
            loop.run()
        finally:
            loop.shutdown()

    def __init__(self, worker_settings, consumer_settings, topic_name, queue):
        self.worker_settings = worker_settings
        self.consumer_settings = consumer_settings
        self.consumer = AvroConsumer(self.consumer_settings)
        self.consumer.subscribe([topic_name])
        self.queue = queue

    def shutdown(self):
        self.consumer.close()

    def run(self):
        while True:
            message = self.consumer.poll(timeout=self.worker_settings['poll_timeout'])

            if message is None:
                continue

            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    logger.info('%% %s [%d] reached end at offset %d\n' %
                                (message.topic(), message.partition(), message.offset()))
                elif message.error():
                    raise KafkaException(message.error())

            else:
                value = self.parse_message(message.value())
                self.queue.put(value)

                if self.worker_settings['commit_on_complete']:
                    self.commit()

    def commit(self):
        if not self.consumer_settings.get('enable.auto.commit'):
            self.consumer.commit(async=self.worker_settings['async_commit'])

    def parse_message(self, message):
        for field in self.worker_settings['timestamp_fields']:
            if field in message:
                try:
                    message[field] = datetime.fromtimestamp(message[field], utc)
                except ValueError:
                    try:
                        message[field] = datetime.fromtimestamp(message[field] / 1000, utc)
                    except TypeError:
                        pass
                except TypeError:
                    pass
        for field in self.worker_settings['decimal_fields']:
            if field in message:
                try:
                    message[field] = decimal.Decimal(message[field])
                except (TypeError, decimal.InvalidOperation):
                    pass
        for field in self.worker_settings['boolean_fields']:
            if field in message:
                try:
                    message[field] = bool(message[field])
                except TypeError:
                    pass
        return message


class KafkaConsumerWorker(BaseWorker):
    topic_name = None
    consumer_name = None
    consumer_settings = {}
    commit_on_complete = True
    async_commit = True
    poll_timeout = 1
    sleep_time = 0
    timestamp_fields = ['timestamp']
    decimal_fields = []
    boolean_fields = []

    def setup(self):
        self.queue_read, self.queue_write = gipc.pipe()
        self.consumer = gipc.start_process(target=KafkaConsumerLoop.spawn,
                                           args=(self.get_worker_settings(),
                                                 self.get_consumer_settings(),
                                                 self.get_topic_name(),
                                                 self.queue_write))

    def teardown(self):
        self.consumer.terminate()
        self.consumer.join()
        self.queue_read.close()
        self.queue_write.close()

    def get_worker_settings(self):
        return {
            'commit_on_complete': self.commit_on_complete,
            'async_commit': self.async_commit,
            'poll_timeout': self.poll_timeout,
            'sleep_time': self.sleep_time,
            'timestamp_fields': self.timestamp_fields,
            'decimal_fields': self.decimal_fields,
            'boolean_fields': self.boolean_fields,
        }

    def get_consumer_settings(self):
        initial_settings = {
            'api.version.request': True,
            'broker.version.fallback': '0.9.0',
            'client.id': 'JanglConsumer',
            'bootstrap.servers': self.get_broker_url(),
            'group.id': self.get_consumer_name(),
            'default.topic.config': {'auto.offset.reset': 'earliest'},
            'enable.auto.commit': False,
            'session.timeout.ms': 10000,
            'heartbeat.interval.ms': 1000,
            'schema.registry.url': self.get_schema_registry_url(),
        }
        return utils.generate_client_settings(initial_settings, self.consumer_settings)

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
        if self.consumer.is_alive():
            self.consume_message(self.queue_read.get())
            self.done()
        else:
            raise KafkaException(KafkaError._FAIL)

    def consume_message(self, message):
        pass
