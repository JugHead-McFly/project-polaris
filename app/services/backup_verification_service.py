import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from app.services.capture_sync_service import (
    FITS_SUFFIXES,
    POLARIS_ID_PATTERN,
)


DEFAULT_DATABASE_NAME = "polaris.db"
DEFAULT_LIBRARY_NAME = "ProjectPolaris"


def _normalized(value: Optional[str]) -> str:
    return (value or "").strip().upper()


def _backup_paths(
    backup_root: Path,
    database_name: str,
    library_name: str,
) -> Dict[str, Path]:
    resolved_root = backup_root.expanduser().resolve()
    database_path = Path(database_name).expanduser()
    library_root = Path(library_name).expanduser()

    if not database_path.is_absolute():
        database_path = resolved_root / database_path
    if not library_root.is_absolute():
        library_root = resolved_root / library_root

    return {
        "backup_root": resolved_root,
        "database_path": database_path.resolve(),
        "library_root": library_root.resolve(),
    }


def _database_capture_rows(database_path: Path) -> Dict:
    connection = None
    try:
        database_uri = f"{database_path.as_uri()}?mode=ro"
        connection = sqlite3.connect(database_uri, uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        integrity_rows = [
            row[0]
            for row in connection.execute("PRAGMA quick_check")
        ]
        rows = [
            dict(row)
            for row in connection.execute(
                "SELECT polaris_id, object_name, filename, asset_path "
                "FROM captures ORDER BY polaris_id"
            )
        ]
    except sqlite3.Error as error:
        return {
            "quick_check": [],
            "quick_check_ok": False,
            "captures": [],
            "error": str(error),
        }
    finally:
        if connection is not None:
            connection.close()

    return {
        "quick_check": integrity_rows,
        "quick_check_ok": integrity_rows == ["ok"],
        "captures": rows,
        "error": None,
    }


def _library_entries(library_root: Path) -> Dict:
    targets_root = library_root / "targets"
    if not targets_root.is_dir():
        return {
            "entries": [],
            "error": (
                "Capture library targets folder was not found: "
                f"{targets_root}"
            ),
        }

    entries = []
    for path in sorted(targets_root.glob("*/fits/*")):
        if not path.is_file() or path.suffix.lower() not in FITS_SUFFIXES:
            continue

        entries.append(
            {
                "polaris_id": path.stem.upper(),
                "object_name": path.parent.parent.name.strip().upper(),
                "filename": path.name,
                "path": str(path.resolve()),
            }
        )

    return {"entries": entries, "error": None}


def _asset_path_matches_logical_location(
    asset_path: Optional[str],
    object_name: str,
    filename: str,
) -> bool:
    if not asset_path:
        return False

    parts = [_normalized(part) for part in Path(asset_path).parts]
    expected = [
        "TARGETS",
        _normalized(object_name),
        "FITS",
        _normalized(filename),
    ]
    return len(parts) >= len(expected) and parts[-4:] == expected


def _compare_pair(database_captures: List[Dict], files: List[Dict]) -> Dict:
    conflicts = []
    database_by_id: Dict[str, List[Dict]] = {}
    files_by_id: Dict[str, List[Dict]] = {}

    for capture in database_captures:
        polaris_id = _normalized(capture.get("polaris_id"))
        if POLARIS_ID_PATTERN.fullmatch(polaris_id) is None:
            conflicts.append(
                {
                    "type": "invalid_database_id",
                    "polaris_id": capture.get("polaris_id"),
                }
            )
            continue
        database_by_id.setdefault(polaris_id, []).append(capture)

    for entry in files:
        if POLARIS_ID_PATTERN.fullmatch(entry["polaris_id"]) is None:
            conflicts.append(
                {
                    "type": "invalid_library_id",
                    **entry,
                }
            )
            continue
        files_by_id.setdefault(entry["polaris_id"], []).append(entry)

    unique_database = {}
    for polaris_id, captures in database_by_id.items():
        if len(captures) > 1:
            conflicts.append(
                {
                    "type": "duplicate_database_id",
                    "polaris_id": polaris_id,
                    "count": len(captures),
                }
            )
            continue
        unique_database[polaris_id] = captures[0]

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
        capture = unique_database.get(polaris_id)
        if capture is None:
            orphan_files.append(entry)
            continue

        capture_target = _normalized(capture.get("object_name"))
        entry_conflicts = []
        if capture_target != entry["object_name"]:
            entry_conflicts.append(
                {
                    "type": "target_mismatch",
                    "polaris_id": polaris_id,
                    "database_target": capture.get("object_name"),
                    "library_target": entry["object_name"],
                }
            )
        elif not _asset_path_matches_logical_location(
            capture.get("asset_path"),
            entry["object_name"],
            entry["filename"],
        ):
            entry_conflicts.append(
                {
                    "type": "asset_path_mismatch",
                    "polaris_id": polaris_id,
                    "database_path": capture.get("asset_path"),
                    "expected_suffix": str(
                        Path("targets")
                        / entry["object_name"]
                        / "fits"
                        / entry["filename"]
                    ),
                }
            )

        if entry_conflicts:
            conflicts.extend(entry_conflicts)
        else:
            matched.append(entry)

    missing_database_assets = [
        {
            "polaris_id": polaris_id,
            "object_name": capture.get("object_name"),
            "filename": capture.get("filename"),
            "database_path": capture.get("asset_path"),
        }
        for polaris_id, capture in sorted(unique_database.items())
        if polaris_id not in unique_files
    ]

    return {
        "matched": matched,
        "orphan_files": orphan_files,
        "missing_database_assets": missing_database_assets,
        "conflicts": conflicts,
    }


def verify_backup_pair(
    backup_root: Path,
    database_name: str = DEFAULT_DATABASE_NAME,
    library_name: str = DEFAULT_LIBRARY_NAME,
) -> Dict:
    paths = _backup_paths(
        backup_root=backup_root,
        database_name=database_name,
        library_name=library_name,
    )
    database_path = paths["database_path"]
    library_root = paths["library_root"]
    errors = []

    database_present = database_path.is_file()
    library_present = library_root.is_dir()
    if not database_present:
        errors.append(f"Backup database was not found: {database_path}")
    if not library_present:
        errors.append(f"Backup capture library was not found: {library_root}")

    database_report = {
        "quick_check": [],
        "quick_check_ok": False,
        "captures": [],
        "error": None,
    }
    if database_present:
        database_report = _database_capture_rows(database_path)
        if database_report["error"]:
            errors.append(
                "Backup database could not be verified: "
                f"{database_report['error']}"
            )
        elif not database_report["quick_check_ok"]:
            errors.append("Backup database failed SQLite quick_check.")

    library_report = {"entries": [], "error": None}
    if library_present:
        library_report = _library_entries(library_root)
        if library_report["error"]:
            errors.append(library_report["error"])

    comparison = _compare_pair(
        database_captures=database_report["captures"],
        files=library_report["entries"],
    )
    matched_count = len(comparison["matched"])
    orphan_count = len(comparison["orphan_files"])
    missing_asset_count = len(comparison["missing_database_assets"])
    conflict_count = len(comparison["conflicts"])
    valid = (
        database_present
        and library_present
        and database_report["quick_check_ok"]
        and not errors
        and orphan_count == 0
        and missing_asset_count == 0
        and conflict_count == 0
    )

    return {
        "mode": "read-only",
        "backup_root": str(paths["backup_root"]),
        "database_path": str(database_path),
        "library_root": str(library_root),
        "database_present": database_present,
        "library_present": library_present,
        "database_quick_check": database_report["quick_check"],
        "database_quick_check_ok": database_report["quick_check_ok"],
        "database_capture_count": len(database_report["captures"]),
        "library_fits_count": len(library_report["entries"]),
        "matched_count": matched_count,
        "orphan_count": orphan_count,
        "missing_asset_count": missing_asset_count,
        "conflict_count": conflict_count,
        "valid": valid,
        "errors": errors,
        "orphan_files": comparison["orphan_files"],
        "missing_database_assets": comparison["missing_database_assets"],
        "conflicts": comparison["conflicts"],
    }
