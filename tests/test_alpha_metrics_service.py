from datetime import datetime
from datetime import timezone
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.models import HostedObservatory
from app.models import Profile
from app.models import RecommendationFeedback
from app.models import RecommendationRun
from app.services.alpha_metrics_service import build_alpha_metrics_report


ALICE_ID = UUID("4d3d6526-f7ce-4e5a-a4d9-4dca6bf671ba")
BOB_ID = UUID("97cc45e6-7767-4f72-9ce4-8d7c23e64606")


def _database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


def _add_run(database, observatory, planned_for, outcome):
    run = RecommendationRun(
        user_id=observatory.user_id,
        observatory_id=observatory.id,
        planned_for=planned_for,
        outcome=outcome,
        explanation={},
        input_provenance={},
        planner_version="Planner V3",
    )
    database.add(run)
    database.flush()
    return run


def test_alpha_metrics_are_aggregate_and_track_repeat_planning():
    engine, database = _database()
    try:
        alice_home = HostedObservatory(
            user_id=ALICE_ID,
            name="Private Alice Home",
            latitude=33.45,
            longitude=-112.07,
            timezone_name="America/Phoenix",
        )
        bob_home = HostedObservatory(
            user_id=BOB_ID,
            name="Private Bob Home",
            latitude=-33.87,
            longitude=151.21,
            timezone_name="Australia/Sydney",
        )
        database.add_all(
            [
                Profile(user_id=ALICE_ID, display_name="Alice"),
                Profile(user_id=BOB_ID, display_name="Bob"),
                alice_home,
                bob_home,
            ]
        )
        database.flush()
        first_run = _add_run(
            database,
            alice_home,
            datetime(2026, 7, 27, 3, tzinfo=timezone.utc),
            "Proceed",
        )
        _add_run(
            database,
            alice_home,
            datetime(2026, 7, 28, 3, tzinfo=timezone.utc),
            "Use Caution",
        )
        _add_run(
            database,
            bob_home,
            datetime(2026, 7, 28, 3, tzinfo=timezone.utc),
            "Do Not Image",
        )
        database.add(
            RecommendationFeedback(
                user_id=ALICE_ID,
                observatory_id=alice_home.id,
                recommendation_run_id=first_run.id,
                useful=True,
                reason="Private feedback text is never reported.",
            )
        )
        database.commit()

        report = build_alpha_metrics_report(database)
    finally:
        database.close()
        engine.dispose()

    assert report["accounts"] == {
        "profiles_created": 2,
        "with_observing_home": 2,
        "with_saved_plan": 2,
        "returning_for_two_or_more_nights": 1,
    }
    assert report["recommendations"]["saved"] == 3
    assert report["recommendations"]["by_outcome"] == {
        "Do Not Image": 1,
        "Proceed": 1,
        "Use Caution": 1,
    }
    assert report["feedback"] == {
        "responses": 1,
        "useful": 1,
        "not_useful": 0,
        "response_rate_percent": 33.3,
    }
    rendered = str(report)
    assert "Alice" not in rendered
    assert "Bob" not in rendered
    assert "Private feedback" not in rendered
    assert "33.45" not in rendered


def test_alpha_metrics_handles_an_empty_alpha():
    engine, database = _database()
    try:
        report = build_alpha_metrics_report(database)
    finally:
        database.close()
        engine.dispose()

    assert report["accounts"]["profiles_created"] == 0
    assert report["recommendations"] == {
        "saved": 0,
        "by_outcome": {},
        "first_saved_at": None,
        "last_saved_at": None,
    }
    assert report["feedback"]["response_rate_percent"] is None
