from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.core.diagnostics import get_service_diagnostics
from app.core.diagnostics import record_service_failure
from app.core.diagnostics import record_service_success
from app.core.diagnostics import reset_service_diagnostics
from app.services.system_service import build_data_freshness


def record(**values):
    return SimpleNamespace(**values)


def test_data_freshness_handles_night_and_timezone_boundary():
    now = datetime(2026, 7, 17, 7, 15, tzinfo=timezone.utc)
    freshness = build_data_freshness(
        captures=[
            record(
                observation_utc="2026-07-16T23:45:00-07:00",
                updated_at=datetime(2026, 7, 17, 6, 50),
            )
        ],
        sessions=[record(updated_at=datetime(2026, 7, 17, 6, 55))],
        analyses=[record(created_at=datetime(2026, 7, 17, 7, 0))],
        now=now,
    )

    assert freshness["status"] == "Current"
    assert freshness["capture_age_hours"] == 0.5
    assert freshness["latest_capture_observation_utc"] == (
        "2026-07-17T06:45:00+00:00"
    )


def test_data_freshness_thresholds_are_explicit():
    now = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)

    def status_for_age(age):
        timestamp = (now - age).isoformat()
        return build_data_freshness(
            captures=[record(observation_utc=timestamp, updated_at=timestamp)],
            sessions=[],
            analyses=[],
            now=now,
        )["status"]

    assert status_for_age(timedelta(hours=24)) == "Current"
    assert status_for_age(timedelta(hours=24, seconds=1)) == "Recent"
    assert status_for_age(timedelta(days=30)) == "Recent"
    assert status_for_age(timedelta(days=30, seconds=1)) == "Stale"


def test_service_diagnostics_preserve_last_success_across_failure():
    reset_service_diagnostics()
    first_check = datetime(2026, 7, 17, 10, 0, tzinfo=timezone.utc)
    second_check = datetime(2026, 7, 17, 10, 5, tzinfo=timezone.utc)

    record_service_success(
        "weather",
        "Weather connected.",
        checked_at=first_check,
    )
    record_service_failure(
        "weather",
        "Weather timed out.",
        checked_at=second_check,
    )
    weather = get_service_diagnostics()[0]

    assert weather["status"] == "Degraded"
    assert weather["checked_at"] == second_check.isoformat()
    assert weather["last_success_at"] == first_check.isoformat()

    reset_service_diagnostics()
