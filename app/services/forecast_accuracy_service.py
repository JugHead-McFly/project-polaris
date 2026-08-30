from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Dict
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import ForecastAccuracySnapshot
from app.models import HostedObservatory


RETENTION_DAYS = 90
MATCH_TOLERANCE_MINUTES = 75
FORECAST_EXPIRY_HOURS = 2
MINIMUM_CONFIDENCE_SAMPLES = 5
LOCAL_DATE_TIME_FORMAT = "%Y-%m-%d %I:%M %p"
TRACKED_FIELDS = (
    "temperature_f",
    "cloud_cover_percent",
    "humidity_percent",
    "dew_point_f",
    "wind_speed_mph",
)


def _as_utc(value: Optional[datetime]) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_provider_time(
    value: Optional[str],
    timezone_name: str,
) -> Optional[datetime]:
    if not value:
        return None
    normalized = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized.replace(" ", "T"))
    except (TypeError, ValueError):
        try:
            parsed = datetime.strptime(normalized, LOCAL_DATE_TIME_FORMAT)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        try:
            parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
        except (KeyError, ValueError):
            return None
    return parsed.astimezone(timezone.utc)


def _provider_name(weather: Dict) -> Optional[str]:
    provider = weather.get("provider")
    if provider:
        return str(provider)[:40]
    status = str(weather.get("status") or "").lower()
    if "open-meteo" in status or status == "live weather connected.":
        return "open-meteo"
    if "weatherapi" in status:
        return "weatherapi"
    return None


def _has_values(values: Dict, prefix: str = "") -> bool:
    return any(values.get(f"{prefix}{field}") is not None for field in TRACKED_FIELDS)


def _set_forecast_values(snapshot: ForecastAccuracySnapshot, weather: Dict) -> None:
    for field in TRACKED_FIELDS:
        setattr(snapshot, f"forecast_{field}", weather.get(f"planned_{field}"))


def _set_observed_values(snapshot: ForecastAccuracySnapshot, weather: Dict) -> None:
    for field in TRACKED_FIELDS:
        setattr(snapshot, f"observed_{field}", weather.get(field))


def _expire_old_pending(
    db: Session,
    *,
    user_id: UUID,
    observatory_id,
    reference_time: datetime,
) -> None:
    (
        db.query(ForecastAccuracySnapshot)
        .filter(
            ForecastAccuracySnapshot.user_id == user_id,
            ForecastAccuracySnapshot.observatory_id == observatory_id,
            ForecastAccuracySnapshot.status == "pending",
            ForecastAccuracySnapshot.expires_at < reference_time,
        )
        .update({"status": "expired"}, synchronize_session=False)
    )


def _match_nearest_observation(
    db: Session,
    *,
    user_id: UUID,
    observatory: HostedObservatory,
    weather: Dict,
    checked_at: datetime,
) -> None:
    observed_at = _parse_provider_time(
        weather.get("observed_at"),
        observatory.timezone_name,
    )
    if observed_at is None or not _has_values(weather):
        _expire_old_pending(
            db,
            user_id=user_id,
            observatory_id=observatory.id,
            reference_time=checked_at,
        )
        return

    tolerance = timedelta(minutes=MATCH_TOLERANCE_MINUTES)
    candidates = (
        db.query(ForecastAccuracySnapshot)
        .filter(
            ForecastAccuracySnapshot.user_id == user_id,
            ForecastAccuracySnapshot.observatory_id == observatory.id,
            ForecastAccuracySnapshot.status == "pending",
            ForecastAccuracySnapshot.forecast_for >= observed_at - tolerance,
            ForecastAccuracySnapshot.forecast_for <= observed_at + tolerance,
        )
        .all()
    )
    if candidates:
        snapshot = min(
            candidates,
            key=lambda item: abs(
                _as_utc(item.forecast_for) - observed_at
            ),
        )
        snapshot.observed_at = observed_at
        snapshot.observed_provider = _provider_name(weather)
        _set_observed_values(snapshot, weather)
        snapshot.status = "matched"
        snapshot.matched_at = checked_at

    _expire_old_pending(
        db,
        user_id=user_id,
        observatory_id=observatory.id,
        reference_time=observed_at,
    )


