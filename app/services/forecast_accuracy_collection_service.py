"""Scheduled forecast-accuracy collection within explicit tenant scopes."""

import logging
from typing import Callable
from typing import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.database.database import TENANT_SESSION_KEY
from app.services.forecast_accuracy_service import track_forecast_accuracy
from app.services.hosted_account_service import get_primary_observatory
from app.services.hosted_account_service import (
    planning_context_from_observatory,
)
from app.services.planner_service import get_tonight_plan


LOGGER = logging.getLogger(__name__)


def collect_forecast_accuracy(
    user_ids: Iterable[UUID],
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> dict[str, int]:
    """Run one forecast check for each explicitly configured tenant."""
    configured_user_ids = tuple(dict.fromkeys(user_ids))
    report = {
        "configured_tenants": len(configured_user_ids),
        "processed_tenants": 0,
        "skipped_without_observatory": 0,
        "failed_tenants": 0,
    }

    for user_id in configured_user_ids:
        db = session_factory()
        if not hasattr(db, "info"):
            db.info = {}
        db.info[TENANT_SESSION_KEY] = user_id
        try:
            observatory = get_primary_observatory(db, user_id=user_id)
            if observatory is None:
                report["skipped_without_observatory"] += 1
                continue

            planner = get_tonight_plan(
                db,
                observatory=planning_context_from_observatory(observatory),
                use_capture_history=False,
            )
            track_forecast_accuracy(
                db,
                user_id=user_id,
                observatory=observatory,
                weather=planner["weather"],
            )
            report["processed_tenants"] += 1
        except Exception:
            db.rollback()
            report["failed_tenants"] += 1
            LOGGER.exception(
                "Forecast accuracy collection failed for one configured "
                "tenant."
            )
        finally:
            db.close()

    return report
