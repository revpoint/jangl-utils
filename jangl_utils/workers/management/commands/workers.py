import importlib
import gevent
from django.conf import settings
from django.core.management import BaseCommand, CommandError

from jangl_utils.workers.base import worker_registry, kill_all_workers


class Command(BaseCommand):
    args = '<worker_name worker_name ...>'

    def add_arguments(self, parser):
        parser.add_argument('args', metavar='worker_name', nargs='+', help='Run specific workers')

    def handle(self, *worker_names, **options):
        workers = [w.spawn() for w in find_workers(worker_names)]
        if not workers:
            raise CommandError('Could not find workers')
        try:
            gevent.joinall(workers, raise_error=True)
        except:
            kill_all_workers()


def find_workers(worker_names):
    for app in settings.INSTALLED_APPS:
        if app.startswith('jangl_utils'):
            continue
        package = '{0}.workers'.format(app)
        try:
            importlib.import_module(package)
        except ImportError:
            pass

    workers = worker_registry.registered
    if worker_names:
        workers = [w for w in workers if w.worker_name in worker_names]
    return workers
