#!/usr/bin/env python3
"""Print a privacy-safe aggregate health report for the private alpha."""

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import inspect


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.core.config import settings
from app.database.database import SessionLocal
from app.services.alpha_metrics_service import build_alpha_metrics_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Print aggregate private-alpha health metrics without any "
            "personal observatory data."
        )
    )
    parser.add_argument(
        "--confirm-production-read",
        action="store_true",
        help=(
            "Required when POLARIS_ENVIRONMENT=production. The script is "
            "read-only and prints aggregate counts only."
        ),
    )
    arguments = parser.parse_args()

    if (
        settings.ENVIRONMENT == "production"
        and not arguments.confirm_production_read
    ):
        raise SystemExit(
            "Refusing a production database read without "
            "--confirm-production-read."
        )

    database = SessionLocal()
    try:
        required_tables = {
            "profiles",
            "observatories",
            "recommendation_runs",
            "recommendation_feedback",
        }
        available_tables = set(
            inspect(database.get_bind()).get_table_names()
        )
        missing_tables = required_tables - available_tables
        if missing_tables:
            missing_text = ", ".join(sorted(missing_tables))
            raise SystemExit(
                "The configured database is not the hosted alpha database "
                f"(missing: {missing_text})."
            )
        report = build_alpha_metrics_report(database)
    finally:
        database.close()

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
