import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional


SESSION_PATTERN = re.compile(
    r"^DWARF_RAW_TELE_(?P<target>.*?)_EXP_"
    r"(?P<exposure>[\d.]+)_GAIN_"
    r"(?P<gain>\d+)_"
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d+)$"
)

IGNORED_TOP_LEVEL_NAMES = {
    "CALI_FRAME",
    "DWARF_DARK",
    "RESTACKED",
    "STARTRAILS",
    "Solving_Failed",
}

STACK_PREFIXES = (
    "stacked-",
    "stacked.",
    "stacked_",
)

SUPPORTED_IMAGE_SUFFIXES = {
    ".fits",
    ".fit",
    ".fts",
    ".jpg",
    ".jpeg",
    ".png",
}


def normalize_target_name(value: str) -> str:
    cleaned = " ".join(value.split()).strip()

    if not cleaned:
        return "UNKNOWN"

    match = re.fullmatch(r"M\s*(\d+)", cleaned, re.IGNORECASE)
    if match:
        return f"M{match.group(1)}"

    match = re.fullmatch(r"NGC\s*(\d+)", cleaned, re.IGNORECASE)
    if match:
        return f"NGC{match.group(1)}"

    match = re.fullmatch(r"IC\s*(\d+)", cleaned, re.IGNORECASE)
    if match:
        return f"IC{match.group(1)}"

    return cleaned.upper()


def parse_session_folder(folder: Path) -> Optional[Dict]:
    match = SESSION_PATTERN.match(folder.name)

    if not match:
        return None

    target_name = normalize_target_name(match.group("target"))

    return {
        "folder_name": folder.name,
        "folder_path": str(folder),
        "target": target_name,
        "exposure_seconds": float(match.group("exposure")),
        "gain": int(match.group("gain")),
        "session_timestamp": match.group("timestamp"),
    }


def classify_file(path: Path) -> str:
    name_lower = path.name.lower()
    suffix = path.suffix.lower()

    if path.parent.name == "Thumbnail":
        return "thumbnail"

    if name_lower.startswith("failed_"):
        return "failed"

    if name_lower == "shotsinfo.json":
        return "session_metadata"

    if name_lower in {
        "stacked.jpg",
        "stacked_thumbnail.jpg",
    }:
        return "stacked_preview"

    if name_lower.startswith(STACK_PREFIXES):
        if suffix in {".fits", ".fit", ".fts"}:
            return "stacked_fits"

        if suffix == ".png":
            return "stacked_png"

        if suffix in {".jpg", ".jpeg"}:
            return "stacked_jpg"

    if suffix in {".fits", ".fit", ".fts"}:
        return "raw_fits"

    if suffix in {".jpg", ".jpeg"}:
        return "jpg"

    if suffix == ".png":
        return "png"

    return "other"


def scan_session(folder: Path) -> Optional[Dict]:
    session = parse_session_folder(folder)

    if session is None:
        return None

    counts = Counter()
    files: List[Dict] = []

    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue

        classification = classify_file(path)
        counts[classification] += 1

        if classification != "other":
            files.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "classification": classification,
                    "size_bytes": path.stat().st_size,
                }
            )

    session["counts"] = dict(sorted(counts.items()))
    session["total_supported_files"] = len(files)
    session["files"] = files

    session["import_candidate"] = (
        counts["stacked_fits"] > 0
        or counts["raw_fits"] > 0
    )

    return session


def scan_calibration_library(astronomy_root: Path) -> Dict:
    calibration_root = astronomy_root / "CALI_FRAME"
    dwarf_dark_root = astronomy_root / "DWARF_DARK"

    result = {
        "cali_frame_exists": calibration_root.exists(),
        "dwarf_dark_exists": dwarf_dark_root.exists(),
        "bias_files": 0,
        "flat_files": 0,
        "master_dark_files": 0,
        "raw_dark_files": 0,
    }

    if calibration_root.exists():
        result["bias_files"] = len(
            list((calibration_root / "bias").rglob("*.fits"))
        )
        result["flat_files"] = len(
            list((calibration_root / "flat").rglob("*.fits"))
        )
        result["master_dark_files"] = len(
            list((calibration_root / "dark").rglob("*.fits"))
        )

    if dwarf_dark_root.exists():
        result["raw_dark_files"] = len(
            list(dwarf_dark_root.rglob("*.fits"))
        )

    return result


def build_inventory(archive_root: Path) -> Dict:
    astronomy_root = archive_root / "Astronomy"

    if not astronomy_root.exists():
        raise FileNotFoundError(
            f"Astronomy folder was not found at '{astronomy_root}'."
        )

    sessions = []

    for folder in sorted(astronomy_root.iterdir()):
        if not folder.is_dir():
            continue

        if folder.name in IGNORED_TOP_LEVEL_NAMES:
            continue

        session = scan_session(folder)

        if session is not None:
            sessions.append(session)

    targets = Counter(
        session["target"]
        for session in sessions
    )

    totals = Counter()

    for session in sessions:
        totals.update(session["counts"])

    return {
        "archive_root": str(archive_root),
        "astronomy_root": str(astronomy_root),
        "session_count": len(sessions),
        "target_count": len(targets),
        "targets": dict(sorted(targets.items())),
        "file_totals": dict(sorted(totals.items())),
        "calibration": scan_calibration_library(
            astronomy_root
        ),
        "sessions": sessions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Scan a DWARF archive and create a dry-run "
            "inventory without moving files."
        )
    )

    parser.add_argument(
        "archive_root",
        type=Path,
        help=(
            "Root folder containing Astronomy, Burst, "
            "Normal_Photos, and Videos."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path.home()
        / "Desktop"
        / "dwarf_inventory.json",
        help="Path for the generated JSON inventory.",
    )

    args = parser.parse_args()

    archive_root = args.archive_root.expanduser().resolve()
    output_path = args.output.expanduser().resolve()

    inventory = build_inventory(archive_root)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            inventory,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("DWARF archive scan complete.")
    print(f"Sessions found: {inventory['session_count']}")
    print(f"Targets found: {inventory['target_count']}")
    print(f"Inventory saved to: {output_path}")

    print("\nTargets:")
    for target, count in inventory["targets"].items():
        print(f"  {target}: {count} session(s)")

    print("\nCalibration:")
    for key, value in inventory["calibration"].items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()