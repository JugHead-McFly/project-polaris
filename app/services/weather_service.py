import json
import os
from datetime import datetime, timedelta, timezone
from copy import deepcopy
from threading import RLock
from time import sleep
from typing import Optional
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

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
WEATHER_CACHE_TTL_SECONDS = 20 * 60
WEATHER_STALE_FALLBACK_SECONDS = 6 * 60 * 60
WEATHERAPI_FORECAST_DAYS = 3
ASTRO_FORECAST_URL = "https://www.7timer.info/bin/api.pl"
ASTRO_FORECAST_REQUEST_TIMEOUT_SECONDS = 6
ASTRO_FORECAST_MAX_MATCH_HOURS = 4

_weather_cache = {}
_weather_cache_lock = RLock()


def _empty_astro_forecast(status: str) -> dict:
    return {
        "seeing": None,
        "seeing_index": None,
        "seeing_forecast_at": None,
        "transparency": None,
        "transparency_index": None,
        "transparency_forecast_at": None,
        "hourly_astro_forecast": {},
        "astro_forecast_provider": None,
        "astro_forecast_status": status,
        "astro_forecast_fetched_at": None,
    }


def _astro_quality_label(index: int) -> str:
    if index <= 2:
        return "Excellent"
    if index <= 4:
        return "Good"
    if index <= 6:
        return "Fair"
    return "Poor"


def _parse_astro_forecast(
    data: dict,
    context: ObservatoryContext,
    checked_at: datetime,
) -> dict:
    if not isinstance(data, dict):
        return _empty_astro_forecast("Astronomy forecast response was invalid.")
    try:
        initialized_at = datetime.strptime(
            str(data.get("init")),
            "%Y%m%d%H",
        ).replace(tzinfo=timezone.utc)
        local_timezone = ZoneInfo(context.timezone_name or "UTC")
    except (TypeError, ValueError, KeyError):
        return _empty_astro_forecast("Astronomy forecast response was invalid.")

    hourly_astro_forecast = {}
    for item in data.get("dataseries") or []:
        if not isinstance(item, dict):
            continue
        try:
            timepoint = float(item.get("timepoint"))
        except (TypeError, ValueError):
            continue

        forecast = {}
        for field in ("seeing", "transparency"):
            try:
                index = int(item.get(field))
            except (TypeError, ValueError):
                continue
            if 1 <= index <= 8:
                forecast[f"{field}_index"] = index
        if not forecast:
            continue

        forecast_at = (
            initialized_at + timedelta(hours=timepoint)
        ).astimezone(local_timezone).replace(tzinfo=None)
        hourly_astro_forecast[forecast_at.isoformat(timespec="minutes")] = forecast

    if not hourly_astro_forecast:
        return _empty_astro_forecast("Astronomy forecast values were unavailable.")

    checked_local = checked_at.astimezone(local_timezone).replace(tzinfo=None)

    current = {}
    for field in ("seeing", "transparency"):
        key = f"{field}_index"
        candidates = []
        for time_text, forecast in hourly_astro_forecast.items():
            if key not in forecast:
                continue
            forecast_at = datetime.fromisoformat(time_text)
            candidates.append(
                (abs(forecast_at - checked_local), forecast_at, forecast[key])
            )
        if not candidates:
            continue
        difference, forecast_at, index = min(candidates, key=lambda item: item[0])
        if difference <= timedelta(hours=ASTRO_FORECAST_MAX_MATCH_HOURS):
            current[key] = index
            current[f"{field}_forecast_at"] = forecast_at.strftime(
                "%Y-%m-%d %I:%M %p"
            )

    if not current:
        return _empty_astro_forecast("Astronomy forecast did not cover the current period.")

    seeing_index = current.get("seeing_index")
    transparency_index = current.get("transparency_index")
    return {
        "seeing": _astro_quality_label(seeing_index) if seeing_index else None,
        "seeing_index": seeing_index,
        "seeing_forecast_at": current.get("seeing_forecast_at"),
        "transparency": (
            _astro_quality_label(transparency_index)
            if transparency_index
            else None
        ),
        "transparency_index": transparency_index,
        "transparency_forecast_at": current.get("transparency_forecast_at"),
        "hourly_astro_forecast": hourly_astro_forecast,
        "astro_forecast_provider": "7timer-astro",
        "astro_forecast_status": "Astronomy forecast connected.",
        "astro_forecast_fetched_at": checked_at.isoformat(),
    }


