from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.api.tonight import _build_operator_message
from app.core.planning_context import ObservatoryContext
from app.services.night_rating_service import calculate_night_rating


class FakeDatabase:
    closed = False

    def close(self):
        self.closed = True


def planner_target(name, score):
    return {
        "advisor": {"object": name},
        "planner_score": score,
        "observable": True,
        "current_altitude": 55.0,
        "altitude_at_dark_midpoint": 64.2,
        "maximum_dark_altitude": 81.9,
        "average_dark_altitude": 58.4,
        "target_geometry": {
            "samples": [
                {
                    "at": "2026-07-17T21:14:00-07:00",
                    "altitude_degrees": 42.0,
                    "label": "9:14 PM",
                },
                {
                    "at": "2026-07-17T23:29:00-07:00",
                    "altitude_degrees": 81.9,
                    "label": "11:29 PM",
                },
            ],
            "peak_altitude_degrees": 81.9,
            "peak_at": "2026-07-17T23:29:00-07:00",
            "peak_label": "11:29 PM",
        },
        "usable_dark_minutes": 444,
        "usable_dark_hours": 7.4,
        "transit_time": "2026-07-17 11:30 PM",
        "recommended_start": "2026-07-17 09:14 PM",
        "recommended_end": "2026-07-18 01:00 AM",
        "moon_separation_degrees": 80.0,
        "moon_warning": "None",
        "selection_reason": f"{name} is the best available target.",
    }


def planner_response():
    recommended = planner_target("M57", 149.6)
    return {
        "recommended_target": recommended,
        "best_theoretical_target": recommended,
        "alternatives": [planner_target("M27", 140.0)],
        "weather": {
            "postal_code": "85297",
            "cloud_cover_percent": 10,
            "humidity_percent": 25,
            "wind_speed_mph": 4.0,
            "planned_temperature_f": 66,
            "planned_dew_point_f": 58,
            "planned_temperature_at": "2026-07-17 09:00 PM",
            "planned_seeing_index": 4,
            "planned_seeing_forecast_at": "2026-07-17 09:00 PM",
            "planned_transparency_index": 3,
            "planned_transparency_forecast_at": "2026-07-17 09:00 PM",
            "astro_forecast_provider": "7timer-astro",
            "astro_forecast_status": "Astronomy forecast connected.",
            "astro_forecast_fetched_at": "2026-07-17T20:02:00-07:00",
            "observing_rating": 5,
            "status": "Live weather connected.",
        },
        "moon": {
            "illumination_percent": 15.0,
            "altitude_degrees": 9.5,
            "above_horizon": True,
            "next_moonrise": "2026-07-18 10:16 AM",
            "next_moonset": "2026-07-17 09:57 PM",
        },
        "darkness": {
            "sunset": "2026-07-17 07:31 PM",
            "astronomical_darkness_start": "2026-07-17 09:14 PM",
            "astronomical_darkness_end": "2026-07-18 03:51 AM",
        },
        "decision": "Proceed",
        "notes": [],
    }


def schedule_response(planner):
    return {
        "date": "2026-07-17",
        "decision": "Proceed",
        "advisory_only": True,
        "blocks": [
            {
                "object": "M57",
                "start": "2026-07-17 09:14 PM",
                "end": "2026-07-17 11:24 PM",
                "duration_minutes": 130,
                "setup_minutes": 5,
                "imaging_minutes": 125,
                "planner_score": 149.6,
                "reason": "Highest-ranked observable target.",
                "recommended_sub_exposure_seconds": 15,
                "recommended_gain": 100.0,
                "recommended_filter": "Duo-Band",
                "recommendation_source": "best_capture",
                "planned_subframes": 497,
                "setup_changes": ["Slew to and center M57"],
            }
        ],
        "allocated_minutes": 130,
        "unscheduled_dark_minutes": 267,
        "weather": planner["weather"],
        "moon": planner["moon"],
        "darkness": planner["darkness"],
        "notes": [],
        "fallback_target": "M57",
    }


