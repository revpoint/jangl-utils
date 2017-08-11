import inspect
import logging

__all__ = ['debug', 'info', 'warning', 'warn', 'error',
           'exception', 'critical', 'fatal', 'log']


def _log(level, *args, **kwargs):
    """Use the logger from the caller's module"""
    frame = inspect.stack()[2]
    module = inspect.getmodule(frame[0])
    logger = logging.getLogger(module.__name__)
    logger.log(level, *args, **kwargs)


def debug(*args, **kwargs):
    _log(logging.DEBUG, *args, **kwargs)


def info(*args, **kwargs):
    _log(logging.INFO, *args, **kwargs)


def warning(*args, **kwargs):
    _log(logging.WARNING, *args, **kwargs)


warn = warning


def error(*args, **kwargs):
    _log(logging.ERROR, *args, **kwargs)


def exception(*args, **kwargs):
    kwargs['exc_info'] = 1
    _log(logging.ERROR, *args, **kwargs)


def critical(*args, **kwargs):
    _log(logging.CRITICAL, *args, **kwargs)


fatal = critical


def log(level, *args, **kwargs):
    _log(level, *args, **kwargs)
