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
