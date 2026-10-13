from uuid import uuid4
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.database.database import Base, TENANT_SESSION_KEY
from app.models import Profile, LegacyCapture
from app.services.legacy_capture_service import import_legacy_records, legacy_summary
from app.services.capture_history_service import library_summary, progress_map


@pytest.fixture
def db():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def owner(db):
    key = uuid4(); db.add(Profile(user_id=key)); db.commit()
    db.info[TENANT_SESSION_KEY] = key
    return key


def record(key='a', seconds=3600):
    return dict(source_key=key*64, target='M 31', basis='legacy_stack_metadata',
                original_observation_time='2026-06-12T05:32:03',
                reported_integration_seconds=seconds, flags=['timezone_unconfirmed'])


def test_repeat_import_is_idempotent_and_does_not_credit_verified_time(db):
    user = owner(db)
    before = progress_map(library_summary(db,user))
    assert import_legacy_records(db,user,[record()])['records_added']==1
    db.commit()
    assert import_legacy_records(db,user,[record()])['records_unchanged']==1
    summary=library_summary(db,user)
    assert summary['legacy']['record_count']==1
    assert summary['session_count']==0
    assert progress_map(summary)==before


def test_same_source_can_belong_to_two_owners_without_mixing(db):
    first=owner(db); second=owner(db)
    db.info[TENANT_SESSION_KEY]=first
    import_legacy_records(db,first,[record()]);db.commit()
    assert legacy_summary(db,second)['record_count']==0
    db.info[TENANT_SESSION_KEY]=second
    import_legacy_records(db,second,[record(seconds=7200)]);db.commit()
    assert legacy_summary(db,first)['record_count']==1
    assert legacy_summary(db,second)['record_count']==1
    rows=db.scalars(select(LegacyCapture)).all()
    assert {r.user_id:r.reported_integration_seconds for r in rows}=={first:3600,second:7200}


def test_wrong_tenant_rejected(db):
    first=owner(db); owner(db)
    with pytest.raises(ValueError,match='tenant'):import_legacy_records(db,first,[record()])
    assert not db.scalars(select(LegacyCapture)).all()


def test_conflict_does_not_partially_insert_batch(db):
    user=owner(db);import_legacy_records(db,user,[record()]);db.commit()
    with pytest.raises(ValueError,match='conflicts'):
        import_legacy_records(db,user,[record('b'),record(seconds=7200)])
    assert len(db.scalars(select(LegacyCapture)).all())==1


def test_rollback_and_bad_evidence(db):
    user=owner(db)
    import_legacy_records(db,user,[record()]);db.rollback()
    assert legacy_summary(db,user)['record_count']==0
    bad=record();bad['basis']='verified_raw_frames'
    with pytest.raises(ValueError):import_legacy_records(db,user,[bad])
    with pytest.raises(ValueError):import_legacy_records(db,user,[record(),record()])
    with pytest.raises(ValueError):import_legacy_records(db,user,[record(seconds=float('nan'))])
    assert legacy_summary(db,user)['record_count']==0
