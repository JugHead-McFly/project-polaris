from datetime import datetime
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Capture
from app.models import ObservingSession
from app.core.storage import get_light_capture_path


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

    return f"POL-{year}-{count + 1:06d}"


def create_capture_from_parsed_fits(
    db: Session,
    parsed: dict,
    filename: str,
    source_path: str,
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

    object_name = target.get("id") or "UNKNOWN"

    polaris_id = _next_polaris_id(db)

    destination = get_light_capture_path(
        object_name=object_name,
        polaris_id=polaris_id,
        suffix=".fits",
    )

    shutil.copy2(
        Path(source_path),
        destination,
    )

    capture = Capture(
        polaris_id=polaris_id,
        session_id=latest_session.id if latest_session else None,
        object_name=object_name,
        filename=filename,
        asset_path=str(destination),
        observation_utc=observation.get("observation_utc", ""),
        gain=_to_float(settings.get("gain")),
        exposure_seconds=_to_float(settings.get("integration_seconds")),
        ra=_to_float(observation.get("ra")),
        dec=_to_float(observation.get("dec")),
        telescope=equipment.get("telescope", ""),
        firmware=equipment.get("firmware", ""),
        status="Raw",
    )

    db.add(capture)
    db.commit()
    db.refresh(capture)

    return capture