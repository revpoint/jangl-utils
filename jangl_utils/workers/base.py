import sys
import gevent
from greenlet import GreenletExit
import logging
import signal
from jangl_utils import sentry

logger = logging.getLogger(__name__)


class BaseWorker(object):
    sleep_time = 5
    attempt = 0
    worker_name = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.logger = logger

    def wait(self):
        gevent.sleep(self.sleep_time)

    def done(self):
        gevent.sleep(0)

    def run(self):
        self.attempt += 1
        logger.info('run: attempt %d - %s', self.attempt, gevent.getcurrent())
        try:
            while True:
                self.handle()
        except (KeyboardInterrupt, SystemExit, GreenletExit):
            logger.info('greenlet exit %s', gevent.getcurrent())
            self.teardown()
            sys.exit(0)
        except Exception as exc:
            logger.error('Unrecoverable error %s: %r', gevent.getcurrent(), exc, exc_info=True)
            sentry.captureException()

            if self.attempt < 2:
                self.wait()
                self.start_decrease_attempt_timer()
                self.run()
            else:
                self.teardown()
                sys.exit(1)

    def start_decrease_attempt_timer(self):
        seconds = 30 * (2 ** self.attempt)
        gevent.spawn_later(seconds, self.decrease_attempt)
        logger.info('set decrease timer: %d seconds - %s', seconds, gevent.getcurrent())

    def decrease_attempt(self):
        self.attempt -= 1
        logger.info('attempt decreased: attempt %d - %s', self.attempt, gevent.getcurrent())

    def handle(self):
        pass

    def setup(self):
        pass

    def teardown(self):
        pass

    def start(self):
        with sentry.capture_on_error():
            self.setup()
        self.thread = gevent.spawn(self.run)
        self.thread.link(self.end)
        gevent.signal(signal.SIGTERM, self.thread.kill)

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
