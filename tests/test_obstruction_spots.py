from copy import deepcopy
from uuid import UUID, uuid4
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.core.auth import CurrentUser, get_current_user
from app.database.database import Base, get_tenant_db
from app.models import Profile, HostedObservatory, ObstructionSpot
from app.api.tonight import _build_tonight_payload


@pytest.fixture
def setup():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    event.listen(engine, 'connect', lambda conn, _: conn.execute('PRAGMA foreign_keys=ON'))
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine)
    alice=CurrentUser(user_id=uuid4(),auth_mode='supabase')
    bob=CurrentUser(user_id=uuid4(),auth_mode='supabase')
    with factory() as db:
        db.add_all([Profile(user_id=alice.user_id),Profile(user_id=bob.user_id)]);db.flush()
        homes=[HostedObservatory(user_id=u.user_id,name='Home',latitude=30,longitude=-110,timezone_name='America/Phoenix') for u in [alice,alice,bob]]
        db.add_all(homes);db.commit(); ids=[h.id for h in homes]
    def database():
        with factory() as db:yield db
    app.dependency_overrides[get_tenant_db]=database
    app.dependency_overrides[get_current_user]=lambda:alice
    payload={'name':'Patio tripod','source_quality':'manual_measured','reviewed':True,'profile':{
        'complete_coverage':True,'clearance_degrees':1,'horizon':[{'azimuth_degrees':0,'altitude_degrees':10},{'azimuth_degrees':180,'altitude_degrees':10}],'sectors':[]}}
    yield TestClient(app),factory,alice,bob,ids,payload
    app.dependency_overrides.pop(get_tenant_db);app.dependency_overrides.pop(get_current_user)
    engine.dispose()


def path(home):return f'/observatories/{home}/obstruction-spots'


def test_crud_cas_owner_home_and_delete(setup):
    client,factory,alice,bob,homes,payload=setup
    created=client.post(path(homes[0]),json=payload);assert created.status_code==201
    spot=created.json();assert spot['revision']==1 and spot['available_for_tonight']
    assert created.headers['cache-control']=='no-store'
    assert client.get(path(homes[1])).json()==[]
    changed={**payload,'name':'Patio new','expected_revision':1}
    assert client.put(path(homes[1])+'/'+spot['id'],json=changed).status_code==409
    app.dependency_overrides[get_current_user]=lambda:bob
    assert client.get(path(homes[0])).status_code==404
    assert client.put(path(homes[0])+'/'+spot['id'],json=changed).status_code==404
    app.dependency_overrides[get_current_user]=lambda:alice
    assert client.put(path(homes[0])+'/'+spot['id'],json=changed).json()['revision']==2
    assert client.put(path(homes[0])+'/'+spot['id'],json=changed).status_code==409
    assert client.delete(path(homes[0])+'/'+spot['id']+'?expected_revision=1').status_code==409
    assert client.delete(path(homes[0])+'/'+spot['id']+'?expected_revision=2').status_code==204
    assert client.get(path(homes[0])).json()==[]


def test_home_change_requires_review_and_resave(setup):
    client,factory,alice,bob,homes,payload=setup
    spot=client.post(path(homes[0]),json=payload).json()
    with factory() as db:
        home=db.get(HostedObservatory,homes[0]);home.latitude=31;db.commit()
    assert not client.get(path(homes[0])).json()[0]['available_for_tonight']
    result=client.post(f'/tonight?obstruction_spot_id={spot["id"]}&obstruction_revision=1')
    assert result.status_code==409 and 'home or rig changed' in result.json()['detail']
    assert client.put(path(homes[0])+'/'+spot['id'],json={**payload,'expected_revision':1}).json()['available_for_tonight']


@pytest.mark.parametrize('mutate',[lambda p:p.update(reviewed=False),lambda p:p.update(reviewed='true'),lambda p:p.update(source_quality='photo_estimate'),lambda p:p.update(name=' '),lambda p:p.update(expected_revision=True),lambda p:p['profile'].update(complete_coverage=False),lambda p:p.update(user_id=str(uuid4()))])
def test_invalid_write_rejected(setup,mutate):
    client,_,_,_,homes,payload=setup;mutate(payload)
    assert client.post(path(homes[0]),json=payload).status_code==422
    assert client.get(path(homes[0])).json()==[]


def test_tonight_attaches_validated_snapshot_and_off_parity(setup):
    client,factory,alice,_,homes,payload=setup
    spot=client.post(path(homes[0]),json=payload).json()
    class StopAtPlanner(Exception):pass
    contexts=[]
    def planner(*args,**kwargs):contexts.append(kwargs['observatory']);raise StopAtPlanner()
    with factory() as db, patch('app.api.tonight.get_tonight_plan',side_effect=planner):
        with pytest.raises(StopAtPlanner):_build_tonight_payload(alice,db)
        with pytest.raises(StopAtPlanner):_build_tonight_payload(alice,db,obstruction_spot_id=UUID(spot['id']),obstruction_revision=1)
    assert contexts[0].obstruction_profile is None
    assert contexts[1].obstruction_profile.model_dump(mode='json')==payload['profile']
    assert contexts[1].timezone_name==contexts[0].timezone_name


