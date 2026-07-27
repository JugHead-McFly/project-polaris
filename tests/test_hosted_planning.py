from datetime import datetime
from unittest.mock import patch
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.tonight import tonight
from app.core.auth import CurrentUser
from app.data.targets import TARGETS
from app.database.database import Base
from app.models import HostedObservatory
from app.models import Profile
from app.services.advisor_service import get_catalog_exposure_advice
from app.services.hosted_account_service import get_planning_context
from app.services.planner_service import build_target_plan


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
                side_effect=lambda planner, timezone_name: _schedule_response(
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


def test_hosted_catalog_recommends_a_filter_for_every_supported_target():
    recommendations = {
        target_name: get_catalog_exposure_advice(target_name)[
            "recommended_filter"
        ]
        for target_name in TARGETS
    }

    assert recommendations["C 20"] == "Duo-Band"
    assert set(recommendations.values()) <= {"Duo-Band", "Astro"}
