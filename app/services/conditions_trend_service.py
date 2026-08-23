from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


TREND_THRESHOLD_POINTS = 3.0
MINIMUM_TREND_SPAN = timedelta(hours=1)
MAXIMUM_BOUNDARY_GAP = timedelta(minutes=75)


def _parse_local_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d %I:%M %p")
        except ValueError:
            return None
    return parsed.replace(tzinfo=None)


def _number(value) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _condition_point(time: datetime, conditions: Dict) -> Optional[Dict]:
    cloud = _number(conditions.get("cloud_cover_percent"))
    humidity = _number(conditions.get("humidity_percent"))
    wind = _number(conditions.get("wind_speed_mph"))
    if cloud is None or humidity is None or wind is None:
        return None

    cloud = _clamp(cloud, 0, 100)
    humidity = _clamp(humidity, 0, 100)
    wind = max(0, wind)
    components = {
        "cloud": 30 * (1 - cloud / 100),
        "humidity": 8 * (1 - _clamp((humidity - 50) / 50, 0, 1)),
        "wind": 7 * (1 - _clamp((wind - 5) / 15, 0, 1)),
    }
    return {
        "time": time,
        "cloud": cloud,
        "humidity": humidity,
        "wind": wind,
        "components": components,
        "score": sum(components.values()),
    }


def _window_points(
    weather: Dict,
    planned_start: Optional[str],
    planned_end: Optional[str],
) -> Tuple[List[Dict], bool]:
    start = _parse_local_datetime(planned_start)
    end = _parse_local_datetime(planned_end)
    if start is None or end is None or end <= start:
        return [], False

    points = []
    coverage_complete = True
    for time_text, conditions in (weather.get("hourly_forecast") or {}).items():
        forecast_time = _parse_local_datetime(time_text)
        if forecast_time is None or not start <= forecast_time <= end:
            continue
        if not isinstance(conditions, dict):
            coverage_complete = False
            continue
        point = _condition_point(forecast_time, conditions)
        if point is None:
            coverage_complete = False
            continue
        points.append(point)
    return sorted(points, key=lambda item: item["time"]), coverage_complete


def _display_number(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _dominant_basis(start: Dict, end: Dict) -> Optional[str]:
    component_changes = {
        key: end["components"][key] - start["components"][key]
        for key in ("cloud", "humidity", "wind")
    }
    key = max(component_changes, key=lambda item: abs(component_changes[item]))
    if abs(component_changes[key]) < 1:
        return None

    before = start[key]
    after = end[key]
    if key == "cloud":
        verb = "drops" if after < before else "rises"
        return (
            f"Cloud cover {verb} from {_display_number(before)}% to "
            f"{_display_number(after)}%."
        )
    if key == "wind":
        verb = "eases" if after < before else "increases"
        return (
            f"Wind {verb} from {_display_number(before)} to "
            f"{_display_number(after)} mph."
        )

    verb = "falls" if after < before else "rises"
    return (
        f"Humidity {verb} from {_display_number(before)}% to "
        f"{_display_number(after)}%."
    )


def _unavailable() -> Dict:
    return {
        "direction": "unavailable",
        "label": "Trend unavailable",
        "message": (
            "Trend unavailable: check live conditions at the window start."
        ),
        "basis": None,
        "forecast_start": None,
        "forecast_end": None,
    }


def assess_conditions_trend(
    weather: Dict,
    *,
    planned_start: Optional[str],
    planned_end: Optional[str],
) -> Dict:
    """Describe meaningful weather movement across a recommended window."""
    points, coverage_complete = _window_points(
        weather, planned_start, planned_end
    )
    if len(points) < 2 or not coverage_complete:
        return _unavailable()

    start, end = points[0], points[-1]
    planned_start_time = _parse_local_datetime(planned_start)
    planned_end_time = _parse_local_datetime(planned_end)
    if planned_start_time is None or planned_end_time is None:
        return _unavailable()
    if (
        start["time"] - planned_start_time > MAXIMUM_BOUNDARY_GAP
        or planned_end_time - end["time"] > MAXIMUM_BOUNDARY_GAP
    ):
        return _unavailable()
    if end["time"] - start["time"] < MINIMUM_TREND_SPAN:
        return _unavailable()

    score_change = end["score"] - start["score"]
    basis = _dominant_basis(start, end)
    if score_change >= TREND_THRESHOLD_POINTS:
        direction = "improving"
        label = "Improving"
        message = "Improving: later may be better."
    elif score_change <= -TREND_THRESHOLD_POINTS:
        direction = "worsening"
        label = "Worsening"
        message = "Worsening: favor the window opening if you image."
    else:
        direction = "steady"
        label = "Steady"
        message = "Steady: start when the window opens."
        basis = None

    if basis:
        message = f"{message} {basis}"

    return {
        "direction": direction,
        "label": label,
        "message": message,
        "basis": basis,
        "forecast_start": start["time"].strftime("%Y-%m-%d %I:%M %p"),
        "forecast_end": end["time"].strftime("%Y-%m-%d %I:%M %p"),
    }
