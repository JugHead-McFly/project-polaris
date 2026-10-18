from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from unittest.mock import patch
import pytest
from astropy.utils import iers
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core import calculation_cache as cache
from app.core.planning_context import ObservatoryContext
from app.services import astronomy_service as astronomy, planner_service as planner
from app.services.deep_sky_catalog import catalog
from app.services.scheduler_service import build_tonight_schedule
from app.data.targets import TARGETS


class DisabledCache:
    def get(self): return None
    def set(self, value): return None
    def reset(self, token): pass


def test_altitude_cache_concurrent_calculations_and_exception_cleanup():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, local
    barrier = Barrier(2)
    worker = local()
    at = datetime(2026, 10, 18, tzinfo=timezone.utc)
    @cache.reuse_altitude_samples
    def calculate(target, times, observatory=None):
        worker.calls += 1
        return [worker.value] * len(times)
    @cache.astronomy_calculation
    def run(value):
        worker.calls, worker.value = 0, value
        first = calculate('M31', [at], 'same-observatory')
        barrier.wait(timeout=10)
        assert calculate('M31', [at], 'same-observatory') == first == [value]
        assert worker.calls == 1
        return first
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(run, [10.0, 20.0])) == [[10.0], [20.0]]
    assert cache._values.get() is None
    @cache.astronomy_calculation
    def failed():
        worker.calls, worker.value = 0, 99.0
        calculate('M31', [at])
        raise RuntimeError('fixture')
    with pytest.raises(RuntimeError, match='fixture'):
        failed()
    assert cache._values.get() is None


def test_nested_calculations_restore_outer_seeded_transit_values():
    @cache.reuse_exact
    def value(at, observatory=None): return 'computed'
    at = datetime(2026, 10, 18, tzinfo=timezone.utc)
    @cache.astronomy_calculation
    def inner():
        assert value(at, 'a') == 'computed'
        value.seed_exact_result('inner', at, 'a')
        assert value(at, 'a') == 'inner'
    @cache.astronomy_calculation
    def outer():
        value.seed_exact_result('outer', at, 'a')
        inner()
        assert value(at, 'a') == 'outer'
    outer()
    assert value(at, 'a') == 'computed'


def test_implicit_now_transit_is_resolved_before_cache_lookup():
    first = datetime(2026, 10, 18, tzinfo=timezone.utc)
    second = datetime(2026, 10, 19, tzinfo=timezone.utc)
    class Clock:
        instants = iter([first, second])
        @classmethod
        def now(cls, tz=None): return next(cls.instants)
    context = ObservatoryContext('Synthetic', 33.4, -112.074, 'America/Phoenix')
    with iers.conf.set_temp('auto_download', False), patch.object(astronomy, 'datetime', Clock):
        @cache.astronomy_calculation
        def run():
            a = astronomy.get_transit_datetime('M31', observatory=context)
            b = astronomy.get_transit_datetime('M31', observatory=context)
            assert b > a
        run()


def test_altitude_sample_reuse_preserves_order_fold_context_and_lists():
    calls = []
    @cache.reuse_altitude_samples
    def calculate(target, times, observatory=None):
        calls.append((target, list(times), observatory))
        return [float(at.fold) for at in times]
    at = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo('America/New_York'))
    other = at.replace(fold=1)
    @cache.astronomy_calculation
    def run():
        result = calculate('M31', [at, other, at], 'a')
        assert result == [0, 1, 0]
        result[0] = 99
        assert calculate('M31', [other, at], 'a') == [1, 0]
        assert calculate('M31', [], 'a') == []
        calculate('M31', [at], 'b')
        calculate('M33', [at], 'a')
    run()
    assert [len(times) for _, times, _ in calls] == [2, 1, 1]
    calculate('M31', [at], 'a')
    assert len(calls) == 4


@pytest.mark.parametrize('target', ['M31', 'MARS', 'NGC7092'])
def test_real_altitude_batches_equal_scalar_results(target):
    context = ObservatoryContext('Synthetic', 40.7, -74.0, 'America/New_York', elevation_meters=50)
    zone = ZoneInfo(context.timezone_name)
    times = [datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=fold) for fold in (0, 1)]
    with iers.conf.set_temp('auto_download', False):
        expected = [astronomy.get_altitude_at(target, at, context) for at in times]
        @cache.astronomy_calculation
        def run():
            assert astronomy.get_altitudes_at(target, times, context) == expected
            assert [astronomy.get_altitude_at(target, at, context) for at in reversed(times)] == expected[::-1]
        run()


