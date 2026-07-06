from sqlalchemy.orm import Session

from app.models import Capture


def _to_float(value):
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def create_capture_from_parsed_fits(
    db: Session,
    parsed: dict,
    filename: str,
) -> Capture:
    target = parsed.get("target", {})
    observation = parsed.get("observation", {})
    settings = parsed.get("capture_settings", {})
    equipment = parsed.get("equipment", {})

    capture = Capture(
        object_name=target.get("id", ""),
        filename=filename,
        observation_utc=observation.get("observation_utc", ""),
        gain=_to_float(settings.get("gain")),
        ra=_to_float(observation.get("ra")),
        dec=_to_float(observation.get("dec")),
        telescope=equipment.get("telescope", ""),
        firmware=equipment.get("firmware", ""),
    )

    db.add(capture)
    db.commit()
    db.refresh(capture)

    return capture