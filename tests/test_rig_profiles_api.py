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
    assert payload["profiles_with_field_of_view"] == 15
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
    assert dwarf["has_equatorial_tracking"] is True
    assert seestar["label"] == "ZWO Seestar S50"
    assert seestar["has_frame_limit"] is False
    assert seestar["has_equatorial_tracking"] is False


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


def test_rig_profile_detail_exposes_calculated_dwarf_mini_fov():
    response = TestClient(app).get("/rig-profiles/dwarf-mini")

    assert response.status_code == 200
    payload = response.json()
    assert payload["native_fov_degrees"] is None
    assert payload["framing_fov_degrees"] == [2.13, 1.2]
    assert payload["framing_fov_source"] == "calculated_from_official_specs"


def test_rig_profile_detail_endpoint_returns_404_for_unknown_rig():
    response = TestClient(app).get("/rig-profiles/not-a-real-rig")

    assert response.status_code == 404
    assert "not-a-real-rig" in response.json()["detail"]


def test_rig_profile_fit_check_endpoint_returns_comfortable_fit():
    response = TestClient(app).get(
        "/rig-profiles/dwarf-3/fit-check",
        params={"target_width_degrees": 2.0, "target_height_degrees": 1.0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rig_key"] == "dwarf-3"
    assert payload["fits"] is True
    assert payload["label"] == "Comfortable fit"
    assert payload["margin_degrees"] == 0.9


def test_rig_profile_fit_check_endpoint_returns_too_large():
    response = TestClient(app).get(
        "/rig-profiles/Seestar S50/fit-check",
        params={"target_width_degrees": 2.0, "target_height_degrees": 1.0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rig_key"] == "seestar-s50"
    assert payload["fits"] is False
    assert payload["label"] == "Too large"


def test_rig_profile_fit_check_uses_calculated_dwarf_mini_fov():
    response = TestClient(app).get(
        "/rig-profiles/dwarf-mini/fit-check",
        params={"target_width_degrees": 2.0, "target_height_degrees": 1.0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["fits"] is True
    assert payload["label"] == "Tight fit"
    assert payload["data_status"] == "supported"
    assert payload["framing_fov_degrees"] == [2.13, 1.2]


def test_rig_profile_fit_check_keeps_missing_rig_fov_visible():
    response = TestClient(app).get(
        "/rig-profiles/dwarf-2/fit-check",
        params={"target_width_degrees": 2.0, "target_height_degrees": 1.0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["fits"] is None
    assert payload["label"] == "Unknown fit"
    assert payload["data_status"] == "rig_fov_unavailable"
    assert payload["framing_fov_degrees"] is None


def test_rig_profile_fit_check_endpoint_validates_positive_target_size():
    response = TestClient(app).get(
        "/rig-profiles/dwarf-3/fit-check",
        params={"target_width_degrees": 0, "target_height_degrees": 1.0},
    )

    assert response.status_code == 422


def test_rig_profile_fit_check_endpoint_returns_404_for_unknown_rig():
    response = TestClient(app).get(
        "/rig-profiles/not-a-real-rig/fit-check",
        params={"target_width_degrees": 2.0, "target_height_degrees": 1.0},
    )

    assert response.status_code == 404


def test_rig_profile_run_plan_endpoint_returns_single_run():
    response = TestClient(app).get(
        "/rig-profiles/dwarf-3/run-plan",
        params={"imaging_minutes": 240, "sub_exposure_seconds": 30},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rig_key"] == "dwarf-3"
    assert payload["total_frames"] == 480
    assert payload["run_count"] == 1
    assert payload["frames_per_run"] == 480
    assert payload["label"] == "Single run"


def test_rig_profile_run_plan_endpoint_returns_split_run():
    response = TestClient(app).get(
        "/rig-profiles/dwarf-3/run-plan",
        params={"imaging_minutes": 600, "sub_exposure_seconds": 30},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_frames"] == 1200
    assert payload["run_count"] == 2
    assert payload["frames_per_run"] == 999
    assert payload["label"] == "Split run"


def test_rig_profile_run_plan_endpoint_keeps_unknown_frame_limit_visible():
    response = TestClient(app).get(
        "/rig-profiles/Seestar S50/run-plan",
        params={"imaging_minutes": 240, "sub_exposure_seconds": 10},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rig_key"] == "seestar-s50"
    assert payload["total_frames"] == 1440
    assert payload["run_count"] is None
    assert payload["frames_per_run"] is None
    assert payload["label"] == "Frame limit unknown"


def test_rig_profile_run_plan_endpoint_validates_positive_inputs():
    response = TestClient(app).get(
        "/rig-profiles/dwarf-3/run-plan",
        params={"imaging_minutes": 0, "sub_exposure_seconds": 30},
    )

    assert response.status_code == 422


def test_rig_profile_run_plan_endpoint_returns_404_for_unknown_rig():
    response = TestClient(app).get(
        "/rig-profiles/not-a-real-rig/run-plan",
        params={"imaging_minutes": 240, "sub_exposure_seconds": 30},
    )

    assert response.status_code == 404


def test_rig_profile_target_score_endpoint_returns_explainable_score():
    response = TestClient(app).get(
        "/rig-profiles/dwarf-3/target-score",
        params={
            "target_width_degrees": 2.0,
            "target_height_degrees": 1.0,
            "maximum_altitude_degrees": 58,
            "usable_dark_minutes": 210,
            "moon_illumination_percent": 22,
            "moon_separation_degrees": 95,
            "bortle_class": 4,
            "exposure_confidence": 0.75,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rig_key"] == "dwarf-3"
    assert payload["score"] == 100
    assert payload["quality"] == "Excellent opportunity"
    assert payload["field_of_view_label"] == "Comfortable fit"
    assert [component["label"] for component in payload["components"]] == [
        "Altitude",
        "Usable window",
        "Moon",
        "Sky brightness",
        "Field of view",
        "Exposure confidence",
    ]


def test_rig_profile_target_score_endpoint_penalizes_oversized_target():
    response = TestClient(app).get(
        "/rig-profiles/Seestar S50/target-score",
        params={
            "target_width_degrees": 2.0,
            "target_height_degrees": 1.0,
            "maximum_altitude_degrees": 58,
            "usable_dark_minutes": 210,
            "moon_illumination_percent": 22,
            "moon_separation_degrees": 95,
            "bortle_class": 4,
            "exposure_confidence": 0.75,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["field_of_view_label"] == "Too large"
    assert any(
        component["label"] == "Field of view" and component["points"] == -30
        for component in payload["components"]
    )


def test_rig_profile_target_score_endpoint_validates_ranges():
    response = TestClient(app).get(
        "/rig-profiles/dwarf-3/target-score",
        params={
            "target_width_degrees": 2.0,
            "target_height_degrees": 1.0,
            "usable_dark_minutes": 210,
            "bortle_class": 10,
        },
    )

    assert response.status_code == 422


def test_rig_profile_target_score_endpoint_returns_404_for_unknown_rig():
    response = TestClient(app).get(
        "/rig-profiles/not-a-real-rig/target-score",
        params={
            "target_width_degrees": 2.0,
            "target_height_degrees": 1.0,
            "usable_dark_minutes": 210,
        },
    )

    assert response.status_code == 404


def test_rig_profiles_endpoint_has_no_write_route():
    paths = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    assert ("POST", "/rig-profiles") not in paths
    assert ("PUT", "/rig-profiles") not in paths
    assert ("DELETE", "/rig-profiles") not in paths
