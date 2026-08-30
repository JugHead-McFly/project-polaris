from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest.mock import patch
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.tonight import tonight
from app.api.tonight import create_tonight_recommendation
from app.core.auth import CurrentUser
from app.data.targets import TARGETS
from app.database.database import Base
from app.models import HostedObservatory
from app.models import ForecastAccuracySnapshot
from app.models import Profile
from app.models import RecommendationFeedback
from app.models import RecommendationRun
from app.services.advisor_service import get_catalog_exposure_advice
from app.services.hosted_account_service import get_planning_context
from app.services.hosted_recommendation_service import (
    save_recommendation_feedback,
)
from app.services.planner_service import build_target_plan
from app.services.planner_service import get_dark_visibility


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


def _user(user_id):
    return CurrentUser(
        user_id=user_id,
        email=None,
        auth_mode="supabase",
    )


def _planner_response():
    return {
        "recommended_target": None,
        "best_theoretical_target": None,
        "alternatives": [],
        "weather": {
            "postal_code": None,
            "observing_rating": 0,
            "status": "Weather unavailable",
        },
        "moon": {
            "illumination_percent": 20.0,
            "altitude_degrees": -5.0,
            "above_horizon": False,
            "next_moonrise": "2026-07-27 08:00 PM",
            "next_moonset": "2026-07-27 08:00 AM",
        },
        "darkness": {
            "sunset": "2026-07-26 07:00 PM",
            "astronomical_darkness_start": "2026-07-26 09:00 PM",
            "astronomical_darkness_end": "2026-07-27 04:00 AM",
        },
        "decision": "Do Not Image",
        "notes": [],
    }


def _schedule_response(planner, date):
    return {
        "date": date,
        "decision": planner["decision"],
        "advisory_only": True,
        "blocks": [],
        "allocated_minutes": 0,
        "unscheduled_dark_minutes": 420,
        "weather": planner["weather"],
        "moon": planner["moon"],
        "darkness": planner["darkness"],
        "notes": [],
        "fallback_target": None,
    }


def test_hosted_plans_use_each_users_own_observatory():
    engine, db = _database()
    try:
        db.add_all(
            [
                Profile(user_id=ALICE_ID),
                Profile(user_id=BOB_ID),
                HostedObservatory(
                    user_id=ALICE_ID,
                    name="Alice Arizona",
                    latitude=33.45,
                    longitude=-112.07,
                    timezone_name="America/Phoenix",
                ),
                HostedObservatory(
                    user_id=BOB_ID,
                    name="Bob Sydney",
                    latitude=-33.87,
                    longitude=151.21,
                    timezone_name="Australia/Sydney",
                ),
            ]
        )
        db.commit()

        observed_contexts = []

        def planner_side_effect(
            database,
            observatory,
            use_capture_history,
            equatorial_mode_enabled=False,
        ):
            observed_contexts.append(
                (observatory, use_capture_history)
            )
            return _planner_response()

        with (
            patch(
                "app.api.tonight.get_tonight_plan",
                side_effect=planner_side_effect,
            ),
            patch(
                "app.api.tonight.build_tonight_schedule",
                side_effect=lambda planner, timezone_name, **kwargs: _schedule_response(
                    planner,
                    "2026-07-26",
                ),
            ),
        ):
            alice = tonight(current_user=_user(ALICE_ID), db=db)
            bob = tonight(current_user=_user(BOB_ID), db=db)
    finally:
        db.close()
        engine.dispose()

    assert alice["observatory"]["name"] == "Alice Arizona"
    assert bob["observatory"]["name"] == "Bob Sydney"
    assert observed_contexts[0][0].longitude == -112.07
    assert observed_contexts[1][0].longitude == 151.21
    assert observed_contexts[0][1] is False
    assert observed_contexts[1][1] is False


def test_hosted_plan_requires_an_observing_home():
    engine, db = _database()
    try:
        db.add(Profile(user_id=ALICE_ID))
        db.commit()

        with pytest.raises(HTTPException) as raised:
            tonight(current_user=_user(ALICE_ID), db=db)
    finally:
        db.close()
        engine.dispose()

    assert raised.value.status_code == 409


