import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.services.backup_verification_service import (
    DEFAULT_DATABASE_NAME,
    DEFAULT_LIBRARY_NAME,
    verify_backup_pair,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify a copied Polaris database and capture library as a "
            "matched backup pair without changing either one."
        )
    )
    parser.add_argument(
        "backup_root",
        type=Path,
        help=(
            "Backup folder containing polaris.db and the ProjectPolaris "
            "capture-library folder."
        ),
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_DATABASE_NAME,
        help=(
            "Database filename relative to the backup folder, or an absolute "
            "path. Defaults to polaris.db."
        ),
    )
    parser.add_argument(
        "--library",
        default=DEFAULT_LIBRARY_NAME,
        help=(
            "Capture-library folder relative to the backup folder, or an "
            "absolute path. Defaults to ProjectPolaris."
        ),
    )
    args = parser.parse_args()
    report = verify_backup_pair(
        backup_root=args.backup_root,
        database_name=args.database,
        library_name=args.library,
    )

    print(json.dumps(report, indent=2))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

