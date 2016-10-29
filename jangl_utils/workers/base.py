import gevent
import logging
import signal
from jangl_utils import sentry

logger = logging.getLogger(__name__)


class WorkerAttemptFailed(Exception):
    def __init__(self, worker_class, attempt, original_exc):
        self.worker_class = worker_class
        self.attempt = attempt
        self.original_exc = original_exc

    def attempt_worker(self):
        return self.worker_class.spawn(attempt=self.attempt).get()


class BaseWorker(object):
    sleep_time = 5
    max_attempts = 3
    worker_name = None

    @classmethod
    def spawn(cls, **kwargs):
        """Starts the workers main loop."""
        self = cls(**kwargs)
        self.start()
        return self.thread

    def __init__(self, attempt=0, **kwargs):
        self.attempt = attempt + 1
        self.kwargs = kwargs
        self.logger = logger

    def __repr__(self):
        return '<worker.{worker_name} - Attempt: {attempt}>'.format(
            worker_name=self.worker_name or self.__class__.__name__,
            attempt=self.attempt,
        )

    def start(self):
        self.thread = gevent.spawn(self.run)
        gevent.signal(signal.SIGTERM, self.thread.kill)

    def run(self):
        logger.info('run: attempt %d - %s', self.attempt, gevent.getcurrent())
        # Wrap main try block to catch failed attempt and call teardown before next attempt
        try:
            try:
                self.setup()
                while True:
                    self.handle()
            except (KeyboardInterrupt, SystemExit, gevent.GreenletExit):
                logger.warning('greenlet exit %s', gevent.getcurrent())
            except Exception as exc:
                logger.error('Unrecoverable error %s: %r', gevent.getcurrent(), exc, exc_info=True)
                sentry.captureException()
                if self.attempt < self.max_attempts:
                    exc = WorkerAttemptFailed(self.__class__, self.attempt, original_exc=exc)
                raise exc
            finally:
                logger.warning('tearing down greenlet %s', gevent.getcurrent())
                with sentry.capture_on_error(raise_error=False):
                    self.teardown()

        except WorkerAttemptFailed, exc:
            self.wait()
            exc.attempt_worker()

    def wait(self):
        gevent.sleep(self.sleep_time)

    def done(self):
        gevent.sleep(0)

    def setup(self):
        pass

    def handle(self):
        pass

    def teardown(self):
        pass


class WorkerRegistry(object):
    registered = []

    def register(self, registry, num_workers=1):
        if not issubclass(registry, BaseWorker):
            raise ValueError
        self.registered.extend([registry] * num_workers)

    def unregister(self, section):
        self.registered.remove(section)

worker_registry = WorkerRegistry()
