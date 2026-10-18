from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.error import URLError

import pytest

from app.core.planning_context import ObservatoryContext
from app.services import weather_service as weather


@pytest.fixture(autouse=True)
def isolated_weather():
    weather.reset_weather_cache()
    with patch.object(weather, '_fetch_weather_data', return_value={'current': {'cloud_cover': 10}}), \
            patch.object(weather, '_enrich_weather'):
        yield
    weather.reset_weather_cache()


def context():
    return ObservatoryContext(name='Synthetic', latitude=33.251, longitude=-111.781,
                              timezone_name='America/Phoenix')


@pytest.mark.parametrize('change', [
    {'latitude': 33.252}, {'longitude': -111.782}, {'timezone_name': 'America/Denver'},
])
def test_changed_location_or_timezone_does_not_reuse_payload(change):
    first_context = context()
    with patch.object(weather, '_fetch_weather_data', return_value={'current': {}}) as fetch:
        weather.get_weather_summary('first', first_context)
        weather.get_weather_summary('second', replace(first_context, **change))
    assert fetch.call_count == 2


@pytest.mark.parametrize('stale', [False, True])
def test_shared_public_weather_never_reuses_callers_postal_or_mutation(stale):
    first = weather.get_weather_summary('first', context())
    first['hourly_forecast']['private-mutation'] = {}
    with patch.object(weather, 'WEATHER_CACHE_TTL_SECONDS', -1 if stale else 1200), \
            patch.object(weather, '_fetch_weather_data', side_effect=URLError('synthetic offline')) as fetch:
        second = weather.get_weather_summary('second', context())
    assert second['postal_code'] == 'second'
    assert first['postal_code'] == 'first'
    assert 'private-mutation' not in second['hourly_forecast']
    assert second['fetched_at'] == first['fetched_at']
    assert second['cache_status'] == ('stale' if stale else 'fresh')
    assert fetch.call_count == int(stale)


def test_cache_expiry_and_clock_reversal_do_not_extend_freshness():
    now = datetime(2026, 10, 18, 23, 55, tzinfo=timezone.utc)
    key = weather._weather_cache_key(context())
    weather._store_cached_weather(key, {'fetched_at': now.isoformat()}, now)
    assert weather._get_cached_weather(key, now + timedelta(minutes=10)) is not None
    assert weather._get_cached_weather(key, now + timedelta(minutes=21)) is None
    assert weather._get_cached_weather(key, now + timedelta(hours=6, seconds=1), allow_stale=True) is None
    assert weather._get_cached_weather(key, now - timedelta(seconds=1)) is None
    assert weather._get_cached_weather(key, now - timedelta(seconds=1), allow_stale=True) is None
