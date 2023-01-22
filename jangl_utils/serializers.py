import json
import re
from django.utils import six
from rest_framework import serializers

phone_digits_re = re.compile(r'^(?:\+?1-?)?(\d{3})[-\.]?(\d{3})[-\.]?(\d{4})$')


class PhoneNumberField(serializers.CharField):
    def __init__(self, **kwargs):
        super(PhoneNumberField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        data = super(PhoneNumberField, self).to_internal_value(data)
        p = phone_digits_re.search(data)
        if not p:
            raise serializers.ValidationError('Invalid phone number <{}>'.format(data))
        return '+1%s%s%s' % (p.group(1), p.group(2), p.group(3))


class JSONCaptureField(serializers.CharField):
    def to_representation(self, value):
        return json.loads(value)

    def to_internal_value(self, data):
        if isinstance(data, six.string_types):
            return data
        try:
            val = json.dumps(data)
        except TypeError:
            raise serializers.ValidationError('Could not load json <{}>'.format(data))
        return val.decode('utf8')
