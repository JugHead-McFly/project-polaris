from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.api.tonight import _build_operator_message
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
        patch("app.api.tonight.SessionLocal", return_value=database),
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
    assert payload["backup_target"]["object"] == "M27"
    assert payload["night_plan"]["target_sequence"][0]["object"] == "M57"
    assert payload["schedule"]["blocks"][0]["planned_subframes"] == 497
    assert payload["message"].startswith("Conditions currently support imaging")
    assert database.closed


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

    assert rating == {"score": 10, "quality": "Very Poor"}


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

    assert rating == {"score": 0, "quality": "Unavailable"}
