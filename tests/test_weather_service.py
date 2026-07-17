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
