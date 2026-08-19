from fastapi.testclient import TestClient

from app.main import app


def test_rig_profiles_endpoint_returns_catalog_summary():
    response = TestClient(app).get("/rig-profiles")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_profiles"] == 17
    assert payload["manufacturers"] == [
        "Celestron",
        "DWARFLAB",
        "Unistellar",
        "Vaonis",
        "ZWO",
    ]
    assert payload["profiles_with_field_of_view"] == 14
    assert payload["profiles_with_frame_limit"] == 1
    assert len(payload["profiles"]) == 17


def test_rig_profiles_endpoint_exposes_plain_language_profile_summaries():
    response = TestClient(app).get("/rig-profiles")

    payload = response.json()
    dwarf = next(profile for profile in payload["profiles"] if profile["key"] == "dwarf-3")
    seestar = next(
        profile for profile in payload["profiles"] if profile["key"] == "seestar-s50"
    )

    assert dwarf["label"] == "DWARFLAB DWARF 3"
    assert dwarf["has_frame_limit"] is True
    assert seestar["label"] == "ZWO Seestar S50"
    assert seestar["has_frame_limit"] is False


def test_rig_profiles_endpoint_has_no_write_route():
    paths = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    assert ("POST", "/rig-profiles") not in paths
    assert ("PUT", "/rig-profiles") not in paths
    assert ("DELETE", "/rig-profiles") not in paths
