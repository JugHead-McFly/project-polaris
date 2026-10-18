"""Exact reuse during a single calculation, never a cross-request plan cache."""
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from inspect import signature

_values = ContextVar("astronomy_calculation_values", default=None)


def astronomy_calculation(function):
    @wraps(function)
    def scoped(*args, **kwargs):
        token = _values.set({})
        try:
            return function(*args, **kwargs)
        finally:
            _values.reset(token)
    return scoped


def reuse_exact(function):
    parameters = signature(function)

    @wraps(function)
    def reused(*args, **kwargs):
        values = _values.get()
        if values is None:
            return function(*args, **kwargs)
        bound = parameters.bind(*args, **kwargs)
        bound.apply_defaults()
        # ISO offset + fold distinguishes repeated local times across DST.
        key = (function, tuple((name, (value.isoformat(), value.fold)
                               if isinstance(value, datetime) else value)
                              for name, value in bound.arguments.items()))
        if key not in values:
            values[key] = function(*args, **kwargs)
        result = values[key]
        # Moon summaries contain scalar fields; callers may safely modify them.
        return dict(result) if isinstance(result, dict) else result
    return reused
