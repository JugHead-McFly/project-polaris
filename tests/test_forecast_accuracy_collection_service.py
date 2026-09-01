from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.database.database import TENANT_SESSION_KEY
from app.models import HostedObservatory
from app.models import Profile
from app.services import forecast_accuracy_collection_service
from scripts.collect_forecast_accuracy import parse_user_ids


ALICE_ID = UUID("33466ab6-6a44-485b-89b2-15b7fb31c207")
BOB_ID = UUID("7d30b290-5497-4963-81e9-f5a3f6d92c85")


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    db.add_all([Profile(user_id=ALICE_ID), Profile(user_id=BOB_ID)])
    db.add(
        HostedObservatory(
            user_id=ALICE_ID,
            name="Alice Home",
            latitude=33.3,
            longitude=-111.7,
            timezone_name="America/Phoenix",
        )
    )
    db.commit()
    db.close()
    return factory


def test_collector_uses_one_tenant_scoped_session_per_configured_user(
    monkeypatch,
):
    factory = _session_factory()
    tenant_contexts = []
    planned_users = []
    tracked_users = []

    real_get_primary_observatory = (
        forecast_accuracy_collection_service.get_primary_observatory
    )

    def recording_get_primary_observatory(db, *, user_id):
        tenant_contexts.append(db.info[TENANT_SESSION_KEY])
        return real_get_primary_observatory(db, user_id=user_id)

    def fake_plan(db, **kwargs):
        planned_users.append(db.info[TENANT_SESSION_KEY])
        return {"weather": {"status": "Weather unavailable"}}

    def fake_track(db, *, user_id, observatory, weather):
        tracked_users.append(user_id)
        return {}

    monkeypatch.setattr(
        forecast_accuracy_collection_service,
        "get_primary_observatory",
        recording_get_primary_observatory,
    )
    monkeypatch.setattr(
        forecast_accuracy_collection_service,
        "get_tonight_plan",
        fake_plan,
    )
    monkeypatch.setattr(
        forecast_accuracy_collection_service,
        "track_forecast_accuracy",
        fake_track,
    )

    report = forecast_accuracy_collection_service.collect_forecast_accuracy(
        [ALICE_ID, ALICE_ID, BOB_ID],
        session_factory=factory,
    )

    assert tenant_contexts == [ALICE_ID, BOB_ID]
    assert planned_users == [ALICE_ID]
    assert tracked_users == [ALICE_ID]
    assert report == {
        "configured_tenants": 2,
        "processed_tenants": 1,
        "skipped_without_observatory": 1,
        "failed_tenants": 0,
    }


def test_collector_reports_failure_without_stopping_other_tenants(monkeypatch):
    factory = _session_factory()

    def fail_plan(db, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        forecast_accuracy_collection_service,
        "get_tonight_plan",
        fail_plan,
    )

    report = forecast_accuracy_collection_service.collect_forecast_accuracy(
        [ALICE_ID, BOB_ID],
        session_factory=factory,
    )

    assert report["failed_tenants"] == 1
    assert report["skipped_without_observatory"] == 1


def test_parse_user_ids_requires_valid_deduplicated_allowlist():
    assert parse_user_ids(f" {ALICE_ID}, {ALICE_ID}, {BOB_ID} ") == (
        ALICE_ID,
        BOB_ID,
    )

    with pytest.raises(ValueError) as error:
        parse_user_ids("not-a-uuid")

    assert "comma-separated list of UUIDs" in str(error.value)
