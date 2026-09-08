from datetime import datetime
from datetime import timedelta
from datetime import timezone
import math
from typing import Dict
from typing import List
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
RECENT_HISTORY_LIMIT = 8
MINIMUM_HORIZON_SAMPLES = 5
HORIZON_BUCKETS = (
    ("0_6", "0-6 hr", 0, 6),
    ("6_12", "6-12 hr", 6, 12),
    ("12_24", "12-24 hr", 12, 24),
    ("24_plus", "24+ hr", 24, None),
)


def _round(value: Optional[float], digits: int = 1) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


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
        nearest = min(
            candidates,
            key=lambda item: abs(
                _as_utc(item.forecast_for) - observed_at
            ),
        )
        nearest_forecast_for = _as_utc(nearest.forecast_for)
        for snapshot in candidates:
            if _as_utc(snapshot.forecast_for) != nearest_forecast_for:
                continue
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

    forecast_created_at = _parse_provider_time(
        weather.get("fetched_at"),
        observatory.timezone_name,
    ) or checked_at
    lead_hours = max(
        0,
        (forecast_for - _as_utc(forecast_created_at)).total_seconds() / 3600,
    )
    lead_hour = int(math.ceil(lead_hours))
    snapshot = (
        db.query(ForecastAccuracySnapshot)
        .filter(
            ForecastAccuracySnapshot.user_id == user_id,
            ForecastAccuracySnapshot.observatory_id == observatory.id,
            ForecastAccuracySnapshot.forecast_for == forecast_for,
            ForecastAccuracySnapshot.forecast_lead_hour == lead_hour,
        )
        .one_or_none()
    )
    if snapshot is not None:
        return

    snapshot = ForecastAccuracySnapshot(
        user_id=user_id,
        observatory_id=observatory.id,
        forecast_for=forecast_for,
        forecast_created_at=forecast_created_at,
        forecast_lead_hour=lead_hour,
        expires_at=forecast_for + timedelta(hours=FORECAST_EXPIRY_HOURS),
        status="pending",
    )
    db.add(snapshot)
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
    matched_snapshots = (
        db.query(ForecastAccuracySnapshot)
        .filter(
            ForecastAccuracySnapshot.user_id == user_id,
            ForecastAccuracySnapshot.observatory_id == observatory_id,
            ForecastAccuracySnapshot.status == "matched",
        )
        .order_by(ForecastAccuracySnapshot.forecast_for.desc())
        .all()
    )
    latest_snapshots = _latest_forecast_snapshots(matched_snapshots)
    matched_count = len(latest_snapshots)
    remaining = max(0, MINIMUM_CONFIDENCE_SAMPLES - matched_count)
    if remaining:
        message = (
            f"{matched_count} verified forecast comparison"
            f"{'s' if matched_count != 1 else ''} collected. Trends begin "
            f"after {MINIMUM_CONFIDENCE_SAMPLES}."
        )
    else:
        message = (
            f"{matched_count} verified comparisons show an early pattern. "
            "This is not a confidence rating and does not affect tonight's "
            "score."
        )
    recent_checks = _recent_checks(latest_snapshots)
    metrics = _accuracy_metrics(latest_snapshots)
    horizon_buckets = _horizon_metrics(matched_snapshots)
    return {
        "state": "building" if remaining else "ready_for_calibration",
        "label": "Building forecast confidence",
        "message": message,
        "matched_samples": matched_count,
        "revision_count": len(matched_snapshots),
        "minimum_samples": MINIMUM_CONFIDENCE_SAMPLES,
        "confidence": None,
        "metrics": metrics,
        "recent_checks": recent_checks,
        "has_history_chart": len(recent_checks) >= 3,
        "horizon_buckets": horizon_buckets,
        "has_horizon_analysis": sum(
            1 for bucket in horizon_buckets if bucket["ready"]
        ) >= 2,
    }


def _field_error(snapshot: ForecastAccuracySnapshot, field: str) -> Optional[float]:
    forecast = getattr(snapshot, f"forecast_{field}")
    observed = getattr(snapshot, f"observed_{field}")
    if forecast is None or observed is None:
        return None
    return abs(float(forecast) - float(observed))


def _field_bias(snapshot: ForecastAccuracySnapshot, field: str) -> Optional[float]:
    forecast = getattr(snapshot, f"forecast_{field}")
    observed = getattr(snapshot, f"observed_{field}")
    if forecast is None or observed is None:
        return None
    return float(observed) - float(forecast)


