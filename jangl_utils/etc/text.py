from django.utils import six
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe, SafeText
import decimal
import unicodedata
import re

from jangl_utils._compat import allow_lazy


def slugify(value):
    """
    Converts to ASCII. Converts spaces to hyphens. Removes characters that
    aren't alphanumerics, underscores, or hyphens. Converts to lowercase.
    Also strips leading and trailing whitespace.
    """
    value = force_text(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return mark_safe(re.sub('[-\s]+', '_', value))
slugify = allow_lazy(slugify, six.text_type, SafeText)


def _clean_number(value):
    if isinstance(value, six.string_types):
        try:
            value = decimal.Decimal(value)
        except decimal.InvalidOperation:
            pass
    return value


def format_percent(value):
    if value is None:
        return ''
    return '{:0.2f}%'.format(value)


def format_dollars(value):
    if value is None:
        return ''

    value = _clean_number(value)
    if isinstance(value, (int, float, decimal.Decimal)):
        negative = '-' if value < 0 else ''
        return '{}${:0.2f}'.format(negative, abs(value))

    return value


def format_time(value):
    if value is None:
        return ''

    value = _clean_number(value)
    if isinstance(value, (int, float, decimal.Decimal)):
        value = int(value)
        mins = value / 60
        secs = value % 60
        return '{:01d}:{:02d}'.format(mins, secs)

    return value
