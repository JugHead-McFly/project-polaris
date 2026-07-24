"""Preview or apply Quality Scoring v2 to original FITS captures."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.database import SessionLocal
from app.models import Capture
from app.services.capture_analysis_service import (
    analyze_and_save_capture,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reanalyze original FITS captures with Quality Scoring v2. "
            "The default is a read-only preview."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist v2 measurements and scores.",
    )
    parser.add_argument(
        "--backup-file",
        type=Path,
        help=(
            "Required with --apply. Path to a verified database backup "
            "created before the migration."
        ),
    )
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.apply:
        if (
            arguments.backup_file is None
            or not arguments.backup_file.is_file()
        ):
            print(
                "--apply requires an existing --backup-file.",
                file=sys.stderr,
            )
            return 2

    db = SessionLocal()
    try:
        captures = (
            db.query(Capture)
            .filter(Capture.asset_path.isnot(None))
            .order_by(Capture.id)
            .all()
        )
        if not arguments.apply:
            print(
                f"Dry run: {len(captures)} captures are eligible for "
                "Quality Scoring v2 reanalysis."
            )
            for capture in captures:
                print(
                    f"{capture.polaris_id}: {capture.object_name} "
                    f"({capture.asset_path})"
                )
            return 0

        for capture in captures:
            result = analyze_and_save_capture(
                db=db,
                capture=capture,
            )
            score = result["quality_score"]
            score_label = (
                f"{score}/100"
                if score is not None
                else "not scored"
            )
            print(
                f"{capture.polaris_id}: {capture.object_name} -> "
                f"{score_label} "
                f"({result['analysis_confidence']} confidence)"
            )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
