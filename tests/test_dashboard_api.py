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
            "analysis_records": 0,
            "total_integration_seconds": 0,
            "total_integration_hours": 0.0,
        },
        "targets": [],
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


def test_dashboard_service_builds_consolidated_history():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    database = sessionmaker(bind=engine)()

    session = ObservingSession(
        session_id="SES-TEST-1",
        date="2026-07-16",
        location="Gilbert, AZ",
        observatory="Doug's Observatory",
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
            quality_score=91,
        )
    )
    database.commit()

    payload = build_dashboard_response(database)

    assert payload["metrics"] == {
        "captures": 2,
        "targets": 1,
        "sessions": 1,
        "analysis_records": 1,
        "total_integration_seconds": 2400,
        "total_integration_hours": 0.67,
    }
    assert payload["targets"][0]["object"] == "M57"
    assert payload["targets"][0]["best_quality"] == 91
    assert payload["recent_captures"][0]["polaris_id"] == "POL-TEST-2"
    assert payload["recent_sessions"][0]["targets"] == ["M57"]

    database.close()
