"""Bounded, request-scoped timings; never record arguments or user data.

Stages may overlap or nest and must not be summed as a request total.
Context is copied into worker threads; the shared collector is lock protected.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import logging
from threading import Lock
from time import perf_counter

_current = ContextVar("request_timings", default=None)
logger = logging.getLogger(__name__)


class RequestTimings:
    def __init__(self, request_id):
        self.request_id = request_id
        self.values = {}
        self.lock = Lock()

    def add(self, name, milliseconds):
        with self.lock:
            elapsed, count = self.values.get(name, (0.0, 0))
            self.values[name] = (elapsed + milliseconds, count + 1)

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
            logger.info("request_stage request_id=%s stage=%s duration_ms=%.1f calls=%d",
                        request_id, name, elapsed, count)


def timed(name):
    """Use only literal internal stage names, never request-derived labels."""
    def decorate(function):
        @wraps(function)
        def measured(*args, **kwargs):
            timings = _current.get()
            if timings is None:
                return function(*args, **kwargs)
            start = perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                timings.add(name, (perf_counter() - start) * 1000)
        return measured
    return decorate
