import argparse
import json
import sys
from pathlib import Path
from typing import Dict


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


def analyze_all_captures() -> Dict:
    db = SessionLocal()

    analyzed = []
    failed = []

    try:
        captures = (
            db.query(Capture)
            .order_by(Capture.id)
            .all()
        )

        total = len(captures)

        for index, capture in enumerate(
            captures,
            start=1,
        ):
            print(
                f"\n[{index}/{total}] "
                f"{capture.polaris_id} "
                f"{capture.object_name}"
            )

            try:
                result = analyze_and_save_capture(
                    db=db,
                    capture=capture,
                )

                analyzed.append(result)

                print(
                    "  ANALYZED: "
                    f"stars={result['stars_detected']}, "
                    f"analysis_id={result['analysis_id']}"
                )

            except Exception as exc:
                db.rollback()

                failed_result = {
                    "capture_database_id": capture.id,
                    "polaris_id": capture.polaris_id,
                    "object_name": capture.object_name,
                    "asset_path": capture.asset_path,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }

                failed.append(failed_result)

                print(
                    "  FAILED: "
                    f"{type(exc).__name__}: {exc}"
                )

        return {
            "captures_found": total,
            "analyzed_count": len(analyzed),
            "failed_count": len(failed),
            "analyzed": analyzed,
            "failed": failed,
        }

    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze all captures currently stored "
            "in Project Polaris."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=(
            Path.home()
            / "Desktop"
            / "polaris_analysis_report.json"
        ),
        help="Path for the JSON analysis report.",
    )

    args = parser.parse_args()

    output_path = args.output.expanduser().resolve()

    try:
        report = analyze_all_captures()

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

        print("\nAnalysis backfill complete.")
        print(
            f"Captures found: "
            f"{report['captures_found']}"
        )
        print(
            f"Analyzed: "
            f"{report['analyzed_count']}"
        )
        print(
            f"Failed: "
            f"{report['failed_count']}"
        )
        print(
            f"Report saved to: "
            f"{output_path}"
        )

        if report["failed_count"] > 0:
            sys.exit(1)

    except Exception as exc:
        print(
            "\nAnalysis backfill failed.",
            file=sys.stderr,
        )
        print(
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()