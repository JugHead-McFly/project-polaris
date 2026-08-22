from unittest.mock import MagicMock
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.error import URLError

import pytest

from app.core.planning_context import ObservatoryContext
from app.services.planner_service import _apply_planned_heat_safeguard
from app.services.planner_service import _context_equipment_label
from app.services.weather_service import get_weather_summary
from app.services.weather_service import reset_weather_cache


@pytest.fixture(autouse=True)
def clear_weather_cache():
    reset_weather_cache()
    yield
    reset_weather_cache()


def test_unavailable_weather_fails_closed():
    with patch(
        "app.services.weather_service.urlopen",
        side_effect=URLError("unavailable"),
    ), patch("app.services.weather_service.sleep"):
        weather = get_weather_summary("85297")

    assert weather["observing_rating"] == 0
    assert weather["cloud_cover_percent"] is None
    assert weather["status"].startswith("Weather unavailable:")


def test_weather_request_retries_once_after_transient_failure():
    response, response_data = _weather_response(72)

    with (
        patch(
            "app.services.weather_service.urlopen",
            side_effect=[URLError("temporary DNS failure"), response],
        ) as opened,
        patch("app.services.weather_service.sleep") as delayed,
        patch("app.services.weather_service.json.load", return_value=response_data),
    ):
        weather = get_weather_summary("85297")

    assert opened.call_count == 2
    delayed.assert_called_once()
    assert weather["observing_rating"] == 5
    assert weather["status"] == "Live weather connected."


def test_weather_uses_short_lived_cache_for_repeated_requests():
    response, response_data = _weather_response(72)

    with (
        patch("app.services.weather_service.urlopen", return_value=response) as opened,
        patch("app.services.weather_service.json.load", return_value=response_data),
    ):
        first = get_weather_summary("85297")
        second = get_weather_summary("85297")

    assert opened.call_count == 1
    assert first["status"] == "Live weather connected."
    assert second["status"] == "Live weather connected."
    assert second["cache_status"] == "fresh"


def test_weather_rate_limit_can_use_recent_cached_weather():
    response, response_data = _weather_response(72)
    rate_limit = HTTPError(
        "https://api.open-meteo.com/v1/forecast",
        429,
        "Too Many Requests",
        {},
        None,
    )

    with (
        patch(
            "app.services.weather_service.urlopen",
            side_effect=[response, rate_limit, rate_limit],
        ) as opened,
        patch("app.services.weather_service.json.load", return_value=response_data),
        patch("app.services.weather_service.sleep"),
        patch("app.services.weather_service.WEATHER_CACHE_TTL_SECONDS", -1),
    ):
        first = get_weather_summary("85297")
        reset = get_weather_summary("85297")

    assert opened.call_count == 2
    assert first["status"] == "Live weather connected."
    assert reset["observing_rating"] == 5
    assert reset["cache_status"] == "stale"
    assert reset["status"].startswith(
        "Using recent cached weather because live weather is unavailable:"
    )


def test_weather_rate_limit_is_not_retried_without_cache():
    rate_limit = HTTPError(
        "https://api.open-meteo.com/v1/forecast",
        429,
        "Too Many Requests",
        {},
        None,
    )

    with (
        patch("app.services.weather_service.urlopen", side_effect=rate_limit) as opened,
        patch("app.services.weather_service.sleep") as delayed,
    ):
        weather = get_weather_summary("85297")

    assert opened.call_count == 1
    delayed.assert_not_called()
    assert weather["observing_rating"] == 0
    assert "HTTP Error 429" in weather["status"]


def test_weatherapi_fallback_is_used_when_configured():
    rate_limit = HTTPError(
        "https://api.open-meteo.com/v1/forecast",
        429,
        "Too Many Requests",
        {},
        None,
    )
    fallback_response = MagicMock()
    fallback_response.__enter__.return_value = fallback_response
    fallback_response.__exit__.return_value = None
    fallback_data = {
        "current": {
            "temp_f": 76.2,
            "cloud": 10,
            "humidity": 40,
            "dewpoint_f": 50.1,
            "wind_mph": 3.2,
            "last_updated": "2026-07-24 20:00",
        },
        "forecast": {
            "forecastday": [
                {
                    "hour": [
                        {
                            "time": "2026-07-24 21:00",
                            "temp_f": 72.4,
                            "humidity": 42,
                            "dewpoint_f": 52.0,
                            "cloud": 12,
                            "wind_mph": 4.1,
                        }
                    ]
                }
            ]
        },
    }

    with (
        patch(
            "app.services.weather_service.urlopen",
            side_effect=[rate_limit, fallback_response],
        ) as opened,
        patch("app.services.weather_service.json.load", return_value=fallback_data),
        patch("app.services.weather_service.sleep"),
        patch.dict(
            "app.services.weather_service.os.environ",
            {"POLARIS_WEATHERAPI_KEY": "test-key"},
        ),
    ):
        weather = get_weather_summary("85297")

    assert opened.call_count == 2
    fallback_url = opened.call_args.args[0]
    assert "api.weatherapi.com" in fallback_url
    assert "key=test-key" in fallback_url
    assert weather["provider"] == "weatherapi"
    assert weather["status"] == "Fallback weather connected via WeatherAPI.com."
    assert weather["observing_rating"] == 5
    assert weather["cloud_cover_percent"] == 10
    assert weather["hourly_forecast"]["2026-07-24T21:00"] == {
        "temperature_f": 72.4,
        "humidity_percent": 42,
        "dew_point_f": 52.0,
        "cloud_cover_percent": 12,
        "wind_speed_mph": 4.1,
    }


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


def test_planner_heat_guidance_label_uses_selected_rig_catalog_name():
    observatory = ObservatoryContext(
        name="Home",
        latitude=33.3,
        longitude=-111.8,
        timezone_name="America/Phoenix",
        rig_profile_key="seestar-s50",
    )

    assert _context_equipment_label(observatory) == "ZWO Seestar S50"


def test_planner_heat_guidance_label_falls_back_to_generic_equipment():
    observatory = ObservatoryContext(
        name="Home",
        latitude=33.3,
        longitude=-111.8,
        timezone_name="America/Phoenix",
    )

    assert _context_equipment_label(observatory) == "smart telescope"
