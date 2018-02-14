from confluent_kafka import KafkaError, KafkaException, TopicPartition, OFFSET_BEGINNING, OFFSET_END
from confluent_kafka.avro import AvroConsumer
from jangl_utils.kafka import utils
from jangl_utils.kafka._confluent.old_consumer import KafkaConsumerWorker
from jangl_utils.workers import BaseWorker

__all__ = ['KafkaWorker', 'StartAtBeginningKafkaWorker', 'StartAtEndKafkaWorker', 'MessageValue', 'KafkaConsumerWorker']


class KafkaWorker(BaseWorker):
    topic_name = None
    consumer_name = None
    consumer_settings = {}
    commit_on_complete = False
    async_commit = True
    poll_timeout = 0
    auto_offset_reset = 'earliest'
    consumer = None
    last_message = None

    def setup(self):
        self.consumer = AvroConsumer(self.get_consumer_settings())
        self.consumer.subscribe([self.get_topic_name()])

    def teardown(self):
        if self.consumer:
            self.consumer.close()

    def get_topic_name(self):
        return self.topic_name or utils.config_missing('topic name')

    def get_consumer_name(self):
        return self.consumer_name or utils.generate_random_consumer_name()

    def get_consumer_settings(self):
        initial = {
            'group.id': self.get_consumer_name(),
            'default.topic.config': {'auto.offset.reset': self.auto_offset_reset},
            'enable.auto.commit': False,
            'bootstrap.servers': utils.get_broker_url(),
            'schema.registry.url': utils.get_schema_registry_url(),
            'session.timeout.ms': 10000,
            'heartbeat.interval.ms': 1000,
        }
        return utils.generate_client_settings(initial, self.consumer_settings)

    def poll(self):
        message = self.consumer.poll(timeout=self.poll_timeout)
        if message is not None:
            self.last_message = message
        return message

    def reset_consumer_offsets(self, offset):
        self.poll()
        self.consumer.assign([TopicPartition(tp.topic, tp.partition, offset)
                              for tp in self.consumer.assignment()])

    def get_current_offsets(self):
        return self.consumer.position(self.consumer.assignment())

    def handle(self):
        message = self.poll()

        if message is None:
            self.wait()

        elif message.error():
            if message.error().code() == KafkaError._PARTITION_EOF:
                self.partition_eof(message)

            else:
                raise KafkaException(message.error())

        else:
            self.consume_message(MessageValue(message))

            if self.commit_on_complete:
                self.commit()

        self.done()

    def commit(self):
        if not self.consumer_settings.get('enable.auto.commit'):
            self.consumer.commit(async=self.async_commit)

    def consume_message(self, message):
        pass

    def partition_eof(self, message):
        pass


class StartAtBeginningKafkaWorker(KafkaWorker):
    auto_offset_reset = 'earliest'

    def setup(self):
        super(StartAtBeginningKafkaWorker, self).setup()
        self.reset_consumer_offsets(OFFSET_BEGINNING)


class StartAtEndKafkaWorker(KafkaWorker):
    auto_offset_reset = 'latest'

    def setup(self):
        super(StartAtEndKafkaWorker, self).setup()
        self.reset_consumer_offsets(OFFSET_END)


class MessageValue(object):
    def __init__(self, message):
        self._message = message
        self._value = message.value()

    def __getattr__(self, item):
        if item in ('error', 'key', 'offset', 'partition',
                    'timestamp', 'topic', 'value'):
            return getattr(self._message, item)
        return getattr(self._value, item)

    def __getitem__(self, item):
        if isinstance(self._value, (list, dict)):
            return self._value[item]


# For compatibility
KafkaConsumerWorker = KafkaConsumerWorker
