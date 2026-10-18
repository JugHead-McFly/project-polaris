from datetime import datetime, timezone
from threading import Event
from unittest.mock import patch
import pytest

from app.core.planning_context import ObservatoryContext
from app.core.request_timing import request_timings, timed
from app.services import weather_service as weather


def test_independent_providers_overlap_and_preserve_payload():
    astro_started, nws_started = Event(), Event()
    context = ObservatoryContext(name='Synthetic', latitude=33, longitude=-112, timezone_name='America/Phoenix')
    checked = datetime(2026, 10, 18, tzinfo=timezone.utc)
    payload = {'provider': 'synthetic', 'hourly_forecast': {'hour': {'cloud_cover_percent': 10}}}

    @timed('fixture_astro')
    def astro(actual_context, actual_checked):
        assert (actual_context, actual_checked) == (context, checked)
        astro_started.set()
        assert nws_started.wait(2), 'NWS did not overlap astronomy provider'
        return {'seeing': 'Good', 'seeing_index': 3}

    def blend(actual, actual_context, actual_checked):
        assert (actual_context, actual_checked) == (context, checked)
        nws_started.set()
        assert astro_started.wait(2), 'Astronomy provider did not overlap NWS'
        actual['hourly_forecast']['hour']['cloud_cover_percent'] = 15

    with request_timings('parallel') as timings, \
            patch.object(weather, '_get_astro_forecast', side_effect=astro), \
            patch.object(weather, 'blend_cloud_forecasts', side_effect=blend):
        weather._enrich_weather(payload, context, checked)
        assert timings.values['fixture_astro'][1] == 1
    assert payload == {'provider': 'synthetic', 'hourly_forecast': {'hour': {'cloud_cover_percent': 15}},
                       'seeing': 'Good', 'seeing_index': 3}


def test_unavailable_supplements_preserve_primary():
    payload = {'provider': 'synthetic', 'cloud_cover_percent': 10}
    with patch.object(weather, '_get_astro_forecast', return_value={'seeing': None}), \
            patch.object(weather, 'blend_cloud_forecasts'):
        weather._enrich_weather(payload, None, None)
    assert payload == {'provider': 'synthetic', 'cloud_cover_percent': 10, 'seeing': None}


def test_provider_timeouts_keep_primary_and_unavailable_supplements():
    context = ObservatoryContext(name='Synthetic', latitude=33, longitude=-112, timezone_name='America/Phoenix')
    payload = {'provider': 'synthetic', 'cloud_cover_percent': 10, 'hourly_forecast': {}}
    with patch.object(weather, 'urlopen', side_effect=TimeoutError), \
            patch('app.services.cloud_forecast_service.urlopen', side_effect=TimeoutError):
        weather._enrich_weather(payload, context, datetime.now(timezone.utc))
    assert payload['cloud_cover_percent'] == 10
    assert payload['seeing'] is None
    assert 'unavailable' in payload['cloud_forecast_status']


def test_unexpected_worker_failure_is_propagated_and_joined():
    finished = Event()
    def failed(*args):
        try:
            raise RuntimeError('synthetic worker failure')
        finally:
            finished.set()
    with patch.object(weather, '_get_astro_forecast', side_effect=failed), \
            patch.object(weather, 'blend_cloud_forecasts'):
        with pytest.raises(RuntimeError, match='synthetic worker failure'):
            weather._enrich_weather({}, None, None)
    assert finished.is_set()
