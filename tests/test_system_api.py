from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


class FakeDatabase:
    closed = False

    def close(self):
        self.closed = True


def system_response():
    return {
        "project": "Project Polaris",
        "version": settings.VERSION,
        "database_version": 1,
        "captures": 19,
        "targets": 18,
        "sessions": 19,
        "analysis_records": 19,
        "capture_library": {
            "available": True,
            "clean": True,
            "library_root": "/Users/doug/ProjectPolaris",
            "database_capture_count": 19,
            "library_fits_count": 19,
            "matched_count": 19,
            "orphan_count": 0,
            "missing_asset_count": 0,
            "conflict_count": 0,
            "status": "Healthy",
            "message": None,
        },
        "diagnostics": {
            "checked_at": "2026-07-17T12:00:00+00:00",
            "uptime_seconds": 120,
            "database_status": "Healthy",
            "data_freshness": {
                "status": "Recent",
                "latest_capture_observation_utc": (
                    "2026-07-09T00:56:11.704000+00:00"
                ),
                "capture_age_hours": 203.1,
                "latest_database_update_utc": (
                    "2026-07-15T01:34:25.895623+00:00"
                ),
                "latest_session_update_utc": (
                    "2026-07-14T17:17:22.360807+00:00"
                ),
                "latest_analysis_utc": (
                    "2026-07-15T00:46:13.554113+00:00"
                ),
            },
            "services": [
                {
                    "service": "Open-Meteo weather",
                    "status": "Healthy",
                    "checked_at": "2026-07-17T11:59:00+00:00",
                    "last_success_at": "2026-07-17T11:59:00+00:00",
                    "message": "Live weather data received successfully.",
                },
                {
                    "service": "NASA JPL Horizons",
                    "status": "Not Checked",
                    "checked_at": None,
                    "last_success_at": None,
                    "message": "No request has been made during this process.",
                },
            ],
        },
        "status": "Healthy",
    }


def test_system_endpoint_includes_read_only_library_health():
    database = FakeDatabase()

    with (
        patch(
            "app.api.system.SessionLocal",
            return_value=database,
        ),
        patch(
            "app.api.system.build_system_status",
            return_value=system_response(),
        ),
    ):
        response = TestClient(app).get("/system")

    assert response.status_code == 200
    payload = response.json()
    assert payload["capture_library"]["clean"]
    assert payload["capture_library"]["matched_count"] == 19
    assert payload["version"] == settings.VERSION
    assert payload["diagnostics"]["data_freshness"]["status"] == "Recent"
    assert database.closed


def test_system_endpoint_has_no_sync_write_route():
    paths = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    assert ("POST", "/system/sync") not in paths
    assert ("PUT", "/system/sync") not in paths
