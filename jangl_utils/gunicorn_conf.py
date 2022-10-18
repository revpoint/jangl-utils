
__all__ = ['accesslog', 'access_log_format', 'logger_class']

accesslog = '-'
access_log_format = (
    '{"uri":"%({RAW_URI}e)s","method":"%(m)s","proto":"%(H)s","host":"%({host}i)s",'
    '"status":"%(s)s","remote_addr":"%({x-forwarded-for}i)s","time":"%(t)s",'
    '"duration_us":%(D)s,"worker_pid":"%(p)s","referer":"%(f)s","uagent":"%(a)s"}'
)

try:
    from gunicorn import glogging
    import logging

    class HealthCheckFilter(logging.Filter):
        def filter(self, record):
            return '"uri":"/_hc"' not in record.getMessage()

    class HealthCheckGunicornLogger(glogging.Logger):
        def setup(self, cfg):
            super(HealthCheckGunicornLogger, self).setup(cfg)
            # Add filters to Gunicorn logger
            logger = logging.getLogger('gunicorn.access')
            logger.addFilter(HealthCheckFilter())

    logger_class = HealthCheckGunicornLogger
except ImportError:
    logger_class = None
