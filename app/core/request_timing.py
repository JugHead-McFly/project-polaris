"""Bounded, request-scoped timings; never record arguments or user data.

Stages may overlap or nest and must not be summed as a request total.
Context is copied into worker threads; the shared collector is lock protected.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import logging
from threading import Lock
from time import perf_counter, thread_time
from app.core.runtime_diagnostics import mark, planner_scope

_current = ContextVar("request_timings", default=None)
logger = logging.getLogger(__name__)


class RequestTimings:
    def __init__(self, request_id):
        self.request_id = request_id
        self.values = {}
        self.thread_cpu = {}
        self.lock = Lock()

    def add(self, name, milliseconds, cpu_milliseconds=0.0):
        with self.lock:
            elapsed, count = self.values.get(name, (0.0, 0))
            self.values[name] = (elapsed + milliseconds, count + 1)
            self.thread_cpu[name] = self.thread_cpu.get(name, 0.0) + cpu_milliseconds

    def header(self):
        with self.lock:
            return ", ".join(f"{name};dur={elapsed:.1f}" for name, (elapsed, _) in sorted(self.values.items()))


@contextmanager
def request_timings(request_id):
    timings = RequestTimings(request_id)
    token = _current.set(timings)
    try:
        yield timings
    finally:
        _current.reset(token)
        for name, (elapsed, count) in sorted(timings.values.items()):
            logger.info("request_stage request_id=%s stage=%s duration_ms=%.1f calls=%d thread_cpu_ms=%.1f",
                        request_id, name, elapsed, count, timings.thread_cpu[name])


def timed(name):
    """Use only literal internal stage names, never request-derived labels."""
    def decorate(function):
        @wraps(function)
        def measured(*args, **kwargs):
            if name == 'auth':
                mark('auth_entry')
            if name == 'planner':
                with planner_scope():
                    return measure_call(*args, **kwargs)
            return measure_call(*args, **kwargs)

        def measure_call(*args, **kwargs):
            timings = _current.get()
            if timings is None:
                return function(*args, **kwargs)
            start = perf_counter()
            cpu_start = thread_time()
            try:
                return function(*args, **kwargs)
            finally:
                timings.add(name, (perf_counter() - start) * 1000,
                            (thread_time() - cpu_start) * 1000)
        return measured
    return decorate