def _capture_planned_forecast(
    db: Session,
    *,
    user_id: UUID,
    observatory: HostedObservatory,
    weather: Dict,
    checked_at: datetime,
) -> None:
    forecast_for = _parse_provider_time(
        weather.get("planned_temperature_at"),
        observatory.timezone_name,
    )
    if (
        forecast_for is None
        or forecast_for <= checked_at
        or not _has_values(weather, "planned_")
    ):
        return

    snapshot = (
        db.query(ForecastAccuracySnapshot)
        .filter(
            ForecastAccuracySnapshot.user_id == user_id,
            ForecastAccuracySnapshot.observatory_id == observatory.id,
            ForecastAccuracySnapshot.forecast_for == forecast_for,
        )
        .one_or_none()
    )
    if snapshot is not None and snapshot.status != "pending":
        return

    forecast_created_at = _parse_provider_time(
        weather.get("fetched_at"),
        observatory.timezone_name,
    ) or checked_at
    if snapshot is None:
        snapshot = ForecastAccuracySnapshot(
            user_id=user_id,
            observatory_id=observatory.id,
            forecast_for=forecast_for,
            forecast_created_at=forecast_created_at,
            expires_at=forecast_for + timedelta(hours=FORECAST_EXPIRY_HOURS),
            status="pending",
        )
        db.add(snapshot)
    else:
        snapshot.forecast_created_at = forecast_created_at
        snapshot.expires_at = forecast_for + timedelta(
            hours=FORECAST_EXPIRY_HOURS
        )
    snapshot.forecast_provider = _provider_name(weather)
    _set_forecast_values(snapshot, weather)


def _apply_retention(
    db: Session,
    *,
    user_id: UUID,
    observatory_id,
    checked_at: datetime,
) -> None:
    cutoff = checked_at - timedelta(days=RETENTION_DAYS)
    (
        db.query(ForecastAccuracySnapshot)
        .filter(
            ForecastAccuracySnapshot.user_id == user_id,
            ForecastAccuracySnapshot.observatory_id == observatory_id,
            ForecastAccuracySnapshot.created_at < cutoff,
        )
        .delete(synchronize_session=False)
    )


def forecast_accuracy_summary(
    db: Session,
    *,
    user_id: UUID,
    observatory_id,
) -> Dict:
    matched_count = (
        db.query(ForecastAccuracySnapshot)
        .filter(
            ForecastAccuracySnapshot.user_id == user_id,
            ForecastAccuracySnapshot.observatory_id == observatory_id,
            ForecastAccuracySnapshot.status == "matched",
        )
        .count()
    )
    remaining = max(0, MINIMUM_CONFIDENCE_SAMPLES - matched_count)
    if remaining:
        message = (
            "Not enough verified history yet. "
            f"{matched_count} of {MINIMUM_CONFIDENCE_SAMPLES} forecast "
            "checks matched."
        )
    else:
        message = (
            "Enough checks have been collected for a future calibrated "
            "confidence rating. Polaris is not using them in tonight's "
            "score yet."
        )
    return {
        "state": "building" if remaining else "ready_for_calibration",
        "label": "Building forecast confidence",
        "message": message,
        "matched_samples": matched_count,
        "minimum_samples": MINIMUM_CONFIDENCE_SAMPLES,
        "confidence": None,
    }


def track_forecast_accuracy(
    db: Session,
    *,
    user_id: UUID,
    observatory: HostedObservatory,
    weather: Dict,
    checked_at: Optional[datetime] = None,
) -> Dict:
    checked_at = _as_utc(checked_at)
    _apply_retention(
        db,
        user_id=user_id,
        observatory_id=observatory.id,
        checked_at=checked_at,
    )
    _match_nearest_observation(
        db,
        user_id=user_id,
        observatory=observatory,
        weather=weather,
        checked_at=checked_at,
    )
    _capture_planned_forecast(
        db,
        user_id=user_id,
        observatory=observatory,
        weather=weather,
        checked_at=checked_at,
    )
    db.commit()
    return forecast_accuracy_summary(
        db,
        user_id=user_id,
        observatory_id=observatory.id,
    )


def unavailable_forecast_accuracy_summary() -> Dict:
    return {
        "state": "unavailable",
        "label": "Forecast confidence unavailable",
        "message": "Signed-in forecast history is needed to build confidence.",
        "matched_samples": 0,
        "minimum_samples": MINIMUM_CONFIDENCE_SAMPLES,
        "confidence": None,
    }
