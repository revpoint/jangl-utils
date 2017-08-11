import cProfile
import functools
import logging
import pstats
import random

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from jangl_utils import logger


def log_cprofile(func=None, action='stats', head=20, sample_rate=None, sort='cumulative',
                 callback=None, log_level='debug'):
    """Decorator to log cProfile output of a method

    :param func: Function to profile
    :param action: The profile data to output (stats, callees, callers)
    :param head: Number of lines to output. None or 0 shows all lines.
    :param sort: One or more ``pstats.Stats`` sort columns (cumulative, ncalls, time, stdname, filename, ...)
    :param sample_rate: Number between 0 and 1 that determines how often the function is profiled.
    :param callback: The callback to log the final output. Default is the function's module logger
    :param log_level: The log level of the default callback
    :return: If settings.ENABLE_PROFILING or Django is not installed, return a profiled function.
     Otherwise, return original function
    """
    sort_args = sort if isinstance(sort, (list, tuple)) else (sort,)

    def decorator(_func):
        @functools.wraps(_func)
        def profiled_func(*args, **kwargs):
            # If random number between 0 and 1 > sample rate, skip profiling
            if should_not_sample(sample_rate):
                return _func(*args, **kwargs)

            profile = cProfile.Profile()
            try:
                # Run profile
                profile.enable()
                result = _func(*args, **kwargs)
                profile.disable()
                return result
            finally:
                # Sort stats and print to output
                with StringIO.StringIO() as out_buffer:
                    stats = pstats.Stats(profile, stream=out_buffer).sort_stats(*sort_args)
                    getattr(stats, 'print_' + action)()
                    output = out_buffer.getvalue()

                # If head, get top lines + 5 header lines
                if head and head > 0:
                    output = '\n'.join(output.splitlines()[:head + 5])

                logger.info('Logging cProfile for: {}({})[{}]'.format(
                    _func.__name__,
                    _func.func_code.co_filename,
                    _func.func_code.co_firstlineno
                ))

                # Send log output to handler
                log_stats = get_log_handler(_func, callback, log_level)
                log_stats('\n' + output + '\n\n')

        if profiling_is_enabled():
            return profiled_func
        else:
            return _func

    if func is None:
        return decorator
    return decorator(func)


try:
    from django.conf import settings as django_settings
    if not django_settings.configured:
        django_settings = None
except ImportError:
    django_settings = None


def profiling_is_enabled():
    if django_settings:
        return getattr(django_settings, 'ENABLE_PROFILING', False)
    return True


def should_not_sample(sample_rate):
    if sample_rate is None:
        if django_settings:
            sample_rate = getattr(django_settings, 'PROFILING_DEFAULT_SAMPLE_RATE', 1.0)
        else:
            sample_rate = 1.0

    return random.random() > sample_rate


def get_log_handler(_func, callback, log_level):
    if callback is None:
        _logger = logging.getLogger(_func.__module__)
        return getattr(_logger, log_level)
    else:
        return callback
