from unittest.mock import MagicMock
from unittest.mock import patch
from urllib.error import URLError

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
        }
    }
    return response, response_data


def test_hot_weather_requires_caution_even_when_sky_conditions_are_good():
    response, response_data = _weather_response(102.9)
    with (
        patch("app.services.weather_service.urlopen", return_value=response),
        patch("app.services.weather_service.json.load", return_value=response_data),
    ):
        weather = get_weather_summary("85297")

    assert weather["observing_rating"] == 3


def test_extreme_heat_prevents_a_proceed_decision():
    response, response_data = _weather_response(105)
    with (
        patch("app.services.weather_service.urlopen", return_value=response),
        patch("app.services.weather_service.json.load", return_value=response_data),
    ):
        weather = get_weather_summary("85297")

    assert weather["observing_rating"] == 2
