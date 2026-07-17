import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.core.storage import POLARIS_ROOT
from app.database.database import SessionLocal
from app.services.capture_sync_service import (
    synchronize_capture_library,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the Polaris capture library and optionally register valid "
            "orphan FITS files without changing source files."
        )
    )
    parser.add_argument(
        "library_root",
        nargs="?",
        type=Path,
        default=POLARIS_ROOT,
        help="Polaris library containing targets/<target>/fits folders.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Register valid orphan FITS files in the database.",
    )
    args = parser.parse_args()
    db = SessionLocal()

    try:
        report = synchronize_capture_library(
            db=db,
            library_root=args.library_root,
            apply=args.apply,
        )
    finally:
        db.close()

    print(json.dumps(report, indent=2))

    if report["conflict_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
