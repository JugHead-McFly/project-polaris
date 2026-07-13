import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from app.core.observatory import LATITUDE
from app.core.observatory import LONGITUDE


def get_weather_summary(postal_code: str):
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "dew_point_2m,"
            "cloud_cover,"
            "wind_speed_10m"
        ),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "auto",
    }

    url = (
        "https://api.open-meteo.com/v1/forecast?"
        + urlencode(params)
    )

    try:
        with urlopen(url, timeout=10) as response:
            data = json.load(response)

        current = data.get("current", {})
        cloud_cover = current.get("cloud_cover")
        humidity = current.get("relative_humidity_2m")
        wind_speed = current.get("wind_speed_10m")

        rating = 5

        if cloud_cover is not None:
            if cloud_cover >= 75:
                rating -= 3
            elif cloud_cover >= 50:
                rating -= 2
            elif cloud_cover >= 25:
                rating -= 1

        if humidity is not None and humidity >= 80:
            rating -= 1

        if wind_speed is not None and wind_speed >= 15:
            rating -= 1

        rating = max(1, rating)

        return {
            "postal_code": postal_code,
            "temperature_f": current.get("temperature_2m"),
            "cloud_cover_percent": current.get("cloud_cover"),
            "humidity_percent": current.get(
                "relative_humidity_2m"
            ),
            "dew_point_f": current.get("dew_point_2m"),
            "wind_speed_mph": current.get("wind_speed_10m"),
            "seeing": None,
            "transparency": None,
            "observing_rating": rating,
            "status": "Live weather connected.",
        }

    except (URLError, TimeoutError, ValueError) as error:
        return {
            "postal_code": postal_code,
            "temperature_f": None,
            "cloud_cover_percent": None,
            "humidity_percent": None,
            "dew_point_f": None,
            "wind_speed_mph": None,
            "seeing": None,
            "transparency": None,
            "observing_rating": rating,
            "status": f"Weather unavailable: {error}",
        }