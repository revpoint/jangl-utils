import functools
import contextlib
from opentracing.ext import tags
from opentracing_instrumentation import get_current_span, span_in_context, utils


def func_span(func, tags=None, require_active_trace=True):
    """
    Creates a new local span for execution of the given `func`.
    The returned span is best used as a context manager, e.g.

    .. code-block:: python

        with func_span('my_function'):
            return my_function(...)

    At this time the func should be a string name. In the future this code
    can be enhanced to accept a real function and derive its qualified name.

    :param func: name of the function or method
    :param tags: optional tags to add to the child span
    :param require_active_trace: controls what to do when there is no active
        trace. If require_active_trace=True, then no span is created.
        If require_active_trace=False, a new trace is started.
    :return: new child span, or a dummy context manager if there is no
        active/current parent span
    """
    current_span = get_current_span()

    if current_span is None and require_active_trace:
        @contextlib.contextmanager
        def empty_ctx_mgr():
            yield None

        return empty_ctx_mgr()

    # TODO convert func to a proper name: module:class.func
    operation_name = str(func)
    span = utils.start_child_span(
        operation_name=operation_name, parent=current_span, tags=tags)
    with span_in_context(span):
        return span


def traced_function(func=None, name=None, on_start=None,
                    require_active_trace=True):
    """
    A decorator that enables tracing of the wrapped function or
    Tornado co-routine provided there is a parent span already established.

    .. code-block:: python

        @traced_function
        def my_function1(arg1, arg2=None)
            ...

    :param func: decorated function
    :param name: optional name to use as the Span.operation_name.
        If not provided, func.__name__ will be used.
    :param on_start: an optional callback to be executed once the child span
        is started, but before the decorated function is called. It can be
        used to set any additional tags on the span, perhaps by inspecting
        the decorated function arguments. The callback must have a signature
        `(span, *args, *kwargs)`, where the last two collections are the
        arguments passed to the actual decorated function.

        .. code-block:: python

            def extract_call_site_tag(span, *args, *kwargs)
                if 'call_site_tag' in kwargs:
                    span.set_tag('call_site_tag', kwargs['call_site_tag'])

            @traced_function(on_start=extract_call_site_tag)
            def my_function(arg1, arg2=None, call_site_tag=None)
                ...

    :param require_active_trace: controls what to do when there is no active
        trace. If require_active_trace=True, then no span is created.
        If require_active_trace=False, a new trace is started.
    :return: returns a tracing decorator
    """

    if func is None:
        return functools.partial(traced_function, name=name,
                                 on_start=on_start,
                                 require_active_trace=require_active_trace)

    if name:
        operation_name = name
    else:
        operation_name = func.__name__

    @functools.wraps(func)
    def decorator(*args, **kwargs):
        parent_span = get_current_span()
        if parent_span is None and require_active_trace:
            return func(*args, **kwargs)

        span = utils.start_child_span(
            operation_name=operation_name, parent=parent_span)
        if callable(on_start):
            on_start(span, *args, **kwargs)

        with span, span_in_context(span):
            try:
                return func(*args, **kwargs)
            except Exception as error:
                span.set_tag(tags.ERROR, True)
                span.log_kv({
                    'event': tags.ERROR,
                    'error.object': error,
                })
                raise
    return decorator
