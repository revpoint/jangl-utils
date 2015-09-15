from importlib import import_module
from django.conf import settings
from jangl_utils.kafka import Producer


class NotRegisteredError(Exception):
    pass

class AlreadyRegisteredError(Exception):
    pass


class ProducerRegistry(object):
    registered = {}
    kwargs = {}
    initialized = {}

    def register(self, name, producer, **kwargs):
        if not issubclass(producer, Producer):
            raise ValueError
        if name in self.registered:
            raise AlreadyRegisteredError

        self.registered[name] = producer
        self.kwargs[name] = kwargs

    def unregister(self, name):
        if name not in self.registered:
            raise NotRegisteredError

        self.registered.pop(name)
        self.kwargs.pop(name)
        self.initialized.pop(name)

    def get_producer(self, name):
        if name not in self.registered:
            raise NotRegisteredError

        if name not in self.initialized:
            self.initialized[name] = self.registered[name](**self.kwargs[name])

        return self.initialized[name]


def autodiscover():
    """
    Populate the registry by iterating through every section declared in :py:const:`settings.INSTALLED_APPS`.
    """
    for app in settings.INSTALLED_APPS:
        package = '{0}.producers'.format(app)
        try:
            import_module(package)
        except ImportError:
            pass


registry = ProducerRegistry()

register_producer = registry.register
unregister_producer = registry.unregister
get_producer = registry.get_producer