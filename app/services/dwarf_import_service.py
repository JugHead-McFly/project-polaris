import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.core.storage import get_preview_path
from app.models import Capture
from app.models import ObservingSession
from app.services.capture_service import create_capture_from_parsed_fits
from parser.fits_parser import parse_fits


SESSION_PATTERN = re.compile(
    r"^DWARF_RAW_TELE_(?P<target>.*?)_EXP_"
    r"(?P<exposure>[\d.]+)_GAIN_"
    r"(?P<gain>\d+)_"
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}-"
    r"\d{2}-\d{2}-\d{2}-\d+)$"
)


def normalize_target_name(value: str) -> str:
    cleaned = " ".join(value.split()).strip()

    if not cleaned:
        return "UNKNOWN"

    match = re.fullmatch(
        r"M\s*(\d+)",
        cleaned,
        re.IGNORECASE,
    )

    if match:
        return f"M{match.group(1)}"

    match = re.fullmatch(
        r"NGC\s*(\d+)",
        cleaned,
        re.IGNORECASE,
    )

    if match:
        return f"NGC{match.group(1)}"

    match = re.fullmatch(
        r"IC\s*(\d+)",
        cleaned,
        re.IGNORECASE,
    )

    if match:
        return f"IC{match.group(1)}"

    return cleaned.upper()


def parse_session_folder_name(
    folder_name: str,
) -> Dict:
    match = SESSION_PATTERN.match(folder_name)

    if match is None:
        raise ValueError(
            "The folder name does not match the expected "
            "DWARF session format:\n"
            f"{folder_name}"
        )

    raw_timestamp = match.group("timestamp")

    timestamp_parts = raw_timestamp.split("-")

    session_datetime = datetime.strptime(
        "-".join(timestamp_parts[:6]),
        "%Y-%m-%d-%H-%M-%S",
    )

    milliseconds = timestamp_parts[6]

    session_id = (
        f"SES-{session_datetime.strftime('%Y%m%d-%H%M%S')}-"
        f"{milliseconds}"
    )

    return {
        "session_id": session_id,
        "target": normalize_target_name(
            match.group("target")
        ),
        "exposure_seconds": float(
            match.group("exposure")
        ),
        "gain": float(match.group("gain")),
        "session_datetime": session_datetime,
        "session_date": session_datetime.strftime(
            "%Y-%m-%d"
        ),
    }


def find_stacked_fits(
    session_folder: Path,
) -> Path:
    candidates = []

    for suffix in ("*.fits", "*.fit", "*.fts"):
        candidates.extend(
            session_folder.glob(f"stacked-{suffix}")
        )

    if not candidates:
        for path in session_folder.iterdir():
            if not path.is_file():
                continue

            if not path.name.lower().startswith(
                "stacked-"
            ):
                continue

            if path.suffix.lower() in {
                ".fits",
                ".fit",
                ".fts",
            }:
                candidates.append(path)

    candidates = sorted(set(candidates))

    if not candidates:
        raise FileNotFoundError(
            "No stacked FITS file was found in:\n"
            f"{session_folder}"
        )

    if len(candidates) > 1:
        raise RuntimeError(
            "More than one stacked FITS file was found:\n"
            + "\n".join(str(path) for path in candidates)
        )

    return candidates[0]


def find_optional_file(
    session_folder: Path,
    filename: str,
) -> Optional[Path]:
    path = session_folder / filename

    if path.exists() and path.is_file():
        return path

    return None


