import opentracing
import six
from django_opentracing import DjangoTracer as OldDjangoTracer
from opentracing.ext import tags
from opentracing_instrumentation.request_context import RequestContextManager


class DjangoTracer(OldDjangoTracer):
    def _apply_tracing(self, request, view_func, attributes):

        # strip headers for trace info
        headers = {}
        for k, v in six.iteritems(request.META):
            k = k.lower().replace('_', '-')
            if k.startswith('http-'):
                k = k[5:]
            headers[k] = v

        # start new span from trace info
        span = None
        operation_name = view_func.__name__
        try:
            span_ctx = self._tracer.extract(opentracing.Format.HTTP_HEADERS, headers)
            span = self._tracer.start_span(operation_name=operation_name, child_of=span_ctx)
        except (opentracing.InvalidCarrierException, opentracing.SpanContextCorruptedException) as e:
            span = self._tracer.start_span(operation_name=operation_name)
        if span is None:
            span = self._tracer.start_span(operation_name=operation_name)

        # add span to current spans
        self._current_spans[request] = span

        span.set_tag(tags.COMPONENT, 'django')
        span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_SERVER)
        span.set_tag(tags.HTTP_METHOD, request.method)
        span.set_tag(tags.HTTP_URL, request.get_full_path())

        # log any traced attributes
        for attr in attributes:
            if hasattr(request, attr):
                payload = str(getattr(request, attr))
                if payload:
                    span.set_tag(attr, payload)

        request.tracing_context_manager = RequestContextManager(span=span)
        request.tracing_context_manager.__enter__()
        return span

    def _finish_tracing(self, request, response=None, error=None):
        span = self._current_spans.pop(request, None)
        if span is None:
            return

        if error is not None:
            span.set_tag(tags.ERROR, True)
            span.log_kv({
                'event': tags.ERROR,
                'error.object': error,
            })
        if response is not None:
            span.set_tag(tags.HTTP_STATUS_CODE, response.status_code)

        span.finish()

        if hasattr(request, 'tracing_context_manager'):
            request.tracing_context_manager.__exit__()
