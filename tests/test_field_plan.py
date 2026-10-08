from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch, Mock
from uuid import uuid4

import pytest
from app.services.field_plan_service import build_field_plan, _build
from app.services.obstruction_spot_service import resolve_spot, home_binding
from app.schemas.obstruction_spot import SpotWrite


def payload():
    return {'date': '2026-10-08', 'observatory': {'name': 'Synthetic site', 'timezone': 'America/Phoenix',
            'latitude': 33.123456789, 'longitude': -110.987654321, 'rig_profile_label': 'Test rig'},
            'obstruction': {'mode': 'off'}, 'recommended_target': {'object': 'NOT SCHEDULED'},
            'schedule': {'date': '2026-10-08', 'decision': 'Proceed', 'notes': ['Recheck wind'], 'blocks': [
                {'object': 'M31', 'start': '2026-10-08 11:30 PM', 'end': '2026-10-09 01:00 AM',
                 'setup_minutes': 5, 'imaging_minutes': 85, 'recommendation_source': 'Synthetic settings',
                 'reason': 'Actual block', 'run_number': 1, 'total_runs': 1}]}}


def test_actual_blocks_cross_midnight_and_stable_ids_no_coordinates():
    source = payload(); original = deepcopy(source)
    a = _build(source, datetime(2026, 10, 8, tzinfo=timezone.utc))
    b = _build(source, datetime(2026, 10, 8, 1, tzinfo=timezone.utc))
    assert a['snapshot_id'] == b['snapshot_id']
    assert 'DTSTART:20261009T063000Z' in a['calendar']
    assert 'DTEND:20261009T080000Z' in a['calendar']
    assert 'NOT SCHEDULED' not in a['text']
    assert '33.123456789' not in a['text'] + a['calendar']
    assert a['text'] != b['text']
    assert source == original


@pytest.mark.parametrize('start,end,night', [
    ('2026-11-01 01:10 AM', '2026-11-01 01:40 AM', '2026-10-31'),
    ('2026-03-08 02:10 AM', '2026-03-08 03:40 AM', '2026-03-07'),
    ('2026-11-01 12:10 AM', '2026-11-01 03:40 AM', '2026-10-31'),
])
def test_dst_rejects_fold_gap_or_clock_change(start,end,night):
    p=payload();p['observatory']['timezone']='America/New_York'
    p['date']=p['schedule']['date']=night
    p['schedule']['blocks'][0].update(start=start,end=end)
    result=build_field_plan(p)
    assert result['text'] is None and result['calendar'] is None
    assert result['unavailable_reason']


def test_invalid_stale_date_overlap_unknown_zone_and_oversized_fail_without_mutation():
    for mutation in [lambda p:p.update(date='2026-09-01'),
                     lambda p:p['schedule']['blocks'][0].update(end='2026-10-08 10:00 PM'),
                     lambda p:p['schedule']['blocks'].append(deepcopy(p['schedule']['blocks'][0])),
                     lambda p:p['observatory'].update(timezone='Invalid/Zone'),
                     lambda p:p['schedule']['blocks'][0].update(reason='x'*4001)]:
        p=payload();mutation(p);before=deepcopy(p)
        assert build_field_plan(p)['text'] is None
        assert p==before


def test_empty_and_do_not_image_never_calendar():
    p=payload();p['schedule'].update(decision='Do Not Image',blocks=[])
    r=build_field_plan(p);assert 'No scheduled' in r['text'];assert r['calendar'] is None
    p['schedule']['blocks']=payload()['schedule']['blocks']
    assert build_field_plan(p)['calendar'] is None


def test_runs_kept_separate_ics_escaped_utf8_folded():
    p=payload();b=p['schedule']['blocks'][0]
    b['object']='星'*60+';,\\\nBEGIN:VEVENT';b['total_runs']=2
    second=deepcopy(b);second.update(start=b['end'],end='2026-10-09 02:00 AM',run_number=2)
    p['schedule']['blocks'].append(second)
    result=build_field_plan(p);ics=result['calendar']
    assert ics.count('\r\nBEGIN:VEVENT\r\n')==2
    assert all(len(line.encode())<=75 for line in ics.split('\r\n'))
    assert '\\;' in ics and '\\,' in ics
    assert 'run 2/2' in result['text']


