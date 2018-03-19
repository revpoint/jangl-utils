from __future__ import absolute_import

import datetime
import json

import decimal
import uuid
from types import MethodType

from jangl_utils import timezone

DATE_FMT = '%Y-%m-%d'
ISO8601_FMT = '%Y-%m-%dT%H:%M:%S.%fZ'


def datetime_decoder(dict_):
    for key, value in dict_.iteritems():
        if value == '':
            dict_[key] = u''
            continue

        try:
            datetime_obj = datetime.datetime.strptime(value, ISO8601_FMT)
            datetime_obj = timezone.make_aware(datetime_obj)
            dict_[key] = datetime_obj
        except (ValueError, TypeError):
            try:
                date_obj = datetime.datetime.strptime(value, DATE_FMT)
                dict_[key] = date_obj.date()
            except (ValueError, TypeError):
                continue

    return dict_


def decode_json_response_hook(response, *args, **kwargs):
    def json(self, **kw):
        kw['object_hook'] = datetime_decoder
        return self._json(**kw)

    response._json = response.json
    response.json = MethodType(json, response)
    return response


class JSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time, decimal types and UUIDs.
    """
    def default(self, o):
        try:
            # See "Date Time String Format" in the ECMA-262 specification.
            if isinstance(o, datetime.datetime):
                r = o.isoformat()
                if o.microsecond:
                    r = r[:23] + r[26:]
                else:
                    r = r[:19] + '.000' + r[19:]
                if r.endswith('+00:00'):
                    r = r[:-6] + 'Z'
                return r
            elif isinstance(o, datetime.date):
                return o.isoformat()
            elif isinstance(o, datetime.time):
                if timezone.is_aware(o):
                    raise ValueError("JSON can't represent timezone-aware times.")
                r = o.isoformat()
                if o.microsecond:
                    r = r[:12]
                return r
            elif isinstance(o, decimal.Decimal):
                return str(o)
            elif isinstance(o, uuid.UUID):
                return str(o)
            else:
                return super(JSONEncoder, self).default(o)
        except TypeError:
            return str(o)


def to_json(data, **kwargs):
    kwargs.setdefault('cls', JSONEncoder)
    return json.dumps(data, **kwargs)
