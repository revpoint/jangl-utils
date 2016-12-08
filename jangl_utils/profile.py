import cProfile
import functools
import logging
import pstats
import random

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

try:
    from django.conf import settings
    if not settings.configured:
        settings = None
except ImportError:
    settings = None

logger = logging.getLogger(__name__)


def log_cprofile(func=None, action='stats', sort='cumulative', head=20, sample_rate=1.0, callback=logger.debug):
    """Decorator to log cProfile output of a method

    :param func: Function to profile
    :param action: The profile data to output (stats, callees, callers)
    :param sort: One or more ``pstats.Stats`` sort columns (cumulative, ncalls, time, stdname, filename, ...)
    :param head: Number of lines to output
    :param sample_rate: Number between 0 and 1 that determines how often the function is profiled.
    :param callback: The callback to log the final output
    :return: If settings.ENABLE_PROFILING is or django is not installed, return a profiled function.
     Otherwise, return original function
    """
    def decorator(_func):
        @functools.wraps(_func)
        def profiled_func(*args, **kwargs):
            # If random number between 0 and 1 > sample rate, skip profiling
            if random.random() > sample_rate:
                return _func(*args, **kwargs)

            profile = cProfile.Profile()
            try:
                # Run profile
                profile.enable()
                result = _func(*args, **kwargs)
                profile.disable()
                return result
            finally:
                output = StringIO.StringIO()
                sort_args = sort if isinstance(sort, (list, tuple)) else (sort,)

                # Sort stats and print to output
                stats = pstats.Stats(profile, stream=output).sort_stats(*sort_args)
                getattr(stats, 'print_' + action)()
                log_stats = output.getvalue()
                output.close()

                # If head, get top lines
                if head and head > 0:
                    log_stats = '\n'.join(log_stats.splitlines()[:head])

                logger.info('Logging cProfile for: ' + _func.__name__)
                callback('\n' + log_stats + '\n\n')

        if settings is None or settings.ENABLE_PROFILING:
            return profiled_func
        else:
            return _func

    if func is None:
        return decorator
    return decorator(func)