@pytest.mark.parametrize('latitude,month,names', [
    (33.4, 10, ['M31']),
    (-33.8, 2, ['M31', 'M42', 'NGC7092', 'NGC2099']),
    (65, 6, ['M31', 'M42', 'NGC7092', 'NGC2099']),
])
def test_batched_transits_exactly_equal_scalar_transits(latitude, month, names):
    context = ObservatoryContext('Synthetic', latitude, -112.074, 'America/Phoenix', elevation_meters=331)
    at = datetime(2026, month, 18, 2, 49, tzinfo=timezone.utc)
    with iers.conf.set_temp('auto_download', False):
        expected = [astronomy.get_transit_datetime(name, at, context) for name in names]
        @cache.astronomy_calculation
        def run():
            astronomy.prepare_fixed_target_transits(names, at, context)
            with patch.object(astronomy, '_get_observer', side_effect=AssertionError('scalar transit recomputed')):
                actual = [astronomy.get_transit_datetime(name, at, context) for name in names]
            assert actual == expected
        run()


def test_transit_batch_excludes_moving_and_unknown_targets():
    at = datetime(2026, 10, 18, tzinfo=timezone.utc)
    with patch.object(astronomy, 'is_ephemeris_target', side_effect=lambda name: name == 'COMET'), \
            patch.object(astronomy, '_get_observer', side_effect=AssertionError('unexpected batch')):
        astronomy.prepare_fixed_target_transits(['MARS', 'COMET', 'UNKNOWN'], at)


def test_exact_cache_scope_location_fold_and_mutation():
    calls = []
    @cache.reuse_exact
    def value(at, location=None):
        calls.append((at, location))
        return {'value': len(calls)}
    zone = ZoneInfo('America/New_York')
    first = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    second = first.replace(fold=1)
    @cache.astronomy_calculation
    def run():
        result = value(first, 'a')
        result['value'] = -1
        assert value(at=first, location='a')['value'] == 1
        assert value(second, 'a')['value'] == 2
        assert value(first, 'b')['value'] == 3
    run()
    assert len(calls) == 3
    value(first, 'a')
    assert len(calls) == 4
    @cache.astronomy_calculation
    def failed():
        value(first, 'a')
        raise RuntimeError()
    with pytest.raises(RuntimeError): failed()
    assert cache._values.get() is None


@pytest.mark.parametrize('date', ['2026-10-18T02:02:00+00:00', '2026-12-16T02:02:00+00:00'])
def test_55_candidate_plan_and_schedule_exactly_match_without_reuse(date):
    instant = datetime.fromisoformat(date)
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    context = ObservatoryContext('Synthetic Phoenix', 33.4484, -112.074, 'America/Phoenix',
                                 elevation_meters=331, bortle_class=8, rig_profile_key='dwarf-mini')
    # 55 distinct physical catalog objects including the existing curated pool.
    from app.services.deep_sky_catalog import get_entry
    candidates = {}
    for name in list(TARGETS) + ['NGC7092', 'NGC1039', 'NGC2099'] + [f'NGC{i}' for i in range(1, 1000)]:
        entry = get_entry(name)
        if entry:
            candidates.setdefault(entry['id'], name)
        if len(candidates) == 55: break
    assert len(candidates) == 55
    weather = dict(observing_rating=5, cloud_cover_percent=0, humidity_percent=30,
                   wind_speed_mph=2, temperature_f=65, cache_status='fresh')
    with iers.conf.set_temp('auto_download', False), Session(create_engine('sqlite:///:memory:')) as db, \
            patch.object(planner, 'datetime', FrozenDateTime), \
            patch.object(astronomy, 'datetime', FrozenDateTime), \
            patch('app.services.scheduler_service.datetime', FrozenDateTime), \
            patch.object(planner, 'get_weather_summary', side_effect=lambda *a, **kw: dict(weather)), \
            patch.object(astronomy, 'get_body', wraps=astronomy.get_body) as bodies:
        args = dict(observatory=context, use_capture_history=False,
                    capture_progress={'M31': {'seconds': 999999}}, target_names=list(candidates.values()))
        with patch.object(cache, '_values', DisabledCache()):
            before = planner.get_tonight_plan(db, **args)
        before_calls = bodies.call_count
        bodies.reset_mock()
        after = planner.get_tonight_plan(db, **args)
        assert after == before
        assert bodies.call_count <= 3
        assert before_calls >= 55 * 3
        assert build_tonight_schedule(after, timezone_name=context.timezone_name, rig_profile_key=context.rig_profile_key) == \
               build_tonight_schedule(before, timezone_name=context.timezone_name, rig_profile_key=context.rig_profile_key)
