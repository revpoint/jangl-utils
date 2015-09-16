from datetime import datetime
from confluent.schemaregistry.client import CachedSchemaRegistryClient
from confluent.schemaregistry.serializers import MessageSerializer
from django.conf import settings
import gevent
from greenlet import GreenletExit
import logging
from pykafka import KafkaClient
from raven.contrib.django.models import get_client
import signal

logger = logging.getLogger(__name__)


class BaseWorker(object):
    sleep_time = 5

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.logger = logger

    def wait(self):
        gevent.sleep(self.sleep_time)

    def done(self):
        gevent.sleep(0)

    def run(self, attempt=0):
        logger.info(gevent.getcurrent())
        logger.info('run: attempt {0}'.format(attempt + 1))
        try:
            while True:
                self.handle()
        except (KeyboardInterrupt, SystemExit, GreenletExit):
            logger.info(gevent.getcurrent())
            logger.info('greenlet exit')
        except Exception as exc:
            logger.error(gevent.getcurrent())
            logger.error('Unrecoverable error: %r', exc, exc_info=True)
            if getattr(settings, 'SENTRY_URL'):
                get_client().captureException()

            if attempt < 2:
                self.wait()
                self.run(attempt+1)
            else:
                raise

    def handle(self):
        pass

    def setup(self):
        pass

    def teardown(self):
        pass

    def start(self):
        gevent.signal(signal.SIGTERM, gevent.kill)
        self.setup()
        self.thread = gevent.spawn(self.run)
        self.thread.link(self.end)

    def end(self, greenlet):
        self.teardown()

    @classmethod
    def spawn(cls, **kwargs):
        """Starts the workers main loop."""
        self = cls(**kwargs)
        self.start()
        return self.thread


class KafkaConsumerWorker(BaseWorker):
    topic_name = None
    consumer_name = None
    commit_on_complete = True

    def setup(self):
        assert self.topic_name, 'Topic name cannot be empty'
        assert self.consumer_name, 'Consumer name cannot be empty'

        kafka_url = self.kwargs.get('kafka_url', getattr(settings, 'KAFKA_URL'))
        self.kafka_client = KafkaClient(hosts=kafka_url)

        assert self.topic_name in self.kafka_client.topics, \
            'Cannot find kafka topic "{0}".'.format(self.topic_name)
        self.topic = self.kafka_client.topics[self.topic_name]

        zookeeper_url = self.kwargs.get('zookeeper_url', getattr(settings, 'ZOOKEEPER_URL'))
        self.consumer = self.topic.get_balanced_consumer(self.consumer_name,
                                                         zookeeper_connect=zookeeper_url)

        schema_registry_url = self.kwargs.get('schema_registry_url', getattr(settings, 'SCHEMA_REGISTRY_URL'))
        schema_client = CachedSchemaRegistryClient(url=schema_registry_url)
        self.serializer = MessageSerializer(schema_client)

    def teardown(self):
        self.consumer.stop()

    def handle(self):
        message = self.consumer.consume()
        if message is not None:
            message = self.serializer.decode_message(message.value)
            message = self.parse_message(message)
            
            self.consume_message(message)

            if self.commit_on_complete:
                self.commit()
        else:
            self.wait()

    def parse_message(self, message):
        if 'timestamp' in message:
            message['timestamp'] = datetime.fromtimestamp(message['timestamp'])
        return message

    def commit(self):
        self.consumer.commit_offsets()

    def consume_message(self, message):
        pass


class WorkerRegistry(object):
    registered = []

    def register(self, registry, num_workers=1):
        if not issubclass(registry, BaseWorker):
            raise ValueError
        self.registered.extend([registry] * num_workers)

    def unregister(self, section):
        self.registered.remove(section)

worker_registry = WorkerRegistry()
