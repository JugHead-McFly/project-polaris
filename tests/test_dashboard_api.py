from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.database import Base
from app.main import app
from app.models import Capture
from app.models import CaptureAnalysis
from app.models import ObservingSession
from app.services.dashboard_service import build_dashboard_response


class FakeDatabase:
    closed = False

    def close(self):
        self.closed = True


def empty_dashboard_response():
    return {
        "api_version": settings.VERSION,
        "generated_at": "2026-07-17T12:00:00+00:00",
        "metrics": {
            "captures": 0,
            "targets": 0,
            "sessions": 0,
            "sessions_with_captures": 0,
            "analysis_records": 0,
            "total_integration_seconds": 0,
            "total_integration_hours": 0.0,
        },
        "targets": [],
        "capture_locations": [],
        "recent_captures": [],
        "recent_sessions": [],
    }


def test_dashboard_endpoint_is_typed_get_only_and_closes_database():
    database = FakeDatabase()

    with (
        patch("app.api.dashboard.SessionLocal", return_value=database),
        patch(
            "app.api.dashboard.build_dashboard_response",
            return_value=empty_dashboard_response(),
        ),
    ):
        response = TestClient(app).get("/dashboard")

    assert response.status_code == 200
    assert response.json()["recent_captures"] == []
    assert database.closed

    methods = {
        method
        for route in app.routes
        if getattr(route, "path", None) == "/dashboard"
        for method in getattr(route, "methods", set())
    }
    assert methods == {"GET"}


def test_dashboard_endpoint_passes_history_expansion_request():
    database = FakeDatabase()

    with (
        patch("app.api.dashboard.SessionLocal", return_value=database),
        patch(
            "app.api.dashboard.build_dashboard_response",
            return_value=empty_dashboard_response(),
        ) as build_response,
    ):
        response = TestClient(app).get("/dashboard?include_all_history=true")

    assert response.status_code == 200
    assert build_response.call_args.kwargs["include_all_history"] is True


def test_dashboard_service_builds_consolidated_history():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    database = sessionmaker(bind=engine)()

    session = ObservingSession(
        session_id="SES-TEST-1",
        date="2026-07-16",
        location="Gilbert, AZ 85297",
        observatory="Doug's Observatory",
        bortle_class=7,
    )
    database.add(session)
    database.flush()

    first_capture = Capture(
        polaris_id="POL-TEST-1",
        session_id=session.id,
        object_name="M57",
        filename="m57-first.fits",
        observation_utc="2026-07-16T04:00:00Z",
        total_integration_seconds=1800,
        sub_exposure_seconds=15,
        subframe_count=120,
        gain=100,
        filter_name="Duo-Band",
        status="Analyzed",
    )
    second_capture = Capture(
        polaris_id="POL-TEST-2",
        session_id=session.id,
        object_name="M57",
        filename="m57-second.fits",
        observation_utc="2026-07-16T05:00:00Z",
        exposure_seconds=600,
        status="Raw",
    )
    database.add_all([first_capture, second_capture])
    database.flush()
    database.add(
        CaptureAnalysis(
            capture_id=first_capture.id,
            stars_detected=2500,
            background_level=10000,
            trailing_detected=False,
            quality_score=95,
            recommendation="quality=95/100, stddev=500.00",
        )
    )
    database.commit()

    payload = build_dashboard_response(database)

    assert payload["metrics"] == {
        "captures": 2,
        "targets": 1,
        "sessions": 1,
        "sessions_with_captures": 1,
        "analysis_records": 1,
        "total_integration_seconds": 2400,
        "total_integration_hours": 0.67,
    }
    assert payload["targets"][0]["object"] == "M57"
    assert payload["targets"][0]["common_name"] == "Ring Nebula"
    assert payload["targets"][0]["profile"]["object_type"] == (
        "Planetary nebula"
    )
    assert payload["targets"][0]["profile"]["distance"] == (
        "About 2,000 light-years"
    )
    assert payload["targets"][0]["profile"]["wow_fact"]
    assert payload["targets"][0]["preview_url"] == (
        "/operator-preview/POL-TEST-1"
    )
    assert payload["targets"][0]["preview_image"]["preview_url"] == (
        "/operator-preview/POL-TEST-1"
    )
    assert payload["targets"][0]["preview_image"]["quality_score"] == 95
    assert payload["targets"][0]["preview_image"]["quality_recommendation"] == (
        "Star detection is the largest scoring gap: 2500 stars earned 15 of "
        "20 points. Check focus and sky clarity before collecting more frames."
    )
    assert payload["targets"][0]["best_quality"] == 95
    assert payload["targets"][0]["average_quality"] == 95
    assert payload["targets"][0]["scored_capture_count"] == 1
    assert payload["targets"][0]["integration_goal_note"] == (
        "Detailed starter goal for a planetary nebula. Its compact, bright "
        "ring reduces the starter goal by 1 hour. This is a planning baseline, "
        "not an image-quality score or guarantee."
    )
    assert payload["targets"][0]["goal_tier"] == "detailed"
    assert [option["hours"] for option in payload["targets"][0]["goal_options"]] == [
        2.0,
        4.0,
        8.0,
    ]
    quality_capture = payload["targets"][0]["quality_captures"][0]
    assert quality_capture["quality_score"] == 95
    assert quality_capture["components"] == {
        "base_points": 50,
        "star_points": 15,
        "background_points": 10,
        "variation_points": 15,
        "trailing_points": 5,
        "stars_detected": 2500,
        "background_level": 10000,
        "background_variation": 500.0,
        "trailing_detected": False,
    }
    assert payload["recent_captures"][0]["polaris_id"] == "POL-TEST-2"
    assert payload["recent_captures"][0]["preview_url"] == (
        "/operator-preview/POL-TEST-2"
    )
    assert payload["recent_captures"][0]["common_name"] == "Ring Nebula"
    assert payload["recent_captures"][0]["location"] == "Gilbert, AZ 85297"
    assert payload["recent_captures"][0]["bortle_class"] == 7
    assert payload["recent_captures"][0]["observatory"] == (
        "Doug's Observatory"
    )
    assert payload["recent_captures"][0]["quality_recommendation"] == (
        "Quality analysis is not available for this capture yet."
    )
    assert payload["recent_captures"][0]["components"] is None
    assert payload["recent_sessions"][0]["targets"] == ["M57"]
    assert payload["recent_sessions"][0]["target_labels"] == [
        "M57 — Ring Nebula"
    ]
    assert payload["recent_sessions"][0]["target_common_names"] == [
        "Ring Nebula"
    ]
    assert payload["recent_sessions"][0]["started_at"] == (
        "2026-07-16T04:00:00+00:00"
    )
    assert payload["recent_sessions"][0]["location"] == "Gilbert, AZ 85297"
    assert payload["recent_sessions"][0]["bortle_class"] == 7
    assert payload["capture_locations"] == [
        {
            "location": "Gilbert, AZ 85297",
            "city_label": "Gilbert, AZ",
            "latitude": 33.3528,
            "longitude": -111.789,
            "capture_count": 2,
            "bortle_class": 7,
        }
    ]
    assert payload["recent_sessions"][0]["total_subframes"] == 120
    assert payload["recent_sessions"][0]["sub_exposure_seconds"] == 15
    assert payload["recent_sessions"][0]["gain"] == 100
    assert payload["recent_sessions"][0]["filter_name"] == "Duo-Band"
    assert payload["recent_sessions"][0]["average_quality"] == 95
    assert len(payload["recent_sessions"][0]["images"]) == 2
    assert {
        image["preview_url"]
        for image in payload["recent_sessions"][0]["images"]
    } == {
        "/operator-preview/POL-TEST-1",
        "/operator-preview/POL-TEST-2",
    }

    database.close()