def test_hosted_read_only_plan_reports_saved_forecast_history():
    engine, db = _database()
    try:
        profile = Profile(user_id=ALICE_ID)
        observatory = HostedObservatory(
            user_id=ALICE_ID,
            name="Alice Arizona",
            latitude=33.45,
            longitude=-112.07,
            timezone_name="America/Phoenix",
        )
        db.add_all([profile, observatory])
        db.commit()
        db.refresh(observatory)
        checked_at = datetime(2026, 7, 26, 18, tzinfo=timezone.utc)
        db.add(
            ForecastAccuracySnapshot(
                user_id=ALICE_ID,
                observatory_id=observatory.id,
                forecast_for=checked_at,
                forecast_created_at=checked_at - timedelta(hours=12),
                expires_at=checked_at + timedelta(hours=2),
                observed_at=checked_at,
                status="matched",
            )
        )
        db.commit()

        with (
            patch(
                "app.api.tonight.get_tonight_plan",
                return_value=_planner_response(),
            ),
            patch(
                "app.api.tonight.build_tonight_schedule",
                side_effect=lambda plan, timezone_name, **kwargs: _schedule_response(
                    plan,
                    "2026-07-26",
                ),
            ),
        ):
            payload = tonight(current_user=_user(ALICE_ID), db=db)
    finally:
        db.close()
        engine.dispose()

    assert payload["forecast_accuracy"]["matched_samples"] == 1
    assert payload["forecast_accuracy"]["confidence"] is None


def test_hosted_recommendation_is_saved_for_its_owner():
    engine, db = _database()
    try:
        db.add(Profile(user_id=ALICE_ID))
        db.add(
            HostedObservatory(
                user_id=ALICE_ID,
                name="Alice Arizona",
                latitude=33.45,
                longitude=-112.07,
                timezone_name="America/Phoenix",
            )
        )
        db.commit()

        planner = _planner_response()
        planner["weather"]["observed_at"] = (
            "2026-07-26T19:15:00-07:00"
        )
        with (
            patch(
                "app.api.tonight.get_tonight_plan",
                return_value=planner,
            ),
            patch(
                "app.api.tonight.build_tonight_schedule",
                side_effect=lambda plan, timezone_name, **kwargs: _schedule_response(
                    plan,
                    "2026-07-26",
                ),
            ),
        ):
            payload = create_tonight_recommendation(
                current_user=_user(ALICE_ID),
                db=db,
            )

        saved = db.query(RecommendationRun).one()
        assert payload["recommendation_run_id"] == saved.id
        assert saved.user_id == ALICE_ID
        assert saved.outcome == "Do Not Image"
        assert saved.primary_target is None
        assert saved.observatory_id is not None
        assert saved.input_provenance[
            "coordinates_are_approximate"
        ] is True
        assert "latitude" not in saved.input_provenance
        assert saved.forecast_observed_at.isoformat().startswith(
            "2026-07-27T02:15:00"
        )
    finally:
        db.close()
        engine.dispose()


def test_feedback_updates_without_crossing_user_boundary():
    engine, db = _database()
    try:
        alice_observatory = HostedObservatory(
            user_id=ALICE_ID,
            name="Alice Arizona",
            latitude=33.45,
            longitude=-112.07,
            timezone_name="America/Phoenix",
        )
        db.add_all(
            [
                Profile(user_id=ALICE_ID),
                Profile(user_id=BOB_ID),
                alice_observatory,
            ]
        )
        db.commit()
        run = RecommendationRun(
            user_id=ALICE_ID,
            observatory_id=alice_observatory.id,
            planned_for=datetime.now(ZoneInfo("UTC")),
            outcome="Proceed",
            primary_target="M57",
            explanation={},
            input_provenance={},
            planner_version="Planner V3",
        )
        db.add(run)
        db.commit()

        alice_feedback = save_recommendation_feedback(
            db,
            user_id=ALICE_ID,
            recommendation_run_id=run.id,
            useful=True,
        )
        blocked_feedback = save_recommendation_feedback(
            db,
            user_id=BOB_ID,
            recommendation_run_id=run.id,
            useful=False,
        )
        updated_feedback = save_recommendation_feedback(
            db,
            user_id=ALICE_ID,
            recommendation_run_id=run.id,
            useful=False,
            reason="The setup steps were unclear.",
        )

        assert alice_feedback is not None
        assert blocked_feedback is None
        assert updated_feedback.id == alice_feedback.id
        assert updated_feedback.useful is False
        assert updated_feedback.reason == "The setup steps were unclear."
        assert db.query(RecommendationFeedback).count() == 1
    finally:
        db.close()
        engine.dispose()


