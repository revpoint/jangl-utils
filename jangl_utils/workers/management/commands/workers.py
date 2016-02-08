from importlib import import_module
from django.conf import settings
from django.core.management import BaseCommand, CommandError
import gevent
from jangl_utils.workers.base import worker_registry


class Command(BaseCommand):
    args = '<worker_name worker_name ...>'

    def handle(self, *worker_names, **options):
        workers = [w.spawn() for w in self.find_workers()
                   if worker_names and w.worker_name in worker_names]
        if not workers:
            raise CommandError('Could not find workers')
        try:
            gevent.joinall(workers)
        except (KeyboardInterrupt, SystemExit):
            gevent.killall(workers)

    def find_workers(self):
        for app in settings.INSTALLED_APPS:
            if app.startswith('jangl_utils'):
                continue
            package = '{0}.workers'.format(app)
            try:
                import_module(package)
            except ImportError:
                pass
        return worker_registry.registered
