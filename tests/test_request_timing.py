import asyncio
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.request_timing import request_timings, timed
from import_plan_fixture import workflow


def test_stage_records_cpu_separately_from_elapsed(monkeypatch, caplog):
    import app.core.request_timing as timing
    wall = iter([10.0, 12.0])
    cpu = iter([1.0, 1.25])
    monkeypatch.setattr(timing, 'perf_counter', lambda: next(wall))
    monkeypatch.setattr(timing, 'thread_time', lambda: next(cpu))
    @timed('fixture')
    def operation(): return 7
    with caplog.at_level(logging.INFO), request_timings('cpu-test') as timings:
        assert operation() == 7
    assert timings.values['fixture'] == (2000.0, 1)
    assert timings.thread_cpu['fixture'] == 250.0
    assert 'thread_cpu_ms=250.0' in caplog.text


def test_thread_timings_are_correlated_and_do_not_log_arguments(caplog):
    @timed('fixture')
    def operation(secret):
        return secret

    with caplog.at_level(logging.INFO), request_timings('test-request') as timings:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(copy_context().run, operation, 'private-token') for _ in range(2)]
            assert [future.result() for future in futures] == ['private-token'] * 2
        assert timings.values['fixture'][1] == 2
    assert 'request_id=test-request stage=fixture' in caplog.text
    assert 'private-token' not in caplog.text
    operation('outside')
    assert timings.values['fixture'][1] == 2


def test_concurrent_requests_and_errors_are_isolated():
    @timed('operation')
    def failure():
        raise ValueError('private error')

    async def request(name):
        with request_timings(name) as timings:
            await asyncio.sleep(0)
            with pytest.raises(ValueError):
                failure()
        return timings

    async def run():
        return await asyncio.gather(request('a'), request('b'))

    first, second = asyncio.run(run())
    assert first is not second
    assert first.values['operation'][1] == second.values['operation'][1] == 1


def test_hosted_request_exposes_correlated_stages(caplog):
    from app.main import log_request
    with caplog.at_level(logging.INFO), workflow() as flow:
        flow.app.middleware('http')(log_request)
        with TestClient(flow.app) as client:
            response = client.post('/tonight')
        assert response.status_code == 200, response.text
        for name in ('app', 'capture_history', 'planner', 'schedule', 'save_recommendation', 'forecast_tracking'):
            assert f'{name};dur=' in response.headers['Server-Timing']
        request_id = response.headers['X-Request-ID']
        assert f'request_id={request_id} stage=planner' in caplog.text


def test_failed_request_keeps_stage_timing_without_error_details():
    from fastapi import FastAPI
    from app.main import log_request
    app = FastAPI()
    app.middleware('http')(log_request)

    @app.get('/fixture-failure')
    @timed('fixture_failure')
    def failure():
        raise ValueError('private-error-detail')

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/fixture-failure')
    assert response.status_code == 500
    assert 'fixture_failure;dur=' in response.headers['Server-Timing']
    assert 'private-error-detail' not in response.text