def test_real_resolved_spot_provenance_contract():
    p=payload();user=SimpleNamespace(user_id=uuid4())
    home=SimpleNamespace(id=uuid4(),latitude=30.,longitude=40.,elevation_m=0.,timezone_name='UTC',rig_profile_key=None)
    write=SpotWrite.model_validate({'name':'Patio','source_quality':'manual_measured','reviewed':True,'profile':{
        'complete_coverage':True,'horizon':[{'azimuth_degrees':0.,'altitude_degrees':10.},{'azimuth_degrees':180.,'altitude_degrees':10.}], 'sectors':[]}})
    spot=SimpleNamespace(id=uuid4(),name=write.name,revision=2,schema_version=1,source_quality=write.source_quality,
        reviewed_at=datetime.now(timezone.utc),profile=write.profile.model_dump(mode='json'),home_binding=home_binding(home))
    query=Mock();query.filter_by.return_value.one_or_none.return_value=spot
    with patch('app.services.obstruction_spot_service.spot_query',return_value=query):
        _,p['obstruction']=resolve_spot(None,user,home,spot.id,2)
    r=build_field_plan(p)
    assert 'Patio; revision 2; source manual_measured' in r['text']
    assert 'horizon' not in r['calendar']


def test_real_tonight_route_schema_keeps_export_and_export_failure_keeps_plan():
    from fastapi.testclient import TestClient
    from app.main import app
    from tests.test_tonight_api import FakeDatabase, planner_response, schedule_response, target_response
    planner=planner_response()
    with patch('app.database.database.SessionLocal',return_value=FakeDatabase()), patch('app.api.tonight.get_tonight_plan',return_value=planner), patch('app.api.tonight.build_tonight_schedule',return_value=schedule_response(planner)), patch('app.api.tonight.build_target_response',side_effect=lambda db,target_name:target_response(target_name)):
        response=TestClient(app).get('/tonight');assert response.status_code==200
        data=response.json();assert data['field_plan']['text']
        for block in data['schedule']['blocks']:assert block['start'] in data['field_plan']['text']
        with patch('app.services.field_plan_service._build',side_effect=ValueError('Export unavailable')):
            response=TestClient(app).get('/tonight')
        assert response.status_code==200
        assert response.json()['schedule']==data['schedule']
        assert response.json()['field_plan']['unavailable_reason']=='Export unavailable'


def test_after_midnight_schedule_anchors_night_to_actual_darkness():
    p=payload();p['date']=p['schedule']['date']='2026-10-09'
    p['schedule']['darkness']={'astronomical_darkness_start':'2026-10-08 08:00 PM',
                               'astronomical_darkness_end':'2026-10-09 05:00 AM'}
    r=build_field_plan(p)
    assert r['night']=='2026-10-08'
    assert 'Night reference: 2026-10-08 (site-local darkness-start date)' in r['text']
    assert 'Schedule calculation date (site local): 2026-10-09' in r['text']
    assert 'DTSTART:20261009T063000Z' in r['calendar']
    p['date']=p['schedule']['date']='2026-10-10'
    assert build_field_plan(p)['text'] is None
    p['date']=p['schedule']['date']='2026-10-09'
    p['schedule']['blocks'][0]['start']='2026-10-08 07:00 PM'
    assert build_field_plan(p)['text'] is None


def test_summer_dusk_after_midnight_uses_actual_sunset_night():
    p=payload();p['date']=p['schedule']['date']='2026-05-20'
    p['observatory']['timezone']='Europe/Paris'
    p['schedule']['darkness']={'sunset':'2026-05-20 09:30 PM',
        'astronomical_darkness_start':'2026-05-21 12:14 AM',
        'astronomical_darkness_end':'2026-05-21 03:19 AM'}
    p['schedule']['blocks'][0].update(start='2026-05-21 12:30 AM',end='2026-05-21 02:00 AM')
    r=build_field_plan(p)
    assert r['night']=='2026-05-20'
    assert 'Night reference: 2026-05-20 (site-local sunset date)' in r['text']
    assert 'DTSTART:20260520T223000Z' in r['calendar']
    p['schedule']['darkness']['sunset']='2026-05-18 09:30 PM'
    assert build_field_plan(p)['text'] is None
