from datetime import datetime
from typing import Dict, Optional


SEEING_RANGES = {
    1: "<0.5″",
    2: "0.5–0.75″",
    3: "0.75–1.0″",
    4: "1.0–1.25″",
    5: "1.25–1.5″",
    6: "1.5–2.0″",
    7: "2.0–2.5″",
    8: ">2.5″",
}
TRANSPARENCY_RANGES = {
    1: "<0.3 mag/airmass",
    2: "0.3–0.4 mag/airmass",
    3: "0.4–0.5 mag/airmass",
    4: "0.5–0.6 mag/airmass",
    5: "0.6–0.7 mag/airmass",
    6: "0.7–0.85 mag/airmass",
    7: "0.85–1.0 mag/airmass",
    8: ">1.0 mag/airmass",
}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _points(value: float, maximum: float) -> float:
    return round(_clamp(value, 0, maximum), 1)


def _display_number(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _planned_or_current(weather: Dict, field: str):
    planned = weather.get(f"planned_{field}")
    return planned if planned is not None else weather.get(field)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %I:%M %p")
        except ValueError:
            return None


def _display_time(value: Optional[str]) -> str:
    parsed = _parse_datetime(value)
    return parsed.strftime("%I:%M %p").lstrip("0") if parsed else "unavailable"


def _weather_component(weather: Dict) -> Dict:
    cloud = _planned_or_current(weather, "cloud_cover_percent")
    humidity = _planned_or_current(weather, "humidity_percent")
    wind = _planned_or_current(weather, "wind_speed_mph")
    if cloud is None or humidity is None or wind is None:
        return {
            "key": "cloud",
            "label": "Cloud + stability",
            "description": "Cloud, humidity, or wind data is incomplete",
            "points": None,
            "max": 45,
            "source": "Future data",
        }

    cloud = _clamp(float(cloud), 0, 100)
    humidity = _clamp(float(humidity), 0, 100)
    wind = max(0, float(wind))
    if cloud >= 100:
        return {
            "key": "cloud",
            "label": "Cloud + stability",
            "description": (
                f"{_display_number(cloud)}% cloud · "
                f"{_display_number(humidity)}% humidity · "
                f"{_display_number(wind)} mph wind"
            ),
            "points": 0,
            "max": 45,
            "source": "Hard stop",
        }

    cloud_points = 30 * (1 - cloud / 100)
    humidity_points = 8 * (1 - _clamp((humidity - 50) / 50, 0, 1))
    wind_points = 7 * (1 - _clamp((wind - 5) / 15, 0, 1))
    return {
        "key": "cloud",
        "label": "Cloud + stability",
        "description": (
            f"{_display_number(cloud)}% cloud · "
            f"{_display_number(humidity)}% humidity · "
            f"{_display_number(wind)} mph wind"
        ),
        "points": _points(cloud_points + humidity_points + wind_points, 45),
        "max": 45,
        "source": "Proportional",
    }


def _darkness_component(darkness: Dict) -> Dict:
    start = _parse_datetime(darkness.get("astronomical_darkness_start"))
    end = _parse_datetime(darkness.get("astronomical_darkness_end"))
    if start is None or end is None or end <= start:
        return {
            "key": "night",
            "label": "Astronomical darkness",
            "description": "Usable darkness duration is unavailable",
            "points": None,
            "max": 20,
            "source": "Unavailable",
        }

    hours = (end - start).total_seconds() / 3600
    return {
        "key": "night",
        "label": "Astronomical darkness",
        "description": f"{_display_number(hours)} dark hours · full credit at 8 hours",
        "points": _points(hours / 8 * 20, 20),
        "max": 20,
        "source": "Proportional",
        "detail_title": "Astronomical darkness window",
        "detail": (
            f"Astronomical darkness runs from "
            f"{_display_time(darkness.get('astronomical_darkness_start'))} to "
            f"{_display_time(darkness.get('astronomical_darkness_end'))} "
            f"({_display_number(hours)} hours)."
        ),
    }


def _moon_component(moon: Dict) -> Dict:
    illumination = moon.get("illumination_percent")
    if illumination is None:
        return {
            "key": "moon",
            "label": "Moon interference",
            "description": "Moon illumination is unavailable",
            "points": None,
            "max": 15,
            "source": "Unavailable",
        }

    illumination = _clamp(float(illumination), 0, 100)
    if moon.get("above_horizon"):
        horizon_detail = (
            f"Above the horizon now; sets {_display_time(moon.get('next_moonset'))}."
            if moon.get("next_moonset")
            else "Above the horizon now."
        )
    else:
        horizon_detail = (
            f"Below the horizon now; rises {_display_time(moon.get('next_moonrise'))}."
            if moon.get("next_moonrise")
            else "Below the horizon now."
        )
    return {
        "key": "moon",
        "label": "Moon interference",
        "description": f"{_display_number(illumination)}% illuminated · lower is better",
        "points": _points(15 * (1 - illumination / 100), 15),
        "max": 15,
        "source": "Proportional",
        "detail_title": "Moon status",
        "detail": (
            f"{moon.get('phase_name') or 'Moon'} · "
            f"{_display_number(illumination)}% illuminated. {horizon_detail}"
        ),
    }


def _astro_forecast_component(
    *,
    key: str,
    field: str,
    label: str,
    weather: Dict,
    maximum: float,
    ranges: Dict[int, str],
) -> Dict:
    value = _planned_or_current(weather, f"{field}_index")
    forecast_at = _planned_or_current(weather, f"{field}_forecast_at")
    if value is None or forecast_at is None:
        return {
            "key": key,
            "label": label,
            "description": f"Astronomical {label.lower()} forecast unavailable",
            "points": None,
            "max": maximum,
            "source": "Unavailable",
        }

    try:
        index = int(value)
    except (TypeError, ValueError):
        index = 0
    if index not in ranges:
        return {
            "key": key,
            "label": label,
            "description": f"Astronomical {label.lower()} forecast unavailable",
            "points": None,
            "max": maximum,
            "source": "Unavailable",
        }

    quality = (
        "Excellent" if index <= 2
        else "Good" if index <= 4
        else "Fair" if index <= 6
        else "Poor"
    )
    measure_name = "seeing" if field == "seeing" else "extinction"
    return {
        "key": key,
        "label": label,
        "description": (
            f"{quality} · forecast {ranges[index]} {measure_name} "
            f"near {_display_time(forecast_at)}"
        ),
        "points": _points(maximum * (8 - index) / 7, maximum),
        "max": maximum,
        "source": "Forecast",
        "detail_title": f"{label} forecast",
        "detail": (
            f"7Timer ASTRO bin {index} of 8 at the forecast point nearest "
            f"the planned imaging start. Lower {measure_name} is better. "
            "Cloud, humidity, and wind are scored separately."
        ),
    }


def _altitude_component(target: Optional[Dict]) -> Dict:
    target = target or {}
    altitude = next(
        (
            target.get(field)
            for field in (
                "maximum_dark_altitude",
                "altitude_at_dark_midpoint",
                "average_dark_altitude",
                "current_altitude",
            )
            if target.get(field) is not None
        ),
        None,
    )
    if altitude is None:
        return {
            "key": "altitude",
            "label": "Target altitude",
            "description": "Target altitude is unavailable",
            "points": None,
            "max": 5,
            "source": "Unavailable",
        }

    altitude = _clamp(float(altitude), -90, 90)
    return {
        "key": "altitude",
        "label": "Target altitude",
        "description": f"{_display_number(altitude)}° peak altitude · 20°–90° scale",
        "points": _points((altitude - 20) / 70 * 5, 5),
        "max": 5,
        "source": "Proportional",
    }


def calculate_opportunity_score(
    *,
    weather: Dict,
    moon: Dict,
    darkness: Dict,
    target: Optional[Dict],
) -> Dict:
    components = [
        _weather_component(weather),
        _darkness_component(darkness),
        _moon_component(moon),
        _astro_forecast_component(
            key="visibility",
            field="transparency",
            label="Transparency",
            weather=weather,
            maximum=10,
            ranges=TRANSPARENCY_RANGES,
        ),
        _astro_forecast_component(
            key="seeing",
            field="seeing",
            label="Seeing",
            weather=weather,
            maximum=5,
            ranges=SEEING_RANGES,
        ),
        _altitude_component(target),
    ]
    total = round(sum(component["points"] or 0 for component in components), 1)
    return {
        "total": total,
        "label": opportunity_score_label(total),
        "guidance": "Use the score as a planning aid alongside the nightly recommendation.",
        "components": components,
    }


def opportunity_score_label(score: float) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Very good"
    if score >= 55:
        return "Usable"
    if score >= 35:
        return "Challenging"
    return "Poor"


def explain_opportunity_for_decision(score: Dict, decision: str) -> Dict:
    adjusted = dict(score)
    if decision == "Do Not Image":
        adjusted["label"] = "No imaging window"
        adjusted["guidance"] = (
            "The score still shows which ingredients are present, but the "
            "nightly recommendation is a hard stop because a critical safety "
            "or weather input failed."
        )
    elif decision == "Use Caution":
        adjusted["label"] = "Caution only"
        adjusted["guidance"] = (
            "Some ingredients are usable, but Polaris recommends a live "
            "conditions check before opening equipment."
        )
    else:
        adjusted["label"] = opportunity_score_label(adjusted["total"])
        adjusted["guidance"] = (
            "Conditions support imaging; use the component drivers to choose "
            "how ambitious tonight's plan should be."
        )
    return adjusted
