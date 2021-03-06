from confluent.schemaregistry.serializers import Util
from jangl_utils import logger


class Schema(object):
    schema_id = None
    schema_avro = None
    schema_version = None

    def __init__(self, producer, subject, local_schema=None):
        self.serializer = producer.serializer
        self.schema_client = producer.serializer.registry_client
        self.subject = subject
        self.local_schema = self.parse_json(local_schema)

    def parse_json(self, json):
        if json:
            return Util.parse_schema_from_string(json)

    def get_latest(self):
        self.schema_id, self.schema_avro, self.schema_version = self.schema_client.get_latest_schema(self.subject)
        if self.schema_id is None:
            self.register_schema()
        else:
            logger.info('latest schema for "{0}" - id: {1} - version: {2}'
                        .format(self.subject, self.schema_id, self.schema_version))
            logger.debug(self.schema_avro)
        return self.schema_id

    def register_schema(self, new_schema=None):
        if new_schema is None:
            new_schema = self.local_schema
        self.schema_id = self.schema_client.register(self.subject, new_schema)
        self.schema_avro = self.schema_client.get_by_id(self.schema_id)
        self.schema_version = self.schema_client.get_version(self.subject, self.schema_avro)
        logger.info('new schema for "{0}" - id: {1} - version: {2}'
                    .format(self.subject, self.schema_id, self.schema_version))
        logger.debug(self.schema_avro)

    def update_schema(self, new_schema=None):
        if new_schema is None:
            new_schema = self.local_schema
        if self.test_compatibility(new_schema) and not self.already_exists():
            self.register_schema(new_schema)

    def test_compatibility(self, new_schema=None):
        if new_schema is None:
            new_schema = self.local_schema
        return self.schema_client.test_compatibility(self.subject, new_schema)

    def already_exists(self, new_schema=None):
        if new_schema is None:
            new_schema = self.local_schema
        return self.schema_client.get_version(self.subject, new_schema) > -1

    def encode_message(self, message):
        if self.schema_id is None:
            self.get_latest()
        return self.serializer.encode_record_with_schema_id(self.schema_id, message)

    def decode_message(self, encoded):
        return self.serializer.decode_message(encoded)