def test_local_planning_context_remains_dougs_observatory():
    engine, db = _database()
    try:
        context = get_planning_context(
            db,
            current_user=CurrentUser(
                user_id=ALICE_ID,
                email=None,
                auth_mode="local",
            ),
        )
    finally:
        db.close()
        engine.dispose()

    assert context.name == "Doug's Observatory"
    assert context.timezone_name == "America/Phoenix"
    assert context.rig_profile_key is None


def test_hosted_planning_context_includes_selected_rig_profile():
    engine, db = _database()
    try:
        db.add(
            Profile(
                user_id=ALICE_ID,
                display_name="Alice",
                onboarding_state="complete",
            )
        )
        db.add(
            HostedObservatory(
                user_id=ALICE_ID,
                name="Alice's Observatory",
                latitude=33.25,
                longitude=-111.75,
                timezone_name="America/Phoenix",
                bortle_class=6,
                rig_profile_key="dwarf-3",
            )
        )
        db.commit()

        context = get_planning_context(
            db,
            current_user=_user(ALICE_ID),
        )
    finally:
        db.close()
        engine.dispose()

    assert context.name == "Alice's Observatory"
    assert context.bortle_class == 6
    assert context.rig_profile_key == "dwarf-3"


def test_hosted_target_plan_does_not_query_private_capture_history():
    class PrivateCaptureDatabase:
        def query(self, *args, **kwargs):
            raise AssertionError("Hosted planning read private captures.")

    observatory = get_planning_context(
        object(),
        current_user=CurrentUser(
            user_id=ALICE_ID,
            email=None,
            auth_mode="local",
        ),
    )
    dark_start = datetime(
        2026,
        7,
        26,
        21,
        0,
        tzinfo=ZoneInfo("America/Phoenix"),
    )
    dark_end = datetime(
        2026,
        7,
        27,
        4,
        0,
        tzinfo=ZoneInfo("America/Phoenix"),
    )

    plan = build_target_plan(
        db=PrivateCaptureDatabase(),
        object_name="M57",
        dark_start=dark_start,
        dark_end=dark_end,
        observatory=observatory,
        use_capture_history=False,
    )

    assert plan["advisor"]["recommendation_source"] == "catalog_fallback"
    assert plan["advisor"]["current_integration_seconds"] == 0


def test_target_geometry_preserves_local_offset_across_midnight():
    timezone = ZoneInfo("America/New_York")
    dark_start = datetime(2026, 8, 23, 23, 45, tzinfo=timezone)
    dark_end = datetime(2026, 8, 24, 0, 15, tzinfo=timezone)

    with patch(
        "app.services.planner_service.get_altitudes_at",
        return_value=[30.0, 52.0, 44.0],
    ):
        visibility = get_dark_visibility(
            object_name="M31",
            dark_start=dark_start,
            dark_end=dark_end,
        )

    geometry = visibility["target_geometry"]
    assert geometry["peak_altitude_degrees"] == 52.0
    assert geometry["peak_at"] == "2026-08-24T00:00:00-04:00"
    assert geometry["peak_label"] == "12:00 AM next day"
    assert geometry["samples"][0]["label"] == "11:45 PM"
    assert geometry["samples"][-1]["label"] == "12:15 AM next day"


def test_target_geometry_is_absent_when_position_is_unknown():
    timezone = ZoneInfo("America/Phoenix")
    dark_start = datetime(2026, 8, 23, 20, 0, tzinfo=timezone)
    dark_end = datetime(2026, 8, 23, 20, 15, tzinfo=timezone)

    with patch(
        "app.services.planner_service.get_altitudes_at",
        return_value=[None, None],
    ):
        visibility = get_dark_visibility(
            object_name="UNRESOLVED",
            dark_start=dark_start,
            dark_end=dark_end,
        )

    assert visibility["known_position"] is False
    assert visibility["target_geometry"] is None


def test_hosted_catalog_recommends_a_filter_for_every_supported_target():
    recommendations = {
        target_name: get_catalog_exposure_advice(target_name)[
            "recommended_filter"
        ]
        for target_name in TARGETS
    }

    assert recommendations["C 20"] == "Duo-Band"
    assert set(recommendations.values()) <= {"Duo-Band", "Astro"}
