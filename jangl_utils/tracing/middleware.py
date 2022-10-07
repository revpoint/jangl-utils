from django_opentracing import OpenTracingMiddleware as BaseOpenTracingMiddleware

from jangl_utils import tracing


class OpenTracingMiddleware(BaseOpenTracingMiddleware):
    _django_tracing = None

    def __init__(self, get_response=None):
        self.get_response = get_response

    @property
    def _tracing(self):
        if self._django_tracing is None:
            if tracing.JAEGER_TRACING is None:
                return
            self._init_tracing()
            self._django_tracing = tracing.init_django_tracer()
        return self._django_tracing

    def process_view(self, *args, **kwargs):
        if self._tracing is None:
            return
        super(OpenTracingMiddleware, self).process_view(*args, **kwargs)

    def process_exception(self, request, exception):
        if self._tracing:
            self._tracing._finish_tracing(request, error=exception)

    def process_response(self, request, response):
        if self._tracing:
            self._tracing._finish_tracing(request, response)
        return response
