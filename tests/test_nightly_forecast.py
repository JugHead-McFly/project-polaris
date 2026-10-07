from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models import Profile, HostedObservatory, NightlyForecast
from app.services.nightly_forecast_service import collect_nightly, forecast_window, observation_summary, nightly_summary

START = datetime(2026, 10, 6, 20, tzinfo=timezone.utc)
END = START+timedelta(hours=2)


def setup():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = uuid4()
    db.add(Profile(user_id=user))
    home = HostedObservatory(user_id=user, name="Home", latitude=33.28, longitude=-111.72, timezone_name="America/Phoenix")
    db.add(home)
    db.commit()
    return db, home


def weather(now, value=10):
    return {"fetched_at": now.isoformat(), "provider": "test", "hourly_forecast": {
        START.isoformat(): {"cloud_cover_percent": value},
        (START+timedelta(hours=1)).isoformat(): {"cloud_cover_percent": value},
    }}


def run(db, home, at, value=10, **extra):
    return collect_nightly(db, user_id=home.user_id, observatory=home, now=at,
        clock=lambda: at, weather_fetch=lambda *a, **kw: weather(at, value),
        darkness=lambda **kw: (START-timedelta(hours=1), START, END), **extra)


def test_prospective_snapshots_are_immutable_separate_and_never_backfilled():
    db, home = setup()
    assert run(db, home, START-timedelta(hours=6, minutes=5))["snapshots_saved"] == 1
    run(db, home, START-timedelta(hours=6, minutes=2), value=90)
    row = db.query(NightlyForecast).one()
    assert row.forecasts["afternoon"]["average"] == 10
    assert "dusk" not in row.forecasts
    run(db, home, START-timedelta(minutes=5), value=20)
    assert row.forecasts["dusk"]["average"] == 20
    assert len(row.forecasts) == 2
    db2, home2 = setup()
    run(db2, home2, START+timedelta(minutes=1))
    assert all(s["status"] == "missed" for s in db2.query(NightlyForecast).one().forecasts.values())


def test_late_fetch_cannot_be_labelled_as_dusk_forecast():
    db, home = setup()
    at = START-timedelta(minutes=1)
    collect_nightly(db, user_id=home.user_id, observatory=home, now=at,
        clock=lambda: START+timedelta(seconds=1), weather_fetch=lambda *a, **kw: weather(at),
        darkness=lambda **kw: (START, START, END))
    assert db.query(NightlyForecast).one().forecasts["dusk"]["status"] == "missed"


def test_weighted_window_clips_edges_and_reports_missing_hours():
    at = START+timedelta(minutes=30)
    w = weather(START)
    w["hourly_forecast"][START.isoformat()]["cloud_cover_percent"] = 100
    assert forecast_window(w, at, END, "UTC")["average"] == 40
    del w["hourly_forecast"][START.isoformat()]
    result = forecast_window(w, at, END, "UTC")
    assert result["average"] is None
    assert result["coverage"] == pytest.approx(2/3)


def satellite(target, lat, lon):
    return {"status": "usable", "cloud_cover_percent": 5, "forecast_for": target.isoformat(),
            "scan_midpoint": target.isoformat(), "good_pixel_fraction": 1,
            "time_offset_seconds": 0}


def test_full_night_collection_resumes_is_owned_and_records_distinct_horizons():
    db, home = setup()
    run(db, home, START-timedelta(hours=6, minutes=5), value=40)
    run(db, home, START-timedelta(minutes=5), value=5)
    result = run(db, home, END+timedelta(hours=1), satellite_fetch=satellite)
    assert result["satellite_samples"] == 24
    assert result["completed_nights"] == 1
    assert run(db, home, END+timedelta(hours=2), satellite_fetch=lambda *a: pytest.fail("repeat download"))["satellite_samples"] == 0
    summary = nightly_summary(db, user_id=home.user_id, observatory_id=home.id)
    afternoon, dusk = summary["horizons"]
    assert afternoon["count"] == dusk["count"] == 1
    assert afternoon["missed_clear"] == 1
    assert dusk["missed_clear"] == 0
    assert not afternoon["review_ready"]
    assert nightly_summary(db, user_id=uuid4(), observatory_id=home.id)["completed_nights"] == 0


def test_missing_duplicate_and_low_quality_samples_do_not_inflate_coverage():
    cells = [{"target": (START+timedelta(minutes=5*i)).isoformat(), "seconds": 300,
              "reference": satellite(START+timedelta(minutes=5*i), 0, 0)} for i in range(24)]
    assert observation_summary(cells)["adequate"]
    cells[0]["reference"]["good_pixel_fraction"] = .1
    cells[1]["reference"]["scan_midpoint"] = cells[2]["reference"]["scan_midpoint"]
    cells[3]["reference"] = None
    result = observation_summary(cells)
    assert not result["adequate"]
    assert result["average"] is None
    assert result["coverage"] == pytest.approx(21/24)


def test_retry_budget_records_gaps_without_inventing_clear_sky():
    db, home = setup()
    run(db, home, START-timedelta(minutes=5))
    def failed(*a):
        raise ValueError("unavailable")
    for i in range(3):
        run(db, home, END+timedelta(hours=1, minutes=i*5), satellite_fetch=failed)
    row = db.query(NightlyForecast).one()
    assert row.observation["complete"]
    assert not row.observation["adequate"]
    assert row.observation["average"] is None
    assert all(c["attempts"] == 3 for c in row.observation["cells"])


def test_method_and_source_mix_changes_do_not_mix_cohorts():
    db, home = setup()
    run(db, home, START-timedelta(hours=6, minutes=5))
    run(db, home, END+timedelta(hours=1), satellite_fetch=satellite)
    original = db.query(NightlyForecast).one()
    new = NightlyForecast(user_id=home.user_id, observatory_id=home.id,
        night_date=original.night_date+timedelta(days=1), window_start=START+timedelta(days=1),
        window_end=END+timedelta(days=1), latitude=home.latitude, longitude=home.longitude,
        timezone_name=home.timezone_name,
        forecasts={"afternoon": {**original.forecasts["afternoon"], "source_mix": ["different"]}}, observation={})
    db.add(new); db.commit()
    assert nightly_summary(db, user_id=home.user_id, observatory_id=home.id)["horizons"][0]["count"] == 0


def test_location_change_and_scans_outside_darkness_are_excluded():
    db, home = setup()
    run(db, home, START-timedelta(hours=6, minutes=5))
    home.latitude += 1
    db.commit()
    run(db, home, START-timedelta(minutes=5))
    assert db.query(NightlyForecast).one().forecasts["dusk"]["status"] == "location_changed"
    def outside(target, lat, lon):
        return {**satellite(target, lat, lon), "scan_midpoint": (END+timedelta(minutes=1)).isoformat()}
    run(db, home, END+timedelta(hours=1), satellite_fetch=outside)
    assert db.query(NightlyForecast).one().observation["average"] is None
