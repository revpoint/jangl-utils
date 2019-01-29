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
from opentracing_instrumentation.utils import start_child_span

standard_library.install_aliases()
import logging

import opentracing
from opentracing.ext import tags
from opentracing_instrumentation import get_current_span
from opentracing_instrumentation.client_hooks._patcher import Patcher

log = logging.getLogger(__name__)

# Try to save the original entry points
try:
    import jangl_utils.kafka.producers
except ImportError:  # pragma: no cover
    pass
else:
    _Producer_produce = jangl_utils.kafka.producers.Producer._produce


class KafkaProducerPatcher(Patcher):
    applicable = '_Producer_produce' in globals()

    def _install_patches(self):
        jangl_utils.kafka.producers.Producer._produce = self._get_produce_wrapper()

    def _reset_patches(self):
        jangl_utils.kafka.producers.Producer._produce = _Producer_produce

    def _get_produce_wrapper(self):
        def produce_wrapper(producer, value, key=None, **kwargs):
            """Wraps Producer._produce"""

            parent_ctx = get_current_span()
            if parent_ctx:
                span = start_child_span(
                    operation_name='kafka:produce',
                    parent=parent_ctx,
                )

                span.set_tag(tags.MESSAGE_BUS_DESTINATION, producer.get_topic_name())

                headers = kwargs.pop('headers', {})
                try:
                    opentracing.tracer.inject(span_context=span.context,
                                              format=Format.TEXT_MAP,
                                              carrier=headers)
                except opentracing.UnsupportedFormatException:
                    pass

                original_delivery = kwargs.pop('on_delivery', lambda *a: None)

                def on_delivery(err, msg):
                    span.finish()
                    original_delivery(err, msg)

                _Producer_produce(producer, value, key=key, headers=headers,
                                  on_delivery=on_delivery, **kwargs)
            else:
                _Producer_produce(producer, value, key=key, **kwargs)

        return produce_wrapper


patcher = KafkaProducerPatcher()


def set_patcher(custom_patcher):
    global patcher
    patcher = custom_patcher


def install_patches():
    patcher.install_patches()