def target_response(name):
    return {
        "object": name,
        "capture_count": 1,
        "session_count": 1,
        "total_integration_seconds": 3600,
        "total_integration_hours": 1.0,
        "best_quality": 90,
        "average_quality": 90.0,
        "latest_capture": "2026-07-01T04:00:00Z",
        "recommended_settings": {
            "source": "best_capture",
            "polaris_id": f"POLARIS-{name}",
            "exposure_seconds": 15,
            "gain": 100.0,
            "filter_name": "Duo-Band",
        },
        "constellation": "Unknown",
        "target_type": "Unknown",
        "difficulty": "Unknown",
        "recommended_filter": "Unknown",
        "recommended_exposure": {
            "exposure_seconds": 15,
            "gain": 60,
            "goal_subframes": 960,
        },
        "season_score": 5,
        "science_priority": 0,
        "readiness_score": 110,
        "status": "In Progress",
        "best_window": "Unknown",
        "progress_percent": 25.0,
        "portfolio_level": "Bronze",
        "next_action": "Continue imaging",
        "current_hours": 1.0,
        "goal_hours": 4.0,
        "remaining_hours": 3.0,
        "estimated_nights_remaining": 0.8,
        "observable": True,
        "current_altitude": None,
        "transit_time": None,
        "moon_warning": None,
        "recommended_start": None,
        "recommended_end": None,
        "moon_separation_degrees": None,
        "reason": None,
        "captures": [],
    }


def test_tonight_preserves_legacy_fields_and_adds_v3_schedule():
    database = FakeDatabase()
    planner = planner_response()

    with (
        patch("app.database.database.SessionLocal", return_value=database),
        patch("app.api.tonight.get_tonight_plan", return_value=planner),
        patch(
            "app.api.tonight.build_tonight_schedule",
            return_value=schedule_response(planner),
        ),
        patch(
            "app.api.tonight.build_target_response",
            side_effect=lambda db, target_name: target_response(target_name),
        ),
    ):
        response = TestClient(app).get("/tonight")

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_target"]["capture_count"] == 1
    assert payload["recommended_target"]["maximum_dark_altitude"] == 81.9
    assert payload["recommended_target"]["average_dark_altitude"] == 58.4
    assert payload["recommended_target"]["target_geometry"]["peak_altitude_degrees"] == 81.9
    assert payload["recommended_target"]["target_geometry"]["peak_label"] == "11:29 PM"
    assert payload["recommended_target"]["usable_dark_hours"] == 7.4
    assert payload["recommended_target"]["artwork"]["slug"] == "ring-nebula-m57"
    assert payload["recommended_target"]["artwork"]["match_kind"] == "exact"
    assert payload["recommended_target"]["artwork"]["asset_url"].startswith(
        "/operator-assets/target-art/library/assets/ring-nebula-m57.svg?v="
    )
    assert payload["backup_target"]["object"] == "M27"
    assert payload["backup_target"]["artwork"]["slug"] == "dumbbell-nebula-m27"
    assert payload["backup_target"]["maximum_dark_altitude"] == 81.9
    assert payload["night_plan"]["target_sequence"][0]["object"] == "M57"
    assert payload["schedule"]["blocks"][0]["planned_subframes"] == 497
    assert payload["opportunity_score"]["total"] == 85.7
    assert payload["dew_risk"]["level"] == "low"
    assert payload["dew_risk"]["spread_f"] == 8.0
    assert payload["dew_risk"]["action"].startswith("No special dew action")
    assert payload["conditions_trend"]["direction"] == "unavailable"
    assert "check live conditions" in payload["conditions_trend"]["message"]
    assert payload["session_checklist"]["status"] == "ready"
    assert [
        step["time_label"] for step in payload["session_checklist"]["steps"]
    ] == ["9:14 PM", "9:19 PM", "11:24 PM"]
    assert payload["session_checklist"]["actions"] == []
    assert [
        component["key"]
        for component in payload["opportunity_score"]["components"]
    ] == ["cloud", "night", "moon", "visibility", "seeing", "altitude"]
    components = {
        item["key"]: item for item in payload["opportunity_score"]["components"]
    }
    assert components["visibility"]["points"] == 7.1
    assert components["seeing"]["points"] == 2.9
    assert components["visibility"]["description"].startswith("Good · forecast")
    assert components["seeing"]["description"].startswith("Good · forecast")
    assert payload["message"].startswith("Conditions currently support imaging")


def test_tonight_adds_selected_rig_profile_and_target_fit():
    database = FakeDatabase()
    planner = planner_response()
    context = ObservatoryContext(
        name="Doug's Rig Test",
        postal_code="85297",
        timezone_name="America/Phoenix",
        latitude=33.2,
        longitude=-111.7,
        rig_profile_key="seestar-s50",
    )

    with (
        patch("app.database.database.SessionLocal", return_value=database),
        patch("app.api.tonight.get_planning_context", return_value=context),
        patch("app.api.tonight.get_tonight_plan", return_value=planner),
        patch(
            "app.api.tonight.build_tonight_schedule",
            return_value=schedule_response(planner),
        ) as build_schedule,
        patch(
            "app.api.tonight.build_target_response",
            side_effect=lambda db, target_name: target_response(target_name),
        ),
    ):
        response = TestClient(app).get("/tonight")

    assert response.status_code == 200
    payload = response.json()
    assert payload["observatory"]["rig_profile_key"] == "seestar-s50"
    assert payload["observatory"]["rig_profile_label"] == "Seestar S50"
    assert build_schedule.call_args.kwargs["rig_profile_key"] == "seestar-s50"
    assert payload["recommended_target"]["rig_fit"]["rig_key"] == "seestar-s50"
    assert payload["recommended_target"]["rig_fit"]["label"] == "Very small"
    assert payload["recommended_target"]["rig_fit"]["target_width_degrees"] == 0.023
    assert (
        "Polaris selected M57 for Seestar S50"
        in payload["recommended_target"]["rig_fit"]["match_summary"]
    )
    assert "framing check is very small" in payload["recommended_target"]["rig_fit"]["match_summary"]
    assert database.closed


