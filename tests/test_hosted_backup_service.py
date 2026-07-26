from datetime import datetime
from datetime import timezone
from uuid import UUID
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models import HostedObservatory
from app.models import Profile
from app.models import RecommendationFeedback
from app.models import RecommendationRun
from app.services.hosted_backup_service import HostedBackupError
from app.services.hosted_backup_service import export_hosted_tenant
from app.services.hosted_backup_service import restore_hosted_tenant
from app.services.hosted_backup_service import verify_hosted_tenant_export


ALICE_ID = UUID("d5fe97a5-dfc1-4a78-96b9-719dec266ca7")
BOB_ID = UUID("697d7fc2-a433-4cf7-a92f-5f917f93b899")


def database_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


def seed_tenant(database, user_id, name):
    profile = Profile(
        user_id=user_id,
        display_name=name,
        onboarding_state="complete",
    )
    observatory = HostedObservatory(
        id=uuid4(),
        user_id=user_id,
        name=f"{name} Observatory",
        latitude=33.25,
        longitude=-111.75,
        coordinates_are_approximate=True,
        elevation_m=390,
        timezone_name="America/Phoenix",
        bortle_class=6,
    )
    run = RecommendationRun(
        id=uuid4(),
        user_id=user_id,
        observatory_id=observatory.id,
        planned_for=datetime(2026, 7, 26, tzinfo=timezone.utc),
        forecast_observed_at=datetime(2026, 7, 25, tzinfo=timezone.utc),
        outcome="go",
        primary_target="M57",
        explanation={"reason": "clear"},
        input_provenance={"weather": "test"},
        planner_version="test",
    )
    feedback = RecommendationFeedback(
        id=uuid4(),
        user_id=user_id,
        observatory_id=observatory.id,
        recommendation_run_id=run.id,
        useful=True,
        reason="Accurate",
    )
    database.add_all([profile, observatory, run, feedback])
    database.commit()
    return observatory, run


def test_export_is_tenant_scoped_and_restores_to_empty_database():
    source_engine, source = database_session()
    target_engine, target = database_session()
    try:
        alice_observatory, alice_run = seed_tenant(
            source,
            ALICE_ID,
            "Alice",
        )
        seed_tenant(source, BOB_ID, "Bob")

        document = export_hosted_tenant(
            source,
            user_id=ALICE_ID,
            exported_at=datetime(2026, 7, 26, tzinfo=timezone.utc),
        )
        report = verify_hosted_tenant_export(document)
        restore_hosted_tenant(target, document=document)

        assert report["valid"]
        assert report["counts"] == {
            "profiles": 1,
            "observatories": 1,
            "recommendation_runs": 1,
            "recommendation_feedback": 1,
        }
        assert document["tables"]["profiles"][0]["user_id"] == str(
            ALICE_ID
        )
        assert target.query(Profile).one().user_id == ALICE_ID
        assert (
            target.query(HostedObservatory).one().id
            == alice_observatory.id
        )
        assert target.query(RecommendationRun).one().id == alice_run.id
        assert target.query(RecommendationFeedback).count() == 1
    finally:
        source.close()
        target.close()
        source_engine.dispose()
        target_engine.dispose()


def test_tampered_export_is_rejected_before_restore():
    source_engine, source = database_session()
    target_engine, target = database_session()
    try:
        seed_tenant(source, ALICE_ID, "Alice")
        document = export_hosted_tenant(source, user_id=ALICE_ID)
        document["tables"]["observatories"][0]["name"] = "Tampered"

        report = verify_hosted_tenant_export(document)

        assert not report["valid"]
        assert "Backup checksum does not match its payload." in report[
            "errors"
        ]
        with pytest.raises(HostedBackupError):
            restore_hosted_tenant(target, document=document)
        assert target.query(Profile).count() == 0
    finally:
        source.close()
        target.close()
        source_engine.dispose()
        target_engine.dispose()
