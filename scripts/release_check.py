import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.services.release_readiness_service import (
    build_release_readiness_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Project Polaris release gates without tagging, pushing, "
            "or changing the backup pair."
        )
    )
    parser.add_argument(
        "--expected-version",
        required=True,
        help="Exact release version expected from the application.",
    )
    parser.add_argument(
        "--backup-root",
        required=True,
        type=Path,
        help="Timestamped folder containing polaris.db and ProjectPolaris.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Running local Polaris API used for live smoke checks.",
    )
    parser.add_argument(
        "--expected-branch",
        default="develop",
        help="Git branch that must be clean for the release check.",
    )
    args = parser.parse_args()
    report = build_release_readiness_report(
        project_root=PROJECT_ROOT,
        backup_root=args.backup_root,
        base_url=args.base_url,
        expected_version=args.expected_version,
        expected_branch=args.expected_branch,
    )
    print(json.dumps(report, indent=2))
    if not report["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

