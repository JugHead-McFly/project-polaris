from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class FakeDatabase:
    closed = False

    def close(self):
        self.closed = True


def system_response():
    return {
        "project": "Project Polaris",
        "version": "1.1.0",
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
    assert database.closed


def test_system_endpoint_has_no_sync_write_route():
    paths = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    assert ("POST", "/system/sync") not in paths
    assert ("PUT", "/system/sync") not in paths
