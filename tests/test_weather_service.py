from unittest.mock import MagicMock
from unittest.mock import patch
from urllib.error import URLError

from app.core.planning_context import ObservatoryContext
from app.services.planner_service import _apply_planned_heat_safeguard
from app.services.weather_service import get_weather_summary


def test_unavailable_weather_fails_closed():
    with patch(
        "app.services.weather_service.urlopen",
        side_effect=URLError("unavailable"),
    ):
        weather = get_weather_summary("85297")

    assert weather["observing_rating"] == 0
    assert weather["cloud_cover_percent"] is None
    assert weather["status"].startswith("Weather unavailable:")


def _weather_response(temperature_f):
    response = MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = None
    response.read.return_value = b""
    response.__iter__.return_value = iter(())
    response.getcode.return_value = 200
    response.headers = {}
    response_data = {
        "current": {
            "temperature_2m": temperature_f,
            "cloud_cover": 0,
            "relative_humidity_2m": 30,
            "dew_point_2m": 50,
            "wind_speed_10m": 2,
            "time": "2026-07-24T22:00",
        },
        "hourly": {
            "time": ["2026-07-24T22:00"],
            "temperature_2m": [temperature_f],
            "relative_humidity_2m": [42],
            "dew_point_2m": [55],
            "cloud_cover": [12],
            "wind_speed_10m": [4],
        },
    }
    return response, response_data


def test_live_heat_does_not_change_the_imaging_decision_rating():
    response, response_data = _weather_response(102.9)
    with (
        patch("app.services.weather_service.urlopen", return_value=response),
        patch("app.services.weather_service.json.load", return_value=response_data),
    ):
        weather = get_weather_summary("85297")

    assert weather["observing_rating"] == 5
    assert weather["hourly_temperature_f"] == {"2026-07-24T22:00": 102.9}


def test_hourly_forecast_is_available_for_the_planner():
    response, response_data = _weather_response(105)
    with (
        patch("app.services.weather_service.urlopen", return_value=response),
        patch("app.services.weather_service.json.load", return_value=response_data),
    ):
        weather = get_weather_summary("85297")

    assert weather["observing_rating"] == 5
    assert weather["hourly_temperature_f"] == {"2026-07-24T22:00": 105}
    assert weather["hourly_forecast"]["2026-07-24T22:00"] == {
        "temperature_f": 105,
        "humidity_percent": 42,
        "dew_point_f": 55,
        "cloud_cover_percent": 12,
        "wind_speed_mph": 4,
    }


def test_heat_safeguard_uses_forecast_at_the_planned_start_not_live_heat():
    weather = {
        "temperature_f": 102.9,
        "observing_rating": 5,
        "hourly_temperature_f": {
            "2026-07-24T21:00": 90,
            "2026-07-24T22:00": 88,
        },
    }

    _apply_planned_heat_safeguard(weather, "2026-07-24 09:13 PM")

    assert weather["observing_rating"] == 5
    assert weather["planned_temperature_f"] == 90
    assert weather["planned_temperature_at"] == "2026-07-24 09:00 PM"


def test_forecast_heat_prevents_a_proceed_decision_at_the_planned_start():
    weather = {
        "temperature_f": 85,
        "observing_rating": 5,
        "hourly_temperature_f": {"2026-07-24T21:00": 105},
    }

    _apply_planned_heat_safeguard(weather, "2026-07-24 09:13 PM")

    assert weather["observing_rating"] == 2
    assert weather["planned_temperature_f"] == 105


def test_planner_uses_cloud_wind_and_humidity_at_the_planned_start():
    weather = {
        "temperature_f": 75,
        "cloud_cover_percent": 0,
        "humidity_percent": 20,
        "wind_speed_mph": 2,
        "observing_rating": 5,
        "hourly_forecast": {
            "2026-07-24T21:00": {
                "temperature_f": 80,
                "cloud_cover_percent": 55,
                "humidity_percent": 85,
                "dew_point_f": 76,
                "wind_speed_mph": 16,
            },
        },
    }

    _apply_planned_heat_safeguard(weather, "2026-07-24 09:13 PM")

    assert weather["planned_cloud_cover_percent"] == 55
    assert weather["planned_humidity_percent"] == 85
    assert weather["planned_wind_speed_mph"] == 16
    assert weather["observing_rating"] == 1


def test_weather_request_uses_the_planning_observatory_coordinates():
    response, response_data = _weather_response(70)
    observatory = ObservatoryContext(
        name="Sydney",
        latitude=-33.8688,
        longitude=151.2093,
        timezone_name="Australia/Sydney",
    )

    with (
        patch("app.services.weather_service.urlopen", return_value=response) as opened,
        patch("app.services.weather_service.json.load", return_value=response_data),
    ):
        get_weather_summary("", observatory=observatory)

    requested_url = opened.call_args.args[0]
    assert "latitude=-33.8688" in requested_url
    assert "longitude=151.2093" in requested_url
