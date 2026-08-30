from datetime import datetime
from datetime import timedelta
from datetime import timezone
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.models import ForecastAccuracySnapshot
from app.models import HostedObservatory
from app.models import Profile
from app.services.forecast_accuracy_service import track_forecast_accuracy


USER_ID = UUID("4d3d6526-f7ce-4e5a-a4d9-4dca6bf671ba")


def _database(timezone_name="America/Phoenix"):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(Profile(user_id=USER_ID))
    observatory = HostedObservatory(
        user_id=USER_ID,
        name="Home",
        latitude=33.3,
        longitude=-111.7,
        timezone_name=timezone_name,
    )
    db.add(observatory)
    db.commit()
    db.refresh(observatory)
    return db, observatory


def _forecast_weather(**overrides):
    weather = {
        "provider": "open-meteo",
        "status": "Live weather connected.",
        "fetched_at": "2026-08-30T18:00:00+00:00",
        "observed_at": "2026-08-30T11:00",
        "temperature_f": 90,
        "cloud_cover_percent": 12,
        "humidity_percent": 30,
        "dew_point_f": 55,
        "wind_speed_mph": 5,
        "planned_temperature_at": "2026-08-30 08:00 PM",
        "planned_temperature_f": 82,
        "planned_cloud_cover_percent": 20,
        "planned_humidity_percent": 40,
        "planned_dew_point_f": 54,
        "planned_wind_speed_mph": 7,
    }
    weather.update(overrides)
    return weather


def test_saves_one_minimal_snapshot_per_observatory_forecast_hour():
    db, observatory = _database()
    checked_at = datetime(2026, 8, 30, 18, tzinfo=timezone.utc)

    first = track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather=_forecast_weather(),
        checked_at=checked_at,
    )
    track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather=_forecast_weather(planned_cloud_cover_percent=24),
        checked_at=checked_at + timedelta(minutes=10),
    )

    snapshots = db.query(ForecastAccuracySnapshot).all()
    assert len(snapshots) == 1
    assert snapshots[0].forecast_cloud_cover_percent == 24
    assert snapshots[0].forecast_provider == "open-meteo"
    assert snapshots[0].status == "pending"
    assert first["state"] == "building"
    assert first["confidence"] is None


def test_matches_near_observation_without_fabricating_values():
    db, observatory = _database()
    track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather=_forecast_weather(),
        checked_at=datetime(2026, 8, 30, 18, tzinfo=timezone.utc),
    )

    summary = track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather=_forecast_weather(
            fetched_at="2026-08-31T03:20:00+00:00",
            observed_at="2026-08-30T20:00",
            temperature_f=79,
            cloud_cover_percent=31,
            humidity_percent=47,
            dew_point_f=None,
            wind_speed_mph=9,
        ),
        checked_at=datetime(2026, 8, 31, 3, 20, tzinfo=timezone.utc),
    )

    snapshot = db.query(ForecastAccuracySnapshot).one()
    assert snapshot.status == "matched"
    assert snapshot.observed_cloud_cover_percent == 31
    assert snapshot.observed_dew_point_f is None
    assert summary["matched_samples"] == 1
    assert summary["confidence"] is None


def test_missing_weather_creates_no_snapshot_or_match():
    db, observatory = _database()
    summary = track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather={"status": "Weather unavailable"},
        checked_at=datetime(2026, 8, 30, 18, tzinfo=timezone.utc),
    )

    assert db.query(ForecastAccuracySnapshot).count() == 0
    assert summary["matched_samples"] == 0
    assert "Not enough verified history" in summary["message"]


def test_observation_outside_boundary_does_not_match():
    db, observatory = _database()
    track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather=_forecast_weather(),
        checked_at=datetime(2026, 8, 30, 18, tzinfo=timezone.utc),
    )

    track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather=_forecast_weather(
            observed_at="2026-08-30T18:44",
            planned_temperature_at=None,
        ),
        checked_at=datetime(2026, 8, 31, 1, 44, tzinfo=timezone.utc),
    )

    snapshot = db.query(ForecastAccuracySnapshot).one()
    assert snapshot.status == "pending"
    assert snapshot.observed_at is None


def test_observation_at_exact_boundary_matches():
    db, observatory = _database()
    track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather=_forecast_weather(),
        checked_at=datetime(2026, 8, 30, 18, tzinfo=timezone.utc),
    )

    summary = track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather=_forecast_weather(
            observed_at="2026-08-30T18:45",
            planned_temperature_at=None,
        ),
        checked_at=datetime(2026, 8, 31, 1, 45, tzinfo=timezone.utc),
    )

    snapshot = db.query(ForecastAccuracySnapshot).one()
    assert snapshot.status == "matched"
    assert summary["matched_samples"] == 1


def test_timezone_day_boundary_maps_local_forecast_to_utc():
    db, observatory = _database("Asia/Manila")
    track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather=_forecast_weather(
            observed_at="2026-08-30T20:00",
            planned_temperature_at="2026-08-31 01:00 AM",
        ),
        checked_at=datetime(2026, 8, 30, 12, tzinfo=timezone.utc),
    )

    snapshot = db.query(ForecastAccuracySnapshot).one()
    forecast_for = snapshot.forecast_for.replace(tzinfo=timezone.utc)
    assert forecast_for == datetime(2026, 8, 30, 17, tzinfo=timezone.utc)


def test_retention_removes_snapshots_older_than_ninety_days():
    db, observatory = _database()
    checked_at = datetime(2026, 8, 30, 18, tzinfo=timezone.utc)
    db.add(
        ForecastAccuracySnapshot(
            user_id=USER_ID,
            observatory_id=observatory.id,
            forecast_for=checked_at - timedelta(days=100),
            forecast_created_at=checked_at - timedelta(days=101),
            expires_at=checked_at - timedelta(days=100),
            created_at=checked_at - timedelta(days=101),
            status="expired",
        )
    )
    db.commit()

    track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather={"status": "Weather unavailable"},
        checked_at=checked_at,
    )

    assert db.query(ForecastAccuracySnapshot).count() == 0


def test_pending_snapshot_expires_without_observed_values():
    db, observatory = _database()
    track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather=_forecast_weather(),
        checked_at=datetime(2026, 8, 30, 18, tzinfo=timezone.utc),
    )

    track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather={"status": "Weather unavailable"},
        checked_at=datetime(2026, 8, 31, 5, 1, tzinfo=timezone.utc),
    )

    snapshot = db.query(ForecastAccuracySnapshot).one()
    assert snapshot.status == "expired"
    assert snapshot.observed_at is None


def test_enough_matches_still_does_not_claim_confidence():
    db, observatory = _database()
    checked_at = datetime(2026, 8, 30, 18, tzinfo=timezone.utc)
    for offset in range(5):
        forecast_for = checked_at - timedelta(hours=offset + 1)
        db.add(
            ForecastAccuracySnapshot(
                user_id=USER_ID,
                observatory_id=observatory.id,
                forecast_for=forecast_for,
                forecast_created_at=forecast_for - timedelta(hours=12),
                expires_at=forecast_for + timedelta(hours=2),
                observed_at=forecast_for,
                status="matched",
            )
        )
    db.commit()

    summary = track_forecast_accuracy(
        db,
        user_id=USER_ID,
        observatory=observatory,
        weather={"status": "Weather unavailable"},
        checked_at=checked_at,
    )

    assert summary["state"] == "ready_for_calibration"
    assert summary["matched_samples"] == 5
    assert summary["confidence"] is None
    assert "not using them in tonight's score" in summary["message"]