def test_tonight_uses_calculated_dwarf_mini_fov_without_guessing():
    database = FakeDatabase()
    planner = planner_response()
    context = ObservatoryContext(
        name="Doug's Rig Test",
        postal_code="85297",
        timezone_name="America/Phoenix",
        latitude=33.2,
        longitude=-111.7,
        rig_profile_key="dwarf-mini",
    )

    with (
        patch("app.database.database.SessionLocal", return_value=database),
        patch("app.api.tonight.get_planning_context", return_value=context),
        patch("app.api.tonight.get_tonight_plan", return_value=planner),
        patch(
            "app.api.tonight.build_tonight_schedule",
            return_value=schedule_response(planner),
        ),
        patch(
            "app.api.tonight.build_target_response",
            side_effect=lambda db, target_name: target_response(target_name),
        ),
    ):
        response = TestClient(app).get("/tonight")

    assert response.status_code == 200
    payload = response.json()
    fit = payload["recommended_target"]["rig_fit"]
    assert fit["rig_label"] == "DWARFLAB DWARF mini"
    assert fit["label"] == "Very small"
    assert fit["data_status"] == "supported"
    assert fit["framing_fov_degrees"] == [2.13, 1.2]
    assert fit["framing_fov_source"] == "calculated_from_official_specs"
    assert "for Dwarf Mini" in fit["match_summary"]
    assert "DWARFLAB" not in fit["match_summary"]
    assert "framing check is very small" in fit["match_summary"]
    assert database.closed


def test_tonight_explains_when_rig_framing_is_not_supported():
    database = FakeDatabase()
    planner = planner_response()
    context = ObservatoryContext(
        name="Doug's Rig Test",
        postal_code="85297",
        timezone_name="America/Phoenix",
        latitude=33.2,
        longitude=-111.7,
        rig_profile_key="dwarf-2",
    )

    with (
        patch("app.database.database.SessionLocal", return_value=database),
        patch("app.api.tonight.get_planning_context", return_value=context),
        patch("app.api.tonight.get_tonight_plan", return_value=planner),
        patch(
            "app.api.tonight.build_tonight_schedule",
            return_value=schedule_response(planner),
        ),
        patch(
            "app.api.tonight.build_target_response",
            side_effect=lambda db, target_name: target_response(target_name),
        ),
    ):
        response = TestClient(app).get("/tonight")

    assert response.status_code == 200
    fit = response.json()["recommended_target"]["rig_fit"]
    assert fit["label"] == "Unknown fit"
    assert fit["data_status"] == "rig_fov_unavailable"
    assert "Framing is not yet supported" in fit["match_summary"]
    assert database.closed


def test_tonight_passes_explicit_eq_confirmation_to_planner():
    database = FakeDatabase()
    planner = planner_response()

    with (
        patch("app.database.database.SessionLocal", return_value=database),
        patch(
            "app.api.tonight.get_tonight_plan",
            return_value=planner,
        ) as get_plan,
        patch(
            "app.api.tonight.build_tonight_schedule",
            return_value=schedule_response(planner),
        ),
        patch(
            "app.api.tonight.build_target_response",
            side_effect=lambda db, target_name: target_response(target_name),
        ),
    ):
        response = TestClient(app).get(
            "/tonight?equatorial_mode_enabled=true"
        )

    assert response.status_code == 200
    assert get_plan.call_args.kwargs["equatorial_mode_enabled"] is True


def test_do_not_image_message_names_the_weather_reasons():
    message = _build_operator_message(
        {
            "decision": "Do Not Image",
            "weather": {
                "observing_rating": 1,
                "cloud_cover_percent": 82,
                "humidity_percent": 84,
                "wind_speed_mph": 17,
            },
        }
    )

    assert message == (
        "Do not image: cloud cover is 82%, humidity is 84%, "
        "wind is 17 mph."
    )


