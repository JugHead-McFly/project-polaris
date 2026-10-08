from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user
from app.api.sky_view import SkyViewRequest, calculate_view
from app.core.planning_context import ObservatoryContext
from app.services.astronomy_service import get_horizontal_positions_at


def payload():
    return {'at':'2026-10-08T00:00:00Z','location':{'latitude':0.,'longitude':0.,'elevation_meters':0.,'timezone_name':'UTC'},'targets':['M31','M57','M13']}


def test_actual_positions_match_existing_astronomy_and_no_plan_or_db_writes():
    request=SkyViewRequest.model_validate(payload())
    with patch('sqlalchemy.orm.Session.execute',side_effect=AssertionError('No DB')), patch('app.services.planner_service.get_tonight_plan',side_effect=AssertionError('No plan')):
        response=TestClient(app).post('/sky-view/positions',json=payload())
    assert response.status_code==200
    result=response.json();assert not result['applied_to_tonight'];assert response.headers['cache-control']=='no-store'
    context=ObservatoryContext(name='Synthetic',**request.location.model_dump())
    for row in result['targets']:
        expected=get_horizontal_positions_at(row['id'],[request.at],observatory=context)[0]
        assert row['azimuth_degrees']==pytest.approx(expected[0],abs=1e-10)
        assert row['altitude_degrees']==pytest.approx(expected[1],abs=1e-10)


def test_time_location_and_offset_equivalence():
    first=calculate_view(SkyViewRequest.model_validate(payload()))
    offset=payload();offset['at']='2026-10-07T17:00:00-07:00';offset['location']['timezone_name']='America/Phoenix'
    same=calculate_view(SkyViewRequest.model_validate(offset));assert first['targets']==same['targets']
    assert same['at_local'].endswith('-07:00') and same['at_utc']==first['at_utc']
    for update in ['time','location']:
        changed=payload()
        if update=='time':changed['at']='2026-10-08T04:00:00Z'
        else:changed['location'].update(latitude=45.,longitude=120.)
        result=calculate_view(SkyViewRequest.model_validate(changed));assert result['targets']!=first['targets']


def test_dst_fold_is_two_distinct_instants_with_explicit_offsets():
    request=payload();request['location']['timezone_name']='America/New_York'
    request['at']='2026-11-01T01:30:00-04:00';a=calculate_view(SkyViewRequest.model_validate(request))
    request['at']='2026-11-01T01:30:00-05:00';b=calculate_view(SkyViewRequest.model_validate(request))
    assert a['at_utc']!=b['at_utc'];assert a['targets']!=b['targets'];assert a['at_local'].endswith('-04:00');assert b['at_local'].endswith('-05:00')


@pytest.mark.parametrize('change',[
 lambda p:p.update(at='2026-10-08T00:00:00'),lambda p:p.update(at=0),lambda p:p.update(at='0001-01-01T00:00:00+14:00'),lambda p:p.update(at='9999-12-31T23:00:00-14:00'),lambda p:p.update(at='2200-01-01T00:00:00Z'),
 lambda p:p['location'].update(latitude=91),lambda p:p['location'].update(longitude=True),lambda p:p['location'].update(timezone_name='Bad/Zone'),
 lambda p:p.update(targets=[]),lambda p:p.update(targets=['M31','m31']),lambda p:p.update(targets=['Unknown']),lambda p:p.update(targets=['M31']*13),lambda p:p.update(skyline={}),
])
def test_invalid_input_fails_without_calculation(change):
    body=payload();change(body)
    with patch('app.api.sky_view.get_horizontal_positions_at',side_effect=AssertionError('No computation')):
        assert TestClient(app).post('/sky-view/positions',json=body).status_code==422


def test_seam_below_horizon_and_unavailable_have_honest_states():
    with patch('app.api.sky_view.get_horizontal_positions_at',side_effect=[[(-.1,20)],[(360.1,-5)],[None]]):
        rows=calculate_view(SkyViewRequest.model_validate(payload()))['targets']
    assert rows[0]['azimuth_degrees']==pytest.approx(359.9)
    assert rows[1]['azimuth_degrees']==pytest.approx(.1) and rows[1]['status']=='below_horizon'
    assert rows[2]['status']=='unavailable' and rows[2]['altitude_degrees'] is None


def test_routes_require_auth_and_catalog_is_bounded_known_names():
    client=TestClient(app);catalog=client.get('/sky-view/catalog');assert catalog.status_code==200
    assert any(row['id']=='M31' for row in catalog.json())
    def deny():raise HTTPException(401,'Sign in')
    app.dependency_overrides[get_current_user]=deny
    try:
        for route in ['/sky-view/catalog','/sky-view/home']:
            assert client.get(route).status_code==401
        assert client.post('/sky-view/positions',json=payload()).status_code==401
    finally:app.dependency_overrides.pop(get_current_user)


def test_home_uses_existing_current_user_context():
    home=ObservatoryContext(name='Synthetic home',latitude=35,longitude=-105,elevation_meters=2000,timezone_name='America/Denver')
    with patch('app.api.sky_view.get_planning_context',return_value=home) as resolve:
        result=TestClient(app).get('/sky-view/home')
    assert result.status_code==200 and result.json()['latitude']==35
    assert resolve.call_args.kwargs['current_user'] is not None


def test_real_home_context_is_account_isolated():
    from uuid import uuid4
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.core.auth import CurrentUser
    from app.database.database import Base, get_tenant_db
    from app.models import Profile, HostedObservatory
    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine);factory=sessionmaker(bind=engine)
    users=[CurrentUser(user_id=uuid4(),auth_mode='supabase') for _ in range(2)]
    with factory() as db:
        for user,lat in zip(users,[12.,48.]):
            db.add(Profile(user_id=user.user_id));db.flush()
            db.add(HostedObservatory(user_id=user.user_id,name='Synthetic',latitude=lat,longitude=0,timezone_name='UTC'))
        db.commit()
    def database():
        with factory() as db:yield db
    app.dependency_overrides[get_tenant_db]=database
    try:
        for user,lat in zip(users,[12.,48.]):
            app.dependency_overrides[get_current_user]=lambda user=user:user
            assert TestClient(app).get('/sky-view/home').json()['latitude']==lat
    finally:
        app.dependency_overrides.pop(get_current_user);app.dependency_overrides.pop(get_tenant_db);engine.dispose()