def _get_astro_forecast(
    context: ObservatoryContext,
    checked_at: datetime,
) -> dict:
    # 7Timer's model is much coarser than a neighborhood. Never disclose the
    # saved coordinate precision: the user-approved request is rounded to 0.1°.
    params = {
        "lat": f"{round(context.latitude, 1):.1f}",
        "lon": f"{round(context.longitude, 1):.1f}",
        "product": "astro",
        "output": "json",
    }
    url = ASTRO_FORECAST_URL + "?" + urlencode(params)
    try:
        with urlopen(
            url,
            timeout=ASTRO_FORECAST_REQUEST_TIMEOUT_SECONDS,
        ) as response:
            data = json.load(response)
    except (URLError, TimeoutError, ValueError):
        return _empty_astro_forecast("Astronomy forecast unavailable.")
    return _parse_astro_forecast(data, context, checked_at)


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
    cache_key = _weather_cache_key(context)
    cached_weather = _get_cached_weather(cache_key, checked_at)
    if cached_weather is not None:
        return cached_weather

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

        weather = {
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
            **_get_astro_forecast(context, checked_at),
            "observing_rating": rating,
            "status": "Live weather connected.",
            "observed_at": current.get("time"),
            "fetched_at": checked_at.isoformat(),
        }
        _store_cached_weather(cache_key, weather, checked_at)
        return weather

    except (URLError, TimeoutError, ValueError) as error:
        stale_weather = _get_cached_weather(
            cache_key,
            checked_at,
            allow_stale=True,
        )
        if stale_weather is not None:
            stale_weather["status"] = (
                f"Using recent cached weather because live weather "
                f"is unavailable: {error}"
            )
            record_service_failure(
                "weather",
                stale_weather["status"],
                checked_at=checked_at,
            )
            return stale_weather

        fallback_weather = _get_weatherapi_summary(
            postal_code,
            context,
            checked_at,
        )
        if fallback_weather is not None:
            fallback_weather.update(_get_astro_forecast(context, checked_at))
            record_service_success(
                "weather",
                "Fallback weather data received successfully.",
                checked_at=checked_at,
            )
            _store_cached_weather(cache_key, fallback_weather, checked_at)
            return fallback_weather

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
            **_get_astro_forecast(context, checked_at),
            # A missing live forecast must never be interpreted as safe
            # observing conditions by the planner.
            "observing_rating": 0,
            "status": f"Weather unavailable: {error}",
            "observed_at": None,
            # No provider returned data, so there is no truthful data-pull
            # timestamp to expose. Attempt timing remains in diagnostics.
            "fetched_at": None,
        }


def _fetch_weather_data(url: str):
    last_error = None
    for attempt in range(WEATHER_REQUEST_ATTEMPTS):
        try:
            with urlopen(url, timeout=WEATHER_REQUEST_TIMEOUT_SECONDS) as response:
                return json.load(response)
        except (URLError, TimeoutError, ValueError) as error:
            last_error = error
            if _is_rate_limited(error):
                break
            if attempt < WEATHER_REQUEST_ATTEMPTS - 1:
                sleep(WEATHER_RETRY_DELAY_SECONDS)
    raise last_error


def _is_rate_limited(error) -> bool:
    return isinstance(error, HTTPError) and error.code == 429


def _get_weatherapi_summary(
    postal_code: str,
    context: ObservatoryContext,
    checked_at: datetime,
):
    api_key = os.getenv("POLARIS_WEATHERAPI_KEY", "").strip()
    if not api_key:
        return None

    params = {
        "key": api_key,
        "q": f"{context.latitude},{context.longitude}",
        "days": WEATHERAPI_FORECAST_DAYS,
        "aqi": "no",
        "alerts": "no",
    }
    url = "https://api.weatherapi.com/v1/forecast.json?" + urlencode(params)

    try:
        data = _fetch_weather_data(url)
    except (URLError, TimeoutError, ValueError):
        return None

    current = data.get("current", {})
    cloud_cover = current.get("cloud")
    humidity = current.get("humidity")
    wind_speed = current.get("wind_mph")
    rating = calculate_observing_rating(
        cloud_cover,
        humidity,
        wind_speed,
    )
    hourly_forecast = {}
    for forecast_day in data.get("forecast", {}).get("forecastday", []):
        for hour in forecast_day.get("hour", []):
            forecast_time = hour.get("time")
            if not forecast_time:
                continue
            hourly_forecast[forecast_time.replace(" ", "T")] = {
                "temperature_f": hour.get("temp_f"),
                "humidity_percent": hour.get("humidity"),
                "dew_point_f": hour.get("dewpoint_f"),
                "cloud_cover_percent": hour.get("cloud"),
                "wind_speed_mph": hour.get("wind_mph"),
            }

    hourly_temperature_f = {
        time: forecast["temperature_f"]
        for time, forecast in hourly_forecast.items()
        if forecast.get("temperature_f") is not None
    }

    return {
        "postal_code": postal_code,
        "temperature_f": current.get("temp_f"),
        "cloud_cover_percent": cloud_cover,
        "humidity_percent": humidity,
        "dew_point_f": current.get("dewpoint_f"),
        "wind_speed_mph": wind_speed,
        "hourly_temperature_f": hourly_temperature_f,
        "hourly_forecast": hourly_forecast,
        **_empty_astro_forecast("Astronomy forecast not requested yet."),
        "observing_rating": rating,
        "status": "Fallback weather connected via WeatherAPI.com.",
        "observed_at": current.get("last_updated"),
        "fetched_at": checked_at.isoformat(),
        "provider": "weatherapi",
    }


def _weather_cache_key(context: ObservatoryContext):
    return (
        round(context.latitude, 2),
        round(context.longitude, 2),
    )


def _get_cached_weather(
    cache_key,
    checked_at: datetime,
    *,
    allow_stale: bool = False,
):
    max_age_seconds = (
        WEATHER_STALE_FALLBACK_SECONDS
        if allow_stale
        else WEATHER_CACHE_TTL_SECONDS
    )
    with _weather_cache_lock:
        cached = _weather_cache.get(cache_key)
        if cached is None:
            return None
        age_seconds = (
            checked_at - cached["cached_at"]
        ).total_seconds()
        if age_seconds > max_age_seconds:
            return None
        weather = deepcopy(cached["weather"])

    if allow_stale:
        weather["cache_status"] = "stale"
    else:
        weather["cache_status"] = "fresh"
    return weather


def _store_cached_weather(
    cache_key,
    weather,
    checked_at: datetime,
) -> None:
    with _weather_cache_lock:
        _weather_cache[cache_key] = {
            "cached_at": checked_at,
            "weather": deepcopy(weather),
        }


def reset_weather_cache() -> None:
    with _weather_cache_lock:
        _weather_cache.clear()
