from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.forecast_accuracy_service import (
    _latest_forecast_snapshots,
    _satellite_reliability,
)


def snapshot(hour=3, forecast=0, satellite=100, lead=1):
    target = datetime(2026, 9, 6, hour, tzinfo=timezone.utc)
    return SimpleNamespace(
        forecast_for=target,
        forecast_created_at=target - timedelta(hours=lead),
        forecast_cloud_cover_percent=forecast,
        satellite_cloud_observation={
            "status": "usable", "cloud_cover_percent": satellite,
            "good_pixel_fraction": 1, "radius_km": 10,
            "forecast_for": target.isoformat(),
            "scan_midpoint": (target - timedelta(minutes=2)).isoformat(),
        },
    )


def test_latest_revision_once_and_after_midnight_in_same_evening():
    rows = [snapshot(forecast=50, lead=2), snapshot(), snapshot(hour=8, satellite=0)]
    result = _satellite_reliability(_latest_forecast_snapshots(rows), "America/Phoenix")
    assert result["check_count"] == 2
    assert result["average_absolute_difference"] == 50
    assert len(result["nights"]) == 1
    assert result["nights"][0]["evening"] == "2026-09-05"
    assert result["nights"][0]["checks"][0]["forecast_cloud_cover_percent"] == 0


@pytest.mark.parametrize("field,value", [
    ("status", "insufficient_quality"), ("cloud_cover_percent", float("nan")),
    ("cloud_cover_percent", 101), ("good_pixel_fraction", .89),
    ("forecast_for", "2026-09-05T03:00:00+00:00"),
    ("scan_midpoint", "2026-09-06T02:15:00+00:00"),
    ("scan_midpoint", "2026-09-06T03:00:00"),
])
def test_invalid_satellite_reference_does_not_inflate_reliability(field, value):
    row = snapshot()
    row.satellite_cloud_observation[field] = value
    assert _satellite_reliability([row], "UTC")["check_count"] == 0


def test_model_only_and_post_target_forecasts_are_not_scored():
    old = snapshot()
    old.satellite_cloud_observation = None
    future = snapshot(lead=-1)
    result = _satellite_reliability([old, future], "UTC")
    assert result["check_count"] == 0
    assert result["average_absolute_difference"] is None


def test_api_schema_preserves_satellite_summary():
    from app.schemas.tonight import ForecastAccuracySummary
    summary = _satellite_reliability([snapshot()], "America/Phoenix")
    response = ForecastAccuracySummary(
        state="ready_for_calibration", label="", message="",
        matched_samples=1, minimum_samples=5, satellite_reliability=summary,
    )
    assert response.model_dump()["satellite_reliability"]["check_count"] == 1
