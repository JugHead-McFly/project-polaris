from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo
import pytest
from app.services.cloud_forecast_service import blend_cloud_forecasts, parse_nws_clouds, summarize_dark_window
from app.services.planner_service import get_weather_decision

NOW = datetime(2026, 9, 13, 2, tzinfo=timezone.utc)
CONTEXT = SimpleNamespace(timezone_name='America/Phoenix', latitude=33.28, longitude=-111.72)

def test_opposing_sources_average_without_hiding_disagreement():
    weather = {'provider': 'open-meteo', 'hourly_forecast': {'2026-09-12T19:00': {'cloud_cover_percent': 0}}}
    with patch('app.services.cloud_forecast_service.get_nws_clouds', return_value={'status': 'available', 'updated_at': NOW.isoformat(), 'intervals': [(NOW, NOW+timedelta(hours=1), 100)]}):
        blend_cloud_forecasts(weather, CONTEXT, NOW)
    row = weather['hourly_forecast']['2026-09-12T19:00']
    assert row['cloud_cover_percent'] == 50
    assert row['cloud_forecast_spread'] == 100
    assert [s['cloud_cover_percent'] for s in row['cloud_forecast_sources']] == [0, 100]

@pytest.mark.parametrize('primary,expected', [(30,30), (None,None), (float('nan'),None)])
def test_outage_does_not_invent_clear_skies(primary, expected):
    weather = {'hourly_forecast': {'2026-09-12T19:00': {'cloud_cover_percent': primary}}}
    with patch('app.services.cloud_forecast_service.get_nws_clouds', return_value={'status':'unavailable','intervals':[], 'updated_at':None}):
        blend_cloud_forecasts(weather, CONTEXT, NOW)
    assert weather['hourly_forecast']['2026-09-12T19:00']['cloud_cover_percent'] == expected

def test_nws_collapsed_intervals_and_nulls():
    intervals, _ = parse_nws_clouds({'updateTime': NOW.isoformat(), 'skyCover': {'values': [
        {'validTime':'2026-09-13T02:00:00Z/PT2H','value':80},
        {'validTime':'2026-09-13T04:00:00Z/PT1H','value':None}]}}, NOW)
    assert intervals == [(NOW,NOW+timedelta(hours=2),80)]
    with pytest.raises(ValueError):
        parse_nws_clouds({'updateTime': (NOW-timedelta(hours=13)).isoformat()},NOW)

def test_darkness_mean_weights_partial_hours_and_rejects_gaps():
    start=datetime(2026,9,12,19,30,tzinfo=ZoneInfo('America/Phoenix'))
    weather={'hourly_forecast': {
        '2026-09-12T19:00': {'cloud_cover_percent':0},
        '2026-09-12T20:00': {'cloud_cover_percent':90}}}
    assert summarize_dark_window(weather,start,start+timedelta(minutes=90))['average_cloud_cover_percent'] == 60
    assert summarize_dark_window(weather,start,start+timedelta(hours=4))['average_cloud_cover_percent'] is None

def test_cloud_forecast_is_caution_but_heat_remains_stop():
    weather={'observing_rating':1,'planned_cloud_cover_percent':100,'planned_temperature_f':80}
    assert get_weather_decision(weather) == 'Use Caution'
    weather['planned_temperature_f']=105
    assert get_weather_decision(weather) == 'Do Not Image'
