#!/usr/bin/env python3
"""Collect hosted forecast comparisons for explicitly configured tenants."""

import json
import os
import sys
from pathlib import Path
from uuid import UUID


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

USER_IDS_ENV = "POLARIS_FORECAST_ACCURACY_USER_IDS"


def parse_user_ids(value: str) -> tuple[UUID, ...]:
    """Parse a comma-separated, de-duplicated tenant allowlist."""
    values = [item.strip() for item in value.split(",") if item.strip()]
    if not values:
        raise ValueError(f"{USER_IDS_ENV} must contain at least one UUID.")

    try:
        return tuple(dict.fromkeys(UUID(item) for item in values))
    except ValueError as error:
        raise ValueError(
            f"{USER_IDS_ENV} must be a comma-separated list of UUIDs."
        ) from error


def main() -> None:
    from app.services.forecast_accuracy_collection_service import (
        collect_forecast_accuracy,
    )

    try:
        user_ids = parse_user_ids(os.getenv(USER_IDS_ENV, ""))
    except ValueError as error:
        raise SystemExit(str(error)) from error

    report = collect_forecast_accuracy(user_ids)
    print(json.dumps(report, sort_keys=True))
    if report["failed_tenants"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
