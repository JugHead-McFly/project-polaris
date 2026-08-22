from datetime import datetime
from typing import Dict, Optional


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
            "source": "Unavailable",
        }

    cloud = _clamp(float(cloud), 0, 100)
    humidity = _clamp(float(humidity), 0, 100)
    wind = max(0, float(wind))
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


def _categorical_component(
    *,
    key: str,
    label: str,
    value,
    maximum: float,
    mapping: Dict[str, float],
) -> Dict:
    if value is None:
        return {
            "key": key,
            "label": label,
            "description": f"No live {label.lower()} measure yet",
            "points": None,
            "max": maximum,
            "source": "Future data",
        }

    category = str(value).strip()
    points = mapping.get(category.lower())
    if points is None:
        return {
            "key": key,
            "label": label,
            "description": f"Unrecognized forecast category: {category}",
            "points": None,
            "max": maximum,
            "source": "Unavailable",
        }

    return {
        "key": key,
        "label": label,
        "description": f"{category} forecast category",
        "points": points,
        "max": maximum,
        "source": "Category",
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
        _categorical_component(
            key="visibility",
            label="Transparency",
            value=weather.get("transparency"),
            maximum=10,
            mapping={"excellent": 10, "good": 7.5, "fair": 5, "poor": 2.5},
        ),
        _categorical_component(
            key="seeing",
            label="Seeing",
            value=weather.get("seeing"),
            maximum=5,
            mapping={"excellent": 5, "good": 3.8, "fair": 2.5, "poor": 1.2},
        ),
        _altitude_component(target),
    ]
    total = round(sum(component["points"] or 0 for component in components), 1)
    return {"total": total, "components": components}
