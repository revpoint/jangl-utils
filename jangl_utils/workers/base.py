import sys
from django.conf import settings
import gevent
from greenlet import GreenletExit
import logging
import signal

logger = logging.getLogger(__name__)


class BaseWorker(object):
    sleep_time = 5
    attempt = 0

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.logger = logger

    def wait(self):
        gevent.sleep(self.sleep_time)

    def done(self):
        gevent.sleep(0)

    def run(self):
        self.attempt += 1
        logger.info(gevent.getcurrent())
        logger.info('run: attempt {0}'.format(self.attempt))
        try:
            while True:
                self.handle()
        except (KeyboardInterrupt, SystemExit, GreenletExit):
            logger.info(gevent.getcurrent())
            logger.info('greenlet exit')
        except Exception as exc:
            logger.error(gevent.getcurrent())
            logger.error('Unrecoverable error: %r', exc, exc_info=True)
            if getattr(settings, 'SENTRY_URL'):
                try:
                    from raven.contrib.django.models import get_client
                except ImportError:
                    pass
                else:
                    get_client().captureException()

            if self.attempt < 2:
                self.wait()
                self.run()
                self.start_decrease_attempt_timer()
            else:
                sys.exit(1)

    def start_decrease_attempt_timer(self):
        seconds = 30 * (2 ** self.attempt)
        gevent.spawn_later(seconds, self.decrease_attempt)

    def decrease_attempt(self):
        self.attempt -= 1

    def handle(self):
        pass

    def setup(self):
        pass

    def teardown(self):
        pass

    def start(self):
        gevent.signal(signal.SIGTERM, gevent.kill)
        self.setup()
        self.thread = gevent.spawn(self.run)
        self.thread.link(self.end)

    def end(self, greenlet):
        self.teardown()

    @classmethod
    def spawn(cls, **kwargs):
        """Starts the workers main loop."""
        self = cls(**kwargs)
        self.start()
        return self.thread


class WorkerRegistry(object):
    registered = []

    def register(self, registry, num_workers=1):
        if not issubclass(registry, BaseWorker):
            raise ValueError
        self.registered.extend([registry] * num_workers)

    def unregister(self, section):
        self.registered.remove(section)

worker_registry = WorkerRegistry()
