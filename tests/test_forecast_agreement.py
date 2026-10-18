from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from app.services.cloud_forecast_service import blend_cloud_forecasts
from app.services.forecast_agreement_service import summarize_agreement, location_key

START = datetime(2026,10,18,2,tzinfo=timezone.utc)
CONTEXT = SimpleNamespace(latitude=33.4,longitude=-112.074,timezone_name='America/Phoenix')

def weather(primary=10, other=20):
    data={'provider':'open-meteo','cache_status':'fresh','hourly_forecast':{
        '2026-10-17T19:00':{'cloud_cover_percent':primary}}}
    with patch('app.services.cloud_forecast_service.get_nws_clouds',return_value={
        'status':'available','updated_at':START.isoformat(),'intervals':[(START,START+timedelta(hours=1),other)]}):
        return blend_cloud_forecasts(data,CONTEXT,START)

@pytest.mark.parametrize('difference,state',[(0,'close'),(15,'close'),(15.1,'mixed'),(29.9,'mixed'),(30,'split'),(90,'split')])
def test_same_location_hour_percent_bands(difference,state):
    data=weather(0,difference)
    result=summarize_agreement(data,CONTEXT,START,START+timedelta(hours=1))
    assert result['state']==state
    assert result['average_spread_points']==round(difference,1)
    assert result['coverage_percent']==100
    assert result['independence']=='Underlying model independence not verified'

@pytest.mark.parametrize('change',['one','duplicate','location','interval','null','stale'])
def test_missing_incompatible_or_stale_is_unavailable(change):
    data=weather()
    sources=next(iter(data['hourly_forecast'].values()))['cloud_forecast_sources']
    if change=='one': sources.pop()
    if change=='duplicate': sources[1]['provider']='open-meteo'
    if change=='location': sources[1]['location_key']='another-place'
    if change=='interval': sources[1]['valid_to']=(START+timedelta(minutes=30)).isoformat()
    if change=='null': sources[1]['cloud_cover_percent']=None
    if change=='stale': data['cache_status']='stale'
    result=summarize_agreement(data,CONTEXT,START,START+timedelta(hours=1))
    assert result['state']=='unavailable'
    assert result['average_spread_points'] is None

def test_partial_window_and_overlap_are_explicit():
    data=weather()
    result=summarize_agreement(data,CONTEXT,START,START+timedelta(hours=4))
    assert result['coverage_percent']==25 and result['partial']
    data['hourly_forecast'][START.isoformat()]=deepcopy(next(iter(data['hourly_forecast'].values())))
    assert summarize_agreement(data,CONTEXT,START,START+timedelta(hours=1))['state']=='unavailable'

def test_dst_repeated_hour_requires_offset_and_counts_elapsed_time():
    context=SimpleNamespace(latitude=40.7,longitude=-74.0,timezone_name='America/New_York')
    rows={}
    for hour,offset in [(5,'-04:00'),(6,'-05:00')]:
        at=datetime(2026,11,1,hour,tzinfo=timezone.utc)
        rows[f'2026-11-01T01:00:00{offset}']={'cloud_forecast_sources':[
            dict(provider=name,cloud_cover_percent=value,location_key=location_key(context),valid_from=at.isoformat(),valid_to=(at+timedelta(hours=1)).isoformat())
            for name,value in [('open-meteo',10),('nws',30)]]}
    start=datetime(2026,11,1,5,tzinfo=timezone.utc)
    result=summarize_agreement({'hourly_forecast':rows},context,start,start+timedelta(hours=2))
    assert result['compared_minutes']==120 and result['coverage_percent']==100
    assert summarize_agreement({'hourly_forecast':{'2026-11-01T01:00':next(iter(rows.values()))}},context,start,start+timedelta(hours=2))['state']=='unavailable'
