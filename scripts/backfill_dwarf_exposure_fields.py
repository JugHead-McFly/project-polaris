import argparse
import re
import sys
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.database.database import SessionLocal
from app.models import Capture


SESSION_PATTERN = re.compile(
    r"^DWARF_RAW_TELE_(?P<target>.*?)_EXP_"
    r"(?P<exposure>[\d.]+)_GAIN_"
    r"(?P<gain>\d+)_"
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}-"
    r"\d{2}-\d{2}-\d{2}-\d+)$"
)


def find_stacked_fits(
    session_folder: Path,
) -> Optional[Path]:
    candidates = sorted(
        path
        for path in session_folder.iterdir()
        if path.is_file()
        and path.name.lower().startswith("stacked-")
        and path.suffix.lower() in {
            ".fits",
            ".fit",
            ".fts",
        }
    )

    if len(candidates) == 1:
        return candidates[0]

    return None


def count_accepted_subframes(
    session_folder: Path,
) -> int:
    return sum(
        1
        for path in session_folder.iterdir()
        if path.is_file()
        and path.suffix.lower() in {
            ".fits",
            ".fit",
            ".fts",
        }
        and not path.name.lower().startswith("stacked-")
        and not path.name.lower().startswith("failed_")
    )


def detect_filter_name(
    stacked_fits: Path,
) -> Optional[str]:
    filename = stacked_fits.name.lower()

    if "duo-band" in filename:
        return "Duo-Band"

    if "_astro_" in filename:
        return "Astro"

    if "uv-ir" in filename or "uv_ir" in filename:
        return "UV/IR Cut"

    return None


def backfill_archive(
    archive_root: Path,
) -> dict:
    astronomy_root = archive_root / "Astronomy"

    if not astronomy_root.exists():
        raise FileNotFoundError(
            "Astronomy folder was not found:\n"
            f"{astronomy_root}"
        )

    db = SessionLocal()

    updated = []
    skipped = []
    failed = []

    try:
        session_folders = sorted(
            path
            for path in astronomy_root.iterdir()
            if path.is_dir()
            and path.name.startswith(
                "DWARF_RAW_TELE_"
            )
        )

        for session_folder in session_folders:
            match = SESSION_PATTERN.match(
                session_folder.name
            )

            if match is None:
                skipped.append(
                    {
                        "folder": session_folder.name,
                        "reason": (
                            "Folder has no identifiable target"
                        ),
                    }
                )
                continue

            stacked_fits = find_stacked_fits(
                session_folder
            )

            if stacked_fits is None:
                skipped.append(
                    {
                        "folder": session_folder.name,
                        "reason": (
                            "Exactly one stacked FITS "
                            "was not found"
                        ),
                    }
                )
                continue

            capture = (
                db.query(Capture)
                .filter(
                    Capture.filename
                    == stacked_fits.name
                )
                .first()
            )

            if capture is None:
                skipped.append(
                    {
                        "folder": session_folder.name,
                        "reason": (
                            "Matching capture was not found "
                            "in the database"
                        ),
                    }
                )
                continue

            try:
                sub_exposure_seconds = int(
                    round(
                        float(
                            match.group("exposure")
                        )
                    )
                )

                subframe_count = (
                    count_accepted_subframes(
                        session_folder
                    )
                )

                total_integration_seconds = (
                    sub_exposure_seconds
                    * subframe_count
                )

                filter_name = detect_filter_name(
                    stacked_fits
                )

                capture.sub_exposure_seconds = (
                    sub_exposure_seconds
                )
                capture.subframe_count = (
                    subframe_count
                )
                capture.total_integration_seconds = (
                    total_integration_seconds
                )
                capture.filter_name = filter_name

                db.add(capture)
                db.commit()
                db.refresh(capture)

                updated.append(
                    {
                        "polaris_id": (
                            capture.polaris_id
                        ),
                        "object_name": (
                            capture.object_name
                        ),
                        "sub_exposure_seconds": (
                            capture
                            .sub_exposure_seconds
                        ),
                        "subframe_count": (
                            capture.subframe_count
                        ),
                        "total_integration_seconds": (
                            capture
                            .total_integration_seconds
                        ),
                        "filter_name": (
                            capture.filter_name
                        ),
                    }
                )

                print(
                    f"UPDATED {capture.polaris_id}: "
                    f"{capture.object_name}, "
                    f"{subframe_count} × "
                    f"{sub_exposure_seconds}s = "
                    f"{total_integration_seconds}s, "
                    f"filter={filter_name}"
                )

            except Exception as exc:
                db.rollback()

                failed.append(
                    {
                        "folder": session_folder.name,
                        "error_type": (
                            type(exc).__name__
                        ),
                        "error": str(exc),
                    }
                )

        return {
            "updated_count": len(updated),
            "skipped_count": len(skipped),
            "failed_count": len(failed),
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
        }

    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill DWARF sub-exposure, "
            "subframe count, total integration, "
            "and filter fields."
        )
    )

    parser.add_argument(
        "archive_root",
        type=Path,
        help=(
            "DWARF archive root containing "
            "the Astronomy folder."
        ),
    )

    args = parser.parse_args()

    archive_root = (
        args.archive_root
        .expanduser()
        .resolve()
    )

    report = backfill_archive(
        archive_root
    )

    print("\nDWARF exposure backfill complete.")
    print(
        f"Updated: {report['updated_count']}"
    )
    print(
        f"Skipped: {report['skipped_count']}"
    )
    print(
        f"Failed: {report['failed_count']}"
    )

    if report["failed_count"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()