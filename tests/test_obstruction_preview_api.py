from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.main import app
from app.api.obstructions import MAX_PREVIEW_BYTES


@pytest.fixture
def payload():
    return {"profile": {"complete_coverage": True, "clearance_degrees": 1,
        "horizon": [{"azimuth_degrees": 0, "altitude_degrees": 10},
                    {"azimuth_degrees": 180, "altitude_degrees": 10}],
        "sectors": [{"start_azimuth_degrees": 350, "end_azimuth_degrees": 20,
                     "minimum_altitude_degrees": 60, "maximum_altitude_degrees": 90}]},
        "probe": {"azimuth_degrees": 0, "altitude_degrees": 45}}


def test_preview_uses_real_geometry_wrap_and_does_not_query_data(payload):
    with patch("sqlalchemy.orm.Session.execute", side_effect=AssertionError("No DB reads")), patch(
        "app.services.astronomy_service.get_horizontal_positions_at", side_effect=AssertionError("No astronomy fetch")
    ):
        result = TestClient(app).post("/obstructions/preview", json=payload)
    assert result.status_code == 200
    data = result.json()
    assert data["probe"]["clear"] is True
    assert data["applied_to_tonight"] is False
    assert data["horizon"][0] == {"azimuth_degrees": 0, "altitude_degrees": 10}
    assert data["horizon"][-1] == {"azimuth_degrees": 360, "altitude_degrees": 10}
    assert data["sectors"] == [{"start": 350, "end": 360, "low": 59, "high": 90},
                               {"start": 0, "end": 20, "low": 59, "high": 90}]
    assert result.headers["cache-control"] == "no-store"
    payload["probe"]["altitude_degrees"] = 59
    assert TestClient(app).post("/obstructions/preview", json=payload).json()["probe"]["reason"].startswith("Overhead")
    payload["probe"]["altitude_degrees"] = 19.99
    assert "minimum imaging altitude" in TestClient(app).post("/obstructions/preview", json=payload).json()["probe"]["reason"]


def test_preview_respects_authentication(payload):
    def reject():
        raise HTTPException(401, "Sign in")
    app.dependency_overrides[get_current_user] = reject
    try:
        assert TestClient(app).post("/obstructions/preview", json=payload).status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user)


@pytest.mark.parametrize("change", [
    lambda p: p["profile"].update(complete_coverage=False),
    lambda p: p["profile"].update(complete_coverage="true"),
    lambda p: p["profile"].update(clearance_degrees=True),
    lambda p: p["probe"].update(azimuth_degrees=360),
    lambda p: p["probe"].update(altitude_degrees="45"),
    lambda p: p.update(account_id="private-value-that-must-not-be-echoed"),
    lambda p: p["profile"]["horizon"].reverse(),
    lambda p: p["profile"].update(horizon=[]),
    lambda p: p["profile"]["sectors"][0].update(minimum_altitude_degrees=90),
])
def test_invalid_preview_has_safe_errors(payload, change):
    change(payload)
    result = TestClient(app).post("/obstructions/preview", json=payload)
    assert result.status_code == 422
    assert "private-value-that-must-not-be-echoed" not in result.text
    assert result.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("body", ['{"profile":{},"profile":{}}', '{"probe":NaN}', '{"probe":Infinity}', 'null', '{', '[' * 2000])
def test_malformed_duplicate_nonfinite_or_deep_json_is_rejected(body):
    result = TestClient(app).post("/obstructions/preview", content=body, headers={"Content-Type": "application/json"})
    assert result.status_code == 422


def test_request_size_and_content_type_limits(payload):
    client = TestClient(app)
    assert client.post("/obstructions/preview", content="{}", headers={"Content-Type": "text/plain"}).status_code == 415
    result = client.post("/obstructions/preview", content=b" " * (MAX_PREVIEW_BYTES + 1), headers={"Content-Type": "application/json"})
    assert result.status_code == 413


def test_preview_does_not_retain_another_requests_profile(payload):
    client = TestClient(app)
    first = client.post("/obstructions/preview", json=payload).json()
    other = deepcopy(payload)
    other["profile"]["horizon"][0]["altitude_degrees"] = 90
    assert client.post("/obstructions/preview", json=other).json()["probe"]["clear"] is False
    assert client.post("/obstructions/preview", json=payload).json() == first


def test_editor_is_available_in_home_and_locations_and_assets_versioned():
    response = TestClient(app).get("/operator")
    assert response.text.count("data-obstruction-editor") == 2
    assert response.text.index("obstruction-editor.js?v=") < response.text.index("operator.js?v=")
    assert "obstruction-editor.css?v=" in response.text
    for asset in ["obstruction-editor.js", "obstruction-editor.css"]:
        assert TestClient(app).get("/operator-assets/" + asset).status_code == 200


def test_ui_synthetic_fixture_matches_current_backend_geometry():
    import json
    from pathlib import Path
    fixture = json.loads((Path(__file__).parent / "fixtures" / "obstruction_preview.json").read_text())
    probe = {key: fixture["probe"][key] for key in ("azimuth_degrees", "altitude_degrees")}
    result = TestClient(app).post("/obstructions/preview", json={"profile": fixture["profile"], "probe": probe})
    assert result.status_code == 200
    assert result.json() == fixture
