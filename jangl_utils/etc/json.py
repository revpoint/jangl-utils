import datetime
from django.conf import settings
from django.utils import timezone

DATE_FMT = '%Y-%m-%d'
ISO8601_FMT = '%Y-%m-%dT%H:%M:%S.%fZ'


def make_aware_local(dt):
    return timezone.localtime(timezone.make_aware(dt, timezone.utc))


def _datetime_decoder(dict_):
    for key, value in dict_.iteritems():
        # The built-in `json` library will `unicode` strings, except for empty
        # strings which are of type `str`. `jsondate` patches this for
        # consistency so that `unicode` is always returned.
        if value == '':
            dict_[key] = u''
            continue

        try:
            datetime_obj = datetime.datetime.strptime(value, ISO8601_FMT)
            if settings.USE_TZ:
                datetime_obj = make_aware_local(datetime_obj)
            dict_[key] = datetime_obj
        except (ValueError, TypeError):
            try:
                date_obj = datetime.datetime.strptime(value, DATE_FMT)
                if settings.USE_TZ:
                    date_obj = make_aware_local(date_obj)
                dict_[key] = date_obj.date()
            except (ValueError, TypeError):
                continue

    return dict_
