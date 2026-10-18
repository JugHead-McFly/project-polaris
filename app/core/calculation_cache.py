"""Exact reuse during a single calculation, never a cross-request plan cache."""
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from inspect import signature

_values = ContextVar("astronomy_calculation_values", default=None)


def reuse_altitude_samples(function):
    """Reuse exact scalar results while retaining vector evaluation of misses."""
    @wraps(function)
    def reused(target_name, observation_datetimes, observatory=None):
        values = _values.get()
        if values is None:
            return function(target_name, observation_datetimes, observatory)
        keys = [(function, target_name, at.isoformat(), at.fold, observatory)
                for at in observation_datetimes]
        missing = {}
        for key, at in zip(keys, observation_datetimes):
            if key not in values:
                missing.setdefault(key, at)
        if missing:
            results = function(target_name, list(missing.values()), observatory)
            if len(results) != len(missing):
                raise ValueError("Altitude result count does not match sample count")
            values.update(zip(missing, results))
        # A fresh list prevents caller mutations leaking into later requests.
        return [values[key] for key in keys]
    return reused


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

    def key_for(args, kwargs):
        bound = parameters.bind(*args, **kwargs)
        bound.apply_defaults()
        return (function, tuple((name, (value.isoformat(), value.fold)
                                if isinstance(value, datetime) else value)
                               for name, value in bound.arguments.items()))

    def seed(result, *args, **kwargs):
        values = _values.get()
        if values is not None:
            values[key_for(args, kwargs)] = result

    @wraps(function)
    def reused(*args, **kwargs):
        values = _values.get()
        if values is None:
            return function(*args, **kwargs)
        # ISO offset + fold distinguishes repeated local times across DST.
        key = key_for(args, kwargs)
        if key not in values:
            values[key] = function(*args, **kwargs)
        result = values[key]
        # Moon summaries contain scalar fields; callers may safely modify them.
        return dict(result) if isinstance(result, dict) else result
    reused.seed_exact_result = seed
    return reused
