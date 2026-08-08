import json
from time import sleep
from datetime import datetime, timezone
from typing import Optional
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from app.core.diagnostics import record_service_failure
from app.core.diagnostics import record_service_success
from app.core.planning_context import ObservatoryContext
from app.core.planning_context import use_observatory_context


# DWARFLAB documents a 45°C / 113°F high-temperature charging cutoff for
# DWARF mini.  Polaris intentionally applies a lower ambient-air limit: the
# telescope generates its own heat, and the forecast temperature is not an
# internal sensor reading.
HEAT_CAUTION_F = 95
HEAT_STOP_F = 105
WEATHER_REQUEST_TIMEOUT_SECONDS = 10
WEATHER_REQUEST_ATTEMPTS = 2
WEATHER_RETRY_DELAY_SECONDS = 0.5


def calculate_observing_rating(
    cloud_cover: Optional[float],
    humidity: Optional[float],
    wind_speed: Optional[float],
) -> int:
    """Score weather using the same thresholds for live and forecast data."""
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

    return max(1, rating)


def get_weather_summary(
    postal_code: str,
    observatory: Optional[ObservatoryContext] = None,
):
    context = use_observatory_context(observatory)
    checked_at = datetime.now(timezone.utc)
    params = {
        "latitude": context.latitude,
        "longitude": context.longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "dew_point_2m,"
            "cloud_cover,"
            "wind_speed_10m"
        ),
        "hourly": (
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
        data = _fetch_weather_data(url)

        current = data.get("current", {})
        cloud_cover = current.get("cloud_cover")
        humidity = current.get("relative_humidity_2m")
        wind_speed = current.get("wind_speed_10m")

        rating = calculate_observing_rating(
            cloud_cover,
            humidity,
            wind_speed,
        )

        temperature_f = current.get("temperature_2m")

        hourly = data.get("hourly", {})
        hourly_times = hourly.get("time") or []
        hourly_temperatures = hourly.get("temperature_2m") or []
        hourly_humidity = hourly.get("relative_humidity_2m") or []
        hourly_dew_points = hourly.get("dew_point_2m") or []
        hourly_cloud_cover = hourly.get("cloud_cover") or []
        hourly_wind_speed = hourly.get("wind_speed_10m") or []
        hourly_temperature_f = {
            time: temperature
            for time, temperature in zip(hourly_times, hourly_temperatures)
            if temperature is not None
        }
        hourly_forecast = {}
        for index, time in enumerate(hourly_times):
            hourly_forecast[time] = {
                "temperature_f": (
                    hourly_temperatures[index]
                    if index < len(hourly_temperatures)
                    else None
                ),
                "humidity_percent": (
                    hourly_humidity[index]
                    if index < len(hourly_humidity)
                    else None
                ),
                "dew_point_f": (
                    hourly_dew_points[index]
                    if index < len(hourly_dew_points)
                    else None
                ),
                "cloud_cover_percent": (
                    hourly_cloud_cover[index]
                    if index < len(hourly_cloud_cover)
                    else None
                ),
                "wind_speed_mph": (
                    hourly_wind_speed[index]
                    if index < len(hourly_wind_speed)
                    else None
                ),
            }

        record_service_success(
            "weather",
            "Live weather data received successfully.",
            checked_at=checked_at,
        )

        return {
            "postal_code": postal_code,
            "temperature_f": temperature_f,
            "cloud_cover_percent": current.get("cloud_cover"),
            "humidity_percent": current.get(
                "relative_humidity_2m"
            ),
            "dew_point_f": current.get("dew_point_2m"),
            "wind_speed_mph": current.get("wind_speed_10m"),
            # This is intentionally kept separate from the live reading.
            # The planner selects the relevant value for the scheduled start.
            "hourly_temperature_f": hourly_temperature_f,
            "hourly_forecast": hourly_forecast,
            "seeing": None,
            "transparency": None,
            "observing_rating": rating,
            "status": "Live weather connected.",
            "observed_at": current.get("time"),
            "fetched_at": checked_at.isoformat(),
        }

    except (URLError, TimeoutError, ValueError) as error:
        record_service_failure(
            "weather",
            f"Live weather unavailable: {error}",
            checked_at=checked_at,
        )
        return {
            "postal_code": postal_code,
            "temperature_f": None,
            "cloud_cover_percent": None,
            "humidity_percent": None,
            "dew_point_f": None,
            "wind_speed_mph": None,
            "hourly_temperature_f": {},
            "hourly_forecast": {},
            "seeing": None,
            "transparency": None,
            # A missing live forecast must never be interpreted as safe
            # observing conditions by the planner.
            "observing_rating": 0,
            "status": f"Weather unavailable: {error}",
            "observed_at": None,
            "fetched_at": checked_at.isoformat(),
        }


def _fetch_weather_data(url: str):
    last_error = None
    for attempt in range(WEATHER_REQUEST_ATTEMPTS):
        try:
            with urlopen(url, timeout=WEATHER_REQUEST_TIMEOUT_SECONDS) as response:
                return json.load(response)
        except (URLError, TimeoutError, ValueError) as error:
            last_error = error
            if attempt < WEATHER_REQUEST_ATTEMPTS - 1:
                sleep(WEATHER_RETRY_DELAY_SECONDS)
    raise last_error
