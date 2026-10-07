#!/usr/bin/env python3
"""Collect hosted forecast comparisons for explicitly configured tenants."""

import json
import os
import sys
from datetime import datetime, timezone
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

    from app.database.database import SessionLocal, TENANT_SESSION_KEY
    from app.services.hosted_account_service import get_primary_observatory
    from app.services.nightly_forecast_service import collect_nightly
    report = {"nightly": [], "failed_tenants": 0}
    for user_id in user_ids:
        with SessionLocal() as db:
            db.info[TENANT_SESSION_KEY] = user_id
            try:
                home = get_primary_observatory(db, user_id=user_id)
                if home:
                    report["nightly"].append(collect_nightly(db, user_id=user_id, observatory=home))
            except Exception:
                db.rollback()
                import logging
                logging.exception("Nightly collection failed for configured tenant")
                report["failed_tenants"] += 1
    # Retain the old individual-time history on its hourly cadence. Nightly
    # snapshot capture runs first and does not require building a target plan.
    if 15 <= datetime.now(timezone.utc).minute < 20:
        legacy = collect_forecast_accuracy(user_ids)
        report["legacy"] = legacy
        report["failed_tenants"] += legacy["failed_tenants"]
    print(json.dumps(report, sort_keys=True))
    if report["failed_tenants"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
