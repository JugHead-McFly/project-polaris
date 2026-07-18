import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.core.startup_preflight import run_startup_preflight


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check Project Polaris paths, database, web assets, and runtime "
            "configuration before starting the API."
        )
    )
    parser.parse_args()
    report = run_startup_preflight()
    print(json.dumps(report, indent=2))
    if not report["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

