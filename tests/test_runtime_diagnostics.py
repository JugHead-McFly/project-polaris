import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
import json
from threading import Event, get_ident
from time import perf_counter

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.core import runtime_diagnostics as d
from app.core.request_timing import timed
from app.main import log_request
from import_plan_fixture import workflow


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    for name, value in [('ENABLED',True),('_started',None),('_last',None),
                        ('_samples',0),('_active',0),('_background',0),('_background_started',0)]:
        monkeypatch.setattr(d,name,value)
    token=d._current.set(None)
    yield
    d._current.reset(token)


def test_sampling_bounds_expiry_and_other_routes(monkeypatch):
    records=[]; clock=[0.0]
    monkeypatch.setattr(d,'_emit',records.append)
    monkeypatch.setattr(d,'perf_counter',lambda:clock[0])
    for i in range(1900):
        clock[0]=float(i)
        with d.request_scope('generated-id',True): pass
        with d.request_scope('other',False): pass
    assert len(records)==20
    assert d._active==0
    assert all(row['kind']=='request' for row in records)


def test_disabled_has_no_clocks_logs_or_counters(monkeypatch):
    monkeypatch.setattr(d,'ENABLED',False)
    def fail(): raise AssertionError('called')
    monkeypatch.setattr(d,'perf_counter',fail)
    with d.request_scope('id',True),d.planner_scope(): d.mark('route_entry')
    assert d.run_art_refresh(lambda:7)==7
    assert d._active==d._background==d._samples==0


@pytest.mark.parametrize('broken',['perf_counter','process_time','thread_time','_emit','_snapshot'])
def test_diagnostic_failures_do_not_change_application_outcome(monkeypatch,broken):
    def fail(*a,**kw): raise RuntimeError('private failure')
    monkeypatch.setattr(d,broken,fail)
    with d.request_scope('id',True),d.planner_scope():
        d.mark('route_entry')
    assert d.run_art_refresh(lambda:'ok')=='ok'
    assert d._active==d._background==0
    assert d._current.get() is None


def test_worker_cpu_and_shared_process_are_separate(monkeypatch):
    records=[]
    monkeypatch.setattr(d,'_emit',records.append)
    with d.request_scope('id',True):
        d.mark('auth_entry'); d.mark('route_entry')
        with d.planner_scope(): pass
    row=records[0]
    assert set(row['planner'])=={'returned','wall_ms','process_cpu_shared_ms','worker_cpu_ms'}
    assert set(row['phases'])=={'request_entry','auth_entry','route_entry','planner_entry','planner_end','scope_end'}
    assert all(value>=0 for value in row['planner'].values())


def test_background_measured_in_worker_and_overlap_seen(monkeypatch):
    records=[]; identities=[]; running=Event(); release=Event()
    monkeypatch.setattr(d,'_emit',records.append)
    monkeypatch.setattr(d,'thread_time',lambda:identities.append(get_ident()) or 1.0)
    def operation(): running.set(); release.wait(5); return 8
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(d.run_art_refresh,operation)
        assert running.wait(5)
        try:
            with d.request_scope('id',True): pass
        finally: release.set()
        assert future.result()==8
    row=next(r for r in records if r['kind']=='request')
    assert row['phases']['request_entry']['art_workers_sampled']==1
    assert all(identity!=get_ident() for identity in identities)
    assert d._background==0
    with pytest.raises(ValueError):
        d.run_art_refresh(lambda:(_ for _ in ()).throw(ValueError('application failure')))
    assert d._background==0


def test_concurrent_other_request_and_cancellation_cleanup(monkeypatch):
    records=[]
    monkeypatch.setattr(d,'_emit',records.append)
    async def run():
        entered=asyncio.Event()
        async def other():
            with d.request_scope('other',False):
                entered.set()
                await asyncio.Event().wait()
        task=asyncio.create_task(other()); await entered.wait()
        with d.request_scope('sample',True):
            await asyncio.to_thread(d.mark,'route_entry')
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
    asyncio.run(run())
    assert records[0]['phases']['route_entry']['active_requests_sampled']==2
    assert d._active==0


def test_failed_auth_summary_has_no_route_or_secrets(monkeypatch):
    records=[]; monkeypatch.setattr(d,'_emit',records.append)
    app=FastAPI(); app.middleware('http')(log_request)
    @app.get('/tonight')
    @timed('auth')
    def denied(): raise HTTPException(401,'private test reason')
    with TestClient(app) as client:
        response=client.get('/tonight?secret=private-query',headers={'Authorization':'Bearer private-token'})
    assert response.status_code==401
    assert 'auth_entry' in records[0]['phases']
    assert 'route_entry' not in records[0]['phases']
    assert 'private' not in json.dumps(records)
    assert d._active==0


def test_hosted_plan_unchanged_when_enabled_and_logger_fails(monkeypatch):
    with workflow() as flow,TestClient(flow.app) as client:
        monkeypatch.setattr(d,'ENABLED',False)
        before=flow.plan(client)
        monkeypatch.setattr(d,'ENABLED',True)
        def fail(*a): raise RuntimeError('logging unavailable')
        monkeypatch.setattr(d,'_emit',fail)
        flow.app.middleware_stack = None
        flow.app.middleware('http')(log_request)
        after=flow.plan(client)
    for key in ['recommendation_run_id','forecast_accuracy']: before.pop(key,None);after.pop(key,None)
    assert before==after


def test_boundary_overhead_budget(monkeypatch):
    # Loose regression guard, not the release's full-request overhead measurement.
    monkeypatch.setattr(d,'_emit',lambda _:None)
    started=perf_counter()
    for _ in range(1000):
        d._last=None; d._samples=0
        with d.request_scope('id',True):
            d.mark('auth_entry');d.mark('route_entry')
            with d.planner_scope(): pass
    assert perf_counter()-started < 1.0


def test_cancelled_sample_does_not_claim_headers_or_success(monkeypatch):
    records=[];monkeypatch.setattr(d,'_emit',records.append)
    async def run():
        with d.request_scope('id',True),d.planner_scope():
            raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError): asyncio.run(run())
    assert 'response_headers_ready' not in records[0]['phases']
    assert records[0]['planner']['returned'] is False
    assert d._active==0


def test_unsampled_nested_request_does_not_mutate_parent_record(monkeypatch):
    records=[];monkeypatch.setattr(d,'_emit',records.append)
    with d.request_scope('parent',True):
        with d.request_scope('child',True):
            d.mark('auth_entry')
        d.mark('route_entry')
    assert len(records)==1
    assert 'auth_entry' not in records[0]['phases']
    assert 'route_entry' in records[0]['phases']
