import gevent
import signal
from jangl_utils import logger, sentry


class WorkerAttemptFailed(Exception):
    def __init__(self, worker_class, attempt, original_exc):
        self.worker_class = worker_class
        self.attempt = attempt
        self.original_exc = original_exc

    def attempt_worker(self):
        return self.worker_class.spawn(attempt=self.attempt).get()


class BaseWorker(object):
    sleep_time = 0.1
    max_attempts = 3
    worker_name = None
    ready = None
    thread = None

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
        return '<{} - Attempt: {}>'.format(self.__class__.__name__, self.attempt)

    def start(self):
        self.thread = gevent.spawn(self.run)
        setup_kill_signals()

    def run(self):
        logger.info('run: attempt %d - %s', self.attempt, gevent.getcurrent())
        # Wrap main try block to catch failed attempt and call teardown before next attempt
        try:
            try:
                if self.ready is not None:
                    logger.info('{} setup waiting'.format(self.__class__.__name__))
                    while not self.ready():
                        self.wait()
                    logger.info('{} setup ready'.format(self.__class__.__name__))
                self.setup()
                while True:
                    self.handle()
                    if _KILL_ALL_WORKERS:
                        break
            except (KeyboardInterrupt, SystemExit, gevent.GreenletExit):
                pass
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

        except WorkerAttemptFailed as exc:
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


def kill_all_workers(*args):
    global _KILL_ALL_WORKERS
    _KILL_ALL_WORKERS = True
_KILL_ALL_WORKERS = False


def setup_kill_signals():
    global _signals_already_setup
    if _signals_already_setup:
        return
    gevent.signal_handler(signal.SIGTERM, kill_all_workers)
    gevent.signal_handler(signal.SIGINT, kill_all_workers)
    _signals_already_setup = True
_signals_already_setup = False


class WorkerRegistry(object):
    registered = []

    def register(self, registry, num_workers=1):
        if not issubclass(registry, BaseWorker):
            raise ValueError
        self.registered.extend([registry] * num_workers)

    def unregister(self, section):
        self.registered.remove(section)


def register_worker(cls):
    worker_registry.register(cls)
    return cls

worker_registry = WorkerRegistry()