def test_do_not_image_message_uses_planned_start_weather():
    message = _build_operator_message(
        {
            "decision": "Do Not Image",
            "weather": {
                "observing_rating": 2,
                "cloud_cover_percent": 0,
                "humidity_percent": 30,
                "wind_speed_mph": 3,
                "planned_cloud_cover_percent": 98,
                "planned_humidity_percent": 30,
                "planned_wind_speed_mph": 6,
            },
        }
    )

    assert message == (
        "Do not image: forecast near the imaging-window opening indicates "
        "cloud cover is 98%."
    )


def test_do_not_image_message_labels_planned_wind_as_forecast():
    message = _build_operator_message(
        {
            "decision": "Do Not Image",
            "weather": {
                "observing_rating": 1,
                "cloud_cover_percent": 25,
                "wind_speed_mph": 6,
                "planned_cloud_cover_percent": 100,
                "planned_wind_speed_mph": 33.6,
            },
        }
    )

    assert message == (
        "Do not image: forecast near the imaging-window opening indicates "
        "cloud cover is 100%, wind is 33.6 mph."
    )


def test_do_not_image_message_names_excessive_heat():
    message = _build_operator_message(
        {
            "decision": "Do Not Image",
            "weather": {
                "observing_rating": 2,
                "cloud_cover_percent": 0,
                "humidity_percent": 25,
                "wind_speed_mph": 2,
                "planned_temperature_f": 105,
            },
        }
    )

    assert message == (
        "Do not image: forecast temperature near the planned start is 105°F, above Polaris's "
        "conservative heat limit."
    )


def test_do_not_image_message_fails_closed_when_weather_is_unavailable():
    message = _build_operator_message(
        {
            "decision": "Do Not Image",
            "weather": {
                "observing_rating": 0,
                "cloud_cover_percent": None,
                "humidity_percent": None,
                "wind_speed_mph": None,
            },
        }
    )

    assert message == "Do not image: live weather data is unavailable."


def test_night_rating_allows_no_recommended_target():
    rating = calculate_night_rating(
        weather={
            "cloud_cover_percent": 100,
            "humidity_percent": 90,
            "wind_speed_mph": 20,
        },
        moon={"illumination_percent": 100},
        target=None,
    )

    assert rating == {
        "score": 15,
        "quality": "Very Poor",
        "deductions": [
            {"label": "Cloud cover", "points": 50.0},
            {"label": "High humidity", "points": 10},
            {"label": "Strong wind", "points": 10},
            {"label": "Moon illumination", "points": 15.0},
        ],
    }


def test_night_rating_allows_missing_weather_and_moon_measurements():
    rating = calculate_night_rating(
        weather={
            "cloud_cover_percent": None,
            "humidity_percent": None,
            "wind_speed_mph": None,
        },
        moon={"illumination_percent": None},
        target={"moon_separation_degrees": None},
    )

    assert rating == {"score": 0, "quality": "Unavailable", "deductions": []}


def test_night_rating_explains_bright_moon_deduction():
    rating = calculate_night_rating(
        weather={
            "cloud_cover_percent": 0,
            "humidity_percent": 44,
            "wind_speed_mph": 5.6,
        },
        moon={"illumination_percent": 94.3},
        target={"moon_separation_degrees": 55.7},
    )

    assert rating == {
        "score": 86,
        "quality": "Good",
        "deductions": [{"label": "Moon illumination", "points": 14.1}],
    }


def test_night_rating_moon_deduction_is_proportional():
    weather = {
        "cloud_cover_percent": 0,
        "humidity_percent": 44,
        "wind_speed_mph": 5.6,
    }
    target = {"moon_separation_degrees": 55.7}

    expected = {
        0: None,
        50: {"label": "Moon illumination", "points": 7.5},
        75: {"label": "Moon illumination", "points": 11.2},
        100: {"label": "Moon illumination", "points": 15.0},
    }
    for illumination, deduction in expected.items():
        rating = calculate_night_rating(
            weather=weather,
            moon={"illumination_percent": illumination},
            target=target,
        )
        assert rating["deductions"] == ([] if deduction is None else [deduction])


def test_night_rating_uses_planned_start_weather_when_available():
    rating = calculate_night_rating(
        weather={
            "cloud_cover_percent": 0,
            "humidity_percent": 44,
            "wind_speed_mph": 5.6,
            "planned_cloud_cover_percent": 98,
            "planned_humidity_percent": 44,
            "planned_wind_speed_mph": 6,
        },
        moon={"illumination_percent": 82.7},
        target={"moon_separation_degrees": 55.7},
    )

    assert rating == {
        "score": 39,
        "quality": "Very Poor",
        "deductions": [
            {"label": "Cloud cover", "points": 49.0},
            {"label": "Moon illumination", "points": 12.4},
        ],
    }
