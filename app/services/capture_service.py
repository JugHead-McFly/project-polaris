from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Capture
from app.models import ObservingSession


def _to_float(value):
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _next_polaris_id(db: Session) -> str:
    year = datetime.utcnow().year

    count = (
        db.query(Capture)
        .filter(Capture.polaris_id.like(f"POL-{year}-%"))
        .count()
    )

    next_number = count + 1

    return f"POL-{year}-{next_number:06d}"


def create_capture_from_parsed_fits(
    db: Session,
    parsed: dict,
    filename: str,
    asset_path: str = "",
) -> Capture:
    target = parsed.get("target", {})
    observation = parsed.get("observation", {})
    settings = parsed.get("capture_settings", {})
    equipment = parsed.get("equipment", {})
    latest_session = (
    db.query(ObservingSession)
    .order_by(ObservingSession.id.desc())
    .first()
)

    capture = Capture(
        polaris_id=_next_polaris_id(db),
        session_id=latest_session.id if latest_session else None,
        object_name=target.get("id", ""),
        filename=filename,
        asset_path=asset_path,
        observation_utc=observation.get("observation_utc", ""),
        gain=_to_float(settings.get("gain")),
        ra=_to_float(observation.get("ra")),
        dec=_to_float(observation.get("dec")),
        telescope=equipment.get("telescope", ""),
        firmware=equipment.get("firmware", ""),
        status="Raw",
        exposure_seconds=_to_float(settings.get("integration_seconds")),
    )

    db.add(capture)
    db.commit()
    db.refresh(capture)

    return capture