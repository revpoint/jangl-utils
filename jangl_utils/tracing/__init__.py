from django.conf import settings
from django_opentracing import DjangoTracing
from jaeger_client import Config
from opentracing_instrumentation.client_hooks import install_all_patches

from jangl_utils import logger
from jangl_utils.tracing.functions import func_span, traced_function

JAEGER_ENABLED = getattr(settings, 'JAEGER_ENABLED', False)
JAEGER_SERVICE_NAME = getattr(settings, 'JAEGER_SERVICE_NAME', 'jangl-python')
JAEGER_SAMPLING_TYPE = getattr(settings, 'JAEGER_SAMPLING_TYPE', 'const')
JAEGER_SAMPLING_PARAM = getattr(settings, 'JAEGER_SAMPLING_PARAM', '1')
JAEGER_AGENT_HOST = getattr(settings, 'JAEGER_AGENT_HOST', 'localhost')
JAEGER_LOGGING_ENABLED = getattr(settings, 'JAEGER_LOGGING_ENABLED', True)

JAEGER_TRACING = None


def init_jaeger_tracer(**kwargs):
    logger.info('Initializing Jaeger tracer')
    config = {
        'service_name': JAEGER_SERVICE_NAME,
        'sampler': {
            'type': JAEGER_SAMPLING_TYPE,
            'param': JAEGER_SAMPLING_PARAM,
        },
        'local_agent': {
            'reporting_host': JAEGER_AGENT_HOST,
        },
        'logging': JAEGER_LOGGING_ENABLED,
    }
    kwargs.setdefault('propagation', 'b3')
    kwargs.setdefault('generate_128bit_trace_id', True)
    config.update(kwargs)
    global JAEGER_TRACING
    JAEGER_TRACING = Config(config, validate=True).initialize_tracer()


def init_django_tracer():
    if getattr(settings, 'OPENTRACING_TRACING', None) is None:
        tracer = DjangoTracing(JAEGER_TRACING)
        settings.OPENTRACING_TRACING = tracer
        settings.OPENTRACING_TRACER = tracer
    return getattr(settings, 'OPENTRACING_TRACING', None)


def install_custom_patches():
    from jangl_utils.tracing import greenlet
    from jangl_utils.tracing import kafka_consumer
    from jangl_utils.tracing import kafka_producer

    greenlet.install_patches()
    kafka_consumer.install_patches()
    kafka_producer.install_patches()


def init_tracing():
    if JAEGER_ENABLED:
        init_jaeger_tracer()
        init_django_tracer()
        install_all_patches()
        install_custom_patches()


def init_tracing_postfork():
    if JAEGER_ENABLED:
        init_jaeger_tracer()
        install_all_patches()
        install_custom_patches()


def init_tracing_postfork_uwsgi():
    # from uwsgidecorators import postfork
    #
    # @postfork
    # def tracing_postfork():
    #     if JAEGER_ENABLED:
    #         init_jaeger_tracer()
    #         install_all_patches()
    #         install_custom_patches()
    settings.OPENTRACING_TRACER = None
