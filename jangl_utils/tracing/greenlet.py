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

import functools

from future import standard_library
from opentracing_instrumentation.request_context import RequestContextManager, get_current_span
from opentracing_instrumentation.utils import start_child_span

standard_library.install_aliases()
import logging

from opentracing_instrumentation.client_hooks._patcher import Patcher

log = logging.getLogger(__name__)

# Try to save the original entry points
try:
    import gevent
    import gevent.backdoor
    import gevent.baseserver
    import gevent.pool
    import gevent.subprocess
    import gevent.thread
    import gevent.threadpool
except ImportError:  # pragma: no cover
    pass
else:
    _Greenlet = gevent.greenlet.Greenlet
    _joinall = gevent.greenlet.joinall
    _Group_join = gevent.pool.Group.join


class GreenletPatcher(Patcher):
    applicable = '_Greenlet' in globals()

    def _install_patches(self):
        Greenlet = self.TracedGreenlet
        joinall = self._get_joinall_wrapper()
        Group_join = self._get_group_join_wrapper()

        gevent.greenlet.Greenlet = Greenlet
        gevent.Greenlet = Greenlet
        gevent.spawn = Greenlet.spawn
        gevent.spawn_later = Greenlet.spawn_later

        gevent.greenlet.joinall = joinall
        gevent.joinall = joinall

        gevent.backdoor.Greenlet = Greenlet

        gevent.baseserver.Greenlet = Greenlet

        gevent.pool.Greenlet = Greenlet
        gevent.pool.Group.greenlet_class = Greenlet
        gevent.pool.Group.join = Group_join

        gevent.subprocess.Greenlet = Greenlet
        gevent.subprocess.spawn = Greenlet.spawn
        gevent.subprocess.joinall = joinall

        gevent.thread.Greenlet = Greenlet

        gevent.threadpool.Greenlet = Greenlet

    def _reset_patches(self):
        gevent.greenlet.Greenlet = _Greenlet
        gevent.Greenlet = _Greenlet
        gevent.spawn = _Greenlet.spawn
        gevent.spawn_later = _Greenlet.spawn_later

        gevent.greenlet.joinall = _joinall
        gevent.joinall = _joinall

        gevent.backdoor.Greenlet = _Greenlet

        gevent.baseserver.Greenlet = _Greenlet

        gevent.pool.Greenlet = _Greenlet
        gevent.pool.Group.greenlet_class = _Greenlet
        gevent.pool.Group.join = _Group_join

        gevent.subprocess.Greenlet = _Greenlet
        gevent.subprocess.spawn = _Greenlet.spawn
        gevent.subprocess.joinall = _joinall

        gevent.thread.Greenlet = _Greenlet

        gevent.threadpool.Greenlet = _Greenlet

    class TracedGreenlet(_Greenlet):
        def __init__(self, run=None, *args, **kwargs):
            parent_ctx = get_current_span()
            if parent_ctx and run:
                operation = 'gevent:{}'.format(run.__name__)

                @functools.wraps(run)
                def patched_run(*args, **kwargs):
                    span = start_child_span(
                        operation_name=operation,
                        parent=parent_ctx,
                    )
                    with span:
                        with RequestContextManager(span=span):
                            return run(*args, **kwargs)
                super(GreenletPatcher.TracedGreenlet, self).__init__(patched_run, *args, **kwargs)
            else:
                super(GreenletPatcher.TracedGreenlet, self).__init__(run, *args, **kwargs)

    def _get_joinall_wrapper(self):
        def joinall_wrapper(greenlets, timeout=None, raise_error=False, count=None):
            parent_ctx = get_current_span()
            if parent_ctx:
                operation = 'gevent:joinall'
                tags_dict = {
                    'greenlets': self._get_greenlet_names(greenlets),
                    'timeout': timeout,
                    'raise_error': raise_error,
                    'count': count,
                }
                span = start_child_span(
                    operation_name=operation,
                    parent=parent_ctx,
                    tags=tags_dict,
                )
                with span:
                    return _joinall(greenlets, timeout, raise_error, count)
            else:
                return _joinall(greenlets, timeout, raise_error, count)
        return joinall_wrapper

    def _get_group_join_wrapper(self):
        def group_join_wrapper(group, timeout=None, raise_error=False):
            parent_ctx = get_current_span()
            if parent_ctx:
                operation = 'gevent:{}:join'.format(group.__class__.__name__)
                tags_dict = {
                    'greenlets': self._get_greenlet_names(group.greenlets),
                    'timeout': timeout,
                    'raise_error': raise_error,
                }
                span = start_child_span(
                    operation_name=operation,
                    parent=parent_ctx,
                    tags=tags_dict,
                )
                with span:
                    return _Group_join(group, timeout, raise_error)
            else:
                return _Group_join(group, timeout, raise_error)
        return group_join_wrapper

    def _get_greenlet_names(self, greenlets):
        return [g._run.__name__ for g in greenlets if g._run.__name__ != '_run']


patcher = GreenletPatcher()


def set_patcher(custom_patcher):
    global patcher
    patcher = custom_patcher


def install_patches():
    patcher.install_patches()
