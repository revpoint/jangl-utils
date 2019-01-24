from django.conf import settings
from jaeger_client import Config
from opentracing_instrumentation.client_hooks import install_all_patches

from jangl_utils import logger
from jangl_utils.tracing.tracer import DjangoTracer

JAEGER_ENABLED = getattr(settings, 'JAEGER_ENABLED', False)
JAEGER_SERVICE_NAME = getattr(settings, 'JAEGER_SERVICE_NAME', 'jangl-python')
JAEGER_SAMPLING_TYPE = getattr(settings, 'JAEGER_SAMPLING_TYPE', 'const')
JAEGER_SAMPLING_PARAM = getattr(settings, 'JAEGER_SAMPLING_PARAM', '1')
JAEGER_AGENT_HOST = getattr(settings, 'JAEGER_AGENT_HOST', 'localhost')
JAEGER_LOGGING_ENABLED = getattr(settings, 'JAEGER_LOGGING_ENABLED', True)

JAEGER_TRACER = None


def init_jaeger_tracer():
    if JAEGER_ENABLED is False:
        return
    logger.info('Initializing Jaeger tracer')
    config = Config({
        'service_name': JAEGER_SERVICE_NAME,
        'sampler': {
            'type': JAEGER_SAMPLING_TYPE,
            'param': JAEGER_SAMPLING_PARAM,
        },
        'local_agent': {
            'reporting_host': JAEGER_AGENT_HOST,
        },
        'logging': JAEGER_LOGGING_ENABLED,
    }, validate=True)
    global JAEGER_TRACER
    JAEGER_TRACER = config.initialize_tracer()


def init_django_tracer():
    if getattr(settings, 'OPENTRACING_TRACER', None) is None:
        settings.OPENTRACING_TRACER = DjangoTracer(JAEGER_TRACER)
    return getattr(settings, 'OPENTRACING_TRACER', None)


def init_tracing():
    if JAEGER_ENABLED:
        init_jaeger_tracer()
        init_django_tracer()
        install_all_patches()


def init_tracing_postfork():
    from uwsgidecorators import postfork

    @postfork
    def tracing_postfork():
        if JAEGER_ENABLED:
            init_jaeger_tracer()
            install_all_patches()
    settings.OPENTRACING_TRACER = None
