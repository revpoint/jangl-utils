# Copyright (c) 2015 Uber Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import absolute_import

from future import standard_library
from opentracing import Format
from opentracing_instrumentation.request_context import span_in_context

standard_library.install_aliases()
import logging

import opentracing
from opentracing.ext import tags
from opentracing_instrumentation.client_hooks._patcher import Patcher

log = logging.getLogger(__name__)

# Try to save the original entry points
try:
    import jangl_utils.kafka.consumers
except ImportError:  # pragma: no cover
    pass
else:
    _KafkaWorker_consume = jangl_utils.kafka.consumers.KafkaWorker._consume


class KafkaConsumerPatcher(Patcher):
    applicable = '_KafkaWorker_consume' in globals()

    def _install_patches(self):
        jangl_utils.kafka.consumers.KafkaWorker._consume = self._get_consume_wrapper()

    def _reset_patches(self):
        jangl_utils.kafka.consumers.KafkaWorker._consume = _KafkaWorker_consume

    def _get_consume_wrapper(self):
        def consume_wrapper(consumer, message):
            """Wraps KafkaWorker._consume"""

            try:
                carrier = {}
                for (key, value) in message.headers():
                    carrier[key] = value
                log.debug(carrier)
                parent_ctx = opentracing.tracer.extract(
                    format=Format.TEXT_MAP, carrier=carrier
                )
            except:
                parent_ctx = None

            if parent_ctx or getattr(consumer, 'start_new_traces', False):
                tags_dict = {tags.MESSAGE_BUS_DESTINATION: consumer.get_topic_name()}
                if message.key():
                    tags_dict['key'] = str(message.key())

                span = opentracing.tracer.start_span(
                    operation_name='kafka:consume',
                    child_of=parent_ctx,
                    tags=tags_dict,
                )

                with span, span_in_context(span):
                    try:
                        _KafkaWorker_consume(consumer, message)
                    except Exception as error:
                        span.set_tag(tags.ERROR, True)
                        span.log_kv({
                            'event': tags.ERROR,
                            'error.object': error,
                        })
                        raise
            else:
                _KafkaWorker_consume(consumer, message)
        return consume_wrapper


patcher = KafkaConsumerPatcher()


def set_patcher(custom_patcher):
    global patcher
    patcher = custom_patcher


def install_patches():
    patcher.install_patches()
