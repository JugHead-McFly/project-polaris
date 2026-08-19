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


def test_rig_profile_detail_endpoint_returns_source_backed_fields():
    response = TestClient(app).get("/rig-profiles/dwarf-3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["key"] == "dwarf-3"
    assert payload["manufacturer"] == "DWARFLAB"
    assert payload["model"] == "DWARF 3"
    assert payload["frame_limit"] == 999
    assert payload["storage_gb"] == 128
    assert payload["battery_life_hours"] == 5.5
    assert payload["operating_temperature_c"] == [-20.0, 45.0]
    assert payload["source_urls"]


def test_rig_profile_detail_endpoint_accepts_model_names():
    response = TestClient(app).get("/rig-profiles/Seestar S50")

    assert response.status_code == 200
    payload = response.json()
    assert payload["key"] == "seestar-s50"
    assert payload["native_fov_degrees"] == [1.29, 0.73]
    assert payload["frame_limit"] is None


def test_rig_profile_detail_endpoint_returns_404_for_unknown_rig():
    response = TestClient(app).get("/rig-profiles/not-a-real-rig")

    assert response.status_code == 404
    assert "not-a-real-rig" in response.json()["detail"]


def test_rig_profiles_endpoint_has_no_write_route():
    paths = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    assert ("POST", "/rig-profiles") not in paths
    assert ("PUT", "/rig-profiles") not in paths
    assert ("DELETE", "/rig-profiles") not in paths
