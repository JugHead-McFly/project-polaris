import asyncio
import logging
from threading import Event
from unittest.mock import patch

import pytest
from astropy.utils import iers
from app.services import planning_runtime_service as runtime


def test_reference_preparation_uses_current_time_and_preserves_policy(caplog):
    before = (iers.conf.auto_download, iers.conf.auto_max_age, iers.conf.iers_degraded_accuracy)
    with patch.object(runtime, 'get_moon_info_at', return_value={}) as moon, \
            patch.object(runtime, 'catalog', return_value={}) as catalog, caplog.at_level(logging.INFO):
        result = runtime.prepare_planning_runtime()
    at, context = moon.call_args.args
    assert at.tzinfo is not None
    assert (context.latitude, context.longitude, context.timezone_name) == (0, 0, 'UTC')
    assert catalog.call_count == 1
    assert all(row['status'] == 'ready' for row in result.values())
    assert before == (iers.conf.auto_download, iers.conf.auto_max_age, iers.conf.iers_degraded_accuracy)
    assert 'planning_runtime stage=astronomy_reference status=ready' in caplog.text


def test_failure_defers_normally_without_skipping_catalog_or_caching_a_failure(caplog):
    with patch.object(runtime, 'get_moon_info_at', side_effect=[TimeoutError('private-detail'), {}]) as moon, \
            patch.object(runtime, 'catalog', return_value={}) as catalog, caplog.at_level(logging.INFO):
        first = runtime.prepare_planning_runtime()
        second = runtime.prepare_planning_runtime()
    assert first['astronomy_reference']['status'] == 'deferred'
    assert first['catalog_reference']['status'] == 'ready'
    assert second['astronomy_reference']['status'] == 'ready'
    assert moon.call_count == catalog.call_count == 2
    assert 'private-detail' not in caplog.text
    assert 'error_type=TimeoutError' in caplog.text


@pytest.mark.parametrize('environment', ['test', 'development', 'production'])
def test_lifespan_waits_for_preparation_only_in_production(monkeypatch, environment):
    import app.main as main
    started, release = Event(), Event()
    entered = []
    monkeypatch.setattr(main.settings, 'ENVIRONMENT', environment)
    monkeypatch.setattr(main, 'run_startup_preflight', lambda: {'ready': True})
    monkeypatch.setattr(main, 'log_preflight_report', lambda *args: None)
    def prepare():
        started.set()
        assert release.wait(3), 'test did not release startup'
    monkeypatch.setattr(main, 'prepare_planning_runtime', prepare)
    async def noop(): pass
    monkeypatch.setattr(main, 'maintain_target_art_cache', noop)
    async def exercise():
        async def serve():
            async with main.lifespan(main.app):
                entered.append(True)
        task = asyncio.create_task(serve())
        try:
            if environment == 'production':
                assert await asyncio.to_thread(started.wait, 2)
                assert entered == []
                release.set()
            await task
            assert entered == [True]
            assert started.is_set() == (environment == 'production')
        finally:
            release.set()
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    asyncio.run(exercise())


@pytest.mark.parametrize('latitude,longitude,zone,date', [
    (33.4,-112.0,'America/Phoenix','2026-10-18T03:24:00+00:00'),
    (40.7,-74.0,'America/New_York','2026-11-01T06:30:00+00:00'),
    (-33.9,151.2,'Australia/Sydney','2026-12-21T12:00:00+00:00'),
    (0,0,'UTC','2027-03-21T00:00:00+00:00'),
    (89,0,'UTC','2026-06-21T00:00:00+00:00'),
    (-89,0,'UTC','2026-12-21T00:00:00+00:00'),
])
def test_preparation_preserves_exact_moon_outputs(monkeypatch,latitude,longitude,zone,date):
    from datetime import datetime
    from app.core.planning_context import ObservatoryContext
    from app.core.request_timing import request_timings
    from app.services import astronomy_service as astronomy
    monkeypatch.setattr(iers.conf, 'auto_download', False)  # Isolated test only.
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):
            at=datetime.fromisoformat(date)
            return at.astimezone(tz) if tz else at.replace(tzinfo=None)
    monkeypatch.setattr(astronomy,'datetime',Clock)
    context=ObservatoryContext('Synthetic',latitude,longitude,zone)
    before=astronomy.get_moon_info(context)
    runtime.prepare_planning_runtime()
    with request_timings('moon-regression') as timings:
        after=astronomy.get_moon_info(context)
    assert after == before
    assert all(timings.values[stage][1] == 1 for stage in ('moon','moon_current','moon_rise','moon_set'))
