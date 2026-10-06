from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models import ForecastAccuracySnapshot, HostedObservatory, Profile
from app.services.forecast_accuracy_service import forecast_accuracy_summary
from app.services.satellite_cloud_service import collect_satellite_references, _midpoint


NOW = datetime(2026, 10, 6, 23, tzinfo=timezone.utc)


def database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    homes = []
    for _ in range(2):
        user = uuid4()
        db.add(Profile(user_id=user))
        home = HostedObservatory(user_id=user, name="Home", latitude=33.28,
                                 longitude=-111.72, timezone_name="America/Phoenix")
        db.add(home)
        db.flush()
        homes.append(home)
        for lead in (1, 2):
            db.add(ForecastAccuracySnapshot(
                user_id=user, observatory_id=home.id,
                forecast_for=NOW-timedelta(days=1),
                forecast_created_at=NOW-timedelta(days=1, hours=lead),
                forecast_lead_hour=lead, forecast_cloud_cover_percent=20,
                expires_at=NOW, status="expired",
            ))
    db.commit()
    return db, homes


def reference(target, lat, lon):
    return {"status": "usable", "forecast_for": target.isoformat(),
            "scan_midpoint": (target-timedelta(minutes=2)).isoformat(),
            "good_pixel_fraction": 1, "cloud_cover_percent": 30, "radius_km": 10}


def test_backfill_is_idempotent_owned_and_independent_of_model_match():
    db, (home, other) = database()
    before = forecast_accuracy_summary(db, user_id=home.user_id, observatory_id=home.id)
    assert before["saved_forecast_count"] == 1
    assert before["satellite_reliability"]["check_count"] == 0
    result = collect_satellite_references(db, user_id=home.user_id, observatory=home,
                                          fetch=reference, now=NOW)
    assert result["completed_targets"] == 1
    assert all(r.status == "expired" and r.forecast_cloud_cover_percent == 20
               for r in db.query(ForecastAccuracySnapshot).all())
    assert all(r.satellite_cloud_observation is None for r in
               db.query(ForecastAccuracySnapshot).filter_by(user_id=other.user_id))
    assert collect_satellite_references(db, user_id=home.user_id, observatory=home,
                                        fetch=lambda *a: pytest.fail("Repeated download"), now=NOW)["completed_targets"] == 0
    after = forecast_accuracy_summary(db, user_id=home.user_id, observatory_id=home.id)
    assert after["satellite_reliability"]["check_count"] == 1
    assert after["saved_revision_count"] == 2
    assert after["pending_satellite_count"] == 0
    # A second device/request sees the same account-owned database history.
    second = sessionmaker(bind=db.get_bind())()
    assert forecast_accuracy_summary(second, user_id=home.user_id, observatory_id=home.id) == after
    assert forecast_accuracy_summary(second, user_id=other.user_id, observatory_id=home.id)["saved_forecast_count"] == 0
    with pytest.raises(ValueError, match="owner mismatch"):
        collect_satellite_references(db, user_id=other.user_id, observatory=home)


def test_future_and_post_target_forecasts_are_not_backfilled_and_failures_retry():
    db, (home, _) = database()
    rows = db.query(ForecastAccuracySnapshot).filter_by(user_id=home.user_id).all()
    rows[0].forecast_for = NOW+timedelta(hours=3)
    rows[1].forecast_created_at = rows[1].forecast_for+timedelta(minutes=1)
    db.commit()
    result = collect_satellite_references(db, user_id=home.user_id, observatory=home,
                                          fetch=lambda *a: pytest.fail("Invalid target"), now=NOW)
    assert sum(result.values()) == 0
    rows[1].forecast_created_at = NOW-timedelta(days=2)
    db.commit()
    def offline(*args):
        raise ValueError("Network unavailable")
    assert collect_satellite_references(db, user_id=home.user_id, observatory=home,
                                        fetch=offline, now=NOW)["retry_targets"] == 1
    assert rows[1].satellite_cloud_observation is None
    assert collect_satellite_references(db, user_id=home.user_id, observatory=home,
                                        fetch=reference, now=NOW)["completed_targets"] == 1


def test_scan_midpoint_uses_actual_end_and_crosses_midnight():
    value = _midpoint("OR_ABI-L2-ACMC-M6_G18_s20262792359000_e20262800001300_c20262800002000.nc")
    assert value == datetime(2026, 10, 7, 0, 0, 15, tzinfo=timezone.utc)


def test_bad_quality_is_preserved_but_never_scored():
    db, (home, _) = database()
    def bad(target, lat, lon):
        return {**reference(target, lat, lon), "status": "insufficient_quality",
                "good_pixel_fraction": .2, "cloud_cover_percent": None}
    assert collect_satellite_references(db, user_id=home.user_id, observatory=home,
                                        fetch=bad, now=NOW)["unusable_targets"] == 1
    result = forecast_accuracy_summary(db, user_id=home.user_id, observatory_id=home.id)
    assert result["satellite_reliability"]["check_count"] == 0
    assert result["saved_forecast_count"] == 1
