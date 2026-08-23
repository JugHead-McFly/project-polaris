from datetime import datetime
from typing import Dict, Optional, Tuple


HIGH_RISK_SPREAD_F = 3.0
WATCH_SPREAD_F = 7.0


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


def _window_forecast_point(
    weather: Dict,
    planned_start: Optional[str],
    planned_end: Optional[str],
) -> Tuple[Optional[Dict], bool]:
    start = _parse_local_datetime(planned_start)
    end = _parse_local_datetime(planned_end)
    candidates = []
    has_incomplete_window_data = False

    if start is not None and end is not None and end >= start:
        for time_text, conditions in (
            weather.get("hourly_forecast") or {}
        ).items():
            forecast_time = _parse_local_datetime(time_text)
            if forecast_time is None or not start <= forecast_time <= end:
                continue
            temperature_f = _number(conditions.get("temperature_f"))
            dew_point_f = _number(conditions.get("dew_point_f"))
            if temperature_f is None or dew_point_f is None:
                has_incomplete_window_data = True
                continue
            candidates.append(
                {
                    "temperature_f": temperature_f,
                    "dew_point_f": dew_point_f,
                    "spread_f": temperature_f - dew_point_f,
                    "forecast_at": forecast_time.strftime(
                        "%Y-%m-%d %I:%M %p"
                    ),
                }
            )

    if has_incomplete_window_data:
        return None, False

    if candidates:
        return min(candidates, key=lambda item: item["spread_f"]), True

    temperature_f = _number(weather.get("planned_temperature_f"))
    dew_point_f = _number(weather.get("planned_dew_point_f"))
    if temperature_f is None or dew_point_f is None:
        return None, False
    return (
        {
            "temperature_f": temperature_f,
            "dew_point_f": dew_point_f,
            "spread_f": temperature_f - dew_point_f,
            "forecast_at": weather.get("planned_temperature_at"),
        },
        True,
    )


def assess_dew_risk(
    weather: Dict,
    *,
    planned_start: Optional[str],
    planned_end: Optional[str],
) -> Dict:
    """Translate planned-window temperature/dew point into honest guidance."""
    point, coverage_complete = _window_forecast_point(
        weather, planned_start, planned_end
    )
    if point is None or not coverage_complete:
        return {
            "level": "unavailable",
            "label": "Dew risk unavailable",
            "summary": (
                "Planned-window temperature or dew-point data is incomplete."
            ),
            "action": (
                "Check local conditions before imaging and keep dew control "
                "available if moisture begins forming."
            ),
            "temperature_f": None,
            "dew_point_f": None,
            "spread_f": None,
            "forecast_at": None,
        }

    spread_f = round(max(0.0, point["spread_f"]), 1)
    point["spread_f"] = spread_f
    spread_text = f"{spread_f:g}°F"

    if spread_f <= HIGH_RISK_SPREAD_F:
        return {
            **point,
            "level": "high",
            "label": "High dew risk",
            "summary": (
                f"Forecast air comes within about {spread_text} of the dew "
                "point during the planned window."
            ),
            "action": (
                "Use dew control from the start and check the optics "
                "periodically for condensation."
            ),
        }

    if spread_f <= WATCH_SPREAD_F:
        return {
            **point,
            "level": "watch",
            "label": "Watch for dew",
            "summary": (
                f"Forecast air comes within about {spread_text} of the dew "
                "point during the planned window."
            ),
            "action": (
                "Have dew control ready and monitor the optics for "
                "condensation as temperatures fall."
            ),
        }

    return {
        **point,
        "level": "low",
        "label": "Low dew risk",
        "summary": (
            f"Forecast air stays at least about {spread_text} above the dew "
            "point during the planned window."
        ),
        "action": (
            "No special dew action is indicated; continue to monitor local "
            "conditions."
        ),
    }