def get_or_create_session(
    db: Session,
    session_info: Dict,
    source_folder: Path,
) -> tuple:
    session = (
        db.query(ObservingSession)
        .filter(
            ObservingSession.session_id
            == session_info["session_id"]
        )
        .first()
    )

    if session is not None:
        return session, False

    session = ObservingSession(
        session_id=session_info["session_id"],
        date=session_info["session_date"],
        location="",
        observatory="DWARF 3",
        moon_phase="",
        weather_summary="",
        notes=(
            "Imported from DWARF session folder: "
            f"{source_folder.name}"
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session, True


def find_existing_capture(
    db: Session,
    stacked_fits: Path,
) -> Optional[Capture]:
    return (
        db.query(Capture)
        .filter(Capture.filename == stacked_fits.name)
        .first()
    )


def copy_preview(
    source_path: Path,
    object_name: str,
    polaris_id: str,
) -> Path:
    destination = get_preview_path(
        object_name=object_name,
        polaris_id=polaris_id,
        suffix=source_path.suffix.lower(),
    )

    shutil.copy2(
        source_path,
        destination,
    )

    return destination


def import_dwarf_session(
    db: Session,
    session_folder: Path,
) -> Dict:
    session_folder = (
        session_folder.expanduser().resolve()
    )

    if not session_folder.exists():
        raise FileNotFoundError(
            f"Session folder was not found:\n"
            f"{session_folder}"
        )

    if not session_folder.is_dir():
        raise NotADirectoryError(
            f"The supplied path is not a directory:\n"
            f"{session_folder}"
        )

    session_info = parse_session_folder_name(
        session_folder.name
    )

    stacked_fits = find_stacked_fits(
        session_folder
    )

    existing_capture = find_existing_capture(
        db=db,
        stacked_fits=stacked_fits,
    )

    if existing_capture is not None:
        observing_session = None

        if existing_capture.session_id is not None:
            observing_session = (
                db.query(ObservingSession)
                .filter(
                    ObservingSession.id
                    == existing_capture.session_id
                )
                .first()
            )

        return {
            "status": "skipped",
            "reason": "Capture already imported",
            "session_database_id": existing_capture.session_id,
            "session_id": (
                observing_session.session_id
                if observing_session is not None
                else None
            ),
            "polaris_id": existing_capture.polaris_id,
            "object_name": existing_capture.object_name,
            "filename": existing_capture.filename,
            "asset_path": existing_capture.asset_path,
        }

    observing_session, session_created = (
        get_or_create_session(
            db=db,
            session_info=session_info,
            source_folder=session_folder,
        )
    )

    parsed = parse_fits(
        str(stacked_fits)
    )

    parsed.setdefault(
        "target",
        {},
    )

    parsed["target"]["id"] = session_info[
        "target"
    ]

    parsed.setdefault(
        "capture_settings",
        {},
    )

    parsed["capture_settings"]["gain"] = (
        session_info["gain"]
    )

    parsed["capture_settings"][
        "integration_seconds"
    ] = session_info["exposure_seconds"]

    capture = create_capture_from_parsed_fits(
        db=db,
        parsed=parsed,
        filename=stacked_fits.name,
        source_path=str(stacked_fits),
    )

    # Force the capture to the session created or reused
    # by this importer instead of relying on "latest session."
    capture.session_id = observing_session.id
    capture.object_name = session_info["target"]
    capture.gain = session_info["gain"]
    capture.exposure_seconds = int(
        session_info["exposure_seconds"]
    )
    capture.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(capture)

    copied_previews = []

    stacked_png = None

    for path in session_folder.iterdir():
        if (
            path.is_file()
            and path.name.lower().startswith(
                "stacked-"
            )
            and path.suffix.lower() == ".png"
        ):
            stacked_png = path
            break

    if stacked_png is not None:
        destination = copy_preview(
            source_path=stacked_png,
            object_name=capture.object_name,
            polaris_id=capture.polaris_id,
        )

        copied_previews.append(
            str(destination)
        )

    stacked_jpg = find_optional_file(
        session_folder,
        "stacked.jpg",
    )

    if stacked_jpg is not None:
        destination = copy_preview(
            source_path=stacked_jpg,
            object_name=capture.object_name,
            polaris_id=capture.polaris_id,
        )

        copied_previews.append(
            str(destination)
        )

    return {
        "status": "imported",
        "session_created": session_created,
        "session_database_id": observing_session.id,
        "session_id": observing_session.session_id,
        "polaris_id": capture.polaris_id,
        "object_name": capture.object_name,
        "source_folder": str(session_folder),
        "source_fits": str(stacked_fits),
        "asset_path": capture.asset_path,
        "preview_paths": copied_previews,
        "gain": capture.gain,
        "exposure_seconds": (
            capture.exposure_seconds
        ),
    }