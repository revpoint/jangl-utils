from functools import partial
import django
from django.db import models, router, transaction
from django.utils import six
from django.utils.functional import cached_property


if django.VERSION < (2, 0):
    from django.db.models.fields.related import ForeignRelatedObjectsDescriptor

    class DeleteAndCreateDescriptor(ForeignRelatedObjectsDescriptor):
        def __set__(self, instance, value):
            if value is None:
                return

            manager = self.__get__(instance)
            db = router.db_for_write(manager.model, instance=manager.instance)

            related_kwargs = {self.related.field.attname: instance.pk}
            create_obj = partial(manager.model, **related_kwargs)

            value = self.clean_value(value)
            with transaction.atomic(using=db, savepoint=False):
                manager.all().delete()
                if getattr(self.related.field, 'bulk_create'):
                    manager.bulk_create([create_obj(**obj) for obj in value])
                else:
                    [manager.create(**obj) for obj in value]

        def clean_value(self, value):
            if isinstance(value, six.string_types):
                value = [val.strip() for val in value.split(',') if val.strip()]
            ensure_dict = lambda v: v if isinstance(v, dict) else {self.data_field_name: v}
            return [ensure_dict(val) for val in value]

        @cached_property
        def data_field_name(self):
            if getattr(self.related.field, 'data_field_name', None):
                return self.related.field.data_field_name

            related_class = self.related.related_model._meta
            fields = list(related_class.get_fields())
            try:
                fields.remove(related_class.pk)
                fields.remove(self.related.field)
            except ValueError:
                pass

            if len(fields) == 1:
                return fields[0].attname

            raise ValueError('Cannot determine field to save data. Either set the '
                             'data_field property on the SettableForeignKey or pass '
                             'the value as a list of dicts. ex: {field_name: value}.')

else:
    from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor

    class DeleteAndCreateDescriptor(ReverseManyToOneDescriptor):
        def __get__(self, instance, cls=None):
            return super().__get__(instance, cls)

        def __set__(self, instance, value):
            if value is None:
                return

            manager = self.__get__(instance)
            db = router.db_for_write(manager.model, instance=manager.instance)

            related_kwargs = {self.field.attname: instance.pk}
            create_obj = partial(manager.model, **related_kwargs)

            value = self.clean_value(value)
            with transaction.atomic(using=db, savepoint=False):
                manager.all().delete()
                if getattr(self.field, 'bulk_create'):
                    manager.bulk_create([create_obj(**obj) for obj in value])
                else:
                    [manager.create(**obj) for obj in value]

        def clean_value(self, value):
            if isinstance(value, six.string_types):
                value = [val.strip() for val in value.split(',') if val.strip()]
            ensure_dict = lambda v: v if isinstance(v, dict) else {self.data_field_name: v}
            return [ensure_dict(val) for val in value]

        @cached_property
        def data_field_name(self):
            if getattr(self.field, 'data_field_name', None):
                return self.field.data_field_name

            related_class = self.rel.related_model._meta
            fields = list(related_class.get_fields())
            try:
                fields.remove(related_class.pk)
                fields.remove(self.field)
            except ValueError:
                pass

            if len(fields) == 1:
                return fields[0].attname

            raise ValueError('Cannot determine field to save data. Either set the '
                             'data_field property on the SettableForeignKey or pass '
                             'the value as a list of dicts. ex: {field_name: value}.')


class SettableForeignKey(models.ForeignKey):
    related_accessor_class = DeleteAndCreateDescriptor

    def __init__(self, *args, **kwargs):
        self.data_field_name = kwargs.pop('data_field', None)
        self.bulk_create = kwargs.pop('bulk_create', True)
        super(SettableForeignKey, self).__init__(*args, **kwargs)