def _average(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def _hours_between(start: datetime, end: datetime) -> Optional[float]:
    if start is None or end is None:
        return None
    return max(0, (_as_utc(end) - _as_utc(start)).total_seconds() / 3600)


def _latest_forecast_snapshots(
    snapshots: List[ForecastAccuracySnapshot],
) -> List[ForecastAccuracySnapshot]:
    latest_by_hour = {}
    for snapshot in snapshots:
        forecast_for = _as_utc(snapshot.forecast_for)
        current = latest_by_hour.get(forecast_for)
        if current is None or _as_utc(snapshot.forecast_created_at) > _as_utc(
            current.forecast_created_at
        ):
            latest_by_hour[forecast_for] = snapshot
    return sorted(
        latest_by_hour.values(),
        key=lambda item: _as_utc(item.forecast_for),
        reverse=True,
    )


def _horizon_bucket_key(lead_hours: float) -> str:
    for key, _label, minimum, maximum in HORIZON_BUCKETS:
        above_minimum = (
            lead_hours >= minimum if minimum == 0 else lead_hours > minimum
        )
        if above_minimum and (maximum is None or lead_hours <= maximum):
            return key
    return HORIZON_BUCKETS[-1][0]


def _horizon_metrics(
    snapshots: List[ForecastAccuracySnapshot],
) -> List[Dict]:
    representatives = {}
    for snapshot in snapshots:
        lead_hours = _hours_between(
            snapshot.forecast_created_at,
            snapshot.forecast_for,
        )
        cloud_error = _field_error(snapshot, "cloud_cover_percent")
        if lead_hours is None or cloud_error is None:
            continue
        bucket_key = _horizon_bucket_key(lead_hours)
        representative_key = (
            bucket_key,
            _as_utc(snapshot.forecast_for),
        )
        current = representatives.get(representative_key)
        if current is None or lead_hours > current[0]:
            representatives[representative_key] = (
                lead_hours,
                cloud_error,
            )

    summaries = []
    for key, label, _minimum, _maximum in HORIZON_BUCKETS:
        errors = [
            cloud_error
            for (bucket_key, _forecast_for), (_lead, cloud_error)
            in representatives.items()
            if bucket_key == key
        ]
        sample_count = len(errors)
        summaries.append(
            {
                "key": key,
                "label": label,
                "matched_samples": sample_count,
                "minimum_samples": MINIMUM_HORIZON_SAMPLES,
                "average_cloud_error_percent": _round(
                    _average(errors),
                    0,
                ),
                "ready": sample_count >= MINIMUM_HORIZON_SAMPLES,
            }
        )
    return summaries


def _accuracy_metrics(snapshots: List[ForecastAccuracySnapshot]) -> Dict:
    cloud_errors = [
        value
        for snapshot in snapshots
        if (value := _field_error(snapshot, "cloud_cover_percent")) is not None
    ]
    cloud_biases = [
        value
        for snapshot in snapshots
        if (value := _field_bias(snapshot, "cloud_cover_percent")) is not None
    ]
    temperature_errors = [
        value
        for snapshot in snapshots
        if (value := _field_error(snapshot, "temperature_f")) is not None
    ]
    wind_errors = [
        value
        for snapshot in snapshots
        if (value := _field_error(snapshot, "wind_speed_mph")) is not None
    ]
    lead_hours = [
        value
        for snapshot in snapshots
        if (
            value := _hours_between(
                snapshot.forecast_created_at,
                snapshot.forecast_for,
            )
        )
        is not None
    ]
    return {
        "average_cloud_error_percent": _round(_average(cloud_errors), 0),
        "average_cloud_bias_percent": _round(_average(cloud_biases), 0),
        "average_temperature_error_f": _round(_average(temperature_errors), 1),
        "average_wind_error_mph": _round(_average(wind_errors), 1),
        "average_lead_hours": _round(_average(lead_hours), 1),
    }


def _recent_checks(snapshots: List[ForecastAccuracySnapshot]) -> List[Dict]:
    checks = []
    for snapshot in reversed(snapshots[:RECENT_HISTORY_LIMIT]):
        cloud_error = _field_error(snapshot, "cloud_cover_percent")
        lead_hours = _hours_between(
            snapshot.forecast_created_at,
            snapshot.forecast_for,
        )
        checks.append(
            {
                "forecast_for": _as_utc(snapshot.forecast_for).isoformat(),
                "observed_at": (
                    _as_utc(snapshot.observed_at).isoformat()
                    if snapshot.observed_at
                    else None
                ),
                "forecast_cloud_cover_percent": _round(
                    snapshot.forecast_cloud_cover_percent,
                    0,
                ),
                "observed_cloud_cover_percent": _round(
                    snapshot.observed_cloud_cover_percent,
                    0,
                ),
                "cloud_error_percent": _round(cloud_error, 0),
                "lead_hours": _round(lead_hours, 1),
            }
        )
    return checks


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
        "revision_count": 0,
        "minimum_samples": MINIMUM_CONFIDENCE_SAMPLES,
        "confidence": None,
        "metrics": {},
        "recent_checks": [],
        "has_history_chart": False,
        "horizon_buckets": [],
        "has_horizon_analysis": False,
    }
