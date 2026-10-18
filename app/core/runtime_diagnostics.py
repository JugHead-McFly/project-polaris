"""Opt-in, bounded server diagnostics. Shared CPU is not request attribution.

No remote I/O, filesystem reads, user fields, per-target events or public headers.
Enable before process start with POLARIS_RUNTIME_DIAGNOSTICS=true. Capture at most
20 tonight requests, at least 60 seconds apart, within 30 minutes of first use.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import json
import logging
import os
from threading import Lock
from time import perf_counter, process_time, thread_time

logger = logging.getLogger(__name__)
ENABLED = os.getenv('POLARIS_RUNTIME_DIAGNOSTICS', '').strip().lower() == 'true'
_current = ContextVar('runtime_diagnostic', default=None)
_lock = Lock()
_started = None
_last = None
_samples = 0
_active = 0
_background = 0
_background_started = 0


def _safe(operation, *args):
    try:
        return operation(*args)
    except Exception:
        return None


def _emit(payload):
    logger.info('runtime_diagnostic %s', json.dumps(payload, separators=(',', ':')))


def _snapshot():
    with _lock:
        return {'active_requests_sampled': _active, 'art_workers_sampled': _background,
                'art_starts': _background_started}


def _phase(name):
    record = _current.get()
    if record is None:
        return
    record['phases'][name] = {'offset_ms': round((perf_counter()-record['wall'])*1000, 3),
                              **_snapshot()}


def mark(name):
    if name in ('auth_entry', 'route_entry', 'response_headers_ready'):
        _safe(_phase, name)


@contextmanager
def request_scope(request_id, is_tonight):
    global _started, _last, _samples, _active
    counted = False
    token = None
    record = None
    try:
        if ENABLED:
            try:
                # Do not attach a nested/unsampled request's phases to its caller.
                token = _current.set(None)
                now = perf_counter()
                with _lock:
                    if _started is None:
                        _started = now
                    if now - _started <= 1800:
                        _active += 1
                        counted = True
                        if is_tonight and _samples < 20 and (_last is None or now-_last >= 60):
                            _last = now
                            _samples += 1
                            record = {'request_id': request_id, 'wall': now,
                                      'process': process_time(), 'phases': {}}
                if record is not None:
                    _current.set(record)
                    _safe(_phase, 'request_entry')
            except Exception:
                record = None
        yield
    finally:
        if record is not None:
            def finish():
                _phase('scope_end')
                _emit({'kind': 'request', 'request_id': record['request_id'],
                       'wall_ms': round((perf_counter()-record['wall'])*1000, 3),
                       'process_cpu_shared_ms': round((process_time()-record['process'])*1000, 3),
                       'phases': record['phases'], 'planner': record.get('planner')})
            _safe(finish)
        if token is not None:
            _safe(_current.reset, token)
        if counted:
            with _lock:
                _active -= 1


@contextmanager
def planner_scope():
    record = _current.get()
    clocks = None
    if record is not None:
        _safe(_phase, 'planner_entry')
        clocks = _safe(lambda: (perf_counter(), process_time(), thread_time()))
    returned = False
    try:
        yield
        returned = True
    finally:
        if clocks is not None:
            def finish():
                record['planner'] = {'returned': returned, 'wall_ms': round((perf_counter()-clocks[0])*1000, 3),
                    'process_cpu_shared_ms': round((process_time()-clocks[1])*1000, 3),
                    'worker_cpu_ms': round((thread_time()-clocks[2])*1000, 3)}
                _phase('planner_end')
            _safe(finish)


def run_art_refresh(operation):
    """Runs inside the real background worker; propagate operation failures."""
    global _background, _background_started, _started
    clocks = None
    counted = False
    if ENABLED:
        try:
            now = perf_counter()
            with _lock:
                if _started is None:
                    _started = now
                if now-_started <= 1800:
                    _background += 1
                    _background_started += 1
                    counted = True
            if counted:
                clocks = (now, process_time(), thread_time())
                _safe(_emit, {'kind': 'art_worker_start'})
        except Exception:
            pass
    returned = False
    try:
        result = operation()
        returned = True
        return result
    finally:
        if clocks is not None:
            def finish():
                _emit({'kind': 'art_worker_end', 'returned': returned,
                       'wall_ms': round((perf_counter()-clocks[0])*1000, 3),
                       'process_cpu_shared_ms': round((process_time()-clocks[1])*1000, 3),
                       'worker_cpu_ms': round((thread_time()-clocks[2])*1000, 3)})
            _safe(finish)
        if counted:
            with _lock:
                _background -= 1
