from django_opentracing import OpenTracingMiddleware

from jangl_utils import tracing


class JaegerOpenTracingMiddleware(OpenTracingMiddleware):
    _django_tracer = None

    def __init__(self, get_response=None):
        self.get_response = get_response

    @property
    def _tracing(self):
        if self._django_tracer is None:
            if tracing.JAEGER_TRACER is None:
                return
            self._django_tracer = tracing.init_django_tracer()
        return self._django_tracer

    def process_view(self, *args, **kwargs):
        if self._tracing is None:
            return
        super(JaegerOpenTracingMiddleware, self).process_view(*args, **kwargs)

    def process_exception(self, request, exception):
        if self._tracing:
            self._tracing._finish_tracing(request, error=exception)

    def process_response(self, request, response):
        if self._tracing:
            self._tracing._finish_tracing(request, response)
        return response
