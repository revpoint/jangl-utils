from datetime import datetime
from decimal import Decimal
from time import mktime

from django.utils import six

from jangl_utils.kafka import register_producer, Producer
from jangl_utils.timezone import now as tz_now


class TrackChangesProducer(Producer):
    topic_name = 'jangl.data.track_changes'
    value_schema = '''
    {
      "name": "TrackChanges",
      "type": "record",
      "namespace": "jangl.data",
      "fields": [
        {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"},
        {"name": "app_name", "type": "string"},
        {"name": "model", "type": "string"},
        {"name": "pk", "type": ["long", "string"]},
        {"name": "buyer_id", "type": ["null", "long"]},
        {"name": "vendor_id", "type": ["null", "long"]},
        {"name": "site_id", "type": ["null", "long"]},
        {"name": "instance", "type": "string"},
        {"name": "message", "type": "string"},
        {"name": "changes", "type": {"type": "map", "values": {
          "name": "ChangeValues",
          "type": "record",
          "fields": [
            {"name": "old", "type": ["string", "long", "double", "boolean", "null"]},
            {"name": "new", "type": ["string", "long", "double", "boolean", "null"]}
          ]
        }}}
      ]
    }
    '''

    def log_changes(self, instance, message='', **kwargs):
        message = {
            'timestamp': get_timestamp_ms(kwargs.get('timestamp')),
            'app_name': kwargs.get('app_name', self.get_app_name(instance, **kwargs)),
            'model': kwargs.get('model', self.get_model(instance)),
            'pk': instance.pk,
            'buyer_id': kwargs.get('buyer_id', getattr(instance, 'buyer_id', None)),
            'vendor_id': kwargs.get('vendor_id', getattr(instance, 'vendor_id', None)),
            'site_id': kwargs.get('site_id', getattr(instance, 'site_id', None)),
            'instance': kwargs.get('instance', six.text_type(instance)),
            'message': message,
            'changes': self.get_changes(instance),
        }
        self.send_message(message)

    def get_app_name(self, instance, **kwargs):
        return instance._meta.model.__module__.split('.')[0]

    def get_model(self, instance):
        return '.'.join([
            instance._meta.app_label,
            instance._meta.model.__name__
        ])

    def get_changes(self, instance):
        changes = instance.get_tracked_changes()
        for field in changes:
            changes[field] = dict([(k, clean_value(v)) for (k, v) in six.iteritems(changes[field])])
        return changes


def clean_value(value):
    if isinstance(value, Decimal):
        value = str(value)
    if isinstance(value, datetime):
        value = get_timestamp_ms(value)
    if value is not None and not isinstance(value, (six.text_type, int, long, float, bool)):
        value = six.text_type(value)
    return value


def get_timestamp_ms(dt=None):
    timestamp = dt or tz_now()
    if isinstance(timestamp, datetime):
        timestamp = int(mktime(timestamp.timetuple()) * 1000  # seconds
                        + timestamp.microsecond / 1e3)        # ms
    return timestamp


register_producer('track_changes', TrackChangesProducer)