def test_dashboard_history_does_not_invent_capture_location():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    database = sessionmaker(bind=engine)()

    session = ObservingSession(session_id="SES-UNKNOWN", date="2026-07-16")
    database.add(session)
    database.flush()
    database.add(
        Capture(
            polaris_id="POL-UNKNOWN",
            session_id=session.id,
            object_name="M57",
            filename="m57.fits",
            observation_utc="2026-07-16T04:00:00Z",
            total_integration_seconds=900,
        )
    )
    database.commit()

    payload = build_dashboard_response(database)

    assert payload["recent_captures"][0]["location"] is None
    assert payload["recent_captures"][0]["bortle_class"] is None
    assert payload["recent_sessions"][0]["location"] is None
    assert payload["recent_sessions"][0]["bortle_class"] is None


def test_dashboard_history_is_sorted_by_observation_time_not_database_id():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    database = sessionmaker(bind=engine)()

    newer_session = ObservingSession(
        session_id="SES-NEWER",
        date="2026-07-17",
    )
    older_session = ObservingSession(
        session_id="SES-OLDER",
        date="2026-07-16",
    )
    database.add(newer_session)
    database.flush()
    database.add(older_session)
    database.flush()
    database.add(
        ObservingSession(
            session_id="SES-EMPTY",
            date="2026-07-18",
        )
    )
    database.flush()

    database.add(
        Capture(
            polaris_id="POL-NEWER",
            session_id=newer_session.id,
            object_name="M57",
            observation_utc="2026-07-17T05:00:00Z",
            total_integration_seconds=900,
        )
    )
    database.flush()
    database.add(
        Capture(
            polaris_id="POL-OLDER",
            session_id=older_session.id,
            object_name="M27",
            observation_utc="2026-07-16T05:00:00Z",
            total_integration_seconds=900,
        )
    )
    database.commit()

    payload = build_dashboard_response(database)

    assert [capture["polaris_id"] for capture in payload["recent_captures"]] == [
        "POL-NEWER",
        "POL-OLDER",
    ]
    assert [session["session_id"] for session in payload["recent_sessions"]] == [
        "SES-NEWER",
        "SES-OLDER",
    ]
    assert payload["metrics"]["sessions"] == 3
    assert payload["metrics"]["sessions_with_captures"] == 2

    database.close()
