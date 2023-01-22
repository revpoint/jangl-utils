import sys
import django

PY3 = sys.version_info[0] == 3


if django.VERSION < (2, 0):
    from django.db.models.fields.related import ForeignRelatedObjectsDescriptor
else:
    from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor as ForeignRelatedObjectsDescriptor


if django.VERSION < (2, 0):
    from django.utils.functional import allow_lazy
else:
    from django.utils.functional import keep_lazy as allow_lazy
