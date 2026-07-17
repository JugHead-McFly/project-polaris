import re
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.storage import POLARIS_ROOT
from app.models import Capture
from parser.fits_parser import parse_fits


POLARIS_ID_PATTERN = re.compile(r"^POL-\d{4}-\d{6}$")
FITS_SUFFIXES = {".fits", ".fit", ".fts"}


def _to_float(value) -> Optional[float]:
    if value in ("", None):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> Optional[int]:
    number = _to_float(value)
    return int(number) if number is not None else None


def _library_files(library_root: Path) -> List[Dict]:
    targets_root = library_root / "targets"

    if not targets_root.exists():
        raise FileNotFoundError(
            f"Capture library targets folder was not found: {targets_root}"
        )

    entries = []
    for path in sorted(targets_root.glob("*/fits/*")):
        if not path.is_file() or path.suffix.lower() not in FITS_SUFFIXES:
            continue

        entries.append(
            {
                "polaris_id": path.stem.upper(),
                "object_name": path.parent.parent.name.strip().upper(),
                "path": str(path.resolve()),
            }
        )

    return entries


def inspect_capture_library(
    db: Session,
    library_root: Path = POLARIS_ROOT,
) -> Dict:
    resolved_root = library_root.expanduser().resolve()
    file_entries = _library_files(resolved_root)
    database_captures = db.query(Capture).all()
    database_by_id = {
        capture.polaris_id: capture
        for capture in database_captures
        if capture.polaris_id
    }
    files_by_id: Dict[str, List[Dict]] = {}
    conflicts = []

    for entry in file_entries:
        if POLARIS_ID_PATTERN.fullmatch(entry["polaris_id"]) is None:
            conflicts.append(
                {
                    "type": "invalid_polaris_id",
                    **entry,
                }
            )
            continue

        files_by_id.setdefault(entry["polaris_id"], []).append(entry)

    unique_files = {}
    for polaris_id, entries in files_by_id.items():
        if len(entries) > 1:
            conflicts.append(
                {
                    "type": "duplicate_library_id",
                    "polaris_id": polaris_id,
                    "paths": [entry["path"] for entry in entries],
                }
            )
            continue

        unique_files[polaris_id] = entries[0]

    matched = []
    orphan_files = []

    for polaris_id, entry in sorted(unique_files.items()):
        capture = database_by_id.get(polaris_id)

        if capture is None:
            orphan_files.append(entry)
            continue

        if (capture.object_name or "").strip().upper() != entry["object_name"]:
            conflicts.append(
                {
                    "type": "target_mismatch",
                    "polaris_id": polaris_id,
                    "library_target": entry["object_name"],
                    "database_target": capture.object_name,
                    "path": entry["path"],
                }
            )
            continue

        if Path(capture.asset_path or "").expanduser().resolve() != Path(
            entry["path"]
        ):
            conflicts.append(
                {
                    "type": "asset_path_mismatch",
                    "polaris_id": polaris_id,
                    "library_path": entry["path"],
                    "database_path": capture.asset_path,
                }
            )
            continue

        matched.append(entry)

    missing_database_assets = [
        {
            "polaris_id": polaris_id,
            "object_name": capture.object_name,
            "database_path": capture.asset_path,
        }
        for polaris_id, capture in sorted(database_by_id.items())
        if polaris_id not in unique_files
    ]

    return {
        "library_root": str(resolved_root),
        "database_capture_count": len(database_captures),
        "library_fits_count": len(file_entries),
        "matched_count": len(matched),
        "orphan_count": len(orphan_files),
        "missing_asset_count": len(missing_database_assets),
        "conflict_count": len(conflicts),
        "clean": (
            not orphan_files
            and not missing_database_assets
            and not conflicts
        ),
        "matched": matched,
        "orphan_files": orphan_files,
        "missing_database_assets": missing_database_assets,
        "conflicts": conflicts,
    }


def _capture_from_library_file(entry: Dict) -> Capture:
    path = Path(entry["path"])
    parsed = parse_fits(str(path))
    observation = parsed.get("observation", {})
    settings = parsed.get("capture_settings", {})
    equipment = parsed.get("equipment", {})
    total_integration_seconds = _to_int(
        settings.get("integration_seconds")
    )

    return Capture(
        polaris_id=entry["polaris_id"],
        session_id=None,
        object_name=entry["object_name"],
        filename=path.name,
        asset_path=str(path),
        observation_utc=observation.get("observation_utc", ""),
        gain=_to_float(settings.get("gain")),
        ra=_to_float(observation.get("ra")),
        dec=_to_float(observation.get("dec")),
        telescope=equipment.get("telescope", ""),
        firmware=equipment.get("firmware", ""),
        status="Raw",
        exposure_seconds=None,
        sub_exposure_seconds=None,
        subframe_count=None,
        total_integration_seconds=total_integration_seconds,
        filter_name=settings.get("filter") or None,
    )


def synchronize_capture_library(
    db: Session,
    library_root: Path = POLARIS_ROOT,
    apply: bool = False,
) -> Dict:
    report = inspect_capture_library(
        db=db,
        library_root=library_root,
    )
    report["mode"] = "apply" if apply else "dry-run"
    report["registered_count"] = 0
    report["registered"] = []

    if not apply:
        return report

    if report["conflicts"]:
        report["apply_blocked"] = True
        report["apply_blocked_reason"] = (
            "Resolve library conflicts before registering orphan captures."
        )
        return report

    if not report["orphan_files"]:
        report["clean_after_apply"] = report["clean"]
        return report

    captures = [
        _capture_from_library_file(entry)
        for entry in report["orphan_files"]
    ]

    try:
        db.add_all(captures)
        db.commit()
    except Exception:
        db.rollback()
        raise

    report["registered"] = [
        {
            "polaris_id": capture.polaris_id,
            "object_name": capture.object_name,
            "asset_path": capture.asset_path,
        }
        for capture in captures
    ]
    report["registered_count"] = len(captures)
    post_apply = inspect_capture_library(
        db=db,
        library_root=library_root,
    )
    report["clean_after_apply"] = post_apply["clean"]
    report["remaining_orphan_count"] = post_apply["orphan_count"]
    report["remaining_conflict_count"] = post_apply["conflict_count"]

    return report
