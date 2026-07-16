import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from app.database.database import SessionLocal
from app.models import Capture
from app.services.capture_analysis_service import (
    analyze_and_save_capture,
)
from app.services.dwarf_import_service import (
    import_dwarf_session,
)


SESSION_PREFIX = "DWARF_RAW_TELE_"


def find_session_folders(
    archive_root: Path,
) -> List[Path]:
    astronomy_root = archive_root / "Astronomy"

    if not astronomy_root.exists():
        raise FileNotFoundError(
            "Astronomy folder was not found at:\n"
            f"{astronomy_root}"
        )

    if not astronomy_root.is_dir():
        raise NotADirectoryError(
            "Astronomy path is not a directory:\n"
            f"{astronomy_root}"
        )

    session_folders = [
        path
        for path in astronomy_root.iterdir()
        if path.is_dir()
        and path.name.startswith(SESSION_PREFIX)
    ]

    return sorted(
        session_folders,
        key=lambda path: path.name,
    )


def analyze_imported_capture(
    db,
    import_result: Dict,
) -> Dict:
    polaris_id = import_result.get("polaris_id")

    if not polaris_id:
        raise RuntimeError(
            "Imported result did not contain a Polaris ID."
        )

    capture = (
        db.query(Capture)
        .filter(
            Capture.polaris_id == polaris_id
        )
        .first()
    )

    if capture is None:
        raise RuntimeError(
            "The imported capture could not be found "
            f"in the database: {polaris_id}"
        )

    return analyze_and_save_capture(
        db=db,
        capture=capture,
    )


def import_one_session(
    db,
    session_folder: Path,
) -> Dict:
    result = import_dwarf_session(
        db=db,
        session_folder=session_folder,
    )

    if result["status"] == "imported":
        analysis_result = analyze_imported_capture(
            db=db,
            import_result=result,
        )

        result["analysis"] = analysis_result

    return result


def import_archive(
    archive_root: Path,
) -> Dict:
    session_folders = find_session_folders(
        archive_root
    )

    imported = []
    skipped = []
    failed = []

    for index, session_folder in enumerate(
        session_folders,
        start=1,
    ):
        print(
            f"\n[{index}/{len(session_folders)}] "
            f"{session_folder.name}"
        )

        db = SessionLocal()

        try:
            result = import_one_session(
                db=db,
                session_folder=session_folder,
            )

            if result["status"] == "imported":
                imported.append(result)

                analysis = result.get(
                    "analysis",
                    {},
                )

                print(
                    "  IMPORTED: "
                    f"{result['object_name']} "
                    f"as {result['polaris_id']}"
                )

                print(
                    "  ANALYZED: "
                    f"stars={analysis.get('stars_detected')}, "
                    f"quality={analysis.get('quality_score')}"
                )

            elif result["status"] == "skipped":
                skipped.append(result)

                print(
                    "  SKIPPED: "
                    f"{result.get('reason', 'Already imported')}"
                )

            else:
                failed_result = {
                    "session_folder": str(
                        session_folder
                    ),
                    "error": (
                        "Unknown importer status: "
                        f"{result.get('status')}"
                    ),
                }

                failed.append(
                    failed_result
                )

                print(
                    "  FAILED: Unknown importer status"
                )

        except Exception as exc:
            db.rollback()

            failed_result = {
                "session_folder": str(
                    session_folder
                ),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

            failed.append(
                failed_result
            )

            print(
                "  FAILED: "
                f"{type(exc).__name__}: {exc}"
            )

        finally:
            db.close()

    return {
        "archive_root": str(archive_root),
        "sessions_found": len(session_folders),
        "imported_count": len(imported),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "imported": imported,
        "skipped": skipped,
        "failed": failed,
    }


def import_single_session(
    session_folder: Path,
) -> Dict:
    db = SessionLocal()

    try:
        return import_one_session(
            db=db,
            session_folder=session_folder,
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def write_report(
    report: Dict,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            report,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Import and analyze one DWARF session "
            "folder or an entire DWARF archive."
        )
    )

    parser.add_argument(
        "source",
        type=Path,
        help=(
            "Path to one DWARF_RAW_TELE session folder "
            "or the DWARF archive root containing "
            "the Astronomy folder."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=(
            Path.home()
            / "Desktop"
            / "polaris_import_report.json"
        ),
        help=(
            "Path for the bulk-import JSON report."
        ),
    )

    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    output_path = args.output.expanduser().resolve()

    if not source.exists():
        print(
            "\nDWARF import failed.",
            file=sys.stderr,
        )

        print(
            "FileNotFoundError: "
            "Source was not found:\n"
            f"{source}",
            file=sys.stderr,
        )

        sys.exit(1)

    try:
        if source.name.startswith(
            SESSION_PREFIX
        ):
            result = import_single_session(
                session_folder=source,
            )

            print(
                json.dumps(
                    result,
                    indent=2,
                )
            )

            return

        report = import_archive(
            archive_root=source,
        )

        write_report(
            report=report,
            output_path=output_path,
        )

        print("\nBulk import complete.")
        print(
            "Sessions found: "
            f"{report['sessions_found']}"
        )
        print(
            "Imported and analyzed: "
            f"{report['imported_count']}"
        )
        print(
            "Skipped: "
            f"{report['skipped_count']}"
        )
        print(
            "Failed: "
            f"{report['failed_count']}"
        )
        print(
            "Report saved to: "
            f"{output_path}"
        )

        if report["failed_count"] > 0:
            sys.exit(1)

    except Exception as exc:
        print(
            "\nDWARF import failed.",
            file=sys.stderr,
        )

        print(
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        sys.exit(1)


if __name__ == "__main__":
    main()