def test_tonight_stale_unknown_foreign_and_synthetic_fail_before_planning(setup):
    client,factory,alice,bob,homes,payload=setup
    spot=client.post(path(homes[0]),json=payload).json()
    with patch('app.api.tonight.get_tonight_plan',side_effect=AssertionError('Must not plan')):
        for suffix in [f'obstruction_spot_id={spot["id"]}&obstruction_revision=2',f'obstruction_spot_id={uuid4()}&obstruction_revision=1',f'obstruction_spot_id={spot["id"]}', 'obstruction_revision=1']:
            assert client.post('/tonight?'+suffix).status_code in (409,422)
        app.dependency_overrides[get_current_user]=lambda:bob
        assert client.post(f'/tonight?obstruction_spot_id={spot["id"]}&obstruction_revision=1').status_code==409
        app.dependency_overrides[get_current_user]=lambda:alice
        client.put(path(homes[0])+'/'+spot['id'],json={**payload,'source_quality':'synthetic','expected_revision':1})
        assert client.post(f'/tonight?obstruction_spot_id={spot["id"]}&obstruction_revision=2').status_code==409


def test_invalid_persisted_profile_fails_closed(setup):
    client,factory,_,_,homes,payload=setup
    spot=client.post(path(homes[0]),json=payload).json()
    with factory() as db:
        row=db.get(ObstructionSpot,UUID(spot['id']));row.profile={};db.commit()
    assert not client.get(path(homes[0])).json()[0]['available_for_tonight']
    assert client.post(f'/tonight?obstruction_spot_id={spot["id"]}&obstruction_revision=1').status_code==409


def test_body_bound_and_duplicate_fields(setup):
    client,_,_,_,homes,_=setup
    headers={'content-type':'application/json'}
    assert client.post(path(homes[0]),content=b' '*(128*1024+1),headers=headers).status_code==413
    assert client.post(path(homes[0]),content='{"name":"a","name":"b"}',headers=headers).status_code==422


def test_home_api_change_and_revert_does_not_restore_confirmation(setup):
    client,_,_,_,homes,payload=setup
    spot=client.post(path(homes[0]),json=payload).json()
    for latitude in [31,30]:
        assert client.patch(f'/observatories/{homes[0]}',json={'latitude':latitude}).status_code==200
    current=client.get(path(homes[0])).json()[0]
    assert current['revision']==3
    assert not current['available_for_tonight']
    assert client.put(path(homes[0])+'/'+spot['id'],json={**payload,'expected_revision':1}).status_code==409
    saved=client.put(path(homes[0])+'/'+spot['id'],json={**payload,'expected_revision':3}).json()
    assert saved['revision']==4 and saved['available_for_tonight']


def test_owner_fk_and_delete_cascade(setup):
    from sqlalchemy.exc import IntegrityError
    client,factory,alice,bob,homes,payload=setup
    spot=client.post(path(homes[0]),json=payload).json()
    with factory() as db:
        row=db.get(ObstructionSpot,UUID(spot['id']));row.user_id=bob.user_id
        with pytest.raises(IntegrityError):db.commit()
    assert client.delete(f'/observatories/{homes[0]}').status_code==204
    with factory() as db:assert db.get(ObstructionSpot,UUID(spot['id'])) is None


def test_resolved_provenance_is_an_independent_snapshot(setup):
    from app.services.obstruction_spot_service import resolve_spot
    client,factory,alice,_,homes,payload=setup
    spot=client.post(path(homes[0]),json=payload).json()
    with factory() as db:
        profile,provenance=resolve_spot(db,alice,db.get(HostedObservatory,homes[0]),UUID(spot['id']),1)
    changed=deepcopy(payload);changed['profile']['clearance_degrees']=5;changed['expected_revision']=1
    client.put(path(homes[0])+'/'+spot['id'],json=changed)
    assert provenance['revision']==1
    assert provenance['source_quality']=='manual_measured'
    assert provenance['profile']['clearance_degrees']==1
    assert profile.clearance_degrees==1


def test_saved_spot_same_owner_wrong_home_cannot_plan(setup):
    client,_,_,_,homes,payload=setup
    spot=client.post(path(homes[1]),json=payload).json()
    with patch('app.api.tonight.get_tonight_plan',side_effect=AssertionError('Must not plan')):
        assert client.post(f'/tonight?obstruction_spot_id={spot["id"]}&obstruction_revision=1').status_code==409


def test_recommendation_history_keeps_applied_snapshot_after_spot_delete(setup):
    from app.services.obstruction_spot_service import resolve_spot
    from app.services.hosted_recommendation_service import create_recommendation_run
    from app.models import RecommendationRun
    client,factory,alice,_,homes,payload=setup
    spot=client.post(path(homes[0]),json=payload).json()
    with factory() as db:
        home=db.get(HostedObservatory,homes[0])
        _,provenance=resolve_spot(db,alice,home,UUID(spot['id']),1)
        run=create_recommendation_run(db,user_id=alice.user_id,observatory=home,payload={
            'schedule':{'decision':'Do Not Image','blocks':[],'notes':[]},
            'weather':{},'darkness':{},'moon':{},'message':'Synthetic fixture',
            'obstruction':provenance})
        run_id=run.id
    assert client.delete(path(homes[0])+'/'+spot['id']+'?expected_revision=1').status_code==204
    with factory() as db:
        saved=db.get(RecommendationRun,run_id).input_provenance['obstruction']
        assert saved['spot_id']==spot['id'] and saved['revision']==1
        assert saved['profile']==payload['profile']
