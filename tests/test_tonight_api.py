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
    assert payload["recommended_target"]["usable_dark_hours"] == 7.4
    assert payload["backup_target"]["object"] == "M27"
    assert payload["backup_target"]["maximum_dark_altitude"] == 81.9
    assert payload["night_plan"]["target_sequence"][0]["object"] == "M57"
    assert payload["schedule"]["blocks"][0]["planned_subframes"] == 497
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
    assert payload["observatory"]["rig_profile_label"] == "ZWO Seestar S50"
    assert build_schedule.call_args.kwargs["rig_profile_key"] == "seestar-s50"
    assert payload["recommended_target"]["rig_fit"]["rig_key"] == "seestar-s50"
    assert payload["recommended_target"]["rig_fit"]["label"] == "Very small"
    assert payload["recommended_target"]["rig_fit"]["target_width_degrees"] == 0.023
    assert (
        "Polaris selected M57 for ZWO Seestar S50"
        in payload["recommended_target"]["rig_fit"]["match_summary"]
    )
    assert "framing check is very small" in payload["recommended_target"]["rig_fit"]["match_summary"]
    assert database.closed


def test_tonight_explains_unknown_official_rig_fov_without_guessing():
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
    assert fit["label"] == "Unknown fit"
    assert "official rig field-of-view data is incomplete" in fit["match_summary"]
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

    assert message == "Do not image: cloud cover is 98%."


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
        "score": 10,
        "quality": "Very Poor",
        "deductions": [
            {"label": "Cloud cover", "points": 50.0},
            {"label": "High humidity", "points": 10},
            {"label": "Strong wind", "points": 10},
            {"label": "Bright Moon", "points": 20},
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
        "score": 80,
        "quality": "Good",
        "deductions": [{"label": "Bright Moon", "points": 20}],
    }


def test_night_rating_moon_threshold_matches_displayed_whole_percent():
    weather = {
        "cloud_cover_percent": 0,
        "humidity_percent": 44,
        "wind_speed_mph": 5.6,
    }
    target = {"moon_separation_degrees": 55.7}

    for illumination in (74.9, 75.0, 75.1):
        rating = calculate_night_rating(
            weather=weather,
            moon={"illumination_percent": illumination},
            target=target,
        )
        assert rating["score"] == 100
        assert rating["deductions"] == []

    rating = calculate_night_rating(
        weather=weather,
        moon={"illumination_percent": 75.6},
        target=target,
    )
    assert rating["score"] == 80
    assert rating["deductions"] == [{"label": "Bright Moon", "points": 20}]


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
        "score": 31,
        "quality": "Very Poor",
        "deductions": [
            {"label": "Cloud cover", "points": 49.0},
            {"label": "Bright Moon", "points": 20},
        ],
    }
