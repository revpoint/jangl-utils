from django.utils import six
from django.utils.encoding import force_text
from django.utils.functional import allow_lazy
from django.utils.safestring import mark_safe, SafeText
import unicodedata
import re


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
